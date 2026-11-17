from typing import Any, Optional, Tuple

from ...data.locale_data import get_locale_text
from ...models.events import CardPlayEvent
from ...models.state import Card, GameRun, ensure_card_state
from .target_selector import (
    PILE_ATTR_MAP,
    SelectionStepSpec,
    TargetSelectorParser,
    pop_selected_pile_cards,
)

CHOOSE_COMMAND_PREFIXES = ("选择", "c")
INTERACTION_RESERVED_COMMANDS = {
    "使用",
    "p",
    "随从",
    "m",
    "结束",
    "e",
    "end",
    "特殊",
    "sa",
    "队列",
    "q",
    "queue",
    "qi",
    "药水",
    "potion",
    "pot",
    "drink",
    "throw",
    "t",
    "dp",
    "技能",
    "skill",
    "sk",
    "k",
    "状态",
    "status",
    "r",
    "抽牌堆",
    "draw",
    "弃牌堆",
    "discard",
    "消耗堆",
    "exhaust",
    "随从墓地",
    "mg",
    "敌方墓地",
    "eg",
    "帮助",
    "help",
}


def format_candidate_options(candidates: list[dict], selected_uids: set[str]) -> str:
    remaining = [c for c in candidates if c["uid"] not in selected_uids]
    return "\n".join(f"{idx}. {cand['label']}" for idx, cand in enumerate(remaining, 1))


def _step_to_dict(spec: SelectionStepSpec, candidates: list[dict]) -> dict:
    return {
        "step_id": spec.step_id,
        "kind": spec.kind,
        "min_count": int(spec.min_count),
        "max_count": int(spec.max_count),
        "required": bool(spec.required),
        "auto_single": bool(spec.auto_single),
        "allow_simple_auto": bool(spec.allow_simple_auto),
        "prompt_key": spec.prompt_key,
        "continue_key": spec.continue_key,
        "error_key": spec.error_key,
        "invalid_index_key": spec.invalid_index_key,
        "empty_key": spec.empty_key,
        "candidates": candidates,
        "selected": [],
    }


def _selected_uids_for_step(step: dict) -> set[str]:
    return {item["uid"] for item in step.get("selected", [])}


def _remaining_for_step(step: dict) -> list[dict]:
    used = _selected_uids_for_step(step)
    return [c for c in step.get("candidates", []) if c["uid"] not in used]


def _is_step_complete(step: dict) -> bool:
    selected_cnt = len(step.get("selected", []))
    remaining_cnt = len(_remaining_for_step(step))
    max_cnt = int(step.get("max_count", 1))
    min_cnt = int(step.get("min_count", 1))
    if selected_cnt >= max_cnt:
        return True
    if remaining_cnt == 0 and selected_cnt >= min_cnt:
        return True
    if not step.get("candidates") and not step.get("required", True):
        return True
    return False


def _try_auto_fill_step(step: dict) -> bool:
    if not step.get("auto_single", True):
        return False
    changed = False
    while not _is_step_complete(step):
        remaining = _remaining_for_step(step)
        if len(remaining) == 1:
            only_cand = dict(remaining[0])
            only_cand["auto_filled"] = True
            step.setdefault("selected", []).append(only_cand)
            changed = True
        else:
            break
    return changed


def _build_selections_payload(session: dict) -> dict[str, list[dict]]:
    return {step["step_id"]: list(step.get("selected", [])) for step in session.get("steps", [])}


