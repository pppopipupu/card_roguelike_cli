from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("远古红龙")
class BossRedDragonTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("远古红龙", {})
        intents = cfg.get("intents", [])
        intents_list = []
        for _ in range(enemy.max_actions):
            chosen = random.choice(intents)
            intents_list.append(EnemyIntentState(
                type=chosen["id"],
                val=chosen["val"],
                desc=chosen["desc"],
                cost_a=1,
                cost_ba=0
            ))
        for _ in range(enemy.max_bonus_actions):
            chosen = random.choice(intents)
            intents_list.append(EnemyIntentState(
                type=chosen["id"],
                val=chosen["val"],
                desc=chosen["desc"],
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
        import random
        if intent.type == "attack":
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            dmg = intent.val + strength
            self._perform_attack(run, engine, enemy, dmg, logs)
        elif intent.type == "defend":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_defend", enemy_name=enemy.name, val=intent.val))
        elif intent.type == "summon":
            from ....models.state import EnemyState, EnemyIntentState
            cfg = ENEMY_CONFIG.get("远古红龙", {})
            sg = cfg.get("summon_goblin", {})
            new_goblin = EnemyState(
                name=sg.get("name", "魔仆"),
                hp=sg.get("hp", 5),
                max_hp=sg.get("max_hp", 5),
                shield=0,
                actions=1,
                bonus_actions=0,
                is_summon=True,
                max_actions=1,
                max_bonus_actions=0,
                intents=[EnemyIntentState(
                    type="attack",
                    val=sg.get("intent_val", 1),
                    desc=sg.get("intent_desc", get_locale_text("i18n_enemy_boss.goblin_intent_prepare")),
                    cost_a=1,
                    cost_ba=0
                )]
            )
            run.enemies.append(new_goblin)
            logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_summon", enemy_name=enemy.name))
        elif intent.type == "attack_all":
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            dmg = intent.val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            after_logs = run.node_data.get("battle_logs", [])
            if len(after_logs) > before_len:
                dmg_msg = after_logs.pop()
                logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_tail_player", enemy_name=enemy.name, dmg_msg=dmg_msg))
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", dmg, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_tail_minion", minion_name=m_name, dmg_msg=dmg_msg))
        return "\n".join(logs)

@register_enemy("雷霆领主")
class BossThunderLordTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        if run.node_data.get("thunder_lord_overloaded"):
            enemy.actions = max(0, enemy.actions - 1)
            run.node_data["thunder_lord_overloaded"] = False
        turn = run.node_data.get("thunder_lord_turn", 1)
        cycle = (turn - 1) % 4 + 1
        intents_list = []
        if cycle == 1:
            itype, val, desc = "thunder_strike", 8, get_locale_text("i18n_enemy_boss.thunder_lord_intent_strike_8")
        elif cycle == 2:
            itype, val, desc = "lightning_shield", 12, get_locale_text("i18n_enemy_boss.thunder_lord_intent_shield_12")
        elif cycle == 3:
            itype, val, desc = "storm_summon", 0, get_locale_text("i18n_enemy_boss.thunder_lord_intent_summon")
        else:
            itype, val, desc = "electric_overload", 6, get_locale_text("i18n_enemy_boss.thunder_lord_intent_overload")
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=1, cost_ba=0))

        if cycle == 1:
            itype, val, desc = "lightning_shield", 10, get_locale_text("i18n_enemy_boss.thunder_lord_intent_shield_10")
        elif cycle == 2:
            itype, val, desc = "thunder_strike", 6, get_locale_text("i18n_enemy_boss.thunder_lord_intent_strike_6")
        elif cycle == 3:
            itype, val, desc = "defend", 8, get_locale_text("i18n_enemy_boss.thunder_lord_intent_guard_8")
        else:
            itype, val, desc = "thunder_strike", 8, get_locale_text("i18n_enemy_boss.thunder_lord_intent_strike_8")
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=0, cost_ba=1))

        if cycle == 1:
            itype, val, desc = "defend", 6, get_locale_text("i18n_enemy_boss.thunder_lord_intent_guard_6")
        elif cycle == 2:
            itype, val, desc = "defend", 6, get_locale_text("i18n_enemy_boss.thunder_lord_intent_guard_6")
        elif cycle == 3:
            itype, val, desc = "thunder_strike", 6, get_locale_text("i18n_enemy_boss.thunder_lord_intent_strike_6")
        else:
            itype, val, desc = "defend", 10, get_locale_text("i18n_enemy_boss.thunder_lord_intent_guard_10")
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=0, cost_ba=1))
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
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength

        if intent.type == "thunder_strike":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="thunder")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "shock", get_locale_text("i18n_enemy_boss.buff_shock"), get_locale_text("i18n_enemy_boss.buff_shock_desc"), 2)
            logs.append(get_locale_text("i18n_enemy_boss.thunder_lord_log_strike", enemy_name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "lightning_shield":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(enemy, "lightning_shield", get_locale_text("i18n_enemy_boss.buff_lightning_shield"), get_locale_text("i18n_enemy_boss.buff_lightning_shield_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.thunder_lord_log_shield", enemy_name=enemy.name, val=intent.val))
        elif intent.type == "storm_summon":
            from ....models.state import EnemyState, EnemyIntentState
            new_minion = EnemyState(
                name="雷影魔仆",
                hp=12,
                max_hp=12,
                shield=0,
                actions=1,
                bonus_actions=0,
                is_summon=True,
                max_actions=1,
                max_bonus_actions=0,
                intents=[EnemyIntentState(
                    type="lightning_strike",
                    val=4,
                    desc=get_locale_text("i18n_enemy_boss.thunder_lord_intent_lightning_strike_4"),
                    cost_a=1,
                    cost_ba=0
                )]
            )
            run.enemies.append(new_minion)
            logs.append(get_locale_text("i18n_enemy_boss.thunder_lord_log_summon", enemy_name=enemy.name))
        elif intent.type == "electric_overload":
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_boss.buff_strength"), get_locale_text("i18n_enemy_boss.buff_strength_desc"), 2)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="lightning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            run.node_data["thunder_lord_overloaded"] = True
            logs.append(get_locale_text("i18n_enemy_boss.thunder_lord_log_overload", enemy_name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "defend":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_boss.thunder_lord_log_defend", enemy_name=enemy.name, val=intent.val))
        return "\n".join(logs)
