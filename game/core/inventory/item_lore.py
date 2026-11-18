from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from ...data.item_lore_data import ITEM_LORE
from ...data.locale_data import get_locale_text
from ..progress.progressive_unlock import LORE_ITEM_ACHIEVEMENT_RULES, is_lore_rule_unlocked
from .bag_service import get_item_display_name, get_item_weight, is_item_carryover, resolve_item_query

REVEAL_RULES = LORE_ITEM_ACHIEVEMENT_RULES


class LoreVersion(Enum):
    HIDDEN = "hidden"
    PARTIAL = "partial"
    FULL = "full"


@dataclass
class LoreContext:
    stats: Any
    run: Any
    item_id: str


@dataclass
class LoreView:
    item_id: str
    name: str
    weight: float
    carry_tag: str
    version: LoreVersion
    intro: str
    detail: str


class ItemLoreStateMachine:
    def __init__(self, stats=None, run=None):
        self.stats = stats
        self.run = run

    def _initial(self, cfg, ctx: LoreContext):
        hidden = cfg.get("hidden")
        if hidden and not is_lore_rule_unlocked(hidden, ctx.stats):
            return LoreVersion.HIDDEN
        if not cfg.get("secret"):
            return LoreVersion.FULL
        return LoreVersion.PARTIAL

    def _advance(self, state, cfg, ctx: LoreContext):
        if state is LoreVersion.PARTIAL and is_lore_rule_unlocked(cfg["secret"]["reveal"], ctx.stats):
            return LoreVersion.FULL
        return state

    def resolve(self, item_id: str) -> Optional[LoreView]:
        cfg = ITEM_LORE.get(item_id)
        if not cfg:
            return None
        ctx = LoreContext(self.stats, self.run, item_id)
        require_seen = cfg.get("require_seen")
        if require_seen and not is_lore_rule_unlocked(require_seen, ctx.stats):
            return None
        state = self._advance(self._initial(cfg, ctx), cfg, ctx)
        carry_key = "i18n_room_interact.bag.carry_yes" if is_item_carryover(item_id) else "i18n_room_interact.bag.carry_no"
        name = get_item_display_name(item_id)
        weight = get_item_weight(item_id)
        carry_tag = get_locale_text(carry_key)
        if state is LoreVersion.HIDDEN:
            return LoreView(
                item_id=item_id,
                name=name,
                weight=weight,
                carry_tag=carry_tag,
                version=state,
                intro="",
                detail=get_locale_text("i18n_item_lore.hidden_placeholder"),
            )
        intro = get_locale_text(cfg["intro_key"])
        secret = cfg.get("secret")
        if not secret:
            return LoreView(item_id=item_id, name=name, weight=weight, carry_tag=carry_tag, version=state, intro=intro, detail="")
        key = secret["reveal_key"] if state is LoreVersion.FULL else secret["hint_key"]
        return LoreView(item_id=item_id, name=name, weight=weight, carry_tag=carry_tag, version=state, intro=intro, detail=get_locale_text(key))


def query_item_lore(query: str, stats=None, run=None):
    item_id = resolve_item_query(query, list(ITEM_LORE))
    if not item_id:
        return None
    view = ItemLoreStateMachine(stats, run).resolve(item_id)
    return (item_id, view) if view else None
