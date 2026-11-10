from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer

class ChangelogCommand(CommandHandler, names=["更新日志", "changelog", "cl", "更新"], allowed_states=["menu", "town", "explore", "battle", "dialog", "cafe"], help_key="changelog"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        yield GameRenderer.render_changelog()
