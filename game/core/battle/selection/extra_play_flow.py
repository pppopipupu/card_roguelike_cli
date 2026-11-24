from typing import Optional

from ....data.text.locale_data import get_locale_text
from ....models.events import CardEffectResolvedEvent, CardExtraTriggerEvent, CardPlayedEvent
from ....models.state import Card, CardState, GameRun
from .selector import TargetSelectorParser
from .session_state import (
    _advance_session,
    _build_selections_payload,
    _extract_primary_target,
    _render_step_prompt,
    _step_to_dict,
)


def join_messages(*parts: str) -> str:
    return "\n".join(p.strip() for p in parts if p and p.strip())


def card_state_meta(card: Card) -> dict:
    return {
        "card_id": card.id,
        "upgraded": bool(getattr(card, "upgraded", False)),
        "gems": list(getattr(card, "gems", None) or []),
        "enchantments": list(getattr(card, "enchantments", None) or []),
    }


def rebuild_card_from_meta(meta: dict) -> Optional[Card]:
    from ....entities import ALL_CARDS

    card_id = str(meta.get("card_id") or "")
    if not card_id:
        return None
    state = CardState(
        id=card_id,
        upgraded=bool(meta.get("upgraded", False)),
        gems=list(meta.get("gems") or []),
        enchantments=list(meta.get("enchantments") or []),
        replay=0,
    )
    return ALL_CARDS.get(state)


def finalize_extra_play_result(engine, run: GameRun, card: Card, meta: dict, raw_res: str) -> str:
    feedback = raw_res
    target = meta.get("target")
    if meta.get("dispatch_played_event", True):
        played_evt = CardPlayedEvent(run, card, target, raw_res, is_extra=True)
        engine.event_bus.dispatch(played_evt)
        feedback = played_evt.feedback
    if meta.get("dispatch_extra_event", True):
        engine.event_bus.dispatch(CardExtraTriggerEvent(run, card, str(meta.get("trigger_type") or "replay")))
    msg_key = str(meta.get("msg_key") or "")
    if msg_key:
        params = dict(meta.get("msg_params") or {})
        params.setdefault("res", feedback)
        params.setdefault("feedback", feedback)
        params.setdefault("name", card.name)
        return get_locale_text(msg_key, **params)
    return feedback


def start_chained_post_selection(
    engine,
    run: GameRun,
    card: Card,
    spec: dict,
    *,
    extra_play_meta: Optional[dict] = None,
    finalize_suspended_card: bool = False,
    extra_play_prefix_res: str = "",
) -> tuple[str, bool]:
    step_specs = spec["steps"]
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
        "can_cancel": False,
        "finalize_suspended_card": bool(finalize_suspended_card),
        "extra_play_meta": extra_play_meta,
        "extra_play_prefix_res": extra_play_prefix_res,
        "steps": session_steps,
        "current_step": 0,
    }
    if _advance_session(session):
        post_res = card.execute_post_selections(run, _build_selections_payload(session), engine)
        return post_res, False
    run.node_data.setdefault("state_stack", []).append(session)
    step = session["steps"][session["current_step"]]
    return _render_step_prompt(session, step), True


def drain_pending_extra_plays(card_player, run: GameRun, res: str) -> tuple[str, bool]:
    engine = card_player.engine
    pending = run.node_data.get("pending_extra_plays")
    if not isinstance(pending, list) or not pending:
        return res, False
    accum = res
    while pending:
        if engine.is_battle_won(run) or run.player.hp <= 0:
            pending.clear()
            break
        meta = pending.pop(0)
        card = rebuild_card_from_meta(meta)
        if card is None:
            continue
        spec = card.get_selection_spec(run, engine)
        post_spec = card.get_post_selection_spec(run, engine)
        if spec is None:
            raw_res = engine._execute_card_effect(run, card, meta.get("target"))
            if post_spec is not None:
                post_text, suspended = start_chained_post_selection(
                    engine,
                    run,
                    card,
                    post_spec,
                    extra_play_meta=meta,
                    extra_play_prefix_res=raw_res,
                )
                if suspended:
                    return join_messages(accum, raw_res, post_text), True
                raw_res = join_messages(raw_res, post_text)
            formatted = finalize_extra_play_result(engine, run, card, meta, raw_res)
            accum = join_messages(accum, formatted)
            continue
        if spec.get("phase") == "post_play":
            raw_res = engine._execute_card_effect(run, card, meta.get("target"))
            post_text, suspended = start_chained_post_selection(
                engine,
                run,
                card,
                spec,
                extra_play_meta=meta,
                extra_play_prefix_res=raw_res,
            )
            if suspended:
                return join_messages(accum, raw_res, post_text), True
            raw_res = join_messages(raw_res, post_text)
            formatted = finalize_extra_play_result(engine, run, card, meta, raw_res)
            accum = join_messages(accum, formatted)
            continue
        step_specs = spec["steps"]
        session_steps = [
            _step_to_dict(s, TargetSelectorParser.build_candidates(run, s, hand_idx=None))
            for s in step_specs
        ]
        if spec.get("empty_abort_check") and all(not st["candidates"] for st in session_steps):
            raw_res = card.execute_with_selections(run, {}, engine)
            engine.event_bus.dispatch(CardEffectResolvedEvent(run, card, meta.get("target"), raw_res))
            formatted = finalize_extra_play_result(engine, run, card, meta, raw_res)
            accum = join_messages(accum, formatted)
            continue
        session = {
            "type": "interaction_session",
            "owner_uid": run.user_id,
            "card_id": card.id,
            "card_name": card.name,
            "upgraded": bool(card.upgraded),
            "card_meta": card_state_meta(card),
            "phase": "extra_play",
            "can_cancel": False,
            "extra_play_meta": meta,
            "steps": session_steps,
            "current_step": 0,
        }
        if _advance_session(session):
            payload = _build_selections_payload(session)
            raw_res = card.execute_with_selections(run, payload, engine)
            primary_target = _extract_primary_target(payload) or meta.get("target")
            engine.event_bus.dispatch(CardEffectResolvedEvent(run, card, primary_target, raw_res))
            post_spec_now = card.get_post_selection_spec(run, engine)
            if post_spec_now is not None:
                post_text, suspended = start_chained_post_selection(
                    engine,
                    run,
                    card,
                    post_spec_now,
                    extra_play_meta=meta,
                    extra_play_prefix_res=raw_res,
                )
                if suspended:
                    return join_messages(accum, raw_res, post_text), True
                raw_res = join_messages(raw_res, post_text)
            formatted = finalize_extra_play_result(engine, run, card, meta, raw_res)
            accum = join_messages(accum, formatted)
            continue
        run.node_data.setdefault("state_stack", []).append(session)
        step = session["steps"][session["current_step"]]
        prompt = _render_step_prompt(session, step)
        return join_messages(accum, prompt), True
    if not pending:
        run.node_data.pop("pending_extra_plays", None)
    return accum, False


