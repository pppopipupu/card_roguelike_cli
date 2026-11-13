import random
from typing import List, Optional, Tuple
from ....data.locale_data import get_locale_text
from ....data.potion_data import roll_potion
from ....data.room_interact_data import CAFE_GUEST_COMBAT_STATS, ROOM_NPCS
from ...inventory.bag_service import add_bag_item, get_item_display_name
from ...cli.base.pinyin_match import find_entry_by_query
from ...inventory.deck_service import DeckService
from ...party.coordinator import apply_and_scope
from .interact import _reveal_any_special, get_current_room, resolve_npc_in_room
from ...party.session import SessionContextScoper
from ..sp_system import reduce_exhaustion, restore_sp


def talk_room_npc(save_manager, run, query: str) -> Optional[str]:
    room, coord = get_current_room(run)
    if room is None:
        return None
    nid = resolve_npc_in_room(room, query)
    if not nid:
        return None
    SessionContextScoper.create_session(
        run,
        coord,
        "room_dialog",
        [run.user_id],
        node_data={"npc_id": nid, "dialog_state": "start", "coord": coord},
    )
    save_manager.save_save(run.user_id, run)
    return render_room_dialog(run)


def _room_dialog_content(run) -> Tuple[str, str, List[str]]:
    nid = run.node_data.get("npc_id", "")
    dstate = run.node_data.get("dialog_state", "start")
    cfg = ROOM_NPCS.get(nid, {})
    name = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else nid
    if nid == "wandering_smith":
        if dstate == "lore":
            return name, get_locale_text("i18n_room_interact.dialog.smith_lore_text"), [
                get_locale_text("i18n_room_interact.dialog.smith_lore_opt1"),
                get_locale_text("i18n_room_interact.dialog.smith_lore_opt2"),
                get_locale_text("i18n_room_interact.dialog.smith_lore_opt3"),
            ]
        return name, get_locale_text("i18n_room_interact.dialog.smith_start_text"), [
            get_locale_text("i18n_room_interact.dialog.smith_start_opt1", cost=cfg["forge_cost"]),
            get_locale_text("i18n_room_interact.dialog.smith_start_opt2", cost=cfg["gem_cost"]),
            get_locale_text("i18n_room_interact.dialog.smith_start_opt3"),
            get_locale_text("i18n_room_interact.dialog.smith_start_opt4"),
        ]
    if nid == "smuggler_broker":
        if dstate == "trade":
            return name, get_locale_text("i18n_room_interact.dialog.broker_trade_text"), [
                get_locale_text("i18n_room_interact.dialog.broker_trade_opt1"),
                get_locale_text("i18n_room_interact.dialog.broker_trade_opt2"),
                get_locale_text("i18n_room_interact.dialog.broker_trade_opt3"),
            ]
        return name, get_locale_text("i18n_room_interact.dialog.broker_start_text"), [
            get_locale_text("i18n_room_interact.dialog.broker_start_opt1", cost=cfg["gamble_cost"]),
            get_locale_text("i18n_room_interact.dialog.broker_start_opt2", cost=cfg["intel_cost"]),
            get_locale_text("i18n_room_interact.dialog.broker_start_opt3"),
            get_locale_text("i18n_room_interact.dialog.broker_start_opt4"),
        ]
    if nid == "lost_scholar":
        return name, get_locale_text("i18n_room_interact.dialog.scholar_start_text"), [
            get_locale_text("i18n_room_interact.dialog.scholar_start_opt1", hp=cfg["study_hp_cost"]),
            get_locale_text("i18n_room_interact.dialog.scholar_start_opt2"),
            get_locale_text("i18n_room_interact.dialog.scholar_start_opt3"),
            get_locale_text("i18n_room_interact.dialog.scholar_start_opt4"),
        ]
    if nid == "wounded_scout":
        return name, get_locale_text("i18n_room_interact.dialog.scout_start_text"), [
            get_locale_text("i18n_room_interact.dialog.scout_start_opt1"),
            get_locale_text("i18n_room_interact.dialog.scout_start_opt2"),
            get_locale_text("i18n_room_interact.dialog.scout_start_opt3"),
            get_locale_text("i18n_room_interact.dialog.scout_start_opt4"),
        ]
    return name, get_locale_text("i18n_room_interact.dialog.keeper_start_text"), [
        get_locale_text("i18n_room_interact.dialog.keeper_start_opt1", hp=cfg.get("ritual_hp_cost", 6)),
        get_locale_text("i18n_room_interact.dialog.keeper_start_opt2"),
        get_locale_text("i18n_room_interact.dialog.keeper_start_opt3"),
        get_locale_text("i18n_room_interact.dialog.keeper_start_opt4"),
    ]


