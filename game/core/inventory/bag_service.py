import random
from typing import List, Optional, Tuple
from ...data.grid_map_config import PERMANENT_ICON_TYPES
from ..world.grid_map_generator import coord_to_xy, xy_to_coord
from ...data.locale_data import get_locale_text
from ...data.potion_data import POTION_CONFIG, POTION_SLOT_LIMIT, get_potion_desc, get_potion_name
from ...data.room_interact_data import BAG_DEFAULT_MAX_WEIGHT, ROGUE_ITEMS
from ..i18n.locale_manager import LocaleManager
from ..world.sp_system import reduce_exhaustion, restore_sp


def get_item_weight(item_id: str) -> int:
    if item_id.startswith("potion:"):
        return 0
    cfg = ROGUE_ITEMS.get(item_id)
    if cfg:
        return int(cfg.get("weight", 1))
    return 1


def get_bag_weight(player) -> int:
    items = getattr(player, "bag_items", None) or []
    return sum(get_item_weight(it) for it in items)


def get_bag_max_weight(player) -> int:
    return max(1, int(getattr(player, "bag_max_weight", BAG_DEFAULT_MAX_WEIGHT) or BAG_DEFAULT_MAX_WEIGHT))


def is_item_carryover(item_id: str) -> bool:
    if item_id.startswith("potion:"):
        return True
    return bool(ROGUE_ITEMS.get(item_id, {}).get("carryover", False))


def get_item_display_name(item_id: str) -> str:
    if item_id.startswith("potion:"):
        pid = item_id.split(":", 1)[1]
        return get_locale_text("i18n_room_interact.items.potion_drop", name=get_potion_name(pid))
    cfg = ROGUE_ITEMS.get(item_id)
    if cfg:
        return get_locale_text(cfg["name_key"])
    zh_cn = LocaleManager.get_all_translations()
    names = zh_cn.get("items", {}).get(item_id)
    if isinstance(names, list) and names:
        return names[0]
    return item_id


def get_item_desc(item_id: str) -> str:
    if item_id.startswith("potion:"):
        pid = item_id.split(":", 1)[1]
        return get_potion_desc(pid)
    cfg = ROGUE_ITEMS.get(item_id)
    if cfg:
        return get_locale_text(cfg["desc_key"])
    zh_cn = LocaleManager.get_all_translations()
    return zh_cn.get("item_descs", {}).get(item_id, get_locale_text("renderer_menu.bag_default_item_desc"))


def resolve_item_query(query: str, candidates: List[str]) -> Optional[str]:
    from ..cli.base.pinyin_match import find_entry_by_query
    q = (query or "").strip()
    if not q or not candidates:
        return None
    ql = q.lower()
    zh_cn = LocaleManager.get_all_translations()
    town_items = zh_cn.get("items", {})
    entries = []
    for item_id in candidates:
        if item_id.lower() == ql:
            return item_id
        dname = get_item_display_name(item_id)
        if dname.lower() == ql:
            return item_id
        entries.append((item_id, dname))
        if item_id.startswith("potion:"):
            pid = item_id.split(":", 1)[1]
            pname = get_potion_name(pid)
            if pname.lower() == ql or pid.lower() == ql:
                return item_id
            entries.append((item_id, pname))
        cfg = ROGUE_ITEMS.get(item_id)
        if cfg:
            for alias in cfg.get("aliases", []):
                if alias.lower() == ql:
                    return item_id
                entries.append((item_id, alias))
        if item_id in town_items and isinstance(town_items[item_id], list):
            for alias in town_items[item_id]:
                if alias.lower() == ql:
                    return item_id
                entries.append((item_id, alias))
    return find_entry_by_query(entries, q)


