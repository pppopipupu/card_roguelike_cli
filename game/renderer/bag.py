import os
import json
from typing import Dict, Any
from ..models.state import UserStats
from ..entities import ALL_CARDS
from ..data.locale_data import get_locale_text

def _load_zh_cn() -> Dict[str, Any]:
    from ..core.locale_manager import LocaleManager
    return LocaleManager.get_all_translations()

def render_bag(stats: UserStats) -> str:
    zh_cn = _load_zh_cn()
    items_loc = zh_cn.get("items", {})
    item_descs = zh_cn.get("item_descs", {})
    
    lines = [
        get_locale_text("renderer_menu.separator_long"),
        get_locale_text("renderer_menu.bag_title"),
        get_locale_text("renderer_menu.separator_long"),
        get_locale_text("renderer_menu.bag_gp", gp=stats.gp),
        ""
    ]
    
    lines.append(get_locale_text("renderer_menu.bag_items_section"))
    if stats.town_inventory:
        for item_id in stats.town_inventory:
            ch_name = items_loc.get(item_id, [item_id])[0]
            desc = item_descs.get(item_id, get_locale_text("renderer_menu.bag_default_item_desc"))
            lines.append(get_locale_text("renderer_menu.bag_item_line", name=ch_name, item_id=item_id))
            lines.append(get_locale_text("renderer_menu.bag_item_desc_line", desc=desc))
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
    lines.append(get_locale_text("renderer_menu.bag_tip"))
    lines.append(get_locale_text("renderer_menu.separator_long"))
    
    return "\n".join(lines)
