from typing import Generator

from ...base import CommandHandler


class RenameCommand(CommandHandler, names=["rename", "改名", "昵称"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe"], help_key="rename"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        text = " ".join(parts[1:]).strip()
        yield router.social_service.friend_name(user_id, text)
