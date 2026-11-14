from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

from ...data.item_lore_data import ITEM_LORE
from ...data.locale_data import get_locale_text
from .bag_service import get_item_display_name, get_item_weight, is_item_carryover, resolve_item_query


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
    weight: int
    carry_tag: str
    version: LoreVersion
    intro: str
    detail: str


REVEAL_RULES: Dict[str, Callable[[LoreContext], bool]] = {}


def register_reveal(name: str):
    def decorator(fn):
        REVEAL_RULES[name] = fn
        return fn
    return decorator


@register_reveal("always")
def _reveal_always(ctx: LoreContext) -> bool:
    return True


@register_reveal("killed_yog")
def _reveal_killed_yog(ctx: LoreContext) -> bool:
    return bool(ctx.stats and getattr(ctx.stats, "yog_sothoth_kill_count", 0) > 0)


@register_reveal("secret_clue_found")
def _reveal_secret_clue(ctx: LoreContext) -> bool:
    run = ctx.run
    fm = getattr(run, "floor_map", None) if run is not None else None
    return bool(fm and getattr(fm, "secret_clue_found", False))


def _is_revealed(rule_name: str, ctx: LoreContext) -> bool:
    rule = REVEAL_RULES.get(rule_name)
    return bool(rule and rule(ctx))


class ItemLoreStateMachine:
    def __init__(self, stats=None, run=None):
        self.stats = stats
        self.run = run

    def _initial(self, cfg, ctx):
        hidden = cfg.get("hidden")
        if hidden and not _is_revealed(hidden, ctx):
            return LoreVersion.HIDDEN
        if not cfg.get("secret"):
            return LoreVersion.FULL
        return LoreVersion.PARTIAL

    def _advance(self, state, cfg, ctx):
        if state is LoreVersion.PARTIAL and _is_revealed(cfg["secret"]["reveal"], ctx):
            return LoreVersion.FULL
        return state

    def resolve(self, item_id: str) -> Optional[LoreView]:
        cfg = ITEM_LORE.get(item_id)
        if not cfg:
            return None
        ctx = LoreContext(self.stats, self.run, item_id)
        state = self._advance(self._initial(cfg, ctx), cfg, ctx)
        carry_key = "i18n_room_interact.bag.carry_yes" if is_item_carryover(item_id) else "i18n_room_interact.bag.carry_no"
        base = dict(
            item_id=item_id,
            name=get_item_display_name(item_id),
            weight=get_item_weight(item_id),
            carry_tag=get_locale_text(carry_key),
        )
        if state is LoreVersion.HIDDEN:
            return LoreView(**base, version=state, intro="", detail=get_locale_text("i18n_item_lore.hidden_placeholder"))
        intro = get_locale_text(cfg["intro_key"])
        secret = cfg.get("secret")
        if not secret:
            return LoreView(**base, version=state, intro=intro, detail="")
        key = secret["reveal_key"] if state is LoreVersion.FULL else secret["hint_key"]
        return LoreView(**base, version=state, intro=intro, detail=get_locale_text(key))


def query_item_lore(query: str, stats=None, run=None):
    item_id = resolve_item_query(query, list(ITEM_LORE))
    if not item_id:
        return None
    view = ItemLoreStateMachine(stats, run).resolve(item_id)
    return (item_id, view) if view else None
