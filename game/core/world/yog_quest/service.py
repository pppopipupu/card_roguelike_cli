import uuid
from typing import Optional

from ....data.locale_data import get_locale_text
from ....data.outer_plane_config import NECRONOMICON_ITEM, OUTER_PLANE_ACTIVE_FLAG
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
from ....data.balance_config import COOP_MAX_PLAYERS
from ..presence import sync_active
from ..world_social import WorldSocialService
from ..open_world.loadout_service import OpenWorldLoadoutService
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
    if int(getattr(stats, "yog_sothoth_kill_count", 0) or 0) <= 0:
        return False, get_locale_text("i18n_yog_quest.enter.need_kill")
    if not stats.town_flags.get(YOG_INFO_FLAG):
        return False, get_locale_text("i18n_yog_quest.enter.need_info")
    if YOG_SIGIL_ITEM not in (getattr(stats, "town_inventory", None) or []):
        return False, get_locale_text("i18n_yog_quest.enter.need_sigil")
    if stats.town_pos != "west_gate":
        return False, get_locale_text("i18n_yog_quest.enter.need_gate")
    return True, ""


def _party_quest_members(save_manager, user_id: str, stats) -> tuple[list[str] | None, str]:
    lobby_id = getattr(stats, "active_lobby_id", "")
    if not lobby_id:
        return None, ""
    lobby = save_manager.get_lobby(lobby_id)
    if not lobby:
        stats.active_lobby_id = ""
        save_manager.save_stats(user_id, stats)
        return None, ""
    if lobby.get("leader_id") != user_id:
        return [], get_locale_text("i18n_world_social.team_quest.not_leader")
    members = list(lobby.get("members", []))
    if len(members) < 2:
        return None, ""
    if len(members) > COOP_MAX_PLAYERS:
        return [], get_locale_text("i18n_social.team_start.max_players", max_members=COOP_MAX_PLAYERS)
    ready = lobby.get("ready", {})
    for member_uid in members:
        member_stats = save_manager.load_stats(member_uid)
        profile_name = getattr(member_stats, "player_name", member_uid)
        if getattr(member_stats, "active_lobby_id", "") != lobby_id:
            return [], get_locale_text("i18n_world_social.team_quest.member_not_town", name=profile_name)
        if (
            getattr(member_stats, "active_coop_id", "")
            or save_manager.has_personal_save(member_uid)
            or member_stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG)
        ):
            return [], get_locale_text("i18n_world_social.team_quest.member_busy", name=profile_name)
        if not member_stats.in_town:
            return [], get_locale_text("i18n_world_social.team_quest.member_not_town", name=profile_name)
        if not ready.get(member_uid) and member_uid != user_id:
            return [], get_locale_text("i18n_world_social.team_quest.member_not_ready", name=profile_name)
        if not member_stats.town_flags.get(YOG_INFO_FLAG):
            return [], get_locale_text("i18n_yog_quest.enter.need_info")
    return members, ""


def _start_party_quest(save_manager, engine, user_id: str, members: list[str]) -> str:
    coop_id = uuid.uuid4().hex[:8]
    lobby_id = getattr(save_manager.load_stats(user_id), "active_lobby_id", "")
    players = {}
    member_stats = {}
    for member_uid in members:
        m_stats = save_manager.load_stats(member_uid)
        player = OpenWorldLoadoutService.build_player_state(member_uid, m_stats)
        player.stage = int(FLOOR_CONFIGS[YOG_FLOOR_WILDS]["stage_min"])
        players[member_uid] = player
        member_stats[member_uid] = m_stats
        save_manager.save_stats(member_uid, m_stats)
    leader_player = players[user_id]
    run = GameRun(
        user_id=user_id,
        node_type="grid_map",
        player=leader_player,
        enemies=[],
        node_data={"yog_quest": True},
        coop_id=coop_id,
        leader_id=user_id,
        party_order=list(members),
        players=players,
    )
    run.floor_map = generate_yog_quest_floor(run, YOG_FLOOR_WILDS)
    run.player = leader_player
    run.user_id = user_id
    for member_uid in members:
        stats = member_stats[member_uid]
        if stats.town_flags.get(YOG_QUEST_FLAG) != "completed":
            stats.town_flags[YOG_QUEST_FLAG] = "started"
        stats.town_flags[YOG_QUEST_ZONE_KEY] = 0
        stats.in_town = False
        stats.active_coop_id = coop_id
        stats.active_lobby_id = ""
        save_manager.save_stats(member_uid, stats)
    save_manager.save_save(user_id, run)
    if lobby_id:
        save_manager.delete_lobby(lobby_id)
    social = WorldSocialService(save_manager)
    for member_uid in members:
        social.presence.sync(member_uid, stats=member_stats[member_uid], run=run)
        if member_uid != user_id:
            social.send_system(member_uid, get_locale_text("i18n_world_social.team_quest.member_notice"))
    return get_locale_text("i18n_yog_quest.enter.first") + "\n\n" + GameRenderer.render_game(run)


