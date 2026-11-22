import random
from typing import List, Optional, Tuple
from ....data.battle.battle_mode_config import BATTLE_MODE_FORCED_SOLO
from ....data.text.locale_data import get_locale_text
from ....data.world.open_world_config import WORLD_YOG_TEMPLE
from ....data.world.room_interact_data import CAFE_GUEST_COMBAT_STATS, ROOM_NPCS
from ....data.world.world_social_config import WORLD_SNOWFIELD
from ....data.world.yog_quest_config import YOG_FLOOR_TEMPLE
from ...inventory.bag_service import add_bag_item, get_item_display_name
from ...inventory.card_distribution import CardDistributor
from ...party.coordinator import apply_and_scope
from ...party.session import SessionContextScoper
from ...text.events import RenderedText
from ..open_world.ghost_service import OpenWorldGhostService
from ..open_world.loadout_service import is_open_world_run
from ..persistent_buffs import break_map_invisibility
from .big_room import add_effective_item, mark_effective_npc_defeated, sync_big_room_clear_state
from .dialog.registry import resolve_provider_by_name, resolve_provider_for_open
from .dialog.renderer import render_crpg_dialog_screen, render_legacy_dialog_screen
from .dialog.state import NpcMemoryStore
from .hostile_npc import is_hostile_npc, trigger_hostile_npc_battle
from .interact import get_current_room, resolve_npc_in_room


def _open_world_grid_location(run, coord: str) -> tuple[str, str]:
    fm = getattr(run, "floor_map", None)
    floor_idx = getattr(fm, "floor_index", 0) if fm is not None else 0
    world = WORLD_YOG_TEMPLE if floor_idx == YOG_FLOOR_TEMPLE else WORLD_SNOWFIELD
    return world, coord


def talk_room_npc(save_manager, run, query: str) -> Optional[str]:
    room, coord = get_current_room(run)
    if room is None:
        return None
    fm = getattr(run, "floor_map", None)
    nid = resolve_npc_in_room(room, query, fm=fm, include_hostile=False)
    if not nid:
        if run.node_type == "grid_map" and is_open_world_run(run):
            world, pos = _open_world_grid_location(run, coord)
            ghost_msg = OpenWorldGhostService.try_inspect_ghost(save_manager, world, pos, query, is_touch=False)
            if ghost_msg is not None:
                broken_msg = break_map_invisibility(run, reason="interact")
                if broken_msg:
                    save_manager.save_save(run.user_id, run)
                    return f"{broken_msg}\n{ghost_msg}"
            return ghost_msg
        return None
    broken_msg = break_map_invisibility(run, reason="interact")
    from ..encounter_lore import record_encounter_for_run

    record_encounter_for_run(save_manager, run, nid)
    from .forced_triggers import run_forced_triggers

    trigger_logs = run_forced_triggers(run, fm, room, "on_interact")

    resolved = resolve_provider_for_open(run, nid)
    node_data = None
    if resolved is not None:
        _, provider = resolved
        node_data = provider.open_dialog(save_manager, run, room, coord, nid)
    if node_data is None:
        node_data = {"npc_id": nid, "dialog_state": "start", "coord": coord}
    SessionContextScoper.create_session(run, coord, "room_dialog", [run.user_id], node_data=node_data)
    rendered = render_room_dialog(run, save_manager=save_manager)
    save_manager.save_save(run.user_id, run)
    prefix = "\n".join(x for x in (broken_msg, *trigger_logs) if x)
    return f"{prefix}\n\n{rendered}" if prefix else rendered


def _room_dialog_content(run, save_manager=None) -> Tuple[str, str, List[str]]:
    pname = str((run.node_data or {}).get("provider") or "")
    if pname:
        provider = resolve_provider_by_name(pname)
        if provider is not None:
            res = provider.render_content(run, save_manager=save_manager)
            if res is not None:
                return res
    for candidate in ("bleak_falls", "chireiden", "tutorial", "crpg_graph"):
        provider = resolve_provider_by_name(candidate)
        if provider is not None:
            res = provider.render_content(run, save_manager=save_manager)
            if res is not None:
                return res
    nid = str((run.node_data or {}).get("npc_id") or "")
    cfg = ROOM_NPCS.get(nid, {})
    name = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else nid
    return name, "", [get_locale_text("i18n_npc_crpg_core.common.opt_leave")]


