from typing import Generator

from ....text.pipeline import render_text_node
from ...base import CommandHandler


class TradeCommand(CommandHandler, names=["trade", "tr", "交易"], allowed_states=["menu", "town", "dialog", "grid_map", "explore", "outer_plane"], help_key="trade"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        yield render_text_node(router.trade_service.handle(user_id, parts))
