import random
from typing import Optional

from ...data.battle.battle_mode_config import BATTLE_MODE_FORCED_SOLO
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.content.chireiden_data import (
    CHIREIDEN_BIG_ROOM_PLANS,
    CHIREIDEN_CARD_POOL,
    CHIREIDEN_EXIT_COORD,
    CHIREIDEN_FLOOR_INDEX,
    CHIREIDEN_FORCED_TRIGGER_CONFIGS,
    CHIREIDEN_ITEMS,
    CHIREIDEN_LOCKED_COORDS,
    CHIREIDEN_MAP_HEIGHT,
    CHIREIDEN_MAP_WIDTH,
    CHIREIDEN_PORTAL_BOSS_COORD,
    CHIREIDEN_PROPS,
    CHIREIDEN_RIN_ELITE_COORD,
    CHIREIDEN_SPECIAL_ROOMS,
    CHIREIDEN_STAGE_MIN,
    CHIREIDEN_START_COORD,
    CHIREIDEN_UTSUHO_BOSS_COORD,
    CHIREIDEN_WALL_COORDS,
)
from ...data.enemies.enemy_data import ENEMY_CONFIG
from ...data.enemies.enemy_data_chireiden import (
    CHIREIDEN_ELITE_ENCOUNTER,
    CHIREIDEN_HIGH_DANGER_ENCOUNTERS,
    CHIREIDEN_NORMAL_ENCOUNTERS,
    CHIREIDEN_PORTAL_ENCOUNTER,
    CHIREIDEN_UTSUHO_ENCOUNTER,
)
from ...data.world.grid_map_config import FLOOR_CONFIGS
from ...data.text.locale_data import get_locale_raw, get_locale_text
from ...models.state import FloorMapState, GameRun, RoomState
from ..inventory.bag_service import add_bag_item, get_item_display_name
from ..inventory.deck_service import DeckService
from ..inventory.relic_service import grant_relic
from ..party.coordinator import add_notice
from ..progress.achievement_service import AchievementService, record_run_achievement_stat
from .grid_map_generator import coord_to_xy, xy_to_coord
from .rooms.big_room import add_effective_item, create_big_room_instance
from .rooms.forced_triggers import register_forced_trigger
from .rooms.interact import register_prop_handler


def _reveal_coords(fm: FloorMapState, coords: list[str]):
    for coord in coords:
        if coord in fm.rooms and coord not in fm.revealed_coords:
            fm.revealed_coords.append(coord)


def _reveal_special_targets(fm: FloorMapState) -> list[str]:
    found: list[str] = []
    for coord, room in fm.rooms.items():
        if room.room_type in ("landmark", "elite", "boss", "downstairs", "big_room", "treasure"):
            if coord not in fm.revealed_coords:
                fm.revealed_coords.append(coord)
                found.append(coord)
    return found


