from ..models.state import GameRun
from ..data.locale_data import get_locale_text
from ..data.potion_data import POTION_SLOT_LIMIT, get_potion_drink_text, get_potion_name, get_potion_throw_text


def render_potion_list(run: GameRun) -> str:
    player = run.player
    potions = list(getattr(player, "potions", None) or [])
    separator = get_locale_text("renderer_menu.separator_long")
    lines = [
        separator,
        get_locale_text("i18n_cli_general_a.potion.list_title", count=len(potions), limit=POTION_SLOT_LIMIT),
        ""
    ]
    if not potions:
        lines.append(get_locale_text("i18n_cli_general_a.potion.list_empty"))
    for idx, potion_id in enumerate(potions, 1):
        lines.append(get_locale_text("i18n_cli_general_a.potion.list_entry", idx=idx, name=get_potion_name(potion_id)))
        drink_text = get_potion_drink_text(potion_id)
        throw_text = get_potion_throw_text(potion_id)
        if drink_text:
            lines.append(get_locale_text("i18n_cli_general_a.potion.list_drink", desc=drink_text))
        if throw_text:
            lines.append(get_locale_text("i18n_cli_general_a.potion.list_throw", desc=throw_text))
    lines.append("")
    lines.append(get_locale_text("i18n_cli_general_a.potion.list_hint"))
    lines.append(separator)
    return "\n".join(lines)
