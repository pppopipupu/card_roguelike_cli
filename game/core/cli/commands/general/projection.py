from typing import Generator

from ...base import CommandHandler
from .....data.locale_data import get_locale_text


class ProjectionCommand(CommandHandler, names=["projection", "投影", "pj"], allowed_states=["menu", "town", "explore", "battle", "dialog", "cafe"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        if len(parts) == 1:
            stats.projection_enabled = not stats.projection_enabled
            if not stats.projection_enabled:
                stats.projection_feed = []
            router.save_manager.save_stats(user_id, stats)
            key = "i18n_projection.enabled" if stats.projection_enabled else "i18n_projection.disabled"
            yield get_locale_text(key)
            return
        value = parts[1].strip().lower()
        if value in ("on", "enable", "open", "开启", "开"):
            stats.projection_enabled = True
            router.save_manager.save_stats(user_id, stats)
            yield get_locale_text("i18n_projection.enabled")
            return
        if value in ("off", "disable", "close", "关闭", "关"):
            stats.projection_enabled = False
            stats.projection_feed = []
            router.save_manager.save_stats(user_id, stats)
            yield get_locale_text("i18n_projection.disabled")
            return
        if value in ("status", "state", "状态"):
            key = "i18n_projection.status_on" if stats.projection_enabled else "i18n_projection.status_off"
            yield get_locale_text(key)
            return
        if value in ("help", "用法", "帮助"):
            yield get_locale_text("i18n_projection.usage")
            return
        yield get_locale_text("i18n_projection.unknown")