def generate_chireiden_floor(run: GameRun, floor_index: float = CHIREIDEN_FLOOR_INDEX) -> FloorMapState:
    rooms: dict[str, RoomState] = {}
    wall_set = set(CHIREIDEN_WALL_COORDS)
    for y in range(CHIREIDEN_MAP_HEIGHT):
        for x in range(CHIREIDEN_MAP_WIDTH):
            coord = xy_to_coord(x, y)
            if coord in wall_set:
                rooms[coord] = RoomState(coord=coord, room_type="wall", explored=False, cleared=True)
                continue
            spec = CHIREIDEN_SPECIAL_ROOMS.get(coord)
            if spec is None:
                rooms[coord] = RoomState(coord=coord, room_type="empty", env_id="chireiden_turbine_corridor")
                continue
            payload = {}
            for key in ("encounter", "boss_name", "elite_name", "chireiden_stage", "reward_relic", "forced_triggers"):
                if key in spec:
                    val = spec[key]
                    payload[key] = list(val) if isinstance(val, list) else val
            rooms[coord] = RoomState(
                coord=coord,
                room_type=spec["room_type"],
                explored=(coord == CHIREIDEN_START_COORD),
                cleared=(spec["room_type"] == "spawn"),
                locked=(coord in CHIREIDEN_LOCKED_COORDS),
                is_high_danger=(spec["room_type"] == "high_danger"),
                landmark_id=str(spec.get("landmark_id", "")),
                shared_payload=payload,
                env_id=str(spec.get("env", "chireiden_turbine_corridor")),
                items=list(spec.get("items", []) or []),
                props=list(spec.get("props", []) or []),
            )

    revealed = [CHIREIDEN_START_COORD]
    sx, sy = coord_to_xy(CHIREIDEN_START_COORD)
    for nx, ny in ((sx, sy - 1), (sx, sy + 1), (sx - 1, sy), (sx + 1, sy)):
        if 0 <= nx < CHIREIDEN_MAP_WIDTH and 0 <= ny < CHIREIDEN_MAP_HEIGHT:
            nb = xy_to_coord(nx, ny)
            if nb not in revealed:
                revealed.append(nb)

    player_coords = {uid: CHIREIDEN_START_COORD for uid in run.human_uids()}
    fm = FloorMapState(
        floor_index=floor_index,
        width=CHIREIDEN_MAP_WIDTH,
        height=CHIREIDEN_MAP_HEIGHT,
        rooms=rooms,
        player_coords=player_coords,
        revealed_coords=revealed,
        boss_coord=CHIREIDEN_PORTAL_BOSS_COORD,
        floor_flags={
            "chireiden_zone": True,
            "chireiden_utsuho_defeated": False,
            "chireiden_portal_defeated": False,
        },
    )

    rng = random.Random(35035)
    for plan in CHIREIDEN_BIG_ROOM_PLANS:
        br = create_big_room_instance(fm, plan["group_id"], plan["template_id"], list(plan["cells"]), rng=rng)
        br.shared_payload["icon"] = plan["icon"]
        if any(c in CHIREIDEN_LOCKED_COORDS for c in plan["cells"]):
            for c in plan["cells"]:
                fm.rooms[c].locked = True

    return fm


def enter_chireiden_elevator(map_engine, run: GameRun, actor_uid: str) -> str:
    cfg = FLOOR_CONFIGS[CHIREIDEN_FLOOR_INDEX]
    fm = generate_chireiden_floor(run, CHIREIDEN_FLOOR_INDEX)
    run.floor_map = fm
    msg = map_engine._finalize_next_floor(run, actor_uid, cfg, yog_quest=False)
    for uid in run.human_uids():
        pl = run.players.get(uid)
        if pl is not None:
            pl.stage = CHIREIDEN_STAGE_MIN
    sm = getattr(map_engine, "save_manager", None)
    record_run_achievement_stat(sm, run, "chireiden_visits", 1)
    banner = get_locale_text("i18n_chireiden.elevator.entered_banner")
    intro = get_locale_text("i18n_chireiden.gate.floor_intro")
    return f"{banner}\n{intro}\n{msg}"


def check_move_blocked_by_chireiden_gate(fm: Optional[FloorMapState], cur_coord: str, target_coord: str) -> Optional[str]:
    if fm is None or not fm.floor_flags.get("chireiden_zone"):
        return None
    if target_coord not in CHIREIDEN_LOCKED_COORDS:
        return None
    if not fm.floor_flags.get("chireiden_utsuho_defeated"):
        return get_locale_text("i18n_chireiden.gate.utsuho_blocked")
    if target_coord == CHIREIDEN_EXIT_COORD and not fm.floor_flags.get("chireiden_portal_defeated"):
        return get_locale_text("i18n_yog_quest.room_locked")
    return None


def _build_enemies(battle_engine, names: list[str]) -> list:
    built = []
    for ename in names:
        cfg = ENEMY_CONFIG.get(ename, {})
        hp_val = int(str(cfg.get("hp", "60")).split()[0])
        act_str = str(cfg.get("actions", "1A 1BA"))
        act_a = 3 if "3A" in act_str else (2 if "2A" in act_str else 1)
        act_ba = 2 if "2BA" in act_str else (1 if "1BA" in act_str else 0)
        built.append(battle_engine._build_enemy_state(ename, hp_val, act_a, act_ba))
    return built


