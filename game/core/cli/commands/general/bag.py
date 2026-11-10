from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer

class BagCommand(CommandHandler, names=["背包", "bag", "inventory", "inv"], help_key="bag"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield GameRenderer.render_bag(stats)
