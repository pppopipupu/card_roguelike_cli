import os
from typing import List, Dict, Any
from ..models.state import UserStats, get_user_id
from ..core.world.presence import render_players
from ..data.world_social_config import WORLD_PLAYER_ICON, WORLD_TOWN
from ..entities import ALL_CARDS
from ..entities.cards.market import MARKET_SHELF_CARDS, get_market_price
from ..data.locale_data import t, get_locale_text
from ..data.balance_config import TOWN_INVENTORY_FOLD_THRESHOLD
from ..data.room_interact_data import BAG_DEFAULT_MAX_WEIGHT
from ..core.inventory.bag_service import calc_bag_items_weight, get_item_display_name
from ..core.world.open_world.loadout_service import OpenWorldLoadoutService

def _load_zh_cn() -> Dict[str, Any]:
    from ..core.i18n.locale_manager import LocaleManager
    return LocaleManager.get_all_translations()

def render_town_map(stats: UserStats, current_id: str) -> str:
    from ..data.town_map_config import (
        TOWN_EMPTY_ICON,
        TOWN_ICON_ORDER,
        TOWN_MAP_HEIGHT,
        TOWN_MAP_WIDTH,
        TOWN_PLAYER_ICON,
        TOWN_ROOM_COORDS,
        TOWN_ROOM_ICONS,
        TOWN_UNKNOWN_ICON,
    )
    from .world_grid import render_grid_view

    coord = TOWN_ROOM_COORDS.get(current_id, "C2")
    coord_rooms = {c: rid for rid, c in TOWN_ROOM_COORDS.items()}
    visited = set(stats.town_flags.get("visited_rooms") or [])
    visited.add(current_id)

    def icon_for(cell: str) -> str:
        rid = coord_rooms.get(cell)
        if rid is None:
            return TOWN_EMPTY_ICON
        if rid == current_id:
            return TOWN_PLAYER_ICON
        if rid not in visited:
            return TOWN_UNKNOWN_ICON
        return TOWN_ROOM_ICONS.get(rid, TOWN_UNKNOWN_ICON)

    grid_lines, seen = render_grid_view(
        TOWN_MAP_WIDTH,
        TOWN_MAP_HEIGHT,
        coord,
        icon_for,
        show_viewport=False,
    )
    lines = [get_locale_text("i18n_world_grid.town_title", coord=coord)]
    lines.extend(grid_lines)
    legend_parts = []
    for rid in TOWN_ICON_ORDER:
        icon = TOWN_PLAYER_ICON if rid == current_id else TOWN_ROOM_ICONS[rid]
        if rid not in visited:
            continue
        name = get_locale_text(f"rooms.{rid}.name")
        legend_parts.append(f"{icon}{name}")
    if TOWN_UNKNOWN_ICON in seen:
        legend_parts.append(f"{TOWN_UNKNOWN_ICON}{get_locale_text('i18n_world_grid.town_unknown')}")
    if TOWN_EMPTY_ICON in seen:
        legend_parts.append(f"{TOWN_EMPTY_ICON}{get_locale_text('renderer_town.legend_wall')}")
    if legend_parts:
        lines.append(get_locale_text("renderer_town.legend_title") + " ".join(legend_parts))
    lines.append(get_locale_text("i18n_world_grid.town_hint"))
    return "\n".join(lines)

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
    elif npc_id == "Farengar_Secret_Fire":
        flags = getattr(stats, "town_flags", {}) or {}
        if flags.get("bleak_falls_tavern_ready"):
            return " ❗"
    return ""

def render_town(stats: UserStats, room_data: Dict[str, Any], world_players: List[Dict[str, Any]] | None = None, ghost_names: List[str] | None = None) -> str:
    zh_cn = _load_zh_cn()
    current_id = stats.town_pos
    if world_players is None:
        world_players = render_players(WORLD_TOWN, None, get_user_id())
    from ..data.town_map_config import TOWN_ROOM_COORDS
    coord = TOWN_ROOM_COORDS.get(stats.town_pos, "C2")
    world_here = [entry for entry in world_players if str(entry.get("coord", "")) == coord]
    map_str = render_town_map(stats, current_id)

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

    if current_id == "tavern":
        flags = getattr(stats, "town_flags", {}) or {}
        if flags.get("bleak_falls_tavern_ready") or flags.get("quest_bleak_falls_state") == "completed":
            f_name = entities_loc.get("Farengar_Secret_Fire", {}).get("name", "Farengar_Secret_Fire")
            f_ind = get_npc_quest_indicator("Farengar_Secret_Fire", stats)
            visible_npcs.append(f"{f_name}{f_ind}")

    for entry in world_here:
        visible_npcs.append(f"{WORLD_PLAYER_ICON}{entry.get('name', '')}")
    for gname in (ghost_names or []):
        if gname:
            visible_npcs.append(gname)

    none_label = get_locale_text("global.none")
    npc_str = get_locale_text("renderer_town.list_separator").join(visible_npcs) if visible_npcs else none_label

    visible_items = []
    for item_id in room_data.get("items", []):
        if not stats.town_flags.get(f"taken_{item_id}", 0):
            visible_items.append(get_item_display_name(item_id))
    
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

    ow_bag = list(getattr(stats, "open_world_bag", []) or [])
    ow_relics = list(getattr(stats, "open_world_relics", []) or [])
    hp, max_hp, sp, max_sp, _ = OpenWorldLoadoutService.get_vitals(stats)
    player_name = str(getattr(stats, "player_handle", "") or getattr(stats, "player_name", "") or get_locale_text("i18n_town.player_default_name"))
    inventory_line = get_locale_text(
        "i18n_open_world.bag.loadout_summary",
        player_name=player_name,
        hp=hp,
        max_hp=max_hp,
        sp=sp,
        max_sp=max_sp,
        count=len(ow_bag),
        weight=round(calc_bag_items_weight(ow_bag), 1),
        max_weight=BAG_DEFAULT_MAX_WEIGHT,
        relics=len(ow_relics),
        gp=stats.gp,
    )
    town_inv = list(stats.town_inventory)
    tokens_line = ""
    if town_inv:
        if len(town_inv) > TOWN_INVENTORY_FOLD_THRESHOLD:
            tokens_line = get_locale_text("i18n_open_world.bag.quest_tokens_folded", count=len(town_inv))
        else:
            inv_display = [get_item_display_name(item_id) for item_id in town_inv]
            inv_str = get_locale_text("renderer_town.list_separator").join(inv_display)
            tokens_line = get_locale_text("i18n_open_world.bag.quest_tokens", items=inv_str)

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
        inventory_line,
    ]
    if tokens_line:
        lines.append(tokens_line)
    lines.extend([
        quest_str,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        get_locale_text("global.help_move"),
        get_locale_text("global.help_take"),
        get_locale_text("global.help_use"),
        get_locale_text("global.help_talk"),
        get_locale_text("global.help_touch"),
        get_locale_text("global.help_attack"),
        get_locale_text("global.help_system"),
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ])
    return "\n".join(lines)
