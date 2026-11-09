from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer

class StatusCommand(CommandHandler, names=["状态", "status", "s"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            stats = router.save_manager.load_stats(user_id)
            yield GameRenderer.render_menu(stats)
        else:
            yield GameRenderer.render_game(run)
