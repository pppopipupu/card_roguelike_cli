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

@register_enemy("幽灵法师")
class GhostMageTemplate(EnemyTemplate):
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
        if intent.type == "soul_frost":
            entry = _intent_config(self.name, intent.type)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val + strength, source=f"enemy:{enemy.name}", damage_type="cold")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(p, "mana_leak", get_locale_text("i18n_enemy_normal.ghost_mage.buff_mana_leak"), get_locale_text("i18n_enemy_normal.ghost_mage.buff_mana_leak_desc"), entry.get("mana_leak", 1))
            logs.append(get_locale_text("i18n_enemy_normal.ghost_mage.soul_frost", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "ethereal_veil":
            entry = _intent_config(self.name, intent.type)
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_normal.ghost_mage.buff_strength"), get_locale_text("i18n_enemy_normal.ghost_mage.buff_strength_desc"), entry.get("strength", 1))
            logs.append(get_locale_text("i18n_enemy_normal.ghost_mage.ethereal_veil", name=enemy.name, val=intent.val))

@register_enemy("剧毒蜘蛛")
class VenomSpiderTemplate(EnemyTemplate):
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
        if intent.type == "neuro_fang":
            entry = _intent_config(self.name, intent.type)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val + strength, source=f"enemy:{enemy.name}", damage_type="piercing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(p, "poison", get_locale_text("i18n_enemy_normal.venom_spider.buff_poison"), get_locale_text("i18n_enemy_normal.venom_spider.buff_poison_desc"), entry.get("poison", 3))
            logs.append(get_locale_text("i18n_enemy_normal.venom_spider.neuro_fang", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "sticky_silk":
            entry = _intent_config(self.name, intent.type)
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(p, "drain_ba", get_locale_text("i18n_enemy_normal.venom_spider.buff_drain_ba"), get_locale_text("i18n_enemy_normal.venom_spider.buff_drain_ba_desc"), entry.get("drain_ba", 1))
            logs.append(get_locale_text("i18n_enemy_normal.venom_spider.sticky_silk", name=enemy.name, val=intent.val))

@register_enemy("幻梦境潜猎者")
class DreamlandsProwlerTemplate(EnemyTemplate):
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
        if intent.type == "dream_pilfer":
            import random
            from ....entities import ALL_CARDS
            entry = _intent_config(self.name, intent.type)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val + strength, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            candidates = []
            for c_state in p.hand:
                card = ALL_CARDS.get(c_state)
                if card is not None and getattr(card, "type", "") != "curse":
                    candidates.append(c_state)
            if candidates:
                target_state = random.choice(candidates)
                target_state.fragile = max(getattr(target_state, "fragile", 0), entry.get("fragile", 1))
                logs.append(get_locale_text("i18n_enemy_normal.dreamlands_prowler.dream_pilfer", name=enemy.name, dmg_msg=dmg_msg))
            else:
                logs.append(get_locale_text("i18n_enemy_normal.dreamlands_prowler.dream_pilfer_no_target", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "shadow_pounce":
            entry = _intent_config(self.name, intent.type)
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            has_fragile = any(getattr(c_state, "fragile", 0) > 0 for c_state in p.hand)
            if has_fragile:
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", entry.get("extra_damage", 6) + strength, source=f"enemy:{enemy.name}", damage_type="piercing")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
                engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_normal.dreamlands_prowler.buff_strength"), get_locale_text("i18n_enemy_normal.dreamlands_prowler.buff_strength_desc"), entry.get("strength", 1))
                logs.append(get_locale_text("i18n_enemy_normal.dreamlands_prowler.shadow_pounce", name=enemy.name, dmg_msg=dmg_msg))
            else:
                logs.append(get_locale_text("i18n_enemy_normal.dreamlands_prowler.shadow_pounce_guard", name=enemy.name, val=intent.val))
