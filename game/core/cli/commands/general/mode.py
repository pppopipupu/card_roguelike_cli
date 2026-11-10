from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class ModeCommand(CommandHandler, names=["mode", "模式"], allowed_states=["menu", "town", "dialog", "explore", "battle"], help_key="mode"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        stats.rogue_mode = not stats.rogue_mode
        if stats.rogue_mode:
            stats.duel_mode = False
        router.save_manager.save_stats(user_id, stats)
        status_str = get_locale_text("i18n_cli_general_b.mode_status_on") if stats.rogue_mode else get_locale_text("i18n_cli_general_b.mode_status_off")
        yield get_locale_text("i18n_cli_general_b.mode_toggle", status=status_str)
