from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text

class TownMoveCommand(CommandHandler, names=["w", "a", "s", "d", "up", "down", "left", "right"], allowed_states=["town"], help_key="town_move"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        yield router.town_engine.move(user_id, parts[0].lower())

class TownHomeCommand(CommandHandler, names=["回城", "home"], allowed_states=["town"], help_key="town_home"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        stats.town_pos = "square"
        router.save_manager.save_stats(user_id, stats)
        yield router.town_engine.render_current_room(user_id, stats)

class TownExitCommand(CommandHandler, names=["退出", "quit", "exit"], allowed_states=["town"], help_key="town_exit"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        stats.in_town = False
        router.save_manager.save_stats(user_id, stats)
        yield get_locale_text("i18n_cli_commands.town_exit_success") + "\n\n" + GameRenderer.render_menu(stats)
