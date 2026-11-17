import random
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ...data.locale_data import get_locale_text
from ...data.minion_data import MINION_CONFIG
from ...models.state import ensure_card_state

SELECTOR_ALLY_MG_QUERY_RE = re.compile(r"^a(\d+)mg:(.+)$")
SELECTOR_ALLY_MG_IDX_RE = re.compile(r"^a(\d+)mg(\d+)$")
SELECTOR_ALLY_M_QUERY_RE = re.compile(r"^a(\d+)m:(.+)$")
SELECTOR_ALLY_M_IDX_RE = re.compile(r"^a(\d+)m(\d+)$")
SELECTOR_ALLY_IDX_RE = re.compile(r"^a(\d+)$")
SELECTOR_ALLY_QUERY_RE = re.compile(r"^a:(.+)$")
SELECTOR_MG_QUERY_RE = re.compile(r"^mg:(.+)$")
SELECTOR_MG_IDX_RE = re.compile(r"^mg(\d+)$")
SELECTOR_EG_QUERY_RE = re.compile(r"^eg:(.+)$")
SELECTOR_EG_IDX_RE = re.compile(r"^eg(\d+)$")
SELECTOR_PREFIX_QUERY_RE = re.compile(r"^(ex|dc|dr|h|m|e):(.+)$")
SELECTOR_PREFIX_IDX_RE = re.compile(r"^(ex|dc|dr|h|m|e)(\d+)$")
SELECTOR_OWN_P_IDX_RE = re.compile(r"^p(\d+)$")

PREFIX_SCOPE_MAP = {
    "ex": "exhaust",
    "dc": "discard",
    "dr": "draw",
    "h": "hand",
    "m": "own_minion",
    "e": "enemy",
}

PILE_ATTR_MAP = {
    "hand": "hand",
    "exhaust": "exhaust_pile",
    "discard": "discard_pile",
    "draw": "draw_pile",
}

GRAVEYARD_SCOPES = {"minion_graveyard", "enemy_graveyard", "ally_minion_graveyard"}
PILE_SCOPES = {"hand", "exhaust", "discard", "draw"}
GRID_SCOPES = {"enemy", "own_minion", "ally_minion", "ally_player"}


@dataclass
class ParsedSelector:
    scope: str
    ally_slot: Optional[int] = None
    index: Optional[int] = None
    query: Optional[str] = None
    raw: str = ""


@dataclass
class SelectionStepSpec:
    step_id: str
    kind: str
    min_count: int = 1
    max_count: int = 1
    required: bool = True
    auto_single: bool = True
    allow_simple_auto: bool = False
    exclude_playing_card: bool = False
    filter_fn: Optional[Callable[[Any, Any, Any], bool]] = None
    prompt_key: str = "i18n_cli_core.select_prompt_default"
    continue_key: str = "i18n_cli_core.select_continue_default"
    error_key: str = "i18n_cli_core.select_required_default"
    invalid_index_key: str = "i18n_cli_core.select_invalid_index_default"
    empty_key: str = "i18n_cli_core.select_empty_default"


