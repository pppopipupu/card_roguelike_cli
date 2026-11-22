import os
import logging
from typing import Dict, Any
from ...json_codec import load

logger = logging.getLogger(__name__)

_NPC_FILE_NAME = "npcs.json"


class LocaleManager:
    _data: Dict[str, Any] = {}
    _current_lang: str = "zh_cn"
    _loaded: bool = False

    @classmethod
    def load_locale(cls, lang: str = "zh_cn") -> None:
        cls._current_lang = lang
        cls._data = {}

        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        locale_dir = os.path.join(current_dir, "data", "locale", lang)

        if not os.path.exists(locale_dir):
            return

        try:
            os.listdir(locale_dir)
        except OSError as exc:
            logger.warning("locale directory read failed %s: %s", locale_dir, exc)
            return

        seen_stems = set()
        for dirpath, dirnames, filenames in os.walk(locale_dir):
            dirnames[:] = sorted(
                (name for name in dirnames if name != "__pycache__"),
                key=lambda name: (name != "_root", name),
            )
            filenames.sort()

            relative = os.path.relpath(dirpath, locale_dir)
            if relative == ".":
                for name in filenames:
                    logger.warning("locale entry in locale root, skipped %s", os.path.join(dirpath, name))
                continue

            merge_to_root = relative.split(os.sep)[0] == "_root"
            for name in filenames:
                path = os.path.join(dirpath, name)
                if not name.endswith(".json"):
                    logger.warning("locale entry is not JSON, skipped %s", path)
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        payload = load(f)
                except (OSError, ValueError, TypeError) as exc:
                    logger.warning("locale file read failed %s: %s", path, exc)
                    continue
                if not isinstance(payload, dict):
                    logger.warning("locale payload is not an object %s", path)
                    continue

                if name == _NPC_FILE_NAME:
                    if "interactive_entities" in cls._data:
                        logger.warning("duplicate npcs file ignored %s", path)
                        continue
                    cls._data["interactive_entities"] = payload
                elif merge_to_root:
                    cls._data.update(payload)
                else:
                    stem = os.path.splitext(name)[0]
                    if stem in seen_stems:
                        logger.warning("duplicate locale namespace %s ignored %s", stem, path)
                        continue
                    seen_stems.add(stem)
                    cls._data[stem] = payload

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
    def get_raw(cls, key: str, default: Any = None) -> Any:
        if not cls._loaded:
            cls.load_locale(cls._current_lang)

        current: Any = cls._data
        for part in key.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    @classmethod
    def get_all_translations(cls) -> Dict[str, Any]:
        if not cls._loaded:
            cls.load_locale(cls._current_lang)
        return cls._data


def t(key: str, default: str = "", **kwargs: Any) -> str:
    return LocaleManager.get_text(key, default, **kwargs)
