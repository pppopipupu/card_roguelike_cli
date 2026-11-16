from collections.abc import Sequence
from typing import Any

import msgspec


class TextNode(msgspec.Struct, tag=True):
    section: str = "body"


class LocaleText(TextNode, tag="locale"):
    key: str = ""
    params: dict[str, Any] = msgspec.field(default_factory=dict)


class RenderedText(TextNode, tag="rendered"):
    text: str = ""


class JoinedText(TextNode, tag="joined"):
    parts: Sequence["TextPayload"] = msgspec.field(default_factory=list)
    separator: str = "\n"


class ScreenText(TextNode, tag="screen"):
    screen: str = "screen"
    scene: Sequence["TextPayload"] = msgspec.field(default_factory=list)
    notice: Sequence["TextPayload"] = msgspec.field(default_factory=list)


TextPayload = TextNode | LocaleText | RenderedText | JoinedText | ScreenText
TextDocument = list[TextPayload]


def locale_text(key: str, params: dict | None = None) -> LocaleText:
    return LocaleText(key=key, params=params or {})


def coerce_text_node(value: Any) -> Any:
    if isinstance(value, TextNode):
        return value
    if isinstance(value, list):
        return [coerce_text_node(item) for item in value]
    if not isinstance(value, dict):
        return value
    tag = value.get("type")
    section = value.get("section", "body")
    if tag == "locale":
        params = {
            key: coerce_text_node(item)
            for key, item in (value.get("params") or {}).items()
        }
        return LocaleText(
            section=section,
            key=value.get("key", ""),
            params=params,
        )
    if tag == "rendered":
        return RenderedText(section=section, text=value.get("text", ""))
    if tag == "joined":
        return JoinedText(
            section=section,
            parts=[coerce_text_node(item) for item in value.get("parts") or []],
            separator=value.get("separator", "\n"),
        )
    if tag == "screen":
        return ScreenText(
            section=section,
            screen=value.get("screen", "screen"),
            scene=[coerce_text_node(item) for item in value.get("scene") or []],
            notice=[coerce_text_node(item) for item in value.get("notice") or []],
        )
    return value

