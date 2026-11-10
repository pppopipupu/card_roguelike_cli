from typing import List
import random
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text
from ....core.deck_service import DeckService

@register_enemy("虚境之影")
class ShroudShadowTemplate(EnemyTemplate):
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

    def _intent_entry(self, intents, intent_id):
        return next((it for it in intents if it.get("id") == intent_id), None)

    def on_battle_start(self, run, enemy, engine):
        if any(b.id == "shroud_time_warp" for b in enemy.buffs):
            return
        engine._add_buff_to(enemy, "shroud_time_warp", get_locale_text("i18n_buffs.shroud_time_warp_name"), get_locale_text("i18n_buffs.shroud_time_warp_desc"), 0)

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        cfg = ENEMY_CONFIG.get(self.name, {})
        intents = cfg.get("intents", [])
        a_pool = [it for it in intents if it.get("id") in ("void_echo", "chrono_slam", "shroud_miasma")] or intents
        intents_list = []
        for _ in range(enemy.actions):
            chosen = random.choice(a_pool)
            intents_list.append(EnemyIntentState(
                type=chosen.get("id", ""),
                val=chosen.get("val", 0),
                desc=chosen.get("desc", ""),
                cost_a=1,
                cost_ba=0
            ))
        guard = self._intent_entry(intents, "shroud_guard") or {"id": "shroud_guard", "val": 0, "desc": ""}
        rewind = self._intent_entry(intents, "foolish_rewind")
        used = run.node_data.setdefault("shroud_rewind_used", {})
        chosen = guard
        if enemy.max_bonus_actions > 0 and rewind is not None and enemy.hp * 2 <= enemy.max_hp and not used.get(enemy.name):
            used[enemy.name] = True
            chosen = rewind
        for _ in range(enemy.bonus_actions):
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

        if intent.type == "void_echo":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            dmg_msg = self._damage_logs(run, before_len)
            logs.append(get_locale_text("i18n_enemy_elite_c.shroud_shadow_void_echo_log", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "chrono_slam":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            dmg_msg = self._damage_logs(run, before_len)
            run.node_data["draw_penalty_next_turn"] = run.node_data.get("draw_penalty_next_turn", 0) + 1
            logs.append(get_locale_text("i18n_enemy_elite_c.shroud_shadow_chrono_slam_log", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "shroud_miasma":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            dmg_msg = self._damage_logs(run, before_len)
            engine._add_buff_to(p, "weak", get_locale_text("i18n_battle_core.buff_weak_name"), get_locale_text("i18n_battle_core.buff_weak_desc"), 1)
            DeckService.add_card_to_discard(p, "curse_dazed")
            DeckService.add_card_to_discard(p, "curse_dazed")
            logs.append(get_locale_text("i18n_enemy_elite_c.shroud_shadow_miasma_log", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "shroud_guard":
            if target:
                engine._gain_shield(run, target, intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_c.shroud_shadow_guard_log", name=enemy.name, val=intent.val))
        elif intent.type == "foolish_rewind":
            from ...buffs import is_debuff
            heal = intent.val
            shield = 20
            enemy.buffs[:] = [b for b in enemy.buffs if not is_debuff(b.id)]
            engine._sync_enemy_intents(enemy)
            if target:
                engine._heal_target(run, target, heal)
                engine._gain_shield(run, target, shield)
            logs.append(get_locale_text("i18n_enemy_elite_c.shroud_shadow_rewind_log", name=enemy.name, heal=heal, shield=shield))
            logs.append(get_locale_text("i18n_enemy_elite_c.shroud_shadow_rewind_quote"))
        return "\n".join(logs)