def start_quest_run(save_manager, engine, user_id: str) -> Optional[str]:
    if save_manager.load_save(user_id) is not None:
        return get_locale_text("i18n_yog_quest.enter.run_in_progress")
    stats = save_manager.load_stats(user_id)
    ok, msg = can_start(stats)
    if not ok:
        return msg
    members, party_error = _party_quest_members(save_manager, user_id, stats)
    if party_error:
        return party_error
    if members:
        return _start_party_quest(save_manager, engine, user_id, members)
    lobby_id = getattr(stats, "active_lobby_id", "")
    if lobby_id:
        stats.active_lobby_id = ""
        save_manager.delete_lobby(lobby_id)
    player = OpenWorldLoadoutService.build_player_state(user_id, stats)
    run = GameRun(
        user_id=user_id,
        node_type="grid_map",
        player=player,
        enemies=[],
        node_data={"yog_quest": True},
        party_order=[user_id],
        leader_id=user_id,
        players={user_id: player},
    )
    run.floor_map = generate_yog_quest_floor(run, YOG_FLOOR_WILDS)
    player.stage = int(FLOOR_CONFIGS[YOG_FLOOR_WILDS]["stage_min"])
    if stats.town_flags.get(YOG_QUEST_FLAG) != "completed":
        stats.town_flags[YOG_QUEST_FLAG] = "started"
    stats.town_flags[YOG_QUEST_ZONE_KEY] = 0
    stats.in_town = False
    save_manager.save_stats(user_id, stats)
    save_manager.save_save(user_id, run)
    sync_active(user_id, stats=stats, run=run)
    return get_locale_text("i18n_yog_quest.enter.first") + "\n\n" + GameRenderer.render_game(run)


def finish_quest(save_manager, map_engine, run: GameRun) -> str:
    from ...progress.achievement_service import AchievementService
    OpenWorldLoadoutService.sync_run_to_stats(save_manager, run)
    uid = run.user_id
    fm = getattr(run, "floor_map", None)
    flags = dict((fm.floor_flags.get("yog_flags") or {})) if fm is not None else {}
    butcher = bool(flags.get("altar_defiled") or flags.get("blade_offered"))
    coop_id = getattr(run, "coop_id", "")
    members = list(run.all_human_uids()) if hasattr(run, "all_human_uids") else [uid]
    stats_by_uid = {}
    for member_uid in members:
        stats = save_manager.load_stats(member_uid)
        prev_flags = stats.town_flags.get("yog_quest_flags")
        merged_flags = dict(flags)
        if isinstance(prev_flags, dict) and prev_flags.get("altar_defiled"):
            merged_flags["altar_defiled"] = True
        stats.town_flags[YOG_QUEST_FLAG] = "completed"
        stats.town_flags["yog_quest_flags"] = merged_flags
        stats.town_flags[YOG_QUEST_ROUTE_KEY] = "butcher" if butcher else "standard"
        if NECRONOMICON_ITEM not in stats.town_inventory:
            stats.town_inventory.append(NECRONOMICON_ITEM)
        stats.in_town = True
        stats.town_pos = "square"
        stats.active_coop_id = ""
        stats.active_lobby_id = ""
        save_manager.save_stats(member_uid, stats)
        stats_by_uid[member_uid] = stats
    run.node_data["yog_finished"] = True
    if coop_id:
        save_manager.delete_coop_save(coop_id)
    else:
        save_manager.delete_save(uid)
    achievement = AchievementService(save_manager)
    for member_uid, stats in stats_by_uid.items():
        achievement.unlock(member_uid, "temple_awakening", stats=stats)
        if butcher:
            achievement.unlock(member_uid, "silent_passage", stats=stats)
    town_engine = getattr(map_engine, "town_engine", None)
    if town_engine is None:
        return ""
    leader_stats = stats_by_uid.get(uid) or save_manager.load_stats(uid)
    return town_engine.render_current_room(uid, leader_stats)
