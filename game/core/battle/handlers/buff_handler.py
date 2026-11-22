from ....models.events import (
    TurnStartEvent, TurnEndEvent, CardPlayEvent, CardPlayedEvent,
    DamageCalculateEvent, HealEvent, ShieldGainEvent, DamageTakeEvent,
    HealCalculateEvent, EnemySyncIntentsEvent, CardExhaustEvent, BuffGainEvent,
    MinionDeathEvent, BeforeDamageApplyEvent, BattleBeforeWinCleanupEvent,
    BuffAppliedEvent, ShieldDecayCalculateEvent, TurnStartAfterDrawEvent,
    BeforeCardDrawEvent, CardDrawnEvent, CardCostCalculateEvent,
    CardPlayCheckEvent, CardPostPlayRouteEvent, CardEffectResolvedEvent,
    DamageRedirectEvent, PlayerBeforeDeathEvent, EnemyTargetSelectEvent,
    EnemyRollIntentEvent, LexKelaChangedEvent,
)


class BuffTriggerHandler:
    """将标准战斗事件转发给实体身上 Buff 实现的生命周期钩子。

    Buff 可实现 ``hook_priorities`` 映射（钩子名 -> 整数优先级）来声明
    自身顺序，数值越大越先执行；默认 0，同优先级保持挂载顺序。
    """

    def __init__(self, event_bus, engine):
        self.engine = engine
        self._hook_arity = {}
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end)
        event_bus.subscribe(CardPlayEvent, self.on_card_play)
        event_bus.subscribe(CardEffectResolvedEvent, self.on_card_effect_resolved)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(HealEvent, self.on_heal)
        event_bus.subscribe(ShieldGainEvent, self.on_shield_gain)
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(HealCalculateEvent, self.on_heal_calculate)
        event_bus.subscribe(EnemySyncIntentsEvent, self.on_enemy_sync_intents)
        event_bus.subscribe(CardExhaustEvent, self.on_card_exhaust)
        event_bus.subscribe(BuffGainEvent, self.on_buff_gain)
        event_bus.subscribe(MinionDeathEvent, self.on_unit_death)
        event_bus.subscribe(BeforeDamageApplyEvent, self.on_before_damage_apply)
        event_bus.subscribe(BuffAppliedEvent, self.on_buff_applied)
        event_bus.subscribe(ShieldDecayCalculateEvent, self.on_shield_decay_calculate)
        event_bus.subscribe(TurnStartAfterDrawEvent, self.on_turn_start_after_draw)
        event_bus.subscribe(BeforeCardDrawEvent, self.on_before_card_draw)
        event_bus.subscribe(CardDrawnEvent, self.on_card_drawn)
        event_bus.subscribe(CardCostCalculateEvent, self.on_card_cost_calculate)
        event_bus.subscribe(CardPlayCheckEvent, self.on_card_play_check)
        event_bus.subscribe(CardPostPlayRouteEvent, self.on_card_post_play_route)
        event_bus.subscribe(DamageRedirectEvent, self.on_damage_redirect)
        event_bus.subscribe(PlayerBeforeDeathEvent, self.on_player_before_death)
        event_bus.subscribe(EnemyTargetSelectEvent, self.on_enemy_target_select)
        event_bus.subscribe(EnemyRollIntentEvent, self.on_enemy_roll_intent)
        event_bus.subscribe(LexKelaChangedEvent, self.on_lex_kela_changed)
        event_bus.subscribe(BattleBeforeWinCleanupEvent, self.on_battle_before_win_cleanup)

    def _call_hook(self, impl, method_name, event, buff_state, entity):
        import inspect
        key = (type(impl), method_name)
        arity = self._hook_arity.get(key)
        if arity is None:
            method = getattr(impl, method_name)
            try:
                arity = len(inspect.signature(method).parameters)
            except (TypeError, ValueError):
                arity = 3
            self._hook_arity[key] = arity
        method = getattr(impl, method_name)
        if arity >= 4:
            method(event, buff_state, entity, self.engine)
        else:
            method(event, buff_state, entity)

    def _dispatch(self, event, entities, method_name):
        from ....entities.buffs import get_buff_impl
        seen = set()
        for entity in entities:
            if entity is None or id(entity) in seen:
                continue
            seen.add(id(entity))
            entries = []
            for buff_state in list(getattr(entity, "buffs", []) or []):
                impl = get_buff_impl(buff_state.id, buff_state.stacks, getattr(buff_state, "stacks2", None))
                if impl is None or not hasattr(impl, method_name):
                    continue
                priority = int(getattr(impl, "hook_priorities", {}).get(method_name, 0))
                entries.append((priority, buff_state, impl))
            entries.sort(key=lambda item: item[0], reverse=True)
            for _, buff_state, impl in entries:
                self._call_hook(impl, method_name, event, buff_state, entity)

    def _target_entity(self, run, target):
        if target == "p0":
            return run.player
        if target and target.startswith("e"):
            try:
                index = int(target[1:]) - 1
            except ValueError:
                return None
            if 0 <= index < len(run.enemies):
                return run.enemies[index]
        if target and target.startswith("p"):
            grid = target[1:]
            if grid in run.player.minions:
                return run.player.minions[grid]
        return None

    def _source_entity(self, run, source):
        if source in ("p0", "player", "effect") or source.startswith("player:"):
            return run.player
        if source.startswith("p") and len(source) > 1:
            grid = source[1:]
            if grid in run.player.minions:
                return run.player.minions[grid]
        if source.startswith("e"):
            try:
                index = int(source[1:]) - 1
            except ValueError:
                return None
            if 0 <= index < len(run.enemies):
                return run.enemies[index]
        return None

    def _trigger_turn_buffs(self, event, entity, method_name):
        from ....entities.buffs import get_buff_impl
        from ....entities.buffs.base import is_positive_buff
        import copy
        from ....data.entities.buffs.buff_data import BUFF_CONFIG
        internal = {bid for bid, cfg in BUFF_CONFIG.items() if cfg.get("internal")}
        has_refill = any(BUFF_CONFIG.get(b.id, {}).get("infinite_refill") and b.stacks > 0 for b in entity.buffs)
        snapshot = []
        if has_refill:
            snapshot = [(b, int(b.stacks)) for b in entity.buffs if is_positive_buff(b.id) and b.id not in internal and b.stacks > 0]
        entries = []
        for buff_state in list(entity.buffs):
            impl = get_buff_impl(buff_state.id, buff_state.stacks, getattr(buff_state, "stacks2", None))
            if impl and hasattr(impl, method_name):
                priority = int(getattr(impl, "hook_priorities", {}).get(method_name, 0))
                entries.append((priority, buff_state, impl))
        entries.sort(key=lambda item: item[0], reverse=True)
        for _, buff_state, impl in entries:
            self._call_hook(impl, method_name, event, buff_state, entity)
        if not has_refill or not snapshot:
            return
        if entity in event.run.enemies and entity.hp <= 0:
            return
        for old_buff, old_stacks in snapshot:
            existing = next((b for b in entity.buffs if b.id == old_buff.id), None)
            if existing is not None:
                existing.stacks = max(int(existing.stacks), old_stacks)
            else:
                restored = copy.copy(old_buff)
                restored.stacks = old_stacks
                entity.buffs.append(restored)

    def on_turn_start(self, event):
        if event.is_player:
            self._trigger_turn_buffs(event, event.run.player, "on_turn_start")
            return
        for enemy in list(event.run.enemies):
            self._trigger_turn_buffs(event, enemy, "on_turn_start")

    def on_turn_end(self, event):
        if event.is_player:
            self._trigger_turn_buffs(event, event.run.player, "on_turn_end")
            for minion in list(event.run.player.minions.values()):
                self._trigger_turn_buffs(event, minion, "on_turn_end")
            return
        for enemy in list(event.run.enemies):
            self._trigger_turn_buffs(event, enemy, "on_turn_end")
        for player in list(event.run.players.values()):
            self._dispatch(event, [player], "on_enemy_turn_end")

    def on_card_play(self, event):
        self._dispatch(event, [event.run.player], "on_card_play")

    def on_card_effect_resolved(self, event):
        self._dispatch(event, [event.run.player], "on_card_effect_resolved")

    def on_card_played(self, event):
        self._dispatch(event, [event.run.player, *event.run.enemies], "on_card_played")

    def on_damage_calculate(self, event):
        source = event.source
        player_source = (
            source in ("p0", "player", "effect")
            or source.startswith("player:")
            or (len(source) > 1 and source[0] in ("p", "a") and source[1:].isdigit())
        )
        entities = []
        if player_source:
            entities.append(event.run.player)
        entities.append(self._source_entity(event.run, source))
        self._dispatch(event, entities, "on_damage_calculate")
        self._dispatch(event, [self._target_entity(event.run, event.target)], "on_damage_calculate_defend")

    def on_heal(self, event):
        self._dispatch(event, [self._target_entity(event.run, event.target)], "on_heal")

    def on_heal_calculate(self, event):
        self._dispatch(event, [self._target_entity(event.run, event.target)], "on_heal_calculate")

    def on_enemy_sync_intents(self, event):
        self._dispatch(event, [event.enemy], "on_enemy_sync_intents")

    def on_shield_gain(self, event):
        self._dispatch(event, [self._target_entity(event.run, event.target)], "on_shield_gain")

    def on_damage_take(self, event):
        self._dispatch(event, [self._target_entity(event.run, event.target)], "on_damage_take_defend")
        self._dispatch(event, [self._source_entity(event.run, event.source)], "on_damage_take_attack")

    def on_card_exhaust(self, event):
        self._dispatch(event, [event.run.player, *event.run.enemies], "on_card_exhaust")

    def on_buff_gain(self, event):
        self._dispatch(event, [event.entity], "on_buff_gain")

    def on_unit_death(self, event):
        entities = [event.run.player, *event.run.enemies]
        entities.extend(player for player in event.run.players.values() if player is not event.run.player)
        self._dispatch(event, entities, "on_unit_death")

    def on_before_damage_apply(self, event):
        entities = []
        source = event.source
        player_source = (
            source in ("p0", "player", "effect")
            or source.startswith("player:")
            or (len(source) > 1 and source[0] in ("p", "a") and source[1:].isdigit())
        )
        if player_source or event.target == "p0":
            entities.append(event.run.player)
        for index, enemy in enumerate(event.run.enemies, 1):
            if source == f"e{index}" or event.target == f"e{index}":
                entities.append(enemy)
        self._dispatch(event, entities, "on_before_damage_apply")

    def on_buff_applied(self, event):
        self._dispatch(event, [event.entity], "on_buff_applied")

    def on_shield_decay_calculate(self, event):
        self._dispatch(event, [event.entity], "on_shield_decay_calculate")

    def on_turn_start_after_draw(self, event):
        self._dispatch(event, [event.player], "on_turn_start_after_draw")

    def on_before_card_draw(self, event):
        self._dispatch(event, [event.player], "on_before_card_draw")

    def on_card_drawn(self, event):
        self._dispatch(event, [event.player], "on_card_drawn")

    def on_card_cost_calculate(self, event):
        self._dispatch(event, [event.player], "on_card_cost_calculate")

    def on_card_play_check(self, event):
        self._dispatch(event, [event.player], "on_card_play_check")

    def on_card_post_play_route(self, event):
        self._dispatch(event, [event.player], "on_card_post_play_route")

    def on_damage_redirect(self, event):
        entities = [
            event.run.player,
            self._source_entity(event.run, event.source),
            self._target_entity(event.run, event.target),
        ]
        self._dispatch(event, entities, "on_damage_redirect")

    def on_player_before_death(self, event):
        self._dispatch(event, [event.player], "on_player_before_death")

    def on_enemy_target_select(self, event):
        entities = list(event.run.players.values())
        self._dispatch(event, entities, "on_enemy_target_select")

    def on_enemy_roll_intent(self, event):
        self._dispatch(event, [event.enemy], "on_enemy_roll_intent")

    def on_lex_kela_changed(self, event):
        self._dispatch(event, [event.player], "on_lex_kela_changed")

    def on_battle_before_win_cleanup(self, event):
        self._dispatch(event, [event.player], "on_battle_before_win_cleanup")