def apply_chireiden_encounter(battle_engine, run: GameRun, room: RoomState) -> bool:
    names = list(room.shared_payload.get("encounter") or [])
    if not names:
        if room.coord == CHIREIDEN_PORTAL_BOSS_COORD:
            names = list(CHIREIDEN_PORTAL_ENCOUNTER)
        elif room.coord == CHIREIDEN_UTSUHO_BOSS_COORD:
            names = list(CHIREIDEN_UTSUHO_ENCOUNTER)
        elif room.coord == CHIREIDEN_RIN_ELITE_COORD or room.room_type == "elite":
            names = list(CHIREIDEN_ELITE_ENCOUNTER)
        elif room.room_type == "high_danger":
            names = list(random.choice(CHIREIDEN_HIGH_DANGER_ENCOUNTERS))
        elif room.room_type == "boss":
            names = list(CHIREIDEN_UTSUHO_ENCOUNTER)
        else:
            names = list(random.choice(CHIREIDEN_NORMAL_ENCOUNTERS))
    built = _build_enemies(battle_engine, names)
    if not built:
        return False

    run.enemies = built
    room.shared_payload["chireiden_combat_tag"] = room.room_type
    run.node_data["chireiden_combat_tag"] = room.room_type
    run.node_data["chireiden_room_coord"] = room.coord
    if room.shared_payload.get("boss_name"):
        run.node_data["boss_name"] = room.shared_payload["boss_name"]
    if room.shared_payload.get("elite_name"):
        run.node_data["elite_name"] = room.shared_payload["elite_name"]

    fm = getattr(run, "floor_map", None)
    if fm is not None:
        overcharge = int(fm.floor_flags.pop("chireiden_next_overcharge", 0) or 0)
        pre_shield = int(fm.floor_flags.pop("chireiden_next_shield", 0) or 0)
        if overcharge > 0:
            bcfg = BUFF_CONFIG["fusion_overcharge"]
            for uid in run.party_order:
                pl = run.players.get(uid)
                if pl is not None and pl.hp > 0:
                    battle_engine._add_buff_to(pl, "fusion_overcharge", bcfg["name"], bcfg["desc"], overcharge)
        if pre_shield > 0:
            battle_engine._gain_shield(run, "p0", pre_shield)

    from ...entities.enemies import get_enemy_template

    for enemy in list(run.enemies):
        tpl = get_enemy_template(enemy.name)
        if hasattr(tpl, "on_battle_start"):
            tpl.on_battle_start(run, enemy, battle_engine)
    battle_engine.enemy_controller.roll_enemy_intent(run)
    return True


def cleanup_utsuho_ally(run: GameRun):
    merc_uid = "merc_utsuho"
    changed = False
    if merc_uid in run.players:
        run.players.pop(merc_uid, None)
        changed = True
    if merc_uid in run.party_order:
        run.party_order = [u for u in run.party_order if u != merc_uid]
        changed = True
    full_order = getattr(run, "_full_party_order", None)
    if isinstance(full_order, list) and merc_uid in full_order:
        setattr(run, "_full_party_order", [u for u in full_order if u != merc_uid])
        changed = True
    fm = getattr(run, "floor_map", None)
    if fm is not None and isinstance(getattr(fm, "player_session_map", None), dict):
        fm.player_session_map.pop(merc_uid, None)
    return changed


