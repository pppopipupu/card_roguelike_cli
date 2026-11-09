from .base import BuffImpl
from .registry import register_buff
from ...data.buff_data import BUFF_CONFIG
from ...data.locale_data import get_locale_text

def _stat(instance, buff_id, name, default):
    cfg = BUFF_CONFIG.get(buff_id, {})
    return getattr(instance, name, cfg.get(name, default))


@register_buff("coop_aegis")
class CoopAegisBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.run.node_data.get("coop_damage_aoe"):
            return
        if event.target != "p0":
            return
        event.modified_damage = int(event.modified_damage * _stat(self, "coop_aegis", "damage_multiplier", 0.75))


@register_buff("coop_soul_resonance")
class CoopSoulResonanceBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if event.source != "p0" or entity != event.run.player:
            return
        card = event.card
        if card is None or getattr(card, "type", "") not in ("attack", "spell"):
            return
        bonus = buff_state.stacks2 if buff_state.stacks2 else _stat(self, "coop_soul_resonance", "damage_bonus", 4)
        event.modified_damage += bonus
        high_bonus_threshold = _stat(self, "coop_soul_resonance", "high_bonus_threshold", 6)
        heal_amount = _stat(self, "coop_soul_resonance", "high_heal_amount", 3) if bonus >= high_bonus_threshold else _stat(self, "coop_soul_resonance", "heal_amount", 2)
        source_uid = getattr(buff_state, "source_uid", "")
        source = event.run.players.get(source_uid) if source_uid else None
        if source is not None and source.hp > 0:
            if source_uid == event.run.uid_for(event.run.player):
                target_ref = "p0"
            elif source_uid in event.run.party_order:
                target_ref = f"a{event.run.party_order.index(source_uid) + 1}"
            else:
                target_ref = ""
            if target_ref:
                event.engine._heal_target(event.run, target_ref, heal_amount)
            event.engine._log_event(
                event.run,
                get_locale_text("i18n_buffs.coop_soul_resonance_log", entity=entity.name, source=source.name, heal=heal_amount),
            )
        buff_state.stacks -= 1
        if buff_state.stacks <= 0:
            if buff_state in entity.buffs:
                entity.buffs.remove(buff_state)
