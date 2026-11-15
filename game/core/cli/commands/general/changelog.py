from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text
from .....renderer.menu import get_changelog_pages, render_reader_page

class ChangelogCommand(CommandHandler, names=["更新日志", "changelog", "cl", "更新"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe"], help_key="changelog"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        stats.reader_title = get_locale_text("renderer_menu.changelog_title")
        stats.reader_items = get_changelog_pages()
        stats.reader_page = 1
        stats.reader_active = True
        stats.reader_mode = "changelog"
        router.save_manager.save_stats(user_id, stats)
        yield render_reader_page(stats)