def on_chireiden_combat_resolved(run: GameRun, room: RoomState, save_manager=None):
    cleanup_utsuho_ally(run)
    room.shared_payload.pop("chireiden_combat_tag", None)
    fm = getattr(run, "floor_map", None)
    if fm is None or not fm.floor_flags.get("chireiden_zone"):
        return

    reward_relic = room.shared_payload.get("reward_relic", "")
    if reward_relic and not room.shared_payload.get("reward_relic_granted"):
        for uid in run.human_uids():
            pl = run.players.get(uid)
            if pl is not None:
                grant_relic(pl, reward_relic)
        room.shared_payload["reward_relic_granted"] = True

    if save_manager is not None and room.coord == CHIREIDEN_RIN_ELITE_COORD:
        ach = AchievementService(save_manager)
        for msg_uid in run.human_uids():
            ach.record_stat(msg_uid, "chireiden_rin_kills", 1, mode="add", run=run)

    if room.coord == CHIREIDEN_UTSUHO_BOSS_COORD and not fm.floor_flags.get("chireiden_utsuho_defeated"):
        fm.floor_flags["chireiden_utsuho_defeated"] = True
        unlocked = []
        for coord in CHIREIDEN_LOCKED_COORDS:
            if coord == CHIREIDEN_EXIT_COORD:
                continue
            target_room = fm.rooms.get(coord)
            if target_room is not None:
                target_room.locked = False
                unlocked.append(coord)
        _reveal_coords(fm, ["B16", "C16", "D16", CHIREIDEN_PORTAL_BOSS_COORD])
        DeckService.add_card_to_deck(run.player, random.choice(CHIREIDEN_CARD_POOL))
        unlock_msg = get_locale_text("i18n_chireiden.gate.utsuho_defeated_unlock")
        if save_manager is not None:
            ach = AchievementService(save_manager)
            for msg_uid in run.human_uids():
                ach.record_stat(msg_uid, "chireiden_utsuho_kills", 1, mode="add", run=run)
        for msg_uid in run.human_uids():
            add_notice(run, msg_uid, unlock_msg)
    elif room.coord == CHIREIDEN_PORTAL_BOSS_COORD and not fm.floor_flags.get("chireiden_portal_defeated"):
        fm.floor_flags["chireiden_portal_defeated"] = True
        exit_room = fm.rooms.get(CHIREIDEN_EXIT_COORD)
        if exit_room is not None:
            exit_room.locked = False
            exit_room.room_type = "downstairs"
        _reveal_coords(fm, [CHIREIDEN_EXIT_COORD])
        DeckService.add_card_to_deck(run.player, "hisoutensoku_thermonuclear_cannon")
        portal_msg = get_locale_text("i18n_chireiden.gate.portal_defeated_unlock", coord=CHIREIDEN_EXIT_COORD)
        if save_manager is not None:
            from ...data.content.ultimate_prism_data import CHIREIDEN_QUEST_COMPLETED_FLAG
            ach = AchievementService(save_manager)
            for msg_uid in run.human_uids():
                ach.record_stat(msg_uid, "chireiden_portal_kills", 1, mode="add", run=run)
                st = save_manager.load_stats(msg_uid)
                st.town_flags[CHIREIDEN_QUEST_COMPLETED_FLAG] = True
                save_manager.save_stats(msg_uid, st)
        for msg_uid in run.human_uids():
            add_notice(run, msg_uid, portal_msg)

    if save_manager is not None:
        save_manager.save_save(run.user_id, run)


def build_chireiden_landmark_options(run: GameRun, lm_id: str, coord: str) -> Optional[dict]:
    if lm_id not in ("chireiden_fusion_terminal", "chireiden_penning_stabilizer"):
        return None
    fm = run.floor_map
    if fm is None:
        return None
    title = get_locale_text(f"i18n_chireiden.landmarks.{lm_id}.name")
    desc = get_locale_text(f"i18n_chireiden.landmarks.{lm_id}.desc")
    options = []
    used_key = f"chireiden_lm_used_{lm_id}"
    if not fm.floor_flags.get(used_key):
        if lm_id == "chireiden_fusion_terminal":
            options.extend([
                {"action": "chireiden_term_he3", "text": get_locale_text("i18n_chireiden.landmarks.chireiden_fusion_terminal.opt_draw_he3")},
                {"action": "chireiden_term_coolant", "text": get_locale_text("i18n_chireiden.landmarks.chireiden_fusion_terminal.opt_sync_coolant")},
                {"action": "chireiden_term_overclock", "text": get_locale_text("i18n_chireiden.landmarks.chireiden_fusion_terminal.opt_overclock")},
            ])
        else:
            options.extend([
                {"action": "chireiden_well_calibrate", "text": get_locale_text("i18n_chireiden.landmarks.chireiden_penning_stabilizer.opt_calibrate_well")},
                {"action": "chireiden_well_purge", "text": get_locale_text("i18n_chireiden.landmarks.chireiden_penning_stabilizer.opt_purge_xen")},
                {"action": "chireiden_well_shard", "text": get_locale_text("i18n_chireiden.landmarks.chireiden_penning_stabilizer.opt_resonance_shield")},
            ])
    options.append({"action": "landmark_leave", "text": get_locale_text("i18n_grid_map.opt_leave")})
    return {"title": title, "desc": desc, "landmark_id": lm_id, "coord": coord, "options": options}


