from typing import List, Optional
from ..base import EnemyTemplate, register_enemy
from ....data.enemies.enemy_data import ENEMY_CONFIG
from ....data.text.locale_data import get_locale_text

@register_enemy("狂暴魔仆")
class DemonServantTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("狂暴魔仆", {})
        intents = cfg.get("intents", [])
        chosen = random.choice(intents)
        return [EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0)]

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        if logs is None:
            logs = []
        if intent.type == "rage_bite":
            val = intent.val
            if enemy.hp < enemy.max_hp // 2:
                val *= 2
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val
            self._perform_attack(run, engine, enemy, final_dmg, logs, damage_type="piercing")
        elif intent.type == "evil_gaze":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_normal.demon_servant.evil_gaze", name=enemy.name, val=intent.val))
