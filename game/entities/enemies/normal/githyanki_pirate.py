from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("吉斯洋基海盗")
class GithyankiPirateTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("吉斯洋基海盗", {})
        intents = cfg.get("intents", [])
        
        extra_actions = 0
        speed_buff = next((b for b in enemy.buffs if b.id == "astral_speed"), None)
        if speed_buff:
            extra_actions = speed_buff.stacks
            enemy.buffs.remove(speed_buff)
            enemy.actions += extra_actions
            
        intents_list = []
        for _ in range(enemy.max_actions + extra_actions):
            chosen = random.choice(intents)
            intents_list.append(EnemyIntentState(
                type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0
            ))
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
        from ....entities.enemies.trash_talk_actions import try_trash_talk
        try_trash_talk(run, enemy, logs)
        p = run.player
        if intent.type == "silver_sword":
            strength = 0
            for b in enemy.buffs:
                if b.id == "strength":
                    strength += b.stacks
            val = intent.val + strength
            
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="slashing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            
            extra_msg = ""
            if p.shield > 0:
                extra_before = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", 4, source=f"enemy:{enemy.name}", damage_type="force")
                extra_after = run.node_data.get("battle_logs", [])
                if len(extra_after) > extra_before:
                    extra_msg = get_locale_text("i18n_enemy_normal.githyanki_pirate.silver_sword_extra", dmg=extra_after.pop())
            
            logs.append(get_locale_text("i18n_enemy_normal.githyanki_pirate.silver_sword", name=enemy.name, dmg=dmg_msg, extra=extra_msg))
        elif intent.type == "astral_step":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(enemy, "astral_speed", get_locale_text("i18n_enemy_normal.githyanki_pirate.buff_astral_speed"), get_locale_text("i18n_enemy_normal.githyanki_pirate.buff_astral_speed_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_normal.githyanki_pirate.astral_step", name=enemy.name, val=intent.val))
        elif intent.type == "parry":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_normal.githyanki_pirate.parry", name=enemy.name, val=intent.val))
