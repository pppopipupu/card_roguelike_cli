import random
from typing import List, Optional
from ....data.locale_data import get_locale_text
from ....data.potion_data import get_potion_name, roll_potion
from ....data.room_interact_data import ROOM_NPCS, ROOM_PROPS
from ...inventory.bag_service import add_bag_item, get_item_display_name, resolve_item_query
from ...cli.base.pinyin_match import find_entry_by_query
from ..sp_system import reduce_exhaustion, restore_sp


def get_current_room(run):
    fm = getattr(run, "floor_map", None)
    if fm is None:
        return None, ""
    coord = fm.player_coords.get(run.user_id, "")
    return fm.rooms.get(coord), coord


def _reveal_any_special(fm, count: int = 1) -> List[str]:
    candidates = [
        c for c, r in fm.rooms.items()
        if r.room_type not in ("wall", "obstacle", "empty", "spawn", "secret_boss")
        and not r.explored
        and c not in fm.revealed_coords
    ]
    if not candidates:
        candidates = [
            c for c, r in fm.rooms.items()
            if r.room_type not in ("wall", "secret_boss")
            and not r.explored
            and c not in fm.revealed_coords
        ]
    random.shuffle(candidates)
    chosen = candidates[:count]
    for c in chosen:
        if c not in fm.revealed_coords:
            fm.revealed_coords.append(c)
    return chosen


def resolve_npc_in_room(room, query: str) -> Optional[str]:
    if room is None:
        return None
    defeated = set(getattr(room, "defeated_npcs", None) or [])
    alive = [nid for nid in (getattr(room, "npcs", None) or []) if nid not in defeated]
    if not alive:
        return None
    q = (query or "").strip()
    if not q:
        return alive[0] if len(alive) == 1 else None
    ql = q.lower()
    entries = []
    for nid in alive:
        if nid.lower() == ql:
            return nid
        cfg = ROOM_NPCS.get(nid, {})
        name = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else nid
        if name.lower() == ql or ql in name.lower():
            return nid
        entries.append((nid, name))
        for alias in cfg.get("aliases", []):
            if alias.lower() == ql:
                return nid
            entries.append((nid, alias))
    return find_entry_by_query(entries, q)


def resolve_prop_in_room(room, query: str) -> Optional[str]:
    if room is None:
        return None
    props = list(getattr(room, "props", None) or [])
    if not props:
        return None
    q = (query or "").strip()
    if not q:
        return None
    ql = q.lower()
    entries = []
    for pid in props:
        if pid.lower() == ql:
            return pid
        cfg = ROOM_PROPS.get(pid, {})
        name = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else pid
        if name.lower() == ql or ql in name.lower():
            return pid
        entries.append((pid, name))
        for alias in cfg.get("aliases", []):
            if alias.lower() == ql:
                return pid
            entries.append((pid, alias))
    return find_entry_by_query(entries, q)