def complete_extra_play_session(card_player, run: GameRun, session: dict) -> tuple[str, bool]:
    engine = card_player.engine
    meta = dict(session.get("extra_play_meta") or {})
    card = rebuild_card_from_meta(meta or session.get("card_meta") or {"card_id": session.get("card_id"), "upgraded": session.get("upgraded")})
    if card is None:
        return drain_pending_extra_plays(card_player, run, "")
    payload = _build_selections_payload(session)
    raw_res = card.execute_with_selections(run, payload, engine)
    primary_target = _extract_primary_target(payload) or meta.get("target")
    engine.event_bus.dispatch(CardEffectResolvedEvent(run, card, primary_target, raw_res))
    post_spec = card.get_post_selection_spec(run, engine)
    if post_spec is not None:
        post_text, suspended = start_chained_post_selection(
            engine,
            run,
            card,
            post_spec,
            extra_play_meta=meta,
            extra_play_prefix_res=raw_res,
        )
        if suspended:
            return join_messages(raw_res, post_text), True
        raw_res = join_messages(raw_res, post_text)
    formatted = finalize_extra_play_result(engine, run, card, meta, raw_res)
    return drain_pending_extra_plays(card_player, run, formatted)


def resolve_pre_play_post_and_extra(
    card_player,
    run: GameRun,
    card: Card,
    c_state,
    hand_idx: Optional[int],
    primary_target: Optional[str],
    req_a: int,
    req_ba: int,
    res: str,
    *,
    already_suspended: bool,
) -> tuple[str, bool]:
    engine = card_player.engine
    p = run.player
    engine.event_bus.dispatch(CardEffectResolvedEvent(run, card, primary_target, res))
    post_spec = card.get_post_selection_spec(run, engine)
    if post_spec is not None:
        if not already_suspended:
            run.node_data["suspended_card_cid"] = c_state
            run.node_data["suspended_card_cost_a"] = req_a
            run.node_data["suspended_card_cost_ba"] = req_ba
            run.node_data["suspended_card_hand_idx"] = (hand_idx - 1) if hand_idx is not None else None
        run.node_data["suspended_card_primary_target"] = primary_target
        post_text, post_suspended = start_chained_post_selection(
            engine,
            run,
            card,
            post_spec,
            finalize_suspended_card=True,
        )
        res = join_messages(res, post_text)
        if post_suspended:
            return res, True
        run.node_data.pop("suspended_card_primary_target", None)
        if already_suspended:
            engine.resolve_suspended_card(run, target=primary_target)
        else:
            run.node_data.pop("suspended_card_cid", None)
            run.node_data.pop("suspended_card_cost_a", None)
            run.node_data.pop("suspended_card_cost_ba", None)
            run.node_data.pop("suspended_card_hand_idx", None)
            res, _ = card_player._finalize_card_play(
                run, p, card, c_state, primary_target, res, source="played", register=True
            )
    elif already_suspended:
        engine.resolve_suspended_card(run, target=primary_target)
    else:
        res, _ = card_player._finalize_card_play(
            run, p, card, c_state, primary_target, res, source="played", register=True
        )
    return drain_pending_extra_plays(card_player, run, res)


def complete_post_play_session(card_player, run: GameRun, session: dict) -> tuple[str, bool]:
    engine = card_player.engine
    card_meta = session.get("card_meta") or {
        "card_id": session.get("card_id"),
        "upgraded": session.get("upgraded"),
    }
    card = rebuild_card_from_meta(card_meta)
    post_res = card.execute_post_selections(run, _build_selections_payload(session), engine) if card else ""
    if session.get("finalize_suspended_card"):
        target = run.node_data.pop("suspended_card_primary_target", None)
        engine.resolve_suspended_card(run, target=target)
        return drain_pending_extra_plays(card_player, run, post_res)
    extra_meta = session.get("extra_play_meta")
    if isinstance(extra_meta, dict):
        prefix_res = str(session.get("extra_play_prefix_res") or "")
        combined_raw = join_messages(prefix_res, post_res)
        formatted = finalize_extra_play_result(engine, run, card, extra_meta, combined_raw) if card else combined_raw
        return drain_pending_extra_plays(card_player, run, formatted)
    return drain_pending_extra_plays(card_player, run, post_res)
