import random
from typing import Any, Optional

from ...data.battle_mode_config import BATTLE_MODE_SOLO
from ...data.grid_map_config import FLOOR_CONFIGS, PASSABLE_ROOM_TYPES, ROOM_ICONS
from ...data.locale_data import get_locale_text
from ...data.map_quest_config import (
    BLEAK_FALLS_FLOOR_INDEX,
    BLEAK_FALLS_MAP_HEIGHT,
    BLEAK_FALLS_MAP_WIDTH,
    BLEAK_FALLS_REWARDS,
    BLEAK_FALLS_ROOMS,
    BLEAK_FALLS_START_COORD,
    BLEAK_SANCTUARY_FLOOR_INDEX,
    BLEAK_SANCTUARY_MAP_HEIGHT,
    BLEAK_SANCTUARY_MAP_WIDTH,
    BLEAK_SANCTUARY_ROOMS,
    BLEAK_SANCTUARY_START_COORD,
    ITEM_ARVEL_JOURNAL,
    ITEM_DRAGONSTONE,
    ITEM_GOLDEN_CLAW,
    ITEM_NORDIC_MEAD,
    ITEM_QGP_BOMB,
    NEXT_FLOOR_AFTER_BLEAK_FALLS,
    NPC_ARVEL_TRAPPED,
    NPC_BRAZIER_KEEPER,
    NPC_FARENGAR_ROOM,
    NPC_MAP_SURVEYOR,
    QUEST_ANCIENT_CARTOGRAPHER,
    QUEST_BLEAK_FALLS,
    QUEST_RUNIC_ECHOES,
    RANDOM_QUEST_CONFIG,
    ROOM_BARROW_EXIT,
    ROOM_BLEAK_ENTRANCE,
    ROOM_CLAW_DOOR,
    ROOM_PILLAR_PUZZLE,
    ROOM_SANCTUARY_GATE,
    ROOM_SOLID_WALL,
    ROOM_WORD_WALL,
)
from ...entities import ALL_CARDS
from ...models.state import EnemyState, FloorMapState, GameRun, RoomState, UserStats, ensure_card_state
from ..inventory.bag_service import add_bag_item
from ..inventory.deck_service import DeckService
from ..party.coordinator import add_notice, apply_and_scope, restore_player, swap_player
from ..party.session import SessionContextScoper
from ..text.events import LocaleText, RenderedText, locale_text
from ..text.pipeline import render_text_node
from .grid_map_generator import coord_to_xy, xy_to_coord
from .sp_system import restore_sp
from .map_quest_service import (
    accept_random_quest,
    complete_random_quest,
    get_bleak_falls_entry,
    give_item_or_drop,
    is_bleak_falls_done_or_tavern_ready,
    sync_run_to_stats,
    update_bleak_falls_stage,
)


BLEAK_LANDMARK_TYPES = {
    ROOM_BLEAK_ENTRANCE,
    ROOM_PILLAR_PUZZLE,
    ROOM_SANCTUARY_GATE,
    ROOM_CLAW_DOOR,
    ROOM_WORD_WALL,
    ROOM_BARROW_EXIT,
}


def _t(key: str, **kwargs: Any) -> str:
    return render_text_node(locale_text(f"i18n_bleak_falls.{key}", params=kwargs))


def _push_post_notice(run: GameRun, msg: str) -> None:
    if not msg:
        return
    bucket = run.node_data.setdefault("post_session_notices", [])
    bucket.append(msg)
    for uid in run.human_uids():
        add_notice(run, uid, msg)


def _find_solid_wall_coord(fm: FloorMapState, around_coord: str) -> Optional[str]:
    cx, cy = coord_to_xy(around_coord)
    if cx < 0:
        return None
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = cx + dx, cy + dy
        if not (0 <= nx < fm.width and 0 <= ny < fm.height):
            continue
        nc = xy_to_coord(nx, ny)
        room = fm.rooms.get(nc)
        if room and room.room_type == ROOM_SOLID_WALL:
            return nc
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = cx + dx, cy + dy
        if not (0 <= nx < fm.width and 0 <= ny < fm.height):
            continue
        nc = xy_to_coord(nx, ny)
        room = fm.rooms.get(nc)
        if room and room.room_type == "wall":
            return nc
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = cx + dx, cy + dy
        if not (0 <= nx < fm.width and 0 <= ny < fm.height):
            continue
        nc = xy_to_coord(nx, ny)
        room = fm.rooms.get(nc)
        if room and room.room_type in ("empty", "obstacle", "battle", "event"):
            return nc
    return None