def touch_in_room(save_manager, run, query: str) -> str:
    q = (query or "").strip()
    if not q:
        return get_locale_text("i18n_room_interact.touch.need_arg")
    room, coord = get_current_room(run)
    if room is None:
        return get_locale_text("i18n_grid_map.err_no_floor_map")
    if room.room_type == "downstairs":
        from ..landmark_system import ensure_descent_tunnel
        ensure_descent_tunnel(room)
    prop_id = resolve_prop_in_room(room, q)
    if not prop_id:
        return get_locale_text("i18n_room_interact.touch.not_found", target=q)
    cfg = ROOM_PROPS.get(prop_id, {})
    pname = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else prop_id
    if prop_id == "descent_tunnel":
        from ..landmark_system import open_room_talk
        from ....renderer import GameRenderer
        err = open_room_talk(save_manager, run, run.user_id)
        if err:
            return err
        return GameRenderer.render_game(run)
    done = room.interacted_props
    if prop_id in done:
        return get_locale_text("i18n_room_interact.touch.already_done", name=pname)
    done.append(prop_id)
    p = run.player
    fm = run.floor_map
    if prop_id == "ancient_brazier":
        sp = restore_sp(p, cfg["sp_gain"])
        msg = get_locale_text("i18n_room_interact.touch.ancient_brazier", sp=sp)
    elif prop_id == "cracked_statue":
        if random.random() < 0.35:
            dmg = cfg["trap_dmg"]
            p.hp = max(1, p.hp - dmg)
            p.gold += cfg["gold_gain"]
            msg = get_locale_text("i18n_room_interact.touch.cracked_statue_trap", dmg=dmg, gold=cfg["gold_gain"])
        else:
            p.gold += cfg["gold_gain"]
            msg = get_locale_text("i18n_room_interact.touch.cracked_statue_gold", gold=cfg["gold_gain"])
    elif prop_id == "alchemy_desk":
        pid = roll_potion(getattr(p, "selected_class", "法师"))
        ok, _ = add_bag_item(p, f"potion:{pid}")
        if ok:
            msg = get_locale_text("i18n_room_interact.touch.alchemy_desk_potion", potion=get_potion_name(pid))
        else:
            ok2, _ = add_bag_item(p, "field_bandage")
            if ok2:
                msg = get_locale_text("i18n_room_interact.touch.alchemy_desk_item", item=get_item_display_name("field_bandage"))
            else:
                room.items.append(f"potion:{pid}")
                msg = get_locale_text("i18n_room_interact.touch.alchemy_desk_full", potion=get_potion_name(pid))
    elif prop_id == "bloodied_pack":
        p.gold += cfg["gold_gain"]
        ok, _ = add_bag_item(p, "field_bandage")
        if not ok:
            room.items.append("field_bandage")
        msg = get_locale_text("i18n_room_interact.touch.bloodied_pack", gold=cfg["gold_gain"])
    elif prop_id == "runic_wall":
        revealed = _reveal_any_special(fm, 1) if fm is not None else []
        if revealed:
            msg = get_locale_text("i18n_room_interact.touch.runic_wall_reveal", coord=revealed[0])
        else:
            restore_sp(p, 2)
            msg = get_locale_text("i18n_room_interact.touch.runic_wall_sp")
    elif prop_id == "crystal_cluster":
        before = p.hp
        p.hp = min(p.max_hp, p.hp + cfg["heal"])
        sp = restore_sp(p, cfg["sp_gain"])
        msg = get_locale_text("i18n_room_interact.touch.crystal_cluster", hp=p.hp - before, sp=sp)
    elif prop_id == "shop_scale":
        p.gold += cfg["gold_gain"]
        msg = get_locale_text("i18n_room_interact.touch.shop_scale", gold=cfg["gold_gain"])
    elif prop_id == "shop_display":
        p.gold += 8
        msg = get_locale_text("i18n_room_interact.touch.shop_display", gold=8)
    elif prop_id == "cafe_espresso_machine":
        sp = restore_sp(p, cfg["sp_gain"])
        msg = get_locale_text("i18n_room_interact.touch.cafe_espresso_machine", sp=sp)
    elif prop_id == "cafe_gramophone":
        from ..persistent_buffs import cure_persistent_debuffs
        old_ex = getattr(p, "exhaustion", 0)
        new_ex = reduce_exhaustion(p, cfg["exhaustion_cure"])
        cure_persistent_debuffs(p, 1)
        msg = get_locale_text("i18n_room_interact.touch.cafe_gramophone", cured=max(0, old_ex - new_ex))
    elif prop_id == "cafe_guestbook":
        revealed = _reveal_any_special(fm, 1) if fm is not None else []
        target_c = revealed[0] if revealed else (fm.boss_coord if fm is not None and fm.boss_coord else coord)
        msg = get_locale_text("i18n_room_interact.touch.cafe_guestbook", coord=target_c)
    elif prop_id == "forgotten_shrine":
        from ..persistent_buffs import add_persistent_buff
        before = p.hp
        p.hp = min(p.max_hp, p.hp + cfg["heal"])
        add_persistent_buff(p, "ancient_ward", 1)
        msg = get_locale_text("i18n_room_interact.touch.forgotten_shrine", heal=p.hp - before)
    elif prop_id == "arcane_mirror":
        revealed = _reveal_any_special(fm, 2) if fm is not None else []
        if revealed:
            msg = get_locale_text("i18n_room_interact.touch.arcane_mirror_reveal", coords="、".join(revealed))
        else:
            sp = restore_sp(p, cfg["sp_gain"])
            p.gold += cfg["gold_gain"]
            msg = get_locale_text("i18n_room_interact.touch.arcane_mirror_fallback", sp=sp, gold=cfg["gold_gain"])
    elif prop_id == "smuggler_cache":
        loot = random.choice(["skeleton_key", "sugar_cube_pack"])
        ok, _ = add_bag_item(p, loot)
        if ok:
            msg = get_locale_text("i18n_room_interact.touch.smuggler_cache_item", item=get_item_display_name(loot))
        else:
            p.gold += cfg["gold_gain"]
            msg = get_locale_text("i18n_room_interact.touch.smuggler_cache_gold", gold=cfg["gold_gain"])
    elif prop_id == "dusty_bookshelf":
        from ..persistent_buffs import add_persistent_buff
        add_persistent_buff(p, "arcane_clarity", 1)
        ok, _ = add_bag_item(p, "ancient_notes")
        if not ok:
            room.items.append("ancient_notes")
        msg = get_locale_text("i18n_room_interact.touch.dusty_bookshelf")
    else:
        msg = get_locale_text("i18n_room_interact.touch.already_done", name=pname)
    save_manager.save_save(run.user_id, run)
    return msg


