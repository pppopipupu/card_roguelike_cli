from typing import Any

from ..core.locale_manager import LocaleManager


def get_locale_text(key: str, default: str = "", **kwargs: Any) -> str:
    return LocaleManager.get_text(key, default, **kwargs)


def get_locale_raw(key: str, default: Any = None) -> Any:
    return LocaleManager.get_raw(key, default)

t = get_locale_text
