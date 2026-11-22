import random
from typing import List, Optional, Tuple
from ...data.world.grid_map_config import PERMANENT_ICON_TYPES
from ..world.grid_map_generator import coord_to_xy, xy_to_coord
from ...data.text.locale_data import get_locale_text
from ...data.entities.potion_data import POTION_CONFIG, get_potion_desc, get_potion_name, get_potion_rarity, get_potion_weight
from ...data.world.room_interact_data import BAG_DEFAULT_MAX_WEIGHT, ROGUE_ITEMS
from ..i18n.locale_manager import LocaleManager
from ..world.sp_system import reduce_exhaustion, restore_sp


def get_item_weight(item_id: str) -> float:
    if item_id.startswith("potion:"):
        return round(get_potion_weight(item_id.split(":", 1)[1]), 2)
    cfg = ROGUE_ITEMS.get(item_id)
    if cfg:
        return round(float(cfg.get("weight", 1.0)), 2)
    return 1.0


def format_weight(weight: float) -> str:
    rounded = round(float(weight), 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:g}"


def calc_bag_items_weight(items: Optional[List[str]]) -> float:
    return round(sum(get_item_weight(it) for it in (items or [])), 2)


def get_bag_weight(player) -> float:
    items = getattr(player, "bag_items", None) or []
    return calc_bag_items_weight(items)


def can_add_bag_item(items: Optional[List[str]], item_id: str, max_weight: float = BAG_DEFAULT_MAX_WEIGHT) -> bool:
    return round(calc_bag_items_weight(items) + get_item_weight(item_id), 2) <= float(max_weight)


def get_bag_max_weight(player) -> int:
    return max(1, int(getattr(player, "bag_max_weight", BAG_DEFAULT_MAX_WEIGHT) or BAG_DEFAULT_MAX_WEIGHT))


def get_item_rarity(item_id: str) -> str:
    if item_id.startswith("potion:"):
        return get_potion_rarity(item_id.split(":", 1)[1])
    cfg = ROGUE_ITEMS.get(item_id)
    if cfg:
        return str(cfg.get("rarity", "common"))
    return "common"


def get_item_rarity_label(item_id: str) -> str:
    rarity = get_item_rarity(item_id)
    return get_locale_text(f"renderer_menu.rarity_{rarity}")


def get_player_potions(player) -> List[Tuple[int, str]]:
    items = getattr(player, "bag_items", None) or []
    return [(idx, it.split(":", 1)[1]) for idx, it in enumerate(items) if it.startswith("potion:")]


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
    if not hasattr(player, "bag_items") or player.bag_items is None:
        player.bag_items = []
    w = get_item_weight(item_id)
    used = get_bag_weight(player)
    mx = get_bag_max_weight(player)
    dname = get_item_display_name(item_id)
    new_used = round(used + w, 2)
    if new_used > mx:
        return False, get_locale_text(
            "i18n_room_interact.bag.weight_full",
            used=format_weight(used),
            max=mx,
            name=dname,
            weight=format_weight(w),
        )
    player.bag_items.append(item_id)
    return True, get_locale_text(
        "i18n_room_interact.bag.take_success",
        name=dname,
        weight=format_weight(w),
        used=format_weight(new_used),
        max=mx,
    )


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
        weight=format_weight(w),
        used=format_weight(get_bag_weight(p)),
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
    if item_id.startswith("potion:"):
        pid = item_id.split(":", 1)[1]
        if run.node_type != "battle" and not POTION_CONFIG.get(pid, {}).get("usable_out_of_battle", False):
            return get_locale_text("i18n_cli_general_a.potion.battle_only")
        items.remove(item_id)
        return engine.potion_resolver.use_potion(run, pid, "p0", False)
    cfg = ROGUE_ITEMS.get(item_id)
    if not cfg:
        return get_locale_text("i18n_room_interact.bag.use_town_item", name=get_item_display_name(item_id), desc=get_item_desc(item_id))
    fm = getattr(run, "floor_map", None)
    if item_id == "qgp_bomb":
        from ..world.bleak_falls import use_qgp_bomb
        return use_qgp_bomb(engine, run)
    if item_id == "arvel_journal":
        return get_locale_text("i18n_bleak_falls.items.use_journal")
    if item_id == "golden_claw":
        return get_locale_text("i18n_bleak_falls.items.use_claw_in_bag")
    if item_id == "dragonstone":
        return get_locale_text("i18n_bleak_falls.items.use_dragonstone_in_bag")
    if item_id == "survey_chart":
        return get_locale_text("i18n_bleak_falls.items.use_survey_chart")
    if item_id == "glass_shard":
        return get_locale_text("i18n_prism.glass_shard.use_msg")
    if item_id == "nordic_mead":
        items.remove(item_id)
        before_hp = p.hp
        heal_amt = int(cfg.get("heal", 12))
        p.hp = min(p.max_hp, p.hp + heal_amt)
        sp_gained = restore_sp(p, int(cfg.get("sp_gain", 4)))
        return get_locale_text("i18n_bleak_falls.items.use_nordic_mead", heal=p.hp - before_hp, sp=sp_gained)
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
            from ..progress.achievement_service import record_run_achievement_stat

            record_run_achievement_stat(getattr(engine, "save_manager", None), run, "secret_clues_found", 1)
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
    from .chaos_items import try_use_chaos_item

    chaos_msg = try_use_chaos_item(engine, run, item_id, cfg, add_bag_item, _reveal_special_rooms)
    if chaos_msg is not None:
        return chaos_msg
    from ..world.chireiden import try_use_chireiden_item

    chireiden_msg = try_use_chireiden_item(engine, run, item_id, cfg, add_bag_item, _reveal_special_rooms)
    if chireiden_msg is not None:
        return chireiden_msg
    return get_locale_text("i18n_room_interact.bag.use_cannot_here", name=get_item_display_name(item_id))


def _is_valid_carryover_item(item_id: str) -> bool:
    if item_id.startswith("potion:"):
        return item_id.split(":", 1)[1] in POTION_CONFIG
    return item_id in ROGUE_ITEMS and is_item_carryover(item_id)


def carryin_from_stats(player, stats) -> None:
    chest_items = list(getattr(stats, "town_chest", []) or [])
    remaining_chest = []
    for item_id in chest_items:
        if _is_valid_carryover_item(item_id):
            w = get_item_weight(item_id)
            if round(get_bag_weight(player) + w, 2) <= get_bag_max_weight(player):
                player.bag_items.append(item_id)
                continue
        remaining_chest.append(item_id)
    stats.town_chest = remaining_chest

    town_inv = list(getattr(stats, "town_inventory", []) or [])
    remaining_inv = []
    for item_id in town_inv:
        if _is_valid_carryover_item(item_id):
            w = get_item_weight(item_id)
            if round(get_bag_weight(player) + w, 2) <= get_bag_max_weight(player):
                player.bag_items.append(item_id)
                continue
        remaining_inv.append(item_id)
    stats.town_inventory = remaining_inv


def carryout_to_stats(player, stats) -> List[str]:
    carried = []
    if not hasattr(stats, "town_chest") or stats.town_chest is None:
        stats.town_chest = []
    for item_id in list(getattr(player, "bag_items", []) or []):
        if is_item_carryover(item_id):
            stats.town_chest.append(item_id)
            carried.append(get_item_display_name(item_id))
    return carried
