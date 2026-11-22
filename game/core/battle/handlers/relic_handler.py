from ....models.events import (
    BattleStartEvent, BattleWinEvent, TurnStartEvent, CardPlayedEvent,
    DamageCalculateEvent, BeforeDamageApplyEvent, MinionSummonEvent,
    ShieldGainEvent, HealEvent, DamageTakeEvent, ShieldDecayEvent,
    TurnEndEvent, MinionDeathEvent, RewardGenerateEvent, CardSelectInitEvent,
    CardObtainEvent, BeforeCardDrawEvent, CardDrawnEvent, CardDiscardEvent,
    HandLimitCalculateEvent, TurnDrawCalculateEvent, BuffAppliedEvent,
    PlayerBeforeDeathEvent, MinionSkillUsedEvent,
)


class RelicTriggerHandler:
    """将标准战斗事件转发给玩家当前持有的遗物实现。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(BattleWinEvent, self.on_battle_win)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(BeforeDamageApplyEvent, self.on_before_damage_apply)
        event_bus.subscribe(MinionSummonEvent, self.on_minion_summon)
        event_bus.subscribe(ShieldGainEvent, self.on_shield_gain)
        event_bus.subscribe(HealEvent, self.on_heal)
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(ShieldDecayEvent, self.on_shield_decay)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end)
        event_bus.subscribe(MinionDeathEvent, self.on_minion_death)
        event_bus.subscribe(RewardGenerateEvent, self.on_reward_generate)
        event_bus.subscribe(CardSelectInitEvent, self.on_card_select_init)
        event_bus.subscribe(CardObtainEvent, self.on_card_obtain)
        event_bus.subscribe(BeforeCardDrawEvent, self.on_before_card_draw)
        event_bus.subscribe(CardDrawnEvent, self.on_card_drawn)
        event_bus.subscribe(CardDiscardEvent, self.on_card_discard)
        event_bus.subscribe(HandLimitCalculateEvent, self.on_hand_limit_calculate)
        event_bus.subscribe(TurnDrawCalculateEvent, self.on_turn_draw_calculate)
        event_bus.subscribe(BuffAppliedEvent, self.on_buff_applied)
        event_bus.subscribe(PlayerBeforeDeathEvent, self.on_player_before_death)
        event_bus.subscribe(MinionSkillUsedEvent, self.on_minion_skill_used)

    def _impls(self, run):
        from ....entities.relics import get_relic_impl
        for relic_id in list(run.player.relics):
            impl = get_relic_impl(relic_id)
            if impl is not None:
                yield impl

    def on_battle_start(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_battle_start"):
                impl.on_battle_start(event.run, self.engine)

    def on_battle_win(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_battle_win"):
                impl.on_battle_win(event.run, self.engine)

    def on_turn_start(self, event):
        if event.is_player:
            event.run.node_data["player_damaged_this_turn"] = False
            for impl in self._impls(event.run):
                if hasattr(impl, "on_turn_start"):
                    impl.on_turn_start(event, event.run, self.engine)

    def on_card_played(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_card_played"):
                impl.on_card_played(event, event.run, self.engine)

    def on_damage_calculate(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_damage_calculate"):
                impl.on_damage_calculate(event, event.run, self.engine)

    def on_before_damage_apply(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_before_damage_apply"):
                impl.on_before_damage_apply(event, event.run, self.engine)

    def on_minion_summon(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_minion_summon"):
                impl.on_minion_summon(event, event.run, self.engine)

    def on_shield_gain(self, event):
        if event.target != "p0":
            return
        for impl in self._impls(event.run):
            if hasattr(impl, "on_shield_gain"):
                impl.on_shield_gain(event, event.run, self.engine)

    def on_heal(self, event):
        if event.target != "p0":
            return
        for impl in self._impls(event.run):
            if hasattr(impl, "on_heal"):
                impl.on_heal(event, event.run, self.engine)

    def on_damage_take(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_damage_take"):
                impl.on_damage_take(event, event.run, self.engine)

    def on_shield_decay(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_shield_decay"):
                impl.on_shield_decay(event, event.run, self.engine)

    def on_turn_end(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_turn_end"):
                impl.on_turn_end(event, event.run, self.engine)

    def on_minion_death(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_minion_death"):
                impl.on_minion_death(event, event.run, self.engine)

    def on_reward_generate(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_reward_generate"):
                impl.on_reward_generate(event, event.run, self.engine)

    def on_card_select_init(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_card_select_init"):
                impl.on_card_select_init(event, event.run, self.engine)

    def on_card_obtain(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_card_obtain"):
                impl.on_card_obtain(event, event.run, self.engine)

    def on_before_card_draw(self, event):
        from ....entities.relics.base import RelicImpl
        for impl in self._impls(event.run):
            overridden = type(impl).on_before_card_draw is not RelicImpl.on_before_card_draw
            if overridden:
                impl.on_before_card_draw(event, event.run, self.engine)
            elif getattr(impl, "blocks_in_turn_draw", False) and not event.is_turn_start:
                event.cancel()
                impl.on_draw_blocked(event.run, self.engine)

    def on_card_drawn(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_card_drawn"):
                impl.on_card_drawn(event, event.run, self.engine)

    def on_card_discard(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_card_discard"):
                impl.on_card_discard(event, event.run, self.engine)

    def on_hand_limit_calculate(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_hand_limit_calculate"):
                impl.on_hand_limit_calculate(event, event.run, self.engine)

    def on_turn_draw_calculate(self, event):
        from ....entities.relics.base import RelicImpl
        for impl in self._impls(event.run):
            overridden = type(impl).on_turn_draw_calculate is not RelicImpl.on_turn_draw_calculate
            if overridden:
                impl.on_turn_draw_calculate(event, event.run, self.engine)
            elif event.is_initial:
                event.draw_count = impl.modify_initial_draw(event.run, event.draw_count, self.engine)
            else:
                event.draw_count = impl.modify_turn_draw(event.run, event.draw_count, self.engine)

    def on_buff_applied(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_buff_applied"):
                impl.on_buff_applied(event, event.run, self.engine)

    def on_player_before_death(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_player_before_death"):
                impl.on_player_before_death(event, event.run, self.engine)

    def on_minion_skill_used(self, event):
        for impl in self._impls(event.run):
            if hasattr(impl, "on_minion_skill_used"):
                impl.on_minion_skill_used(event, event.run, self.engine)