def render_room_dialog(run) -> str:
    name, text, opts = _room_dialog_content(run)
    lines = [
        get_locale_text("i18n_grid_map.separator"),
        get_locale_text("i18n_room_interact.dialog.title", name=name),
        "",
        text,
        "",
    ]
    for idx, opt in enumerate(opts, 1):
        lines.append(f" [{idx}] {opt}")
    lines.append("")
    lines.append(get_locale_text("i18n_room_interact.dialog.footer"))
    lines.append(get_locale_text("i18n_grid_map.separator"))
    return "\n".join(lines)


def close_room_dialog(save_manager, run) -> str:
    nid = run.node_data.get("npc_id", "")
    cfg = ROOM_NPCS.get(nid, {})
    name = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else nid
    fm = getattr(run, "floor_map", None)
    if fm is not None:
        sid = fm.player_session_map.get(run.user_id)
        if sid:
            SessionContextScoper.close_session(run, sid, mark_cleared=False)
    run.node_type = "grid_map"
    save_manager.save_save(run.user_id, run)
    return get_locale_text("i18n_room_interact.dialog.ended", name=name)


def handle_room_dialog_choice(map_engine, run, idx: int) -> str:
    nid = run.node_data.get("npc_id", "")
    dstate = run.node_data.get("dialog_state", "start")
    cfg = ROOM_NPCS.get(nid, {})
    p = run.player
    fm = getattr(run, "floor_map", None)
    _, opts = _room_dialog_content(run)[1:]
    if idx < 1 or idx > len(opts):
        return get_locale_text("err_invalid_option_idx")
    if nid == "wandering_smith":
        if dstate == "lore":
            if idx == 1:
                if p.gold < 30:
                    return get_locale_text("i18n_room_interact.dialog.err_gold", cost=30)
                ok, msg = add_bag_item(p, "rusty_pickaxe")
                if not ok:
                    return msg
                p.gold -= 30
                map_engine.save_manager.save_save(run.user_id, run)
                return get_locale_text("i18n_room_interact.dialog.smith_buy_pickaxe_ok")
            if idx == 2:
                restore_sp(p, 2)
                return close_room_dialog(map_engine.save_manager, run)
            run.node_data["dialog_state"] = "start"
            map_engine.save_manager.save_save(run.user_id, run)
            return render_room_dialog(run)
        if idx == 1:
            cost = cfg["forge_cost"]
            if p.gold < cost:
                return get_locale_text("i18n_room_interact.dialog.err_gold", cost=cost)
            from ....data.card_upgrade_data import CARD_UPGRADE_CONFIG
            if not any(not c.upgraded and c.id in CARD_UPGRADE_CONFIG for c in p.deck):
                return get_locale_text("i18n_room_interact.dialog.smith_no_unupgraded")
            p.gold -= cost
            run.node_data["upgrade_source"] = "room_dialog"
            run.node_data["pending_upgrade"] = True
            map_engine.save_manager.save_save(run.user_id, run)
            return "UPGRADE_FLOW"
        if idx == 2:
            cost = cfg["gem_cost"]
            if p.gold < cost:
                return get_locale_text("i18n_room_interact.dialog.err_gold", cost=cost)
            from ....data.gem_data import GEM_CONFIG
            p.gold -= cost
            gid = random.choice(list(GEM_CONFIG.keys()))
            res = map_engine.explore_engine.start_gem_insert_flow(run, gid, "room_dialog", dict(run.node_data))
            return get_locale_text("i18n_room_interact.dialog.smith_gem_ok") + "\n" + res
        if idx == 3:
            run.node_data["dialog_state"] = "lore"
            map_engine.save_manager.save_save(run.user_id, run)
            return render_room_dialog(run)
        return close_room_dialog(map_engine.save_manager, run)
    if nid == "smuggler_broker":
        if dstate == "trade":
            if idx == 1:
                if p.gold < 28:
                    return get_locale_text("i18n_room_interact.dialog.err_gold", cost=28)
                pid = roll_potion(getattr(p, "selected_class", "法师"))
                ok, msg = add_bag_item(p, f"potion:{pid}")
                if not ok:
                    return msg
                p.gold -= 28
                map_engine.save_manager.save_save(run.user_id, run)
                return msg
            if idx == 2:
                if p.gold < 30:
                    return get_locale_text("i18n_room_interact.dialog.err_gold", cost=30)
                ok, msg = add_bag_item(p, "skeleton_key")
                if not ok:
                    return msg
                p.gold -= 30
                map_engine.save_manager.save_save(run.user_id, run)
                return msg
            run.node_data["dialog_state"] = "start"
            map_engine.save_manager.save_save(run.user_id, run)
            return render_room_dialog(run)
        if idx == 1:
            cost = cfg["gamble_cost"]
            if p.gold < cost:
                return get_locale_text("i18n_room_interact.dialog.err_gold", cost=cost)
            p.gold -= cost
            if random.random() < 0.55:
                gain = cost * 2
                p.gold += gain
                add_bag_item(p, "smuggler_token")
                msg = get_locale_text("i18n_room_interact.dialog.broker_gamble_win", gold=gain)
            else:
                add_bag_item(p, "sugar_cube_pack")
                msg = get_locale_text("i18n_room_interact.dialog.broker_gamble_lose", cost=cost)
            map_engine.save_manager.save_save(run.user_id, run)
            return msg
        if idx == 2:
            cost = cfg["intel_cost"]
            if p.gold < cost:
                return get_locale_text("i18n_room_interact.dialog.err_gold", cost=cost)
            p.gold -= cost
            revealed = _reveal_any_special(fm, 2) if fm is not None else []
            map_engine.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_room_interact.dialog.broker_intel_ok", coords="、".join(revealed) if revealed else get_locale_text("i18n_grid_map.none"))
        if idx == 3:
            run.node_data["dialog_state"] = "trade"
            map_engine.save_manager.save_save(run.user_id, run)
            return render_room_dialog(run)
        return close_room_dialog(map_engine.save_manager, run)
    if nid == "lost_scholar":
        if idx == 1:
            hpc = cfg["study_hp_cost"]
            if p.hp <= hpc:
                return get_locale_text("i18n_room_interact.dialog.err_hp")
            p.hp -= hpc
            from ....entities import ALL_CARDS
            pool = DeckService.eligible_card_ids(None, colors=("wizard", "neutral"), rarities=("rare",))
            cid = random.choice(pool) if pool else "fireball"
            DeckService.add_card_to_deck(p, cid)
            close_room_dialog(map_engine.save_manager, run)
            return get_locale_text("i18n_room_interact.dialog.scholar_study_ok", card=ALL_CARDS[cid].name)
        if idx == 2:
            ok, msg = add_bag_item(p, "ancient_notes")
            if not ok:
                restore_sp(p, 3)
            close_room_dialog(map_engine.save_manager, run)
            return msg if ok else get_locale_text("i18n_room_interact.bag.use_espresso_beans", sp=3)
        if idx == 3:
            if fm is not None and fm.ritual_coord:
                fm.secret_clue_found = True
                if fm.ritual_coord not in fm.revealed_coords:
                    fm.revealed_coords.append(fm.ritual_coord)
                map_engine.save_manager.save_save(run.user_id, run)
                return get_locale_text("i18n_room_interact.dialog.scholar_lore_clue", coord=fm.ritual_coord)
            return get_locale_text("i18n_room_interact.dialog.scholar_lore_none")
        return close_room_dialog(map_engine.save_manager, run)
    if nid == "wounded_scout":
        if idx == 1:
            cost = cfg["aid_gold"]
            if p.gold < cost:
                return get_locale_text("i18n_room_interact.dialog.err_gold", cost=cost)
            p.gold -= cost
            add_bag_item(p, "glowing_runestone")
            if fm is not None:
                _reveal_any_special(fm, 2)
            close_room_dialog(map_engine.save_manager, run)
            return get_locale_text("i18n_room_interact.dialog.scout_aid_ok")
        if idx == 2:
            restore_sp(p, 2)
            add_bag_item(p, "sugar_cube_pack")
            close_room_dialog(map_engine.save_manager, run)
            return get_locale_text("i18n_room_interact.dialog.scout_supply_ok")
        if idx == 3:
            restore_sp(p, 1)
            p.gold += 15
            close_room_dialog(map_engine.save_manager, run)
            return get_locale_text("i18n_room_interact.dialog.scout_shield_ok")
        return close_room_dialog(map_engine.save_manager, run)
    if idx == 1:
        hpc = cfg.get("ritual_hp_cost", 6)
        if p.hp <= hpc:
            return get_locale_text("i18n_room_interact.dialog.err_hp")
        p.hp -= hpc
        sp = restore_sp(p, 5)
        old_ex = getattr(p, "exhaustion", 0)
        new_ex = reduce_exhaustion(p, 1)
        close_room_dialog(map_engine.save_manager, run)
        return get_locale_text("i18n_room_interact.dialog.keeper_bless_ok", sp=sp, cured=max(0, old_ex - new_ex))
    if idx == 2:
        if p.gold < 35:
            return get_locale_text("i18n_room_interact.dialog.err_gold", cost=35)
        p.gold -= 35
        from ....data.reward_config import TREASURE_RELIC_POOL
        avail = [r for r in TREASURE_RELIC_POOL if r not in p.relics]
        if avail:
            rid = random.choice(avail)
            p.relics.append(rid)
            from ....entities import get_relic_name
            close_room_dialog(map_engine.save_manager, run)
            return get_locale_text("i18n_explore_core.relic_gained", relic_name=get_relic_name(rid))
        add_bag_item(p, "glowing_runestone")
        close_room_dialog(map_engine.save_manager, run)
        return get_locale_text("i18n_room_interact.dialog.scout_aid_ok")
    if idx == 3:
        coords = []
        if fm is not None:
            for c in (fm.boss_coord, fm.ritual_coord):
                if c:
                    if c not in fm.revealed_coords:
                        fm.revealed_coords.append(c)
                    coords.append(c)
        map_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_room_interact.dialog.keeper_boss_reveal", coords="、".join(coords) if coords else get_locale_text("i18n_grid_map.none"))
    return close_room_dialog(map_engine.save_manager, run)