def add_bag_item(player, item_id: str) -> Tuple[bool, str]:
    if item_id.startswith("potion:"):
        pid = item_id.split(":", 1)[1]
        if not hasattr(player, "potions") or player.potions is None:
            player.potions = []
        pname = get_potion_name(pid)
        if len(player.potions) >= POTION_SLOT_LIMIT:
            return False, get_locale_text("i18n_room_interact.bag.potion_full", count=len(player.potions), limit=POTION_SLOT_LIMIT, name=pname)
        player.potions.append(pid)
        return True, get_locale_text("i18n_room_interact.bag.take_potion_success", name=pname, count=len(player.potions), limit=POTION_SLOT_LIMIT)
    if not hasattr(player, "bag_items") or player.bag_items is None:
        player.bag_items = []
    w = get_item_weight(item_id)
    used = get_bag_weight(player)
    mx = get_bag_max_weight(player)
    dname = get_item_display_name(item_id)
    if used + w > mx:
        return False, get_locale_text("i18n_room_interact.bag.weight_full", used=used, max=mx, name=dname, weight=w)
    player.bag_items.append(item_id)
    return True, get_locale_text("i18n_room_interact.bag.take_success", name=dname, weight=w, used=used + w, max=mx)


def drop_bag_item(run, query: str) -> str:
    p = run.player
    items = getattr(p, "bag_items", None) or []
    item_id = resolve_item_query(query, items)
    if not item_id:
        return get_locale_text("i18n_room_interact.bag.drop_not_found", target=query)
    items.remove(item_id)
    w = get_item_weight(item_id)
    return get_locale_text(
        "i18n_room_interact.bag.drop_success",
        name=get_item_display_name(item_id),
        weight=w,
        used=get_bag_weight(p),
        max=get_bag_max_weight(p),
    )


def _reveal_special_rooms(fm, count: int) -> List[str]:
    candidates = []
    for coord, room in fm.rooms.items():
        if room.room_type in ("wall", "obstacle", "empty", "spawn", "secret_boss"):
            continue
        if not room.explored and coord not in fm.revealed_coords:
            candidates.append(coord)
    if not candidates:
        for coord, room in fm.rooms.items():
            if room.room_type not in ("wall", "secret_boss") and not room.explored and coord not in fm.revealed_coords:
                candidates.append(coord)
    random.shuffle(candidates)
    chosen = candidates[:count]
    for c in chosen:
        if c not in fm.revealed_coords:
            fm.revealed_coords.append(c)
    return chosen


