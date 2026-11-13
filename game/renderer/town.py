import os
import json
from typing import List, Dict, Any
from ..models.state import UserStats
from ..entities import ALL_CARDS
from ..entities.cards.market import MARKET_SHELF_CARDS, get_market_price
from ..data.locale_data import t, get_locale_text

def _load_zh_cn() -> Dict[str, Any]:
    from ..core.i18n.locale_manager import LocaleManager
    return LocaleManager.get_all_translations()

def get_display_width(s: str) -> int:
    width = 0
    for c in s:
        if ord(c) > 127:
            width += 2
        else:
            width += 1
    return width

def render_town_map_classic(current_id: str) -> str:
    emoji_map = {
        "watch_tower": "🗼",
        "west_gate": "⛩️",
        "range": "🎯",
        "alley": "🛣️",
        "square": "🏟️",
        "fountain": "⛲",
        "shop": "🏪",
        "market": "🪙",
        "tavern": "🍺",
        "vip_room": "🛋️",
        "blacksmith": "⚒️"
    }
    
    grid = [
        ["watch_tower", None, "range", None, "tavern", "vip_room"],
        ["west_gate", "alley", "square", "fountain", "shop", None],
        [None, "blacksmith", "market", None, None, None]
    ]
    
    lines = [t("renderer_town.map_title")]
    for row in grid:
        row_strs = []
        for rid in row:
            if rid is None:
                row_strs.append("🧱")
            elif rid == current_id:
                row_strs.append("📍")
            else:
                row_strs.append(emoji_map.get(rid, "🧱"))
        lines.append("".join(row_strs))
        
    lines.append("")
    lines.append(t("renderer_town.legend_title"))
    
    def get_leg(rid: str, name_key: str) -> str:
        emo = "📍" if rid == current_id else emoji_map.get(rid, "🧱")
        return f"{emo} {t(name_key)}"
        
    lines.append(t(
        "renderer_town.legend_row_1",
        watch_tower=get_leg("watch_tower", "renderer_town.room_watch_tower"),
        west_gate=get_leg("west_gate", "renderer_town.room_west_gate"),
        range=get_leg("range", "renderer_town.room_range")
    ))
    lines.append(t(
        "renderer_town.legend_row_2",
        alley=get_leg("alley", "renderer_town.room_alley"),
        square=get_leg("square", "renderer_town.room_square"),
        fountain=get_leg("fountain", "renderer_town.room_fountain")
    ))
    lines.append(t(
        "renderer_town.legend_row_3",
        shop=get_leg("shop", "renderer_town.room_shop"),
        tavern=get_leg("tavern", "renderer_town.room_tavern"),
        vip_room=get_leg("vip_room", "renderer_town.room_vip_room")
    ))
    lines.append(t(
        "renderer_town.legend_row_4",
        blacksmith=get_leg("blacksmith", "renderer_town.room_blacksmith"),
        market=get_leg("market", "renderer_town.room_market"),
        wall=t("renderer_town.legend_wall")
    ))
    
    return "\n".join(lines)

