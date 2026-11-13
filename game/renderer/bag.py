from typing import Dict, Any, Optional
from ..models.state import UserStats, GameRun
from ..entities import ALL_CARDS
from ..data.locale_data import get_locale_text
from ..data.potion_data import POTION_SLOT_LIMIT, get_potion_desc, get_potion_name
from ..core.inventory.bag_service import (
    get_bag_max_weight,
    get_bag_weight,
    get_item_desc,
    get_item_display_name,
    get_item_weight,
    is_item_carryover,
)


def _load_zh_cn() -> Dict[str, Any]:
    from ..core.i18n.locale_manager import LocaleManager
    return LocaleManager.get_all_translations()


def render_bag(stats: UserStats, run: Optional[GameRun] = None, mode: Optional[str] = None) -> str:
    zh_cn = _load_zh_cn()
    items_loc = zh_cn.get("items", {})
    item_descs = zh_cn.get("item_descs", {})
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
        potions = list(getattr(p, "potions", None) or [])
        lines.append(get_locale_text("i18n_room_interact.bag.rogue_weight_line", used=used, max=mx))
        lines.append("")
        lines.append(get_locale_text("i18n_room_interact.bag.rogue_potion_section", count=len(potions), limit=POTION_SLOT_LIMIT))
        if potions:
            for idx, pid in enumerate(potions, 1):
                lines.append(get_locale_text(
                    "i18n_room_interact.bag.rogue_potion_line",
                    idx=idx,
                    name=get_potion_name(pid),
                    desc=get_potion_desc(pid),
                ))
        else:
            lines.append(get_locale_text("i18n_room_interact.bag.rogue_potion_empty"))
        lines.append("")
        lines.append(get_locale_text("i18n_room_interact.bag.rogue_items_section"))
        bag_items = list(getattr(p, "bag_items", None) or [])
        if bag_items:
            for item_id in bag_items:
                carry_tag = get_locale_text("i18n_room_interact.bag.carry_yes") if is_item_carryover(item_id) else get_locale_text("i18n_room_interact.bag.carry_no")
                lines.append(get_locale_text(
                    "i18n_room_interact.bag.rogue_item_line",
                    name=get_item_display_name(item_id),
                    weight=get_item_weight(item_id),
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
    if stats.town_inventory:
        for item_id in stats.town_inventory:
            if item_id in items_loc:
                ch_name = items_loc.get(item_id, [item_id])[0]
                desc = item_descs.get(item_id, get_locale_text("renderer_menu.bag_default_item_desc"))
            else:
                ch_name = get_item_display_name(item_id)
                desc = get_item_desc(item_id)
            lines.append(get_locale_text("renderer_menu.bag_item_line", name=ch_name, item_id=item_id))
            lines.append(get_locale_text("renderer_menu.bag_item_desc_line", desc=desc))
    else:
        lines.append(get_locale_text("renderer_menu.bag_empty_items"))
    lines.append("")

    town_potions = list(getattr(stats, "town_potions", []) or [])
    lines.append(get_locale_text("i18n_room_interact.bag.town_potion_section"))
    if town_potions:
        for pid in town_potions:
            lines.append(get_locale_text(
                "i18n_room_interact.bag.town_potion_line",
                name=get_potion_name(pid),
                desc=get_potion_desc(pid),
            ))
    else:
        lines.append(get_locale_text("i18n_room_interact.bag.town_potion_empty"))
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