def on_floor1_boss_cleared(run: GameRun, room: RoomState, save_manager=None) -> Optional[str]:
    fm = getattr(run, "floor_map", None)
    if fm is None or fm.floor_index != 1 or fm.floor_flags.get("yog_quest") or fm.floor_flags.get("bleak_falls_zone"):
        return None
    stats = save_manager.load_stats(run.user_id) if save_manager is not None else None
    if is_bleak_falls_done_or_tavern_ready(stats):
        return None
    qstore = (run.map_data or {}).get("map_quests") or {}
    if QUEST_BLEAK_FALLS in qstore:
        return None
    wall_coord = _find_solid_wall_coord(fm, room.coord)
    if wall_coord is None:
        return None
    wall_room = fm.rooms[wall_coord]
    wall_room.room_type = ROOM_SOLID_WALL
    wall_room.explored = True
    wall_room.cleared = False
    wall_room.npcs.clear()
    wall_room.items.clear()
    wall_room.props.clear()
    if wall_coord not in fm.revealed_coords:
        fm.revealed_coords.append(wall_coord)
    if NPC_FARENGAR_ROOM not in room.npcs:
        room.npcs.append(NPC_FARENGAR_ROOM)
    room.shared_payload["bleak_wall_coord"] = wall_coord
    in_bag, _ = give_item_or_drop(run, room, ITEM_QGP_BOMB)
    update_bleak_falls_stage(run, stats, "need_bomb")
    run.map_data["map_quests"][QUEST_BLEAK_FALLS]["wall_coord"] = wall_coord
    run.map_data["map_quests"][QUEST_BLEAK_FALLS]["boss_coord"] = room.coord
    if save_manager is not None and stats is not None:
        save_manager.save_stats(run.user_id, stats)
    msg = _t("farengar.ambush_notice")
    if not in_bag:
        msg = f"{msg}\n{_t('farengar.ambush_bag_full')}"
    _push_post_notice(run, msg)
    return msg


def _consume_item_from_bag(player, item_id: str) -> bool:
    items = list(getattr(player, "bag_items", []) or [])
    if item_id not in items:
        return False
    items.remove(item_id)
    player.bag_items = items
    return True


def use_qgp_bomb(engine, run: GameRun) -> str:
    if run.node_type != "grid_map" or run.floor_map is None:
        return _t("bomb.not_in_grid")
    fm = run.floor_map
    cur_coord = fm.player_coords.get(run.user_id) or ""
    cx, cy = coord_to_xy(cur_coord)
    target_coord = None
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = cx + dx, cy + dy
        if not (0 <= nx < fm.width and 0 <= ny < fm.height):
            continue
        nc = xy_to_coord(nx, ny)
        rm = fm.rooms.get(nc)
        if rm and rm.room_type == ROOM_SOLID_WALL:
            target_coord = nc
            break
    if target_coord is None:
        return _t("bomb.no_wall_nearby")
    if not _consume_item_from_bag(run.player, ITEM_QGP_BOMB):
        return _t("bomb.no_wall_nearby")
    wall_room = fm.rooms[target_coord]
    wall_room.room_type = ROOM_BLEAK_ENTRANCE
    wall_room.landmark_id = ROOM_BLEAK_ENTRANCE
    wall_room.explored = True
    wall_room.cleared = False
    if target_coord not in fm.revealed_coords:
        fm.revealed_coords.append(target_coord)
    save_mgr = getattr(engine, "save_manager", None)
    stats = save_mgr.load_stats(run.user_id) if save_mgr is not None else None
    update_bleak_falls_stage(run, stats, "wall_breached")
    if save_mgr is not None and stats is not None:
        save_mgr.save_stats(run.user_id, stats)
    from ...renderer import GameRenderer
    return f"{_t('bomb.explode_success')}\n\n{GameRenderer.render_game(run)}"