def render_room_dialog(run, save_manager=None) -> str:
    name, text, opts = _room_dialog_content(run, save_manager=save_manager)
    if (run.node_data or {}).get("provider") == "crpg_graph":
        res = render_crpg_dialog_screen(run, name, [RenderedText(text=text)], opts)
        if (run.node_data or {}).get("last_outcome_nodes"):
            run.node_data["last_outcome_nodes"] = []
        return res
    return render_legacy_dialog_screen(run, name, text, opts)


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


def resume_room_dialog_after_flow(save_manager, run, msg: str, committed: bool) -> str:
    nd = run.node_data or {}
    cost = int(nd.pop("pending_room_dialog_cost", 0) or 0)
    service_key = str(nd.pop("pending_room_dialog_service", "") or "")
    return_node = str(nd.pop("pending_return_node", "") or "")
    npc_id = str(nd.get("npc_id", "") or "")
    coord = str(nd.get("coord", "") or "")
    if committed:
        if cost > 0:
            run.player.gold = max(0, int(run.player.gold) - cost)
        if service_key and npc_id:
            p_enc = NpcMemoryStore.ensure_player_encounter(run, npc_id, run.user_id, coord=coord)
            uses = p_enc.setdefault("service_uses", {})
            uses[service_key] = int(uses.get(service_key, 0) or 0) + 1
        if return_node:
            nd["node_id"] = return_node
    if nd.get("provider") == "crpg_graph":
        nd["last_outcome_nodes"] = [{"type": "rendered", "text": msg}] if msg else []
        run.node_type = "room_dialog"
        save_manager.save_save(run.user_id, run)
        return render_room_dialog(run, save_manager=save_manager)
    close_room_dialog(save_manager, run)
    return msg


def handle_room_dialog_choice(map_engine, run, idx: int) -> str:
    _, _, opts = _room_dialog_content(run, save_manager=map_engine.save_manager)
    if idx < 1 or idx > len(opts):
        return get_locale_text("err_invalid_option_idx")
    pname = str((run.node_data or {}).get("provider") or "")
    if pname:
        provider = resolve_provider_by_name(pname)
        if provider is not None:
            res = provider.handle_choice(map_engine, run, idx)
            if res is not None:
                return res
    for candidate in ("bleak_falls", "chireiden", "tutorial", "crpg_graph"):
        provider = resolve_provider_by_name(candidate)
        if provider is not None:
            res = provider.handle_choice(map_engine, run, idx)
            if res is not None:
                return res
    return close_room_dialog(map_engine.save_manager, run)


def start_npc_combat(
    map_engine,
    run,
    npc_id: str,
    npc_source: str = "grid",
    guest_name: str = "",
    non_lethal: Optional[bool] = None,
) -> str:
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
    if non_lethal is None:
        non_lethal = bool(cfg.get("non_lethal", npc_source == "grid"))
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
        "non_lethal": bool(non_lethal),
    }
    node_payload = {
        "difficulty": "npc_combat",
        "npc_combat": npc_combat,
        "battle_mode": BATTLE_MODE_FORCED_SOLO,
        "non_lethal": bool(non_lethal),
    }
    if fm is not None:
        old_sid = fm.player_session_map.get(run.user_id)
        if old_sid:
            SessionContextScoper.close_session(run, old_sid, mark_cleared=False)
        SessionContextScoper.create_session(run, coord, "battle", [run.user_id], node_data=node_payload)
    else:
        run.node_type = "battle"
        run.node_data = node_payload
    map_engine.battle_engine._init_battle_node(run, difficulty="npc_combat")
    map_engine.save_manager.save_save(run.user_id, run)
    prefix = get_locale_text("i18n_room_interact.combat.attack_start", name=enemy_name)
    return f"{prefix}\n\n{GameRenderer.render_game(run)}"


