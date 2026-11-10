from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text

class EnemyGraveyardCommand(CommandHandler, names=["敌人墓地", "enemy_graveyard", "eg"], allowed_states=["battle"], help_key="enemy_graveyard"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_commands.err_no_active_game_start_hint")
        elif run.node_type != "battle":
            yield get_locale_text("i18n_cli_commands.err_battle_graveyard_only")
        else:
            yield GameRenderer.render_enemy_graveyard(run)
