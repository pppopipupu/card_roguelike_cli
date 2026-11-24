from typing import Optional

from ....data.text.locale_data import get_locale_text
from ....models.events import CardPlayEvent
from ....models.state import Card, GameRun
from .extra_play_flow import (
    card_state_meta,
    drain_pending_extra_plays,
    resolve_pre_play_post_and_extra,
)
from .selector import TargetSelectorParser
from .session_state import (
    _advance_session,
    _build_selections_payload,
    _consume_tokens_into_session,
    _extract_primary_target,
    _remaining_for_step,
    _render_step_prompt,
    _step_to_dict,
    _validate_all_selections_live,
)
from .spec import SelectionStepSpec


def _play_cancelled_message(play_evt, card) -> str:
    return play_evt.cancel_message or get_locale_text("i18n_battle_core.spacetime_distortion", name=card.name)


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
        run.node_data["current_playing_card_hand_idx"] = hand_idx - 1
        play_evt = CardPlayEvent(run, card, primary_target, req_a, req_ba)
        engine.event_bus.dispatch(play_evt)
        if play_evt.cancelled:
            run.node_data.pop("current_playing_card_hand_idx", None)
            run.node_data.pop("prism_pending_refracts", None)
            return _play_cancelled_message(play_evt, card)
        req_a = play_evt.cost_a
        req_ba = play_evt.cost_ba
        if p.actions < req_a or p.bonus_actions < req_ba:
            run.node_data.pop("current_playing_card_hand_idx", None)
            run.node_data.pop("prism_pending_refracts", None)
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
    run.node_data["extra_play_msgs"] = []
    suspended_after = False
    try:
        res = card.execute_with_selections(run, selections, engine)
        res, suspended_after = resolve_pre_play_post_and_extra(
            card_player,
            run,
            card,
            c_state,
            hand_idx,
            primary_target,
            req_a,
            req_ba,
            res,
            already_suspended=already_suspended,
        )
    finally:
        run.node_data["current_playing_card_id"] = ""
        run.node_data["current_playing_card_cid"] = ""
        run.node_data.pop("current_playing_card_hand_idx", None)
        run.node_data.pop("split_to_ten_active", None)
    engine.save_manager.save_save(run.user_id, run)
    if not suspended_after:
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
    run.node_data["current_playing_card_hand_idx"] = hand_idx - 1
    play_evt = CardPlayEvent(run, card, None, req_a, req_ba)
    engine.event_bus.dispatch(play_evt)
    if play_evt.cancelled:
        run.node_data.pop("current_playing_card_hand_idx", None)
        run.node_data.pop("prism_pending_refracts", None)
        return _play_cancelled_message(play_evt, card)
    req_a = play_evt.cost_a
    req_ba = play_evt.cost_ba
    if p.actions < req_a or p.bonus_actions < req_ba:
        run.node_data.pop("current_playing_card_hand_idx", None)
        run.node_data.pop("prism_pending_refracts", None)
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
        return _play_cancelled_message(play_evt, card)
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
        "type": "interaction_session",
        "owner_uid": run.user_id,
        "card_id": card.id,
        "card_name": card.name,
        "upgraded": bool(card.upgraded),
        "card_meta": card_state_meta(card),
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
        combined, suspended_extra = drain_pending_extra_plays(card_player, run, combined)
        engine.save_manager.save_save(run.user_id, run)
        if not suspended_extra:
            combined = card_player._post_battle_action_check(run, initial_status, combined, p)
        return engine._append_logs_to_res(run, combined)

    run.node_data.setdefault("state_stack", []).append(session)
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
    """创建并推进一次卡牌选择会话，必要时挂起等待玩家输入。"""
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
        "type": "interaction_session",
        "owner_uid": run.user_id,
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
