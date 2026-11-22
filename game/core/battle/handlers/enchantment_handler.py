from ....models.events import DamageCalculateEvent, ShieldGainEvent, HealEvent, BeforeDamageApplyEvent, TurnStartEvent, TurnEndEvent
from ..event_bus import PRIORITY_MODIFIER_ADD, PRIORITY_SYSTEM_PRE
from ..enchantment_runtime import (
    apply_enchantment_dmg,
    apply_enchantment_shield,
    apply_enchantment_heal,
    apply_enchantment_turn_start,
    apply_enchantment_turn_end,
    enchantment_pierces,
)


class EnchantmentTriggerHandler:
    """将附魔数值修饰与穿透护盾效果接入标准伤害流程。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate, PRIORITY_MODIFIER_ADD)
        event_bus.subscribe(ShieldGainEvent, self.on_shield_gain, PRIORITY_MODIFIER_ADD)
        event_bus.subscribe(HealEvent, self.on_heal, PRIORITY_MODIFIER_ADD)
        event_bus.subscribe(BeforeDamageApplyEvent, self.on_before_damage_apply)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start, PRIORITY_SYSTEM_PRE)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end, PRIORITY_SYSTEM_PRE)

    @staticmethod
    def _playing_card(run):
        cid = run.node_data.get("current_playing_card_cid")
        if not cid:
            return None
        from ....entities.cards import ALL_CARDS
        return ALL_CARDS.get(cid)

    def on_damage_calculate(self, event):
        source = event.source
        player_source = (
            source in ("p0", "player", "effect")
            or source.startswith("player:")
            or (len(source) > 1 and source[0] in ("p", "a") and source[1:].isdigit())
        )
        if not player_source:
            return
        card = event.card or self._playing_card(event.run)
        if card is None or not getattr(card, "enchantments", None):
            return
        event.modified_damage, _ = apply_enchantment_dmg(event.run, card, event.target, event.modified_damage)

    def on_shield_gain(self, event):
        if event.target != "p0":
            return
        card = self._playing_card(event.run)
        if card is None or not getattr(card, "enchantments", None):
            return
        event.modified_amount = apply_enchantment_shield(event.run, card, event.modified_amount)

    def on_heal(self, event):
        if event.target != "p0" and not event.target.startswith("p"):
            return
        card = self._playing_card(event.run)
        if card is None or not getattr(card, "enchantments", None):
            return
        event.amount = apply_enchantment_heal(card, event.amount)

    def on_before_damage_apply(self, event):
        card = event.card or self._playing_card(event.run)
        if card is not None and enchantment_pierces(card):
            event.pierce_shield = True

    def on_turn_start(self, event):
        if not event.is_player:
            return
        apply_enchantment_turn_start(self.engine, event.run, event.run.player)

    def on_turn_end(self, event):
        if not event.is_player:
            return
        apply_enchantment_turn_end(event.run, event.run.player)
