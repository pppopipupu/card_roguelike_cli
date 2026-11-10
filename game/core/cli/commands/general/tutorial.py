from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer

class TutorialCommand(CommandHandler, names=["教程", "tutorial"], help_key="tutorial"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        yield GameRenderer.render_tutorial()