def use_bag_item(engine, run, query: str) -> str:
    q = (query or "").strip()
    if not q:
        return get_locale_text("i18n_room_interact.bag.use_need_arg")
    p = run.player
    items = getattr(p, "bag_items", None) or []
    item_id = resolve_item_query(q, items)
    if not item_id:
        return get_locale_text("i18n_room_interact.bag.use_not_found", target=q)
    cfg = ROGUE_ITEMS.get(item_id)
    if not cfg:
        return get_locale_text("i18n_room_interact.bag.use_town_item", name=get_item_display_name(item_id), desc=get_item_desc(item_id))
    fm = getattr(run, "floor_map", None)
    if item_id == "espresso_beans":
        sp = restore_sp(p, cfg["sp_gain"])
        items.remove(item_id)
        return get_locale_text("i18n_room_interact.bag.use_espresso_beans", sp=sp)
    if item_id == "rusty_pickaxe":
        items.remove(item_id)
        cleared_coord = ""
        if fm is not None:
            cur = fm.player_coords.get(run.user_id, "")
            if cur:
                cx, cy = coord_to_xy(cur)
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < fm.width and 0 <= ny < fm.height:
                        nc = xy_to_coord(nx, ny)
                        nroom = fm.rooms.get(nc)
                        if nroom and nroom.room_type == "obstacle":
                            nroom.room_type = "empty"
                            nroom.cleared = True
                            nroom.obstacle_sp = 0
                            if nc not in fm.revealed_coords:
                                fm.revealed_coords.append(nc)
                            cleared_coord = nc
                            break
        sp = restore_sp(p, 1)
        if cleared_coord:
            return get_locale_text("i18n_room_interact.bag.use_rusty_pickaxe_clear", coord=cleared_coord, sp=sp)
        return get_locale_text("i18n_room_interact.bag.use_rusty_pickaxe_sp", sp=sp)
    if item_id == "glowing_runestone":
        items.remove(item_id)
        if fm is not None:
            revealed = _reveal_special_rooms(fm, cfg["reveal_count"])
            if revealed:
                return get_locale_text("i18n_room_interact.bag.use_glowing_runestone", coords="、".join(revealed))
        restore_sp(p, 2)
        return get_locale_text("i18n_room_interact.bag.use_glowing_runestone_none")
    if item_id == "field_bandage":
        before = p.hp
        p.hp = min(p.max_hp, p.hp + cfg["heal"])
        items.remove(item_id)
        return get_locale_text("i18n_room_interact.bag.use_field_bandage", hp=p.hp - before)
    if item_id == "ancient_notes":
        items.remove(item_id)
        if fm is not None and fm.ritual_coord:
            fm.secret_clue_found = True
            if fm.ritual_coord not in fm.revealed_coords:
                fm.revealed_coords.append(fm.ritual_coord)
            return get_locale_text("i18n_room_interact.bag.use_ancient_notes_clue", coord=fm.ritual_coord)
        p.gold += 15
        return get_locale_text("i18n_room_interact.bag.use_ancient_notes_gold", gold=15)
    if item_id == "skeleton_key":
        items.remove(item_id)
        sp = restore_sp(p, cfg["sp_gain"])
        if fm is not None:
            cur = fm.player_coords.get(run.user_id, "")
            if cur:
                cx, cy = coord_to_xy(cur)
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < fm.width and 0 <= ny < fm.height:
                        nc = xy_to_coord(nx, ny)
                        if nc not in fm.revealed_coords:
                            fm.revealed_coords.append(nc)
        return get_locale_text("i18n_room_interact.bag.use_skeleton_key", sp=sp)
    if item_id == "sugar_cube_pack":
        items.remove(item_id)
        sp = restore_sp(p, cfg["sp_gain"])
        old_ex = getattr(p, "exhaustion", 0)
        new_ex = reduce_exhaustion(p, cfg["exhaustion_cure"])
        return get_locale_text("i18n_room_interact.bag.use_sugar_cube_pack", sp=sp, cured=max(0, old_ex - new_ex))
    if item_id in ("smuggler_token", "merchant_ledger"):
        items.remove(item_id)
        g = int(cfg["gold_gain"])
        p.gold += g
        key = "use_smuggler_token" if item_id == "smuggler_token" else "use_merchant_ledger"
        return get_locale_text(f"i18n_room_interact.bag.{key}", gold=g)
    if item_id == "barista_seal":
        items.remove(item_id)
        sp = restore_sp(p, cfg["sp_gain"])
        return get_locale_text("i18n_room_interact.bag.use_barista_seal", sp=sp)
    return get_locale_text("i18n_room_interact.bag.use_cannot_here", name=get_item_display_name(item_id))


def carryin_from_stats(player, stats) -> None:
    town_potions = list(getattr(stats, "town_potions", []) or [])
    remaining_potions = []
    for pid in town_potions:
        if pid in POTION_CONFIG and len(player.potions) < POTION_SLOT_LIMIT:
            player.potions.append(pid)
        else:
            remaining_potions.append(pid)
    stats.town_potions = remaining_potions

    town_inv = list(getattr(stats, "town_inventory", []) or [])
    remaining_inv = []
    for item_id in town_inv:
        if item_id in ROGUE_ITEMS and is_item_carryover(item_id):
            w = get_item_weight(item_id)
            if get_bag_weight(player) + w <= get_bag_max_weight(player):
                player.bag_items.append(item_id)
                continue
        remaining_inv.append(item_id)
    stats.town_inventory = remaining_inv


def carryout_to_stats(player, stats) -> List[str]:
    carried = []
    if not hasattr(stats, "town_potions") or stats.town_potions is None:
        stats.town_potions = []
    if not hasattr(stats, "town_inventory") or stats.town_inventory is None:
        stats.town_inventory = []
    for pid in list(getattr(player, "potions", []) or []):
        if pid in POTION_CONFIG:
            stats.town_potions.append(pid)
            carried.append(get_potion_name(pid))
    for item_id in list(getattr(player, "bag_items", []) or []):
        if is_item_carryover(item_id):
            stats.town_inventory.append(item_id)
            carried.append(get_item_display_name(item_id))
    return carried
