from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class MapStyleCommand(CommandHandler, names=["地图", "map"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        if not stats.in_town:
            yield get_locale_text("i18n_cli_commands.town_map_style_not_in_town")
            return
        current_style = stats.town_flags.get("map_style", "classic")
        target_style = None
        if len(parts) > 1:
            arg = parts[1].lower()
            if arg in ("经典", "classic", "c"):
                target_style = "classic"
            elif arg in ("雷达", "radar", "r"):
                target_style = "radar"
            else:
                yield get_locale_text("i18n_cli_commands.town_map_style_invalid")
                return
        else:
            target_style = "radar" if current_style == "classic" else "classic"
        stats.town_flags["map_style"] = target_style
        router.save_manager.save_stats(user_id, stats)
        style_desc = get_locale_text("i18n_cli_commands.town_map_style_desc_classic") if target_style == "classic" else get_locale_text("i18n_cli_commands.town_map_style_desc_radar")
        yield get_locale_text("i18n_cli_commands.town_map_style_switched", style_desc=style_desc) + router.town_engine.render_current_room(user_id, stats)
