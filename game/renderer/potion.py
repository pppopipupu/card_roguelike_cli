from ..models.state import GameRun
from ..data.locale_data import get_locale_text
from ..data.potion_data import get_potion_drink_text, get_potion_name, get_potion_throw_text, get_potion_weight
from ..core.inventory.bag_service import format_weight, get_bag_max_weight, get_bag_weight, get_item_rarity_label, get_player_potions


def render_potion_list(run: GameRun) -> str:
    player = run.player
    potions = get_player_potions(player)
    separator = get_locale_text("renderer_menu.separator_long")
    lines = [
        separator,
        get_locale_text(
            "i18n_cli_general_a.potion.list_title",
            count=len(potions),
            used=format_weight(get_bag_weight(player)),
            max=get_bag_max_weight(player),
        ),
        ""
    ]
    if not potions:
        lines.append(get_locale_text("i18n_cli_general_a.potion.list_empty"))
    for idx, (_, potion_id) in enumerate(potions, 1):
        lines.append(get_locale_text(
            "i18n_cli_general_a.potion.list_entry",
            idx=idx,
            name=get_potion_name(potion_id),
            rarity=get_item_rarity_label(f"potion:{potion_id}"),
            weight=format_weight(get_potion_weight(potion_id)),
        ))
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
