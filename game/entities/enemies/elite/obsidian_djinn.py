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
        intents_list = []
        for _ in range(enemy.actions):
            chosen = random.choice(intents)
            intents_list.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.bonus_actions):
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
        strength = 0
        if getattr(enemy, "buffs", None):
            for buff in enemy.buffs:
                if buff.id == "strength":
                    strength += buff.stacks
        val = intent.val + strength
        if intent.type == "quake":
            self._perform_attack(run, engine, enemy, val, logs, damage_type="bludgeoning")
            engine._add_buff_to(run.player, "drain_ba", get_locale_text("i18n_enemy_elite_c.drain_ba_name"), get_locale_text("i18n_enemy_elite_c.drain_ba_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_c.obsidian_djinn_quake_log", name=enemy.name))
        elif intent.type == "defend":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_c.obsidian_djinn_defend_log", name=enemy.name, val=intent.val))
