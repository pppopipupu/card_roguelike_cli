from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("末日守卫")
class DoomguardTemplate(EnemyTemplate):
    def on_battle_start(self, run, enemy, engine):
        engine._add_buff_to(enemy, "doom_furnace_passive", get_locale_text("i18n_buffs.doom_furnace_passive_name"), get_locale_text("i18n_buffs.doom_furnace_passive_desc"), 1)

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("末日守卫", {})
        intents = cfg.get("intents", [])
        a_pool = [it for it in intents if it.get("id") in ("doom_strike", "hellfire")] or intents
        ba_pool = [it for it in intents if it.get("id") == "sacrifice"] or intents
        intents_list = []
        for _ in range(enemy.actions):
            chosen = random.choice(a_pool)
            intents_list.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.bonus_actions):
            chosen = random.choice(ba_pool)
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
        cfg = ENEMY_CONFIG.get("末日守卫", {})
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength
        if intent.type == "doom_strike":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="piercing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "minor_vulnerable_slashing", get_locale_text("i18n_enemy_elite_a.common.slashing_vulnerable_name"), get_locale_text("i18n_enemy_elite_a.common.slashing_vulnerable_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_a.doomguard.doom_strike", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "hellfire":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="fire")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            for grid in list(run.player.minions.keys()):
                before_minion = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{grid}", val, source=f"enemy:{enemy.name}", damage_type="fire")
                after_minion = run.node_data.get("battle_logs", [])
                if len(after_minion) > before_minion:
                    dmg_msg = f"{dmg_msg}{after_minion.pop()}"
            engine._add_buff_to(run.player, "burning", get_locale_text("i18n_battle_core.buff_burning_name"), get_locale_text("i18n_battle_core.buff_burning_desc"), cfg.get("hellfire_burn", 2))
            logs.append(get_locale_text("i18n_enemy_elite_a.doomguard.hellfire", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "sacrifice":
            self_idx = next((i for i, e in enumerate(run.enemies) if e is enemy), -1)
            self_dmg = cfg.get("sacrifice_self_damage", 4)
            strength_gain = cfg.get("sacrifice_strength", 2)
            if self_idx >= 0:
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"e{self_idx+1}", self_dmg, source=f"enemy:{enemy.name}", damage_type="true")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    after_logs.pop()
            if any(e is enemy for e in run.enemies):
                self_idx = next(i for i, e in enumerate(run.enemies) if e is enemy)
                engine._gain_shield(run, f"e{self_idx+1}", intent.val)
                engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_elite_a.common.strength_name"), get_locale_text("i18n_enemy_elite_a.common.strength_desc"), strength_gain)
            logs.append(get_locale_text("i18n_enemy_elite_a.doomguard.sacrifice", name=enemy.name, val=intent.val, strength=strength_gain, self_dmg=self_dmg))
