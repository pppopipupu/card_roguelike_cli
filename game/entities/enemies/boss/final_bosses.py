import random
from typing import List, Optional

from ..base import EnemyTemplate, register_enemy
from ...buffs import is_debuff
from ....core.inventory.deck_service import DeckService
from ....data.text.locale_data import get_locale_text
from ....core.text.events import locale_text
from ....data.enemies.yog_sothoth_data import (
    YOG_HELP_CARDS,
    YOG_INTENT_EFFECTS,
    YOG_INTENT_HANDLERS,
    YOG_INTENT_SCHEDULE,
    YOG_PHASE4_PASSIVE,
    YOG_PHASE_BY_NAME,
    YOG_SOTHOTH_PHASES,
)


@register_enemy("虚空之门·尤格-索托斯")
class BossYogSothothTemplate(EnemyTemplate):
    def _text(self, key: str, **kwargs) -> str:
        return get_locale_text(f"i18n_enemy_boss.{key}", **kwargs)

    def on_battle_start(self, run, enemy, engine):
        engine._add_buff_to(enemy, "ancient_protection", get_locale_text("i18n_battle_core.ancient_protection_name"), get_locale_text("i18n_battle_core.ancient_protection_desc"))
        run.node_data["boss_name"] = enemy.name
        run.node_data["yog_sothoth_phase"] = 1
        run.node_data["yog_sothoth_turn"] = 1
        stats = engine.save_manager.load_stats(run.user_id) if engine.save_manager else None
        if stats:
            stats.yog_sothoth_challenge_count = getattr(stats, "yog_sothoth_challenge_count", 0) + 1
            from ....core.progress.achievement_service import AchievementService
            AchievementService(engine.save_manager).reconcile(run.user_id, stats=stats, save=False, run=run, battle_engine=engine)
            engine.save_manager.save_stats(run.user_id, stats)
            challenge_count = stats.yog_sothoth_challenge_count
        else:
            challenge_count = 1
        if challenge_count == 1:
            engine._log_event(run, locale_text(key="i18n_battle_core.yog_sothoth_intro_first"))
        else:
            engine._log_event(run, locale_text(key="i18n_battle_core.yog_sothoth_intro_repeat", params={"name": run.player.name}))

    def _hit_target(self, run, engine, enemy, target: str, amount: int, damage_type: str) -> str:
        before_len = len(run.node_data.get("battle_logs", []))
        engine._damage_target(run, target, amount, source=f"enemy:{enemy.name}", damage_type=damage_type)
        after_logs = run.node_data.get("battle_logs", [])
        return after_logs.pop() if len(after_logs) > before_len else ""

    def _apply_buff(self, target, engine, buff_id: str, stacks: int):
        engine._add_buff_to(
            target,
            buff_id,
            self._text(f"buff_{buff_id}"),
            self._text(f"buff_{buff_id}_desc"),
            stacks,
        )

    def _hit_minions(self, run, engine, enemy, effect: dict, val: int, logs: list):
        mode = effect.get("minion_mode")
        if not mode:
            return
        player = run.player
        amount = effect.get("minion_val")
        if amount is None:
            amount = val
        damage_type = effect.get("minion_damage_type", effect.get("damage_type", "force"))
        if mode == "random":
            for _ in range(effect.get("minion_count", 1)):
                if not player.minions:
                    return
                target_key = random.choice(list(player.minions.keys()))
                minion_name = player.minions[target_key].name
                dmg_msg = self._hit_target(run, engine, enemy, f"p{target_key}", amount, damage_type)
                logs.append(self._text(effect["minion_log"], minion_name=minion_name, dmg_msg=dmg_msg))
            return
        for target_key in list(player.minions.keys()):
            if target_key not in player.minions:
                continue
            minion_name = player.minions[target_key].name
            dmg_msg = self._hit_target(run, engine, enemy, f"p{target_key}", amount, damage_type)
            logs.append(self._text(effect["minion_log"], minion_name=minion_name, dmg_msg=dmg_msg))

    def _self_target(self, run, enemy) -> str:
        return f"e{run.enemies.index(enemy)+1}"

    def on_turn_start(self, event, enemy, engine):
        if not event.is_player:
            return
        run = event.run
        p = run.player
        run.node_data["merchant_collection_free_cards"] = []
        if run.node_data.get("yog_sothoth_phase", 1) == 4:
            run.node_data["yog_sothoth_turn"] = run.node_data.get("yog_sothoth_turn", 0) + 1
            npc_id, card_id, quote_key, name_key = random.choice(YOG_HELP_CARDS)
            from ....models.state import CardState
            p.hand.append(CardState(id=card_id, upgraded=True))
            engine._log_event(
                run,
                self._text("yog_log_help_card", quote=self._text(quote_key), card_name=self._text(name_key)),
            )

    def on_card_play(self, event, enemy, engine):
        run = event.run
        p = run.player
        card = event.card
        if run.node_data.get("intangible_whisper_active"):
            run.node_data.pop("intangible_whisper_active", None)
            if card.type == "spell" and getattr(card, "base_dmg", 0) > 0:
                my_targets = ["p0"] + [f"p{k}" for k in p.minions.keys()]
                event.target = random.choice(my_targets)
                engine._log_event(run, self._text("yog_log_whisper_redirect_spell", card_name=card.name, target_name=engine._get_target_name(run, event.target)))
            elif card.type == "spell" and getattr(card, "heal_amount", 0) > 0:
                if run.enemies:
                    event.target = f"e{random.randint(1, len(run.enemies))}"
                    engine._log_event(run, self._text("yog_log_whisper_redirect_heal", target_name=engine._get_target_name(run, event.target)))
            elif card.type == "attack" or card.id.startswith("warrior_"):
                my_targets = ["p0"] + [f"p{k}" for k in p.minions.keys()]
                event.target = random.choice(my_targets)
                engine._log_event(run, self._text("yog_log_whisper_redirect_attack", card_name=card.name, target_name=engine._get_target_name(run, event.target)))

        if card.id in run.node_data.get("merchant_collection_free_cards", []):
            event.cost_a = 0
            event.cost_ba = 0

        if run.node_data.get("yog_sothoth_phase", 1) == 4 and card.type == "spell":
            if random.random() < YOG_PHASE4_PASSIVE["spell_cancel_chance"]:
                event.cancel()
                p.actions = max(0, p.actions - event.cost_a)
                p.bonus_actions = max(0, p.bonus_actions - event.cost_ba)
                hand_idx = run.node_data.get("current_playing_card_hand_idx", 0)
                if 0 <= hand_idx < len(p.hand):
                    c_state = p.hand.pop(hand_idx)
                else:
                    c_state = None
                if c_state:
                    p.exhaust_pile.append(c_state)
                    from ....models.events import CardExhaustEvent
                    exhaust_evt = CardExhaustEvent(run, c_state, "void_distortion_cancel")
                    engine.event_bus.dispatch(exhaust_evt)
                engine._log_event(run, self._text("yog_log_space_disorder", card_name=card.name))
                turn_key = run.turn_key("cards_played_this_turn", run.player)
                run.node_data[turn_key] = run.node_data.get(turn_key, 0) + 1
                engine.save_manager.save_save(run.user_id, run)

    def on_turn_end(self, event, enemy, engine):
        if not event.is_player:
            return
        run = event.run
        p = run.player
        if run.node_data.get("yog_sothoth_phase", 1) == 4 and len(p.hand) == 0:
            engine.combat_resolver.damage_target(run, "p0", YOG_PHASE4_PASSIVE["empty_hand_damage"], source="yog_sothoth_passive", damage_type="true")
            engine._log_event(run, self._text("yog_log_no_hand_damage"))
        for cs in p.hand:
            if cs.id == "curse_intangible_whisper":
                run.node_data["intangible_whisper_active"] = True

    def on_enemy_before_death(self, run, enemy, event, engine):
        target_phase = YOG_PHASE_BY_NAME.get(enemy.name)
        if target_phase is None:
            return
        config = YOG_SOTHOTH_PHASES[target_phase]
        event.cancel()
        enemy.hp = 1
        enemy.shield = 0
        run.node_data.setdefault("pending_transitions", {})[enemy.name] = target_phase
        from ....models.state import BuffState, EnemyIntentState
        enemy.buffs.append(BuffState(
            id="phase_transition_immune",
            name=self._text("buff_phase_transition"),
            stacks=1,
            desc=self._text("buff_phase_transition_desc"),
        ))
        enemy.intents.clear()
        enemy.intents.append(EnemyIntentState(
            type="phase_transition",
            val=0,
            desc=self._text(config["transition_desc_key"]),
            cost_a=1,
            cost_ba=0,
        ))
        engine.enemy_controller.sync_enemy_intents(enemy)
        engine._log_event(run, self._text(config["death_log"]))

    def apply_phase_transition(self, run, enemy, target_phase: int, engine, logs: list):
        config = YOG_SOTHOTH_PHASES.get(target_phase)
        if not config:
            return
        from ....models.state import BuffState, EnemyIntentState
        enemy.name = config["name"]
        enemy.max_hp = config["max_hp"]
        enemy.hp = config["max_hp"]
        enemy.shield = config["shield"]
        enemy.actions = config["actions"]
        enemy.bonus_actions = config["bonus_actions"]
        enemy.max_actions = config["max_actions"]
        enemy.max_bonus_actions = config["max_bonus_actions"]
        enemy.buffs.clear()
        passive_id, passive_name_key, passive_desc_key = config["passive_buff"]
        enemy.buffs.append(BuffState(
            id=passive_id,
            name=self._text(passive_name_key),
            stacks=1,
            desc=self._text(passive_desc_key),
        ))
        enemy.buffs.append(BuffState(
            id="phase_transition_immune",
            name=self._text("buff_phase_transition"),
            stacks=1,
            desc=self._text("buff_phase_transition_desc"),
        ))
        run.node_data["yog_sothoth_phase"] = target_phase
        run.node_data["yog_sothoth_turn"] = 0
        run.node_data["is_void_corrupted"] = True
        if config["set_transition_intent"]:
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc=self._text(config["transition_desc_key"]),
                cost_a=1,
                cost_ba=0,
            ))
        for key, kwargs_source in config["append_logs"]:
            if kwargs_source == "player_name":
                logs.append(self._text(key, player_name=run.player.name))
            else:
                logs.append(self._text(key))
        if config["sync_intents"]:
            engine.enemy_controller.sync_enemy_intents(enemy)
        for key, kwargs_source in config["event_logs"]:
            if kwargs_source == "player_name":
                engine._log_event(run, self._text(key, player_name=run.player.name))
            else:
                engine._log_event(run, self._text(key))
        if config["challenge_logs"]:
            stats = engine.save_manager.load_stats(run.user_id)
            challenge_count = getattr(stats, "yog_sothoth_challenge_count", 1)
            challenge_key = config["challenge_logs"]["first"] if challenge_count == 1 else config["challenge_logs"]["repeat"]
            engine._log_event(run, self._text(challenge_key))
        for key, kwargs_source in config["tail_event_logs"]:
            engine._log_event(run, self._text(key))

    def roll_intents(self, run, engine, enemy) -> List:
        from ....models.state import EnemyIntentState
        phase = run.node_data.get("yog_sothoth_phase", 1)
        turn = run.node_data.get("yog_sothoth_turn", 1)
        run.node_data["yog_sothoth_turn"] = turn + 1
        cycle = (turn - 1) % 4 + 1
        schedule = YOG_INTENT_SCHEDULE.get(phase, YOG_INTENT_SCHEDULE[4])
        entries = schedule.get(cycle, schedule[4])
        return [
            EnemyIntentState(
                type=intent_type,
                val=val,
                desc=self._text(desc_key),
                cost_a=cost_a,
                cost_ba=cost_ba,
            )
            for intent_type, val, desc_key, cost_a, cost_ba in entries
        ]

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        if logs is None:
            logs = []
        strength = sum(b.stacks for b in enemy.buffs if b.id == "strength")
        val = intent.val
        handler_name = YOG_INTENT_HANDLERS.get(intent.type)
        if handler_name:
            getattr(self, handler_name)(run, engine, enemy, intent, val, logs)
        return "\n".join(logs)

    def intent_gate_gaze(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))
        self._hit_minions(run, engine, enemy, effect, val, logs)
        buff_id, stacks = effect["buff"]
        self._apply_buff(run.player, engine, buff_id, stacks)
        for key in effect.get("extra_logs", []):
            logs.append(self._text(key, enemy_name=enemy.name))

    def intent_void_storm(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))
        self._hit_minions(run, engine, enemy, effect, val, logs)

    def intent_ancient_resonance(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        if enemy in run.enemies:
            engine._gain_shield(run, self._self_target(run, enemy), intent.val)
        self._apply_buff(enemy, engine, "strength", effect["self_strength"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name, val=intent.val))

    def intent_void_corruption(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        buff_id, stacks = effect["buff"]
        self._apply_buff(run.player, engine, buff_id, stacks)
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))
        for key in effect.get("extra_logs", []):
            logs.append(self._text(key))

    def intent_gravity_press(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        lost_shield_msg = ""
        if run.player.shield > 0:
            lost_amount = min(effect["shield_loss"], run.player.shield)
            run.player.shield -= lost_amount
            lost_shield_msg = self._text(effect["shield_log"], amount=lost_amount)
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg, lost_shield_msg=lost_shield_msg))
        self._hit_minions(run, engine, enemy, effect, val, logs)

    def intent_void_exhaust(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        buff_id, stacks = effect["buff"]
        self._apply_buff(run.player, engine, buff_id, stacks)
        logs.append(self._text(effect["log"], enemy_name=enemy.name))

    def intent_decay_whisper(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        buff_id, stacks = effect["buff"]
        self._apply_buff(run.player, engine, buff_id, stacks)
        logs.append(self._text(effect["log"], enemy_name=enemy.name))

    def intent_mana_block(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        buff_id, stacks = effect["buff"]
        self._apply_buff(run.player, engine, buff_id, stacks)
        logs.append(self._text(effect["log"], enemy_name=enemy.name))

    def intent_dimensional_distortion(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        if enemy in run.enemies:
            engine._gain_shield(run, self._self_target(run, enemy), intent.val)
        logs.append(self._text(effect["log"], enemy_name=enemy.name, val=intent.val))

    def intent_time_collapse(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        for buff_id, stacks in effect["buffs"]:
            self._apply_buff(run.player, engine, buff_id, stacks)
        for card_id in effect["curses"]:
            DeckService.add_card_to_draw(run.player, card_id)
        random.shuffle(run.player.draw_pile)
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))

    def intent_chaos_beam(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))
        self._hit_minions(run, engine, enemy, effect, val, logs)

    def intent_void_shield_large(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        if enemy in run.enemies:
            engine._gain_shield(run, self._self_target(run, enemy), intent.val)
        neg_buff = next((b for b in enemy.buffs if is_debuff(b.id)), None)
        if neg_buff:
            neg_name = neg_buff.name
            neg_buff.stacks -= effect["cleanse"]
            if neg_buff.stacks <= 0:
                enemy.buffs.remove(neg_buff)
            engine._sync_enemy_intents(enemy)
            logs.append(self._text(effect["cleanse_log"], enemy_name=enemy.name, val=intent.val, neg_name=neg_name))
        else:
            logs.append(self._text(effect["log"], enemy_name=enemy.name, val=intent.val))

    def intent_all_gates_open(self, run, engine, enemy, intent, val, logs):
        from ....models.state import EnemyState, EnemyIntentState
        effect = YOG_INTENT_EFFECTS[intent.type]
        summon = effect["summon"]
        empty_slots = effect["max_enemies"] - len(run.enemies)
        summon_count = min(effect["max_summons"], empty_slots)
        for _ in range(summon_count):
            run.enemies.append(EnemyState(
                name=summon["name"],
                hp=summon["hp"],
                max_hp=summon["hp"],
                shield=summon["shield"],
                actions=summon["actions"],
                bonus_actions=summon["bonus_actions"],
                is_summon=True,
                max_actions=summon["max_actions"],
                max_bonus_actions=summon["max_bonus_actions"],
                intents=[EnemyIntentState(
                    type=summon["intent_type"],
                    val=summon["intent_val"],
                    desc=self._text(summon["intent_desc_key"]),
                    cost_a=summon["intent_cost_a"],
                    cost_ba=summon["intent_cost_ba"],
                )],
            ))
        for e in run.enemies:
            self._apply_buff(e, engine, "strength", effect["strength"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name, summon_count=summon_count))
        if summon_count < effect["max_summons"]:
            dmg_msg = self._hit_target(run, engine, enemy, "p0", effect["blocked_damage"], effect["blocked_damage_type"])
            logs.append(self._text(effect["blocked_log"], dmg_msg=dmg_msg))

    def intent_abyss_gaze(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        run.node_data["draw_penalty_next_turn"] = effect["draw_penalty"]
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))

    def intent_strength_infuse(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        for e in run.enemies:
            self._apply_buff(e, engine, "strength", effect["strength"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name))

    def intent_end_whisper(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        buff_id, stacks = effect["buff"]
        self._apply_buff(run.player, engine, buff_id, stacks)
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))

    def intent_doomsday_tide(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))
        self._hit_minions(run, engine, enemy, effect, val, logs)
        if enemy in run.enemies:
            engine._heal_target(run, self._self_target(run, enemy), effect["self_heal"])
        logs.append(self._text(effect["heal_log"], enemy_name=enemy.name))

    def intent_reality_shatter(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))

    def intent_meta_code_injection(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))
        for key in effect.get("extra_logs", []):
            logs.append(self._text(key))

    def intent_data_overflow(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        before_len = len(run.node_data.get("battle_logs", []))
        for _ in range(effect["hits"]):
            engine._damage_target(run, "p0", effect["damage"], source=f"enemy:{enemy.name}", damage_type=effect["damage_type"])
        after_logs = run.node_data.get("battle_logs", [])
        dmg_msgs = []
        while len(after_logs) > before_len:
            dmg_msgs.append(after_logs.pop())
        dmg_msgs.reverse()
        dmg_summary = " ".join(dmg_msgs)
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_summary=dmg_summary))
        for key in effect.get("extra_logs", []):
            logs.append(self._text(key))

    def intent_save_erase(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        if enemy in run.enemies:
            engine._gain_shield(run, self._self_target(run, enemy), effect["self_shield"])
        gold_removed = 0
        if run.player.gold >= effect["gold_cost"]:
            run.player.gold -= effect["gold_cost"]
            gold_removed = effect["gold_cost"]
        else:
            if run.player.hp > effect["hp_floor"]:
                amount = min(effect["gold_cost"], run.player.hp - effect["hp_floor"])
                engine._damage_target(run, "p0", amount, source=f"enemy:{enemy.name}", damage_type="true")
            run.player.max_hp = max(effect["min_max_hp"], run.player.max_hp - effect["max_hp_loss"])
        if gold_removed:
            logs.append(self._text(effect["log_gold"], enemy_name=enemy.name))
        else:
            logs.append(self._text(effect["log_hp"], enemy_name=enemy.name, hp_limit_removed=effect["max_hp_loss"]))

    def intent_input_hijack(self, run, engine, enemy, intent, val, logs):
        effect = YOG_INTENT_EFFECTS[intent.type]
        dmg_msg = self._hit_target(run, engine, enemy, "p0", val, effect["damage_type"])
        for card_id in effect["curses"]:
            DeckService.add_card_to_draw(run.player, card_id)
        random.shuffle(run.player.draw_pile)
        logs.append(self._text(effect["log"], enemy_name=enemy.name, dmg_msg=dmg_msg))


register_enemy("【觉醒】虚空之门·尤格-索托斯")(BossYogSothothTemplate)
register_enemy("【终焉】虚空之门·尤格-索托斯")(BossYogSothothTemplate)
register_enemy("【万物归一】虚空之门·尤格-索托斯")(BossYogSothothTemplate)
