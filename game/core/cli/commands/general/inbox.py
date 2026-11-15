from typing import Generator

from ...base import CommandHandler


class InboxCommand(CommandHandler, names=["消息", "信箱", "邮件", "inbox", "mailbox"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe", "outer_plane"], help_key="inbox"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        yield router.world_social.render_inbox(user_id)
