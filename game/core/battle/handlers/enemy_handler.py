from ....models.events import (
    EnemyBeforeDeathEvent, CardPlayEvent, TurnStartEvent, TurnEndEvent,
    BattleStartEvent, CardPlayedEvent, DamageTakeEvent, DamageCalculateEvent,
    CardExhaustEvent, MinionDeathEvent, EnemyRollIntentEvent,
)


class EnemyTriggerHandler:
    """将战斗事件转发给敌人模板，模板可在此拦截或改写结算。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(EnemyBeforeDeathEvent, self.on_enemy_before_death)
        event_bus.subscribe(CardPlayEvent, self.on_card_play)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end)
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(CardExhaustEvent, self.on_card_exhaust)
        event_bus.subscribe(MinionDeathEvent, self.on_minion_death)
        event_bus.subscribe(EnemyRollIntentEvent, self.on_enemy_roll_intent)

    def _templates(self, event):
        from ....entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template is not None:
                yield enemy, template

    def on_enemy_before_death(self, event):
        from ....entities import get_enemy_template
        template = get_enemy_template(event.enemy.name)
        if template and hasattr(template, "on_enemy_before_death"):
            template.on_enemy_before_death(event.run, event.enemy, event, self.engine)

    def on_card_play(self, event):
        for enemy, template in self._templates(event):
            if hasattr(template, "on_card_play"):
                template.on_card_play(event, enemy, self.engine)

    def on_turn_start(self, event):
        for enemy, template in self._templates(event):
            if hasattr(template, "on_turn_start"):
                template.on_turn_start(event, enemy, self.engine)

    def on_turn_end(self, event):
        for enemy, template in self._templates(event):
            if hasattr(template, "on_turn_end"):
                template.on_turn_end(event, enemy, self.engine)

    def on_battle_start(self, event):
        for enemy, template in self._templates(event):
            if hasattr(template, "on_battle_start") and not getattr(enemy, "_battle_init_done", False):
                enemy._battle_init_done = True
                template.on_battle_start(event.run, enemy, self.engine)

    def on_card_played(self, event):
        for enemy, template in self._templates(event):
            if hasattr(template, "on_card_played"):
                template.on_card_played(event, enemy, self.engine)

    def on_damage_take(self, event):
        for enemy, template in self._templates(event):
            if hasattr(template, "on_damage_take"):
                template.on_damage_take(event, enemy, self.engine)

    def on_damage_calculate(self, event):
        for enemy, template in self._templates(event):
            if hasattr(template, "on_damage_calculate"):
                template.on_damage_calculate(event, enemy, self.engine)

    def on_card_exhaust(self, event):
        for enemy, template in self._templates(event):
            if hasattr(template, "on_card_exhaust"):
                template.on_card_exhaust(event, enemy, self.engine)

    def on_minion_death(self, event):
        for enemy, template in self._templates(event):
            if hasattr(template, "on_minion_death"):
                template.on_minion_death(event, enemy, self.engine)

    def on_enemy_roll_intent(self, event):
        from ....entities import get_enemy_template
        template = get_enemy_template(event.enemy.name)
        if template and hasattr(template, "on_enemy_roll_intent"):
            template.on_enemy_roll_intent(event, event.enemy, self.engine)
