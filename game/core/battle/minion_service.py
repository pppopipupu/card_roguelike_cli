import random

from ...models.state import GameRun
from ...data.text.locale_data import get_locale_text


def recall_dead_minion(resolver, run: GameRun, hp_limit: int) -> str:
        p = run.player
        from ...entities.cards.base import ALL_CARDS
        eligible = []
        for cid in p.minion_graveyard:
            card = ALL_CARDS.get(cid)
            if card and card.type == "minion":
                hp_val = getattr(card, "minion_hp", 999)
                if hp_val < hp_limit:
                    eligible.append(cid)
        if not eligible:
            return get_locale_text("i18n_battle_misc.recall_no_eligible")
        chosen_cid = random.choice(eligible)
        p.minion_graveyard.remove(chosen_cid)
        card = ALL_CARDS[chosen_cid]
        hp_val = getattr(card, "minion_hp", 10)
        atk_val = getattr(card, "minion_atk", 1)
        grid = resolver.summon_minion(run, chosen_cid, card.name, hp_val, atk_val, 0)
        if grid:
            return get_locale_text("i18n_battle_misc.recall_success", name=card.name, grid=grid)
        return get_locale_text("i18n_battle_misc.recall_battlefield_full")
