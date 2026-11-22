from typing import Generator

from ...base import CommandHandler
from .....data.text.locale_data import get_locale_text
from .....data.world.outer_plane_config import OUTER_PLANE_ACTIVE_FLAG
from ....social.player_inspect import PlayerInspectService
from ....text.pipeline import render_text_node


class OuterPlaneTouchCommand(CommandHandler, names=["touch", "tch", "摸", "触摸", "调查", "inspect"], allowed_states=["outer_plane"], help_key="world_touch"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        if not stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG):
            yield get_locale_text("i18n_outer_plane.ui.not_in_outer_plane")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        if not query:
            yield get_locale_text("i18n_trade.status_need_target")
            return
        node = PlayerInspectService(router.save_manager, router.world_social).touch_target(user_id, query)
        if node is None:
            yield get_locale_text("i18n_trade.err_target_not_here", query=query)
            return
        yield render_text_node(node)