def generate_bleak_falls_floor(run: GameRun, floor_index: float) -> FloorMapState:
    is_sanctuary = abs(floor_index - BLEAK_SANCTUARY_FLOOR_INDEX) < 1e-4
    width = BLEAK_SANCTUARY_MAP_WIDTH if is_sanctuary else BLEAK_FALLS_MAP_WIDTH
    height = BLEAK_SANCTUARY_MAP_HEIGHT if is_sanctuary else BLEAK_FALLS_MAP_HEIGHT
    start_coord = BLEAK_SANCTUARY_START_COORD if is_sanctuary else BLEAK_FALLS_START_COORD
    layout = BLEAK_SANCTUARY_ROOMS if is_sanctuary else BLEAK_FALLS_ROOMS
    rooms: dict[str, RoomState] = {}
    for y in range(height):
        for x in range(width):
            coord = xy_to_coord(x, y)
            spec = layout.get(coord)
            if spec is None:
                rooms[coord] = RoomState(coord=coord, room_type="wall", explored=False, cleared=True)
                continue
            payload = {}
            for key in ("encounter", "boss_name", "elite_name", "arvel_pending", "bonus_item", "blocks_coords"):
                if key in spec:
                    payload[key] = list(spec[key]) if isinstance(spec[key], list) else spec[key]
            room = RoomState(
                coord=coord,
                room_type=spec["room_type"],
                explored=(coord == start_coord),
                cleared=(spec["room_type"] == "spawn"),
                is_high_danger=bool(spec.get("is_high_danger", False)),
                landmark_id=str(spec.get("landmark_id", "")),
                shared_payload=payload,
                env_id=str(spec.get("env", "dungeon_corridor")),
                props=list(spec.get("props", []) or []),
            )
            rooms[coord] = room
    revealed = [start_coord]
    sx, sy = coord_to_xy(start_coord)
    for nx, ny in ((sx, sy - 1), (sx, sy + 1), (sx - 1, sy), (sx + 1, sy)):
        if 0 <= nx < width and 0 <= ny < height:
            revealed.append(xy_to_coord(nx, ny))
    player_coords = {uid: start_coord for uid in run.human_uids()}
    return FloorMapState(
        floor_index=floor_index,
        width=width,
        height=height,
        rooms=rooms,
        player_coords=player_coords,
        revealed_coords=revealed,
        floor_flags={"bleak_falls_zone": True},
    )


def enter_bleak_floor(save_manager, map_engine, run: GameRun, target_floor: float, stage_key: str) -> str:
    stats = save_manager.load_stats(run.user_id) if save_manager is not None else None
    new_fm = generate_bleak_falls_floor(run, target_floor)
    cfg = FLOOR_CONFIGS.get(target_floor, {})
    stage_min = int(cfg.get("stage_min", 5))
    run.floor_map = new_fm
    run.node_type = "grid_map"
    run.node_data = {}
    for uid in run.human_uids():
        pl = run.players.get(uid)
        if pl is not None and pl.stage < stage_min:
            pl.stage = stage_min
    update_bleak_falls_stage(run, stats, stage_key)
    map_engine.open_floor_arrival_ancient(run)
    if save_manager is not None:
        if stats is not None:
            save_manager.save_stats(run.user_id, stats)
        save_manager.save_save(run.user_id, run)
    msg_key = "entrance.enter_sanctuary_ok" if abs(target_floor - BLEAK_SANCTUARY_FLOOR_INDEX) < 1e-4 else "entrance.enter_ok"
    from ...renderer import GameRenderer
    return f"{_t(msg_key)}\n\n{GameRenderer.render_game(run)}"


def check_move_blocked_by_claw_door(fm: Optional[FloorMapState], from_coord: str, to_coord: str) -> Optional[str]:
    if fm is None or not fm.floor_flags.get("bleak_falls_zone"):
        return None
    cur_room = fm.rooms.get(from_coord)
    if cur_room and cur_room.room_type == ROOM_CLAW_DOOR and not cur_room.shared_payload.get("door_opened"):
        blocked = set(cur_room.shared_payload.get("blocks_coords") or [])
        if to_coord in blocked:
            return _t("puzzles.claw_door_blocked")
    for rm in fm.rooms.values():
        if rm.room_type == ROOM_CLAW_DOOR and not rm.shared_payload.get("door_opened"):
            if to_coord in (rm.shared_payload.get("blocks_coords") or []):
                return _t("puzzles.claw_door_blocked")
    return None


def _player_has_item_anywhere(run: GameRun, room: Optional[RoomState], item_id: str) -> bool:
    if item_id in (getattr(run.player, "bag_items", []) or []):
        return True
    if room is not None and item_id in (room.items or []):
        return True
    return False


