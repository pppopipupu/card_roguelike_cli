from ...models.events import CardPlayedCountEvent
from ...models.state import ensure_card_state


class InstantSummonHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(CardPlayedCountEvent, self.on_card_played_count)

    def on_card_played_count(self, event):
        run = event.run
        p = run.player
        marked = run.node_data.setdefault("instant_summon_counts", [])
        if event.count in marked:
            return
        from ...entities import ALL_CARDS
        found_state = None
        found_pile = None
        found_index = -1
        found_card = None
        found_id = ""
        for pile in (p.discard_pile, p.draw_pile):
            for idx, c_state in enumerate(pile):
                card_id = ensure_card_state(c_state).id
                card = ALL_CARDS.get(card_id)
                if card and getattr(card, "instant_summon", False) and event.count in getattr(card, "instant_summon_thresholds", ()):
                    found_state = c_state
                    found_pile = pile
                    found_index = idx
                    found_card = card
                    found_id = card_id
                    break
            if found_state is not None:
                break
        if found_state is None:
            return
        if self.engine._get_free_grid(p) is None:
            self.engine._log_event(run, f"🏹 [瞬念召唤] 第 {event.count} 张牌结算时，战场已满，【{found_card.name}】无法跃入战场。")
            return
        found_pile.pop(found_index)
        grid = self.engine._summon_minion(
            run,
            found_id,
            found_card.name,
            getattr(found_card, "minion_hp", 0),
            getattr(found_card, "minion_atk", 0),
            0,
        )
        if not grid:
            found_pile.insert(found_index, found_state)
            self.engine._log_event(run, f"🏹 [瞬念召唤] 第 {event.count} 张牌结算时，召唤失败。")
            return
        marked.append(event.count)
        pile_name = "弃牌堆" if found_pile is p.discard_pile else "抽牌堆"
        self.engine._log_event(run, f"🏹 [瞬念召唤] 第 {event.count} 张牌结算，【{found_card.name}】从{pile_name}跃入格子 [{grid}]！")
