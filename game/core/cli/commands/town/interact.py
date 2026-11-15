from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text
from .....data.world_social_config import WORLD_TALK_END_WORDS

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
        if query in WORLD_TALK_END_WORDS:
            yield router.world_social.close(user_id)
            return
        yield router.town_engine.talk_npc(user_id, query)

class TownTouchCommand(CommandHandler, names=["触摸", "touch", "tch", "摸", "调查", "inspect"], allowed_states=["town", "dialog"], help_key="town_touch"):
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
