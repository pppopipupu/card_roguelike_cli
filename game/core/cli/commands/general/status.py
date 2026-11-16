from typing import Generator
from ...base import CommandHandler
from .....data.outer_plane_config import OUTER_PLANE_ACTIVE_FLAG
from .....renderer import GameRenderer

class StatusCommand(CommandHandler, names=["状态", "status", "r"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe", "outer_plane"], help_key="status"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if run:
            yield GameRenderer.render_game(run)
            return
        stats = router.save_manager.load_stats(user_id)
        if stats.in_town:
            if stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG):
                yield router.town_engine.outer_plane_engine.look(user_id, stats)
                return
            yield router.town_engine.render_current_room(user_id, stats)
            return
        yield GameRenderer.render_menu(stats)