class TargetSelectorParser:
    @staticmethod
    def split_tokens(raw_target: Optional[str]) -> list[str]:
        if raw_target is None:
            return []
        text = str(raw_target).strip()
        if not text:
            return []
        normalized = text.replace("，", " ").replace(",", " ")
        return [part.strip() for part in normalized.split() if part.strip()]

    @staticmethod
    def parse_token(token: str) -> ParsedSelector:
        raw = str(token or "").strip()
        lowered = raw.lower()
        if not lowered:
            return ParsedSelector(scope="auto", raw=raw)
        if m := SELECTOR_ALLY_MG_QUERY_RE.match(lowered):
            return ParsedSelector("ally_minion_graveyard", ally_slot=int(m.group(1)), query=raw[raw.index(":") + 1:].strip(), raw=raw)
        if m := SELECTOR_ALLY_MG_IDX_RE.match(lowered):
            return ParsedSelector("ally_minion_graveyard", ally_slot=int(m.group(1)), index=int(m.group(2)), raw=raw)
        if m := SELECTOR_ALLY_M_QUERY_RE.match(lowered):
            return ParsedSelector("ally_minion", ally_slot=int(m.group(1)), query=raw[raw.index(":") + 1:].strip(), raw=raw)
        if m := SELECTOR_ALLY_M_IDX_RE.match(lowered):
            return ParsedSelector("ally_minion", ally_slot=int(m.group(1)), index=int(m.group(2)), raw=raw)
        if m := SELECTOR_ALLY_IDX_RE.match(lowered):
            return ParsedSelector("ally_player", ally_slot=int(m.group(1)), index=int(m.group(1)), raw=raw)
        if m := SELECTOR_ALLY_QUERY_RE.match(lowered):
            return ParsedSelector("ally_player", query=raw[raw.index(":") + 1:].strip(), raw=raw)
        if m := SELECTOR_MG_QUERY_RE.match(lowered):
            return ParsedSelector("minion_graveyard", query=raw[raw.index(":") + 1:].strip(), raw=raw)
        if m := SELECTOR_MG_IDX_RE.match(lowered):
            return ParsedSelector("minion_graveyard", index=int(m.group(1)), raw=raw)
        if m := SELECTOR_EG_QUERY_RE.match(lowered):
            return ParsedSelector("enemy_graveyard", query=raw[raw.index(":") + 1:].strip(), raw=raw)
        if m := SELECTOR_EG_IDX_RE.match(lowered):
            return ParsedSelector("enemy_graveyard", index=int(m.group(1)), raw=raw)
        if m := SELECTOR_PREFIX_QUERY_RE.match(lowered):
            return ParsedSelector(PREFIX_SCOPE_MAP[m.group(1)], query=raw[raw.index(":") + 1:].strip(), raw=raw)
        if m := SELECTOR_PREFIX_IDX_RE.match(lowered):
            return ParsedSelector(PREFIX_SCOPE_MAP[m.group(1)], index=int(m.group(2)), raw=raw)
        if lowered in ("p0", "p", "self"):
            return ParsedSelector("self", index=0, raw=raw)
        if m := SELECTOR_OWN_P_IDX_RE.match(lowered):
            return ParsedSelector("own_minion", index=int(m.group(1)), raw=raw)
        if lowered.isdigit():
            return ParsedSelector("auto", index=int(lowered), raw=raw)
        return ParsedSelector("auto", query=raw, raw=raw)

    @staticmethod
    def is_explicit_selector(token: str) -> bool:
        raw = str(token or "").strip()
        if not raw:
            return False
        parsed = TargetSelectorParser.parse_token(raw)
        if parsed.scope != "auto":
            return True
        return parsed.index is not None or ":" in raw

    @staticmethod
    def build_candidates(
        run,
        step_spec: SelectionStepSpec,
        hand_idx: Optional[int] = None,
        shuffle_draw: bool = True,
    ) -> list[dict]:
        kind = step_spec.kind
        if kind in PILE_ATTR_MAP:
            return TargetSelectorParser._build_pile_candidates(
                run,
                kind,
                step_spec.filter_fn,
                exclude_hand_idx=hand_idx if (kind == "hand" and step_spec.exclude_playing_card) else None,
                shuffle_draw=shuffle_draw,
            )
        if kind in GRAVEYARD_SCOPES:
            return TargetSelectorParser._build_graveyard_candidates(run, kind, step_spec.filter_fn)
        return TargetSelectorParser._build_entity_candidates(run, kind, step_spec.filter_fn)

    @staticmethod
    def _build_pile_candidates(
        run,
        scope: str,
        filter_fn: Optional[Callable[[Any, Any, Any], bool]],
        exclude_hand_idx: Optional[int] = None,
        shuffle_draw: bool = True,
    ) -> list[dict]:
        p = run.player
        pile = getattr(p, PILE_ATTR_MAP[scope], []) or []
        from ...entities import ALL_CARDS
        candidates = []
        for idx, raw_c in enumerate(pile):
            if exclude_hand_idx is not None and idx == exclude_hand_idx - 1:
                continue
            c_state = ensure_card_state(raw_c)
            card_obj = ALL_CARDS.get(c_state)
            if filter_fn is not None and not filter_fn(c_state, card_obj, run):
                continue
            name = card_obj.name if card_obj else c_state.id
            candidates.append({
                "uid": f"{scope}:0:{idx}:{c_state.id}",
                "value": f"{scope}:{idx}",
                "label": name,
                "match_name": name,
                "scope": scope,
                "source_idx": idx,
                "ally_slot": None,
                "card_id": c_state.id,
                "upgraded": bool(c_state.upgraded),
                "gems": list(c_state.gems or []),
            })
        if scope == "draw" and shuffle_draw and len(candidates) > 1:
            random.shuffle(candidates)
        return candidates

    @staticmethod
    def _build_graveyard_candidates(
        run,
        scope: str,
        filter_fn: Optional[Callable[[Any, Any, Any], bool]],
    ) -> list[dict]:
        candidates = []
        if scope == "minion_graveyard":
            for idx, mid in enumerate(getattr(run.player, "minion_graveyard", []) or []):
                name = MINION_CONFIG.get(mid, {}).get("name", mid)
                if filter_fn is not None and not filter_fn(mid, name, run):
                    continue
                candidates.append({
                    "uid": f"minion_graveyard:0:{idx}:{mid}",
                    "value": f"mg:{idx}",
                    "label": get_locale_text("i18n_cli_core.select_label_graveyard", name=name),
                    "match_name": name,
                    "scope": "minion_graveyard",
                    "source_idx": idx,
                    "ally_slot": None,
                    "entry_id": mid,
                })
        elif scope == "enemy_graveyard":
            for idx, ename in enumerate(getattr(run.player, "enemy_graveyard", []) or []):
                if filter_fn is not None and not filter_fn(ename, ename, run):
                    continue
                candidates.append({
                    "uid": f"enemy_graveyard:0:{idx}:{ename}",
                    "value": f"eg:{idx}",
                    "label": get_locale_text("i18n_cli_core.select_label_graveyard", name=ename),
                    "match_name": str(ename),
                    "scope": "enemy_graveyard",
                    "source_idx": idx,
                    "ally_slot": None,
                    "entry_id": ename,
                })
        elif scope == "ally_minion_graveyard":
            party_order = list(getattr(run, "party_order", []) or [])
            players_map = getattr(run, "players", {}) or {}
            for slot, uid in enumerate(party_order, 1):
                ally_p = players_map.get(uid)
                if ally_p is None:
                    continue
                for idx, mid in enumerate(getattr(ally_p, "minion_graveyard", []) or []):
                    name = MINION_CONFIG.get(mid, {}).get("name", mid)
                    if filter_fn is not None and not filter_fn(mid, (slot, ally_p, name), run):
                        continue
                    candidates.append({
                        "uid": f"ally_minion_graveyard:{slot}:{idx}:{mid}",
                        "value": f"a{slot}mg:{idx}",
                        "label": get_locale_text("i18n_cli_core.select_label_ally_minion", ally_name=ally_p.name, name=name, grid=idx + 1),
                        "match_name": name,
                        "scope": "ally_minion_graveyard",
                        "source_idx": idx,
                        "ally_slot": slot,
                        "entry_id": mid,
                    })
        return candidates

    @staticmethod
    def _build_entity_candidates(
        run,
        kind: str,
        filter_fn: Optional[Callable[[Any, Any, Any], bool]],
    ) -> list[dict]:
        candidates: list[dict] = []
        p = run.player
        my_uid = run.uid_for(p)
        party_order = list(getattr(run, "party_order", []) or [])
        players_map = getattr(run, "players", {}) or {}

        def _append_if(cand: dict, obj: Any, ctx_obj: Any = None) -> None:
            if filter_fn is not None and not filter_fn(cand, obj, ctx_obj or run):
                return
            candidates.append(cand)

        if kind in ("enemy", "any_other"):
            for idx, enemy in enumerate(run.enemies, 1):
                if enemy.hp <= 0:
                    continue
                _append_if({
                    "uid": f"enemy:0:{idx}",
                    "value": f"e{idx}",
                    "label": get_locale_text("i18n_cli_core.select_label_enemy", name=enemy.name, hp=enemy.hp, max_hp=enemy.max_hp),
                    "match_name": enemy.name,
                    "scope": "enemy",
                    "source_idx": idx,
                    "ally_slot": None,
                }, enemy)

        if kind in ("self", "self_and_allies"):
            _append_if({
                "uid": "self:0:0",
                "value": "p0",
                "label": get_locale_text("i18n_cli_core.select_label_self", name=p.name),
                "match_name": p.name,
                "scope": "self",
                "source_idx": 0,
                "ally_slot": None,
            }, p)

        if kind in ("own_minion", "self_and_allies", "any_other", "ally_or_minion"):
            for grid in sorted(p.minions.keys(), key=lambda g: int(g) if str(g).isdigit() else 999):
                m = p.minions[grid]
                _append_if({
                    "uid": f"own_minion:0:{grid}",
                    "value": f"p{grid}",
                    "label": get_locale_text("i18n_cli_core.select_label_own_minion", name=m.name, grid=grid),
                    "match_name": m.name,
                    "scope": "own_minion",
                    "source_idx": str(grid),
                    "ally_slot": None,
                }, m)

        if kind in ("ally_player", "ally_minion", "ally_any", "self_and_allies", "any_other", "ally_or_minion"):
            for slot, uid in enumerate(party_order, 1):
                ally_p = players_map.get(uid)
                if ally_p is None or ally_p.downed or ally_p.hp <= 0:
                    continue
                is_self = uid == my_uid
                if kind in ("ally_player", "ally_any", "self_and_allies", "any_other", "ally_or_minion"):
                    if not is_self or kind == "ally_any":
                        _append_if({
                            "uid": f"ally_player:{slot}:{slot}",
                            "value": f"a{slot}",
                            "label": get_locale_text("i18n_cli_core.select_label_ally_player", name=ally_p.name),
                            "match_name": ally_p.name,
                            "scope": "ally_player",
                            "source_idx": slot,
                            "ally_slot": slot,
                        }, ally_p)
                if kind in ("ally_minion", "ally_any", "self_and_allies", "any_other", "ally_or_minion"):
                    if not is_self or kind == "ally_any":
                        for grid in sorted(ally_p.minions.keys(), key=lambda g: int(g) if str(g).isdigit() else 999):
                            m = ally_p.minions[grid]
                            _append_if({
                                "uid": f"ally_minion:{slot}:{grid}",
                                "value": f"a{slot}m{grid}",
                                "label": get_locale_text("i18n_cli_core.select_label_ally_minion", ally_name=ally_p.name, name=m.name, grid=grid),
                                "match_name": m.name,
                                "scope": "ally_minion",
                                "source_idx": str(grid),
                                "ally_slot": slot,
                            }, m)

        return candidates

    @staticmethod
    def resolve_token(
        candidates: list[dict],
        token: str,
        selected_uids: Optional[set[str]] = None,
    ) -> Optional[dict]:
        used = selected_uids or set()
        remaining = [c for c in candidates if c["uid"] not in used]
        if not remaining:
            return None
        parsed = TargetSelectorParser.parse_token(token)
        if parsed.scope == "self":
            for cand in remaining:
                if cand["scope"] == "self":
                    return cand
            return None

        if parsed.scope == "auto":
            if parsed.index is not None:
                idx = parsed.index - 1
                if 0 <= idx < len(remaining):
                    return remaining[idx]
                return None
            if parsed.query:
                from ..cli.base.pinyin_match import find_candidate_index_by_query
                idx = find_candidate_index_by_query(remaining, lambda c: c.get("match_name", ""), parsed.query)
                return remaining[idx] if idx is not None else None
            return None

        scoped = [c for c in remaining if TargetSelectorParser._scope_matches(c, parsed)]
        if not scoped:
            return None

        if parsed.scope in GRID_SCOPES:
            if parsed.scope == "ally_player" and parsed.ally_slot is not None:
                for cand in scoped:
                    if cand.get("ally_slot") == parsed.ally_slot:
                        return cand
                return None
            if parsed.index is not None:
                target_key = str(parsed.index)
                for cand in scoped:
                    if str(cand.get("source_idx")) == target_key:
                        return cand
                return None
            if parsed.query:
                from ..cli.base.pinyin_match import find_candidate_index_by_query
                idx = find_candidate_index_by_query(scoped, lambda c: c.get("match_name", ""), parsed.query)
                return scoped[idx] if idx is not None else None
            return None

        if parsed.index is not None:
            idx = parsed.index - 1
            if 0 <= idx < len(scoped):
                return scoped[idx]
            return None
        if parsed.query:
            from ..cli.base.pinyin_match import find_candidate_index_by_query
            idx = find_candidate_index_by_query(scoped, lambda c: c.get("match_name", ""), parsed.query)
            return scoped[idx] if idx is not None else None
        return None

    @staticmethod
    def _scope_matches(cand: dict, parsed: ParsedSelector) -> bool:
        if cand["scope"] != parsed.scope:
            return False
        if parsed.ally_slot is not None and cand.get("ally_slot") != parsed.ally_slot:
            return False
        return True

    @staticmethod
    def resolve_simple_target(
        run,
        target: Optional[str],
        *,
        is_self_spell: bool = False,
        is_coop_card: bool = False,
        is_any_other: bool = False,
        engine=None,
    ) -> tuple[Optional[str], Optional[str]]:
        if target is None:
            return None, None
        raw = str(target).strip()
        if not raw:
            return None, None
        parsed = TargetSelectorParser.parse_token(raw)

        if parsed.scope == "auto" and parsed.index is not None:
            idx_val = 1 if parsed.index == 0 else parsed.index
            return f"e{idx_val}", None

        if parsed.scope == "self":
            return "p0", None

        if parsed.scope == "enemy":
            if parsed.index is not None:
                idx_val = 1 if parsed.index == 0 else parsed.index
                return f"e{idx_val}", None
            if parsed.query:
                cands = TargetSelectorParser._build_entity_candidates(run, "enemy", None)
                matched = TargetSelectorParser.resolve_token(cands, raw)
                if matched:
                    return matched["value"], None
                return None, get_locale_text("i18n_battle_core.invalid_target")

        if parsed.scope == "own_minion":
            if parsed.index is not None:
                return f"p{parsed.index}", None
            if parsed.query:
                cands = TargetSelectorParser._build_entity_candidates(run, "own_minion", None)
                matched = TargetSelectorParser.resolve_token(cands, raw)
                if matched:
                    return matched["value"], None
                return None, get_locale_text("i18n_battle_core.invalid_target")

        if parsed.scope in ("ally_player", "ally_minion"):
            if parsed.ally_slot is not None:
                if parsed.scope == "ally_minion" and parsed.index is not None:
                    return f"a{parsed.ally_slot}m{parsed.index}", None
                if parsed.scope == "ally_minion" and parsed.query:
                    cands = TargetSelectorParser._build_entity_candidates(run, "ally_any", None)
                    matched = TargetSelectorParser.resolve_token(cands, raw)
                    if matched:
                        return matched["value"], None
                    return None, get_locale_text("i18n_battle_misc.coop_ally_not_found", target=raw)
                return f"a{parsed.ally_slot}", None
            if parsed.query:
                cands = TargetSelectorParser._build_entity_candidates(run, "ally_player", None)
                matched = TargetSelectorParser.resolve_token(cands, raw)
                if matched:
                    return matched["value"], None
                return None, get_locale_text("i18n_battle_misc.coop_ally_not_found", target=raw)

        if parsed.scope == "auto" and parsed.query:
            allowed_kind = "any_other" if is_any_other else ("ally_or_minion" if is_coop_card else ("self_and_allies" if is_self_spell else "enemy"))
            cands = TargetSelectorParser._build_entity_candidates(run, allowed_kind, None)
            matched = TargetSelectorParser.resolve_token(cands, raw)
            if matched:
                return matched["value"], None
            return None, get_locale_text("i18n_battle_core.invalid_target")

        return raw, None