def _pack_landmark(ltype: str, title: str, desc: str, options: list[dict[str, Any]]) -> dict[str, Any]:
    tagged = [dict(o, bleak_landmark=True) for o in options]
    return {
        "landmark_type": ltype,
        "title": title,
        "name": title,
        "desc": desc,
        "options": tagged,
    }


def build_bleak_landmark_data(run: GameRun, room: RoomState) -> Optional[dict[str, Any]]:
    ltype = room.landmark_id or room.room_type
    if ltype not in BLEAK_LANDMARK_TYPES:
        return None
    if ltype == ROOM_BLEAK_ENTRANCE:
        return _pack_landmark(
            ltype,
            get_locale_text("i18n_grid_map.room_name.bleak_falls_entrance"),
            _t("entrance.desc"),
            [
                {"action": "enter_1_5", "text": _t("entrance.opt_enter")},
                {"action": "leave", "text": _t("entrance.opt_stay")},
            ],
        )
    if ltype == ROOM_PILLAR_PUZZLE:
        solved = bool(room.shared_payload.get("solved"))
        opts = (
            [{"action": "leave", "text": _t("puzzles.pillar_opt_leave")}]
            if solved
            else [
                {"action": "pillar_correct", "text": _t("puzzles.pillar_opt_correct")},
                {"action": "pillar_wrong_a", "text": _t("puzzles.pillar_opt_wrong_a")},
                {"action": "pillar_wrong_b", "text": _t("puzzles.pillar_opt_wrong_b")},
                {"action": "leave", "text": _t("puzzles.pillar_opt_leave")},
            ]
        )
        return _pack_landmark(
            ltype,
            get_locale_text("i18n_grid_map.room_name.bleak_pillar_puzzle"),
            _t("puzzles.pillar_done_desc" if solved else "puzzles.pillar_desc"),
            opts,
        )
    if ltype == ROOM_SANCTUARY_GATE:
        return _pack_landmark(
            ltype,
            get_locale_text("i18n_grid_map.room_name.bleak_sanctuary_gate"),
            _t("entrance.sanctuary_gate_desc"),
            [
                {"action": "enter_1_67777", "text": _t("entrance.opt_enter_sanctuary")},
                {"action": "leave", "text": _t("entrance.opt_stay")},
            ],
        )
    if ltype == ROOM_CLAW_DOOR:
        opened = bool(room.shared_payload.get("door_opened"))
        opts = (
            [{"action": "leave", "text": _t("puzzles.pillar_opt_leave")}]
            if opened
            else [
                {"action": "claw_open", "text": _t("puzzles.claw_door_opt_open")},
                {"action": "claw_inspect", "text": _t("puzzles.claw_door_opt_inspect")},
                {"action": "leave", "text": _t("puzzles.pillar_opt_leave")},
            ]
        )
        return _pack_landmark(
            ltype,
            get_locale_text("i18n_grid_map.room_name.golden_claw_door"),
            _t("puzzles.claw_door_done" if opened else "puzzles.claw_door_desc"),
            opts,
        )
    if ltype == ROOM_WORD_WALL:
        absorbed = bool(room.shared_payload.get("absorbed"))
        opts = (
            [{"action": "leave", "text": _t("word_wall.opt_leave")}]
            if absorbed
            else [
                {"action": "word_absorb", "text": _t("word_wall.opt_absorb")},
                {"action": "leave", "text": _t("word_wall.opt_leave")},
            ]
        )
        return _pack_landmark(
            ltype,
            get_locale_text("i18n_grid_map.room_name.word_wall"),
            _t("word_wall.done_desc" if absorbed else "word_wall.desc"),
            opts,
        )
    if ltype == ROOM_BARROW_EXIT:
        return _pack_landmark(
            ltype,
            get_locale_text("i18n_grid_map.room_name.barrow_exit"),
            _t("barrow_exit.desc"),
            [
                {"action": "exit_to_floor2", "text": _t("barrow_exit.opt_to_floor2")},
                {"action": "leave", "text": _t("barrow_exit.opt_stay")},
            ],
        )
    return None


def _grant_word_wall_card(run: GameRun, stats: Optional[UserStats]) -> str:
    from ..inventory.card_distribution import CardDistributor

    p = run.player
    cid = CardDistributor.roll_one("word_wall", run, p, stats, fallback="first_aid") or "first_aid"
    DeckService.add_card_to_deck(p, cid)
    card_obj = ALL_CARDS.get(cid)
    return card_obj.name if card_obj else cid


