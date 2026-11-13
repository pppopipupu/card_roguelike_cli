import random
from typing import Optional

from ...data.locale_data import get_locale_raw, get_locale_text
from ...data.mercenary_data import (
    HARRY_MAX_VOICES_PER_TURN,
    HARRY_SKILL_IDS,
    HARRY_VOICE_CHANCE,
    MERCENARY_CONFIG,
    MERCENARY_TIMING_AFTER,
    MERCENARY_TIMING_BEFORE,
)
from ...entities import ALL_CARDS
from ...models.events import BattleStartEvent, BattleWinEvent, CardPlayEvent, DamageCalculateEvent, TurnStartEvent
from ...models.state import CardState, GameRun, PlayerState, ensure_card_state
from ..inventory.deck_service import DeckService
from .coordinator import restore_player, swap_player


def is_mercenary(player: Optional[PlayerState]) -> bool:
    return bool(player is not None and getattr(player, "is_mercenary", False))


def get_mercenary_config(merc_id: str) -> dict:
    return MERCENARY_CONFIG.get(merc_id, MERCENARY_CONFIG["harry_du_bois"])


def resolve_mercenary_id(query: str) -> Optional[str]:
    q = str(query or "").strip().lower()
    if not q:
        return None
    for mid, cfg in MERCENARY_CONFIG.items():
        if q == mid.lower() or q == cfg["name"].lower():
            return mid
        if any(q == alias.lower() for alias in cfg.get("aliases", [])):
            return mid
    return None


def build_mercenary_player(merc_id: str, owner_uid: str) -> PlayerState:
    cfg = get_mercenary_config(merc_id)
    deck = [CardState(id=cid) for cid in cfg.get("starting_deck", [])]
    random.shuffle(deck)
    hp = int(cfg.get("hp", 72))
    return PlayerState(
        hp=hp,
        max_hp=hp,
        shield=0,
        gold=0,
        stage=0,
        name=cfg["name"],
        deck=deck,
        draw_pile=[],
        discard_pile=[],
        hand=[],
        actions=1,
        bonus_actions=1,
        minions={},
        amulets={},
        abilities=[],
        subclass="",
        selected_class=cfg.get("class_name", "RCM 警探"),
        is_mercenary=True,
        mercenary_id=cfg["id"],
        mercenary_owner=owner_uid,
        mercenary_timing=cfg.get("default_timing", MERCENARY_TIMING_AFTER),
    )


def list_owned_mercenaries(run: Optional[GameRun], owner_uid: str = "") -> list[tuple[str, PlayerState]]:
    if run is None:
        return []
    result = []
    for uid in run.party_order:
        p = run.players.get(uid)
        if not is_mercenary(p):
            continue
        if owner_uid and getattr(p, "mercenary_owner", "") != owner_uid:
            continue
        result.append((uid, p))
    return result


def find_mercenary_uid(run: Optional[GameRun], query: str = "", owner_uid: str = "") -> tuple[Optional[str], Optional[str]]:
    owned = list_owned_mercenaries(run, owner_uid)
    if not owned:
        return None, get_locale_text("i18n_mercenary.err_no_mercenary")
    q = str(query or "").strip().lower()
    if not q:
        return owned[0][0], None
    for uid, p in owned:
        mid = getattr(p, "mercenary_id", "")
        cfg = get_mercenary_config(mid)
        if q == mid.lower() or q == p.name.lower() or any(q == a.lower() for a in cfg.get("aliases", [])):
            return uid, None
    for uid, p in owned:
        mid = getattr(p, "mercenary_id", "")
        cfg = get_mercenary_config(mid)
        if q in mid.lower() or q in p.name.lower() or any(q in a.lower() for a in cfg.get("aliases", [])):
            return uid, None
    return None, get_locale_text("i18n_mercenary.err_not_found", target=query)


