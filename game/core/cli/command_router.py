from typing import Generator
from ..cli.base import CommandHandler
from ...data.locale_data import get_locale_text

class CommandRouter:
    def __init__(self, save_manager, engine):
        self.save_manager = save_manager
        self.engine = engine
        self._command_handlers = CommandHandler.registry

    def execute_command(self, router, user_id: str, parts: list[str], curr_state: str) -> Generator[str, None, None]:
        if not parts:
            return
        sub = parts[0].lower()
        handler, exists = CommandHandler.resolve(sub, curr_state)
        if handler:
            yield from handler.execute(router, user_id, parts)
        elif exists:
            yield get_locale_text("i18n_cli_commands.err_command_unavailable", sub=sub)
