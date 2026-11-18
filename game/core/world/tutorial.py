from typing import Any, Optional

from ...data.locale_data import get_locale_text
from ...data.tutorial_data import (
    TUTORIAL_DECK,
    TUTORIAL_ENEMY,
    TUTORIAL_FLOOR_INDEX,
    TUTORIAL_MAP_HEIGHT,
    TUTORIAL_MAP_WIDTH,
    TUTORIAL_REWARD_CARDS,
    TUTORIAL_REWARD_GOLD,
    TUTORIAL_REWARD_POTION,
    TUTORIAL_ROOMS,
    TUTORIAL_START_COORD,
    TUTORIAL_STARTING_GOLD,
    TUTORIAL_STARTING_HP,
    TUTORIAL_STARTING_MAX_HP,
    TUTORIAL_STARTING_SP,
)
from ...models.state import CardState, EnemyState, FloorMapState, GameRun, PlayerState, RoomState
from ..party.coordinator import add_notice
from ..party.session import SessionContextScoper
from .grid_map_generator import coord_to_xy, xy_to_coord
from .rooms.forced_triggers import register_forced_trigger
from .sp_system import restore_sp


def is_tutorial_run(run: Optional[GameRun]) -> bool:
    if run is None:
        return False
    fm = getattr(run, "floor_map", None)
    if fm is not None and bool((fm.floor_flags or {}).get("tutorial_zone")):
        return True
    return bool((getattr(run, "node_data", None) or {}).get("tutorial_zone"))


def generate_tutorial_floor(run: GameRun) -> FloorMapState:
    rooms: dict[str, RoomState] = {}
    for y in range(TUTORIAL_MAP_HEIGHT):
        for x in range(TUTORIAL_MAP_WIDTH):
            coord = xy_to_coord(x, y)
            spec = TUTORIAL_ROOMS.get(coord)
            if spec is None:
                rooms[coord] = RoomState(coord=coord, room_type="wall", explored=False, cleared=True)
                continue
            payload: dict[str, Any] = {}
            if spec.get("name_key"):
                payload["name_key"] = spec["name_key"]
            if spec.get("encounter"):
                payload["tutorial_encounter"] = spec["encounter"]
            if spec.get("forced_triggers"):
                payload["forced_triggers"] = [dict(entry) for entry in spec["forced_triggers"]]
            rooms[coord] = RoomState(
                coord=coord,
                room_type=spec["room_type"],
                explored=(coord == TUTORIAL_START_COORD),
                cleared=(spec["room_type"] == "spawn"),
                obstacle_sp=int(spec.get("obstacle_sp", 0) or 0),
                obstacle_style=str(spec.get("obstacle_style", "")),
                landmark_id=str(spec.get("landmark_id", "")),
                shared_payload=payload,
                env_id=str(spec.get("env", "dungeon_corridor")),
                npcs=list(spec.get("npcs", []) or []),
                items=list(spec.get("items", []) or []),
                props=list(spec.get("props", []) or []),
            )

    revealed = [TUTORIAL_START_COORD]
    sx, sy = coord_to_xy(TUTORIAL_START_COORD)
    for nx, ny in ((sx, sy - 1), (sx, sy + 1), (sx - 1, sy), (sx + 1, sy)):
        if 0 <= nx < TUTORIAL_MAP_WIDTH and 0 <= ny < TUTORIAL_MAP_HEIGHT:
            nb = xy_to_coord(nx, ny)
            if nb not in revealed:
                revealed.append(nb)

    player_coords = {uid: TUTORIAL_START_COORD for uid in run.human_uids()}
    return FloorMapState(
        floor_index=TUTORIAL_FLOOR_INDEX,
        width=TUTORIAL_MAP_WIDTH,
        height=TUTORIAL_MAP_HEIGHT,
        rooms=rooms,
        revealed_coords=revealed,
        player_coords=player_coords,
        active_sessions={},
        player_session_map={},
        boss_coord="",
        secret_boss_coord="",
        ritual_coord="",
        ritual_protocol="",
        secret_unlocked=False,
        secret_clue_found=False,
        floor_flags={"tutorial_zone": True},
    )


