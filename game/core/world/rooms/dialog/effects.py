import random
from typing import Any, Callable, Dict, List
from .....data.entities.gem_data import GEM_CONFIG
from .....data.entities.potion_data import roll_potion
from .....data.progression.reward_config import TREASURE_RELIC_POOL
from .....data.text.locale_data import get_locale_text
from .....data.world.room_interact_data import ROOM_NPCS
from ....inventory.bag_service import add_bag_item, get_item_display_name
from ....inventory.card_distribution import CardDistributor
from ....inventory.deck_service import DeckService
from ....inventory.relic_service import grant_relic
from ....progress.achievement_service import record_run_achievement_stat
from ....text.events import TextNode, locale_text
from ...persistent_buffs import add_persistent_buff
from ...sp_system import reduce_exhaustion, restore_sp
from ..big_room import add_effective_item
from ..interact import _reveal_any_special
from .state import NpcMemoryStore

DIALOG_EFFECTS: Dict[str, Callable[[dict, dict, List[TextNode]], Any]] = {}


def register_dialog_effect(name: str):
    def decorator(fn: Callable[[dict, dict, List[TextNode]], Any]):
        DIALOG_EFFECTS[name] = fn
        return fn

    return decorator


def apply_effects(effects: list, ctx: dict) -> Dict[str, Any]:
    outcomes: List[TextNode] = []
    control: Dict[str, Any] = {}
    for eff in effects or ():
        if not isinstance(eff, dict):
            continue
        etype = str(eff.get("type", ""))
        fn = DIALOG_EFFECTS.get(etype)
        if fn is None:
            continue
        res = fn(eff, ctx, outcomes)
        if isinstance(res, dict):
            control.update(res)
            if control.get("halt"):
                break
    control["outcomes"] = outcomes
    return control


def _give_item_or_drop(run, fm, room, item_id: str) -> str:
    p = run.player
    ok, _ = add_bag_item(p, item_id)
    if not ok and fm is not None and room is not None:
        add_effective_item(fm, room, item_id)
    return get_item_display_name(item_id)


@register_dialog_effect("message")
def _eff_message(eff: dict, ctx: dict, outcomes: List[TextNode]):
    key = str(eff.get("key", ""))
    if key:
        outcomes.append(locale_text(key, params=dict(eff.get("params") or {})))


@register_dialog_effect("gold")
def _eff_gold(eff: dict, ctx: dict, outcomes: List[TextNode]):
    p = ctx["player"]
    amount = int(eff.get("amount", 0))
    p.gold = max(0, int(getattr(p, "gold", 0) or 0) + amount)
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"amount": abs(amount), "gold": abs(amount)}))


@register_dialog_effect("gp")
def _eff_gp(eff: dict, ctx: dict, outcomes: List[TextNode]):
    stats = ctx.get("stats")
    if stats is None:
        return
    amount = int(eff.get("amount", 0))
    stats.gp = max(0, int(getattr(stats, "gp", 0) or 0) + amount)
    NpcMemoryStore.save_stats(ctx.get("save_manager"), ctx["uid"], stats)
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"gp": amount}))


@register_dialog_effect("hp")
def _eff_hp(eff: dict, ctx: dict, outcomes: List[TextNode]):
    p = ctx["player"]
    amount = int(eff.get("amount", 0))
    before = int(p.hp)
    if amount >= 0:
        p.hp = min(int(p.max_hp), before + amount)
        delta = p.hp - before
    else:
        min_hp = int(eff.get("min_hp", 1))
        p.hp = max(min_hp, before + amount)
        delta = before - p.hp
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"heal": delta, "dmg": delta, "hp": delta}))


@register_dialog_effect("max_hp")
def _eff_max_hp(eff: dict, ctx: dict, outcomes: List[TextNode]):
    p = ctx["player"]
    amount = int(eff.get("amount", 0))
    min_limit = int(eff.get("min_max_hp", 1))
    if amount < 0 and int(p.max_hp) <= min_limit:
        delta = 0
    else:
        old = int(p.max_hp)
        p.max_hp = max(1, old + amount)
        p.hp = min(int(p.hp), int(p.max_hp))
        delta = abs(int(p.max_hp) - old)
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"max_hp": delta}))


