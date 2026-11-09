from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("先古守卫")
class AncientWardenTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("先古守卫", {})
        intents = cfg.get("intents", [])
        
        intents_list = []
        for _ in range(enemy.max_actions):
            chosen = random.choice(intents)
            intents_list.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.max_bonus_actions):
            chosen = random.choice(intents)
            intents_list.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1))
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

        if intent.type == "portal_smash":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_elite_a.ancient_warden.portal_smash", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "ancient_charge":
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_elite_a.common.strength_name"), get_locale_text("i18n_enemy_elite_a.common.strength_desc"), 3)
            logs.append(get_locale_text("i18n_enemy_elite_a.ancient_warden.ancient_charge", name=enemy.name))
        elif intent.type == "space_lock":
            engine._add_buff_to(run.player, "drain_a", get_locale_text("i18n_enemy_elite_a.common.time_entangle_name"), get_locale_text("i18n_enemy_elite_a.common.time_entangle_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_a.ancient_warden.space_lock", name=enemy.name))
