import random
from typing import Callable, Dict, List, Optional, Tuple
from ....data.content.chaos_expansion_data import CHAOS_NPCS
from ....data.content.chireiden_data import CHIREIDEN_RUMOR_GREETING_NPCS
from ....data.text.locale_data import get_locale_raw, get_locale_text
from ....data.world.room_interact_data import ROOM_NPCS
from ...inventory.bag_service import add_bag_item, get_item_display_name
from ...progress.achievement_service import record_run_achievement_stat
from ..persistent_buffs import add_persistent_buff
from ..sp_system import reduce_exhaustion, restore_sp
from .big_room import add_effective_item

CHAOS_NPC_CHOICE_HANDLERS: Dict[str, Callable] = {}

EXISTING_NPC_GREETING_KEYS = {
    "wandering_smith": "i18n_room_interact.dialog.smith_greetings",
    "smuggler_broker": "i18n_room_interact.dialog.broker_greetings",
    "lost_scholar": "i18n_room_interact.dialog.scholar_greetings",
    "wounded_scout": "i18n_room_interact.dialog.scout_greetings",
    "shrine_keeper": "i18n_room_interact.dialog.keeper_greetings",
}


def register_chaos_npc(*npc_ids: str):
    def decorator(fn: Callable):
        for nid in npc_ids:
            CHAOS_NPC_CHOICE_HANDLERS[nid] = fn
        return fn

    return decorator


def pick_greeting_for(run, locale_list_key: str, fallback_key: str) -> str:
    cached = run.node_data.get("cached_greeting")
    if isinstance(cached, str) and cached:
        return cached
    candidates = get_locale_raw(locale_list_key, [])
    if isinstance(candidates, list) and candidates:
        picked = str(random.choice(candidates))
    else:
        picked = get_locale_text(fallback_key)
    run.node_data["cached_greeting"] = picked
    return picked


def get_chaos_dialog_content(run, save_manager=None) -> Optional[Tuple[str, str, List[str]]]:
    nid = run.node_data.get("npc_id", "")
    if nid not in CHAOS_NPCS:
        return None
    cfg = ROOM_NPCS.get(nid, {})
    name = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else nid
    greetings_key = f"i18n_chaos_expansion.npcs.{nid}.greetings"
    greeting = pick_greeting_for(
        run,
        greetings_key,
        f"i18n_chaos_expansion.npcs.{nid}.desc",
    )
    rumor_idx = CHIREIDEN_RUMOR_GREETING_NPCS.get(nid)
    if rumor_idx is not None:
        candidates = get_locale_raw(greetings_key, [])
        if isinstance(candidates, list) and rumor_idx < len(candidates) and greeting == str(candidates[rumor_idx]):
            record_run_achievement_stat(save_manager, run, "chireiden_rumors_heard", 1)
    opts = [
        get_locale_text(f"i18n_chaos_expansion.npcs.{nid}.opt1"),
        get_locale_text(f"i18n_chaos_expansion.npcs.{nid}.opt2"),
        get_locale_text(f"i18n_chaos_expansion.npcs.{nid}.opt3"),
        get_locale_text(f"i18n_chaos_expansion.npcs.{nid}.opt4"),
    ]
    return name, greeting, opts


def _give_item_or_drop(run, fm, item_id: str) -> str:
    p = run.player
    ok, _ = add_bag_item(p, item_id)
    if not ok and fm is not None:
        coord = fm.player_coords.get(run.user_id, "")
        room = fm.rooms.get(coord)
        if room is not None:
            add_effective_item(fm, room, item_id)
    return get_item_display_name(item_id)


def _start_chaos_battle(map_engine, run, nid: str, battle_line_key: str, start_combat_fn) -> str:
    intro = get_locale_text(battle_line_key)
    battle_view = start_combat_fn(map_engine, run, nid, npc_source="grid")
    return f"{intro}\n\n{battle_view}"