def build_tutorial_player(stats, user_id: str) -> PlayerState:
    return PlayerState(
        hp=TUTORIAL_STARTING_HP,
        max_hp=TUTORIAL_STARTING_MAX_HP,
        shield=0,
        gold=TUTORIAL_STARTING_GOLD,
        stage=1,
        name=getattr(stats, "player_name", get_locale_text("i18n_cli_core.default_player_name")),
        deck=[CardState(id=cid) for cid in TUTORIAL_DECK],
        draw_pile=[],
        discard_pile=[],
        hand=[],
        actions=2,
        bonus_actions=1,
        minions={},
        amulets={},
        abilities=[],
        subclass="",
        selected_class=getattr(stats, "selected_class", "法师"),
        sp=TUTORIAL_STARTING_SP,
        max_sp=TUTORIAL_STARTING_SP,
    )


def start_tutorial_run(
    save_manager,
    engine,
    user_id: str,
    return_to_town: bool = False,
) -> tuple[Optional[GameRun], str]:
    from ...renderer import GameRenderer
    stats = save_manager.load_stats(user_id)
    if getattr(stats, "active_coop_id", "") or getattr(stats, "active_lobby_id", ""):
        return None, get_locale_text("i18n_tutorial.flow.cannot_start_in_coop")
    player = build_tutorial_player(stats, user_id)
    run = GameRun(
        user_id=user_id,
        node_type="grid_map",
        player=player,
        enemies=[],
        node_data={"tutorial_zone": True},
        party_order=[user_id],
        leader_id=user_id,
        players={user_id: player},
    )
    run.floor_map = generate_tutorial_floor(run)
    spawn_room = run.floor_map.rooms.get(TUTORIAL_START_COORD)
    if spawn_room is not None:
        triggers = spawn_room.shared_payload.get("forced_triggers")
        if isinstance(triggers, list):
            for entry in triggers:
                if isinstance(entry, dict) and entry.get("id") == "tutorial_enter_spawn":
                    entry["triggered"] = True
    stats.in_town = False
    stats.town_flags.pop("current_dialog", None)
    stats.town_flags["tutorial_entered"] = True
    stats.town_flags["tutorial_return_to_town"] = bool(return_to_town)
    save_manager.save_stats(user_id, stats)
    save_manager.save_save(user_id, run)
    welcome = get_locale_text("i18n_tutorial.elder.welcome_banner")
    rendered = GameRenderer.render_game(run)
    return run, f"{welcome}\n\n{rendered}"


def finish_tutorial_run(
    save_manager,
    town_engine,
    user_id: str,
    skipped: bool = False,
) -> str:
    from ...renderer import GameRenderer
    stats = save_manager.load_stats(user_id)
    stats.tutorial_done = True
    stats.town_flags.pop("tutorial_pending", None)
    stats.town_flags["tutorial_entered"] = True
    return_to_town = bool(stats.town_flags.pop("tutorial_return_to_town", False))
    save_manager.delete_save(user_id)
    msg_key = "i18n_tutorial.flow.skipped_msg" if skipped else "i18n_tutorial.flow.completed_msg"
    msg = get_locale_text(msg_key)
    if return_to_town:
        stats.in_town = True
        stats.town_pos = "square"
        save_manager.save_stats(user_id, stats)
        if town_engine is not None:
            return f"{msg}\n\n{town_engine.render_current_room(user_id, stats)}"
        return msg
    stats.in_town = False
    save_manager.save_stats(user_id, stats)
    return f"{msg}\n\n{GameRenderer.render_menu(stats)}"


def rescue_tutorial_defeat(save_manager, run: GameRun) -> str:
    from ...renderer import GameRenderer
    uid = run.user_id
    fm = getattr(run, "floor_map", None)
    if fm is not None:
        sid = fm.player_session_map.get(uid, "")
        if sid:
            SessionContextScoper.close_session(run, sid, mark_cleared=False)
        fm.player_coords[uid] = TUTORIAL_START_COORD
    p = run.player
    p.hp = p.max_hp
    p.shield = 0
    p.buffs.clear()
    p.minions.clear()
    p.amulets.clear()
    p.sp = p.max_sp
    p.exhaustion = 0
    run.node_type = "grid_map"
    run.enemies.clear()
    run.node_data = {"tutorial_zone": True}
    save_manager.save_save(uid, run)
    msg = get_locale_text("i18n_tutorial.flow.defeat_rescued")
    return f"{msg}\n\n{GameRenderer.render_game(run)}"


