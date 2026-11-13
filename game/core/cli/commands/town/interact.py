from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class TownTakeCommand(CommandHandler, names=["拿取", "捡起", "take", "pick"], allowed_states=["town"], help_key="take"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.town_take_missing_arg")
        else:
            yield router.town_engine.pick_item(user_id, " ".join(parts[1:]))

class TownUseCommand(CommandHandler, names=["使用", "use"], allowed_states=["town"], help_key="town_use"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.town_use_missing_arg")
        else:
            yield router.town_engine.use_item(user_id, " ".join(parts[1:]))

class TownTalkCommand(CommandHandler, names=["对话", "交互", "talk", "interact", "inter", "talk_to"], allowed_states=["town"], help_key="town_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.town_talk_missing_arg")
        else:
            yield router.town_engine.talk_npc(user_id, " ".join(parts[1:]))
