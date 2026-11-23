import random
from typing import List
from ....inventory.deck_service import DeckService
from ....inventory.enchantment_service import (
    get_enchantment_name,
    is_card_enchantable,
    roll_enchantments,
)
from ....text.events import TextNode, locale_text
from .effects import register_dialog_effect


@register_dialog_effect("enchant_random_card")
def _eff_enchant_random_card(eff: dict, ctx: dict, outcomes: List[TextNode]):
    from .....entities import ALL_CARDS

    p = ctx["player"]
    eligible = [c for c in (getattr(p, "deck", None) or ()) if is_card_enchantable(c)]
    if not eligible:
        fkey = eff.get("fallback_key")
        if fkey:
            outcomes.append(locale_text(str(fkey)))
        return
    target = random.choice(eligible)
    before_name = ALL_CARDS[target].name
    eid = str(eff.get("enchant_id", "") or "")
    if not eid:
        pool = tuple(eff["pool"]) if eff.get("pool") else None
        rolled = roll_enchantments(1, pool=pool)
        if not rolled:
            return
        eid = rolled[0]
    new_state = DeckService.clone_state(target)
    new_state.enchantments = list(new_state.enchantments or []) + [eid]
    p.deck.remove(target)
    p.deck.append(new_state)
    after_name = ALL_CARDS[new_state].name
    ench_name = get_enchantment_name(eid)
    key = eff.get("key")
    if key:
        outcomes.append(
            locale_text(
                str(key),
                params={
                    "before": before_name,
                    "after": after_name,
                    "enchant": ench_name,
                },
            )
        )


@register_dialog_effect("remove_random_curse")
def _eff_remove_random_curse(eff: dict, ctx: dict, outcomes: List[TextNode]):
    from .....entities import ALL_CARDS

    p = ctx["player"]
    curses = [c for c in (getattr(p, "deck", None) or ()) if getattr(ALL_CARDS.get(c), "color", "") == "curse"]
    if not curses:
        fkey = eff.get("fallback_key")
        if fkey:
            outcomes.append(locale_text(str(fkey)))
        return
    target = random.choice(curses)
    cname = ALL_CARDS[target].name
    p.deck.remove(target)
    key = eff.get("key")
    if key:
        outcomes.append(locale_text(str(key), params={"card": cname}))