@register_dialog_effect("sp")
def _eff_sp(eff: dict, ctx: dict, outcomes: List[TextNode]):
    p = ctx["player"]
    amount = int(eff.get("amount", 0))
    gained = restore_sp(p, amount) if amount > 0 else 0
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"sp": gained}))


@register_dialog_effect("exhaustion")
def _eff_exhaustion(eff: dict, ctx: dict, outcomes: List[TextNode]):
    p = ctx["player"]
    amount = int(eff.get("amount", 0))
    cured = 0
    if amount < 0:
        old_ex = int(getattr(p, "exhaustion", 0) or 0)
        new_ex = reduce_exhaustion(p, abs(amount))
        cured = max(0, old_ex - new_ex)
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"cured": cured}))


@register_dialog_effect("shield")
def _eff_shield(eff: dict, ctx: dict, outcomes: List[TextNode]):
    p = ctx["player"]
    amount = int(eff.get("amount", 0))
    p.shield = max(0, int(getattr(p, "shield", 0) or 0) + amount)
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"shield": amount}))


@register_dialog_effect("give_item")
def _eff_give_item(eff: dict, ctx: dict, outcomes: List[TextNode]):
    run = ctx["run"]
    fm = getattr(run, "floor_map", None)
    room = ctx.get("room")
    if eff.get("random_potion"):
        pid = roll_potion(getattr(ctx["player"], "selected_class", "法师"))
        item_id = f"potion:{pid}"
    elif eff.get("pool"):
        item_id = str(random.choice(list(eff["pool"])))
    else:
        item_id = str(eff.get("item_id", ""))
    if not item_id:
        return
    iname = _give_item_or_drop(run, fm, room, item_id)
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"item": iname}))


@register_dialog_effect("consume_item")
def _eff_consume_item(eff: dict, ctx: dict, outcomes: List[TextNode]):
    p = ctx["player"]
    item_id = str(eff.get("item_id", ""))
    bag = getattr(p, "bag_items", None)
    if isinstance(bag, list) and item_id in bag:
        bag.remove(item_id)


@register_dialog_effect("add_buff")
def _eff_add_buff(eff: dict, ctx: dict, outcomes: List[TextNode]):
    p = ctx["player"]
    buff_id = str(eff.get("buff_id", ""))
    stacks = int(eff.get("stacks", 1))
    if buff_id:
        add_persistent_buff(p, buff_id, stacks)
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"stacks": stacks}))


@register_dialog_effect("add_card")
def _eff_add_card(eff: dict, ctx: dict, outcomes: List[TextNode]):
    from .....entities import ALL_CARDS

    run = ctx["run"]
    p = ctx["player"]
    pool = str(eff.get("pool", "npc_scholar"))
    fallback = str(eff.get("fallback", "fireball"))
    cid = str(eff.get("card_id") or "")
    if not cid:
        cid = CardDistributor.roll_one(pool, run, p, None, fallback=fallback) or fallback
    DeckService.add_card_to_deck(p, cid)
    cname = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"card": cname}))


@register_dialog_effect("grant_relic")
def _eff_grant_relic(eff: dict, ctx: dict, outcomes: List[TextNode]):
    from .....entities import get_relic_name

    p = ctx["player"]
    run = ctx["run"]
    fm = getattr(run, "floor_map", None)
    avail = [r for r in TREASURE_RELIC_POOL if r not in getattr(p, "relics", ())]
    if avail:
        rid = random.choice(avail)
        grant_relic(p, rid)
        key = eff.get("key")
        if key:
            outcomes.append(locale_text(str(key), params={"relic_name": get_relic_name(rid)}))
    else:
        fallback_item = str(eff.get("fallback_item", "glowing_runestone"))
        iname = _give_item_or_drop(run, fm, ctx.get("room"), fallback_item)
        fkey = eff.get("fallback_key")
        if fkey:
            outcomes.append(locale_text(str(fkey), params={"item": iname}))


