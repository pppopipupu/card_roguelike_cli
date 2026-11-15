from typing import Callable, Dict, Optional

from ...data.locale_data import get_locale_text
from ...data.text_layout_data import TEXT_LAYOUTS
from .events import JoinedText, LocaleText, RenderedText, ScreenText, TextDocument, TextNode, coerce_text_node

ScreenRenderer = Callable[[str, str], str]


def _render_param(value, screens: Dict[str, ScreenRenderer], layout: dict):
    value = coerce_text_node(value)
    if isinstance(value, TextNode):
        return _render_node(value, screens, layout)
    return value


def _render_node(node: TextNode, screens: Dict[str, ScreenRenderer], layout: dict) -> str:
    if isinstance(node, LocaleText):
        params = {
            key: _render_param(value, screens, layout)
            for key, value in node.params.items()
        }
        return get_locale_text(node.key, **params)
    if isinstance(node, RenderedText):
        return node.text
    if isinstance(node, JoinedText):
        return node.separator.join(
            text for text in (_render_node(item, screens, layout) for item in node.parts) if text
        )
    if isinstance(node, ScreenText):
        screen_layout = layout.get("screen", {})
        scene_separator = screen_layout.get("scene_separator", "\n\n")
        notice_separator = screen_layout.get("notice_separator", "\n")
        scene = scene_separator.join(
            text for text in (_render_node(item, screens, layout) for item in node.scene) if text
        )
        notice = notice_separator.join(
            text for text in (_render_node(item, screens, layout) for item in node.notice) if text
        )
        renderer = screens.get(node.screen)
        if renderer is None:
            raise KeyError(f"text screen renderer missing: {node.screen}")
        return renderer(scene, notice)
    raise TypeError(type(node).__name__)


def render_text_node(node: TextNode | str) -> str:
    if isinstance(node, str):
        return node
    return _render_node(node, {}, {})


def render_text(document: TextDocument, layout_name: str, screens: Optional[Dict[str, ScreenRenderer]] = None) -> str:
    layout = TEXT_LAYOUTS[layout_name]
    sections = layout["sections"]
    renderers = screens or {}
    grouped: Dict[str, list[str]] = {}
    for node in document:
        text = _render_node(node, renderers, layout)
        if text:
            grouped.setdefault(node.section, []).append(text)
    blocks = []
    for section, texts in sorted(grouped.items(), key=lambda item: sections.get(item[0], {}).get("order", 100)):
        section_layout = sections.get(section, {})
        separator = section_layout.get("separator", "\n\n")
        blocks.append(separator.join(texts))
    return layout["separator"].join(blocks)