def execute_bleak_landmark_option(save_manager, map_engine, run: GameRun, opt: dict[str, Any]) -> str:
    res = _execute_bleak_landmark_option_inner(save_manager, map_engine, run, opt)
    if save_manager is not None:
        save_manager.save_save(run.user_id, run)
    return res


def _execute_bleak_landmark_option_inner(save_manager, map_engine, run: GameRun, opt: dict[str, Any]) -> str:
    fm = run.floor_map
    coord = fm.player_coords.get(run.user_id) if fm else None
    room = fm.rooms.get(coord) if (fm and coord) else None
    action = opt.get("action", "leave")
    stats = save_manager.load_stats(run.user_id) if save_manager is not None else None
    sid = fm.player_session_map.get(run.user_id, "") if fm is not None else ""
    if sid and fm is not None and sid in fm.active_sessions:
        SessionContextScoper.close_session(run, sid, mark_cleared=False)
    else:
        run.node_type = "grid_map"
        run.node_data.pop("landmark", None)

    if action == "leave" or room is None:
        from ...renderer import GameRenderer
        return GameRenderer.render_game(run)

    if action == "enter_1_5":
        return enter_bleak_floor(save_manager, map_engine, run, BLEAK_FALLS_FLOOR_INDEX, "in_barrow")

    if action == "pillar_correct":
        gold = BLEAK_FALLS_REWARDS["pillar_gold"]
        heal = BLEAK_FALLS_REWARDS["pillar_heal"]
        run.player.gold += gold
        run.player.hp = min(run.player.max_hp, run.player.hp + heal)
        give_item_or_drop(run, room, ITEM_NORDIC_MEAD)
        room.shared_payload["solved"] = True
        room.cleared = True
        return _t("puzzles.pillar_solved", gold=gold)

    if action in ("pillar_wrong_a", "pillar_wrong_b"):
        dmg = min(max(1, run.player.hp - 1), BLEAK_FALLS_REWARDS["pillar_trap_damage"])
        run.player.hp = max(1, run.player.hp - dmg)
        return _t("puzzles.pillar_wrong", dmg=dmg)

    if action == "enter_1_67777":
        has_claw = _player_has_item_anywhere(run, room, ITEM_GOLDEN_CLAW)
        bleak = get_bleak_falls_entry(run, stats) or {}
        if not has_claw and bleak.get("stage") != "got_claw":
            return _t("entrance.need_claw_first")
        return enter_bleak_floor(save_manager, map_engine, run, BLEAK_SANCTUARY_FLOOR_INDEX, "in_sanctuary")

    if action == "claw_inspect":
        return _t("puzzles.claw_door_inspect")

    if action == "claw_open":
        if not _player_has_item_anywhere(run, room, ITEM_GOLDEN_CLAW):
            return _t("puzzles.claw_door_no_claw")
        room.shared_payload["door_opened"] = True
        room.cleared = True
        update_bleak_falls_stage(run, stats, "door_opened")
        if save_manager is not None and stats is not None:
            save_manager.save_stats(run.user_id, stats)
        return _t("puzzles.claw_door_opened")

    if action == "word_absorb":
        if room.shared_payload.get("absorbed"):
            return _t("word_wall.already_absorbed")
        heal = BLEAK_FALLS_REWARDS["word_wall_heal"]
        sp = BLEAK_FALLS_REWARDS["word_wall_sp"]
        gold = BLEAK_FALLS_REWARDS["word_wall_gold"]
        run.player.hp = min(run.player.max_hp, run.player.hp + heal)
        sp_gained = restore_sp(run.player, sp)
        run.player.gold += gold
        cname = _grant_word_wall_card(run, stats)
        room.shared_payload["absorbed"] = True
        room.cleared = True
        return _t("word_wall.absorb_ok", heal=heal, sp=sp_gained, gold=gold, card=cname)

    if action == "exit_to_floor2":
        bleak = run.map_data.setdefault("map_quests", {}).setdefault(QUEST_BLEAK_FALLS, {"kind": "multi", "status": "active", "history": []})
        bleak["completed_barrow"] = True
        items = list(bleak.get("barrow_items") or [])
        for it in (ITEM_DRAGONSTONE, ITEM_GOLDEN_CLAW):
            if it not in items:
                items.append(it)
        bleak["barrow_items"] = items
        update_bleak_falls_stage(run, stats, "back_on_surface")
        sync_run_to_stats(run, stats)
        if save_manager is not None and stats is not None:
            save_manager.save_stats(run.user_id, stats)
        populate_res = map_engine.advance_to_next_floor(run)
        return f"{_t('barrow_exit.exit_ok')}\n\n{populate_res}"

    from ...renderer import GameRenderer
    return GameRenderer.render_game(run)


