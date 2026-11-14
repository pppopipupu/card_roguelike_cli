from ...data.locale_data import get_locale_text
from ...data.millika_card_config import (
    MILLIKA_CARD_ID,
    MILLIKA_FANFARE_CONFIG,
    MILLIKA_MINION_CONFIG,
    MILLIKA_REPLENISH_CONFIG,
    MILLIKA_TURN_FLAG_KEY,
)
from ...models.events import CardVanishEvent, MinionSummonEvent, TurnEndEvent, TurnStartEvent
from ..inventory.deck_service import DeckService
from .vanish import count_cards_in_piles, vanish_cards


def _base_card_id(state):
    return str(state.id).split(":")[0].rstrip("+")


class MillikaCardHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(MinionSummonEvent, self.on_minion_summon)
        event_bus.subscribe(CardVanishEvent, self.on_cards_vanished)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end)

    def on_turn_start(self, event):
        flags = event.run.node_data.setdefault(MILLIKA_TURN_FLAG_KEY, {})
        if not event.is_player:
            flags.clear()
            return
        flags[event.run.uid_for(event.run.player)] = True

    def on_turn_end(self, event):
        flags = event.run.node_data.setdefault(MILLIKA_TURN_FLAG_KEY, {})
        if not event.is_player:
            flags.clear()
            return
        flags[event.run.uid_for(event.run.player)] = False

    @staticmethod
    def _is_own_turn(run, uid):
        flags = run.node_data.get(MILLIKA_TURN_FLAG_KEY)
        if flags is None:
            return True
        return bool(flags.get(uid, False))

    def on_minion_summon(self, event):
        if _base_card_id(event.minion_state) != MILLIKA_CARD_ID:
            return
        self._apply_ward(event)
        self._apply_fanfare(event)

    def _apply_ward(self, event):
        if not MILLIKA_MINION_CONFIG["ward"]:
            return
        self.engine._add_buff_to(
            event.minion_state,
            "ward",
            get_locale_text("i18n_minions.common.ward_name"),
            get_locale_text("i18n_minions.common.ward_desc"),
        )

    def _apply_fanfare(self, event):
        run = event.run
        cfg = MILLIKA_FANFARE_CONFIG
        total = count_cards_in_piles(run)
        if total >= cfg["pile_count_threshold"]:
            vanished = vanish_cards(run, cfg["vanish_count"], self.engine)
            if vanished:
                joiner = get_locale_text("i18n_cards_millika.names_joiner")
                self.engine._log_event(run, get_locale_text("i18n_cards_millika.fanfare_vanish", name=event.minion_state.name, cards=joiner.join(vanished), pile=total, threshold=cfg["pile_count_threshold"]))
            else:
                self.engine._log_event(run, get_locale_text("i18n_cards_millika.fanfare_vanish_empty", name=event.minion_state.name))
            return
        m = event.minion_state
        m.max_hp += cfg["buff_hp"]
        m.hp += cfg["buff_hp"]
        m.atk += cfg["buff_atk"]
        self.engine._log_event(run, get_locale_text("i18n_cards_millika.fanfare_buff", name=m.name, pile=total, threshold=cfg["pile_count_threshold"], hp=cfg["buff_hp"], atk=cfg["buff_atk"]))

    def on_cards_vanished(self, event):
        run = event.run
        uid = run.uid_for(run.player)
        if not self._is_own_turn(run, uid):
            return
        count = sum(1 for state in event.card_states if _base_card_id(state) == MILLIKA_CARD_ID)
        if count <= 0:
            return
        copies = count * MILLIKA_REPLENISH_CONFIG["copies_per_vanish"]
        for _ in range(copies):
            DeckService.add_card_to_hand(run.player, MILLIKA_CARD_ID)
        from ...entities.cards.base import ALL_CARDS
        name = ALL_CARDS[MILLIKA_CARD_ID].name
        self.engine._log_event(run, get_locale_text("i18n_cards_millika.replenish", name=name, count=copies))
