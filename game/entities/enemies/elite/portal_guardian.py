from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("传送门守卫者")
class PortalGuardianTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("传送门守卫者", {})
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
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength

        if intent.type == "dimensional_tear":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="true")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_elite_c.portal_guardian_dimensional_tear_log", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "void_shield":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            to_remove = next((b for b in enemy.buffs if b.id == "stun"), None)
            if not to_remove:
                neg_buffs = [b for b in enemy.buffs if b.id in ("minor_vulnerable_slashing", "minor_vulnerable_piercing", "minor_vulnerable_bludgeoning", "minor_vulnerable_fire", "minor_vulnerable_cold", "minor_vulnerable_lightning", "minor_vulnerable_thunder", "minor_vulnerable_necrotic", "minor_vulnerable_acid", "minor_vulnerable_poison", "minor_vulnerable_psychic", "minor_vulnerable_radiant", "minor_vulnerable_force")]
                if neg_buffs:
                    to_remove = neg_buffs[0]
            if to_remove:
                enemy.buffs.remove(to_remove)
                engine._sync_enemy_intents(enemy)
                logs.append(get_locale_text("i18n_enemy_elite_c.portal_guardian_void_shield_clear_log", name=enemy.name, val=intent.val, buff_name=to_remove.name))
            else:
                logs.append(get_locale_text("i18n_enemy_elite_c.portal_guardian_void_shield_log", name=enemy.name, val=intent.val))
        elif intent.type == "portal_instability":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "discard_next_turn", get_locale_text("i18n_enemy_elite_c.discard_next_turn_name"), get_locale_text("i18n_enemy_elite_c.discard_next_turn_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_c.portal_guardian_portal_instability_log", name=enemy.name, dmg_msg=dmg_msg))
