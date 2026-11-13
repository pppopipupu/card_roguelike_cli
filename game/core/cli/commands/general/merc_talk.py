from typing import Generator
from ...base import CommandHandler


class MercTalkCommand(CommandHandler, names=["对话", "交谈", "talk", "talk_to", "interact", "inter"], allowed_states=["explore", "battle"], help_key="merc_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        if run.node_type == "shop":
            from .....data.room_interact_data import ROOM_NPCS
            from .....data.locale_data import get_locale_text
            from ...base.pinyin_match import find_entry_by_query
            from ....world.rooms.shop_dialog import open_shop_dialog
            cfg = ROOM_NPCS["shop_merchant"]
            mname = get_locale_text(cfg["name_key"])
            ql = query.lower()
            is_merchant = not query or ql in ("shop_merchant", mname.lower()) or ql in mname.lower() or any(ql == a.lower() for a in cfg["aliases"]) or find_entry_by_query([("shop_merchant", mname)] + [("shop_merchant", a) for a in cfg["aliases"]], query) is not None
            if is_merchant:
                yield open_shop_dialog(router.engine.map_engine.explore_engine, run)
                return
        from ....party.mercenary import find_mercenary_uid, open_merc_dialog
        merc_uid, err = find_mercenary_uid(run, query, user_id)
        if err:
            yield err
            return
        res = open_merc_dialog(run, user_id, merc_uid)
        router.save_manager.save_save(user_id, run)
        yield res
