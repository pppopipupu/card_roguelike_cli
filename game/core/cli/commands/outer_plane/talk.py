from typing import Generator

from ...base import CommandHandler
from .....data.locale_data import get_locale_text
from .....data.outer_plane_config import OUTER_PLANE_ACTIVE_FLAG, OUTER_PLANE_ROOM_KEY, OUTER_PLANE_START_ROOM
from .....data.world_social_config import WORLD_OUTER_PLANE


class OuterPlaneTalkCommand(CommandHandler, names=["talk", "对话", "交谈", "talk_to", "interact", "inter"], allowed_states=["outer_plane"], help_key="world_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        if not stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG):
            yield get_locale_text("i18n_outer_plane.ui.not_in_outer_plane")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        room = str(stats.town_flags.get(OUTER_PLANE_ROOM_KEY) or OUTER_PLANE_START_ROOM)
        yield router.world_social.say_to_world(user_id, WORLD_OUTER_PLANE, room, query)
