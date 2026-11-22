import random
from typing import Callable, Dict, List
from ....data.content.chaos_expansion_data import FORCED_TRIGGER_CONFIGS
from ....data.text.locale_data import get_locale_text
from ..persistent_buffs import add_persistent_buff
from ..sp_system import consume_sp, restore_sp
from .big_room import get_big_room

FORCED_TRIGGER_HANDLERS: Dict[str, Callable] = {}


def register_forced_trigger(*trigger_ids: str):
    def decorator(fn: Callable):
        for tid in trigger_ids:
            FORCED_TRIGGER_HANDLERS[tid] = fn
        return fn

    return decorator


def _ensure_trigger_list(holder) -> List[dict]:
    if holder is None:
        return []
    items = holder.shared_payload.get("forced_triggers")
    if not isinstance(items, list):
        items = []
        holder.shared_payload["forced_triggers"] = items
    return items


def attach_room_triggers(fm, coord: str, triggers: List[dict]) -> None:
    if fm is None or coord not in fm.rooms or not triggers:
        return
    room = fm.rooms[coord]
    br = get_big_room(fm, room)
    holder = br if br is not None else room
    existing = _ensure_trigger_list(holder)
    existing_ids = {t.get("id") for t in existing if isinstance(t, dict)}
    for entry in triggers:
        tid = entry.get("id", "")
        if not tid or tid in existing_ids:
            continue
        existing.append(
            {
                "id": tid,
                "timing": entry.get("timing", "on_enter"),
                "once": bool(entry.get("once", True)),
                "chance": float(entry.get("chance", 1.0)),
                "triggered": False,
            }
        )
        existing_ids.add(tid)


def seed_floor_forced_triggers(fm, floor_index: int) -> None:
    if fm is None:
        return
    from ....data.world.big_room_config import BIG_ROOM_TEMPLATES

    for br in (getattr(fm, "big_rooms", None) or {}).values():
        tpl = BIG_ROOM_TEMPLATES.get(br.template_id, {})
        tlist = tpl.get("forced_triggers") or []
        if tlist:
            holder_list = _ensure_trigger_list(br)
            existing_ids = {t.get("id") for t in holder_list if isinstance(t, dict)}
            for entry in tlist:
                tid = entry.get("id", "")
                if tid and tid not in existing_ids:
                    holder_list.append(
                        {
                            "id": tid,
                            "timing": entry.get("timing", "on_enter"),
                            "once": bool(entry.get("once", True)),
                            "chance": float(entry.get("chance", 1.0)),
                            "triggered": False,
                        }
                    )
                    existing_ids.add(tid)

    rng = random.Random(f"ft:{floor_index}:{fm.width}x{fm.height}:{len(fm.rooms)}")
    candidates = [
        c
        for c in sorted(fm.rooms.keys())
        if not fm.rooms[c].big_room_id
        and fm.rooms[c].room_type in ("empty", "event", "treasure")
        and c != fm.ritual_coord
    ]
    rng.shuffle(candidates)
    enter_picks = candidates[: min(2, len(candidates))]
    for c in enter_picks:
        attach_room_triggers(
            fm,
            c,
            [{"id": "chaos_dimensional_sneak", "timing": "on_enter", "once": True, "chance": 1.0}],
        )
    interact_candidates = [
        c
        for c in sorted(fm.rooms.keys())
        if not fm.rooms[c].big_room_id
        and (fm.rooms[c].npcs or fm.rooms[c].props)
        and fm.rooms[c].room_type not in ("spawn", "boss", "secret_boss", "downstairs")
    ]
    rng.shuffle(interact_candidates)
    for c in interact_candidates[: min(2, len(interact_candidates))]:
        attach_room_triggers(
            fm,
            c,
            [{"id": "chaos_interact_whim", "timing": "on_interact", "once": True, "chance": 1.0}],
        )


def run_forced_triggers(run, fm, room, timing: str) -> List[str]:
    if run is None or room is None:
        return []
    if fm is not None and fm.floor_flags.get("chireiden_zone"):
        from .. import chireiden as _chireiden_mod
    logs: List[str] = []
    holders = []
    br = get_big_room(fm, room) if fm is not None else None
    if br is not None:
        holders.append(br)
    holders.append(room)
    for holder in holders:
        tlist = holder.shared_payload.get("forced_triggers")
        if not isinstance(tlist, list):
            continue
        for entry in tlist:
            if not isinstance(entry, dict) or entry.get("timing") != timing:
                continue
            if entry.get("once", True) and entry.get("triggered"):
                continue
            tid = entry.get("id", "")
            handler = FORCED_TRIGGER_HANDLERS.get(tid)
            if handler is None:
                continue
            chance = float(entry.get("chance", 1.0))
            if chance < 1.0 and random.random() > chance:
                continue
            entry["triggered"] = True
            msg = handler(run, fm, room, entry)
            if msg:
                logs.append(msg)
    return logs