def _pick_card_target(run: GameRun, merc_uid: str, card_obj) -> Optional[str]:
    from ..battle.coop_targeting import COOP_ALLY_CARDS
    from ..battle.party_battle import party_slots, party_target_ref

    base_id = getattr(card_obj, "id", "")
    target_type = getattr(card_obj, "target_type", "enemy")
    if base_id == "discover" or base_id.startswith("neutral_emperor_eye"):
        return None
    if base_id in COOP_ALLY_CARDS:
        allow_self = bool(getattr(card_obj, "upgraded", False)) and base_id in (
            "coop_resonance_hymn",
            "coop_phalanx_bulwark",
        )
        slots = party_slots(run, alive_only=True)
        if not allow_self:
            slots = [(s, u, p) for s, u, p in slots if u != merc_uid]
        if not slots:
            return None
        slots.sort(key=lambda item: (item[1] == merc_uid, item[1] != getattr(run.players.get(merc_uid), "mercenary_owner", ""), item[2].hp / max(1, item[2].max_hp)))
        _, chosen_uid, _ = slots[0]
        return party_target_ref(run, chosen_uid)
    if target_type in ("none", "self", "all_enemies", "random_enemy"):
        return None
    if target_type in ("ally", "ally_or_self", "any_other"):
        slots = party_slots(run, alive_only=True)
        if target_type == "any_other":
            slots = [(s, u, p) for s, u, p in slots if u != merc_uid]
        if not slots:
            return None
        slots.sort(key=lambda item: (item[1] != getattr(run.players.get(merc_uid), "mercenary_owner", ""), item[2].hp / max(1, item[2].max_hp)))
        _, chosen_uid, _ = slots[0]
        return party_target_ref(run, chosen_uid)
    alive_enemies = [(idx + 1, e) for idx, e in enumerate(run.enemies) if e.hp > 0]
    if not alive_enemies:
        return None
    alive_enemies.sort(key=lambda item: item[1].hp + item[1].shield)
    return f"e{alive_enemies[0][0]}"


def _score_card_obj(merc: PlayerState, card_obj) -> int:
    if card_obj is None:
        return -1000
    if getattr(card_obj, "type", "") == "curse" or getattr(card_obj, "unplayable", False):
        return -500
    score = 10
    if getattr(card_obj, "action_gain", 0) > 0 or getattr(card_obj, "bonus_action_gain", 0) > 0:
        score += 30
    if getattr(card_obj, "draw_count", 0) > 0:
        score += 18
    if getattr(card_obj, "heal_amount", 0) > 0 and merc.hp * 100 < merc.max_hp * 75:
        score += 25
    if getattr(card_obj, "shield_amount", 0) > 0 and merc.shield < 12:
        score += 16
    if getattr(card_obj, "base_dmg", 0) > 0:
        score += 20 + int(getattr(card_obj, "base_dmg", 0))
    if getattr(card_obj, "buff_stacks", 0) > 0:
        score += 8
    if getattr(card_obj, "type", "") in ("minion", "amulet"):
        score += 14
    return score


def _pick_discard_index(merc: PlayerState) -> int:
    best_idx = 0
    best_priority = (999, 999)
    for idx, raw_c in enumerate(merc.hand):
        state = ensure_card_state(raw_c)
        card_obj = ALL_CARDS.get(state)
        if card_obj and getattr(card_obj, "agile", False):
            prio = (0, -_score_card_obj(merc, card_obj))
        elif card_obj is None or getattr(card_obj, "type", "") == "curse" or getattr(card_obj, "unplayable", False):
            prio = (1, 0)
        else:
            prio = (2, _score_card_obj(merc, card_obj))
        if prio < best_priority:
            best_priority = prio
            best_idx = idx
    return best_idx


