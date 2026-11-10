from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("雷影魔仆")
class ThunderOrbTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        key = f"thunder_orb_turn:{enemy.name}"
        turn = run.node_data.get(key, 0)
        run.node_data[key] = turn + 1
        intents = ENEMY_CONFIG.get("雷影魔仆", {}).get("intents", [])
        wanted = "lightning_strike" if turn % 2 == 0 else "charge"
        chosen = next((it for it in intents if it["id"] == wanted), None)
        if chosen is None:
            return super().roll_intents(run, engine, enemy)
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
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        if intent.type == "lightning_strike":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val + strength, source=f"enemy:{enemy.name}", damage_type="lightning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "shock", get_locale_text("i18n_enemy_misc.common.shock_name"), get_locale_text("i18n_enemy_misc.common.shock_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_misc.thunder_orb.lightning_strike", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "charge":
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_misc.common.strength_name"), get_locale_text("i18n_enemy_misc.common.strength_desc"), intent.val)
            logs.append(get_locale_text("i18n_enemy_misc.thunder_orb.charge", name=enemy.name))
        else:
            super().execute_intent(run, engine, enemy, intent, logs)
