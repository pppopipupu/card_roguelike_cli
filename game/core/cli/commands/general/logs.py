from typing import Generator

from ...base import CommandHandler
from ....telemetry.log_service import parse_log_limit


class LogsCommand(CommandHandler, names=["logs", "日志"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe"], help_key="logs"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        limit, error = parse_log_limit(parts)
        if error:
            yield error
            return
        yield router.log_service.render(user_id, limit, team=False)


class LogcCommand(CommandHandler, names=["logc", "团队日志", "队伍日志"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe"], help_key="logc"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        limit, error = parse_log_limit(parts)
        if error:
            yield error
            return
        yield router.log_service.render(user_id, limit, team=True)
