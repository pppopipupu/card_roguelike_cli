from ....models.events import (
    MinionDeathEvent, CardPlayedEvent, ShieldGainEvent, DamageTakeEvent,
    CardExhaustEvent, TurnEndEvent, TurnStartEvent, DamageCalculateEvent,
    MinionSummonEvent, CardPlayEvent, MinionSkillUsedEvent,
)


class MinionTriggerHandler:
    """将战斗事件转发给玩家场上随从模板。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(MinionDeathEvent, self.on_minion_death)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(ShieldGainEvent, self.on_shield_gain)
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(CardExhaustEvent, self.on_card_exhaust)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(MinionSummonEvent, self.on_minion_summon)
        event_bus.subscribe(CardPlayEvent, self.on_card_play)
        event_bus.subscribe(MinionSkillUsedEvent, self.on_minion_skill_used)

    def _templates(self, event):
        from ....entities.minions.minions import ALL_MINIONS
        for grid, minion_state in list(event.run.player.minions.items()):
            base_id = minion_state.id.rstrip("+")
            template = ALL_MINIONS.get(base_id)
            if template is not None:
                yield grid, minion_state, template

    def on_card_play(self, event):
        free_cards = event.run.node_data.get("free_minion_cards", [])
        if free_cards:
            matched = None
            if event.card.id in free_cards:
                matched = event.card.id
            elif (event.card.id + "+") in free_cards:
                matched = event.card.id + "+"
            if matched:
                event.cost_a = 0
                event.cost_ba = 0
                try:
                    free_cards.remove(matched)
                except ValueError:
                    pass

    def on_minion_death(self, event):
        for grid, _, template in self._templates(event):
            template.on_minion_death(event.run, grid, event, self.engine)

    def on_card_played(self, event):
        for grid, _, template in self._templates(event):
            template.on_card_played(event.run, grid, event, self.engine)

    def on_shield_gain(self, event):
        for grid, _, template in self._templates(event):
            template.on_shield_gain(event.run, grid, event, self.engine)

    def on_damage_take(self, event):
        for grid, _, template in self._templates(event):
            template.on_damage_take(event.run, grid, event, self.engine)

    def on_card_exhaust(self, event):
        for grid, _, template in self._templates(event):
            template.on_card_exhaust(event.run, grid, event, self.engine)

    def on_turn_end(self, event):
        for grid, _, template in self._templates(event):
            template.on_turn_end(event.run, grid, event, self.engine)

    def on_turn_start(self, event):
        for grid, _, template in self._templates(event):
            template.on_turn_start(event.run, grid, event, self.engine)

    def on_damage_calculate(self, event):
        for grid, _, template in self._templates(event):
            template.on_damage_calculate(event.run, grid, event, self.engine)
            if event.source == f"p{grid}" and getattr(event, "is_attack", False):
                template.on_attack(event.run, grid, event, self.engine)

    def on_minion_summon(self, event):
        from ....entities.minions.minions import ALL_MINIONS
        minion_state = event.minion_state
        template = ALL_MINIONS.get(minion_state.id.rstrip("+"))
        if template:
            template.on_minion_summon(event.run, event.grid, event, self.engine)

    def on_minion_skill_used(self, event):
        from ....entities.minions.minions import ALL_MINIONS
        template = ALL_MINIONS.get(event.minion_state.id.rstrip("+"))
        if template and hasattr(template, "on_minion_skill_used"):
            template.on_minion_skill_used(event.run, event.grid, event, self.engine)