def _render_step_prompt(session: dict, step: dict, prefix_msg: str = "") -> str:
    remaining = _remaining_for_step(step)
    options_str = "\n".join(f"{idx}. {cand['label']}" for idx, cand in enumerate(remaining, 1))
    selected = step.get("selected", [])
    card_name = session.get("card_name", "")
    if selected and step.get("continue_key"):
        last_name = selected[-1].get("label", "")
        body = get_locale_text(
            step["continue_key"],
            card_name=card_name,
            card_name_last=last_name,
            chosen_name=last_name,
            next_index=len(selected) + 1,
            exhaust_list=options_str,
            options=options_str,
            hand_list=options_str,
        )
    else:
        body = get_locale_text(
            step.get("prompt_key", "i18n_cli_core.select_prompt_default"),
            card_name=card_name,
            options=options_str,
            exhaust_list=options_str,
            hand_list=options_str,
        )
    hints = []
    if not step.get("required", True) or (len(selected) >= int(step.get("min_count", 1)) and int(step.get("max_count", 1)) > len(selected)):
        hints.append(
            get_locale_text(
                "i18n_cli_core.select_prompt_optional_hint",
                max_count=step.get("max_count", 1),
                selected_count=len(selected),
            )
        )
    if _has_manual_history(session):
        hints.append(get_locale_text("i18n_cli_core.select_prompt_back_hint"))
    full = "\n".join([p for p in [prefix_msg, body, *hints] if p])
    return full


def _has_manual_history(session: dict) -> bool:
    for step in session.get("steps", []):
        for item in step.get("selected", []):
            if not item.get("auto_filled"):
                return True
    return False


def _advance_session(session: dict) -> bool:
    steps = session.get("steps", [])
    idx = int(session.get("current_step", 0))
    while idx < len(steps):
        step = steps[idx]
        if not step.get("candidates"):
            idx += 1
            continue
        _try_auto_fill_step(step)
        if _is_step_complete(step):
            idx += 1
            continue
        session["current_step"] = idx
        return False
    session["current_step"] = len(steps)
    return True


def _validate_candidate_live(run, cand: dict, hand_idx: Optional[int] = None, exclude_playing: bool = False) -> bool:
    scope = cand.get("scope", "")
    if scope == "self":
        return run.player.hp > 0 and not run.player.downed
    if scope == "enemy":
        idx = int(cand.get("source_idx", 0)) - 1
        return 0 <= idx < len(run.enemies) and run.enemies[idx].hp > 0
    if scope == "own_minion":
        grid = str(cand.get("source_idx", ""))
        return grid in run.player.minions
    if scope in ("ally_player", "ally_minion"):
        slot = cand.get("ally_slot")
        if not isinstance(slot, int) or slot < 1 or slot > len(run.party_order):
            return False
        uid = run.party_order[slot - 1]
        ally = run.players.get(uid)
        if ally is None or ally.downed or ally.hp <= 0:
            return False
        if scope == "ally_minion":
            grid = str(cand.get("source_idx", ""))
            return grid in ally.minions
        return True
    if scope in PILE_ATTR_MAP:
        pile = getattr(run.player, PILE_ATTR_MAP[scope], []) or []
        src_idx = cand.get("source_idx")
        card_id = cand.get("card_id")
        upgraded = bool(cand.get("upgraded", False))
        gems = list(cand.get("gems", []) or [])
        if isinstance(src_idx, int) and 0 <= src_idx < len(pile):
            st = ensure_card_state(pile[src_idx])
            if st.id == card_id and bool(st.upgraded) == upgraded and list(st.gems or []) == gems:
                if not (exclude_playing and scope == "hand" and hand_idx is not None and src_idx == hand_idx - 1):
                    return True
        for i, raw_c in enumerate(pile):
            if exclude_playing and scope == "hand" and hand_idx is not None and i == hand_idx - 1:
                continue
            st = ensure_card_state(raw_c)
            if st.id == card_id and bool(st.upgraded) == upgraded and list(st.gems or []) == gems:
                return True
        return False
    if scope == "minion_graveyard":
        return cand.get("entry_id") in (getattr(run.player, "minion_graveyard", []) or [])
    if scope == "enemy_graveyard":
        return cand.get("entry_id") in (getattr(run.player, "enemy_graveyard", []) or [])
    if scope == "ally_minion_graveyard":
        slot = cand.get("ally_slot")
        if not isinstance(slot, int) or slot < 1 or slot > len(run.party_order):
            return False
        ally = run.players.get(run.party_order[slot - 1])
        return ally is not None and cand.get("entry_id") in (getattr(ally, "minion_graveyard", []) or [])
    return True


