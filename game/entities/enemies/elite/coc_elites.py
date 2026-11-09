from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("冷蛛")
class LengSpiderTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("冷蛛", {})
        intents = cfg.get("intents", [])
        res = []
        for _ in range(enemy.max_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.max_bonus_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1))
        return res

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
        if intent.type == "venom_bite":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            self._perform_attack(run, engine, enemy, final_dmg, logs)
            engine._add_buff_to(run.player, "minor_vulnerable", get_locale_text("i18n_enemy_elite_a.common.minor_vulnerable_name"), get_locale_text("i18n_enemy_elite_a.common.minor_vulnerable_desc"), 1)
            if logs:
                logs[-1] += get_locale_text("i18n_enemy_elite_a.leng_spider.venom_bite_suffix")
        elif intent.type == "web_trap":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(run.player, "discard_next_turn", get_locale_text("i18n_enemy_elite_a.common.discard_next_turn_name"), get_locale_text("i18n_enemy_elite_a.common.discard_next_turn_desc"), 1)
            discard_msg = get_locale_text("i18n_enemy_elite_a.leng_spider.discard_suffix")
            logs.append(get_locale_text("i18n_enemy_elite_a.leng_spider.web_trap", name=enemy.name, val=intent.val, discard_msg=discard_msg))
        elif intent.type == "spider_jump":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            self._perform_attack(run, engine, enemy, final_dmg, logs)

@register_enemy("米·戈")
class MigoTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("米·戈", {})
        intents = cfg.get("intents", [])
        res = []
        for _ in range(enemy.max_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.max_bonus_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1))
        return res

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
        if intent.type == "electric_probe":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine.combat_resolver.damage_target(run, "p0", final_dmg, source=f"enemy:{enemy.name}", damage_type="lightning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            run.node_data["draw_penalty_next_turn"] = run.node_data.get("draw_penalty_next_turn", 0) + 1
            logs.append(get_locale_text("i18n_enemy_elite_a.migo.electric_probe", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "brain_case":
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
            logs.append(get_locale_text("i18n_enemy_elite_a.migo.brain_case", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "bio_shield":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            negatives = {"stun", "weak", "vulnerable"}
            to_remove = None
            for b in enemy.buffs:
                if b.id in negatives or "vulnerable" in b.id or "weak" in b.id:
                    to_remove = b
                    break
            if to_remove:
                enemy.buffs.remove(to_remove)
                if to_remove.id == "stun":
                    engine._sync_enemy_intents(enemy)
                logs.append(get_locale_text("i18n_enemy_elite_a.migo.bio_shield_purge", name=enemy.name, val=intent.val, buff=to_remove.name))
            else:
                logs.append(get_locale_text("i18n_enemy_elite_a.migo.bio_shield", name=enemy.name, val=intent.val))

@register_enemy("修格斯")
class ShoggothTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("修格斯", {})
        intents = cfg.get("intents", [])
        res = []
        for _ in range(enemy.max_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.max_bonus_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1))
        return res

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
        if intent.type == "acid_splash":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine.combat_resolver.damage_target(run, "p0", final_dmg, source=f"enemy:{enemy.name}", damage_type="acid")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "drain_ba", get_locale_text("i18n_enemy_elite_a.common.void_entangle_name"), get_locale_text("i18n_enemy_elite_a.common.void_entangle_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_a.shoggoth.acid_splash", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "slime_cocoon":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_a.shoggoth.slime_cocoon", name=enemy.name, val=intent.val))
        elif intent.type == "ooze_strike":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            self._perform_attack(run, engine, enemy, final_dmg, logs)

@register_enemy("星之精")
class StarVampireTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("星之精", {})
        intents = cfg.get("intents", [])
        res = []
        for _ in range(enemy.max_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.max_bonus_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1))
        return res

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
        if intent.type == "blood_drain":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine.combat_resolver.damage_target(run, "p0", final_dmg, source=f"enemy:{enemy.name}", damage_type="necrotic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            heal = 8
            if enemy in run.enemies:
                engine._heal_target(run, f"e{run.enemies.index(enemy)+1}", heal)
            logs.append(get_locale_text("i18n_enemy_elite_a.star_vampire.blood_drain", name=enemy.name, dmg_msg=dmg_msg, heal=heal))
        elif intent.type == "invisible_stalker":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_elite_a.common.strength_name"), get_locale_text("i18n_enemy_elite_a.common.strength_desc"), 4)
            logs.append(get_locale_text("i18n_enemy_elite_a.star_vampire.invisible_stalker", name=enemy.name, val=intent.val))
        elif intent.type == "talon_rend":
            val = intent.val
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            final_dmg = val + strength
            self._perform_attack(run, engine, enemy, final_dmg, logs)

@register_enemy("克苏鲁之星之眷族")
class StarspawnOfCthulhuTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("克苏鲁之星之眷族", {})
        intents = cfg.get("intents", [])
        res = []
        for _ in range(enemy.max_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.max_bonus_actions):
            chosen = random.choice(intents)
            res.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1))
        return res

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
        if intent.type == "cosmic_blast":
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
            logs.append(get_locale_text("i18n_enemy_elite_a.starspawn_of_cthulhu.cosmic_blast", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "cthulhu_gaze":
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
            run.node_data["drain_a"] = True
            logs.append(get_locale_text("i18n_enemy_elite_a.starspawn_of_cthulhu.cthulhu_gaze", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "star_regeneration":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            heal = 10
            if enemy in run.enemies:
                engine._heal_target(run, f"e{run.enemies.index(enemy)+1}", heal)
            logs.append(get_locale_text("i18n_enemy_elite_a.starspawn_of_cthulhu.star_regeneration", name=enemy.name, val=intent.val, heal=heal))
