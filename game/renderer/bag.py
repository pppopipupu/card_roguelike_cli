from typing import Optional
from ..models.state import UserStats, GameRun
from ..entities import ALL_CARDS
from ..data.locale_data import get_locale_text
from ..core.inventory.bag_service import (
    format_weight,
    get_bag_max_weight,
    get_bag_weight,
    get_item_desc,
    get_item_display_name,
    get_item_rarity_label,
    get_item_weight,
    is_item_carryover,
)


def render_bag(stats: UserStats, run: Optional[GameRun] = None, mode: Optional[str] = None) -> str:
    active_mode = mode or ("r" if (run is not None and run.player is not None) else "t")

    if active_mode == "r":
        lines = [
            get_locale_text("renderer_menu.separator_long"),
            get_locale_text("i18n_room_interact.bag.rogue_bag_title"),
            get_locale_text("renderer_menu.separator_long"),
        ]
        if run is None or run.player is None:
            lines.append(get_locale_text("i18n_room_interact.bag.rogue_bag_no_run"))
            lines.append(get_locale_text("renderer_menu.separator_long"))
            return "\n".join(lines)
        p = run.player
        used = get_bag_weight(p)
        mx = get_bag_max_weight(p)
        lines.append(get_locale_text("i18n_room_interact.bag.rogue_weight_line", used=format_weight(used), max=mx))
        lines.append("")
        lines.append(get_locale_text("i18n_room_interact.bag.rogue_items_section"))
        bag_items = list(getattr(p, "bag_items", None) or [])
        if bag_items:
            for item_id in bag_items:
                carry_tag = get_locale_text("i18n_room_interact.bag.carry_yes") if is_item_carryover(item_id) else get_locale_text("i18n_room_interact.bag.carry_no")
                lines.append(get_locale_text(
                    "i18n_room_interact.bag.rogue_item_line",
                    name=get_item_display_name(item_id),
                    rarity=get_item_rarity_label(item_id),
                    weight=format_weight(get_item_weight(item_id)),
                    carry_tag=carry_tag,
                    desc=get_item_desc(item_id),
                ))
        else:
            lines.append(get_locale_text("i18n_room_interact.bag.rogue_items_empty"))
        lines.append(get_locale_text("renderer_menu.separator_long"))
        lines.append(get_locale_text("i18n_room_interact.bag.rogue_bag_tip"))
        lines.append(get_locale_text("renderer_menu.separator_long"))
        return "\n".join(lines)

    lines = [
        get_locale_text("renderer_menu.separator_long"),
        get_locale_text("i18n_room_interact.bag.town_bag_title"),
        get_locale_text("renderer_menu.separator_long"),
        get_locale_text("renderer_menu.bag_gp", gp=stats.gp),
        get_locale_text("i18n_room_interact.bag.town_infinite_badge"),
        "",
    ]
    lines.append(get_locale_text("renderer_menu.bag_items_section"))
    town_inventory = list(getattr(stats, "town_inventory", []) or [])
    if town_inventory:
        item_counts: dict[str, int] = {}
        for item_id in town_inventory:
            item_counts[item_id] = item_counts.get(item_id, 0) + 1
        for item_id, count in item_counts.items():
            rarity_label = get_item_rarity_label(item_id)
            if count > 1:
                lines.append(get_locale_text("renderer_menu.bag_item_stacked_line", name=get_item_display_name(item_id), rarity=rarity_label, count=count))
            else:
                lines.append(get_locale_text("renderer_menu.bag_item_line", name=get_item_display_name(item_id), rarity=rarity_label))
            lines.append(get_locale_text("renderer_menu.bag_item_desc_line", desc=get_item_desc(item_id)))
    else:
        lines.append(get_locale_text("renderer_menu.bag_empty_items"))
    lines.append("")

    lines.append(get_locale_text("renderer_menu.bag_custom_section"))
    locked_list = getattr(stats, "locked_cards", []) or []
    p_pool = getattr(stats, "purchased_pool", [])

    has_custom = False
    if locked_list:
        has_custom = True
        locked_names = get_locale_text("renderer_menu.list_separator").join([get_locale_text("renderer_menu.card_name_bracket", name=ALL_CARDS[cid].name) if cid in ALL_CARDS else cid for cid in locked_list])
        lines.append(get_locale_text("renderer_menu.bag_locked_line", names=locked_names))
    if p_pool:
        has_custom = True
        p_names = get_locale_text("renderer_menu.list_separator").join([get_locale_text("renderer_menu.card_name_bracket", name=ALL_CARDS[cid].name) if cid in ALL_CARDS else cid for cid in p_pool])
        lines.append(get_locale_text("renderer_menu.bag_purchased_line", names=p_names))
    if not has_custom:
        lines.append(get_locale_text("renderer_menu.bag_empty_custom"))
    lines.append("")

    lines.append(get_locale_text("renderer_menu.bag_privileges_section"))
    unlocked = getattr(stats, "unlocked_subclasses", [])
    has_gatekey = getattr(stats, "unlocked_gatekey", False)

    privileges = []
    for sub in unlocked:
        privileges.append(get_locale_text("renderer_menu.bag_subclass_privilege", sub=sub))
    if has_gatekey:
        privileges.append(get_locale_text("renderer_menu.bag_gatekey_privilege"))

    if privileges:
        lines.append(get_locale_text("renderer_menu.bag_privilege_line", privileges=get_locale_text("renderer_menu.list_separator").join(privileges)))
    else:
        lines.append(get_locale_text("renderer_menu.bag_empty_privileges"))

    lines.append(get_locale_text("renderer_menu.separator_long"))
    lines.append(get_locale_text("i18n_room_interact.bag.town_bag_tip"))
    lines.append(get_locale_text("renderer_menu.separator_long"))

    return "\n".join(lines)
