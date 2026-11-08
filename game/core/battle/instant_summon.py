from ...models.events import CardPlayedCountEvent
from ...models.state import ensure_card_state


class InstantSummonHandler:
    PILE_ORDER = (
        ("draw", "抽牌堆", "draw_pile"),
        ("discard", "弃牌堆", "discard_pile"),
        ("hand", "手牌", "hand"),
        ("exhaust", "消耗堆", "exhaust_pile"),
    )

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(CardPlayedCountEvent, self.on_card_played_count)

    def _condition_met(self, card, count):
        return (
            getattr(card, "type", "") == "minion"
            and getattr(card, "instant_summon", False)
            and count in getattr(card, "instant_summon_thresholds", ())
        )

    def on_card_played_count(self, event):
        run = event.run
        p = run.player
        from ...entities import ALL_CARDS
        candidates = []
        for source, pile_name, pile_attr in self.PILE_ORDER:
            pile = getattr(p, pile_attr)
            for c_state in pile:
                card_id = ensure_card_state(c_state).id
                card = ALL_CARDS.get(card_id)
                if not card or not self._condition_met(card, event.count):
                    continue
                if source not in getattr(card, "instant_summon_piles", ()):
                    continue
                candidates.append((pile_name, pile, c_state, card, card_id))
        for pile_name, pile, c_state, card, card_id in candidates:
            if self.engine._get_free_grid(p) is None:
                self.engine._log_event(run, f"✨ [瞬念召唤] 第 {event.count} 张牌结算时，战场已满，【{card.name}】无法跃入战场。")
                break
            index = next((i for i, value in enumerate(pile) if value is c_state), None)
            if index is None:
                try:
                    index = pile.index(c_state)
                except ValueError:
                    continue
            pile.pop(index)
            grid = self.engine._summon_minion(
                run,
                card_id,
                card.name,
                getattr(card, "minion_hp", 0),
                getattr(card, "minion_atk", 0),
                0,
            )
            if not grid:
                pile.insert(index, c_state)
                self.engine._log_event(run, f"✨ [瞬念召唤] 第 {event.count} 张牌结算时，【{card.name}】召唤失败。")
                continue
            self.engine._log_event(run, f"✨ [瞬念召唤] 第 {event.count} 张牌结算，【{card.name}】从{pile_name}跃入格子 [{grid}]！")
