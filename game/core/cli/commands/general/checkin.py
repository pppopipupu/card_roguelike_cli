from typing import Generator
from ...base import CommandHandler


class CheckinCommand(CommandHandler, names=["签到", "checkin", "check_in", "qd", "每日签到"], allowed_states=["menu", "town", "explore", "battle", "dialog", "cafe"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        choice = " ".join(parts[1:]).strip() if len(parts) > 1 else None
        yield router.checkin_service.claim(user_id, choice)