@register_dialog_effect("reveal_rooms")
def _eff_reveal_rooms(eff: dict, ctx: dict, outcomes: List[TextNode]):
    run = ctx["run"]
    fm = getattr(run, "floor_map", None)
    count = int(eff.get("count", 1))
    revealed = _reveal_any_special(fm, count) if fm is not None else []
    sep = get_locale_text("i18n_cli_core.list_separator")
    coords_str = sep.join(revealed) if revealed else ""
    recap_id = eff.get("recap_id")
    if recap_id and revealed:
        NpcMemoryStore.add_recap(
            ctx["p_enc"],
            str(recap_id),
            str(eff.get("recap_key") or "i18n_npc_crpg_core.recap.revealed_coords"),
            {"coords": coords_str},
        )
    key = eff.get("key") if revealed else (eff.get("empty_key") or eff.get("key"))
    if key:
        outcomes.append(locale_text(str(key), params={"coords": coords_str, "count": len(revealed)}))


@register_dialog_effect("reveal_ritual")
def _eff_reveal_ritual(eff: dict, ctx: dict, outcomes: List[TextNode]):
    run = ctx["run"]
    fm = getattr(run, "floor_map", None)
    if fm is not None and getattr(fm, "ritual_coord", ""):
        fm.secret_clue_found = True
        if fm.ritual_coord not in fm.revealed_coords:
            fm.revealed_coords.append(fm.ritual_coord)
        record_run_achievement_stat(ctx.get("save_manager"), run, "secret_clues_found", 1)
        recap_id = eff.get("recap_id")
        if recap_id:
            NpcMemoryStore.add_recap(
                ctx["p_enc"],
                str(recap_id),
                str(eff.get("recap_key") or "i18n_npc_crpg_core.recap.ritual_coord"),
                {"coord": fm.ritual_coord},
            )
        key = eff.get("key")
        if key:
            outcomes.append(locale_text(str(key), params={"coord": fm.ritual_coord}))
    else:
        empty_key = eff.get("empty_key")
        if empty_key:
            outcomes.append(locale_text(str(empty_key)))


@register_dialog_effect("reveal_boss")
def _eff_reveal_boss(eff: dict, ctx: dict, outcomes: List[TextNode]):
    run = ctx["run"]
    fm = getattr(run, "floor_map", None)
    coords = []
    if fm is not None:
        targets = (fm.boss_coord,) if eff.get("boss_only") else (fm.boss_coord, fm.ritual_coord)
        for c in targets:
            if c:
                if c not in fm.revealed_coords:
                    fm.revealed_coords.append(c)
                coords.append(c)
    sep = get_locale_text("i18n_cli_core.list_separator")
    coords_str = sep.join(coords)
    recap_id = eff.get("recap_id")
    if recap_id and coords:
        NpcMemoryStore.add_recap(
            ctx["p_enc"],
            str(recap_id),
            str(eff.get("recap_key") or "i18n_npc_crpg_core.recap.revealed_coords"),
            {"coords": coords_str},
        )
    key = eff.get("key") if coords else (eff.get("empty_key") or eff.get("key"))
    if key:
        outcomes.append(locale_text(str(key), params={"coords": coords_str}))


@register_dialog_effect("affinity")
def _eff_affinity(eff: dict, ctx: dict, outcomes: List[TextNode]):
    delta = int(eff.get("delta", 0))
    NpcMemoryStore.add_affinity(
        ctx["run"],
        ctx.get("stats"),
        ctx.get("save_manager"),
        ctx["uid"],
        ctx["npc_id"],
        delta,
        ctx["graph"],
    )


@register_dialog_effect("set_local_flag")
def _eff_set_local_flag(eff: dict, ctx: dict, outcomes: List[TextNode]):
    flag = str(eff.get("flag", ""))
    flags = ctx["p_enc"].setdefault("local_flags", [])
    if flag and flag not in flags:
        flags.append(flag)


@register_dialog_effect("set_known_flag")
def _eff_set_known_flag(eff: dict, ctx: dict, outcomes: List[TextNode]):
    flag = str(eff.get("flag", ""))
    flags = ctx["run_npc"].setdefault("known_flags", [])
    if flag and flag not in flags:
        flags.append(flag)


@register_dialog_effect("set_world_flag")
def _eff_set_world_flag(eff: dict, ctx: dict, outcomes: List[TextNode]):
    flag = str(eff.get("flag", ""))
    flags = ctx["run_bucket"].setdefault("world_flags", [])
    if flag and flag not in flags:
        flags.append(flag)


