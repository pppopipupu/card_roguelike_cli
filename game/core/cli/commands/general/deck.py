from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text

class DeckCommand(CommandHandler, names=["牌组", "deck"], allowed_states=["menu", "town", "explore", "battle"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_deck_no_game")
        else:
            yield GameRenderer.render_deck(run)
