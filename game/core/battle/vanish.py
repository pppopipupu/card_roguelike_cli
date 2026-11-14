import random
from ...data.locale_data import get_locale_text
from ...data.anna_card_config import CARD_PILES
from ...models.events import CardVanishEvent


def count_cards_in_piles(run):
    p = run.player
    return sum(len(getattr(p, name, []) or []) for name in CARD_PILES)


def vanish_cards(run, count, engine=None):
    p = run.player
    pool = []
    for pile_name in CARD_PILES:
        pile = getattr(p, pile_name, None) or []
        for state in list(pile):
            pool.append((pile_name, state))
    if not pool or count <= 0:
        return []
    chosen = pool if len(pool) <= count else random.sample(pool, count)
    from ...entities.cards.base import ALL_CARDS
    names = []
    vanished_states = []
    for pile_name, state in chosen:
        pile = getattr(p, pile_name)
        idx = next((i for i, value in enumerate(pile) if value is state), None)
        if idx is None:
            continue
        pile.pop(idx)
        card = ALL_CARDS.get(state)
        names.append(card.name if card is not None else get_locale_text("i18n_cards_anna.unknown_card"))
        vanished_states.append(state)
    if engine is not None and vanished_states:
        engine.event_bus.dispatch(CardVanishEvent(run, vanished_states))
    return names