def apply_tutorial_encounter(battle_engine, run: GameRun, room: RoomState) -> None:
    enemy_name = str(TUTORIAL_ENEMY["name"])
    hp = int(TUTORIAL_ENEMY["hp"])
    actions = int(TUTORIAL_ENEMY["actions"])
    bonus_actions = int(TUTORIAL_ENEMY["bonus_actions"])
    enemy = EnemyState(
        name=enemy_name,
        hp=hp,
        max_hp=hp,
        shield=0,
        actions=actions,
        bonus_actions=bonus_actions,
        max_actions=actions,
        max_bonus_actions=bonus_actions,
    )
    run.enemies = [enemy]
    run.node_data["tutorial_zone"] = True
    run.node_data["tutorial_battle"] = True
    battle_engine.enemy_controller.roll_enemy_intent(run)
    from .encounter_lore import record_encounter_for_run
    record_encounter_for_run(battle_engine.save_manager, run, enemy_name)


def build_tutorial_rewards() -> list[dict[str, Any]]:
    return [
        {"type": "gold", "amount": TUTORIAL_REWARD_GOLD, "taken": False},
        {"type": "potion", "potion_id": TUTORIAL_REWARD_POTION, "taken": False},
        {"type": "card_reward", "cards": list(TUTORIAL_REWARD_CARDS), "taken": False, "force": False},
    ]


def notify_tutorial_battle_win(run: GameRun) -> None:
    add_notice(run, run.user_id, get_locale_text("i18n_tutorial.trigger.battle_won_hint"))


def build_tutorial_elder_dialog(run: GameRun) -> dict[str, Any]:
    return {
        "name": get_locale_text("i18n_tutorial.elder.name"),
        "greeting": get_locale_text("i18n_tutorial.elder.dialog_greeting"),
        "options": [
            {"action": "topic_ops", "text": get_locale_text("i18n_tutorial.elder.opt_ops")},
            {"action": "topic_cards", "text": get_locale_text("i18n_tutorial.elder.opt_cards")},
            {"action": "topic_map", "text": get_locale_text("i18n_tutorial.elder.opt_map")},
            {"action": "skip_tutorial", "text": get_locale_text("i18n_tutorial.elder.opt_skip")},
            {"action": "leave", "text": get_locale_text("i18n_tutorial.elder.opt_leave")},
        ],
    }


def _resolve_town_engine(map_engine):
    te = getattr(map_engine, "town_engine", None)
    if te is not None:
        return te
    from .town.engine import TownEngine
    return TownEngine(map_engine.save_manager, getattr(map_engine, "game_engine", None))


def handle_tutorial_elder_choice(map_engine, run: GameRun, chosen_opt: dict[str, Any]) -> str:
    from .rooms.npc_dialog import close_room_dialog, render_room_dialog
    action = str(chosen_opt.get("action") or "")
    if action == "topic_ops":
        return get_locale_text("i18n_tutorial.elder.reply_ops") + "\n\n" + render_room_dialog(run)
    if action == "topic_cards":
        return get_locale_text("i18n_tutorial.elder.reply_cards") + "\n\n" + render_room_dialog(run)
    if action == "topic_map":
        return get_locale_text("i18n_tutorial.elder.reply_map") + "\n\n" + render_room_dialog(run)
    if action == "skip_tutorial":
        run.node_data["tutorial_finished"] = True
        return finish_tutorial_run(
            map_engine.save_manager,
            _resolve_town_engine(map_engine),
            run.user_id,
            skipped=True,
        )
    return close_room_dialog(map_engine.save_manager, run)


