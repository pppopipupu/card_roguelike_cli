from ....data.text.locale_data import get_locale_text
from ....models.events import CardPlayedEvent, TurnEndEvent
from ....entities.cards.ninja_base import change_lex_kela, has_ninja_tag


class NinjaEventHandler:
    """承接蕾忍的全局出牌记账与职业回合被动，卡牌自身效果由卡牌钩子处理。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end)

    def on_card_played(self, event):
        run = event.run
        p = run.player
        card = event.card
        if card is None or p is None:
            return
        if getattr(card, "science", False):
            if int(getattr(p, "lex_kela", 0) or 0) > 0:
                change_lex_kela(self.engine, run, p, -1, reason="science", source_card_id=card.id)
                self.engine._log_event(run, get_locale_text("i18n_cards_ninja.science_spend", current=p.lex_kela))
        if has_ninja_tag(card, "blade"):
            run.node_data["ninja_blades_played"] = int(run.node_data.get("ninja_blades_played", 0) or 0) + 1
        run.node_data["ninja_last_was_ninjutsu"] = has_ninja_tag(card, "ninjutsu")
        run.node_data["ninja_prev_played_card_id"] = run.node_data.get("ninja_last_played_card_id", "")
        if card.id != "ninja_mobius_loop_snake":
            run.node_data["ninja_last_played_card_id"] = card.id
        if any(
            st.id == "ninja_mosquito_hand"
            for pile in (p.hand, p.draw_pile, p.discard_pile)
            for st in pile
        ):
            self.engine._log_event(run, get_locale_text("i18n_cards_ninja.mosquito_buzz"))

    def on_turn_end(self, event):
        if not event.is_player:
            return
        run = event.run
        p = run.player
        if p is None or getattr(p, "selected_class", "") != "蕾忍":
            return
        spent_key = run.turn_key("lex_kela_spent_this_turn", p)
        if run.node_data.get(spent_key, False):
            return
        gained = change_lex_kela(self.engine, run, p, 1, reason="turn_end")
        if gained > 0:
            self.engine._log_event(run, get_locale_text("i18n_cards_ninja.lex_turn_end", current=p.lex_kela))