def _validate_all_selections_live(run, session: dict, hand_idx: Optional[int] = None) -> bool:
    exclude_playing = session.get("phase") == "pre_play" and hand_idx is not None
    for step in session.get("steps", []):
        for cand in step.get("selected", []):
            if not _validate_candidate_live(run, cand, hand_idx=hand_idx, exclude_playing=exclude_playing):
                return False
    return True


def _extract_primary_target(selections: dict[str, list[dict]]) -> Optional[str]:
    for items in selections.values():
        for item in items:
            if item.get("scope") in ("enemy", "self", "own_minion", "ally_player", "ally_minion"):
                return item.get("value")
    return None


def _consume_tokens_into_session(session: dict, tokens: list[str]) -> tuple[bool, Optional[str]]:
    steps = session.get("steps", [])
    token_idx = 0
    step_idx = 0
    while step_idx < len(steps):
        step = steps[step_idx]
        if not step.get("candidates"):
            step_idx += 1
            continue
        while not _is_step_complete(step) and token_idx < len(tokens):
            token = tokens[token_idx]
            matched = TargetSelectorParser.resolve_token(
                step["candidates"],
                token,
                _selected_uids_for_step(step),
            )
            if matched is None:
                session["current_step"] = step_idx
                return False, token
            chosen = dict(matched)
            chosen["auto_filled"] = False
            step.setdefault("selected", []).append(chosen)
            token_idx += 1
        if token_idx >= len(tokens):
            break
        step_idx += 1
    session["current_step"] = step_idx
    return True, None


def _execute_pre_play_card(
    card_player,
    run: GameRun,
    card: Card,
    c_state,
    hand_idx: Optional[int],
    selections: dict[str, list[dict]],
    req_a: int,
    req_ba: int,
    *,
    already_suspended: bool,
) -> str:
    p = run.player
    engine = card_player.engine
    initial_status = [(e.hp, e.shield) for e in run.enemies]
    primary_target = _extract_primary_target(selections)
    if not already_suspended:
        if hand_idx is None or hand_idx < 1 or hand_idx > len(p.hand):
            return get_locale_text("i18n_battle_core.invalid_hand_index")
        play_err = card.can_play_error(run, primary_target, engine)
        if play_err:
            return play_err
        play_evt = CardPlayEvent(run, card, primary_target, req_a, req_ba)
        engine.event_bus.dispatch(play_evt)
        if play_evt.cancelled:
            return get_locale_text("i18n_battle_core.spacetime_distortion", name=card.name)
        req_a = play_evt.cost_a
        req_ba = play_evt.cost_ba
        if p.actions < req_a or p.bonus_actions < req_ba:
            return get_locale_text(
                "i18n_battle_core.insufficient_actions",
                req_a=req_a,
                req_ba=req_ba,
                actions=p.actions,
                bonus_actions=p.bonus_actions,
            )
        p.actions -= req_a
        p.bonus_actions -= req_ba
        p.hand.pop(hand_idx - 1)
    run.node_data["current_playing_card_cid"] = c_state
    run.node_data["current_playing_card_id"] = card.id
    run.node_data["card_played_triggered_dmg"] = False
    run.node_data["card_played_triggered_shield"] = False
    run.node_data["card_played_triggered_heal"] = False
    run.node_data["extra_play_msgs"] = []
    try:
        res = card.execute_with_selections(run, selections, engine)
        if already_suspended:
            engine.resolve_suspended_card(run, target=primary_target)
        else:
            res, _ = card_player._finalize_card_play(
                run,
                p,
                card,
                c_state,
                primary_target,
                res,
                source="played",
                register=True,
            )
    finally:
        run.node_data["current_playing_card_id"] = ""
        run.node_data["current_playing_card_cid"] = ""
        run.node_data.pop("current_playing_card_hand_idx", None)
        run.node_data.pop("split_to_ten_active", None)
    engine.save_manager.save_save(run.user_id, run)
    res = card_player._post_battle_action_check(run, initial_status, res, p)
    return engine._append_logs_to_res(run, res)


