from typing import List, Optional
from ..base import EnemyTemplate, register_enemy
from ....data.locale_data import get_locale_text

@register_enemy("星界幼犬")
class AstralPuppyTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        from ....models.state import EnemyIntentState
        return [EnemyIntentState(type="star_bite", val=3, desc=get_locale_text("i18n_enemy_misc.astral_puppy.intent_star_bite"), cost_a=1, cost_ba=0)]

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        if logs is None:
            logs = []
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength
        before_len = len(run.node_data.get("battle_logs", []))
        engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
        after_logs = run.node_data.get("battle_logs", [])
        dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
        logs.append(get_locale_text("i18n_enemy_misc.astral_puppy.bite", name=enemy.name, dmg_msg=dmg_msg))