def _pick_playable_card(
    battle_engine,
    run: GameRun,
    merc_uid: str,
    merc: PlayerState,
    skip_obj_ids: Optional[set[int]] = None,
) -> Optional[tuple[int, Optional[str]]]:
    from ..battle.coop_targeting import COOP_ALLY_CARDS

    best_idx = None
    best_target = None
    best_score = -999
    for idx, c_state in enumerate(merc.hand, 1):
        if skip_obj_ids and id(c_state) in skip_obj_ids:
            continue
        state = ensure_card_state(c_state)
        card_obj = ALL_CARDS.get(state)
        if card_obj is None or getattr(card_obj, "unplayable", False):
            continue
        if getattr(card_obj, "type", "") == "curse":
            continue
        cost_a = getattr(card_obj, "cost_a", 0)
        cost_ba = getattr(card_obj, "cost_ba", 0)
        req_a = merc.actions if cost_a == -1 else cost_a
        req_ba = merc.bonus_actions if cost_ba == -1 else cost_ba
        if merc.actions < req_a or merc.bonus_actions < req_ba:
            continue
        if cost_a == -1 and cost_ba == -1 and req_a <= 0 and req_ba <= 0:
            continue
        if cost_a == -1 and cost_ba == 0 and req_a <= 0:
            continue
        if cost_ba == -1 and cost_a == 0 and req_ba <= 0:
            continue
        if getattr(card_obj, "self_hp_cost", 0) >= merc.hp:
            continue
        if getattr(card_obj, "type", "") in ("minion", "amulet") and battle_engine._get_free_grid(merc) is None:
            continue
        target = _pick_card_target(run, merc_uid, card_obj)
        if (getattr(card_obj, "target_type", "enemy") in ("ally", "ally_or_self", "any_other") or card_obj.id in COOP_ALLY_CARDS) and target is None:
            continue
        if card_obj.can_play_error(run, target, battle_engine):
            continue
        score = _score_card_obj(merc, card_obj)
        if score > best_score:
            best_score = score
            best_idx = idx
            best_target = target
    if best_idx is None:
        return None
    return best_idx, best_target


def _resolve_merc_interactions(battle_engine, run: GameRun, merc_uid: str, merc: PlayerState, initial_stack_len: int) -> list[str]:
    extra_notes = []
    for _ in range(16):
        did_work = False
        if run.node_data.pop("pending_discard", None):
            run.node_data.pop("pending_discard_source", None)
            if merc.hand:
                d_idx = _pick_discard_index(merc)
                cid = merc.hand.pop(d_idx)
                d_obj = ALL_CARDS.get(ensure_card_state(cid))
                d_res = battle_engine._discard_card(run, cid)
                extra_notes.append(get_locale_text("i18n_cli_core.discard_result", card_name=d_obj.name if d_obj else ensure_card_state(cid).id))
                if d_res:
                    extra_notes.append(d_res)
                did_work = True
        state_stack = run.node_data.get("state_stack", [])
        if len(state_stack) <= initial_stack_len:
            if not did_work:
                break
            continue
        top = state_stack.pop()
        stype = top.get("type")
        if stype == "force_discard":
            req_count = int(top.get("required_count", 1) or 1)
            already_cnt = len(top.get("discarded", []))
            need = max(0, req_count - already_cnt)
            for _ in range(need):
                if not merc.hand:
                    break
                d_idx = _pick_discard_index(merc)
                cid = merc.hand.pop(d_idx)
                d_obj = ALL_CARDS.get(ensure_card_state(cid))
                d_res = battle_engine._discard_card(run, cid)
                extra_notes.append(get_locale_text("i18n_cli_core.discard_result", card_name=d_obj.name if d_obj else ensure_card_state(cid).id))
                if d_res:
                    extra_notes.append(d_res)
            battle_engine.resolve_suspended_card(run)
        elif stype == "discover_selection":
            req_count = int(top.get("count", 1) or 1)
            already = list(top.get("selected", []))
            need = max(0, req_count - len(already))
            picked_names = []
            for _ in range(need):
                valid_exhaust = [c for c in merc.exhaust_pile if ensure_card_state(c).id != "discover"]
                if not valid_exhaust:
                    break
                best_c = max(valid_exhaust, key=lambda c: _score_card_obj(merc, ALL_CARDS.get(ensure_card_state(c))))
                merc.exhaust_pile.remove(best_c)
                DeckService.add_card_to_hand(merc, best_c)
                b_obj = ALL_CARDS.get(ensure_card_state(best_c))
                picked_names.append(b_obj.name if b_obj else ensure_card_state(best_c).id)
            battle_engine.resolve_suspended_card(run)
            if picked_names:
                sep = get_locale_text("i18n_cli_core.list_separator")
                extra_notes.append(get_locale_text("i18n_cli_core.discover_complete", selected_cards_str=sep.join(picked_names)))
        elif stype == "overload_star_select":
            upgraded = bool(top.get("upgraded", False))
            if merc.hand:
                keep_idx = max(range(len(merc.hand)), key=lambda i: _score_card_obj(merc, ALL_CARDS.get(ensure_card_state(merc.hand[i]))))
            else:
                keep_idx = -1
            emp_res = battle_engine.execute_emperor_eye_resolve(run, keep_idx, upgraded)
            if emp_res:
                extra_notes.append(emp_res)
        elif stype == "cthulhu_puzzle_choice":
            stage = int(top.get("stage", run.node_data.get("cthulhu_seal_stage", 1)) or 1)
            option = 2 if stage == 2 else 1
            from ...entities.enemies.boss.cthulhu_boss import resolve_cthulhu_puzzle
            puz_res = resolve_cthulhu_puzzle(run, battle_engine, option, merc)
            battle_engine.resolve_suspended_card(run)
            if puz_res:
                extra_notes.append(puz_res)
        elif stype == "awaiting_target":
            action_info = top.get("action")
            if action_info == "play_card":
                h_idx = top.get("hand_idx")
                if isinstance(h_idx, int) and 1 <= h_idx <= len(merc.hand):
                    c_obj = ALL_CARDS.get(ensure_card_state(merc.hand[h_idx - 1]))
                    t = _pick_card_target(run, merc_uid, c_obj) if c_obj else None
                    if t:
                        t_res = battle_engine.card_player.play_card(run, h_idx, t)
                        if t_res and not t_res.startswith("[FAIL]") and not t_res.startswith("❌"):
                            extra_notes.append(t_res)
                            continue
            battle_engine.rollback_suspended_card(run)
        else:
            battle_engine.rollback_suspended_card(run)
    return [n for n in extra_notes if n]