def build_tutorial_landmark_data(run: GameRun, lm_id: str, coord: str) -> Optional[dict[str, Any]]:
    if lm_id == "tutorial_shrine":
        return {
            "title": get_locale_text("i18n_tutorial.shrine.title"),
            "desc": get_locale_text("i18n_tutorial.shrine.desc"),
            "landmark_id": lm_id,
            "coord": coord,
            "options": [
                {"action": "tutorial_shrine_recover", "tutorial_landmark": True, "text": get_locale_text("i18n_tutorial.shrine.opt_recover")},
                {"action": "tutorial_shrine_review", "tutorial_landmark": True, "text": get_locale_text("i18n_tutorial.shrine.opt_review_cards")},
                {"action": "tutorial_skip", "tutorial_landmark": True, "text": get_locale_text("i18n_tutorial.shrine.opt_skip")},
                {"action": "landmark_leave", "text": get_locale_text("i18n_tutorial.shrine.opt_leave")},
            ],
        }
    if lm_id == "tutorial_exit":
        return {
            "title": get_locale_text("i18n_tutorial.exit.title"),
            "desc": get_locale_text("i18n_tutorial.exit.desc"),
            "landmark_id": lm_id,
            "coord": coord,
            "options": [
                {"action": "tutorial_complete", "tutorial_landmark": True, "text": get_locale_text("i18n_tutorial.exit.opt_complete")},
                {"action": "tutorial_stay", "tutorial_landmark": True, "text": get_locale_text("i18n_tutorial.exit.opt_stay")},
                {"action": "tutorial_skip", "tutorial_landmark": True, "text": get_locale_text("i18n_tutorial.exit.opt_skip")},
            ],
        }
    return None


def execute_tutorial_landmark_option(save_manager, map_engine, run: GameRun, chosen: dict[str, Any]) -> str:
    action = str(chosen.get("action") or "")
    p = run.player
    uid = run.user_id
    if action == "tutorial_shrine_recover":
        gained_sp = restore_sp(p, 4)
        before_hp = p.hp
        p.hp = min(p.max_hp, p.hp + 10)
        gained_hp = p.hp - before_hp
        save_manager.save_save(uid, run)
        return get_locale_text("i18n_tutorial.shrine.recover_msg", sp=gained_sp, hp=gained_hp)
    if action == "tutorial_shrine_review":
        return get_locale_text("i18n_tutorial.shrine.review_msg")
    if action == "tutorial_stay":
        map_engine.complete_session(run, mark_cleared=False)
        save_manager.save_save(uid, run)
        return get_locale_text("i18n_tutorial.exit.stay_msg")
    if action == "tutorial_complete":
        run.node_data["tutorial_finished"] = True
        return finish_tutorial_run(
            save_manager,
            _resolve_town_engine(map_engine),
            uid,
            skipped=False,
        )
    if action == "tutorial_skip":
        run.node_data["tutorial_finished"] = True
        return finish_tutorial_run(
            save_manager,
            _resolve_town_engine(map_engine),
            uid,
            skipped=True,
        )
    return get_locale_text("err_invalid_option_idx")


@register_forced_trigger("tutorial_enter_spawn")
def _trigger_tutorial_spawn(run, fm, room, entry: dict) -> str:
    return get_locale_text("i18n_tutorial.trigger.spawn_hint")


@register_forced_trigger("tutorial_enter_battle")
def _trigger_tutorial_battle(run, fm, room, entry: dict) -> str:
    return get_locale_text("i18n_tutorial.trigger.battle_intro")


@register_forced_trigger("tutorial_enter_treasure")
def _trigger_tutorial_treasure(run, fm, room, entry: dict) -> str:
    return get_locale_text("i18n_tutorial.trigger.treasure_hint")


@register_forced_trigger("tutorial_enter_rest")
def _trigger_tutorial_rest(run, fm, room, entry: dict) -> str:
    return get_locale_text("i18n_tutorial.trigger.rest_hint")


@register_forced_trigger("tutorial_enter_shop")
def _trigger_tutorial_shop(run, fm, room, entry: dict) -> str:
    return get_locale_text("i18n_tutorial.trigger.shop_hint")
