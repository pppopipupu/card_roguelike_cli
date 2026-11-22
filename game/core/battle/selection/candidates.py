import random
from typing import Any, Callable, Optional

from ....data.entities.minions.minion_data import MINION_CONFIG
from ....data.text.locale_data import get_locale_text
from ....models.state import ensure_card_state
from .spec import GRAVEYARD_SCOPES, PILE_ATTR_MAP, SelectionStepSpec


class CandidateBuilderMixin:
    @staticmethod
    def build_candidates(
        run,
        step_spec: SelectionStepSpec,
        hand_idx: Optional[int] = None,
        shuffle_draw: bool = True,
    ) -> list[dict]:
        kind = step_spec.kind
        if kind == "option":
            return [dict(item) for item in (step_spec.options or [])]
        if kind == "generated_card":
            pool = list(step_spec.card_pool_fn(run)) if step_spec.card_pool_fn is not None else []
            if len(pool) > step_spec.sample_count:
                pool = random.sample(pool, step_spec.sample_count)
            from ....entities import ALL_CARDS
            candidates = []
            for idx, raw_card in enumerate(pool):
                c_state = ensure_card_state(raw_card)
                card_obj = ALL_CARDS.get(c_state)
                name = card_obj.name if card_obj else c_state.id
                candidates.append({
                    "uid": f"generated_card:0:{idx}:{c_state.id}",
                    "value": f"generated:{idx}",
                    "label": name,
                    "match_name": name,
                    "scope": "generated_card",
                    "source_idx": idx,
                    "ally_slot": None,
                    "card_id": c_state.id,
                    "upgraded": bool(c_state.upgraded),
                    "gems": list(c_state.gems or []),
                })
            return candidates
        if kind in PILE_ATTR_MAP:
            return CandidateBuilderMixin._build_pile_candidates(
                run,
                kind,
                step_spec.filter_fn,
                exclude_hand_idx=hand_idx if (kind == "hand" and step_spec.exclude_playing_card) else None,
                shuffle_draw=shuffle_draw,
            )
        if kind in GRAVEYARD_SCOPES:
            return CandidateBuilderMixin._build_graveyard_candidates(run, kind, step_spec.filter_fn)
        return CandidateBuilderMixin._build_entity_candidates(run, kind, step_spec.filter_fn)

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
        from ....entities import ALL_CARDS
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