def end_mercenary_phase(battle_engine, run: GameRun, merc_uid: str) -> str:
    merc = run.players.get(merc_uid)
    if not is_mercenary(merc) or merc.hp <= 0 or merc.downed:
        return ""
    turn_count = int(run.node_data.get("turn_count", 1) or 1)
    ended = run.node_data.setdefault("merc_ended_round", {})
    round_key = f"{turn_count}:{merc_uid}"
    if ended.get(round_key):
        return ""
    ended[round_key] = True
    previous, previous_user = swap_player(run, merc)
    try:
        return battle_engine.card_player._end_player_phase(run, merc)
    finally:
        restore_player(run, previous, previous_user)


def end_unended_mercenary_phases(battle_engine, run: GameRun) -> list[str]:
    outputs = []
    for uid in list(run.party_order):
        player = run.players.get(uid)
        if not is_mercenary(player) or player.hp <= 0 or player.downed:
            continue
        out = end_mercenary_phase(battle_engine, run, uid)
        if out:
            outputs.append(out)
    return outputs


def run_mercenary_turn(battle_engine, run: GameRun, merc_uid: str) -> str:
    merc = run.players.get(merc_uid)
    if not is_mercenary(merc) or merc.hp <= 0 or merc.downed:
        return ""
    if battle_engine.is_battle_won(run):
        return ""
    turn_count = int(run.node_data.get("turn_count", 1) or 1)
    acted = run.node_data.setdefault("merc_acted_round", {})
    round_key = f"{turn_count}:{merc_uid}"
    if acted.get(round_key):
        return ""
    acted[round_key] = True

    slot = run.party_order.index(merc_uid) + 1 if merc_uid in run.party_order else 2
    previous, previous_user = swap_player(run, merc)
    logs = [get_locale_text("i18n_mercenary.ai_turn_banner", name=merc.name, slot=slot)]
    acted_any = False
    skip_obj_ids: set[int] = set()
    try:
        for _ in range(24):
            if merc.hp <= 0 or merc.downed or battle_engine.is_battle_won(run):
                break
            choice = _pick_playable_card(battle_engine, run, merc_uid, merc, skip_obj_ids)
            if choice is None:
                break
            card_idx, target = choice
            raw_entry = merc.hand[card_idx - 1]
            c_state = ensure_card_state(raw_entry)
            card_obj = ALL_CARDS.get(c_state)
            card_name = card_obj.name if card_obj else c_state.id
            initial_stack_len = len(run.node_data.get("state_stack", []))
            res = battle_engine.card_player.play_card(run, card_idx, target)
            if not res or res.startswith("[FAIL]") or res.startswith("❌"):
                skip_obj_ids.add(id(merc.hand[card_idx - 1]) if card_idx - 1 < len(merc.hand) else id(raw_entry))
                continue
            acted_any = True
            extra_notes = _resolve_merc_interactions(battle_engine, run, merc_uid, merc, initial_stack_len)
            combined_res = "\n".join([res, *extra_notes]).strip() if extra_notes else res
            logs.append(get_locale_text("i18n_mercenary.ai_play_card", card=card_name, result=combined_res))
        for grid, minion in list(merc.minions.items()):
            if battle_engine.is_battle_won(run):
                break
            if minion.hp > 0 and minion.attack_actions > 0 and any(e.hp > 0 for e in run.enemies):
                target = f"e{next((i + 1 for i, e in enumerate(run.enemies) if e.hp > 0), 1)}"
                m_res = battle_engine.minion_attack(run, grid, target)
                if m_res:
                    acted_any = True
                    logs.append(get_locale_text("i18n_mercenary.ai_minion_attack", minion=minion.name, result=m_res))
    finally:
        restore_player(run, previous, previous_user)
    if not battle_engine.is_battle_won(run) and merc.hp > 0 and not merc.downed:
        end_mercenary_phase(battle_engine, run, merc_uid)
    if not acted_any:
        logs.append(get_locale_text("i18n_mercenary.ai_no_action"))
    return "\n".join(logs)


