import re

from ..data.checkin_data import DEFAULT_PLAYER_NAME, PLAYER_NAME_MAX_LENGTH

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_HANDLE_SUFFIX = re.compile(r"#\d+$")


class PlayerNameError(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def parse_player_name(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise PlayerNameError("empty")
    if _CONTROL.search(text):
        raise PlayerNameError("control")
    text = " ".join(text.split())
    if "#" in text:
        raise PlayerNameError("hash")
    if len(text) > PLAYER_NAME_MAX_LENGTH:
        raise PlayerNameError("too_long")
    return text


def fallback_player_name(value: str) -> str:
    text = str(value or "").strip()
    text = _CONTROL.sub("", text)
    text = text.replace("#", "＃")
    text = " ".join(text.split())
    if not text:
        return DEFAULT_PLAYER_NAME
    return text[:PLAYER_NAME_MAX_LENGTH]


def unique_handle(base: str, taken: set[str]) -> str:
    name = str(base or "").strip() or DEFAULT_PLAYER_NAME
    if name not in taken:
        return name
    root = _HANDLE_SUFFIX.sub("", name) or DEFAULT_PLAYER_NAME
    index = 2
    while f"{root}#{index}" in taken:
        index += 1
    return f"{root}#{index}"