def attack_in_room(map_engine, run, query: str) -> str:
    from ...cli.base.pinyin_match import find_entry_by_query

    q = (query or "").strip()
    room, coord = get_current_room(run)
    if run.node_type == "grid_map" and is_open_world_run(run):
        if not q or not room or not resolve_npc_in_room(room, q):
            world, pos = _open_world_grid_location(run, coord)
            stats = map_engine.save_manager.load_stats(run.user_id)
            _, ghost_res = OpenWorldGhostService.try_attack_ghost(
                map_engine.save_manager,
                map_engine.battle_engine,
                run.user_id,
                stats,
                world,
                pos,
                q,
                "grid_map",
                active_run=run,
            )
            if ghost_res is not None:
                return ghost_res
            if q:
                world_social = getattr(getattr(map_engine, "grid_map_service", None), "world_social", None)
                if world_social is not None:
                    target_entry, _ = world_social.resolve_target(world, pos, q, exclude_uid=run.user_id)
                    if target_entry is not None:
                        from ...battle.pvp_service import PvpService

                        return PvpService.send_challenge(
                            map_engine.save_manager,
                            world_social,
                            run.user_id,
                            target_entry,
                            world,
                            pos,
                        )
    if not q:
        return get_locale_text("i18n_room_interact.combat.attack_need_arg")
    if run.node_type == "shop":
        if room is not None and room.shared_payload.get("merchant_defeated"):
            return get_locale_text("i18n_room_interact.combat.attack_already_defeated", name=get_locale_text("i18n_room_interact.npcs.shop_merchant.name"))
        cfg = ROOM_NPCS["shop_merchant"]
        mname = get_locale_text(cfg["name_key"])
        ql = q.lower()
        if ql in ("shop_merchant", mname.lower()) or ql in mname.lower() or any(ql == a.lower() for a in cfg["aliases"]) or find_entry_by_query([("shop_merchant", mname)] + [("shop_merchant", a) for a in cfg["aliases"]], q):
            return start_npc_combat(map_engine, run, "shop_merchant", npc_source="shop", non_lethal=False)
        return get_locale_text("i18n_room_interact.combat.attack_not_found", target=q)
    if run.node_type == "cafe":
        from ....data.world.cafe_data import NPC_SHOW_NAMES

        barista_cfg = ROOM_NPCS["cafe_barista"]
        bname = get_locale_text(barista_cfg["name_key"])
        ql = q.lower()
        if ql in ("cafe_barista", bname.lower()) or ql in bname.lower() or any(ql == a.lower() for a in barista_cfg["aliases"]) or find_entry_by_query([("cafe_barista", bname)] + [("cafe_barista", a) for a in barista_cfg["aliases"]], q):
            if room is not None and room.shared_payload.get("barista_defeated"):
                return get_locale_text("i18n_room_interact.combat.attack_already_defeated", name=bname)
            return start_npc_combat(map_engine, run, "cafe_barista", npc_source="cafe_barista", non_lethal=False)
        cafe_data = run.node_data.get("cafe_data") or {}
        npcs = list(cafe_data.get("npcs") or [])
        entries = []
        for npc in npcs:
            if not npc:
                continue
            sname = str(NPC_SHOW_NAMES.get(npc, npc))
            if ql == npc.lower() or ql == sname.lower() or ql in sname.lower():
                return start_npc_combat(map_engine, run, f"cafe_guest:{npc}", npc_source="cafe_guest", guest_name=sname, non_lethal=False)
            entries.append((npc, sname))
        matched = find_entry_by_query(entries, q)
        if matched:
            return start_npc_combat(map_engine, run, f"cafe_guest:{matched}", npc_source="cafe_guest", guest_name=NPC_SHOW_NAMES.get(matched, matched), non_lethal=False)
        return get_locale_text("i18n_room_interact.combat.attack_not_found", target=q)
    if room is None:
        return get_locale_text("i18n_grid_map.err_no_floor_map")
    fm = getattr(run, "floor_map", None)
    nid = resolve_npc_in_room(room, q, fm=fm, include_hostile=True)
    if not nid:
        return get_locale_text("i18n_room_interact.combat.attack_not_found", target=q)
    if is_hostile_npc(nid):
        return trigger_hostile_npc_battle(map_engine.grid_map_service, run, run.user_id, coord, room, nid)
    if ROOM_NPCS.get(nid, {}).get("non_hostile"):
        npc_cfg = ROOM_NPCS[nid]
        nname = get_locale_text(npc_cfg["name_key"]) if npc_cfg.get("name_key") else nid
        return get_locale_text("i18n_room_interact.combat.non_hostile_refuse", name=nname)
    return start_npc_combat(map_engine, run, nid, npc_source="grid")


def enter_post_spar_dialog(save_manager, run, npc_id: str, coord: str, result_kind: str) -> None:
    fm = getattr(run, "floor_map", None)
    if fm is not None:
        sid = fm.player_session_map.get(run.user_id)
        if sid:
            SessionContextScoper.close_session(run, sid, mark_cleared=False)
    run.enemies.clear()
    node_id = "spar_npc_yield" if result_kind == "npc_yield" else "spar_player_lost"
    node_data = {
        "npc_id": npc_id,
        "coord": coord,
        "provider": "crpg_graph",
        "node_id": node_id,
        "last_outcome_nodes": [],
        "pending_return_node": "",
    }
    if fm is not None:
        SessionContextScoper.create_session(run, coord, "room_dialog", [run.user_id], node_data=node_data)
    else:
        run.node_type = "room_dialog"
        run.node_data = node_data
    save_manager.save_save(run.user_id, run)


