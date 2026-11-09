from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.locale_data import get_locale_text

@register_enemy("亚弗戈蒙")
class BossAforgomonTemplate(EnemyTemplate):
    def on_enemy_before_death(self, run, enemy, event, engine):
        if enemy.name == "亚弗戈蒙":
            event.cancel()
            enemy.hp = 1
            enemy.shield = 0
            if "pending_transitions" not in run.node_data:
                run.node_data["pending_transitions"] = {}
            run.node_data["pending_transitions"][enemy.name] = 2
            from ....models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_boss.buff_phase_transition"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_phase_transition_desc")))
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc=get_locale_text("i18n_enemy_boss.aforgomon_intent_phase_transition"),
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, get_locale_text("i18n_enemy_boss.aforgomon_log_death_phase1"))

    def apply_phase_transition(self, run, enemy, target_phase: int, engine, logs: list):
        from ....models.state import BuffState
        if target_phase == 2:
            enemy.name = "【时空主宰】亚弗戈蒙"
            enemy.max_hp = 220
            enemy.hp = 220
            enemy.shield = 40
            enemy.actions = 3
            enemy.bonus_actions = 1
            enemy.max_actions = 3
            enemy.max_bonus_actions = 1
            enemy.buffs.clear()
            enemy.buffs.append(BuffState(id="time_lord_passive", name=get_locale_text("i18n_enemy_boss.buff_time_lord"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_time_lord_desc")))
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_boss.buff_phase_transition"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_phase_transition_desc")))
            engine._add_buff_to(run.player, "pendulum_resonance", get_locale_text("i18n_enemy_boss.buff_pendulum_resonance"), get_locale_text("i18n_enemy_boss.buff_pendulum_resonance_desc"), 1)
            run.node_data["aforgomon_phase"] = 2
            run.node_data["aforgomon_turn"] = 0
            logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_phase2"))
            logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_phase2_quote", player_name=run.player.name))

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        phase = run.node_data.get("aforgomon_phase", 1)
        turn = run.node_data.get("aforgomon_turn", 1)
        run.node_data["aforgomon_turn"] = turn + 1
        intents_list = []
        if phase == 1:
            for _ in range(enemy.max_actions):
                chosen = random.choice([
                    {"id": "chain_of_time", "val": 8, "desc": get_locale_text("i18n_enemy_boss.aforgomon_intent_chain_of_time")},
                    {"id": "portal_implosion", "val": 15, "desc": get_locale_text("i18n_enemy_boss.aforgomon_intent_portal_implosion")}
                ])
                intents_list.append(EnemyIntentState(
                    type=chosen["id"],
                    val=chosen["val"],
                    desc=chosen["desc"],
                    cost_a=1,
                    cost_ba=0
                ))
            for _ in range(enemy.max_bonus_actions):
                intents_list.append(EnemyIntentState(
                    type="time_warp",
                    val=15,
                    desc=get_locale_text("i18n_enemy_boss.aforgomon_intent_time_warp"),
                    cost_a=0,
                    cost_ba=1
                ))
        else:
            for _ in range(enemy.max_actions):
                chosen = random.choice([
                    {"id": "time_fracture", "val": 12, "desc": get_locale_text("i18n_enemy_boss.aforgomon_intent_time_fracture")},
                    {"id": "silver_bell_clang", "val": 15, "desc": get_locale_text("i18n_enemy_boss.aforgomon_intent_silver_bell")},
                    {"id": "time_reflux", "val": 0, "desc": get_locale_text("i18n_enemy_boss.aforgomon_intent_time_reflux")}
                ])
                intents_list.append(EnemyIntentState(
                    type=chosen["id"],
                    val=chosen["val"],
                    desc=chosen["desc"],
                    cost_a=1,
                    cost_ba=0
                ))
            for _ in range(enemy.max_bonus_actions):
                intents_list.append(EnemyIntentState(
                    type="temporal_lock",
                    val=5,
                    desc=get_locale_text("i18n_enemy_boss.aforgomon_intent_temporal_lock"),
                    cost_a=0,
                    cost_ba=1
                ))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ....models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        p = run.player
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength

        if intent.type == "chain_of_time":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "drain_a", get_locale_text("i18n_enemy_boss.buff_drain_a"), get_locale_text("i18n_enemy_boss.buff_drain_a_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_chain_of_time", enemy_name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "portal_implosion":
            extra = 5 if p.shield > 0 else 0
            final_val = val + extra
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", final_val, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_portal_implosion", enemy_name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "time_warp":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_boss.buff_strength"), get_locale_text("i18n_enemy_boss.buff_strength_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_time_warp", enemy_name=enemy.name))
        elif intent.type == "time_fracture":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_time_fracture", enemy_name=enemy.name, dmg_msg=dmg_msg))
            affected = []
            if len(p.hand) > 1:
                for card in p.hand[1:]:
                    card.fragile = max(card.fragile, 1)
                    from ....entities import ALL_CARDS
                    card_name = get_locale_text("i18n_enemy_boss.card_unknown")
                    if card in ALL_CARDS:
                        card_name = ALL_CARDS[card].name
                    elif card.id in ALL_CARDS:
                        card_name = ALL_CARDS[card.id].name
                    affected.append(f"【{card_name}】")
            if affected:
                logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_time_fracture_affected", cards='、'.join(affected)))
        elif intent.type == "silver_bell_clang":
            has_resonance = any(b.id == "pendulum_resonance" for b in p.buffs)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="thunder")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_silver_bell", enemy_name=enemy.name, dmg_msg=dmg_msg))
            if has_resonance:
                before_len2 = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", 5, source=f"enemy:{enemy.name}", damage_type="true")
                after_logs2 = run.node_data.get("battle_logs", [])
                dmg_msg2 = after_logs2.pop() if len(after_logs2) > before_len2 else ""
                logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_silver_bell_resonance", dmg_msg=dmg_msg2))
            else:
                engine._add_buff_to(p, "pendulum_resonance", get_locale_text("i18n_enemy_boss.buff_pendulum_resonance"), get_locale_text("i18n_enemy_boss.buff_pendulum_resonance_desc"), 1)
                logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_silver_bell_apply"))
        elif intent.type == "time_reflux":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", 20)
                engine._heal_target(run, f"e{run.enemies.index(enemy)+1}", 25)
            logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_time_reflux", enemy_name=enemy.name))
            from ...buffs import is_debuff
            neg_buff = next((b for b in enemy.buffs if is_debuff(b.id)), None)
            if neg_buff:
                neg_name = neg_buff.name
                neg_buff.stacks -= 1
                if neg_buff.stacks <= 0:
                    enemy.buffs.remove(neg_buff)
                engine._sync_enemy_intents(enemy)
                logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_time_reflux_cleanse", enemy_name=enemy.name, neg_name=neg_name))
        elif intent.type == "temporal_lock":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "discard_next_turn", get_locale_text("i18n_enemy_boss.buff_discard_next_turn"), get_locale_text("i18n_enemy_boss.buff_discard_next_turn_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.aforgomon_log_temporal_lock", enemy_name=enemy.name, dmg_msg=dmg_msg))
        return "\n".join(logs)

register_enemy("【时空主宰】亚弗戈蒙")(BossAforgomonTemplate)
