from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class AbandonCommand(CommandHandler, names=["放弃", "abandon"], allowed_states=["grid_map", "explore", "battle"], help_key="abandon"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        if len(parts) > 1 and parts[1] in ("确认", "confirm"):
            from ....party.session import SessionContextScoper
            run.party_order = SessionContextScoper.ensure_full_party_order(run)
            multi = run.player_count() > 1
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False, create_corpse=False, force=True)
            if multi:
                yield get_locale_text("i18n_cli_general_b.msg_abandoned_coop", settle_msg=settle_msg)
            else:
                yield get_locale_text("i18n_cli_general_b.msg_abandoned_solo", settle_msg=settle_msg)
        else:
            yield get_locale_text("i18n_cli_general_b.warn_abandon_confirm")