@register_dialog_effect("set_cycle_flag")
def _eff_set_cycle_flag(eff: dict, ctx: dict, outcomes: List[TextNode]):
    flag = str(eff.get("flag", ""))
    stats = ctx.get("stats")
    if not flag or stats is None:
        return
    cmem = NpcMemoryStore.ensure_cycle_memory(stats)
    flags = cmem["cycle_flags"]
    if flag not in flags:
        flags.append(flag)
        NpcMemoryStore.save_stats(ctx.get("save_manager"), ctx["uid"], stats)


@register_dialog_effect("add_recap")
def _eff_add_recap(eff: dict, ctx: dict, outcomes: List[TextNode]):
    rid = str(eff.get("id", ""))
    lkey = str(eff.get("key", ""))
    if rid and lkey:
        NpcMemoryStore.add_recap(ctx["p_enc"], rid, lkey, eff.get("params") or {})


@register_dialog_effect("consume_service")
def _eff_consume_service(eff: dict, ctx: dict, outcomes: List[TextNode]):
    skey = str(eff.get("service", ""))
    if skey:
        uses = ctx["p_enc"].setdefault("service_uses", {})
        uses[skey] = int(uses.get(skey, 0) or 0) + int(eff.get("amount", 1))


@register_dialog_effect("lock_group")
def _eff_lock_group(eff: dict, ctx: dict, outcomes: List[TextNode]):
    gid = str(eff.get("group", ""))
    groups = ctx["p_enc"].setdefault("locked_groups", [])
    if gid and gid not in groups:
        groups.append(gid)


@register_dialog_effect("claim_world")
def _eff_claim_world(eff: dict, ctx: dict, outcomes: List[TextNode]):
    cid = str(eff.get("id", ""))
    claimed = ctx["enc"]["world"].setdefault("shared_claimed", [])
    if cid and cid not in claimed:
        claimed.append(cid)


@register_dialog_effect("mark_spared")
def _eff_mark_spared(eff: dict, ctx: dict, outcomes: List[TextNode]):
    ctx["enc"]["world"]["spared"] = True
    NpcMemoryStore.record_npc_spared(ctx.get("stats"), ctx.get("save_manager"), ctx["uid"], ctx["npc_id"])


@register_dialog_effect("mark_departed")
def _eff_mark_departed(eff: dict, ctx: dict, outcomes: List[TextNode]):
    ctx["enc"]["world"]["departed"] = True


@register_dialog_effect("accept_quest")
def _eff_accept_quest(eff: dict, ctx: dict, outcomes: List[TextNode]):
    from .quest_hooks import accept_npc_quest

    qid = str(eff.get("quest_id", ""))
    if not qid:
        return
    msg_node = accept_npc_quest(ctx["run"], ctx.get("stats"), ctx.get("save_manager"), ctx["uid"], qid)
    if msg_node is not None:
        outcomes.append(msg_node)


@register_dialog_effect("advance_quest")
def _eff_advance_quest(eff: dict, ctx: dict, outcomes: List[TextNode]):
    from .quest_hooks import record_npc_quest_event

    ev_type = str(eff.get("event_type", "custom"))
    payload = dict(eff.get("payload") or {})
    notes = record_npc_quest_event(ctx["run"], ctx.get("stats"), ev_type, payload, save_manager=ctx.get("save_manager"))
    outcomes.extend(notes)


@register_dialog_effect("complete_quest")
def _eff_complete_quest(eff: dict, ctx: dict, outcomes: List[TextNode]):
    from .quest_hooks import complete_npc_quest

    qid = str(eff.get("quest_id", ""))
    if not qid:
        return
    msg_node = complete_npc_quest(ctx["run"], ctx.get("stats"), ctx.get("save_manager"), ctx["uid"], qid)
    if msg_node is not None:
        outcomes.append(msg_node)
    if qid not in ctx["run_npc"].setdefault("completed_quests", []):
        ctx["run_npc"]["completed_quests"].append(qid)


@register_dialog_effect("record_achievement")
def _eff_record_achievement(eff: dict, ctx: dict, outcomes: List[TextNode]):
    stat = str(eff.get("stat", ""))
    delta = int(eff.get("delta", 1))
    if stat:
        record_run_achievement_stat(ctx.get("save_manager"), ctx["run"], stat, delta)


