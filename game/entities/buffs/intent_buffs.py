from .base import BuffImpl
from .registry import register_buff
from ...data.text.locale_data import get_locale_text

@register_buff("drain_ba")
class DrainBABuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player:
            entity.bonus_actions = max(0, entity.bonus_actions - buff_state.stacks)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.drain_ba_log", stacks=buff_state.stacks))
            if buff_state in entity.buffs:
                entity.buffs.remove(buff_state)

@register_buff("drain_a")
class DrainABuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player:
            entity.actions = max(0, entity.actions - buff_state.stacks)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.drain_a_log", stacks=buff_state.stacks))
            if buff_state in entity.buffs:
                entity.buffs.remove(buff_state)

@register_buff("discard_next_turn")
class DiscardNextTurnBuff(BuffImpl):
    def on_turn_start_after_draw(self, event, buff_state, entity):
        import random
        from ..cards.base import ALL_CARDS
        p = entity
        count = buff_state.stacks
        discarded_names = []
        for _ in range(count):
            if p.hand:
                discarded = p.hand.pop(random.randint(0, len(p.hand) - 1))
                card_name = ALL_CARDS[discarded].name if discarded in ALL_CARDS else get_locale_text("i18n_battle_core.unknown_card")
                discarded_names.append(f"【{card_name}】")
                event.engine._discard_card(event.run, discarded)
        if buff_state in p.buffs:
            p.buffs.remove(buff_state)
        if discarded_names:
            event.engine._log_event(event.run, get_locale_text(
                "i18n_battle_core.discard_start_turn_log",
                cards=", ".join(discarded_names),
            ))