def execute_chireiden_landmark_option(save_manager, map_engine, run: GameRun, action: str) -> Optional[str]:
    if not action.startswith("chireiden_"):
        return None
    fm = run.floor_map
    if fm is None:
        return None
    p = run.player
    uid = run.user_id

    if action.startswith("chireiden_term_"):
        used_key = "chireiden_lm_used_chireiden_fusion_terminal"
        if fm.floor_flags.get(used_key):
            return get_locale_text("i18n_chireiden.landmarks.chireiden_fusion_terminal.already_used")
        if action == "chireiden_term_he3":
            fm.floor_flags[used_key] = True
            ok, _ = add_bag_item(p, "he3_fuel_canister")
            if not ok:
                room = fm.rooms.get(fm.player_coords.get(uid, ""))
                if room is not None:
                    add_effective_item(fm, room, "he3_fuel_canister")
            fm.floor_flags["chireiden_next_shield"] = int(fm.floor_flags.get("chireiden_next_shield", 0) or 0) + 6
            msg = get_locale_text(
                "i18n_chireiden.landmarks.chireiden_fusion_terminal.draw_he3_msg",
                item=get_item_display_name("he3_fuel_canister"),
            )
        elif action == "chireiden_term_coolant":
            fm.floor_flags[used_key] = True
            healed = min(p.max_hp - p.hp, 24)
            p.hp += healed
            DeckService.add_card_to_deck(p, "pb_bi_coolant_loop")
            msg = get_locale_text("i18n_chireiden.landmarks.chireiden_fusion_terminal.sync_coolant_msg", healed=healed)
        else:
            cost = 120
            if p.gold < cost:
                return get_locale_text("i18n_chireiden.landmarks.chireiden_fusion_terminal.not_enough_gold", cost=cost)
            p.gold -= cost
            fm.floor_flags[used_key] = True
            fm.floor_flags["chireiden_next_overcharge"] = int(fm.floor_flags.get("chireiden_next_overcharge", 0) or 0) + 4
            p.max_hp += 6
            p.hp = min(p.max_hp, p.hp + 6)
            msg = get_locale_text("i18n_chireiden.landmarks.chireiden_fusion_terminal.overclock_msg", cost=cost)
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        return msg

    used_key = "chireiden_lm_used_chireiden_penning_stabilizer"
    if fm.floor_flags.get(used_key):
        return get_locale_text("i18n_chireiden.landmarks.chireiden_penning_stabilizer.already_used")
    if action == "chireiden_well_calibrate":
        if int(getattr(p, "sp", 0) or 0) < 1:
            return get_locale_text("i18n_chireiden.landmarks.chireiden_penning_stabilizer.no_sp")
        p.sp -= 1
        fm.floor_flags[used_key] = True
        _reveal_coords(fm, [CHIREIDEN_UTSUHO_BOSS_COORD, CHIREIDEN_PORTAL_BOSS_COORD, CHIREIDEN_EXIT_COORD])
        from .persistent_buffs import add_persistent_buff
        add_persistent_buff(p, "ancient_ward", 1)
        msg = get_locale_text("i18n_chireiden.landmarks.chireiden_penning_stabilizer.calibrate_msg", coord=CHIREIDEN_PORTAL_BOSS_COORD)
    elif action == "chireiden_well_purge":
        fm.floor_flags[used_key] = True
        healed = min(p.max_hp - p.hp, 18)
        p.hp += healed
        _reveal_special_targets(fm)
        msg = get_locale_text("i18n_chireiden.landmarks.chireiden_penning_stabilizer.purge_msg", healed=healed)
    else:
        fm.floor_flags[used_key] = True
        gold = 90
        p.gold += gold
        msg = get_locale_text("i18n_chireiden.landmarks.chireiden_penning_stabilizer.resonance_msg", gold=gold)
    map_engine.complete_session(run, mark_cleared=True)
    record_run_achievement_stat(save_manager, run, "chireiden_facilities_used", 1)
    save_manager.save_save(uid, run)
    return msg


