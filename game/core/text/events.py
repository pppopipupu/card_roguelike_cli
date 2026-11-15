from typing import Any

import msgspec


class TextNode(msgspec.Struct, tag=True):
    section: str = "body"


class LocaleText(TextNode, tag="locale"):
    key: str = ""
    params: dict[str, Any] = msgspec.field(default_factory=dict)


class RenderedText(TextNode, tag="rendered"):
    text: str = ""


class ScreenText(TextNode, tag="screen"):
    screen: str = "screen"
    scene: list[LocaleText] = msgspec.field(default_factory=list)
    notice: list[LocaleText] = msgspec.field(default_factory=list)


TextDocument = list[LocaleText | RenderedText | ScreenText]
