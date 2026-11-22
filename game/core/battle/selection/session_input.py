from typing import Tuple

from ....data.text.locale_data import get_locale_text
from ....models.state import GameRun, ensure_card_state
from .selector import TargetSelectorParser
from .session_flow import _execute_pre_play_card
from .session_state import (
    CHOOSE_COMMAND_PREFIXES,
    INTERACTION_RESERVED_COMMANDS,
    _advance_session,
    _build_selections_payload,
    _is_step_complete,
    _remaining_for_step,
    _render_step_prompt,
    _selected_uids_for_step,
    _try_auto_fill_step,
    _validate_all_selections_live,
    format_candidate_options,
)


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
    from ...cli.actions import finalize_defeat, finalize_victory

    engine = action_router.engine
    battle_engine = engine.battle_engine if hasattr(engine, "battle_engine") else engine
    state_stack = run.node_data.get("state_stack", [])
    if session.get("phase") == "post_play":
        from ....entities import ALL_CARDS
        if not _validate_all_selections_live(run, session, hand_idx=None):
            for step in session.get("steps", []):
                step["selected"] = []
            session["current_step"] = 0
            cur_step = session["steps"][0]
            action_router.save_manager.save_save(user_id, run)
            return get_locale_text("i18n_cli_core.select_revalidate_failed") + "\n" + _render_step_prompt(session, cur_step), False, False
        if state_stack and state_stack[-1] is session:
            state_stack.pop()
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
    from ....entities import ALL_CARDS
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
    """处理选择会话中的玩家输入，返回文本、是否结束回合与是否成功。"""
    from ...cli.base.aliases import (
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