def _suspend_pre_play(
    card_player,
    run: GameRun,
    card: Card,
    c_state,
    hand_idx: int,
    req_a: int,
    req_ba: int,
    session: dict,
    prefix_msg: str = "",
) -> str:
    p = run.player
    engine = card_player.engine
    play_evt = CardPlayEvent(run, card, None, req_a, req_ba)
    engine.event_bus.dispatch(play_evt)
    if play_evt.cancelled:
        return get_locale_text("i18n_battle_core.spacetime_distortion", name=card.name)
    req_a = play_evt.cost_a
    req_ba = play_evt.cost_ba
    if p.actions < req_a or p.bonus_actions < req_ba:
        return get_locale_text(
            "i18n_battle_core.insufficient_actions",
            req_a=req_a,
            req_ba=req_ba,
            actions=p.actions,
            bonus_actions=p.bonus_actions,
        )
    p.actions -= req_a
    p.bonus_actions -= req_ba
    p.hand.pop(hand_idx - 1)
    run.node_data["suspended_card_cid"] = c_state
    run.node_data["suspended_card_cost_a"] = req_a
    run.node_data["suspended_card_cost_ba"] = req_ba
    run.node_data["suspended_card_hand_idx"] = hand_idx - 1
    run.node_data.setdefault("state_stack", []).append(session)
    engine.save_manager.save_save(run.user_id, run)
    step = session["steps"][session["current_step"]]
    return engine._append_logs_to_res(run, _render_step_prompt(session, step, prefix_msg=prefix_msg))


def _start_post_play_selection(
    card_player,
    run: GameRun,
    card: Card,
    c_state,
    hand_idx: int,
    spec: dict,
    tokens: list[str],
    req_a: int,
    req_ba: int,
) -> str:
    p = run.player
    engine = card_player.engine
    initial_status = [(e.hp, e.shield) for e in run.enemies]
    step_specs: list[SelectionStepSpec] = spec["steps"]
    first_target = None
    remaining_tokens = list(tokens)
    if step_specs and step_specs[0].allow_simple_auto:
        first_spec = step_specs[0]
        first_cands = TargetSelectorParser.build_candidates(run, first_spec, hand_idx=hand_idx)
        if remaining_tokens:
            first_parsed = TargetSelectorParser.parse_token(remaining_tokens[0])
            if first_parsed.scope in ("hand", "exhaust", "discard", "draw", "minion_graveyard", "enemy_graveyard", "ally_minion_graveyard"):
                first_target = first_cands[0]["value"] if first_cands else engine._get_first_alive_enemy(run)
            else:
                matched = TargetSelectorParser.resolve_token(first_cands, remaining_tokens[0])
                if matched is None:
                    return get_locale_text("i18n_battle_core.invalid_target")
                first_target = matched["value"]
                remaining_tokens.pop(0)
        else:
            first_target = first_cands[0]["value"] if first_cands else engine._get_first_alive_enemy(run)

    play_evt = CardPlayEvent(run, card, first_target, req_a, req_ba)
    engine.event_bus.dispatch(play_evt)
    if play_evt.cancelled:
        return get_locale_text("i18n_battle_core.spacetime_distortion", name=card.name)
    req_a = play_evt.cost_a
    req_ba = play_evt.cost_ba
    if p.actions < req_a or p.bonus_actions < req_ba:
        return get_locale_text(
            "i18n_battle_core.insufficient_actions",
            req_a=req_a,
            req_ba=req_ba,
            actions=p.actions,
            bonus_actions=p.bonus_actions,
        )
    p.actions -= req_a
    p.bonus_actions -= req_ba
    p.hand.pop(hand_idx - 1)
    run.node_data["current_playing_card_cid"] = c_state
    run.node_data["current_playing_card_id"] = card.id
    run.node_data["card_played_triggered_dmg"] = False
    run.node_data["card_played_triggered_shield"] = False
    run.node_data["card_played_triggered_heal"] = False
    run.node_data["extra_play_msgs"] = []
    try:
        res = engine._execute_card_effect(run, card, first_target)
        res, _ = card_player._finalize_card_play(run, p, card, c_state, first_target, res, source="played", register=True)
    finally:
        run.node_data["current_playing_card_id"] = ""
        run.node_data["current_playing_card_cid"] = ""
        run.node_data.pop("current_playing_card_hand_idx", None)

    follow_specs = step_specs[1:] if (step_specs and step_specs[0].allow_simple_auto) else step_specs
    session_steps = [_step_to_dict(s, TargetSelectorParser.build_candidates(run, s)) for s in follow_specs]
    session = {
        "type": "card_selection",
        "card_id": card.id,
        "card_name": card.name,
        "upgraded": bool(card.upgraded),
        "phase": "post_play",
        "can_cancel": bool(spec.get("can_cancel", False)),
        "steps": session_steps,
        "current_step": 0,
    }
    ok, bad_token = _consume_tokens_into_session(session, remaining_tokens)
    all_done = ok and _advance_session(session)
    if all_done:
        post_res = card.execute_post_selections(run, _build_selections_payload(session), engine)
        combined = f"{res}\n{post_res}".strip() if post_res else res
        engine.save_manager.save_save(run.user_id, run)
        combined = card_player._post_battle_action_check(run, initial_status, combined, p)
        return engine._append_logs_to_res(run, combined)

    run.node_data.setdefault("state_stack", []).append(session)
    if any(s["step_id"] == "discard_card" for s in session_steps):
        run.node_data["pending_discard"] = True
    step = session["steps"][session["current_step"]]
    prefix = ""
    if not ok and bad_token is not None:
        prefix = get_locale_text("i18n_cli_core.select_param_error_fallback", token=bad_token, options="")
    prompt = _render_step_prompt(session, step, prefix_msg=prefix)
    combined = f"{res}\n{prompt}".strip() if res else prompt
    engine.save_manager.save_save(run.user_id, run)
    return engine._append_logs_to_res(run, combined)