def run_mercenaries_for_timing(battle_engine, run: GameRun, timing: str) -> str:
    outputs = []
    for uid in list(run.party_order):
        player = run.players.get(uid)
        if not is_mercenary(player) or player.hp <= 0 or player.downed:
            continue
        if getattr(player, "mercenary_timing", MERCENARY_TIMING_AFTER) != timing:
            continue
        out = run_mercenary_turn(battle_engine, run, uid)
        if out:
            outputs.append(out)
    return "\n".join(outputs)
def _group_deck_cards(deck: list) -> list[tuple[CardState, int]]:
    counts = {}
    for c in deck:
        state = ensure_card_state(c)
        counts[state] = counts.get(state, 0) + 1
    return sorted(counts.items(), key=lambda item: (item[0].id, 1 if item[0].upgraded else 0, tuple(item[0].gems or [])))


def _card_cost_text(card) -> str:
    from ...renderer.menu import get_card_cost_str
    return get_card_cost_str(card)


def _replace_active_card(player: PlayerState, old_state: CardState, new_state: CardState):
    for pile in (player.hand, player.draw_pile, player.discard_pile):
        for idx, item in enumerate(pile):
            if ensure_card_state(item) == old_state:
                pile[idx] = DeckService.clone_state(new_state)
                return


def _dialog_bucket(run: GameRun, uid: str) -> Optional[dict]:
    dialogs = run.node_data.get("merc_dialogs")
    if isinstance(dialogs, dict):
        return dialogs.get(uid)
    return None


def is_in_merc_dialog(run: Optional[GameRun], uid: str) -> bool:
    if run is None or not uid:
        return False
    return isinstance(_dialog_bucket(run, uid), dict)


def open_merc_dialog(run: GameRun, owner_uid: str, merc_uid: str) -> str:
    dialogs = run.node_data.setdefault("merc_dialogs", {})
    dialogs[owner_uid] = {
        "merc_uid": merc_uid,
        "state": "main",
        "player_card": None,
        "last_msg": "",
    }
    return render_merc_dialog(run, owner_uid)