def start_npc_combat(map_engine, run, npc_id: str, npc_source: str = "grid", guest_name: str = "") -> str:
    from ....renderer import GameRenderer
    fm = getattr(run, "floor_map", None)
    coord = fm.player_coords.get(run.user_id, "A1") if fm is not None else "A1"
    if npc_source == "cafe_guest":
        enemy_name = guest_name
        cfg = CAFE_GUEST_COMBAT_STATS
        reward_item = "espresso_beans"
    else:
        cfg = ROOM_NPCS[npc_id]
        enemy_name = get_locale_text(cfg["enemy_name_key"])
        reward_item = cfg.get("reward_item", "")
    stage = max(1, int(getattr(run.player, "stage", 1) or 1))
    hp = int(cfg["base_hp"]) + stage * int(cfg.get("hp_per_stage", 2))
    npc_combat = {
        "npc_id": npc_id,
        "enemy_name": enemy_name,
        "hp": hp,
        "atk": int(cfg["atk"]) + stage // 4,
        "actions": int(cfg.get("actions", 1)),
        "bonus_actions": int(cfg.get("bonus_actions", 1)),
        "reward_gold": int(cfg.get("reward_gold", 40)),
        "reward_item": reward_item,
        "room_coord": coord,
        "npc_source": npc_source,
        "guest_name": guest_name,
    }
    if fm is not None:
        old_sid = fm.player_session_map.get(run.user_id)
        if old_sid:
            SessionContextScoper.close_session(run, old_sid, mark_cleared=False)
        SessionContextScoper.create_session(
            run,
            coord,
            "battle",
            [run.user_id],
            node_data={"difficulty": "npc_combat", "npc_combat": npc_combat},
        )
    else:
        run.node_type = "battle"
        run.node_data = {"difficulty": "npc_combat", "npc_combat": npc_combat}
    map_engine.battle_engine._init_battle_node(run, difficulty="npc_combat")
    map_engine.save_manager.save_save(run.user_id, run)
    prefix = get_locale_text("i18n_room_interact.combat.attack_start", name=enemy_name)
    return f"{prefix}\n\n{GameRenderer.render_game(run)}"