def finalize_npc_kill_rewards(save_manager, run, npc_id: str, coord: str) -> str:
    from ....renderer import GameRenderer

    cfg = ROOM_NPCS.get(npc_id, {})
    reward_gold = int(cfg.get("reward_gold", 40) or 40)
    reward_item = str(cfg.get("reward_item", "") or "")
    fm = getattr(run, "floor_map", None)
    if fm is not None:
        sid = fm.player_session_map.get(run.user_id)
        if sid:
            SessionContextScoper.close_session(run, sid, mark_cleared=False)
        room = fm.rooms.get(coord)
        if room is not None and npc_id:
            mark_effective_npc_defeated(fm, room, npc_id)
            sync_big_room_clear_state(fm, room)
    stats = NpcMemoryStore.load_stats(save_manager, run.user_id)
    if stats is not None and npc_id:
        NpcMemoryStore.record_npc_killed(stats, save_manager, run.user_id, npc_id)
    p = run.player
    note_item = ""
    if reward_item:
        ok, _ = add_bag_item(p, reward_item)
        if not ok and fm is not None and coord in fm.rooms:
            add_effective_item(fm, fm.rooms[coord], reward_item)
        note_item = get_locale_text("i18n_room_interact.combat.npc_win_item_note", item=get_item_display_name(reward_item))
    loot_note = get_locale_text("i18n_room_interact.combat.npc_win_loot", gold=reward_gold, item_note=note_item)
    card_picks = CardDistributor.roll("npc_combat", run, p, None, count=3)
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
    stage_ready = {uid: (uid != run.user_id) for uid in run.party_order if uid in run.players}
    run.node_data = {
        "coop_node_type": "reward",
        "player_views": views,
        "stage_ready": stage_ready,
    }
    apply_and_scope(run, run.user_id)
    save_manager.save_save(run.user_id, run)
    return GameRenderer.render_game(run)


def handle_npc_combat_win(card_rewards, run) -> None:
    npc_info = run.node_data.get("npc_combat") or {}
    npc_id = npc_info.get("npc_id", "")
    coord = npc_info.get("room_coord", "")
    npc_source = npc_info.get("npc_source", "grid")
    non_lethal_res = str(run.node_data.pop("non_lethal_result", "") or "")
    if non_lethal_res in ("npc_yield", "player_yield") and npc_source == "grid":
        enter_post_spar_dialog(card_rewards.engine.save_manager, run, npc_id, coord, non_lethal_res)
        return
    reward_gold = int(npc_info.get("reward_gold", 40) or 40)
    reward_item = npc_info.get("reward_item", "")
    fm = getattr(run, "floor_map", None)
    if fm is not None and coord in fm.rooms:
        room = fm.rooms[coord]
        if npc_id:
            mark_effective_npc_defeated(fm, room, npc_id)
            sync_big_room_clear_state(fm, room)
        if npc_source == "shop":
            room.shared_payload["merchant_defeated"] = True
        elif npc_source == "cafe_barista":
            room.shared_payload["barista_defeated"] = True
        elif npc_source == "cafe_guest":
            guest_key = npc_id.split(":", 1)[1] if ":" in npc_id else npc_id
            defeated_guests = room.shared_payload.setdefault("cafe_defeated_guests", [])
            if guest_key not in defeated_guests:
                defeated_guests.append(guest_key)
    if npc_source == "grid" and npc_id:
        stats = NpcMemoryStore.load_stats(card_rewards.engine.save_manager, run.user_id)
        NpcMemoryStore.record_npc_killed(stats, card_rewards.engine.save_manager, run.user_id, npc_id)
    run.enemies.clear()
    caller = run.user_id
    p = run.player
    note_item = ""
    if reward_item:
        ok, _ = add_bag_item(p, reward_item)
        if not ok and fm is not None and coord in fm.rooms:
            add_effective_item(fm, fm.rooms[coord], reward_item)
        note_item = get_locale_text("i18n_room_interact.combat.npc_win_item_note", item=get_item_display_name(reward_item))
    loot_note = get_locale_text("i18n_room_interact.combat.npc_win_loot", gold=reward_gold, item_note=note_item)
    card_picks = CardDistributor.roll("npc_combat", run, p, None, count=3)
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
