from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class TownTakeCommand(CommandHandler, names=["拿取", "捡起", "take", "pick"], allowed_states=["town", "dialog"], help_key="take"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.town_take_missing_arg")
        else:
            yield router.town_engine.pick_item(user_id, " ".join(parts[1:]))

class TownUseCommand(CommandHandler, names=["使用", "use"], allowed_states=["town", "dialog"], help_key="town_use"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.town_use_missing_arg")
        else:
            yield router.town_engine.use_item(user_id, " ".join(parts[1:]))

class TownTalkCommand(CommandHandler, names=["对话", "交互", "talk", "interact", "inter", "talk_to"], allowed_states=["town", "dialog"], help_key="town_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.town_talk_missing_arg")
            return
        query = " ".join(parts[1:]).strip()
        from ....prism.card_talk import strip_card_talk_prefix, try_card_talk
        _, has_card_prefix = strip_card_talk_prefix(query)
        if has_card_prefix:
            stats = router.save_manager.load_stats(user_id)
            card_res = try_card_talk(router.save_manager, router.engine, user_id, query, run=None, stats=stats, explicit=True)
            if card_res is not None:
                yield card_res
                return
        yield router.town_engine.talk_npc(user_id, query)

class TownTouchCommand(CommandHandler, names=["touch", "tch", "摸", "触摸", "调查", "inspect"], allowed_states=["town", "dialog"], help_key="town_touch"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.town_touch_missing_arg")
        else:
            yield router.town_engine.touch_target(user_id, " ".join(parts[1:]))

class TownAttackCommand(CommandHandler, names=["攻击", "attack", "atk", "打"], allowed_states=["town", "dialog"], help_key="town_attack"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.town_attack_missing_arg")
        else:
            yield router.town_engine.attack_target(user_id, " ".join(parts[1:]))