def build_rin_npc_dialog(save_manager, run: GameRun, room: RoomState, nid: str) -> Optional[dict]:
    if nid != "kaenbyou_rin":
        return None
    greetings = get_locale_raw("i18n_chireiden.npcs.kaenbyou_rin.greetings", [])
    greeting = random.choice(greetings) if isinstance(greetings, list) and greetings else get_locale_text("i18n_room_interact.npcs.kaenbyou_rin.desc")
    options = []
    if not room.shared_payload.get("rin_gifted"):
        options.append({"id": "study_lbe", "text": get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.opt_study_lbe")})
    if not room.shared_payload.get("rin_coolant_traded"):
        options.append({"id": "trade_coolant", "text": get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.opt_trade_coolant")})
    options.append({"id": "challenge_rin", "text": get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.opt_challenge_rin")})
    options.append({"id": "leave", "text": get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.opt_leave")})
    return {
        "npc_id": nid,
        "name": get_locale_text("i18n_room_interact.npcs.kaenbyou_rin.name"),
        "greeting": greeting,
        "options": options,
    }


def start_rin_elite_battle(map_engine, run: GameRun, room: RoomState) -> str:
    from .rooms.interact import get_current_room

    _, coord = get_current_room(run)
    map_engine.complete_session(run, mark_cleared=False)
    room.shared_payload["encounter"] = list(CHIREIDEN_ELITE_ENCOUNTER)
    room.shared_payload["elite_name"] = CHIREIDEN_ELITE_ENCOUNTER[0]
    room.shared_payload["reward_relic"] = "lbe_fast_reactor_core"
    return map_engine.grid_map_service._launch_battle_session(
        run, run.user_id, coord, room, "elite", battle_mode=BATTLE_MODE_FORCED_SOLO
    )


def handle_rin_npc_choice(map_engine, run: GameRun, dlg: dict, chosen_opt: dict) -> str:
    opt_id = chosen_opt.get("id", "leave")
    p = run.player
    fm = run.floor_map
    if fm is None:
        map_engine.complete_session(run, mark_cleared=False)
        return get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.left")
    coord = fm.player_coords.get(run.user_id, "")
    room = fm.rooms.get(coord)
    if opt_id == "leave":
        map_engine.complete_session(run, mark_cleared=False)
        map_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.left")
    if opt_id == "study_lbe":
        if room is not None:
            room.shared_payload["rin_gifted"] = True
        ok, _ = add_bag_item(p, "lbe_cooling_flask")
        if not ok and room is not None:
            add_effective_item(fm, room, "lbe_cooling_flask")
        map_engine.complete_session(run, mark_cleared=False)
        map_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.study_lbe_res", item=get_item_display_name("lbe_cooling_flask"))
    if opt_id == "trade_coolant":
        if room is not None and room.shared_payload.get("rin_coolant_traded"):
            map_engine.complete_session(run, mark_cleared=False)
            return get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.left")
        cost = 75
        if p.gold < cost:
            return get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.no_gold", cost=cost)
        if room is not None:
            room.shared_payload["rin_coolant_traded"] = True
        p.gold -= cost
        p.max_hp += 6
        healed = min(p.max_hp - p.hp, 30)
        p.hp += healed
        map_engine.complete_session(run, mark_cleared=False)
        map_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.trade_coolant_res", healed=healed)
    if opt_id == "challenge_rin" and room is not None:
        intro = get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.challenge_res")
        battle_view = start_rin_elite_battle(map_engine, run, room)
        return f"{intro}\n\n{battle_view}"
    map_engine.complete_session(run, mark_cleared=False)
    return get_locale_text("i18n_chireiden.npcs.kaenbyou_rin.left")


@register_prop_handler("he3_storage_cylinder")
def _touch_he3_cylinder(run, room, cfg, p, fm, coord):
    gold = int(cfg.get("gold", 48))
    p.gold += gold
    item_id = cfg.get("reward_item", "he3_fuel_canister")
    ok, _ = add_bag_item(p, item_id)
    if not ok:
        add_effective_item(fm, room, item_id)
    return get_locale_text("i18n_chireiden.props.he3_storage_cylinder.done", item=get_item_display_name(item_id), gold=gold)


@register_prop_handler("pb_bi_coolant_valve")
def _touch_pb_bi_valve(run, room, cfg, p, fm, coord):
    healed = min(p.max_hp - p.hp, int(cfg.get("heal", 24)))
    p.hp += healed
    return get_locale_text("i18n_chireiden.props.pb_bi_coolant_valve.done", healed=healed)


@register_prop_handler("tokamak_magnetic_coil")
def _touch_tokamak_coil(run, room, cfg, p, fm, coord):
    gold = int(cfg.get("gold", 65))
    bonus_hp = int(cfg.get("max_hp_bonus", 5))
    p.gold += gold
    p.max_hp += bonus_hp
    p.hp = min(p.max_hp, p.hp + bonus_hp)
    return get_locale_text("i18n_chireiden.props.tokamak_magnetic_coil.done", gold=gold)


@register_prop_handler("penning_harmonic_console")
def _touch_penning_console(run, room, cfg, p, fm, coord):
    gold = int(cfg.get("gold", 55))
    p.gold += gold
    _reveal_special_targets(fm)
    return get_locale_text("i18n_chireiden.props.penning_harmonic_console.done", gold=gold)


@register_forced_trigger("reactor_steam_vent")
def _trigger_reactor_steam_vent(run, fm, room, entry: dict) -> str:
    cfg = CHIREIDEN_FORCED_TRIGGER_CONFIGS["reactor_steam_vent"]
    p = run.player
    dmg = min(int(cfg.get("damage", 8)), max(0, p.hp - 1))
    p.hp = max(1, p.hp - dmg)
    shield_bonus = int(cfg.get("shield_bonus", 16))
    fm.floor_flags["chireiden_next_shield"] = int(fm.floor_flags.get("chireiden_next_shield", 0) or 0) + shield_bonus
    return get_locale_text("i18n_chireiden.triggers.reactor_steam_vent_instant", dmg=dmg, shield=shield_bonus)


@register_forced_trigger("he3_orbital_capsule")
def _trigger_he3_orbital_capsule(run, fm, room, entry: dict) -> str:
    cfg = CHIREIDEN_FORCED_TRIGGER_CONFIGS["he3_orbital_capsule"]
    p = run.player
    gold = int(cfg.get("gold", 45))
    item_id = cfg.get("item", "he3_fuel_canister")
    p.gold += gold
    ok, _ = add_bag_item(p, item_id)
    if not ok:
        add_effective_item(fm, room, item_id)
    return get_locale_text("i18n_chireiden.triggers.he3_orbital_capsule_instant", item=get_item_display_name(item_id), gold=gold)


@register_forced_trigger("penning_harmonic_alarm")
def _trigger_penning_harmonic_alarm(run, fm, room, entry: dict) -> str:
    cfg = CHIREIDEN_FORCED_TRIGGER_CONFIGS["penning_harmonic_alarm"]
    p = run.player
    heal = min(p.max_hp - p.hp, int(cfg.get("heal", 14)))
    p.hp += heal
    gold = int(cfg.get("gold", 40))
    p.gold += gold
    return get_locale_text("i18n_chireiden.triggers.penning_harmonic_alarm_instant", heal=heal, gold=gold)


def try_use_chireiden_item(engine, run: GameRun, item_id: str, cfg: dict, add_bag_fn, reveal_fn) -> Optional[str]:
    if item_id not in CHIREIDEN_ITEMS:
        return None
    p = run.player
    fm = getattr(run, "floor_map", None)
    if item_id == "he3_fuel_canister":
        healed = min(p.max_hp - p.hp, int(cfg.get("heal", 28)))
        p.hp += healed
        if fm is not None:
            fm.floor_flags["chireiden_next_overcharge"] = int(fm.floor_flags.get("chireiden_next_overcharge", 0) or 0) + int(cfg.get("fusion_overcharge", 2))
        return get_locale_text("i18n_chireiden.items.he3_fuel_canister.used", healed=healed)
    if item_id == "lbe_cooling_flask":
        bonus_hp = int(cfg.get("max_hp_bonus", 4))
        p.max_hp += bonus_hp
        healed = min(p.max_hp - p.hp, int(cfg.get("heal", 36)) + bonus_hp)
        p.hp += healed
        return get_locale_text("i18n_chireiden.items.lbe_cooling_flask.used", healed=healed)
    if item_id == "xen_sample_ampoule":
        healed = min(p.max_hp - p.hp, int(cfg.get("heal", 18)))
        p.hp += healed
        if fm is not None:
            _reveal_special_targets(fm)
        return get_locale_text("i18n_chireiden.items.xen_sample_ampoule.used", healed=healed)
    if item_id == "headband_blueprint_shard":
        bonus_hp = int(cfg.get("max_hp_bonus", 8))
        p.max_hp += bonus_hp
        healed = min(p.max_hp - p.hp, int(cfg.get("heal", 20)) + bonus_hp)
        p.hp += healed
        return get_locale_text("i18n_chireiden.items.headband_blueprint_shard.used", healed=healed)
    if item_id == "headband_of_intellect":
        bonus_hp = int(cfg.get("max_hp_bonus", 6))
        p.max_hp += bonus_hp
        healed = min(p.max_hp - p.hp, int(cfg.get("heal", 24)) + bonus_hp)
        p.hp += healed
        if fm is not None:
            fm.floor_flags["chireiden_next_overcharge"] = int(fm.floor_flags.get("chireiden_next_overcharge", 0) or 0) + int(cfg.get("fusion_overcharge", 3))
        return get_locale_text("i18n_chireiden.items.headband_of_intellect.used", healed=healed)
    return None