def handle_chaos_dialog_choice(
    map_engine,
    run,
    idx: int,
    close_fn: Callable,
    start_combat_fn: Callable,
    reveal_fn: Callable,
) -> Optional[str]:
    nid = run.node_data.get("npc_id", "")
    handler = CHAOS_NPC_CHOICE_HANDLERS.get(nid)
    if handler is None:
        return None
    return handler(map_engine, run, idx, close_fn, start_combat_fn, reveal_fn)


def _append_chireiden_rumor(text: str, rumor_key: str, map_engine=None, run=None) -> str:
    if random.random() < 0.55:
        if map_engine is not None and run is not None:
            record_run_achievement_stat(map_engine.save_manager, run, "chireiden_rumors_heard", 1)
        return f"{text}\n{get_locale_text(rumor_key)}"
    return text


@register_chaos_npc("hakurei_reimu")
def _handle_reimu(map_engine, run, idx: int, close_fn, start_combat_fn, reveal_fn) -> str:
    p = run.player
    fm = getattr(run, "floor_map", None)
    if idx == 1:
        cost = 10
        if p.gold < cost:
            return get_locale_text("i18n_room_interact.dialog.err_gold", cost=cost)
        p.gold -= cost
        if random.random() < 0.45:
            iname = _give_item_or_drop(run, fm, "yin_yang_orb")
            close_fn(map_engine.save_manager, run)
            return _append_chireiden_rumor(
                get_locale_text("i18n_chaos_expansion.npcs.hakurei_reimu.res_donate_gift", item=iname),
                "i18n_chireiden.rumors.reimu_hint",
                map_engine,
                run,
            )
        add_persistent_buff(p, "ancient_ward", 1)
        sp = restore_sp(p, 2)
        close_fn(map_engine.save_manager, run)
        return _append_chireiden_rumor(
            get_locale_text("i18n_chaos_expansion.npcs.hakurei_reimu.res_donate", cost=cost, sp=sp),
            "i18n_chireiden.rumors.reimu_hint",
            map_engine,
            run,
        )
    if idx == 2:
        if random.random() < 0.6:
            iname = _give_item_or_drop(run, fm, random.choice(["yin_yang_orb", "sugar_cube_pack"]))
            close_fn(map_engine.save_manager, run)
            return _append_chireiden_rumor(
                get_locale_text("i18n_chaos_expansion.npcs.hakurei_reimu.res_beg", item=iname),
                "i18n_chireiden.rumors.reimu_hint",
                map_engine,
                run,
            )
        dmg = min(2, max(0, p.hp - 1))
        p.hp = max(1, p.hp - dmg)
        sp = restore_sp(p, 2)
        close_fn(map_engine.save_manager, run)
        return _append_chireiden_rumor(
            get_locale_text("i18n_chaos_expansion.npcs.hakurei_reimu.res_beg_kick", dmg=dmg, sp=sp),
            "i18n_chireiden.rumors.reimu_hint",
            map_engine,
            run,
        )
    if idx == 3:
        return _start_chaos_battle(
            map_engine,
            run,
            "hakurei_reimu",
            "i18n_chaos_expansion.npcs.hakurei_reimu.res_provoke",
            start_combat_fn,
        )
    return close_fn(map_engine.save_manager, run)


