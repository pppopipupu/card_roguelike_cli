from typing import Dict, List, Tuple
from ..data.locale_data import get_locale_text
from ..data.command_data import GAME_STATE_ORDER


def _state_text(states: List[str]) -> str:
    ordered = [state for state in GAME_STATE_ORDER if state in states]
    ordered.extend([state for state in states if state not in GAME_STATE_ORDER])
    separator = get_locale_text("i18n_help.state_sep")
    labels = []
    for state in ordered:
        state_key = "i18n_help.state_" + state
        labels.append(get_locale_text(state_key))
    return separator.join(labels)


def render_help_index(sections: List[Tuple[str, List[Dict]]]) -> str:
    separator = get_locale_text("renderer_menu.separator_long")
    lines = [
        separator,
        get_locale_text("i18n_help.index_title"),
        "",
        get_locale_text("i18n_help.index_intro"),
        ""
    ]
    for section_id, entries in sections:
        section_key = "i18n_help.section_" + section_id
        lines.append(get_locale_text(section_key))
        for entry in entries:
            lines.append(get_locale_text("i18n_help.index_entry", usage=entry["usage"], brief=entry["brief"]))
        lines.append("")
    lines.append(get_locale_text("i18n_help.index_footer"))
    lines.append(separator)
    return "\n".join(lines)


def render_help_detail(entry: Dict) -> str:
    separator = get_locale_text("renderer_menu.separator_long")
    alias_separator = get_locale_text("i18n_help.alias_sep")
    lines = [
        separator,
        get_locale_text("i18n_help.detail_header", name=entry["name"]),
        get_locale_text("i18n_help.usage_label", usage=entry["usage"]),
        get_locale_text("i18n_help.alias_label", aliases=alias_separator.join(entry["aliases"])),
        get_locale_text("i18n_help.state_label", states=_state_text(entry["states"])),
        get_locale_text("i18n_help.desc_label"),
        entry["desc"]
    ]
    if entry.get("example"):
        lines.append(get_locale_text("i18n_help.example_label", example=entry["example"]))
    lines.append(separator)
    return "\n".join(lines)
