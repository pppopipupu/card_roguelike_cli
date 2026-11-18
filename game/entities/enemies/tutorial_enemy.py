from typing import List, Optional
from .base import EnemyTemplate, register_enemy
from ...data.locale_data import get_locale_text
from ...data.tutorial_data import TUTORIAL_ENEMY


@register_enemy("新手训练木偶")
class TutorialDummyEnemy(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        from ...models.state import EnemyIntentState
        turn = int((getattr(run, "node_data", None) or {}).get("turn_count", 1) or 1)
        if turn % 2 == 1:
            dmg = int(TUTORIAL_ENEMY["atk"])
            return [
                EnemyIntentState(
                    type="attack",
                    val=dmg,
                    desc=get_locale_text("i18n_tutorial.enemy.intent_attack", dmg=dmg),
                    cost_a=1,
                    cost_ba=0,
                )
            ]
        shield = int(TUTORIAL_ENEMY["shield"])
        return [
            EnemyIntentState(
                type="defend",
                val=shield,
                desc=get_locale_text("i18n_tutorial.enemy.intent_defend", shield=shield),
                cost_a=1,
                cost_ba=0,
            )
        ]

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None) -> None:
        if logs is None:
            logs = []
        if intent.type == "attack":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_tutorial.enemy.log_attack", name=enemy.name, dmg_msg=dmg_msg))
            return
        if intent.type == "defend":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy) + 1}", intent.val)
            logs.append(get_locale_text("i18n_tutorial.enemy.log_defend", name=enemy.name, shield=intent.val))
