from typing import Generator
from ...base import CommandHandler
from .....data.text.locale_data import get_locale_text
from .....data.world.outer_plane_config import OUTER_PLANE_ACTIVE_FLAG, OUTER_PLANE_ROOM_KEY, OUTER_PLANE_START_ROOM
from .....data.world.world_social_config import WORLD_OUTER_PLANE
from ....world.open_world.death_service import OpenWorldDeathService
from ....world.open_world.loadout_service import is_open_world_run


class AbandonCommand(CommandHandler, names=["放弃", "abandon"], allowed_states=["grid_map", "explore", "battle", "outer_plane"], help_key="abandon"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        confirm = len(parts) > 1 and parts[1] in ("确认", "confirm")
        if not run:
            stats = router.save_manager.load_stats(user_id)
            if stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG):
                if not confirm:
                    yield get_locale_text("i18n_cli_general_b.warn_abandon_confirm")
                    return
                room = str(stats.town_flags.get(OUTER_PLANE_ROOM_KEY) or OUTER_PLANE_START_ROOM)
                yield OpenWorldDeathService.handle_state_death(
                    router.save_manager,
                    router.town_engine,
                    user_id,
                    stats,
                    WORLD_OUTER_PLANE,
                    room,
                    is_abandon=True,
                )
                return
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        if confirm:
            from .....data.world.pvp_config import PVP_MATCH_KEY
            if run.node_data.get(PVP_MATCH_KEY):
                from ....battle.pvp_service import PvpService
                match = router.save_manager.pvp.get_match(run.node_data.get(PVP_MATCH_KEY))
                if match is not None:
                    p1_uid = str(match.get("p1_uid", ""))
                    p2_uid = str(match.get("p2_uid", ""))
                    opp_uid = p2_uid if str(user_id) == p1_uid else p1_uid
                    _, lose_msg = PvpService.settle_pvp_match(
                        router.save_manager,
                        router.town_engine,
                        router.world_social,
                        match["id"],
                        opp_uid,
                        user_id,
                        reason="abandon",
                        actor_uid=user_id,
                    )
                    updated_stats = router.save_manager.load_stats(user_id)
                    yield lose_msg + "\n\n" + router.town_engine.render_current_room(user_id, updated_stats)
                    return
            from ....party.session import SessionContextScoper
            from ....world.tutorial import finish_tutorial_run, is_tutorial_run
            if is_tutorial_run(run):
                yield finish_tutorial_run(router.save_manager, router.town_engine, user_id, skipped=True)
                return
            run.party_order = SessionContextScoper.ensure_full_party_order(run)
            multi = run.player_count() > 1
            open_world = is_open_world_run(run)
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False, create_corpse=open_world, force=True)
            if open_world:
                updated_stats = router.save_manager.load_stats(user_id)
                yield settle_msg + "\n\n" + router.town_engine.render_current_room(user_id, updated_stats)
                return
            if multi:
                yield get_locale_text("i18n_cli_general_b.msg_abandoned_coop", settle_msg=settle_msg)
            else:
                yield get_locale_text("i18n_cli_general_b.msg_abandoned_solo", settle_msg=settle_msg)
        else:
            yield get_locale_text("i18n_cli_general_b.warn_abandon_confirm")
