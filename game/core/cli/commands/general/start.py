from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text

class StartCommand(CommandHandler, names=["开启", "start"], allowed_states=["menu", "town", "explore", "battle"], help_key="start"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if run:
            if len(parts) > 1 and parts[1] in ("确认", "confirm"):
                new_run = router.engine.start_new_game(user_id)
                if not new_run:
                    yield get_locale_text("i18n_cli_general_b.err_coop_no_solo")
                    return
                yield get_locale_text("i18n_cli_general_b.msg_restarted") + GameRenderer.render_game(new_run)
            else:
                yield get_locale_text("i18n_cli_general_b.warn_restart_confirm")
        else:
            new_run = router.engine.start_new_game(user_id)
            if not new_run:
                yield get_locale_text("i18n_cli_general_b.err_coop_no_solo")
                return
            yield GameRenderer.render_game(new_run)
