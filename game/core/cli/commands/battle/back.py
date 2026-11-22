from typing import Generator
from ...base import CommandHandler
from .....data.text.locale_data import get_locale_text
from .....renderer import GameRenderer


class BackCommand(CommandHandler, names=["back", "bk", "返回", "上一轮"], allowed_states=["battle"], help_key="back"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_commands.err_no_active_game")
            return
        if not run.node_data.get("state_stack"):
            yield get_locale_text("i18n_cli_core.back_no_active_selection")
            return
        res, term, success = router._execute_sub_action(user_id, run, parts)
        if term or (run and run.node_data.get("in_queue")):
            yield res
        else:
            yield res + "\n" + GameRenderer.render_game(run)
        return success