def start_card_selection(
    card_player,
    run: GameRun,
    card: Card,
    c_state,
    hand_idx: int,
    raw_target: Optional[str],
    req_a: int,
    req_ba: int,
    spec: dict,
) -> str:
    tokens = TargetSelectorParser.split_tokens(raw_target)
    if spec.get("phase") == "post_play":
        return _start_post_play_selection(card_player, run, card, c_state, hand_idx, spec, tokens, req_a, req_ba)

    step_specs: list[SelectionStepSpec] = spec["steps"]
    session_steps = [
        _step_to_dict(s, TargetSelectorParser.build_candidates(run, s, hand_idx=hand_idx))
        for s in step_specs
    ]
    if spec.get("empty_abort_check") and all(not st["candidates"] for st in session_steps):
        return card.execute_with_selections(run, {}, card_player.engine)

    session = {
        "type": "card_selection",
        "card_id": card.id,
        "card_name": card.name,
        "upgraded": bool(card.upgraded),
        "phase": "pre_play",
        "can_cancel": bool(spec.get("can_cancel", True)),
        "cancel_key": spec.get("cancel_key", "i18n_cli_core.select_cancelled"),
        "steps": session_steps,
        "current_step": 0,
    }
    ok, bad_token = _consume_tokens_into_session(session, tokens)
    if not ok and bad_token is not None:
        if all(len(st.get("candidates", [])) <= 1 for st in session_steps):
            first_spec = step_specs[0]
            return get_locale_text(first_spec.invalid_index_key, count=len(session_steps[0]["candidates"]))
    all_done = ok and _advance_session(session)
    if all_done:
        if not _validate_all_selections_live(run, session, hand_idx=hand_idx):
            return get_locale_text("i18n_cli_core.select_revalidate_failed")
        return _execute_pre_play_card(
            card_player,
            run,
            card,
            c_state,
            hand_idx,
            _build_selections_payload(session),
            req_a,
            req_ba,
            already_suspended=False,
        )

    p = run.player
    play_err = card.can_play_error(run, None, card_player.engine)
    if play_err:
        return play_err
    if p.actions < req_a or p.bonus_actions < req_ba:
        return get_locale_text(
            "i18n_battle_core.insufficient_actions",
            req_a=req_a,
            req_ba=req_ba,
            actions=p.actions,
            bonus_actions=p.bonus_actions,
        )
    prefix = ""
    if not ok and bad_token is not None:
        step_now = session["steps"][session["current_step"]]
        prefix = get_locale_text(step_now.get("invalid_index_key", "i18n_cli_core.select_invalid_index_default"), count=len(_remaining_for_step(step_now)))
    return _suspend_pre_play(card_player, run, card, c_state, hand_idx, req_a, req_ba, session, prefix_msg=prefix)


