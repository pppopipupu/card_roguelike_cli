from ....models.events import (
    CardPlayedEvent, DamageTakeEvent, MinionSummonEvent,
    DamageCalculateEvent, TurnStartEvent, TurnEndAfterHandEvent,
)
from ...text.events import locale_text


class AmuletTriggerHandler:
    """将战斗事件转发给玩家护符模板。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(MinionSummonEvent, self.on_minion_summon)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(TurnEndAfterHandEvent, self.on_after_hand)

    def on_turn_start(self, event):
        if event.is_player:
            return
        from ....entities.amulets.amulets import ALL_AMULETS
        for ak, av in list(event.run.player.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template and hasattr(template, "on_enemy_turn_start"):
                msg = template.on_enemy_turn_start(event.run, ak, self.engine)
                if msg:
                    self.engine._log_event(event.run, msg)

    def on_after_hand(self, event):
        from ....entities.amulets.amulets import ALL_AMULETS
        run = event.run
        player = event.player
        for ak, av in list(player.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template:
                template.on_end_turn(run, ak, self.engine)
            if player.amulets.get(ak) is not av:
                continue
            av.countdown -= 1
            if av.countdown > 0:
                continue
            player.amulets.pop(ak, None)
            player.minion_graveyard.append(av.id)
            death_message = ""
            if template:
                death_message = template.on_death(run, ak, av.id.endswith("+"), self.engine)
            if death_message:
                self.engine._log_event(run, locale_text(
                    "i18n_battle_core.amulet_requiem_death_log",
                    params={"name": av.name, "effect": death_message},
                ))
            else:
                self.engine._log_event(run, locale_text(
                    "i18n_battle_core.amulet_requiem_log",
                    params={"name": av.name},
                ))

    def on_card_played(self, event):
        from ....entities.amulets.amulets import ALL_AMULETS
        for ak, av in list(event.run.player.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template:
                if event.card.type == "spell" and hasattr(template, "on_spell_played"):
                    template.on_spell_played(event.run, ak, event.card, self.engine)
                if hasattr(template, "on_card_played"):
                    template.on_card_played(event.run, ak, event, self.engine)

    def on_damage_take(self, event):
        from ....entities.amulets.amulets import ALL_AMULETS
        if event.target != "p0" or event.amount <= 0:
            return
        run = event.run
        if getattr(run, "_amulet_damage_trigger_active", False):
            return
        run._amulet_damage_trigger_active = True
        try:
            for ak, av in list(run.player.amulets.items()):
                if run.player.amulets.get(ak) is not av:
                    continue
                base_id = av.id[:-1] if av.id.endswith("+") else av.id
                template = ALL_AMULETS.get(base_id)
                if template and hasattr(template, "on_take_damage"):
                    msg = template.on_take_damage(run, ak, event.source, event.amount, self.engine)
                    if msg:
                        self.engine._log_event(run, msg)
        finally:
            run._amulet_damage_trigger_active = False

    def on_minion_summon(self, event):
        from ....entities.amulets.amulets import ALL_AMULETS
        for ak, av in list(event.run.player.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template and hasattr(template, "on_minion_summon"):
                template.on_minion_summon(event.run, ak, event, self.engine)

    def on_damage_calculate(self, event):
        from ....entities.amulets.amulets import ALL_AMULETS
        for ak, av in list(event.run.player.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template and hasattr(template, "on_damage_calculate"):
                template.on_damage_calculate(event.run, ak, event, self.engine)
