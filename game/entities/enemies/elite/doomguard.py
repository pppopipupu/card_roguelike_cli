from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("末日守卫")
class DoomguardTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("末日守卫", {})
        intents = cfg.get("intents", [])
        chosen = random.choice(intents)
        return [EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0)]

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

        if intent.type == "doom_strike":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="piercing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "minor_vulnerable_slashing", get_locale_text("i18n_enemy_elite_a.common.slashing_vulnerable_name"), get_locale_text("i18n_enemy_elite_a.common.slashing_vulnerable_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_a.doomguard.doom_strike", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "hellfire":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="fire")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "minor_vulnerable_fire", get_locale_text("i18n_enemy_elite_a.common.fire_vulnerable_name"), get_locale_text("i18n_enemy_elite_a.common.fire_vulnerable_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_a.doomguard.hellfire", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "sacrifice":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._damage_target(run, f"e{run.enemies.index(enemy)+1}", 2, source=f"enemy:{enemy.name}", damage_type="true")
            logs.append(get_locale_text("i18n_enemy_elite_a.doomguard.sacrifice", name=enemy.name, val=intent.val))
