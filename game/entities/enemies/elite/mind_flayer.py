from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("夺心魔")
class MindFlayerTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("夺心魔", {})
        intents = cfg.get("intents", [])
        
        has_grappled = any(b.id == "grappled" for b in run.player.buffs)
        
        intents_list = []
        for _ in range(enemy.max_actions):
            if has_grappled:
                if random.random() < 0.7:
                    chosen = next(it for it in intents if it["id"] == "extract_brain")
                else:
                    chosen = next(it for it in intents if it["id"] == "defend")
            else:
                valid_choices = [it for it in intents if it["id"] in ("tentacles", "mind_blast", "defend")]
                chosen = random.choice(valid_choices)
            intents_list.append(EnemyIntentState(
                type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0
            ))
            
        for _ in range(enemy.max_bonus_actions):
            valid_choices = [it for it in intents if it["id"] in ("tentacles", "defend")]
            chosen = random.choice(valid_choices)
            intents_list.append(EnemyIntentState(
                type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1
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
        if intent.type == "tentacles":
            strength = 0
            for b in enemy.buffs:
                if b.id == "strength":
                    strength += b.stacks
            val = intent.val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(p, "grappled", get_locale_text("i18n_enemy_elite_c.grappled_name"), get_locale_text("i18n_enemy_elite_c.grappled_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_c.mind_flayer_tentacles_log", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "mind_blast":
            strength = 0
            for b in enemy.buffs:
                if b.id == "strength":
                    strength += b.stacks
            val = intent.val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(p, "stun", get_locale_text("i18n_enemy_elite_c.stun_name"), get_locale_text("i18n_enemy_elite_c.stun_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_c.mind_blast_log", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "extract_brain":
            has_grappled = any(b.id == "grappled" for b in p.buffs)
            if has_grappled:
                dmg_val = 25
                msg_prefix = get_locale_text("i18n_enemy_elite_c.extract_brain_grappled_prefix", name=enemy.name)
            else:
                dmg_val = 8
                msg_prefix = get_locale_text("i18n_enemy_elite_c.extract_brain_normal_prefix", name=enemy.name)
            
            strength = 0
            for b in enemy.buffs:
                if b.id == "strength":
                    strength += b.stacks
            val = dmg_val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="piercing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"{msg_prefix}{dmg_msg}")
        elif intent.type == "defend":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_c.mind_flayer_defend_log", name=enemy.name, val=intent.val))


@register_enemy("夺心魔奥术师")
class MindFlayerArcanistTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("夺心魔奥术师", {})
        intents = cfg.get("intents", [])
        
        has_grappled = any(b.id == "grappled" for b in run.player.buffs)
        
        intents_list = []
        for _ in range(enemy.max_actions):
            if has_grappled:
                if random.random() < 0.6:
                    chosen = next(it for it in intents if it["id"] == "extract_brain")
                else:
                    chosen = random.choice([it for it in intents if it["id"] in ("magic_missile", "shield_spell")])
            else:
                valid_choices = [it for it in intents if it["id"] in ("tentacles", "mind_blast", "magic_missile", "shield_spell")]
                chosen = random.choice(valid_choices)
            intents_list.append(EnemyIntentState(
                type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0
            ))
            
        for _ in range(enemy.max_bonus_actions):
            valid_choices = [it for it in intents if it["id"] in ("tentacles", "shield_spell")]
            chosen = random.choice(valid_choices)
            intents_list.append(EnemyIntentState(
                type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1
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
        if intent.type == "tentacles":
            strength = 0
            for b in enemy.buffs:
                if b.id == "strength":
                    strength += b.stacks
            val = intent.val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(p, "grappled", get_locale_text("i18n_enemy_elite_c.grappled_name"), get_locale_text("i18n_enemy_elite_c.grappled_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_c.arcanist_tentacles_log", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "mind_blast":
            strength = 0
            for b in enemy.buffs:
                if b.id == "strength":
                    strength += b.stacks
            val = intent.val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(p, "stun", get_locale_text("i18n_enemy_elite_c.stun_name"), get_locale_text("i18n_enemy_elite_c.stun_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_c.mind_blast_log", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "extract_brain":
            has_grappled = any(b.id == "grappled" for b in p.buffs)
            if has_grappled:
                dmg_val = 25
                msg_prefix = get_locale_text("i18n_enemy_elite_c.extract_brain_grappled_prefix", name=enemy.name)
            else:
                dmg_val = 8
                msg_prefix = get_locale_text("i18n_enemy_elite_c.extract_brain_normal_prefix", name=enemy.name)
            
            strength = 0
            for b in enemy.buffs:
                if b.id == "strength":
                    strength += b.stacks
            val = dmg_val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="piercing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"{msg_prefix}{dmg_msg}")
        elif intent.type == "magic_missile":
            strength = 0
            for b in enemy.buffs:
                if b.id == "strength":
                    strength += b.stacks
            single_val = intent.val + strength
            missile_logs = []
            for _ in range(3):
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", single_val, source=f"enemy:{enemy.name}", damage_type="force")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    missile_logs.append(after_logs.pop())
            logs.append(get_locale_text("i18n_enemy_elite_c.arcanist_magic_missile_log", name=enemy.name, missiles=', '.join(missile_logs)))
        elif intent.type == "shield_spell":
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
                logs.append(get_locale_text("i18n_enemy_elite_c.arcanist_shield_clear_log", name=enemy.name, val=intent.val, buff_name=to_remove.name))
            else:
                logs.append(get_locale_text("i18n_enemy_elite_c.arcanist_shield_log", name=enemy.name, val=intent.val))