def take_in_room(save_manager, run, query: str) -> str:
    q = (query or "").strip()
    if not q:
        return get_locale_text("i18n_room_interact.bag.take_need_arg")
    room, _ = get_current_room(run)
    if room is None:
        return get_locale_text("i18n_grid_map.err_no_floor_map")
    items = list(getattr(room, "items", None) or [])
    item_id = resolve_item_query(q, items)
    if not item_id:
        return get_locale_text("i18n_room_interact.bag.take_not_found", target=q)
    ok, msg = add_bag_item(run.player, item_id)
    if ok:
        room.items.remove(item_id)
        save_manager.save_save(run.user_id, run)
    return msg


def format_room_env_with_props(room, include_cleared_suffix: bool = True) -> str:
    env_id = getattr(room, "env_id", "") or "dungeon_corridor"
    env_text = get_locale_text(f"i18n_room_interact.env.{env_id}")
    if include_cleared_suffix and room.cleared and room.room_type not in ("spawn", "empty", "shop", "cafe", "landmark", "downstairs"):
        env_text += get_locale_text("i18n_room_interact.env.cleared_suffix")
    done_props = set(getattr(room, "interacted_props", None) or [])
    for pid in getattr(room, "props", None) or []:
        if pid not in ROOM_PROPS:
            continue
        skey = f"i18n_room_interact.props.{pid}.done_scene" if pid in done_props else f"i18n_room_interact.props.{pid}.scene"
        env_text += get_locale_text(skey)
    return env_text


def format_room_extras(run, include_env: bool = True) -> List[str]:
    room, _ = get_current_room(run)
    if room is None:
        return []
    lines = []
    if include_env:
        lines.append(format_room_env_with_props(room, include_cleared_suffix=True))
    defeated = set(getattr(room, "defeated_npcs", None) or [])
    alive_npcs = [nid for nid in (getattr(room, "npcs", None) or []) if nid not in defeated and nid in ROOM_NPCS]
    if alive_npcs:
        nnames = [f"【{get_locale_text(ROOM_NPCS[nid]['name_key'])}】" for nid in alive_npcs]
        lines.append(get_locale_text("i18n_room_interact.room_ui.npcs_line", items="、".join(nnames)))
    items = list(getattr(room, "items", None) or [])
    if items:
        inames = [f"【{get_item_display_name(it)}】" for it in items]
        lines.append(get_locale_text("i18n_room_interact.room_ui.items_line", items="、".join(inames)))
    return lines