def attack_in_room(map_engine, run, query: str) -> str:
    q = (query or "").strip()
    if not q:
        return get_locale_text("i18n_room_interact.combat.attack_need_arg")
    room, _ = get_current_room(run)
    if run.node_type == "shop":
        if room is not None and room.shared_payload.get("merchant_defeated"):
            return get_locale_text("i18n_room_interact.combat.attack_already_defeated", name=get_locale_text("i18n_room_interact.npcs.shop_merchant.name"))
        cfg = ROOM_NPCS["shop_merchant"]
        mname = get_locale_text(cfg["name_key"])
        ql = q.lower()
        if ql in ("shop_merchant", mname.lower()) or ql in mname.lower() or any(ql == a.lower() for a in cfg["aliases"]) or find_entry_by_query([("shop_merchant", mname)] + [("shop_merchant", a) for a in cfg["aliases"]], q):
            return start_npc_combat(map_engine, run, "shop_merchant", npc_source="shop")
        return get_locale_text("i18n_room_interact.combat.attack_not_found", target=q)
    if run.node_type == "cafe":
        from ....data.cafe_data import NPC_SHOW_NAMES
        barista_cfg = ROOM_NPCS["cafe_barista"]
        bname = get_locale_text(barista_cfg["name_key"])
        ql = q.lower()
        if ql in ("cafe_barista", bname.lower()) or ql in bname.lower() or any(ql == a.lower() for a in barista_cfg["aliases"]) or find_entry_by_query([("cafe_barista", bname)] + [("cafe_barista", a) for a in barista_cfg["aliases"]], q):
            if room is not None and room.shared_payload.get("barista_defeated"):
                return get_locale_text("i18n_room_interact.combat.attack_already_defeated", name=bname)
            return start_npc_combat(map_engine, run, "cafe_barista", npc_source="cafe_barista")
        cafe_data = run.node_data.get("cafe_data") or {}
        npcs = list(cafe_data.get("npcs") or [])
        entries = []
        for npc in npcs:
            sname = NPC_SHOW_NAMES.get(npc, npc)
            if ql == npc.lower() or ql == sname.lower() or ql in sname.lower():
                return start_npc_combat(map_engine, run, f"cafe_guest:{npc}", npc_source="cafe_guest", guest_name=sname)
            entries.append((npc, sname))
        matched = find_entry_by_query(entries, q)
        if matched:
            return start_npc_combat(map_engine, run, f"cafe_guest:{matched}", npc_source="cafe_guest", guest_name=NPC_SHOW_NAMES.get(matched, matched))
        return get_locale_text("i18n_room_interact.combat.attack_not_found", target=q)
    if room is None:
        return get_locale_text("i18n_grid_map.err_no_floor_map")
    nid = resolve_npc_in_room(room, q)
    if not nid:
        return get_locale_text("i18n_room_interact.combat.attack_not_found", target=q)
    return start_npc_combat(map_engine, run, nid, npc_source="grid")


