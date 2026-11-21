from typing import Generator
from ...base import CommandHandler


class MercTalkCommand(CommandHandler, names=["对话", "交谈", "talk", "talk_to", "interact", "inter"], allowed_states=["explore", "battle"], help_key="merc_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        if query:
            from ....prism.card_talk import strip_card_talk_prefix, try_card_talk
            _, has_card_prefix = strip_card_talk_prefix(query)
            if has_card_prefix:
                card_res = try_card_talk(router.save_manager, router.engine, user_id, query, run=run, explicit=True)
                if card_res is not None:
                    yield card_res
                    return
            player_res = router.world_social.try_talk(user_id, query, run=run)
            if player_res is not None:
                yield player_res
                return
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
        from .....data.locale_data import get_locale_text
        from ....party.mercenary import find_mercenary_uid, list_owned_mercenaries, open_merc_dialog
        merc_uid, err = find_mercenary_uid(run, query, user_id)
        if merc_uid is None:
            if query:
                from ....prism.card_talk import try_card_talk
                card_res = try_card_talk(router.save_manager, router.engine, user_id, query, run=run, explicit=False)
                if card_res is not None:
                    yield card_res
                    return
                if not list_owned_mercenaries(run, user_id):
                    yield get_locale_text("i18n_room_interact.dialog.talk_not_found", target=query)
                    return
            else:
                location = router.world_social.presence.resolve_location(user_id, run=run)
                if location is not None and router.world_social.presence.players(location[0], coord=location[1], exclude_uid=user_id):
                    yield router.world_social.say_to_world(user_id, location[0], location[1], "")
                    return
            yield err or get_locale_text("i18n_mercenary.err_not_found", target=query)
            return
        res = open_merc_dialog(run, user_id, merc_uid)
        router.save_manager.save_save(user_id, run)
        yield res
