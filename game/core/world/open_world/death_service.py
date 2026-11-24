from typing import Optional

from ....data.world.open_world_config import (
    OPEN_WORLD_COORD_KEY,
    OPEN_WORLD_WORLD_KEY,
    WORLD_YOG_TEMPLE,
)
from ....data.world.outer_plane_config import (
    OUTER_PLANE_ACTIVE_FLAG,
    OUTER_PLANE_LUCIDITY_KEY,
    OUTER_PLANE_ROOM_KEY,
    OUTER_PLANE_START_ROOM,
)
from ....data.world.yog_quest_config import YOG_FLOOR_TEMPLE
from ....models.state import GameRun, PlayerState, UserStats
from ...text.events import LocaleText
from ...text.pipeline import render_text_node
from ..presence import WORLD_OUTER_PLANE, WORLD_SNOWFIELD, WORLD_TOWN
from .ghost_service import OpenWorldGhostService
from .loadout_service import OpenWorldLoadoutService


class OpenWorldDeathService:
    @staticmethod
    def resolve_run_location(run: GameRun, stats: UserStats) -> tuple[str, str]:
        world = str(run.node_data.get(OPEN_WORLD_WORLD_KEY) or "")
        coord = str(run.node_data.get(OPEN_WORLD_COORD_KEY) or "")
        if world and coord:
            return world, coord
        floor_map = getattr(run, "floor_map", None)
        if floor_map is not None:
            coord = str(floor_map.player_coords.get(run.user_id, "") or "")
            world = WORLD_YOG_TEMPLE if getattr(floor_map, "floor_index", 0) == YOG_FLOOR_TEMPLE else WORLD_SNOWFIELD
            return world, coord
        if stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG):
            return WORLD_OUTER_PLANE, str(stats.town_flags.get(OUTER_PLANE_ROOM_KEY) or OUTER_PLANE_START_ROOM)
        return WORLD_TOWN, str(getattr(stats, "town_pos", "square") or "square")

    @staticmethod
    def _clear_outer_plane_flags(stats: UserStats) -> None:
        stats.town_flags.pop(OUTER_PLANE_ACTIVE_FLAG, None)
        stats.town_flags.pop(OUTER_PLANE_ROOM_KEY, None)
        stats.town_flags.pop(OUTER_PLANE_LUCIDITY_KEY, None)

    @staticmethod
    def _clear_transient_dialog_flags(stats: UserStats) -> None:
        for key in (
            "current_dialog",
            "market_sub_menu",
            "shop_sub_menu",
            "jack_agreement_menu",
            "jack_riddle_step",
            "center_chest_tab",
        ):
            stats.town_flags.pop(key, None)

    @staticmethod
    def _spawn_and_strip(
        save_manager,
        user_id: str,
        stats: UserStats,
        world: str,
        coord: str,
        cause_key: str,
        is_abandon: bool,
        player=None,
    ) -> LocaleText:
        snapshot = OpenWorldLoadoutService.snapshot_loadout(stats, player=player)
        cause_text = render_text_node(LocaleText(key=cause_key))
        OpenWorldGhostService.spawn_from_death(
            save_manager,
            user_id,
            stats,
            world,
            coord,
            cause_text,
            snapshot,
        )
        OpenWorldLoadoutService.strip_on_death(stats)
        OpenWorldDeathService._clear_outer_plane_flags(stats)
        OpenWorldDeathService._clear_transient_dialog_flags(stats)
        stats.in_town = True
        stats.town_pos = "square"
        notice_key = "i18n_open_world.ghost_abandon_notice" if is_abandon else "i18n_open_world.ghost_death_notice"
        return LocaleText(
            key=notice_key,
            params={
                "location": OpenWorldGhostService.location_node(world, coord),
                "bag_count": len(snapshot.get("bag_items") or []),
                "relic_count": len(snapshot.get("relics") or []),
                "ghost_name": OpenWorldGhostService.ghost_name_node(str(getattr(stats, "player_name", user_id) or user_id)),
            },
        )

    @staticmethod
    def handle_run_death(
        save_manager,
        town_engine,
        user_id: str,
        run: GameRun,
        *,
        is_abandon: bool = False,
        cause_key: Optional[str] = None,
    ) -> str:
        resolved_cause = cause_key or ("i18n_open_world.cause_abandon" if is_abandon else "i18n_open_world.cause_defeat")
        run.node_data["open_world_death_handled"] = True
        players = getattr(run, "players", None) or {}
        member_uids = list(run.all_human_uids()) if hasattr(run, "all_human_uids") else [run.user_id]
        if user_id not in member_uids:
            member_uids.insert(0, user_id)

        primary_notice: LocaleText | None = None
        for uid in member_uids:
            stats = save_manager.load_stats(uid)
            player = players.get(uid) if players else run.player
            floor_map = getattr(run, "floor_map", None)
            if floor_map is not None:
                coord = str(floor_map.player_coords.get(uid) or floor_map.player_coords.get(run.user_id) or "")
                world = WORLD_YOG_TEMPLE if getattr(floor_map, "floor_index", 0) == YOG_FLOOR_TEMPLE else WORLD_SNOWFIELD
            else:
                world, coord = OpenWorldDeathService.resolve_run_location(run, stats)
            notice_node = OpenWorldDeathService._spawn_and_strip(
                save_manager,
                uid,
                stats,
                world,
                coord,
                resolved_cause,
                is_abandon,
                player=player,
            )
            stats.active_lobby_id = ""
            if town_engine is not None:
                town_engine.record_visited_room(stats)
            save_manager.save_stats(uid, stats)
            if uid == user_id or primary_notice is None:
                primary_notice = notice_node

        save_manager.delete_save(user_id)

        notice_text = render_text_node(primary_notice) if primary_notice is not None else ""
        if town_engine is not None:
            viewer_stats = save_manager.load_stats(user_id)
            return notice_text + "\n\n" + town_engine.render_current_room(user_id, viewer_stats)
        return notice_text

    @staticmethod
    def handle_state_death(
        save_manager,
        town_engine,
        user_id: str,
        stats: UserStats,
        world: str,
        coord: str,
        *,
        is_abandon: bool = False,
        cause_key: Optional[str] = None,
        player: Optional[PlayerState] = None,
    ) -> str:
        resolved_cause = cause_key or ("i18n_open_world.cause_abandon" if is_abandon else "i18n_open_world.cause_lucidity")
        notice_node = OpenWorldDeathService._spawn_and_strip(
            save_manager,
            user_id,
            stats,
            world,
            coord,
            resolved_cause,
            is_abandon,
            player=player,
        )
        if town_engine is not None:
            town_engine.record_visited_room(stats)
        save_manager.save_stats(user_id, stats)
        notice_text = render_text_node(notice_node)
        if town_engine is not None:
            return notice_text + "\n\n" + town_engine.render_current_room(user_id, stats)
        return notice_text
