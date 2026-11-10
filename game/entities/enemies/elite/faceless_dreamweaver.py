from typing import List
import random
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text
from ....core.deck_service import DeckService

@register_enemy("无面织梦者")
class FacelessDreamweaverTemplate(EnemyTemplate):
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

    def on_battle_start(self, run, enemy, engine):
        if any(b.id == "dream_eater_passive" for b in enemy.buffs):
            return
        engine._add_buff_to(enemy, "dream_eater_passive", get_locale_text("i18n_buffs.dream_eater_passive_name"), get_locale_text("i18n_buffs.dream_eater_passive_desc"), 1)

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        cfg = ENEMY_CONFIG.get(self.name, {})
        intents = cfg.get("intents", [])
        a_pool = [it for it in intents if it.get("id") in ("weave_nightmare", "psionic_shatter")] or intents
        ba_pool = [it for it in intents if it.get("id") in ("mirage_cloak", "drowsy_hex")] or intents
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

        if intent.type == "weave_nightmare":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            dmg_msg = self._damage_logs(run, before_len)
            DeckService.add_card_to_draw(p, "curse_intangible_whisper")
            random.shuffle(p.draw_pile)
            candidates = [card for card in p.hand if not self._is_curse(card)]
            for card in random.sample(candidates, min(2, len(candidates))):
                card.fragile = max(getattr(card, "fragile", 0), 1)
            logs.append(get_locale_text("i18n_enemy_elite_a.faceless_dreamweaver.weave_nightmare", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "psionic_shatter":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            dmg_msg = self._damage_logs(run, before_len)
            qualifying = [card for card in p.hand if getattr(card, "fragile", 0) > 0 or self._is_curse(card)]
            extra = 3 * len(qualifying)
            if extra > 0:
                before_extra = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", extra, source=f"enemy:{enemy.name}", damage_type="force")
                self._damage_logs(run, before_extra)
            logs.append(get_locale_text("i18n_enemy_elite_a.faceless_dreamweaver.psionic_shatter", name=enemy.name, dmg_msg=dmg_msg, extra=extra))
        elif intent.type == "mirage_cloak":
            from ...buffs import is_debuff
            if target:
                engine._gain_shield(run, target, intent.val)
            neg_buff = next((b for b in enemy.buffs if is_debuff(b.id)), None)
            if neg_buff:
                neg_buff.stacks -= 1
                if neg_buff.stacks <= 0:
                    enemy.buffs.remove(neg_buff)
                engine._sync_enemy_intents(enemy)
            logs.append(get_locale_text("i18n_enemy_elite_a.faceless_dreamweaver.mirage_cloak", name=enemy.name, val=intent.val))
        elif intent.type == "drowsy_hex":
            engine._add_buff_to(p, "drain_ba", get_locale_text("i18n_enemy_elite_c.drain_ba_name"), get_locale_text("i18n_enemy_elite_c.drain_ba_desc"), max(1, intent.val))
            logs.append(get_locale_text("i18n_enemy_elite_a.faceless_dreamweaver.drowsy_hex", name=enemy.name))
        return "\n".join(logs)
