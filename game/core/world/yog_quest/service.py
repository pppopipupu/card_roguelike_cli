from typing import Optional

from ....data.locale_data import get_locale_text
from ....data.outer_plane_config import NECRONOMICON_ITEM
from ....data.grid_map_config import FLOOR_CONFIGS
from ....data.yog_quest_config import (
    YOG_FLOOR_WILDS,
    YOG_INFO_FLAG,
    YOG_QUEST_FLAG,
    YOG_QUEST_ROUTE_KEY,
    YOG_QUEST_ZONE_KEY,
    YOG_SIGIL_ITEM,
)
from ....models.state import GameRun
from ....renderer import GameRenderer
from .floor import generate_yog_quest_floor


def ensure_sigil(stats) -> bool:
    if not stats.town_flags.get(YOG_INFO_FLAG):
        return False
    inventory = getattr(stats, "town_inventory", None)
    if not isinstance(inventory, list):
        inventory = []
        stats.town_inventory = inventory
    if YOG_SIGIL_ITEM in inventory:
        return False
    inventory.append(YOG_SIGIL_ITEM)
    return True


def can_start(stats) -> tuple[bool, str]:
    if stats.town_flags.get(YOG_QUEST_FLAG) == "completed":
        return False, get_locale_text("i18n_yog_quest.enter.finished")
    if int(getattr(stats, "yog_sothoth_kill_count", 0) or 0) <= 0:
        return False, get_locale_text("i18n_yog_quest.enter.need_kill")
    if not stats.town_flags.get(YOG_INFO_FLAG):
        return False, get_locale_text("i18n_yog_quest.enter.need_info")
    if YOG_SIGIL_ITEM not in (getattr(stats, "town_inventory", None) or []):
        return False, get_locale_text("i18n_yog_quest.enter.need_sigil")
    if stats.town_pos != "west_gate":
        return False, get_locale_text("i18n_yog_quest.enter.need_gate")
    return True, ""


def start_quest_run(save_manager, engine, user_id: str) -> Optional[str]:
    if save_manager.load_save(user_id) is not None:
        return get_locale_text("i18n_yog_quest.enter.run_in_progress")
    stats = save_manager.load_stats(user_id)
    ok, msg = can_start(stats)
    if not ok:
        return msg
    player = engine.build_player_state(user_id)
    run = GameRun(
        user_id=user_id,
        node_type="grid_map",
        player=player,
        enemies=[],
        node_data={},
        party_order=[user_id],
        leader_id=user_id,
        players={user_id: player},
    )
    run.floor_map = generate_yog_quest_floor(run, YOG_FLOOR_WILDS)
    player.stage = int(FLOOR_CONFIGS[YOG_FLOOR_WILDS]["stage_min"])
    player.sp = player.max_sp
    stats.town_flags[YOG_QUEST_FLAG] = "started"
    stats.town_flags[YOG_QUEST_ZONE_KEY] = 0
    stats.in_town = False
    save_manager.save_stats(user_id, stats)
    save_manager.save_save(user_id, run)
    return get_locale_text("i18n_yog_quest.enter.first") + "\n\n" + GameRenderer.render_game(run)


def finish_quest(save_manager, map_engine, run: GameRun) -> str:
    from ...progress.achievement_service import AchievementService
    uid = run.user_id
    stats = save_manager.load_stats(uid)
    fm = getattr(run, "floor_map", None)
    flags = dict((fm.floor_flags.get("yog_flags") or {})) if fm is not None else {}
    butcher = bool(flags.get("altar_defiled") or flags.get("blade_offered"))
    stats.town_flags[YOG_QUEST_FLAG] = "completed"
    stats.town_flags["yog_quest_flags"] = flags
    stats.town_flags[YOG_QUEST_ROUTE_KEY] = "butcher" if butcher else "standard"
    run.node_data["yog_finished"] = True
    if NECRONOMICON_ITEM not in stats.town_inventory:
        stats.town_inventory.append(NECRONOMICON_ITEM)
    stats.in_town = True
    stats.town_pos = "square"
    save_manager.save_stats(uid, stats)
    save_manager.delete_save(uid)
    achievement = AchievementService(save_manager)
    achievement.unlock(uid, "temple_awakening", stats=stats)
    if butcher:
        achievement.unlock(uid, "silent_passage", stats=stats)
    town_engine = getattr(map_engine, "town_engine", None)
    if town_engine is None:
        return ""
    return town_engine.render_current_room(uid, stats)
