from typing import Generator

from ...base import CommandHandler
from .....data.text.locale_data import get_locale_text


class SendMessageCommand(CommandHandler, names=["sendmsg", "发送消息", "私聊", "dm"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe", "outer_plane"], help_key="sendmsg"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 3:
            yield get_locale_text("i18n_world_social.remote.usage")
            return
        yield router.world_social.send_remote(user_id, " ".join(parts[1:]).strip())
