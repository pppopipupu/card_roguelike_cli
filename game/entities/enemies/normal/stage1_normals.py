from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

def _intent_config(enemy_name: str, intent_type: str) -> dict:
    cfg = ENEMY_CONFIG.get(enemy_name, {})
    for entry in cfg.get("intents", []):
        if entry.get("id") == intent_type:
            return entry
    return {}

@register_enemy("地精突袭者")
class GoblinRaiderTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        intents = ENEMY_CONFIG.get(self.name, {}).get("intents", [])
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
        from ....entities.enemies.trash_talk_actions import try_trash_talk
        try_trash_talk(run, enemy, logs)
        p = run.player
        strength = 0
        for b in getattr(enemy, "buffs", []):
            if b.id == "strength":
                strength += b.stacks
        if intent.type == "raid_stab":
            entry = _intent_config(self.name, intent.type)
            had_shield = getattr(p, "shield", 0) > 0
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val + strength, source=f"enemy:{enemy.name}", damage_type="piercing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            bleed_suffix = ""
            if not had_shield:
                engine._add_buff_to(p, "bleed", get_locale_text("i18n_enemy_normal.goblin_raider.buff_bleed"), get_locale_text("i18n_enemy_normal.goblin_raider.buff_bleed_desc"), entry.get("bleed", 2))
                bleed_suffix = get_locale_text("i18n_enemy_normal.goblin_raider.bleed_suffix")
            logs.append(get_locale_text("i18n_enemy_normal.goblin_raider.raid_stab", name=enemy.name, dmg_msg=dmg_msg, bleed_suffix=bleed_suffix))
        elif intent.type == "loot_guard":
            entry = _intent_config(self.name, intent.type)
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_normal.goblin_raider.buff_strength"), get_locale_text("i18n_enemy_normal.goblin_raider.buff_strength_desc"), entry.get("strength", 1))
            logs.append(get_locale_text("i18n_enemy_normal.goblin_raider.loot_guard", name=enemy.name, val=intent.val))

@register_enemy("堕落学徒")
class CorruptApprenticeTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        intents = ENEMY_CONFIG.get(self.name, {}).get("intents", [])
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
        from ....entities.enemies.trash_talk_actions import try_trash_talk
        try_trash_talk(run, enemy, logs)
        p = run.player
        strength = 0
        for b in getattr(enemy, "buffs", []):
            if b.id == "strength":
                strength += b.stacks
        if intent.type == "cinder_bolt":
            entry = _intent_config(self.name, intent.type)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val + strength, source=f"enemy:{enemy.name}", damage_type="fire")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(p, "burning", get_locale_text("i18n_enemy_normal.corrupt_apprentice.buff_burning"), get_locale_text("i18n_enemy_normal.corrupt_apprentice.buff_burning_desc"), entry.get("burning", 2))
            logs.append(get_locale_text("i18n_enemy_normal.corrupt_apprentice.cinder_bolt", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "dark_chant":
            entry = _intent_config(self.name, intent.type)
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(p, "void_weakness", get_locale_text("i18n_enemy_normal.corrupt_apprentice.buff_void_weakness"), get_locale_text("i18n_enemy_normal.corrupt_apprentice.buff_void_weakness_desc"), entry.get("void_weakness", 1))
            logs.append(get_locale_text("i18n_enemy_normal.corrupt_apprentice.dark_chant", name=enemy.name, val=intent.val))

@register_enemy("纳奇姆")
class NazeemTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        intents = ENEMY_CONFIG.get(self.name, {}).get("intents", [])
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
        from ....entities.enemies.trash_talk_actions import try_trash_talk
        try_trash_talk(run, enemy, logs)
        p = run.player
        strength = 0
        for b in getattr(enemy, "buffs", []):
            if b.id == "strength":
                strength += b.stacks
        if intent.type == "vicious_mockery":
            entry = _intent_config(self.name, intent.type)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val + strength, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(p, "weak", get_locale_text("i18n_enemy_normal.na_qi_mu.buff_weak"), get_locale_text("i18n_enemy_normal.na_qi_mu.buff_weak_desc"), entry.get("weak", 1))
            logs.append(get_locale_text("i18n_enemy_normal.na_qi_mu.vicious_mockery", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "self_motivation":
            entry = _intent_config(self.name, intent.type)
            heal = entry.get("heal", entry.get("val", intent.val))
            shield = entry.get("shield", 5)
            if enemy in run.enemies:
                enemy_key = f"e{run.enemies.index(enemy)+1}"
                engine._heal_target(run, enemy_key, heal)
                engine._gain_shield(run, enemy_key, shield)
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_normal.na_qi_mu.buff_strength"), get_locale_text("i18n_enemy_normal.na_qi_mu.buff_strength_desc"), entry.get("strength", 1))
            logs.append(get_locale_text("i18n_enemy_normal.na_qi_mu.self_motivation", name=enemy.name, heal=heal, val=shield))
