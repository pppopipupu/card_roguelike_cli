from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("黑曜石巨灵")
class ObsidianDjinnTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("黑曜石巨灵", {})
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
        if intent.type == "quake":
            self._perform_attack(run, engine, enemy, intent.val, logs)
            engine._add_buff_to(run.player, "drain_ba", get_locale_text("i18n_enemy_elite_c.drain_ba_name"), get_locale_text("i18n_enemy_elite_c.drain_ba_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_c.obsidian_djinn_quake_log", name=enemy.name))
        elif intent.type == "defend":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_c.obsidian_djinn_defend_log", name=enemy.name, val=intent.val))
