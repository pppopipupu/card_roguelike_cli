from ..core.inventory.item_lore import query_item_lore
from ..data.locale_data import get_locale_text


def render_item_lore(query, stats=None, run=None):
    result = query_item_lore(query, stats, run)
    if not result:
        return None
    item_id, view = result
    lines = [
        get_locale_text("i18n_item_lore.title", name=view.name, id=item_id),
        get_locale_text("i18n_item_lore.weight_line", weight=view.weight, carry_tag=view.carry_tag),
    ]
    if view.intro:
        lines.append(get_locale_text("i18n_item_lore.intro_line", intro=view.intro))
    if view.detail:
        lines.append(view.detail)
    lines.append("")
    return "\n".join(lines)