def pop_selected_pile_cards(pile: list, selected: list[dict]) -> list:
    matched_indices: list[int] = []
    used_indices: set[int] = set()
    for cand in selected:
        src_idx = cand.get("source_idx")
        card_id = cand.get("card_id")
        upgraded = bool(cand.get("upgraded", False))
        gems = list(cand.get("gems", []) or [])
        chosen_idx = None
        if isinstance(src_idx, int) and 0 <= src_idx < len(pile) and src_idx not in used_indices:
            st = ensure_card_state(pile[src_idx])
            if st.id == card_id and bool(st.upgraded) == upgraded and list(st.gems or []) == gems:
                chosen_idx = src_idx
        if chosen_idx is None:
            for i, raw_c in enumerate(pile):
                if i in used_indices:
                    continue
                st = ensure_card_state(raw_c)
                if st.id == card_id and bool(st.upgraded) == upgraded and list(st.gems or []) == gems:
                    chosen_idx = i
                    break
        if chosen_idx is not None:
            used_indices.add(chosen_idx)
            matched_indices.append(chosen_idx)
    items_by_idx = {idx: pile[idx] for idx in matched_indices}
    for idx in sorted(matched_indices, reverse=True):
        pile.pop(idx)
    return [items_by_idx[idx] for idx in matched_indices]