def _step_back(session: dict) -> bool:
    steps = session.get("steps", [])
    idx = min(int(session.get("current_step", 0)), len(steps) - 1)
    while idx >= 0:
        selected = steps[idx].get("selected", [])
        while selected:
            last = selected.pop()
            if not last.get("auto_filled"):
                session["current_step"] = idx
                return True
        idx -= 1
    return False


def _finalize_interaction_session(action_router, router, user_id: str, run: GameRun, session: dict) -> Tuple[str, bool, bool]:
    from ..cli.actions import finalize_defeat, finalize_victory

    engine = action_router.engine
    battle_engine = engine.battle_engine if hasattr(engine, "battle_engine") else engine
    state_stack = run.node_data.get("state_stack", [])
    if session.get("phase") == "post_play":
        from ...entities import ALL_CARDS
        if not _validate_all_selections_live(run, session, hand_idx=None):
            for step in session.get("steps", []):
                step["selected"] = []
            session["current_step"] = 0
            cur_step = session["steps"][0]
            action_router.save_manager.save_save(user_id, run)
            return get_locale_text("i18n_cli_core.select_revalidate_failed") + "\n" + _render_step_prompt(session, cur_step), False, False
        if state_stack and state_stack[-1] is session:
            state_stack.pop()
        run.node_data.pop("pending_discard", None)
        run.node_data.pop("pending_discard_source", None)
        card = ALL_CARDS.get(session.get("card_id"))
        if card is not None and session.get("upgraded"):
            card = ALL_CARDS.get(f"{session['card_id']}+") or card
        res = card.execute_post_selections(run, _build_selections_payload(session), battle_engine) if card else ""
        action_router.save_manager.save_save(user_id, run)
        if run.player.hp <= 0:
            return finalize_defeat(action_router.save_manager, user_id, run, res, True)
        if engine.is_battle_won(run):
            return finalize_victory(action_router.save_manager, engine, user_id, run, res, True, append_logs=True)
        return battle_engine._append_logs_to_res(run, res), False, True

    if not _validate_all_selections_live(run, session, hand_idx=None):
        if state_stack and state_stack[-1] is session:
            state_stack.pop()
        battle_engine.rollback_suspended_card(run)
        action_router.save_manager.save_save(user_id, run)
        return get_locale_text("i18n_cli_core.select_revalidate_failed"), False, False

    if state_stack and state_stack[-1] is session:
        state_stack.pop()
    from ...entities import ALL_CARDS
    suspended_state = run.node_data.get("suspended_card_cid")
    card = ALL_CARDS.get(ensure_card_state(suspended_state)) if suspended_state else ALL_CARDS.get(session.get("card_id"))
    if card is None:
        battle_engine.rollback_suspended_card(run)
        action_router.save_manager.save_save(user_id, run)
        return get_locale_text("i18n_battle_core.card_not_found"), False, False

    res = _execute_pre_play_card(
        battle_engine.card_player,
        run,
        card,
        ensure_card_state(suspended_state) if suspended_state else ensure_card_state(card.id),
        None,
        _build_selections_payload(session),
        0,
        0,
        already_suspended=True,
    )
    success = "❌" not in res
    if run.player.hp <= 0:
        return finalize_defeat(action_router.save_manager, user_id, run, res, success)
    if engine.is_battle_won(run):
        return finalize_victory(action_router.save_manager, engine, user_id, run, res, success)
    return res, False, success


