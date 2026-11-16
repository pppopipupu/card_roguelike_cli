from typing import Generator

from ...base import CommandHandler
from .....data.locale_data import get_locale_text


def current_world(router, user_id: str) -> tuple[str, str] | None:
    return router.world_social.presence.resolve_location(user_id)


class WorldSayCommand(CommandHandler, names=["说", "say", "发言"], allowed_states=["town", "dialog", "grid_map", "explore", "battle", "cafe", "outer_plane"], help_key="world_say"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        service = router.world_social
        text = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        location = current_world(router, user_id)
        if location is None:
            yield get_locale_text("i18n_world_social.dialog.no_world")
            return
        yield service.say_to_world(user_id, location[0], location[1], text)