def build_bleak_npc_dialog(save_manager, run: GameRun, room: RoomState, npc_id: str) -> Optional[dict[str, Any]]:
    stats = save_manager.load_stats(run.user_id) if save_manager is not None else None
    if npc_id == NPC_FARENGAR_ROOM:
        return {
            "npc_id": NPC_FARENGAR_ROOM,
            "name": get_locale_text("i18n_bleak_falls.npcs.farengar_court_mage.name"),
            "greeting": _t("farengar.farengar_talk_prompt"),
            "options": [
                {"action": "farengar_hint", "text": _t("farengar.farengar_opt_hint")},
                {"action": "farengar_bomb", "text": _t("farengar.farengar_opt_give_bomb")},
                {"action": "leave", "text": _t("farengar.farengar_opt_leave")},
            ],
        }
    if npc_id == NPC_ARVEL_TRAPPED:
        return {
            "npc_id": NPC_ARVEL_TRAPPED,
            "name": get_locale_text("i18n_bleak_falls.npcs.arvel_trapped.name"),
            "greeting": _t("arvel.intro"),
            "options": [
                {"action": "arvel_fight", "text": _t("arvel.opt_demand")},
                {"action": "arvel_fight", "text": _t("arvel.opt_cut")},
                {"action": "leave", "text": _t("arvel.opt_leave")},
            ],
        }
    if npc_id in (NPC_MAP_SURVEYOR, NPC_BRAZIER_KEEPER):
        qid = QUEST_ANCIENT_CARTOGRAPHER if npc_id == NPC_MAP_SURVEYOR else QUEST_RUNIC_ECHOES
        prefix = "map_surveyor" if npc_id == NPC_MAP_SURVEYOR else "brazier_keeper"
        qstore = (run.map_data or {}).get("map_quests") or {}
        qentry = qstore.get(qid)
        if qentry is None and qid == QUEST_ANCIENT_CARTOGRAPHER and stats is not None:
            qentry = ((stats.town_flags or {}).get("multi_run_quests") or {}).get(qid)
        opts = []
        if not qentry:
            opts.append({"action": f"accept_{qid}", "text": _t(f"npcs.{prefix}.opt_accept")})
        elif qentry.get("status") == "active" and int(qentry.get("progress", 0)) >= int(qentry.get("target", 1)):
            opts.append({"action": f"claim_{qid}", "text": _t(f"npcs.{prefix}.opt_claim")})
        else:
            opts.append({"action": f"status_{qid}", "text": _t(f"npcs.{prefix}.opt_claim")})
        opts.append({"action": "leave", "text": _t(f"npcs.{prefix}.opt_leave")})
        return {
            "npc_id": npc_id,
            "name": get_locale_text(f"i18n_bleak_falls.npcs.{prefix}.name"),
            "greeting": _t(f"npcs.{prefix}.greet"),
            "options": opts,
        }
    return None


def apply_bleak_falls_encounter(battle_engine, run: GameRun, room: RoomState) -> bool:
    names = room.shared_payload.get("encounter")
    if not names:
        return False
    from ...data.enemy_data import ENEMY_CONFIG
    built = []
    for ename in names:
        cfg = ENEMY_CONFIG.get(ename, {})
        hp_val = int(str(cfg.get("hp", "24")).split()[0])
        act_str = str(cfg.get("actions", "1A 1BA"))
        act_a = 2 if "2A" in act_str else 1
        act_ba = 1 if "1BA" in act_str else (2 if "2BA" in act_str else 0)
        built.append(battle_engine._build_enemy_state(ename, hp_val, act_a, act_ba))
    if not built:
        return False
    from ..battle.party_battle import assign_enemy_targets, scale_party_enemies
    run.enemies = built
    scale_party_enemies(run)
    room.shared_payload["bleak_falls_combat_tag"] = room.room_type
    run.node_data["bleak_falls_combat_tag"] = room.room_type
    run.node_data["bleak_falls_room_coord"] = room.coord
    if room.shared_payload.get("boss_name"):
        run.node_data["boss_name"] = room.shared_payload["boss_name"]
    if room.shared_payload.get("elite_name"):
        run.node_data["elite_name"] = room.shared_payload["elite_name"]
    battle_engine.enemy_controller.roll_enemy_intent(run)
    assign_enemy_targets(run)
    return True


