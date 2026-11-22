from typing import Optional

from ....data.text.locale_data import get_locale_text
from ....models.state import ensure_card_state
from .selector import TargetSelectorParser
from .spec import PILE_ATTR_MAP, SelectionStepSpec

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
    if scope == "option":
        return True
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