def close_merc_dialog(run: GameRun, owner_uid: str) -> str:
    dialogs = run.node_data.get("merc_dialogs")
    merc_name = MERCENARY_CONFIG["harry_du_bois"]["name"]
    if isinstance(dialogs, dict):
        entry = dialogs.pop(owner_uid, None)
        if isinstance(entry, dict):
            merc = run.players.get(entry.get("merc_uid", ""))
            if merc is not None:
                merc_name = merc.name
        if not dialogs:
            run.node_data.pop("merc_dialogs", None)
    return get_locale_text("i18n_mercenary.dialog_exit", name=merc_name)


def render_merc_dialog(run: GameRun, owner_uid: str) -> str:
    entry = _dialog_bucket(run, owner_uid)
    if not isinstance(entry, dict):
        return ""
    merc_uid = entry.get("merc_uid", "")
    merc = run.players.get(merc_uid)
    player = run.players.get(owner_uid) or run.player
    if merc is None or player is None:
        close_merc_dialog(run, owner_uid)
        return get_locale_text("i18n_mercenary.err_no_mercenary")
    state = entry.get("state", "main")
    lines = []
    if entry.get("last_msg"):
        lines.append(entry["last_msg"])
        lines.append("")
    timing = getattr(merc, "mercenary_timing", MERCENARY_TIMING_AFTER)
    timing_label = get_locale_text("i18n_mercenary.timing_before" if timing == MERCENARY_TIMING_BEFORE else "i18n_mercenary.timing_after")
    slot = run.party_order.index(merc_uid) + 1 if merc_uid in run.party_order else 2
    preview_names = []
    for c_state, _ in _group_deck_cards(merc.deck)[:5]:
        card_obj = ALL_CARDS.get(c_state)
        preview_names.append(card_obj.name if card_obj else c_state.id)
    deck_preview = "、".join(preview_names)
    if len(_group_deck_cards(merc.deck)) > 5:
        deck_preview += "…"
    lines.append(get_locale_text(
        "i18n_mercenary.dialog_header",
        name=merc.name,
        slot=slot,
        hp=merc.hp,
        max_hp=merc.max_hp,
        timing=timing_label,
        deck_count=len(merc.deck),
        deck_preview=deck_preview,
    ))
    if state == "main":
        lines.append(get_locale_text("i18n_mercenary.dialog_options", timing=timing_label))
        lines.append(get_locale_text("i18n_mercenary.dialog_prompt"))
    elif state == "pick_player_card":
        lines.append(get_locale_text("i18n_mercenary.swap_pick_self_header", count=len(player.deck)))
        for idx, (c_state, count) in enumerate(_group_deck_cards(player.deck), 1):
            card_obj = ALL_CARDS.get(c_state)
            cname = f"{card_obj.name} x{count}" if (card_obj and count > 1) else (card_obj.name if card_obj else c_state.id)
            cost_str = _card_cost_text(card_obj) if card_obj else ""
            desc = card_obj.desc if card_obj else ""
            lines.append(get_locale_text("i18n_mercenary.swap_card_line", idx=idx, name=cname, cost=cost_str, desc=desc))
        lines.append(get_locale_text("i18n_mercenary.swap_cancel_line"))
    elif state == "pick_merc_card":
        p_info = entry.get("player_card") or {}
        p_state = CardState(id=p_info.get("id", ""), upgraded=bool(p_info.get("upgraded", False)), gems=list(p_info.get("gems", [])))
        p_obj = ALL_CARDS.get(p_state)
        p_name = p_obj.name if p_obj else p_state.id
        lines.append(get_locale_text("i18n_mercenary.swap_pick_merc_header", card_name=p_name, merc_name=merc.name))
        for idx, (c_state, count) in enumerate(_group_deck_cards(merc.deck), 1):
            card_obj = ALL_CARDS.get(c_state)
            cname = f"{card_obj.name} x{count}" if (card_obj and count > 1) else (card_obj.name if card_obj else c_state.id)
            cost_str = _card_cost_text(card_obj) if card_obj else ""
            desc = card_obj.desc if card_obj else ""
            lines.append(get_locale_text("i18n_mercenary.swap_card_line", idx=idx, name=cname, cost=cost_str, desc=desc))
        lines.append(get_locale_text("i18n_mercenary.swap_cancel_line"))
    return "\n".join(lines)