@register_forced_trigger("hakurei_donation_barrier")
def _trigger_hakurei_donation(run, fm, room, entry: dict) -> str:
    cfg = FORCED_TRIGGER_CONFIGS["hakurei_donation_barrier"]
    p = run.player
    toll = int(cfg.get("toll_gold", 5))
    if p.gold >= toll:
        p.gold -= toll
        add_persistent_buff(p, "ancient_ward", 1)
        return get_locale_text("i18n_chaos_expansion.triggers.hakurei_donation_barrier", gold=toll)
    restore_sp(p, 1)
    return get_locale_text("i18n_chaos_expansion.triggers.hakurei_donation_broke")


@register_forced_trigger("scarlet_library_flying_tome")
def _trigger_scarlet_tome(run, fm, room, entry: dict) -> str:
    cfg = FORCED_TRIGGER_CONFIGS["scarlet_library_flying_tome"]
    p = run.player
    sp = restore_sp(p, int(cfg.get("sp_gain", 2)))
    add_persistent_buff(p, "arcane_clarity", 1)
    return get_locale_text("i18n_chaos_expansion.triggers.scarlet_library_flying_tome", sp=sp)


@register_forced_trigger("witch_sweet_labyrinth")
def _trigger_witch_sweet(run, fm, room, entry: dict) -> str:
    cfg = FORCED_TRIGGER_CONFIGS["witch_sweet_labyrinth"]
    p = run.player
    before = p.hp
    p.hp = min(p.max_hp, p.hp + int(cfg.get("heal", 4)))
    if int(getattr(p, "sp", 0)) > 0:
        consume_sp(p, int(cfg.get("sp_loss", 1)))
    return get_locale_text("i18n_chaos_expansion.triggers.witch_sweet_labyrinth", heal=max(0, p.hp - before))


@register_forced_trigger("mitakihara_soul_echo")
def _trigger_mitakihara_echo(run, fm, room, entry: dict) -> str:
    cfg = FORCED_TRIGGER_CONFIGS["mitakihara_soul_echo"]
    p = run.player
    sp = restore_sp(p, int(cfg.get("sp_gain", 2)))
    return get_locale_text("i18n_chaos_expansion.triggers.mitakihara_soul_echo", sp=sp)


@register_forced_trigger("tsab_dimensional_turbulence")
def _trigger_tsab_turbulence(run, fm, room, entry: dict) -> str:
    from .interact import _reveal_any_special

    cfg = FORCED_TRIGGER_CONFIGS["tsab_dimensional_turbulence"]
    p = run.player
    shield = int(cfg.get("shield", 6))
    p.shield = int(getattr(p, "shield", 0)) + shield
    revealed = _reveal_any_special(fm, 1) if fm is not None else []
    if revealed:
        return get_locale_text(
            "i18n_chaos_expansion.triggers.tsab_dimensional_turbulence",
            shield=shield,
            coord=revealed[0],
        )
    return get_locale_text("i18n_chaos_expansion.triggers.tsab_dimensional_turbulence_no_coord", shield=shield)


@register_forced_trigger("midchilda_mana_circle")
def _trigger_midchilda_circle(run, fm, room, entry: dict) -> str:
    cfg = FORCED_TRIGGER_CONFIGS["midchilda_mana_circle"]
    p = run.player
    sp = restore_sp(p, int(cfg.get("sp_gain", 2)))
    add_persistent_buff(p, "ancient_ward", 1)
    return get_locale_text("i18n_chaos_expansion.triggers.midchilda_mana_circle", sp=sp)


@register_forced_trigger("chaos_dimensional_sneak")
def _trigger_chaos_sneak(run, fm, room, entry: dict) -> str:
    cfg = FORCED_TRIGGER_CONFIGS["chaos_dimensional_sneak"]
    p = run.player
    gold = int(cfg.get("gold_gain", 8))
    dmg = int(cfg.get("dmg", 2))
    if random.random() < 0.55:
        p.gold += gold
        return get_locale_text("i18n_chaos_expansion.triggers.chaos_dimensional_sneak_loot", gold=gold)
    p.hp = max(1, p.hp - dmg)
    p.gold += gold
    return get_locale_text("i18n_chaos_expansion.triggers.chaos_dimensional_sneak_trip", dmg=dmg, gold=gold)


@register_forced_trigger("chaos_interact_whim")
def _trigger_interact_whim(run, fm, room, entry: dict) -> str:
    cfg = FORCED_TRIGGER_CONFIGS["chaos_interact_whim"]
    p = run.player
    sp = restore_sp(p, int(cfg.get("sp_gain", 1)))
    gold = int(cfg.get("gold_gain", 6))
    if random.random() < 0.5:
        p.gold += gold
        return get_locale_text("i18n_chaos_expansion.triggers.chaos_interact_whim_tip", gold=gold, sp=sp)
    return get_locale_text("i18n_chaos_expansion.triggers.chaos_interact_whim_joke", sp=sp)
