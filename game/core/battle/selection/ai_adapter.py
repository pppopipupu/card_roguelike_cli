from ....models.state import GameRun, ensure_card_state
from .session_flow import _execute_pre_play_card
from .session_state import (
    _build_selections_payload,
    _is_step_complete,
    _remaining_for_step,
)
from .spec import PILE_ATTR_MAP


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
        from ....entities import ALL_CARDS
        card = ALL_CARDS.get(session.get("card_id"))
        if card is not None and session.get("upgraded"):
            card = ALL_CARDS.get(f"{session['card_id']}+") or card
        if card is not None:
            res = card.execute_post_selections(run, _build_selections_payload(session), battle_engine)
            if res:
                notes.append(res)
        return notes

    from ....entities import ALL_CARDS
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
    from ....entities import ALL_CARDS
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
