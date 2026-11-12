from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer

class StatusCommand(CommandHandler, names=["状态", "status", "s"], allowed_states=["menu", "town", "explore", "battle", "dialog", "cafe"], help_key="status"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if run:
            yield GameRenderer.render_game(run)
            return
        stats = router.save_manager.load_stats(user_id)
        if stats.in_town:
            yield router.town_engine.render_current_room(user_id, stats)
            return
        yield GameRenderer.render_menu(stats)
