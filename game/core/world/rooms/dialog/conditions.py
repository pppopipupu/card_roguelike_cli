from typing import Any, Callable, Dict
from .state import NpcMemoryStore

DIALOG_CONDITIONS: Dict[str, Callable[[Any, dict], bool]] = {}


def register_dialog_condition(name: str):
    def decorator(fn: Callable[[Any, dict], bool]):
        DIALOG_CONDITIONS[name] = fn
        return fn

    return decorator


def eval_condition(cond: Any, ctx: dict) -> bool:
    if cond is None or cond == {}:
        return True
    if isinstance(cond, list):
        return all(eval_condition(c, ctx) for c in cond)
    if not isinstance(cond, dict):
        return bool(cond)
    if "all" in cond:
        return all(eval_condition(c, ctx) for c in cond["all"])
    if "any" in cond:
        return any(eval_condition(c, ctx) for c in cond["any"])
    if "not" in cond:
        return not eval_condition(cond["not"], ctx)
    for key, val in cond.items():
        fn = DIALOG_CONDITIONS.get(key)
        if fn is None:
            return False
        if not fn(val, ctx):
            return False
    return True


@register_dialog_condition("affinity_gte")
def _cond_affinity_gte(val, ctx: dict) -> bool:
    return int((ctx.get("run_npc") or {}).get("affinity", 0)) >= int(val)


@register_dialog_condition("affinity_lte")
def _cond_affinity_lte(val, ctx: dict) -> bool:
    return int((ctx.get("run_npc") or {}).get("affinity", 0)) <= int(val)


@register_dialog_condition("attitude_in")
def _cond_attitude_in(val, ctx: dict) -> bool:
    aff = int((ctx.get("run_npc") or {}).get("affinity", 0))
    tier = NpcMemoryStore.attitude_tier(aff)
    allowed = val if isinstance(val, (list, tuple, set, frozenset)) else [val]
    return tier in allowed


@register_dialog_condition("met_count_gte")
def _cond_met_count_gte(val, ctx: dict) -> bool:
    return int((ctx.get("run_npc") or {}).get("met_count", 0)) >= int(val)


@register_dialog_condition("local_flag")
def _cond_local_flag(val, ctx: dict) -> bool:
    flags = set((ctx.get("p_enc") or {}).get("local_flags") or ())
    return str(val) in flags


@register_dialog_condition("known_flag")
def _cond_known_flag(val, ctx: dict) -> bool:
    flags = set((ctx.get("run_npc") or {}).get("known_flags") or ())
    return str(val) in flags


@register_dialog_condition("world_flag")
def _cond_world_flag(val, ctx: dict) -> bool:
    flags = set((ctx.get("run_bucket") or {}).get("world_flags") or ())
    return str(val) in flags


@register_dialog_condition("cycle_flag")
def _cond_cycle_flag(val, ctx: dict) -> bool:
    cmem = NpcMemoryStore.get_cycle_memory_readonly(ctx.get("stats"))
    return str(val) in set(cmem.get("cycle_flags") or ())


@register_dialog_condition("killed_before")
def _cond_killed_before(val, ctx: dict) -> bool:
    cmem = NpcMemoryStore.get_cycle_memory_readonly(ctx.get("stats"))
    target_id = ctx.get("npc_id") if val is True else str(val)
    return int((cmem.get("killed_npcs") or {}).get(target_id, 0) or 0) > 0


@register_dialog_condition("spared_before")
def _cond_spared_before(val, ctx: dict) -> bool:
    cmem = NpcMemoryStore.get_cycle_memory_readonly(ctx.get("stats"))
    target_id = ctx.get("npc_id") if val is True else str(val)
    return int((cmem.get("spared_npcs") or {}).get(target_id, 0) or 0) > 0


@register_dialog_condition("has_item")
def _cond_has_item(val, ctx: dict) -> bool:
    p = ctx.get("player")
    if p is None:
        return False
    return str(val) in (getattr(p, "bag_items", None) or ())


@register_dialog_condition("gold_gte")
def _cond_gold_gte(val, ctx: dict) -> bool:
    p = ctx.get("player")
    return int(getattr(p, "gold", 0) or 0) >= int(val)


@register_dialog_condition("hp_gt")
def _cond_hp_gt(val, ctx: dict) -> bool:
    p = ctx.get("player")
    return int(getattr(p, "hp", 0) or 0) > int(val)


@register_dialog_condition("player_class")
def _cond_player_class(val, ctx: dict) -> bool:
    p = ctx.get("player")
    cls_name = str(getattr(p, "selected_class", "") or "")
    allowed = val if isinstance(val, (list, tuple, set, frozenset)) else [val]
    return cls_name in allowed


@register_dialog_condition("has_unupgraded_card")
def _cond_has_unupgraded_card(val, ctx: dict) -> bool:
    p = ctx.get("player")
    if p is None:
        return False
    from .....data.cards.card_upgrade_data import CARD_UPGRADE_CONFIG

    has_card = any(not c.upgraded and c.id in CARD_UPGRADE_CONFIG for c in (getattr(p, "deck", None) or ()))
    return has_card if bool(val) else not has_card


