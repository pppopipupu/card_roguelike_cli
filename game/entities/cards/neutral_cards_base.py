from ...models.state import Card
from ...data.card_data import CARD_CONFIG
from ...data.card_upgrade_data import CARD_UPGRADE_CONFIG
from ...data.locale_data import get_locale_text
from .registry import register_card

@register_card("tactical_focus")
class TacticalFocusCard(Card):
    def execute(self, run, target, engine) -> str:
        draw_count = getattr(self, "draw_count", 5 if self.upgraded else 3)
        engine._draw_cards(run.player, draw_count, run)
        from ...data.buff_data import BUFF_CONFIG
        buff_info = BUFF_CONFIG.get("tactical_focus", {})
        buff_name = buff_info.get("name", get_locale_text("i18n_cards_neutral.neutral.cards.tactical_focus.buff_name"))
        buff_desc = buff_info.get("desc", get_locale_text("i18n_cards_neutral.neutral.cards.tactical_focus.buff_desc"))
        engine._add_buff_to(run.player, "tactical_focus", buff_name, buff_desc)
        cfg = CARD_CONFIG.get("tactical_focus", {})
        feedback_tmpl = cfg.get("feedback", get_locale_text("i18n_cards_neutral.neutral.cards.tactical_focus.result"))
        return feedback_tmpl.format(name=self.name, draw_count=draw_count)

@register_card("iron_will")
class IronWillCard(Card):
    def execute(self, run, target, engine) -> str:
        buff_id = "iron_will+" if self.upgraded else "iron_will"
        buff_name = get_locale_text("i18n_cards_neutral.neutral.cards.iron_will.buff_name_upgraded") if self.upgraded else get_locale_text("i18n_cards_neutral.neutral.cards.iron_will.buff_name")
        buff_desc = get_locale_text("i18n_cards_neutral.neutral.cards.iron_will.buff_desc_upgraded") if self.upgraded else get_locale_text("i18n_cards_neutral.neutral.cards.iron_will.buff_desc")
        buff_stacks = getattr(self, "buff_stacks", 1)
        engine._add_buff_to(run.player, buff_id, buff_name, buff_desc, buff_stacks, None)
        heal_val = getattr(self, "heal_amount", 15 if self.upgraded else 10)
        engine._heal_target(run, "p0", heal_val)
        if self.upgraded:
            doubled_turns = getattr(self, "buff_turns", 2)
            for b in run.player.buffs:
                if b.id == buff_id:
                    b.stacks2 = doubled_turns
                    break
        shield_msg = ""
        if self.upgraded:
            shield_amount = getattr(self, "shield_amount", 8)
            engine._gain_shield(run, "p0", shield_amount)
            shield_msg = get_locale_text("i18n_cards_neutral.neutral.cards.iron_will.shield_suffix")
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        if self.upgraded:
            return get_locale_text("i18n_cards_neutral.neutral.cards.iron_will.result_upgraded", shield_msg=shield_msg)
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(name=self.name)
        return get_locale_text("i18n_cards_neutral.neutral.cards.iron_will.result")

