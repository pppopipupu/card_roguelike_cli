from ....models.events import (
    CardCostCalculateEvent,
    CardDrawnEvent,
    CardEffectResolvedEvent,
    CardExhaustEvent,
    CardPlayCheckEvent,
    CardPlayEvent,
    CardPostPlayEvent,
    DamageCalculateEvent,
    DamageTakeEvent,
    ShieldDecayCalculateEvent,
    ShieldGainEvent,
    HealEvent,
    BeforeDamageApplyEvent,
    TurnStartEvent,
    TurnEndEvent,
)
from ..event_bus import PRIORITY_MODIFIER_ADD, PRIORITY_SYSTEM_PRE
from ..enchantment_runtime import (
    apply_enchantment_dmg,
    apply_enchantment_shield,
    apply_enchantment_heal,
    apply_enchantment_post_play,
    apply_enchantment_turn_start,
    apply_enchantment_turn_end,
    check_enchantment_playable,
    enchantment_pierces,
)
from ..enchantment_runtime_hooks import (
    apply_enchantment_cost_calc,
    apply_enchantment_incoming_dmg_extra,
    apply_enchantment_on_damage_take,
    apply_enchantment_on_draw,
    apply_enchantment_on_exhaust,
    should_prevent_shield_decay,
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
        event_bus.subscribe(CardPlayCheckEvent, self.on_card_play_check)
        event_bus.subscribe(CardPostPlayEvent, self.on_card_post_play)
        event_bus.subscribe(CardCostCalculateEvent, self.on_card_cost_calculate, PRIORITY_MODIFIER_ADD)
        event_bus.subscribe(CardDrawnEvent, self.on_card_drawn)
        event_bus.subscribe(CardExhaustEvent, self.on_card_exhaust)
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(ShieldDecayCalculateEvent, self.on_shield_decay_calculate)
        event_bus.subscribe(CardPlayEvent, self.on_card_play)
        event_bus.subscribe(CardEffectResolvedEvent, self.on_card_effect_resolved)

    @staticmethod
    def _playing_card(run):
        cid = run.node_data.get("current_playing_card_cid")
        if not cid:
            return None
        from ....entities.cards import ALL_CARDS
        return ALL_CARDS.get(cid)

    def on_card_play_check(self, event):
        error = check_enchantment_playable(event.run, event.card)
        if error:
            event.cancelled = True
            event.error_message = error

    def on_card_post_play(self, event):
        apply_enchantment_post_play(
            self.engine,
            event.run,
            event.run.player,
            event.card,
            event.card_state,
            event.target or "",
            event.prev_alive_enemies,
        )

    def on_damage_calculate(self, event):
        source = event.source
        player_source = (
            source in ("p0", "player", "effect")
            or source.startswith("player:")
            or (len(source) > 1 and source[0] in ("p", "a") and source[1:].isdigit())
        )
        if not player_source:
            event.modified_damage = apply_enchantment_incoming_dmg_extra(event.run, event.target, event.modified_damage)
            return
        card = event.card or self._playing_card(event.run)
        if card is None:
            return
        event.modified_damage, _ = apply_enchantment_dmg(event.run, card, event.target, event.modified_damage, event.damage_type)

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
        apply_enchantment_turn_end(event.run, event.run.player, self.engine)

    def on_card_cost_calculate(self, event):
        event.cost_a = apply_enchantment_cost_calc(event.run, event.player, event.card, event.card_state, event.cost_a)

    def on_card_drawn(self, event):
        if event.intercepted:
            return
        if apply_enchantment_on_draw(self.engine, event.run, event.player, event.card_state, event.card):
            event.intercepted = True

    def on_card_exhaust(self, event):
        apply_enchantment_on_exhaust(self.engine, event.run, event.run.player, event.card)

    def on_damage_take(self, event):
        apply_enchantment_on_damage_take(self.engine, event.run, event.source, event.target, event.amount)

    def on_shield_decay_calculate(self, event):
        if event.target != "p0":
            return
        if should_prevent_shield_decay(event.run, event.run.player):
            event.cancel()

    def on_card_play(self, event):
        if "x_cost" in (getattr(event.card, "enchantments", None) or ()):
            event.run.node_data["enchant_x_repeat_left"] = max(0, int(event.cost_a or 0) - 1)

    def on_card_effect_resolved(self, event):
        left = int(event.run.node_data.pop("enchant_x_repeat_left", 0) or 0)
        if left <= 0 or "x_cost" not in (getattr(event.card, "enchantments", None) or ()):
            return
        if event.run.node_data.get("enchant_x_repeating"):
            return
        event.run.node_data["enchant_x_repeating"] = True
        try:
            for _ in range(left):
                if not any(e.hp > 0 for e in event.run.enemies):
                    break
                event.card.execute(event.run, event.target, self.engine)
        finally:
            event.run.node_data["enchant_x_repeating"] = False