def _start_arvel_combat(map_engine, run: GameRun, room: RoomState) -> str:
    from ...renderer import GameRenderer
    fm = run.floor_map
    old_sid = fm.player_session_map.get(run.user_id, "") if fm is not None else ""
    if old_sid and fm is not None and old_sid in fm.active_sessions:
        SessionContextScoper.close_session(run, old_sid, mark_cleared=False)
    if room.shared_payload.get("arvel_done") or NPC_ARVEL_TRAPPED not in room.npcs:
        if map_engine.save_manager is not None:
            map_engine.save_manager.save_save(run.user_id, run)
        return GameRenderer.render_game(run)
    if fm is not None:
        existing_sid = map_engine.grid_map_service._find_session_at(fm, room.coord, "battle")
        if existing_sid:
            return map_engine.grid_map_service._join_battle_session(run, run.user_id, room.coord, existing_sid)
    battle_engine = map_engine.battle_engine
    arvel_name = get_locale_text("i18n_room_interact.npcs.arvel_trapped.enemy_name")
    from ...data.enemy_data import ENEMY_CONFIG
    from ..battle.party_battle import assign_enemy_targets
    cfg = ENEMY_CONFIG.get(arvel_name, {})
    hp_val = int(str(cfg.get("hp", "30")).split()[0])
    enemy = battle_engine._build_enemy_state(arvel_name, hp_val, 1, 1)
    room.shared_payload["bleak_falls_combat_tag"] = "arvel"
    SessionContextScoper.create_session(
        run,
        room.coord,
        "battle",
        [run.user_id],
        node_data={
            "difficulty": "normal",
            "battle_mode": BATTLE_MODE_SOLO,
            "bleak_falls_combat_tag": "arvel",
            "bleak_falls_room_coord": room.coord,
        },
    )
    battle_engine._init_battle_node(run, "normal")
    run.enemies = [enemy]
    battle_engine.enemy_controller.roll_enemy_intent(run)
    assign_enemy_targets(run)
    if map_engine.save_manager is not None:
        map_engine.save_manager.save_save(run.user_id, run)
    return f"{_t('arvel.fight_start')}\n\n{GameRenderer.render_game(run)}"


def handle_bleak_npc_choice(map_engine, run: GameRun, dialog: dict[str, Any], opt: dict[str, Any]) -> str:
    res = _handle_bleak_npc_choice_inner(map_engine, run, dialog, opt)
    if map_engine.save_manager is not None:
        map_engine.save_manager.save_save(run.user_id, run)
    return res


def _handle_bleak_npc_choice_inner(map_engine, run: GameRun, dialog: dict[str, Any], opt: dict[str, Any]) -> str:
    save_mgr = map_engine.save_manager
    stats = save_mgr.load_stats(run.user_id) if save_mgr is not None else None
    fm = run.floor_map
    coord = fm.player_coords.get(run.user_id) if fm else None
    room = fm.rooms.get(coord) if (fm and coord) else None
    action = opt.get("action", "leave")
    if action == "arvel_fight" and room is not None:
        return _start_arvel_combat(map_engine, run, room)
    sid = fm.player_session_map.get(run.user_id, "") if fm is not None else ""
    if sid and fm is not None and sid in fm.active_sessions:
        SessionContextScoper.close_session(run, sid, mark_cleared=False)
    else:
        run.node_type = "grid_map"
    run.node_data.pop("room_dialog", None)

    if action == "leave" or room is None:
        from ...renderer import GameRenderer
        return GameRenderer.render_game(run)

    if action == "farengar_hint":
        return _t("farengar.farengar_hint_reply")
    if action == "farengar_bomb":
        qentry = (run.map_data or {}).get("map_quests", {}).get(QUEST_BLEAK_FALLS, {})
        if qentry.get("stage") not in ("", "need_bomb", None):
            return _t("farengar.farengar_bomb_after_breach")
        if _player_has_item_anywhere(run, room, ITEM_QGP_BOMB):
            return _t("farengar.farengar_bomb_already")
        give_item_or_drop(run, room, ITEM_QGP_BOMB)
        return _t("farengar.farengar_bomb_given")
    if action == "arvel_fight":
        return _start_arvel_combat(map_engine, run, room)
    if action.startswith("accept_"):
        qid = action[len("accept_"):]
        cfg = RANDOM_QUEST_CONFIG[qid]
        accept_random_quest(run, stats, qid)
        if save_mgr is not None and stats is not None:
            save_mgr.save_stats(run.user_id, stats)
        prefix = "map_surveyor" if qid == QUEST_ANCIENT_CARTOGRAPHER else "brazier_keeper"
        return _t(f"npcs.{prefix}.accepted", target=cfg["target"])
    if action.startswith("claim_") or action.startswith("status_"):
        qid = action.split("_", 1)[1]
        prefix = "map_surveyor" if qid == QUEST_ANCIENT_CARTOGRAPHER else "brazier_keeper"
        qentry = (run.map_data or {}).get("map_quests", {}).get(qid, {})
        prog = int(qentry.get("progress", 0))
        targ = int(qentry.get("target", RANDOM_QUEST_CONFIG[qid]["target"]))
        if prog < targ:
            return _t(f"npcs.{prefix}.progress", progress=prog, target=targ)
        msg = complete_random_quest(run, stats, qid)
        if save_mgr is not None and stats is not None:
            save_mgr.save_stats(run.user_id, stats)
        return msg

    from ...renderer import GameRenderer
    return GameRenderer.render_game(run)


