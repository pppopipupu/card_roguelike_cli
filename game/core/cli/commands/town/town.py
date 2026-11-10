from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class TownCommand(CommandHandler, names=["主城", "town"], allowed_states=["menu"], help_key="town"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if run:
            yield get_locale_text("i18n_cli_commands.town_game_in_progress")
            return
        stats = router.save_manager.load_stats(user_id)
        stats.in_town = True
        router.save_manager.save_stats(user_id, stats)
        yield router.town_engine.render_current_room(user_id, stats)