def handle_merc_dialog_input(run: GameRun, owner_uid: str, raw_text: str) -> str:
    entry = _dialog_bucket(run, owner_uid)
    if not isinstance(entry, dict):
        return get_locale_text("i18n_mercenary.err_no_mercenary")
    text = str(raw_text or "").strip().lower()
    if text in ("离开", "leave", "exit", "quit", "取消", "cancel"):
        return close_merc_dialog(run, owner_uid)
    merc_uid = entry.get("merc_uid", "")
    merc = run.players.get(merc_uid)
    player = run.players.get(owner_uid) or run.player
    if merc is None or player is None:
        return close_merc_dialog(run, owner_uid)
    try:
        idx = int(text)
    except ValueError:
        return get_locale_text("i18n_mercenary.err_invalid_choice")
    state = entry.get("state", "main")
    entry["last_msg"] = ""
    if state == "main":
        if idx == 1:
            chats = get_locale_raw("i18n_mercenary.harry_chats", [])
            if isinstance(chats, list) and chats:
                entry["last_msg"] = random.choice(chats)
            else:
                entry["last_msg"] = get_locale_text("i18n_mercenary.harry_chats")
            return render_merc_dialog(run, owner_uid)
        if idx == 2:
            if not player.deck or not merc.deck:
                entry["last_msg"] = get_locale_text("i18n_mercenary.swap_empty_deck")
                return render_merc_dialog(run, owner_uid)
            entry["state"] = "pick_player_card"
            return render_merc_dialog(run, owner_uid)
        if idx == 3:
            curr = getattr(merc, "mercenary_timing", MERCENARY_TIMING_AFTER)
            merc.mercenary_timing = MERCENARY_TIMING_BEFORE if curr == MERCENARY_TIMING_AFTER else MERCENARY_TIMING_AFTER
            label = get_locale_text("i18n_mercenary.timing_before" if merc.mercenary_timing == MERCENARY_TIMING_BEFORE else "i18n_mercenary.timing_after")
            entry["last_msg"] = get_locale_text("i18n_mercenary.timing_switched", name=merc.name, timing=label)
            return render_merc_dialog(run, owner_uid)
        if idx == 4:
            return close_merc_dialog(run, owner_uid)
        return get_locale_text("i18n_mercenary.err_invalid_choice")
    if state == "pick_player_card":
        if idx == 0:
            entry["state"] = "main"
            return render_merc_dialog(run, owner_uid)
        grouped = _group_deck_cards(player.deck)
        if idx < 1 or idx > len(grouped):
            return get_locale_text("i18n_mercenary.err_invalid_card_index", count=len(grouped))
        chosen_p, _ = grouped[idx - 1]
        entry["player_card"] = {
            "id": chosen_p.id,
            "upgraded": chosen_p.upgraded,
            "gems": list(chosen_p.gems or []),
        }
        entry["state"] = "pick_merc_card"
        return render_merc_dialog(run, owner_uid)
    if state == "pick_merc_card":
        if idx == 0:
            entry["state"] = "main"
            entry.pop("player_card", None)
            return render_merc_dialog(run, owner_uid)
        grouped = _group_deck_cards(merc.deck)
        if idx < 1 or idx > len(grouped):
            return get_locale_text("i18n_mercenary.err_invalid_card_index", count=len(grouped))
        chosen_m, _ = grouped[idx - 1]
        p_info = entry.get("player_card") or {}
        chosen_p = CardState(id=p_info.get("id", ""), upgraded=bool(p_info.get("upgraded", False)), gems=list(p_info.get("gems", [])))
        p_match = next((ensure_card_state(c) for c in player.deck if ensure_card_state(c) == chosen_p), None)
        m_match = next((ensure_card_state(c) for c in merc.deck if ensure_card_state(c) == chosen_m), None)
        if p_match is None or m_match is None:
            entry["state"] = "main"
            entry["last_msg"] = get_locale_text("i18n_mercenary.swap_empty_deck")
            return render_merc_dialog(run, owner_uid)
        player.deck.remove(p_match)
        merc.deck.remove(m_match)
        player.deck.append(DeckService.clone_state(m_match))
        merc.deck.append(DeckService.clone_state(p_match))
        if run.node_type == "battle":
            _replace_active_card(player, p_match, m_match)
            _replace_active_card(merc, m_match, p_match)
        p_name = ALL_CARDS[p_match].name if p_match in ALL_CARDS else p_match.id
        m_name = ALL_CARDS[m_match].name if m_match in ALL_CARDS else m_match.id
        entry["state"] = "main"
        entry.pop("player_card", None)
        entry["last_msg"] = get_locale_text("i18n_mercenary.swap_success", owner_card=p_name, merc_name=merc.name, merc_card=m_name)
        return render_merc_dialog(run, owner_uid)
    return get_locale_text("i18n_mercenary.err_invalid_choice")


class MercenaryVoiceHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(CardPlayEvent, self.on_card_play)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(BattleWinEvent, self.on_battle_win)

    def _find_harry(self, run: Optional[GameRun], owner_uid: str = ""):
        if run is None:
            return None
        for uid in run.party_order:
            p = run.players.get(uid)
            if is_mercenary(p) and getattr(p, "mercenary_id", "") == "harry_du_bois" and p.hp > 0 and not p.downed:
                if not owner_uid or getattr(p, "mercenary_owner", "") == owner_uid or uid == owner_uid:
                    return p
        return None

    def _emit_voice(self, run: GameRun, harry: PlayerState, scenario: str, chance: float):
        if random.random() >= chance:
            return
        turn = int(run.node_data.get("turn_count", 1) or 1)
        counts = run.node_data.setdefault("harry_voice_counts", {})
        tkey = str(turn)
        if counts.get(tkey, 0) >= HARRY_MAX_VOICES_PER_TURN:
            return
        counts[tkey] = counts.get(tkey, 0) + 1
        skill_id = random.choice(HARRY_SKILL_IDS)
        skill_name = get_locale_text(f"i18n_mercenary.skills.{skill_id}.name")
        quote = get_locale_text(f"i18n_mercenary.skills.{skill_id}.quotes.{scenario}")
        owner = getattr(harry, "mercenary_owner", "") or run.user_id
        previous, previous_user = swap_player(run, harry)
        try:
            run.user_id = owner
            self.engine._log_event(run, get_locale_text("i18n_mercenary.skill_voice_format", skill_name=skill_name, quote=quote))
        finally:
            restore_player(run, previous, previous_user)

    def on_battle_start(self, event: BattleStartEvent):
        if is_mercenary(event.run.player) and getattr(event.run.player, "mercenary_id", "") == "harry_du_bois":
            self._emit_voice(event.run, event.run.player, "battle_start", 0.85)

    def on_turn_start(self, event: TurnStartEvent):
        if not event.is_player:
            return
        if is_mercenary(event.run.player) and getattr(event.run.player, "mercenary_id", "") == "harry_du_bois":
            self._emit_voice(event.run, event.run.player, "turn_start", HARRY_VOICE_CHANCE * 0.5)

    def on_card_play(self, event: CardPlayEvent):
        harry = self._find_harry(event.run, event.run.user_id)
        if harry is None:
            return
        self._emit_voice(event.run, harry, "card_play", HARRY_VOICE_CHANCE * 0.45)

    def on_damage_calculate(self, event: DamageCalculateEvent):
        if event.target != "p0" and not str(event.target).startswith("a"):
            return
        harry = self._find_harry(event.run, event.run.user_id)
        if harry is None:
            return
        self._emit_voice(event.run, harry, "take_damage", HARRY_VOICE_CHANCE * 0.45)

    def on_battle_win(self, event: BattleWinEvent):
        if is_mercenary(event.run.player) and getattr(event.run.player, "mercenary_id", "") == "harry_du_bois":
            self._emit_voice(event.run, event.run.player, "battle_win", 0.85)