def on_bleak_combat_resolved(run: GameRun, room: RoomState, save_manager=None) -> Optional[str]:
    fm = getattr(run, "floor_map", None)
    if fm is None or not fm.floor_flags.get("bleak_falls_zone"):
        return None
    stats = save_manager.load_stats(run.user_id) if save_manager is not None else None
    combat_tag = room.shared_payload.pop("bleak_falls_combat_tag", "") or run.node_data.pop("bleak_falls_combat_tag", "")
    run.node_data.pop("bleak_falls_room_coord", None)
    if combat_tag == "arvel":
        if NPC_ARVEL_TRAPPED in room.npcs:
            room.npcs.remove(NPC_ARVEL_TRAPPED)
        room.shared_payload["arvel_done"] = True
        room.cleared = True
        give_item_or_drop(run, room, ITEM_GOLDEN_CLAW)
        give_item_or_drop(run, room, ITEM_ARVEL_JOURNAL)
        update_bleak_falls_stage(run, stats, "got_claw")
        if save_manager is not None and stats is not None:
            save_manager.save_stats(run.user_id, stats)
        msg = _t("arvel.defeated_claw")
        _push_post_notice(run, msg)
        return msg
    if fm.floor_index == BLEAK_FALLS_FLOOR_INDEX and room.shared_payload.get("arvel_pending") and not room.shared_payload.get("arvel_done"):
        room.shared_payload["arvel_pending"] = False
        if NPC_ARVEL_TRAPPED not in room.npcs:
            room.npcs.append(NPC_ARVEL_TRAPPED)
        msg = _t("arvel.title")
        _push_post_notice(run, msg)
        return msg
    if abs(fm.floor_index - BLEAK_SANCTUARY_FLOOR_INDEX) < 1e-4 and room.room_type == "boss":
        room.room_type = ROOM_BARROW_EXIT
        room.landmark_id = ROOM_BARROW_EXIT
        room.cleared = False
        room.explored = True
        gold = BLEAK_FALLS_REWARDS["dragonstone_gold"]
        run.player.gold += gold
        in_bag, _ = give_item_or_drop(run, room, ITEM_DRAGONSTONE)
        bleak = run.map_data.setdefault("map_quests", {}).setdefault(QUEST_BLEAK_FALLS, {"kind": "multi", "status": "active", "history": []})
        bleak["completed_barrow"] = True
        items = list(bleak.get("barrow_items") or [])
        for it in (ITEM_DRAGONSTONE, ITEM_GOLDEN_CLAW):
            if it not in items:
                items.append(it)
        bleak["barrow_items"] = items
        update_bleak_falls_stage(run, stats, "dragonstone_taken")
        if save_manager is not None and stats is not None:
            save_manager.save_stats(run.user_id, stats)
        msg = _t("barrow_exit.dragonstone_loot", gold=gold) if in_bag else _t("barrow_exit.dragonstone_loot_full")
        _push_post_notice(run, msg)
        return msg
    return None
