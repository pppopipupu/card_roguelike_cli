from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text

class MinionGraveyardCommand(CommandHandler, names=["随从墓地", "minion_graveyard", "mg"], allowed_states=["battle"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_commands.err_no_active_game_start_hint")
        elif run.node_type != "battle":
            yield get_locale_text("i18n_cli_commands.err_battle_graveyard_only")
        else:
            yield GameRenderer.render_minion_graveyard(run)