def handle_selection_input(action_router, router, user_id: str, run: GameRun, parts: list[str]) -> Tuple[str, bool, bool]:
    from ..cli.base.aliases import (
        STATE_STACK_BACK_ALIASES,
        STATE_STACK_CANCEL_ALIASES,
        STATE_STACK_DONE_ALIASES,
    )
    state_stack = run.node_data.get("state_stack", [])
    session = state_stack[-1]
    engine = action_router.engine
    battle_engine = engine.battle_engine if hasattr(engine, "battle_engine") else engine
    head = parts[0].strip().lower()
    joined = " ".join(parts).strip()
    joined_lower = joined.lower()
    cur_idx = min(int(session.get("current_step", 0)), len(session.get("steps", [])) - 1)
    step = session["steps"][cur_idx]

    if head in STATE_STACK_CANCEL_ALIASES or joined_lower in STATE_STACK_CANCEL_ALIASES:
        if not session.get("can_cancel", True):
            return get_locale_text("i18n_cli_core.select_cannot_cancel") + "\n" + _render_step_prompt(session, step), False, False
        state_stack.pop()
        battle_engine.rollback_suspended_card(run)
        action_router.save_manager.save_save(user_id, run)
        cancel_key = session.get("cancel_key", "i18n_cli_core.select_cancelled")
        return battle_engine._append_logs_to_res(
            run,
            get_locale_text(cancel_key, card_name=session.get("card_name", "")),
        ), False, False

    if head in STATE_STACK_BACK_ALIASES or joined_lower in STATE_STACK_BACK_ALIASES:
        if _step_back(session):
            action_router.save_manager.save_save(user_id, run)
            prev_step = session["steps"][session["current_step"]]
            return get_locale_text(
                "i18n_cli_core.select_back_success",
                options=format_candidate_options(prev_step["candidates"], _selected_uids_for_step(prev_step)),
            ), False, True
        return get_locale_text("i18n_cli_core.select_back_first_step") + "\n" + _render_step_prompt(session, step), False, False

    if head in STATE_STACK_DONE_ALIASES or joined_lower in STATE_STACK_DONE_ALIASES:
        selected_cnt = len(step.get("selected", []))
        min_cnt = int(step.get("min_count", 1))
        if step.get("required", True) and selected_cnt < min_cnt:
            return get_locale_text("i18n_cli_core.select_cannot_skip_required", min_count=min_cnt) + "\n" + _render_step_prompt(session, step), False, False
        session["current_step"] = cur_idx + 1
        if _advance_session(session):
            return _finalize_interaction_session(action_router, router, user_id, run, session)
        action_router.save_manager.save_save(user_id, run)
        next_step = session["steps"][session["current_step"]]
        return _render_step_prompt(session, next_step), False, True

    raw_tokens = parts[1:] if head in CHOOSE_COMMAND_PREFIXES else parts
    if head in CHOOSE_COMMAND_PREFIXES:
        if not raw_tokens:
            return get_locale_text("i18n_cli_core.err_need_card_index"), False, False
        sub_head = raw_tokens[0].strip().lower()
        if sub_head in STATE_STACK_CANCEL_ALIASES:
            return handle_selection_input(action_router, router, user_id, run, [sub_head])
        if sub_head in STATE_STACK_BACK_ALIASES:
            return handle_selection_input(action_router, router, user_id, run, [sub_head])
        if sub_head in STATE_STACK_DONE_ALIASES:
            return handle_selection_input(action_router, router, user_id, run, [sub_head])
    elif head in INTERACTION_RESERVED_COMMANDS:
        return get_locale_text(step.get("error_key", "i18n_cli_core.select_required_default"), card_name=session.get("card_name", "")), False, False

    tokens = TargetSelectorParser.split_tokens(" ".join(raw_tokens))
    if not tokens:
        return get_locale_text(step.get("error_key", "i18n_cli_core.select_required_default"), card_name=session.get("card_name", "")), False, False

    for token in tokens:
        cur_idx = int(session.get("current_step", 0))
        if cur_idx >= len(session["steps"]):
            break
        step = session["steps"][cur_idx]
        remaining = _remaining_for_step(step)
        matched = TargetSelectorParser.resolve_token(
            step["candidates"],
            token,
            _selected_uids_for_step(step),
        )
        if matched is None:
            return get_locale_text(
                step.get("invalid_index_key", "i18n_cli_core.select_invalid_index_default"),
                count=len(remaining),
            ), False, False
        chosen = dict(matched)
        chosen["auto_filled"] = False
        step.setdefault("selected", []).append(chosen)
        if _is_step_complete(step):
            _advance_session(session)
        else:
            _try_auto_fill_step(step)
            if _is_step_complete(step):
                _advance_session(session)

    if _advance_session(session):
        return _finalize_interaction_session(action_router, router, user_id, run, session)
    action_router.save_manager.save_save(user_id, run)
    next_step = session["steps"][session["current_step"]]
    return _render_step_prompt(session, next_step), False, True


