from .base import BuffImpl
from .registry import register_buff


@register_buff("coop_aegis")
class CoopAegisBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.run.node_data.get("coop_damage_aoe"):
            return
        if event.target != "p0":
            return
        event.modified_damage = int(event.modified_damage * 0.75)


@register_buff("coop_soul_resonance")
class CoopSoulResonanceBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if event.source != "p0" or entity != event.run.player:
            return
        card = event.card
        if card is None or getattr(card, "type", "") not in ("attack", "spell"):
            return
        bonus = buff_state.stacks2 if buff_state.stacks2 else 4
        event.modified_damage += bonus
        heal_amount = 3 if bonus >= 6 else 2
        source_uid = getattr(buff_state, "source_uid", "")
        source = event.run.players.get(source_uid) if source_uid else None
        if source is not None and source.hp > 0:
            source.hp = min(source.max_hp, source.hp + heal_amount)
            event.engine._log_event(
                event.run,
                f"🔗 [灵魂共鸣] 【{entity.name}】的攻击触发共鸣，为【{source.name}】恢复 {heal_amount} 点生命。",
            )
        buff_state.stacks -= 1
        if buff_state.stacks <= 0:
            if buff_state in entity.buffs:
                entity.buffs.remove(buff_state)