@register_dialog_condition("floor_has_ritual")
def _cond_floor_has_ritual(val, ctx: dict) -> bool:
    fm = getattr(ctx.get("run"), "floor_map", None)
    has_ritual = bool(fm is not None and getattr(fm, "ritual_coord", ""))
    return has_ritual if bool(val) else not has_ritual


@register_dialog_condition("service_available")
def _cond_service_available(val, ctx: dict) -> bool:
    service_key = str(val)
    graph = ctx.get("graph") or {}
    quotas = graph.get("service_quotas") or {}
    limit = int(quotas.get(service_key, 1))
    used = int(((ctx.get("p_enc") or {}).get("service_uses") or {}).get(service_key, 0) or 0)
    return used < limit


@register_dialog_condition("not_consumed")
def _cond_not_consumed(val, ctx: dict) -> bool:
    consumed = set((ctx.get("p_enc") or {}).get("consumed_options") or ())
    return str(val) not in consumed


@register_dialog_condition("check_not_tried")
def _cond_check_not_tried(val, ctx: dict) -> bool:
    checked = (ctx.get("p_enc") or {}).get("checked_nodes") or {}
    return str(val) not in checked


@register_dialog_condition("group_unlocked")
def _cond_group_unlocked(val, ctx: dict) -> bool:
    locked = set((ctx.get("p_enc") or {}).get("locked_groups") or ())
    return str(val) not in locked


@register_dialog_condition("quest_status")
def _cond_quest_status(val, ctx: dict) -> bool:
    if not isinstance(val, dict):
        return False
    from .quest_hooks import get_quest_status

    qid = str(val.get("id", ""))
    expected = val.get("status")
    status = get_quest_status(ctx.get("run"), ctx.get("stats"), qid)
    if isinstance(expected, (list, tuple, set, frozenset)):
        return status in expected
    return status == expected


@register_dialog_condition("quest_ready")
def _cond_quest_ready(val, ctx: dict) -> bool:
    from .quest_hooks import is_quest_ready_to_turn_in

    return is_quest_ready_to_turn_in(ctx.get("run"), ctx.get("stats"), str(val))


@register_dialog_condition("can_accept_npc_quest")
def _cond_can_accept_npc_quest(val, ctx: dict) -> bool:
    from .quest_hooks import can_accept_quest

    return can_accept_quest(ctx.get("run"), ctx.get("stats"), str(val))


@register_dialog_condition("has_recap")
def _cond_has_recap(val, ctx: dict) -> bool:
    p_enc = ctx.get("p_enc") or {}
    if p_enc.get("recap_entries"):
        return bool(val)
    from .quest_hooks import has_active_quest_for_npc

    has_any = has_active_quest_for_npc(ctx.get("run"), ctx.get("stats"), str(ctx.get("npc_id", "")))
    return has_any if bool(val) else not has_any


@register_dialog_condition("world_unclaimed")
def _cond_world_unclaimed(val, ctx: dict) -> bool:
    claimed = set(((ctx.get("enc") or {}).get("world") or {}).get("shared_claimed") or ())
    return str(val) not in claimed


@register_dialog_condition("spared_here")
def _cond_spared_here(val, ctx: dict) -> bool:
    spared = bool(((ctx.get("enc") or {}).get("world") or {}).get("spared", False))
    return spared if bool(val) else not spared


@register_dialog_condition("departed_here")
def _cond_departed_here(val, ctx: dict) -> bool:
    departed = bool(((ctx.get("enc") or {}).get("world") or {}).get("departed", False))
    return departed if bool(val) else not departed


@register_dialog_condition("not_attacked_hostile")
def _cond_not_hostile(val, ctx: dict) -> bool:
    aff = int((ctx.get("run_npc") or {}).get("affinity", 0))
    is_hostile = aff <= -4
    return (not is_hostile) if bool(val) else is_hostile


@register_dialog_condition("encounter_turns_gte")
def _cond_turns_gte(val, ctx: dict) -> bool:
    return int((ctx.get("p_enc") or {}).get("talk_turns", 0)) >= int(val)


@register_dialog_condition("has_enchanted_card")
def _cond_has_enchanted_card(val, ctx: dict) -> bool:
    p = ctx.get("player")
    if p is None:
        return False
    has_any = any(bool(getattr(c, "enchantments", None)) for c in (getattr(p, "deck", None) or ()))
    return has_any if bool(val) else not has_any


@register_dialog_condition("enchanted_count_gte")
def _cond_enchanted_count_gte(val, ctx: dict) -> bool:
    p = ctx.get("player")
    if p is None:
        return False
    cnt = sum(1 for c in (getattr(p, "deck", None) or ()) if getattr(c, "enchantments", None))
    return cnt >= int(val)


@register_dialog_condition("has_curse_card")
def _cond_has_curse_card(val, ctx: dict) -> bool:
    p = ctx.get("player")
    if p is None:
        return False
    from .....entities import ALL_CARDS

    has_any = any(getattr(ALL_CARDS.get(c), "color", "") == "curse" for c in (getattr(p, "deck", None) or ()))
    return has_any if bool(val) else not has_any
