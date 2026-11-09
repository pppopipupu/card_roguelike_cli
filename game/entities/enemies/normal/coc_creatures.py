from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("深潜者")
class DeepOneTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("深潜者", {})
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
        if intent.type == "tsunami_strike":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            p = run.player
            extra_msg = ""
            if p.shield > 0:
                before_len = len(run.node_data.get("battle_logs", []))
                engine.combat_resolver.damage_target(run, "p0", 3, source=f"enemy:{enemy.name}", damage_type="true")
                after_logs = run.node_data.get("battle_logs", [])
                true_dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
                extra_msg = get_locale_text("i18n_enemy_normal.deep_one.tsunami_extra", dmg=true_dmg_msg)
            
            before_len = len(run.node_data.get("battle_logs", []))
            self._perform_attack(run, engine, enemy, final_dmg, logs)
            if extra_msg and logs:
                logs[-1] += extra_msg
        elif intent.type == "defend":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_normal.deep_one.defend", name=enemy.name, val=intent.val))

@register_enemy("食尸鬼")
class GhoulTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("食尸鬼", {})
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
        if intent.type == "rot_bite":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            self._perform_attack(run, engine, enemy, final_dmg, logs)
            engine._add_buff_to(run.player, "minor_vulnerable", get_locale_text("i18n_enemy_normal.ghoul.buff_minor_vulnerable"), get_locale_text("i18n_enemy_normal.ghoul.buff_minor_vulnerable_desc"), 1)
            if logs:
                logs[-1] += get_locale_text("i18n_enemy_normal.ghoul.rot_bite_suffix")
        elif intent.type == "claw_slash":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            self._perform_attack(run, engine, enemy, final_dmg, logs)

@register_enemy("夜魇")
class NightgauntTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("夜魇", {})
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
        if intent.type == "tickle_claw":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine.combat_resolver.damage_target(run, "p0", final_dmg, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_normal.nightgaunt.tickle_claw", name=enemy.name, dmg=dmg_msg))
        elif intent.type == "void_glide":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(enemy, "astral_speed", get_locale_text("i18n_enemy_normal.nightgaunt.buff_astral_speed"), get_locale_text("i18n_enemy_normal.nightgaunt.buff_astral_speed_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_normal.nightgaunt.void_glide", name=enemy.name, val=intent.val))

@register_enemy("夏塔克鸟")
class ShantakTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("夏塔克鸟", {})
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
        if intent.type == "wind_buffet":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine.combat_resolver.damage_target(run, "p0", final_dmg, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_normal.shantak.wind_buffet", name=enemy.name, dmg=dmg_msg))
        elif intent.type == "shriek":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine.combat_resolver.damage_target(run, "p0", final_dmg, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            
            engine._add_buff_to(run.player, "discard_next_turn", get_locale_text("i18n_enemy_normal.shantak.buff_discard_next_turn"), get_locale_text("i18n_enemy_normal.shantak.buff_discard_next_turn_desc"), 1)
            discard_msg = get_locale_text("i18n_enemy_normal.shantak.shriek_discard")

            logs.append(get_locale_text("i18n_enemy_normal.shantak.shriek", name=enemy.name, dmg=dmg_msg, discard=discard_msg))

@register_enemy("空鬼")
class DimensionalShamblerTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("空鬼", {})
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
        if intent.type == "phase_strike":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine.combat_resolver.damage_target(run, "p0", final_dmg, source=f"enemy:{enemy.name}", damage_type="true")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_normal.shambler.phase_strike", name=enemy.name, dmg=dmg_msg))
        elif intent.type == "dimensional_shift":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_normal.shambler.dimensional_shift", name=enemy.name, val=intent.val))
