from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("幽灵大魔法师")
class GhostArchmageTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("幽灵大魔法师", {})
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
        p = run.player
        import random
        if intent.type == "spell_burst":
            self._perform_attack(run, engine, enemy, intent.val, logs)
        elif intent.type == "mana_drain":
            self._perform_attack(run, engine, enemy, intent.val, logs)
            engine._add_buff_to(run.player, "discard_next_turn", get_locale_text("i18n_enemy_elite_b.common.discard_next_turn_name"), get_locale_text("i18n_enemy_elite_b.common.discard_next_turn_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_b.ghost_archmage.siphon", name=enemy.name))
