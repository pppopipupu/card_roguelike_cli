import os
import json
from typing import List, Dict, Any
from ..models.state import UserStats
from ..entities import ALL_CARDS
from ..entities.cards.market import MARKET_SHELF_CARDS, get_market_price

def _load_zh_cn() -> Dict[str, Any]:
    from ..core.locale_manager import LocaleManager
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
    
    lines = ["🗺️ 【先古主城地图】"]
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
    lines.append("📖 【主城地标图例手册】 ( 📍 标识当前所在位置 )")
    
    def get_leg(rid: str, default_name: str) -> str:
        emo = "📍" if rid == current_id else emoji_map.get(rid, "🧱")
        return f"{emo} {default_name}"
        
    lines.append(f"{get_leg('watch_tower', '守卫哨塔')}　　{get_leg('west_gate', '西大门')}　　　{get_leg('range', '训练靶场')}")
    lines.append(f"{get_leg('alley', '偏僻小巷')}　　{get_leg('square', '中心广场')}　　{get_leg('fountain', '许愿喷泉')}")
    lines.append(f"{get_leg('shop', '主城商店')}　　{get_leg('tavern', '酒馆大堂')}　　{get_leg('vip_room', '酒馆雅间')}")
    lines.append(f"{get_leg('blacksmith', '铁匠铺')}　　　{get_leg('market', '卡牌大卖场')}　　🧱 墙壁障碍")
    
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
    room_name = room_loc.get("name", zh_cn.get("global", {}).get("unknown_room", "未知房间"))
    desc = room_loc.get("desc", "")

    title = zh_cn.get("global", {}).get("title_format", "✨ 先古主城 ── {name} ✨").format(name=room_name)

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

    none_label = zh_cn.get("global", {}).get("none", "无")
    npc_str = "、".join(visible_npcs) if visible_npcs else none_label

    items_loc = zh_cn.get("items", {})
    visible_items = []
    for item_id in room_data.get("items", []):
        if not stats.town_flags.get(f"taken_{item_id}", 0):
            item_name = items_loc.get(item_id, [item_id])[0]
            visible_items.append(item_name)
    
    if current_id == "vip_room" and not stats.town_flags.get("box_opened", 0):
        chest_name = entities_loc.get("Chest", {}).get("name", "古老的铁宝箱")
        visible_items.append(chest_name)
    
    item_str = "、".join(visible_items) if visible_items else none_label

    exits_dict = room_data.get("exits", {})
    dir_names = zh_cn.get("global", {}).get("directions", {"w": "北", "s": "南", "a": "西", "d": "东"})
    exit_list = []
    for d, target in exits_dict.items():
        if d in dir_names:
            exit_list.append(f"{dir_names[d]}({d.upper()})")
    exit_str = "、".join(exit_list) if exit_list else none_label

    if current_id == "market":
        shelf = stats.town_flags.get("market_shelf", [])
        if not shelf or len(shelf) != len(MARKET_SHELF_CARDS):
            already_bought = set(getattr(stats, "purchased_pool", []) or []) | set(getattr(stats, "unlocked_new_cards", []) or [])
            shelf = [c if c not in already_bought else "" for c in MARKET_SHELF_CARDS]
            stats.town_flags["market_shelf"] = shelf
        
        shelf_strs = []
        for idx, cid in enumerate(shelf):
            if not cid:
                shelf_strs.append(f"{idx+1}. " + zh_cn.get("global", {}).get("market_sold_out", "【已售罄】"))
            else:
                c_name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
                card_obj = ALL_CARDS.get(cid)
                rarity_str = "普通"
                if card_obj:
                    r = getattr(card_obj, "rarity", "common")
                    if r == "common":
                        rarity_str = "普通"
                    elif r == "rare":
                        rarity_str = "稀有"
                    else:
                        rarity_str = "珍奇"
                price = get_market_price(cid, card_obj)
                shelf_strs.append(f"{idx+1}. 【{c_name}】({rarity_str} ─ {price} GP)")
        desc += zh_cn.get("global", {}).get("market_shelf_header", "\n\n🏷️ 今日货架商品：\n") + "\n".join(shelf_strs)
        desc += zh_cn.get("global", {}).get("market_shelf_footer", "\n（输入 交互/talk 卡牌商人 即可开启选购或锁定必带卡）")

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
    inv_str = "、".join(inv_display) if inv_display else zh_cn.get("global", {}).get("empty", "空")

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        title,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        map_str,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        zh_cn.get("global", {}).get("room_env", "环境：{desc}").format(desc=desc),
        zh_cn.get("global", {}).get("room_exits", "出口：{exits}").format(exits=exit_str),
        zh_cn.get("global", {}).get("room_npcs", "居民：{npcs}").format(npcs=npc_str),
        zh_cn.get("global", {}).get("room_items", "物品：{items}").format(items=item_str),
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        zh_cn.get("global", {}).get("room_inventory", "🎒 随身物品：{inv} | 💰 拥有 GP：{gp}").format(inv=inv_str, gp=stats.gp),
        quest_str,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        zh_cn.get("global", {}).get("help_move", "💡 移动 (MOVE)：W(北/UP) / A(西/LEFT) / S(南/DOWN) / D(东/RIGHT)"),
        zh_cn.get("global", {}).get("help_take", "💡 拿取 (TAKE)：拿取/捡起/take/pick <物品>"),
        zh_cn.get("global", {}).get("help_use", "💡 使用 (USE)：使用/use <物品>"),
        zh_cn.get("global", {}).get("help_talk", "💡 交互 (TALK)：交互/talk/interact/talk_to <名字>"),
        zh_cn.get("global", {}).get("help_system", "💡 系统 (SYSTEM)：退出/exit/quit | 回城/home"),
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    return "\n".join(lines)
