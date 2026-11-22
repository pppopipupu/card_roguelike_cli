from typing import Optional

from ....data.text.locale_data import get_locale_text
from .candidates import CandidateBuilderMixin
from .spec import (
    GRID_SCOPES,
    PREFIX_SCOPE_MAP,
    SELECTOR_ALLY_IDX_RE,
    SELECTOR_ALLY_MG_IDX_RE,
    SELECTOR_ALLY_MG_QUERY_RE,
    SELECTOR_ALLY_M_IDX_RE,
    SELECTOR_ALLY_M_QUERY_RE,
    SELECTOR_ALLY_QUERY_RE,
    SELECTOR_EG_IDX_RE,
    SELECTOR_EG_QUERY_RE,
    SELECTOR_MG_IDX_RE,
    SELECTOR_MG_QUERY_RE,
    SELECTOR_OWN_P_IDX_RE,
    SELECTOR_PREFIX_IDX_RE,
    SELECTOR_PREFIX_QUERY_RE,
    ParsedSelector,
)


class TargetSelectorParser(CandidateBuilderMixin):
    @staticmethod
    def _match_query(candidates: list[dict], query: str) -> int | None:
        from ...cli.base.pinyin_match import find_candidate_index_by_query
        idx = find_candidate_index_by_query(candidates, lambda c: c.get("match_name", ""), query)
        if idx is not None:
            return idx
        for index, cand in enumerate(candidates):
            if any(find_candidate_index_by_query([cand], lambda c: alias, query) is not None for alias in cand.get("aliases", [])):
                return index
        return None

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
                idx = TargetSelectorParser._match_query(remaining, parsed.query)
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
                idx = TargetSelectorParser._match_query(scoped, parsed.query)
                return scoped[idx] if idx is not None else None
            return None

        if parsed.index is not None:
            idx = parsed.index - 1
            if 0 <= idx < len(scoped):
                return scoped[idx]
            return None
        if parsed.query:
            from ...cli.base.pinyin_match import find_candidate_index_by_query
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