@register_chaos_npc("kirisame_marisa")
def _handle_marisa(map_engine, run, idx: int, close_fn, start_combat_fn, reveal_fn) -> str:
    p = run.player
    fm = getattr(run, "floor_map", None)
    if idx == 1:
        cost = 20
        if p.gold < cost:
            return get_locale_text("i18n_room_interact.dialog.err_gold", cost=cost)
        p.gold -= cost
        iname = _give_item_or_drop(run, fm, random.choice(["mini_hakkero", "magic_mushroom", "skeleton_key"]))
        close_fn(map_engine.save_manager, run)
        return _append_chireiden_rumor(
            get_locale_text("i18n_chaos_expansion.npcs.kirisame_marisa.res_trade", item=iname),
            "i18n_chireiden.rumors.marisa_hint",
            map_engine,
            run,
        )
    if idx == 2:
        if random.random() < 0.5:
            iname = _give_item_or_drop(run, fm, "magic_mushroom")
            close_fn(map_engine.save_manager, run)
            return _append_chireiden_rumor(
                get_locale_text("i18n_chaos_expansion.npcs.kirisame_marisa.res_mushroom_win", item=iname),
                "i18n_chireiden.rumors.marisa_hint",
                map_engine,
                run,
            )
        dmg = min(2, max(0, p.hp - 1))
        p.hp = max(1, p.hp - dmg)
        p.shield = int(getattr(p, "shield", 0)) + 8
        sp = restore_sp(p, 2)
        close_fn(map_engine.save_manager, run)
        return _append_chireiden_rumor(
            get_locale_text(
                "i18n_chaos_expansion.npcs.kirisame_marisa.res_mushroom_chaos",
                dmg=dmg,
                shield=8,
                sp=sp,
            ),
            "i18n_chireiden.rumors.marisa_hint",
            map_engine,
            run,
        )
    if idx == 3:
        return _start_chaos_battle(
            map_engine,
            run,
            "kirisame_marisa",
            "i18n_chaos_expansion.npcs.kirisame_marisa.res_spark_angry",
            start_combat_fn,
        )
    return close_fn(map_engine.save_manager, run)


@register_chaos_npc("patchouli_knowledge")
def _handle_patchouli(map_engine, run, idx: int, close_fn, start_combat_fn, reveal_fn) -> str:
    from ....entities import ALL_CARDS
    from ...inventory.card_distribution import CardDistributor
    from ...inventory.deck_service import DeckService

    p = run.player
    if idx == 1:
        add_persistent_buff(p, "arcane_clarity", 1)
        cid = CardDistributor.roll_one("npc_scholar", run, p, None, fallback="fireball") or "fireball"
        DeckService.add_card_to_deck(p, cid)
        close_fn(map_engine.save_manager, run)
        return _append_chireiden_rumor(
            get_locale_text("i18n_chaos_expansion.npcs.patchouli_knowledge.res_study", card=ALL_CARDS[cid].name),
            "i18n_chireiden.rumors.patchouli_hint",
            map_engine,
            run,
        )
    if idx == 2:
        p.gold += 24
        sp = restore_sp(p, 2)
        close_fn(map_engine.save_manager, run)
        return _append_chireiden_rumor(
            get_locale_text("i18n_chaos_expansion.npcs.patchouli_knowledge.res_tidy", gold=24, sp=sp),
            "i18n_chireiden.rumors.patchouli_hint",
            map_engine,
            run,
        )
    if idx == 3:
        return _start_chaos_battle(
            map_engine,
            run,
            "patchouli_knowledge",
            "i18n_chaos_expansion.npcs.patchouli_knowledge.res_provoke",
            start_combat_fn,
        )
    return close_fn(map_engine.save_manager, run)


@register_chaos_npc("kyubey")
def _handle_kyubey(map_engine, run, idx: int, close_fn, start_combat_fn, reveal_fn) -> str:
    p = run.player
    fm = getattr(run, "floor_map", None)
    if idx == 1:
        hp_drop = 3 if p.max_hp > 12 else 0
        p.max_hp = max(1, p.max_hp - hp_drop)
        p.hp = min(p.hp, p.max_hp)
        p.gold += 50
        iname = _give_item_or_drop(run, fm, "kyubey_contract")
        close_fn(map_engine.save_manager, run)
        return get_locale_text(
            "i18n_chaos_expansion.npcs.kyubey.res_sign",
            max_hp=hp_drop,
            gold=50,
            item=iname,
        )
    if idx == 2:
        reduce_exhaustion(p, 1)
        iname = _give_item_or_drop(run, fm, "grief_seed")
        close_fn(map_engine.save_manager, run)
        return get_locale_text("i18n_chaos_expansion.npcs.kyubey.res_grief", item=iname)
    if idx == 3:
        return _start_chaos_battle(
            map_engine,
            run,
            "kyubey",
            "i18n_chaos_expansion.npcs.kyubey.res_atk",
            start_combat_fn,
        )
    return close_fn(map_engine.save_manager, run)