def resolve_session_for_mercenary(battle_engine, run: GameRun, merc_uid: str, merc, session: dict, score_card_fn) -> list[str]:
    notes: list[str] = []
    for step in session.get("steps", []):
        while not _is_step_complete(step):
            remaining = _remaining_for_step(step)
            if not remaining:
                break
            best_cand = max(remaining, key=lambda c: _score_merc_candidate(merc, c, score_card_fn))
            chosen = dict(best_cand)
            chosen["auto_filled"] = False
            step.setdefault("selected", []).append(chosen)
    state_stack = run.node_data.get("state_stack", [])
    if state_stack and state_stack[-1] is session:
        state_stack.pop()
    if session.get("phase") == "post_play":
        from ...entities import ALL_CARDS
        run.node_data.pop("pending_discard", None)
        run.node_data.pop("pending_discard_source", None)
        card = ALL_CARDS.get(session.get("card_id"))
        if card is not None and session.get("upgraded"):
            card = ALL_CARDS.get(f"{session['card_id']}+") or card
        if card is not None:
            res = card.execute_post_selections(run, _build_selections_payload(session), battle_engine)
            if res:
                notes.append(res)
        return notes

    from ...entities import ALL_CARDS
    suspended_state = run.node_data.get("suspended_card_cid")
    card = ALL_CARDS.get(ensure_card_state(suspended_state)) if suspended_state else ALL_CARDS.get(session.get("card_id"))
    if card is None:
        battle_engine.rollback_suspended_card(run)
        return notes
    res = _execute_pre_play_card(
        battle_engine.card_player,
        run,
        card,
        ensure_card_state(suspended_state) if suspended_state else ensure_card_state(card.id),
        None,
        _build_selections_payload(session),
        0,
        0,
        already_suspended=True,
    )
    if res:
        notes.append(res)
    return notes


def _score_merc_candidate(merc, cand: dict, score_card_fn) -> int:
    from ...entities import ALL_CARDS
    scope = cand.get("scope", "")
    if scope in PILE_ATTR_MAP:
        cid = cand.get("card_id", "")
        card_obj = ALL_CARDS.get(cid)
        score = score_card_fn(merc, card_obj)
        if scope == "hand" and card_obj and (getattr(card_obj, "agile", False) or getattr(card_obj, "cryptic", False)):
            return score + 1000
        return score
    if scope == "enemy":
        return 100
    if scope == "own_minion":
        return 50
    if scope == "ally_player":
        return 30
    if scope == "self":
        return 10
    return 0
