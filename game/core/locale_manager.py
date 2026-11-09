import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

_ROOT_MERGE_FILES = ("global.json", "explore.json")


class LocaleManager:
    _data: Dict[str, Any] = {}
    _current_lang: str = "zh_cn"
    _loaded: bool = False

    @classmethod
    def load_locale(cls, lang: str = "zh_cn") -> None:
        cls._current_lang = lang
        cls._data = {}

        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        locale_dir = os.path.join(current_dir, "data", "locale", lang)

        if not os.path.exists(locale_dir):
            return

        try:
            names = sorted(os.listdir(locale_dir))
        except OSError as exc:
            logger.warning("locale directory read failed %s: %s", locale_dir, exc)
            return

        for name in names:
            if not name.endswith(".json"):
                continue
            path = os.path.join(locale_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                logger.warning("locale file read failed %s: %s", path, exc)
                continue
            if not isinstance(payload, dict):
                logger.warning("locale payload is not an object %s", path)
                continue
            if name in _ROOT_MERGE_FILES:
                cls._data.update(payload)
            elif name == "npcs.json":
                cls._data["interactive_entities"] = payload
            else:
                cls._data[os.path.splitext(name)[0]] = payload

        cls._loaded = True

    @classmethod
    def get_text(cls, key: str, default: str = "", **kwargs: Any) -> str:
        if not cls._loaded:
            cls.load_locale(cls._current_lang)

        current: Any = cls._data
        for part in key.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                current = None
                break

        if current is None:
            return default if default else key

        if isinstance(current, str):
            try:
                return current.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return current
        return str(current)

    @classmethod
    def get_all_translations(cls) -> Dict[str, Any]:
        if not cls._loaded:
            cls.load_locale(cls._current_lang)
        return cls._data


def t(key: str, default: str = "", **kwargs: Any) -> str:
    return LocaleManager.get_text(key, default, **kwargs)
