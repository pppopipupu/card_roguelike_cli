from typing import List, Optional
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("虚空游荡者")
class VoidWandererTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("虚空游荡者", {})
        intents = cfg.get("intents", [])
        chosen = random.choice(intents)
        return [EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0)]

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        if logs is None:
            logs = []
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength
    
        if intent.type == "void_bite":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="necrotic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "minor_vulnerable_necrotic", get_locale_text("i18n_enemy_normal.void_wanderer.buff_minor_vulnerable_necrotic"), get_locale_text("i18n_enemy_normal.void_wanderer.buff_minor_vulnerable_necrotic_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_normal.void_wanderer.void_bite", name=enemy.name, dmg=dmg_msg))
        elif intent.type == "void_erosion":
            engine._add_buff_to(run.player, "void_weakness", get_locale_text("i18n_enemy_normal.void_wanderer.buff_void_weakness"), get_locale_text("i18n_enemy_normal.void_wanderer.buff_void_weakness_desc"), 2)
            logs.append(get_locale_text("i18n_enemy_normal.void_wanderer.void_erosion", name=enemy.name))
