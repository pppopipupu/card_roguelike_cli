from ....models.events import (
    CardExhaustEvent, CardDrawnEvent, CardDiscardEvent, CardPlayedEvent,
    TurnStartEvent, TurnEndEvent, CardCostCalculateEvent, CardTurnEndResolveEvent,
)


class CardTriggerHandler:
    """将战斗事件转发到手牌、抽牌堆与消耗堆中卡牌的被动钩子。

    卡牌类通过覆写 ``on_draw`` / ``on_discard`` / ``on_exhaust`` 等钩子
    声明被动效果，无需在核心出牌逻辑里判断具体卡牌 ID。
    """

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(CardExhaustEvent, self.on_card_exhaust)
        event_bus.subscribe(CardDrawnEvent, self.on_card_drawn)
        event_bus.subscribe(CardDiscardEvent, self.on_card_discard)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end)
        event_bus.subscribe(CardCostCalculateEvent, self.on_card_cost_calculate)
        event_bus.subscribe(CardTurnEndResolveEvent, self.on_card_turn_end_resolve)

    @staticmethod
    def _card_for(card_state):
        from ....models.state import ensure_card_state
        from ....entities.cards import ALL_CARDS
        state = ensure_card_state(card_state)
        base_id = state.id[:-1] if state.id.endswith("+") else state.id
        return ALL_CARDS.get(base_id), state

    @staticmethod
    def _pile(run, name):
        player = run.player
        return list(getattr(player, name, []) or [])

    def on_card_exhaust(self, event):
        card, state = self._card_for(event.card)
        if card is not None and hasattr(card, "on_exhaust"):
            card.on_exhaust(event, state)
        for pile_name in ("hand", "exhaust_pile"):
            for pile_state in self._pile(event.run, pile_name):
                other, other_state = self._card_for(pile_state)
                if other is None or other is card:
                    continue
                if hasattr(other, "on_other_card_exhaust"):
                    other.on_other_card_exhaust(event, other_state)

    def on_card_drawn(self, event):
        card = event.card
        if card is None:
            card, _ = self._card_for(event.card_state)
        if card is not None and hasattr(card, "on_draw"):
            card.on_draw(event, event.card_state)

    def on_card_discard(self, event):
        card, state = self._card_for(event.card)
        if card is not None and hasattr(card, "on_discard"):
            card.on_discard(event, state)

    def on_card_played(self, event):
        for state in self._pile(event.run, "hand"):
            card, card_state = self._card_for(state)
            if card is not None and card is not event.card and hasattr(card, "on_other_card_played"):
                card.on_other_card_played(event, card_state)

    def on_turn_start(self, event):
        if not event.is_player:
            return
        for state in self._pile(event.run, "hand"):
            card, card_state = self._card_for(state)
            if card is not None and hasattr(card, "on_turn_start_in_hand"):
                card.on_turn_start_in_hand(event, card_state)
        for state in self._pile(event.run, "exhaust_pile"):
            card, card_state = self._card_for(state)
            if card is not None and hasattr(card, "on_turn_start_in_exhaust"):
                card.on_turn_start_in_exhaust(event, card_state)

    def on_turn_end(self, event):
        if not event.is_player:
            return
        for state in self._pile(event.run, "hand"):
            card, card_state = self._card_for(state)
            if card is not None and hasattr(card, "on_turn_end_in_hand"):
                card.on_turn_end_in_hand(event, card_state)

    def on_card_cost_calculate(self, event):
        if hasattr(event.card, "on_cost_calculate"):
            event.card.on_cost_calculate(event, event.card_state)

    def on_card_turn_end_resolve(self, event):
        if event.card is not None and hasattr(event.card, "on_turn_end_resolve"):
            event.card.on_turn_end_resolve(event, event.card_state)
