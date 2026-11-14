from ...data.anna_card_config import (
    ANNE_CARD_ID,
    ANNE_FANFARE_CONFIG,
    ANNE_SPIRIT_CONFIG,
    ANNE_SPIRIT_ID,
)
from ...data.locale_data import get_locale_text
from ...data.minion_data import MINION_CONFIG
from ...models.events import MinionDeathEvent, MinionSummonEvent, TurnStartEvent
from ..inventory.deck_service import DeckService
from .vanish import count_cards_in_piles, vanish_cards


class AnnaCardHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(MinionSummonEvent, self.on_minion_summon)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)

    def on_minion_summon(self, event):
        mid = event.minion_state.id.rstrip("+")
        if mid == ANNE_CARD_ID:
            self._on_anne_summon(event)
        elif mid == ANNE_SPIRIT_ID:
            self._on_spirit_summon(event)

    def _on_anne_summon(self, event):
        run = event.run
        cfg = ANNE_FANFARE_CONFIG
        threshold = cfg["piles_less_than_upgraded"] if event.minion_state.id.endswith("+") else cfg["piles_less_than"]
        total_before = count_cards_in_piles(run)
        vanished = vanish_cards(run, cfg["vanish_count"], self.engine)
        if vanished:
            joiner = get_locale_text("i18n_cards_anna.names_joiner")
            self.engine._log_event(run, get_locale_text("i18n_cards_anna.fanfare", name=event.minion_state.name, cards=joiner.join(vanished)))
        else:
            self.engine._log_event(run, get_locale_text("i18n_cards_anna.fanfare_empty", name=event.minion_state.name))
        if total_before >= threshold:
            return
        from ...entities.cards.base import ALL_CARDS
        spirit_name = MINION_CONFIG[ANNE_SPIRIT_ID]["name"]
        crit_name = ALL_CARDS[cfg["bonus_card_id"]].name
        DeckService.add_card_to_hand(run.player, cfg["bonus_card_id"])
        grid = self.engine._summon_minion(
            run,
            cfg["spirit_minion_id"],
            spirit_name,
            ANNE_SPIRIT_CONFIG["minion_hp"],
            ANNE_SPIRIT_CONFIG["minion_atk"],
            0,
        )
        if grid:
            self.engine._log_event(run, get_locale_text("i18n_cards_anna.spirit_summon", threshold=threshold, spirit=spirit_name, card=crit_name, grid=grid))
        else:
            self.engine._log_event(run, get_locale_text("i18n_cards_anna.spirit_summon_full", threshold=threshold, spirit=spirit_name, card=crit_name))

    def _on_spirit_summon(self, event):
        run = event.run
        m = event.minion_state
        if ANNE_SPIRIT_CONFIG["ward"]:
            self.engine._add_buff_to(m, "ward", get_locale_text("i18n_minions.common.ward_name"), get_locale_text("i18n_minions.common.ward_desc"))
        m.attack_actions += ANNE_SPIRIT_CONFIG["attack_actions_bonus"]
        self.engine._log_event(run, get_locale_text("i18n_cards_anna.spirit_enter", name=m.name, aa=ANNE_SPIRIT_CONFIG["attack_actions_bonus"]))

    def on_turn_start(self, event):
        if not event.is_player or not ANNE_SPIRIT_CONFIG["dies_on_turn_start"]:
            return
        p = event.run.player
        for grid, m in list(p.minions.items()):
            if m.id.rstrip("+") != ANNE_SPIRIT_ID:
                continue
            del p.minions[grid]
            p.minion_graveyard.append(m.id)
            self.engine._reindex_minions(p)
            self.engine._log_event(event.run, get_locale_text("i18n_cards_anna.spirit_death", name=m.name))
            self.engine.event_bus.dispatch(MinionDeathEvent(event.run, m.id, grid, m.name, False))
