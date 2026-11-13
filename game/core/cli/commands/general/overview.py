from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class OverviewCommand(CommandHandler, names=["总览", "overview"], allowed_states=["menu", "town", "grid_map", "explore", "battle"], help_key="overview"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        if len(parts) > 1 and parts[1] in ("遗物", "relic", "relics"):
            from .....renderer.menu import get_rogue_relic_library_items
            items = get_rogue_relic_library_items()
            stats.reader_title = get_locale_text("i18n_cli_general_c.overview.relic_title")
        else:
            from .....renderer.menu import get_rogue_card_library_items
            items = get_rogue_card_library_items(user_id)
            stats.reader_title = get_locale_text("i18n_cli_general_c.overview.card_title")
        stats.reader_items = items
        stats.reader_page = 1
        stats.reader_active = True
        stats.reader_mode = "rogue"
        router.save_manager.save_stats(user_id, stats)
        from .....renderer.menu import render_reader_page
        yield render_reader_page(stats)
