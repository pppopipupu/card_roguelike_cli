from typing import List, Tuple
from ....data.locale_data import get_locale_text
from ....data.room_interact_data import CAFE_BARISTA_CONFIG, ROOM_NPCS
from ....entities import ALL_CARDS
from ...inventory.bag_service import get_item_display_name
from ...cli.base.pinyin_match import find_entry_by_query
from ..rooms.interact import _reveal_any_special, get_current_room
from ..sp_system import reduce_exhaustion, restore_sp


def is_barista_query(query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return False
    cfg = ROOM_NPCS["cafe_barista"]
    name = get_locale_text(cfg["name_key"])
    if q in ("barista_bruno", "cafe_barista", name.lower()) or q in name.lower():
        return True
    if any(q == a.lower() for a in cfg["aliases"]):
        return True
    entries = [("cafe_barista", name)] + [("cafe_barista", a) for a in cfg["aliases"]]
    return find_entry_by_query(entries, query) is not None


def get_barista_dialog_content(run, state: str) -> Tuple[str, List[str]]:
    cfg = CAFE_BARISTA_CONFIG
    opts = [
        get_locale_text("i18n_room_interact.cafe.barista_opt_espresso", cost=cfg["espresso_cost"], sp=cfg["espresso_sp"], cure=cfg["espresso_ex_cure"]),
        get_locale_text("i18n_room_interact.cafe.barista_opt_americano", cost=cfg["arcane_americano_cost"], sp=4),
        get_locale_text("i18n_room_interact.cafe.barista_opt_macchiato", hp=cfg["abyss_macchiato_hp_cost"]),
        get_locale_text("i18n_room_interact.cafe.barista_opt_chamomile", cost=cfg["chamomile_tea_cost"], heal=cfg["chamomile_heal"], cure=cfg["chamomile_ex_cure"]),
        get_locale_text("i18n_room_interact.cafe.barista_opt_grinder", cost=cfg["grinder_gold_cost"]),
        get_locale_text("i18n_room_interact.cafe.barista_opt_rumor", cost=cfg["rumor_cost"]),
        get_locale_text("i18n_room_interact.cafe.barista_opt_leave"),
    ]
    return get_locale_text("i18n_room_interact.cafe.barista_greeting"), opts


def execute_barista_dialog_choice(cafe_engine, run, idx: int) -> str:
    cfg = CAFE_BARISTA_CONFIG
    p = run.player
    cafe_data = cafe_engine._view_cafe(run)
    if idx == 1:
        cost = cfg["espresso_cost"]
        if p.gold < cost:
            return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=cost)
        p.gold -= cost
        gained = restore_sp(p, cfg["espresso_sp"])
        old_ex = getattr(p, "exhaustion", 0)
        new_ex = reduce_exhaustion(p, cfg["espresso_ex_cure"])
        return get_locale_text("i18n_grid_map.cafe_drink_bought", cost=cost, sp=gained, exhaustion_cured=max(0, old_ex - new_ex))
    if idx == 2:
        cost = cfg["arcane_americano_cost"]
        if p.gold < cost:
            return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=cost)
        p.gold -= cost
        gained = restore_sp(p, 4)
        before = p.hp
        p.hp = min(p.max_hp, p.hp + 6)
        return get_locale_text("i18n_room_interact.cafe.americano_ok", sp=gained, heal=p.hp - before)
    if idx == 3:
        hpc = cfg["abyss_macchiato_hp_cost"]
        if p.hp <= hpc:
            return get_locale_text("i18n_room_interact.dialog.err_hp")
        p.hp -= hpc
        restore_sp(p, int(getattr(p, "max_sp", 10) or 10))
        p.gold += 25
        return get_locale_text("i18n_room_interact.cafe.macchiato_ok", hp=hpc, gold=25)
    if idx == 4:
        cost = cfg["chamomile_tea_cost"]
        if p.gold < cost:
            return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=cost)
        from ..persistent_buffs import cure_persistent_debuffs
        p.gold -= cost
        before = p.hp
        p.hp = min(p.max_hp, p.hp + cfg["chamomile_heal"])
        old_ex = getattr(p, "exhaustion", 0)
        new_ex = reduce_exhaustion(p, cfg["chamomile_exhaustion_cure"])
        cure_persistent_debuffs(p, 1)
        cafe_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_room_interact.cafe.chamomile_ok", heal=p.hp - before, cure=max(0, old_ex - new_ex))
    if idx == 5:
        from ....data.card_upgrade_data import CARD_UPGRADE_CONFIG
        unupgraded = [c for c in p.deck if not c.upgraded and c.id in CARD_UPGRADE_CONFIG]
        if not unupgraded:
            return get_locale_text("i18n_room_interact.cafe.grinder_no_card")
        bag_items = getattr(p, "bag_items", None) or []
        if "espresso_beans" in bag_items:
            bag_items.remove("espresso_beans")
            c = unupgraded[0]
            old_name = ALL_CARDS[c].name
            c.upgraded = True
            new_name = ALL_CARDS[c].name
            return get_locale_text("i18n_room_interact.cafe.grinder_beans_ok", old=old_name, new=new_name)
        cost = cfg["grinder_gold_cost"]
        if p.gold < cost:
            return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=cost)
        p.gold -= cost
        run.node_data["upgrade_source"] = "cafe"
        run.node_data["pending_upgrade"] = True
        return "UPGRADE_FLOW"
    if idx == 6:
        cost = cfg["rumor_cost"]
        if p.gold < cost:
            return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=cost)
        fm = getattr(run, "floor_map", None)
        revealed = _reveal_any_special(fm, 2) if fm is not None else []
        if not revealed:
            return get_locale_text("i18n_room_interact.cafe.rumor_none")
        p.gold -= cost
        return get_locale_text("i18n_room_interact.cafe.rumor_ok", coords="、".join(revealed))
    cafe_data["active_npc"] = None
    cafe_data["dialog_state"] = None
    return get_locale_text("i18n_map_cafe.cafe_msg_left_npc") + "\n\n" + cafe_engine.render_cafe(run)


def render_cafe_room_extras(run) -> List[str]:
    room, _ = get_current_room(run)
    if room is None:
        return []
    from ....data.room_interact_data import ROOM_PROPS
    extras = []
    if room.shared_payload.get("barista_defeated"):
        extras.append(get_locale_text("i18n_room_interact.cafe.barista_dead_line"))
    else:
        extras.append(get_locale_text("i18n_room_interact.cafe.barista_line"))
    done = set(room.interacted_props or [])
    prop_scenes = [
        get_locale_text(f"i18n_room_interact.props.{pid}.done_scene" if pid in done else f"i18n_room_interact.props.{pid}.scene")
        for pid in (room.props or []) if pid in ROOM_PROPS
    ]
    if prop_scenes:
        extras.append(get_locale_text("i18n_room_interact.cafe.facilities_scene", desc="".join(prop_scenes)))
    if room.items:
        inames = [f"【{get_item_display_name(it)}】" for it in room.items]
        extras.append(get_locale_text("i18n_room_interact.room_ui.items_line", items="、".join(inames)))
    return extras
