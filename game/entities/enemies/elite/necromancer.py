from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("亡灵巫师")
class NecromancerTemplate(EnemyTemplate):
    def on_battle_start(self, run, enemy, engine):
        engine._add_buff_to(enemy, "soul_phylactery_passive", get_locale_text("i18n_buffs.soul_phylactery_passive_name"), get_locale_text("i18n_buffs.soul_phylactery_passive_desc"), 1)

    def _skeleton_name(self, cfg) -> str:
        return cfg.get("summon_skeleton", {}).get("name", get_locale_text("i18n_enemy_misc.skeleton_minion.name"))

    def _living_skeletons(self, run, skeleton_name: str) -> List:
        return [e for e in run.enemies if e.hp > 0 and skeleton_name and e.name.startswith(skeleton_name)]

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("亡灵巫师", {})
        intents = cfg.get("intents", [])
        skeleton_name = self._skeleton_name(cfg)
        a_ids = ["shadow_bolt"]
        if len(self._living_skeletons(run, skeleton_name)) < 2:
            a_ids.append("raise_dead")
        a_pool = [it for it in intents if it.get("id") in a_ids] or intents
        ba_pool = [it for it in intents if it.get("id") in ("soul_drain", "bone_ward")] or intents
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
        cfg = ENEMY_CONFIG.get("亡灵巫师", {})
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength
        if intent.type == "shadow_bolt":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="necrotic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "minor_vulnerable_necrotic", get_locale_text("i18n_enemy_elite_c.necrotic_vulnerable_name"), get_locale_text("i18n_enemy_elite_c.necrotic_vulnerable_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_c.necromancer_shadow_bolt_log", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "raise_dead":
            from ....models.state import EnemyState, EnemyIntentState
            sh = cfg.get("summon_skeleton", {})
            slash_val = sh.get("val", 4)
            new_skeleton = EnemyState(
                name=sh.get("name", get_locale_text("i18n_enemy_misc.skeleton_minion.name")),
                hp=sh.get("hp", 16),
                max_hp=sh.get("max_hp", 16),
                shield=0,
                actions=1,
                bonus_actions=0,
                is_summon=True,
                max_actions=1,
                max_bonus_actions=0,
                intents=[EnemyIntentState(
                    type="bone_slash",
                    val=slash_val,
                    desc=get_locale_text("i18n_enemy_misc.skeleton_minion.intent_bone_slash", val=slash_val),
                    cost_a=1,
                    cost_ba=0
                )]
            )
            run.enemies.append(new_skeleton)
            logs.append(get_locale_text("i18n_enemy_elite_c.necromancer_raise_dead_log", name=enemy.name))
        elif intent.type == "soul_drain":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="necrotic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            heal = cfg.get("soul_drain_heal", 8)
            self_idx = next((i for i, e in enumerate(run.enemies) if e is enemy), -1)
            if self_idx >= 0:
                engine._heal_target(run, f"e{self_idx+1}", heal)
            logs.append(get_locale_text("i18n_enemy_elite_a.necromancer.soul_drain", name=enemy.name, dmg_msg=dmg_msg, heal=heal))
        elif intent.type == "bone_ward":
            for idx, e in enumerate(run.enemies):
                if e.hp > 0:
                    engine._gain_shield(run, f"e{idx+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_c.necromancer_bone_ward_log", name=enemy.name, val=intent.val))
