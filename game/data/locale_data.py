from typing import Any

from ..core.locale_manager import LocaleManager


def get_locale_text(key: str, default: str = "", **kwargs: Any) -> str:
    return LocaleManager.get_text(key, default, **kwargs)


t = get_locale_text