@register_chaos_npc("tomoe_mami")
def _handle_mami(map_engine, run, idx: int, close_fn, start_combat_fn, reveal_fn) -> str:
    p = run.player
    fm = getattr(run, "floor_map", None)
    if idx == 1:
        before = p.hp
        p.hp = min(p.max_hp, p.hp + 12)
        sp = restore_sp(p, 4)
        old_ex = getattr(p, "exhaustion", 0)
        new_ex = reduce_exhaustion(p, 1)
        close_fn(map_engine.save_manager, run)
        return get_locale_text(
            "i18n_chaos_expansion.npcs.tomoe_mami.res_tea",
            heal=p.hp - before,
            sp=sp,
            cured=max(0, old_ex - new_ex),
        )
    if idx == 2:
        add_persistent_buff(p, "ancient_ward", 1)
        iname = _give_item_or_drop(run, fm, "sugar_cube_pack")
        close_fn(map_engine.save_manager, run)
        return get_locale_text("i18n_chaos_expansion.npcs.tomoe_mami.res_tutor", item=iname)
    if idx == 3:
        return _start_chaos_battle(
            map_engine,
            run,
            "tomoe_mami",
            "i18n_chaos_expansion.npcs.tomoe_mami.res_spar",
            start_combat_fn,
        )
    return close_fn(map_engine.save_manager, run)


@register_chaos_npc("takamachi_nanoha")
def _handle_nanoha(map_engine, run, idx: int, close_fn, start_combat_fn, reveal_fn) -> str:
    p = run.player
    fm = getattr(run, "floor_map", None)
    if idx == 1:
        p.gold += 20
        iname = _give_item_or_drop(run, fm, "mana_cartridge")
        close_fn(map_engine.save_manager, run)
        return get_locale_text("i18n_chaos_expansion.npcs.takamachi_nanoha.res_gift", item=iname, gold=20)
    if idx == 2:
        add_persistent_buff(p, "ancient_ward", 1)
        sp = restore_sp(p, 3)
        close_fn(map_engine.save_manager, run)
        return get_locale_text("i18n_chaos_expansion.npcs.takamachi_nanoha.res_charge", sp=sp)
    if idx == 3:
        return _start_chaos_battle(
            map_engine,
            run,
            "takamachi_nanoha",
            "i18n_chaos_expansion.npcs.takamachi_nanoha.res_canon",
            start_combat_fn,
        )
    return close_fn(map_engine.save_manager, run)


@register_chaos_npc("fate_testarossa")
def _handle_fate(map_engine, run, idx: int, close_fn, start_combat_fn, reveal_fn) -> str:
    p = run.player
    fm = getattr(run, "floor_map", None)
    if idx == 1:
        revealed = reveal_fn(fm, 2) if fm is not None else []
        p.gold += 18
        close_fn(map_engine.save_manager, run)
        return get_locale_text(
            "i18n_chaos_expansion.npcs.fate_testarossa.res_intel",
            count=len(revealed),
            gold=18,
        )
    if idx == 2:
        sp = restore_sp(p, 3)
        iname = _give_item_or_drop(run, fm, "mana_cartridge")
        close_fn(map_engine.save_manager, run)
        return get_locale_text("i18n_chaos_expansion.npcs.fate_testarossa.res_sonic", sp=sp, item=iname)
    if idx == 3:
        return _start_chaos_battle(
            map_engine,
            run,
            "fate_testarossa",
            "i18n_chaos_expansion.npcs.fate_testarossa.res_duel",
            start_combat_fn,
        )
    return close_fn(map_engine.save_manager, run)
