from typing import Generator
from ...base import CommandHandler


class MercTalkCommand(CommandHandler, names=["交谈", "talk", "talk_to", "interact", "inter"], allowed_states=["explore", "battle"], help_key="merc_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            return
        from ....mercenary import find_mercenary_uid, open_merc_dialog
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        merc_uid, err = find_mercenary_uid(run, query, user_id)
        if err:
            yield err
            return
        res = open_merc_dialog(run, user_id, merc_uid)
        router.save_manager.save_save(user_id, run)
        yield res