@register_dialog_effect("upgrade_free_card")
def _eff_upgrade_free_card(eff: dict, ctx: dict, outcomes: List[TextNode]):
    from .....data.cards.card_upgrade_data import CARD_UPGRADE_CONFIG
    from .....entities import ALL_CARDS
    import copy

    p = ctx["player"]
    unupgraded = [c for c in p.deck if not c.upgraded and c.id in CARD_UPGRADE_CONFIG]
    if unupgraded:
        target = unupgraded[0]
        old_name = ALL_CARDS[target].name
        upgraded = copy.copy(target)
        upgraded.upgraded = True
        p.deck.remove(target)
        p.deck.append(upgraded)
        new_name = ALL_CARDS[upgraded].name
        key = eff.get("key")
        if key:
            outcomes.append(locale_text(str(key), params={"old": old_name, "new": new_name}))
        return
    fallback_gold = int(eff.get("fallback_gold", 30))
    p.gold += fallback_gold
    fkey = eff.get("fallback_key")
    if fkey:
        outcomes.append(locale_text(str(fkey), params={"gold": fallback_gold}))


@register_dialog_effect("start_upgrade")
def _eff_start_upgrade(eff: dict, ctx: dict, outcomes: List[TextNode]):
    run = ctx["run"]
    cost = int(eff.get("cost", 0))
    service_key = str(eff.get("service", ""))
    return_node = str(eff.get("return_node", ""))
    run.node_data["upgrade_source"] = "room_dialog"
    run.node_data["pending_room_dialog_cost"] = cost
    run.node_data["pending_room_dialog_service"] = service_key
    run.node_data["pending_return_node"] = return_node
    run.node_data["pending_upgrade"] = True
    return {"halt": True, "flow": "UPGRADE_FLOW"}


@register_dialog_effect("start_gem")
def _eff_start_gem(eff: dict, ctx: dict, outcomes: List[TextNode]):
    run = ctx["run"]
    cost = int(eff.get("cost", 0))
    service_key = str(eff.get("service", ""))
    return_node = str(eff.get("return_node", ""))
    gid = random.choice(list(GEM_CONFIG.keys()))
    next_data = dict(run.node_data)
    next_data["pending_room_dialog_cost"] = cost
    next_data["pending_room_dialog_service"] = service_key
    next_data["pending_return_node"] = return_node
    return {"halt": True, "flow": "GEM_FLOW", "gem_id": gid, "next_data": next_data}


@register_dialog_effect("start_combat")
def _eff_start_combat(eff: dict, ctx: dict, outcomes: List[TextNode]):
    non_lethal = bool(eff.get("non_lethal", True))
    intro_key = str(eff.get("intro_key", ""))
    return {"halt": True, "flow": "COMBAT_FLOW", "non_lethal": non_lethal, "intro_key": intro_key}


@register_dialog_effect("execute_npc_kill")
def _eff_execute_npc_kill(eff: dict, ctx: dict, outcomes: List[TextNode]):
    return {"halt": True, "flow": "EXECUTE_KILL_FLOW"}


@register_dialog_effect("gamble")
def _eff_gamble(eff: dict, ctx: dict, outcomes: List[TextNode]):
    p = ctx["player"]
    cost = int(eff.get("cost", 20))
    win_chance = float(eff.get("win_chance", 0.55))
    if eff.get("rigged_exposed_flag") and eff["rigged_exposed_flag"] in (ctx["p_enc"].get("local_flags") or ()):
        win_chance = float(eff.get("exposed_chance", 0.80))
    if random.random() < win_chance:
        gain = cost * 2
        p.gold += gain
        _give_item_or_drop(ctx["run"], getattr(ctx["run"], "floor_map", None), ctx.get("room"), str(eff.get("win_item", "smuggler_token")))
        wkey = eff.get("win_key")
        if wkey:
            outcomes.append(locale_text(str(wkey), params={"gold": gain}))
    else:
        _give_item_or_drop(ctx["run"], getattr(ctx["run"], "floor_map", None), ctx.get("room"), str(eff.get("lose_item", "sugar_cube_pack")))
        lkey = eff.get("lose_key")
        if lkey:
            outcomes.append(locale_text(str(lkey), params={"cost": cost}))


@register_dialog_effect("close_dialog")
def _eff_close_dialog(eff: dict, ctx: dict, outcomes: List[TextNode]):
    return {"halt": True, "flow": "CLOSE_FLOW"}
