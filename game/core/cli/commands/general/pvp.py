from typing import Generator

from ...base import CommandHandler
from ....battle.pvp_service import PvpService


class PvpCommand(
    CommandHandler,
    names=["pvp", "切磋开关", "决斗开关"],
    allowed_states=["menu", "town", "grid_map", "explore", "cafe", "outer_plane"],
):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        arg = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        yield PvpService.toggle_pvp(router.save_manager, user_id, arg)