@register_card("misty_step")
class MistyStepCard(Card):
    def execute(self, run, target, engine) -> str:
        draw_count = getattr(self, "draw_count", 3 if self.upgraded else 2)
        engine._draw_cards(run.player, draw_count, run)
        cfg = CARD_CONFIG.get(self.id, {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(draw_count=draw_count)
        return get_locale_text("i18n_cards_neutral.neutral.cards.misty_step.result")

@register_card("arcane_intellect")
class ArcaneIntellectCard(Card):
    def execute(self, run, target, engine) -> str:
        draw_count = getattr(self, "draw_count", 4 if self.upgraded else 3)
        engine._draw_cards(run.player, draw_count, run)
        cfg = CARD_CONFIG.get(self.id, {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(draw_count=draw_count)
        return get_locale_text("i18n_cards_neutral.neutral.cards.arcane_intellect.result")

@register_card("calculated_gamble")
class CalculatedGambleCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        discard_count = len(p.hand)
        cfg = CARD_CONFIG.get(self.id, {})
        if discard_count > 0:
            agile_effects = []
            hand_cards = list(p.hand)
            p.hand.clear()
            for cid in hand_cards:
                effect_msg = engine._discard_card(run, cid)
                if effect_msg:
                    agile_effects.append(effect_msg)
            engine._draw_cards(p, discard_count, run)
            agile_str = "\n" + "\n".join(agile_effects) if agile_effects else ""
            feedback_tmpl = cfg.get("feedback")
            if feedback_tmpl:
                return feedback_tmpl.format(discard_count=discard_count) + agile_str
            return get_locale_text("i18n_cards_neutral.neutral.cards.calculated_gamble.result", discard_count=discard_count) + agile_str
        return cfg.get("feedback_empty", get_locale_text("i18n_cards_neutral.neutral.cards.calculated_gamble.empty"))

@register_card("mana_potion")
class ManaPotionCard(Card):
    def __init__(self, id, name, color, type, cost_a, cost_ba, exhaust=False, desc=""):
        super().__init__(id, name, color, type, cost_a, cost_ba, exhaust=exhaust, desc=desc)

    def execute(self, run, target, engine) -> str:
        if self.upgraded:
            gain_a = getattr(self, "gain_a", 1)
            draw_count = getattr(self, "draw_count", 2)
            run.player.actions += gain_a
            engine._draw_cards(run.player, draw_count, run)
            return get_locale_text("i18n_cards_neutral.neutral.cards.mana_potion.result_upgraded")
        else:
            gain_ba = getattr(self, "gain_ba", 1)
            draw_count = getattr(self, "draw_count", 1)
            run.player.bonus_actions += gain_ba
            engine._draw_cards(run.player, draw_count, run)
            cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
            return cfg.get("feedback", get_locale_text("i18n_cards_neutral.neutral.cards.mana_potion.result"))

@register_card("mass_healing_word")
class MassHealingWordCard(Card):
    def execute(self, run, target, engine) -> str:
        heal_val = getattr(self, "heal_amount", 8)
        from ...core.battle.party_battle import party_slots
        for slot, _, player in party_slots(run, alive_only=True):
            engine._heal_target(run, f"a{slot}", heal_val)
            for grid in list(player.minions.keys()):
                if grid in player.minions:
                    engine._heal_target(run, f"a{slot}m{grid}", heal_val)
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(heal_amount=heal_val)
        return get_locale_text("i18n_cards_neutral.neutral.cards.mass_healing_word.result", name=self.name, heal_amount=heal_val)

@register_card("refresh_spirit")
class RefreshSpiritCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        exhausted_count = 0
        remaining_hand = []
        from ...models.events import CardExhaustEvent
        from .base import ALL_CARDS
        for cid in p.hand:
            card_obj = ALL_CARDS.get(cid)
            if card_obj and card_obj.type != "minion":
                p.exhaust_pile.append(cid)
                engine._log_event(run, get_locale_text("i18n_cards_neutral.neutral.cards.refresh_spirit.exhaust_log", card_name=card_obj.name))
                exhaust_evt = CardExhaustEvent(run, cid, "effect")
                engine.event_bus.dispatch(exhaust_evt)
                exhausted_count += 1
            else:
                remaining_hand.append(cid)
        p.hand = remaining_hand
        
        shield_mult = getattr(self, "shield_amount", 8 if self.upgraded else 6)
        shield_to_gain = exhausted_count * shield_mult
        if shield_to_gain > 0:
            engine._gain_shield(run, "p0", shield_to_gain)
            
        bonus_msg = ""
        threshold = getattr(self, "threshold", 3)
        if self.upgraded and exhausted_count >= threshold:
            gain_a = getattr(self, "gain_a", 1)
            run.player.actions += gain_a
            bonus_msg = get_locale_text("i18n_cards_neutral.neutral.cards.refresh_spirit.bonus")
            
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if self.upgraded:
            return get_locale_text("i18n_cards_neutral.neutral.cards.refresh_spirit.result_upgraded", name=self.name, exhaust_count=exhausted_count, shield_amount=shield_to_gain, bonus_msg=bonus_msg)
        if feedback_tmpl:
            return feedback_tmpl.format(exhaust_count=exhausted_count, shield_amount=shield_to_gain)
        return get_locale_text("i18n_cards_neutral.neutral.cards.refresh_spirit.result", name=self.name, exhaust_count=exhausted_count, shield_amount=shield_to_gain)

@register_card("key_resonance")
class KeyResonanceCard(Card):
    def execute(self, run, target, engine) -> str:
        X = run.node_data.get("last_x_cost_a", 0)
        recall_count = getattr(self, "hit_count", 10)
        logs = []
        for _ in range(X):
            msg = engine.combat_resolver.recall_dead_minion(run, recall_count)
            logs.append(msg)
        stats = engine.save_manager.load_stats(run.user_id)
        has_key = getattr(stats, "unlocked_gatekey", False)
        damage_amount = 0
        if has_key and X > 0:
            base_dmg = getattr(self, "base_dmg", 9 if self.upgraded else 6)
            total_dmg = X * base_dmg
            for idx in range(len(run.enemies) - 1, -1, -1):
                engine._damage_target(run, f"e{idx+1}", total_dmg, damage_type="force", card=self)
            damage_amount = total_dmg
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        res_str = ""
        if feedback_tmpl:
            res_str = feedback_tmpl.format(recall_count=X, damage_amount=damage_amount)
        else:
            res_str = get_locale_text("i18n_cards_neutral.neutral.cards.key_resonance.result", recall_count=X, damage_amount=damage_amount)
        if logs:
            res_str += get_locale_text("i18n_cards_neutral.neutral.cards.key_resonance.recall_details") + "\n".join(logs)
        return res_str

@register_card("master_key")
class MasterKeyCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        base_id = self.id[:-1] if self.id.endswith("+") else self.id
        reduction = CARD_UPGRADE_CONFIG.get(base_id, {}).get("reduction", 3) if self.upgraded else getattr(self, "reduction", 2)
        from ..amulets import ALL_AMULETS
        lw_logs = []
        for ak, av in list(p.amulets.items()):
            av.countdown -= reduction
            if av.countdown <= 0:
                del p.amulets[ak]
                p.minion_graveyard.append(av.id)
                base_id = av.id[:-1] if av.id.endswith("+") else av.id
                template = ALL_AMULETS.get(base_id)
                lw_msg = ""
                if template:
                    is_upgraded = av.id.endswith("+")
                    lw_msg = template.on_death(run, ak, is_upgraded, engine)
                if lw_msg:
                    lw_logs.append(get_locale_text("i18n_cards_neutral.neutral.cards.master_key.deathrattle_log", amulet_name=av.name, lw_msg=lw_msg))
        if self.upgraded:
            draw_count = getattr(self, "draw_count", 1)
            engine._draw_cards(p, draw_count, run)
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        res_str = cfg.get("feedback", get_locale_text("i18n_cards_neutral.neutral.cards.master_key.result")).format(reduction=reduction)
        if lw_logs:
            res_str += "\n" + "\n".join(lw_logs)
        return res_str
