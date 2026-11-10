from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer

class StatsCommand(CommandHandler, names=["统计", "stat", "stats"], help_key="stats"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield GameRenderer.render_stats(stats)
