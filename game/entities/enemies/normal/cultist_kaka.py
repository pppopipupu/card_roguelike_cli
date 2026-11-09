from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("邪教徒咔咔")
class CultistKakaTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        cfg = ENEMY_CONFIG.get("邪教徒咔咔", {})
        intents = cfg.get("intents", [])
        has_ritual = any(b.id == "ritual" for b in enemy.buffs)
        if not has_ritual:
            caw_intent = next(it for it in intents if it["id"] == "caw")
            return [EnemyIntentState(type=caw_intent["id"], val=caw_intent["val"], desc=caw_intent["desc"], cost_a=1, cost_ba=0)]
        else:
            peck_intent = next(it for it in intents if it["id"] == "peck")
            return [EnemyIntentState(type=peck_intent["id"], val=peck_intent["val"], desc=peck_intent["desc"], cost_a=1, cost_ba=0)]

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
        from ....entities.enemies.trash_talk_actions import try_trash_talk
        try_trash_talk(run, enemy, logs)
        if intent.type == "caw":
            engine._add_buff_to(enemy, "ritual", get_locale_text("i18n_enemy_normal.cultist_kaka.buff_ritual"), get_locale_text("i18n_enemy_normal.cultist_kaka.buff_ritual_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_normal.cultist_kaka.ritual_start", name=enemy.name))
        elif intent.type == "peck":
            self._perform_attack(run, engine, enemy, intent.val, logs, damage_type="piercing")
