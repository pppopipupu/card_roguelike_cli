from typing import Generator
from ...base import CommandHandler
from ....prism.card_talk import try_card_talk
from .....data.locale_data import get_locale_text


class CardTalkCommand(
    CommandHandler,
    names=["ctalk", "cardtalk", "卡牌对话"],
    allowed_states=["menu", "town", "dialog", "grid_map", "explore", "battle", "cafe", "outer_plane"],
    help_key="card_talk",
):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        run = router.save_manager.load_save(user_id)
        stats = router.save_manager.load_stats(user_id)
        res = try_card_talk(router.save_manager, router.engine, user_id, query, run=run, stats=stats, explicit=True)
        yield res or get_locale_text("i18n_prism.card_talk.missing_arg")


class MenuTalkCommand(
    CommandHandler,
    names=["talk", "talk_to", "interact", "inter", "对话", "交谈"],
    allowed_states=["menu"],
    help_key="menu_talk",
):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        if not query:
            yield get_locale_text("i18n_prism.card_talk.missing_arg")
            return
        stats = router.save_manager.load_stats(user_id)
        res = try_card_talk(router.save_manager, router.engine, user_id, query, run=None, stats=stats, explicit=True)
        yield res or get_locale_text("i18n_prism.card_talk.card_not_found", target=query)
