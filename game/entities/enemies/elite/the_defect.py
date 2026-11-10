from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("故障机器人")
class TheDefectTemplate(EnemyTemplate):
    def _build_intent(self, intents, intent_id, cost_a):
        from ....models.state import EnemyIntentState
        chosen = next((it for it in intents if it.get("id") == intent_id), {})
        return EnemyIntentState(
            type=chosen.get("id", intent_id),
            val=chosen.get("val", 0),
            desc=chosen.get("desc", ""),
            cost_a=cost_a,
            cost_ba=0 if cost_a else 1
        )

    def _pick(self, pool, count):
        import random
        picks = list(pool)
        random.shuffle(picks)
        while len(picks) < count:
            picks.append(random.choice(pool))
        return picks[:count]

    def _damage_logs(self, run, before_len):
        after_logs = run.node_data.get("battle_logs", [])
        msgs = []
        while len(after_logs) > before_len:
            msgs.append(after_logs.pop())
        msgs.reverse()
        return " ".join(msgs)

    def _enemy_target(self, run, enemy):
        if enemy in run.enemies:
            return f"e{run.enemies.index(enemy) + 1}"
        return ""

    def _strength(self, enemy):
        return sum(b.stacks for b in enemy.buffs if b.id == "strength")

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        cfg = ENEMY_CONFIG.get(self.name, {})
        intents = cfg.get("intents", [])
        turns = run.node_data.setdefault("defect_turns", {})
        turn = turns.get(enemy.name, 1)
        turns[enemy.name] = turn + 1
        intents_list = []
        if turn <= 1:
            intents_list.append(self._build_intent(intents, "zap_orb", 1))
            intents_list.append(self._build_intent(intents, "boot_sequence", 0))
            return intents_list
        if turn == 2:
            intents_list.append(self._build_intent(intents, "electrodynamics", 1))
            intents_list.append(self._build_intent(intents, "plasma_awakening", 0))
            return intents_list
        a_pool = [it for it in intents if it.get("id") in ("plasma_beam", "electrodynamics")] or intents
        ba_pool = [it for it in intents if it.get("id") in ("frost_capacitor", "defragment")] or intents
        if enemy.max_actions < 2:
            enemy.max_actions = 2
        if enemy.max_bonus_actions < 2:
            enemy.max_bonus_actions = 2
        for chosen in self._pick(a_pool, enemy.actions):
            intents_list.append(EnemyIntentState(
                type=chosen.get("id", ""),
                val=chosen.get("val", 0),
                desc=chosen.get("desc", ""),
                cost_a=1,
                cost_ba=0
            ))
        for chosen in self._pick(ba_pool, enemy.bonus_actions):
            intents_list.append(EnemyIntentState(
                type=chosen.get("id", ""),
                val=chosen.get("val", 0),
                desc=chosen.get("desc", ""),
                cost_a=0,
                cost_ba=1
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
        p = run.player
        val = intent.val + self._strength(enemy)
        target = self._enemy_target(run, enemy)

        if intent.type == "zap_orb":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="lightning")
            dmg_msg = self._damage_logs(run, before_len)
            engine._add_buff_to(p, "shock", get_locale_text("i18n_enemy_misc.common.shock_name"), get_locale_text("i18n_enemy_misc.common.shock_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_b.the_defect.zap_orb", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "boot_sequence":
            if target:
                engine._gain_shield(run, target, intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_b.the_defect.boot_sequence", name=enemy.name, val=intent.val))
        elif intent.type == "electrodynamics":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="lightning")
            for grid in list(p.minions.keys()):
                engine._damage_target(run, f"p{grid}", val, source=f"enemy:{enemy.name}", damage_type="lightning")
            dmg_msg = self._damage_logs(run, before_len)
            engine._add_buff_to(p, "shock", get_locale_text("i18n_enemy_misc.common.shock_name"), get_locale_text("i18n_enemy_misc.common.shock_desc"), 2)
            logs.append(get_locale_text("i18n_enemy_elite_b.the_defect.electrodynamics", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "plasma_awakening":
            if target:
                engine._gain_shield(run, target, intent.val)
            enemy.max_actions = 2
            enemy.max_bonus_actions = 2
            enemy.actions = max(enemy.actions, 2)
            enemy.bonus_actions = max(enemy.bonus_actions, 2)
            logs.append(get_locale_text("i18n_enemy_elite_b.the_defect.plasma_awakening", name=enemy.name, val=intent.val))
            logs.append(get_locale_text("i18n_enemy_elite_b.the_defect.awakening_quote"))
        elif intent.type == "plasma_beam":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="lightning")
            dmg_msg = self._damage_logs(run, before_len)
            logs.append(get_locale_text("i18n_enemy_elite_b.the_defect.plasma_beam", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "frost_capacitor":
            if target:
                engine._gain_shield(run, target, intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_b.the_defect.frost_capacitor", name=enemy.name, val=intent.val))
        elif intent.type == "defragment":
            from ...buffs import is_debuff
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_elite_b.common.strength_name"), get_locale_text("i18n_enemy_elite_b.common.strength_desc"), intent.val)
            neg_buff = next((b for b in enemy.buffs if is_debuff(b.id)), None)
            if neg_buff:
                neg_buff.stacks -= 1
                if neg_buff.stacks <= 0:
                    enemy.buffs.remove(neg_buff)
                engine._sync_enemy_intents(enemy)
            logs.append(get_locale_text("i18n_enemy_elite_b.the_defect.defragment", name=enemy.name))
        return "\n".join(logs)
