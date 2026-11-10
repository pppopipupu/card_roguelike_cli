from ...models.events import (
    BattleStartEvent, BattleWinEvent, TurnStartEvent, TurnEndEvent,
    CardPlayEvent, CardPlayedEvent, DamageCalculateEvent, DamageTakeEvent,
    HealEvent, MinionSummonEvent, ShieldGainEvent, ShieldDecayEvent,
    MinionDeathEvent, CardExhaustEvent, HealCalculateEvent, EnemyBeforeDeathEvent,
    EnemySyncIntentsEvent, RewardGenerateEvent, CardSelectInitEvent, CardObtainEvent
)
from ...data.locale_data import get_locale_text
from ...models.stats_tracker import StatsTracker

class RelicTriggerHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(BattleWinEvent, self.on_battle_win)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
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

    def on_battle_start(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_battle_start"):
                impl.on_battle_start(event.run, self.engine)

    def on_battle_win(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_battle_win"):
                impl.on_battle_win(event.run, self.engine)

    def on_turn_start(self, event):
        from ...entities.relics import get_relic_impl
        if event.is_player:
            event.run.node_data["player_damaged_this_turn"] = False
            for r in list(event.run.player.relics):
                impl = get_relic_impl(r)
                if impl and hasattr(impl, "on_turn_start"):
                    impl.on_turn_start(event, event.run, self.engine)

    def on_card_played(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_card_played"):
                impl.on_card_played(event, event.run, self.engine)

    def on_damage_calculate(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_damage_calculate"):
                impl.on_damage_calculate(event, event.run, self.engine)

    def on_minion_summon(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_minion_summon"):
                impl.on_minion_summon(event, event.run, self.engine)

    def on_shield_gain(self, event):
        from ...entities.relics import get_relic_impl
        if event.target == "p0":
            for r in list(event.run.player.relics):
                impl = get_relic_impl(r)
                if impl and hasattr(impl, "on_shield_gain"):
                    impl.on_shield_gain(event, event.run, self.engine)

    def on_heal(self, event):
        from ...entities.relics import get_relic_impl
        if event.target == "p0":
            for r in list(event.run.player.relics):
                impl = get_relic_impl(r)
                if impl and hasattr(impl, "on_heal"):
                    impl.on_heal(event, event.run, self.engine)

    def on_damage_take(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_damage_take"):
                impl.on_damage_take(event, event.run, self.engine)

    def on_shield_decay(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_shield_decay"):
                impl.on_shield_decay(event, event.run, self.engine)

    def on_turn_end(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_turn_end"):
                impl.on_turn_end(event, event.run, self.engine)

    def on_minion_death(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_minion_death"):
                impl.on_minion_death(event, event.run, self.engine)

    def on_reward_generate(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_reward_generate"):
                impl.on_reward_generate(event, event.run, self.engine)

    def on_card_select_init(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_card_select_init"):
                impl.on_card_select_init(event, event.run, self.engine)

    def on_card_obtain(self, event):
        from ...entities.relics import get_relic_impl
        for r in list(event.run.player.relics):
            impl = get_relic_impl(r)
            if impl and hasattr(impl, "on_card_obtain"):
                impl.on_card_obtain(event, event.run, self.engine)

class BuffTriggerHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end)
        event_bus.subscribe(CardPlayEvent, self.on_card_play)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(HealEvent, self.on_heal)
        event_bus.subscribe(ShieldGainEvent, self.on_shield_gain)
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(HealCalculateEvent, self.on_heal_calculate)
        event_bus.subscribe(EnemySyncIntentsEvent, self.on_enemy_sync_intents)
        event_bus.subscribe(CardExhaustEvent, self.on_card_exhaust)

    def _trigger_turn_buffs(self, event, entity, method_name):
        from ...entities.buffs import get_buff_impl
        for b in list(entity.buffs):
            impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
            if impl and hasattr(impl, method_name):
                getattr(impl, method_name)(event, b, entity)

    def on_turn_start(self, event):
        if event.is_player:
            self._trigger_turn_buffs(event, event.run.player, "on_turn_start")
            return
        for enemy in list(event.run.enemies):
            self._trigger_turn_buffs(event, enemy, "on_turn_start")

    def on_turn_end(self, event):
        if event.is_player:
            self._trigger_turn_buffs(event, event.run.player, "on_turn_end")
            return
        for enemy in list(event.run.enemies):
            self._trigger_turn_buffs(event, enemy, "on_turn_end")

    def on_card_play(self, event):
        from ...entities.buffs import get_buff_impl
        for b in list(event.run.player.buffs):
            impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
            if impl and hasattr(impl, "on_card_play"):
                impl.on_card_play(event, b, event.run.player)

    def on_card_played(self, event):
        from ...entities.buffs import get_buff_impl
        for b in list(event.run.player.buffs):
            impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
            if impl and hasattr(impl, "on_card_played"):
                impl.on_card_played(event, b, event.run.player)
        for enemy in list(event.run.enemies):
            for b in list(enemy.buffs):
                impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                if impl and hasattr(impl, "on_card_played"):
                    impl.on_card_played(event, b, enemy)

    def on_damage_calculate(self, event):
        from ...entities.buffs import get_buff_impl
        if event.source.startswith("p"):
            for b in list(event.run.player.buffs):
                impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                if impl and hasattr(impl, "on_damage_calculate"):
                    impl.on_damage_calculate(event, b, event.run.player)
        if event.source.startswith("e"):
            try:
                idx = int(event.source[1:]) - 1
                if idx < 0: idx = 0
            except ValueError:
                idx = 0
            if 0 <= idx < len(event.run.enemies):
                enemy = event.run.enemies[idx]
                for b in list(enemy.buffs):
                    impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                    if impl and hasattr(impl, "on_damage_calculate"):
                        impl.on_damage_calculate(event, b, enemy)

        if event.target == "p0":
            for b in list(event.run.player.buffs):
                impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                if impl and hasattr(impl, "on_damage_calculate_defend"):
                    impl.on_damage_calculate_defend(event, b, event.run.player)
        elif event.target.startswith("e"):
            try:
                idx = int(event.target[1:]) - 1
                if idx < 0: idx = 0
            except ValueError:
                idx = 0
            if 0 <= idx < len(event.run.enemies):
                enemy = event.run.enemies[idx]
                for b in list(enemy.buffs):
                    impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                    if impl and hasattr(impl, "on_damage_calculate_defend"):
                        impl.on_damage_calculate_defend(event, b, enemy)

    def on_heal(self, event):
        from ...entities.buffs import get_buff_impl
        if event.target == "p0":
            for b in list(event.run.player.buffs):
                impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                if impl and hasattr(impl, "on_heal"):
                    impl.on_heal(event, b, event.run.player)

    def on_heal_calculate(self, event):
        from ...entities.buffs import get_buff_impl
        if event.target == "p0":
            for b in list(event.run.player.buffs):
                impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                if impl and hasattr(impl, "on_heal_calculate"):
                    impl.on_heal_calculate(event, b, event.run.player)

    def on_enemy_sync_intents(self, event):
        from ...entities.buffs import get_buff_impl
        for b in list(event.enemy.buffs):
            impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
            if impl and hasattr(impl, "on_enemy_sync_intents"):
                impl.on_enemy_sync_intents(event, b, event.enemy)

    def on_shield_gain(self, event):
        from ...entities.buffs import get_buff_impl
        if event.target == "p0":
            for b in list(event.run.player.buffs):
                impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                if impl and hasattr(impl, "on_shield_gain"):
                    impl.on_shield_gain(event, b, event.run.player)

    def on_damage_take(self, event):
        from ...entities.buffs import get_buff_impl
        if event.target == "p0":
            for b in list(event.run.player.buffs):
                impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                if impl and hasattr(impl, "on_damage_take_defend"):
                    impl.on_damage_take_defend(event, b, event.run.player, self.engine)
        elif event.target.startswith("e"):
            try:
                idx = int(event.target[1:]) - 1
            except ValueError:
                idx = -1
            if 0 <= idx < len(event.run.enemies):
                enemy = event.run.enemies[idx]
                for b in list(enemy.buffs):
                    impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                    if impl and hasattr(impl, "on_damage_take_defend"):
                        impl.on_damage_take_defend(event, b, enemy, self.engine)

    def on_card_exhaust(self, event):
        from ...entities.buffs import get_buff_impl
        for b in list(event.run.player.buffs):
            impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
            if impl and hasattr(impl, "on_card_exhaust"):
                impl.on_card_exhaust(event, b, event.run.player)
        for enemy in list(event.run.enemies):
            for b in list(enemy.buffs):
                impl = get_buff_impl(b.id, b.stacks, getattr(b, "stacks2", None))
                if impl and hasattr(impl, "on_card_exhaust"):
                    impl.on_card_exhaust(event, b, enemy)

class AmuletTriggerHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(MinionSummonEvent, self.on_minion_summon)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)

    def on_card_played(self, event):
        from ...entities.amulets.amulets import ALL_AMULETS
        for ak, av in list(event.run.player.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template:
                if event.card.type == "spell" and hasattr(template, "on_spell_played"):
                    template.on_spell_played(event.run, ak, event.card, self.engine)
                if hasattr(template, "on_card_played"):
                    template.on_card_played(event.run, ak, event, self.engine)

    def on_damage_take(self, event):
        from ...entities.amulets.amulets import ALL_AMULETS
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
        from ...entities.amulets.amulets import ALL_AMULETS
        for ak, av in list(event.run.player.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template and hasattr(template, "on_minion_summon"):
                template.on_minion_summon(event.run, ak, event, self.engine)

    def on_damage_calculate(self, event):
        from ...entities.amulets.amulets import ALL_AMULETS
        for ak, av in list(event.run.player.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template and hasattr(template, "on_damage_calculate"):
                template.on_damage_calculate(event.run, ak, event, self.engine)


class RallyTriggerHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(MinionSummonEvent, self.on_minion_summon)

    def on_battle_start(self, event):
        event.run.node_data["rally_count"] = 0

    def on_minion_summon(self, event):
        event.run.node_data["rally_count"] = event.run.node_data.get("rally_count", 0) + 1


class MinionTriggerHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(MinionDeathEvent, self.on_minion_death)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(ShieldGainEvent, self.on_shield_gain)
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(CardExhaustEvent, self.on_card_exhaust)
        event_bus.subscribe(TurnEndEvent, self.on_turn_end)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(MinionSummonEvent, self.on_minion_summon)
        event_bus.subscribe(CardPlayEvent, self.on_card_play)

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
        from ...entities.minions.minions import ALL_MINIONS
        for grid, mstate in list(event.run.player.minions.items()):
            base_id = mstate.id.rstrip("+")
            template = ALL_MINIONS.get(base_id)
            if template and hasattr(template, "on_minion_death"):
                template.on_minion_death(event.run, grid, event, self.engine)

    def on_card_played(self, event):
        from ...entities.minions.minions import ALL_MINIONS
        for grid, mstate in list(event.run.player.minions.items()):
            base_id = mstate.id.rstrip("+")
            template = ALL_MINIONS.get(base_id)
            if template and hasattr(template, "on_card_played"):
                template.on_card_played(event.run, grid, event, self.engine)

    def on_shield_gain(self, event):
        from ...entities.minions.minions import ALL_MINIONS
        for grid, mstate in list(event.run.player.minions.items()):
            base_id = mstate.id.rstrip("+")
            template = ALL_MINIONS.get(base_id)
            if template and hasattr(template, "on_shield_gain"):
                template.on_shield_gain(event.run, grid, event, self.engine)

    def on_damage_take(self, event):
        from ...entities.minions.minions import ALL_MINIONS
        for grid, mstate in list(event.run.player.minions.items()):
            base_id = mstate.id.rstrip("+")
            template = ALL_MINIONS.get(base_id)
            if template and hasattr(template, "on_damage_take"):
                template.on_damage_take(event.run, grid, event, self.engine)

    def on_card_exhaust(self, event):
        from ...entities.minions.minions import ALL_MINIONS
        for grid, mstate in list(event.run.player.minions.items()):
            base_id = mstate.id.rstrip("+")
            template = ALL_MINIONS.get(base_id)
            if template and hasattr(template, "on_card_exhaust"):
                template.on_card_exhaust(event.run, grid, event, self.engine)

    def on_turn_end(self, event):
        from ...entities.minions.minions import ALL_MINIONS
        for grid, mstate in list(event.run.player.minions.items()):
            base_id = mstate.id.rstrip("+")
            template = ALL_MINIONS.get(base_id)
            if template and hasattr(template, "on_turn_end"):
                template.on_turn_end(event.run, grid, event, self.engine)

    def on_damage_calculate(self, event):
        from ...entities.minions.minions import ALL_MINIONS
        for grid, mstate in list(event.run.player.minions.items()):
            base_id = mstate.id.rstrip("+")
            template = ALL_MINIONS.get(base_id)
            if template and hasattr(template, "on_damage_calculate"):
                template.on_damage_calculate(event.run, grid, event, self.engine)
            if event.source == f"p{grid}" and getattr(event, "is_attack", False):
                if template and hasattr(template, "on_attack"):
                    template.on_attack(event.run, grid, event, self.engine)

    def on_minion_summon(self, event):
        from ...entities.minions.minions import ALL_MINIONS
        mstate = event.minion_state
        template = ALL_MINIONS.get(mstate.id.rstrip("+"))
        if template:
            template.on_minion_summon(event.run, event.grid, event, self.engine)


class EnemyTriggerHandler:
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

    def on_enemy_before_death(self, event):
        from ...entities import get_enemy_template
        template = get_enemy_template(event.enemy.name)
        if template and hasattr(template, "on_enemy_before_death"):
            template.on_enemy_before_death(event.run, event.enemy, event, self.engine)

    def on_card_play(self, event):
        from ...entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_card_play"):
                template.on_card_play(event, enemy, self.engine)

    def on_turn_start(self, event):
        from ...entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_turn_start"):
                template.on_turn_start(event, enemy, self.engine)

    def on_turn_end(self, event):
        from ...entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_turn_end"):
                template.on_turn_end(event, enemy, self.engine)

    def on_battle_start(self, event):
        from ...entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_battle_start") and not getattr(enemy, "_battle_init_done", False):
                enemy._battle_init_done = True
                template.on_battle_start(event.run, enemy, self.engine)

    def on_card_played(self, event):
        from ...entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_card_played"):
                template.on_card_played(event, enemy, self.engine)

    def on_damage_take(self, event):
        from ...entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_damage_take"):
                template.on_damage_take(event, enemy, self.engine)

    def on_damage_calculate(self, event):
        from ...entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_damage_calculate"):
                template.on_damage_calculate(event, enemy, self.engine)

    def on_card_exhaust(self, event):
        from ...entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_card_exhaust"):
                template.on_card_exhaust(event, enemy, self.engine)

    def on_minion_death(self, event):
        from ...entities import get_enemy_template
        for enemy in list(event.run.enemies):
            if enemy.hp <= 0:
                continue
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_minion_death"):
                template.on_minion_death(event, enemy, self.engine)



class CardTriggerHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(CardExhaustEvent, self.on_card_exhaust)

    def on_card_exhaust(self, event):
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(event.card_id)
        base_cid = c_state.id
        if base_cid == "warrior_shield_bash":
            p = event.run.player
            p.actions += 2
            p.bonus_actions += 2
            self.engine._log_event(event.run, get_locale_text("i18n_battle_misc.shield_bash_exhaust_log"))


class StatTrackingHandler:
    def __init__(self, event_bus, save_manager):
        self.save_manager = save_manager
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(MinionDeathEvent, self.on_minion_death)
        event_bus.subscribe(BattleWinEvent, self.on_battle_win)

    def on_damage_take(self, event):
        if event.target.startswith("e") and event.amount > 0:
            StatsTracker.record_damage(event.run, event.run.user_id, event.amount)

    def on_minion_death(self, event):
        if event.is_enemy:
            StatsTracker.record_kill(event.run, event.run.user_id)

    def on_battle_win(self, event):
        StatsTracker.flush(self.save_manager, event.run)

