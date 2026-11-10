from typing import List
import random
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("虚空潜伏者")
class VoidLurkerEliteTemplate(EnemyTemplate):
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

    def _is_curse(self, card):
        return str(getattr(card, "id", "")).startswith("curse_")

    def _card_name(self, card):
        from ... import ALL_CARDS
        cid = str(getattr(card, "id", ""))
        impl = ALL_CARDS.get(cid)
        return getattr(impl, "name", cid) if impl is not None else cid

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        cfg = ENEMY_CONFIG.get(self.name, {})
        intents = cfg.get("intents", [])
        a_pool = [it for it in intents if it.get("id") == "void_ambush"] or intents
        ba_pool = [it for it in intents if it.get("id") == "shadow_fade"] or intents
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
        for _ in range(enemy.bonus_actions):
            chosen = random.choice(ba_pool)
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

        if intent.type == "void_ambush":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="necrotic")
            dmg_msg = self._damage_logs(run, before_len)
            logs.append(get_locale_text("i18n_enemy_elite_c.void_lurker_void_ambush_log", name=enemy.name, dmg_msg=dmg_msg))
            if enemy.shield > 0:
                extra = 4
                before_extra = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", extra, source=f"enemy:{enemy.name}", damage_type="true")
                extra_msg = self._damage_logs(run, before_extra)
                logs.append(get_locale_text("i18n_enemy_elite_c.void_lurker_void_ambush_bonus_log", name=enemy.name, extra=extra, extra_msg=extra_msg))
                candidates = [card for card in p.hand if not self._is_curse(card)]
                if candidates:
                    card = random.choice(candidates)
                    card.fragile = max(getattr(card, "fragile", 0), 1)
                    logs.append(get_locale_text("i18n_enemy_elite_c.void_lurker_fragile_log", card=self._card_name(card)))
        elif intent.type == "shadow_fade":
            if target:
                engine._gain_shield(run, target, intent.val)
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_misc.common.strength_name"), get_locale_text("i18n_enemy_misc.common.strength_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_elite_c.void_lurker_shadow_fade_log", name=enemy.name, val=intent.val, stacks=1))
        return "\n".join(logs)