def render_town_map_radar(current_id: str, zh_cn: Dict[str, Any], room_data: Dict[str, Any]) -> str:
    exits = room_data.get("exits", {})
    rooms_loc = zh_cn.get("rooms", {})
    
    def get_room_name(rid: str) -> str:
        if not rid:
            return ""
        return rooms_loc.get(rid, {}).get("name", rid)
        
    curr_name = get_room_name(current_id)
    
    north_id = exits.get("w")
    south_id = exits.get("s")
    west_id = exits.get("a")
    east_id = exits.get("d")
    
    north_str = f"[{get_room_name(north_id)}]" if north_id else ""
    south_str = f"[{get_room_name(south_id)}]" if south_id else ""
    west_str = f"[{get_room_name(west_id)}]" if west_id else ""
    east_str = f"[{get_room_name(east_id)}]" if east_id else ""
    
    curr_str = f"📍{curr_name}"
    curr_len = get_display_width(curr_str)
    
    lines = []
    
    if north_str:
        left_prefix_len = get_display_width(west_str) + 4 if west_str else 6
        curr_center_offset = curr_len // 2
        total_offset = left_prefix_len + curr_center_offset
        
        north_len = get_display_width(north_str)
        north_start = total_offset - (north_len // 2)
        if north_start < 0:
            north_start = 0
            
        lines.append(" " * north_start + north_str)
        lines.append(" " * total_offset + "▲")
        lines.append(" " * total_offset + "│")
        
    mid_parts = []
    if west_str:
        mid_parts.append(f"{west_str} ◄─ ")
    else:
        mid_parts.append("      ")
    mid_parts.append(curr_str)
    if east_str:
        mid_parts.append(f" ─► {east_str}")
    lines.append("".join(mid_parts))
    
    if south_str:
        left_prefix_len = get_display_width(west_str) + 4 if west_str else 6
        curr_center_offset = curr_len // 2
        total_offset = left_prefix_len + curr_center_offset
        
        south_len = get_display_width(south_str)
        south_start = total_offset - (south_len // 2)
        if south_start < 0:
            south_start = 0
            
        lines.append(" " * total_offset + "│")
        lines.append(" " * total_offset + "▼")
        lines.append(" " * south_start + south_str)
        
    return "\n".join(lines)

def render_town_map(current_id: str, zh_cn: Dict[str, Any], room_data: Dict[str, Any] = None, stats: UserStats = None) -> str:
    style = "classic"
    if stats:
        style = stats.town_flags.get("map_style", "classic")
    if style == "radar" and room_data:
        return render_town_map_radar(current_id, zh_cn, room_data)
    return render_town_map_classic(current_id)

def get_npc_quest_indicator(npc_id: str, stats: UserStats) -> str:
    q_tour = stats.town_flags.get("quest_town_tour_state", "unstarted")
    q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
    q_ham = stats.town_flags.get("quest_hammer_state", "unstarted")

    if npc_id == "Guide_Elder":
        if q_tour == "unstarted":
            return " ❗"
        elif q_tour == "started":
            visited = stats.town_flags.get("quest_town_tour_visited", [])
            if len(visited) >= 11:
                return " ✔"
            else:
                return " ❓"
    elif npc_id == "Bartender_Jack":
        if q_brew == "unstarted":
            return " ❗"
        elif q_brew == "started":
            if "wishing_dew" in stats.town_inventory:
                return " ✔"
            else:
                return " ❓"
    elif npc_id == "Blacksmith_Ironclad":
        if q_ham == "unstarted":
            return " ❗"
        elif q_ham == "started":
            if "smith_hammer" in stats.town_inventory or "fake_hammer" in stats.town_inventory or stats.town_flags.get("noob_coerced_hammer"):
                return " ✔"
            else:
                return " ❓"
    elif npc_id == "Lost_Bard":
        if q_ham == "started" and not stats.town_flags.get("taken_smith_hammer") and not stats.town_flags.get("noob_coerced_hammer"):
            if "beer" in stats.town_inventory:
                return " ✔"
            else:
                return " ❓"
    elif npc_id == "Crypto_Whale":
        if not stats.town_flags.get("reported_whale"):
            need_herb = q_brew == "started" and "void_herb" not in stats.town_inventory and "wishing_dew" not in stats.town_inventory
            need_hammer = q_ham == "started" and "smith_hammer" not in stats.town_inventory and "fake_hammer" not in stats.town_inventory
            if need_herb or need_hammer:
                return " ❓"
    elif npc_id == "Town_Guard":
        need_report = q_brew == "started" and "void_herb" not in stats.town_inventory and "wishing_dew" not in stats.town_inventory and not stats.town_flags.get("reported_whale")
        if need_report:
            return " ❓"
    elif npc_id == "Fountain":
        if q_brew == "started" and "void_herb" in stats.town_inventory:
            return " ❗"
    elif npc_id == "NoobSlayer99":
        if q_ham == "started" and "smith_hammer" not in stats.town_inventory and "fake_hammer" not in stats.town_inventory and not stats.town_flags.get("noob_coerced_hammer"):
            return " ❓"
    return ""

def render_town(stats: UserStats, room_data: Dict[str, Any]) -> str:
    zh_cn = _load_zh_cn()
    current_id = stats.town_pos
    map_str = render_town_map(current_id, zh_cn, room_data, stats)

    name_key = room_data.get("name_key", current_id)
    room_loc = zh_cn.get("rooms", {}).get(name_key, {})
    room_name = room_loc.get("name", get_locale_text("global.unknown_room"))
    desc = room_loc.get("desc", "")

    title = get_locale_text("global.title_format", name=room_name)

    entities_loc = zh_cn.get("interactive_entities", {})

    visible_npcs = []
    for npc_id in room_data.get("npcs", []):
        npc_name = entities_loc.get(npc_id, {}).get("name", npc_id)
        ind = get_npc_quest_indicator(npc_id, stats)
        visible_npcs.append(f"{npc_name}{ind}")

    wandering_npcs_config = ["Gamer_Boy", "Crypto_Whale", "Lost_Bard", "Town_Guard", "Naughty_Child"]
    for npc_id in wandering_npcs_config:
        npc_pos = stats.town_flags.get(f"pos_{npc_id}", "square")
        if npc_pos == current_id:
            npc_name = entities_loc.get(npc_id, {}).get("name", npc_id)
            ind = get_npc_quest_indicator(npc_id, stats)
            visible_npcs.append(f"{npc_name}{ind}")

    none_label = get_locale_text("global.none")
    npc_str = get_locale_text("renderer_town.list_separator").join(visible_npcs) if visible_npcs else none_label

    items_loc = zh_cn.get("items", {})
    visible_items = []
    for item_id in room_data.get("items", []):
        if not stats.town_flags.get(f"taken_{item_id}", 0):
            item_name = items_loc.get(item_id, [item_id])[0]
            visible_items.append(item_name)
    
    if current_id == "vip_room" and not stats.town_flags.get("box_opened", 0):
        chest_name = entities_loc.get("Chest", {}).get("name", t("renderer_town.chest_name"))
        visible_items.append(chest_name)
    
    item_str = get_locale_text("renderer_town.list_separator").join(visible_items) if visible_items else none_label

    exits_dict = room_data.get("exits", {})
    dir_names = {d: get_locale_text(f"global.directions.{d}") for d in ("w", "s", "a", "d")}
    exit_list = []
    for d, target in exits_dict.items():
        if d in dir_names:
            exit_list.append(f"{dir_names[d]}({d.upper()})")
    exit_str = get_locale_text("renderer_town.list_separator").join(exit_list) if exit_list else none_label

    if current_id == "market":
        shelf = stats.town_flags.get("market_shelf", [])
        if not shelf or len(shelf) != len(MARKET_SHELF_CARDS):
            already_bought = set(getattr(stats, "purchased_pool", []) or []) | set(getattr(stats, "unlocked_new_cards", []) or [])
            shelf = [c if c not in already_bought else "" for c in MARKET_SHELF_CARDS]
            stats.town_flags["market_shelf"] = shelf
        
        shelf_strs = []
        for idx, cid in enumerate(shelf):
            if not cid:
                shelf_strs.append(f"{idx+1}. " + get_locale_text("global.market_sold_out"))
            else:
                c_name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
                card_obj = ALL_CARDS.get(cid)
                rarity_str = t("renderer_town.rarity_common")
                if card_obj:
                    r = getattr(card_obj, "rarity", "common")
                    if r == "common":
                        rarity_str = t("renderer_town.rarity_common")
                    elif r == "rare":
                        rarity_str = t("renderer_town.rarity_rare")
                    else:
                        rarity_str = t("renderer_town.rarity_epic")
                price = get_market_price(cid, card_obj)
                shelf_strs.append(t(
                    "renderer_town.market_shelf_item",
                    idx=idx + 1,
                    name=c_name,
                    rarity=rarity_str,
                    price=price
                ))
        desc += get_locale_text("global.market_shelf_header") + "\n".join(shelf_strs)
        desc += get_locale_text("global.market_shelf_footer")

    quest_str = ""
    quest_state = stats.town_flags.get("quest_town_tour_state", "unstarted")
    if quest_state == "started":
        visited = stats.town_flags.get("quest_town_tour_visited", [])
        if len(visited) >= 11:
            quest_str = zh_cn.get("global", {}).get("quest_tour_complete_ready", "")
        else:
            quest_str = zh_cn.get("global", {}).get("quest_tour_progress", "").format(visited=len(visited))
    elif quest_state == "completed":
        quest_str = zh_cn.get("global", {}).get("quest_tour_completed", "")
    else:
        quest_str = zh_cn.get("global", {}).get("quest_tour_none", "")

    town_inv = stats.town_inventory
    inv_display = []
    for item_id in town_inv:
        inv_display.append(items_loc.get(item_id, [item_id])[0])
    inv_str = get_locale_text("renderer_town.list_separator").join(inv_display) if inv_display else get_locale_text("global.empty")

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        title,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        map_str,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        get_locale_text("global.room_env", desc=desc),
        get_locale_text("global.room_exits", exits=exit_str),
        get_locale_text("global.room_npcs", npcs=npc_str),
        get_locale_text("global.room_items", items=item_str),
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        get_locale_text("global.room_inventory", inv=inv_str, gp=stats.gp),
        quest_str,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        get_locale_text("global.help_move"),
        get_locale_text("global.help_take"),
        get_locale_text("global.help_use"),
        get_locale_text("global.help_talk"),
        get_locale_text("global.help_system"),
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    return "\n".join(lines)
