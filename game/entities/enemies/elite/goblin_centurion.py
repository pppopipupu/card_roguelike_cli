from typing import List, Optional
from ..base import EnemyTemplate, register_enemy
from ....data.enemies.enemy_data import ENEMY_CONFIG
from ....data.text.locale_data import get_locale_text

@register_enemy("地精百夫长")
class GoblinCenturionTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("地精百夫长", {})
        intents = cfg.get("intents", [])
        a_pool = [it for it in intents if it.get("id") in ("heavy_strike", "phalanx_spear")] or intents
        ba_pool = [it for it in intents if it.get("id") in ("defend", "command")] or intents
        intents_list = []
        for _ in range(enemy.actions):
            chosen = random.choice(a_pool)
            intents_list.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.bonus_actions):
            chosen = random.choice(ba_pool)
            intents_list.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        if logs is None:
            logs = []
        cfg = ENEMY_CONFIG.get("地精百夫长", {})
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        if intent.type == "heavy_strike":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val, source=f"enemy:{enemy.name}", damage_type="slashing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "minor_vulnerable_slashing", get_locale_text("i18n_enemy_elite_a.common.slashing_vulnerable_name"), get_locale_text("i18n_enemy_elite_a.common.slashing_vulnerable_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_b.goblin_centurion.heavy_strike", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "phalanx_spear":
            other_count = sum(1 for e in run.enemies if e is not enemy and e.hp > 0)
            dmg = intent.val + cfg.get("phalanx_bonus", 3) * other_count
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="piercing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_elite_b.goblin_centurion.phalanx_spear", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "defend":
            for idx, e in enumerate(run.enemies):
                if e.hp > 0:
                    engine._gain_shield(run, f"e{idx+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_b.goblin_centurion.defend", name=enemy.name, val=intent.val))
        elif intent.type == "command":
            for e in run.enemies:
                if e.hp > 0:
                    engine._add_buff_to(e, "strength", get_locale_text("i18n_enemy_elite_a.common.strength_name"), get_locale_text("i18n_enemy_elite_a.common.strength_desc"), intent.val)
            engine._add_buff_to(enemy, "astral_speed", get_locale_text("i18n_enemy_elite_b.goblin_centurion.buff_astral_speed"), get_locale_text("i18n_enemy_elite_b.goblin_centurion.buff_astral_speed_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_b.goblin_centurion.command", name=enemy.name))
