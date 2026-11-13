from typing import Generator
from ...base import CommandHandler
from ...help import help_detail_text, help_index_text

class HelpCommand(CommandHandler, names=["帮助", "help"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe"], help_key="help"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield help_index_text()
            return
        yield help_detail_text(router.save_manager, user_id, parts)
