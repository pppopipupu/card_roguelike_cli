from .base import BuffImpl
from .registry import register_buff
from ...data.locale_data import get_locale_text

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
    pass