def handle_npc_combat_win(card_rewards, run) -> None:
    npc_info = run.node_data.get("npc_combat") or {}
    npc_id = npc_info.get("npc_id", "")
    coord = npc_info.get("room_coord", "")
    npc_source = npc_info.get("npc_source", "grid")
    reward_gold = int(npc_info.get("reward_gold", 40) or 40)
    reward_item = npc_info.get("reward_item", "")
    fm = getattr(run, "floor_map", None)
    if fm is not None and coord in fm.rooms:
        room = fm.rooms[coord]
        if npc_id and npc_id not in room.defeated_npcs:
            room.defeated_npcs.append(npc_id)
        if npc_source == "shop":
            room.shared_payload["merchant_defeated"] = True
        elif npc_source == "cafe_barista":
            room.shared_payload["barista_defeated"] = True
        elif npc_source == "cafe_guest":
            guest_key = npc_id.split(":", 1)[1] if ":" in npc_id else npc_id
            defeated_guests = room.shared_payload.setdefault("cafe_defeated_guests", [])
            if guest_key not in defeated_guests:
                defeated_guests.append(guest_key)
    run.enemies.clear()
    caller = run.user_id
    p = run.player
    note_item = ""
    if reward_item:
        ok, _ = add_bag_item(p, reward_item)
        if not ok and fm is not None and coord in fm.rooms:
            fm.rooms[coord].items.append(reward_item)
        note_item = get_locale_text("i18n_room_interact.combat.npc_win_item_note", item=get_item_display_name(reward_item))
    loot_note = get_locale_text("i18n_room_interact.combat.npc_win_loot", gold=reward_gold, item_note=note_item)
    pool = DeckService.eligible_card_ids(None, colors=("wizard", "warrior", "neutral"), rarities=("common", "rare"))
    card_picks = random.sample(pool, min(3, len(pool)))
    items = [
        {"type": "gold", "amount": reward_gold, "taken": False},
        {"type": "card_reward", "cards": card_picks, "taken": False},
    ]
    run.node_type = "reward"
    views = {
        uid: {
            "node_type": "reward",
            "data": {"items": [dict(it) for it in items], "quest_bonus": loot_note, "coop_done": False},
        }
        for uid in run.party_order if uid in run.players
    }
    stage_ready = {uid: (uid != caller) for uid in run.party_order if uid in run.players}
    run.node_data = {
        "coop_node_type": "reward",
        "player_views": views,
        "stage_ready": stage_ready,
    }
    apply_and_scope(run, caller)
    card_rewards.engine.save_manager.save_save(caller, run)
