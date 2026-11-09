from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("狂暴兽王")
class BeastMasterTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("狂暴兽王", {})
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
        if intent.type == "attack":
            self._perform_attack(run, engine, enemy, intent.val, logs)
        elif intent.type == "defend":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_a.beast_master.defend", name=enemy.name, val=intent.val))
        elif intent.type == "summon_beast":
            from ....models.state import EnemyState, EnemyIntentState
            cfg = ENEMY_CONFIG.get("狂暴兽王", {})
            sh = cfg.get("summon_hound", {})
            new_hound = EnemyState(
                name=sh.get("name", get_locale_text("i18n_enemy_elite_a.beast_master.hound_name")),
                hp=sh.get("hp", 8),
                max_hp=sh.get("max_hp", 8),
                shield=0,
                actions=1,
                bonus_actions=0,
                is_summon=True,
                max_actions=1,
                max_bonus_actions=0,
                intents=[EnemyIntentState(
                    type="attack",
                    val=sh.get("intent_val", 2),
                    desc=sh.get("intent_desc", get_locale_text("i18n_enemy_elite_a.beast_master.hound_intent_desc")),
                    cost_a=1,
                    cost_ba=0
                )]
            )
            run.enemies.append(new_hound)
            logs.append(get_locale_text("i18n_enemy_elite_a.beast_master.summon_beast", name=enemy.name))
