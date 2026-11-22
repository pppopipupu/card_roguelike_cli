from typing import List, Optional
from ..base import EnemyTemplate, register_enemy
from ....data.enemies.enemy_data import ENEMY_CONFIG
from ....data.text.locale_data import get_locale_text

@register_enemy("虚空潜影")
class VoidShadeTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        from ....models.state import EnemyIntentState
        import random
        intents = ENEMY_CONFIG.get("虚空潜影", {}).get("intents", [])
        chosen = random.choice(intents)
        return [EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0)]

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        if logs is None:
            logs = []
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        if intent.type == "void_strike":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val + strength, source=f"enemy:{enemy.name}", damage_type="necrotic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_misc.void_shade.void_strike", name=enemy.name, dmg_msg=dmg_msg))
