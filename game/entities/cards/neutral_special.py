from ...models.state import Card
from ...data.card_data import CARD_CONFIG
from ...data.locale_data import get_locale_text
from .registry import register_card

@register_card("ancient_wisdom")
class AncientWisdomCard(Card):
    def execute(self, run, target, engine) -> str:
        X = run.node_data.get("last_x_cost_a", 0)
        Y = run.node_data.get("last_x_cost_ba", 0)
        coef = getattr(self, "coef", 4 if self.upgraded else 3)
        shield_val = Y * coef
        engine._gain_shield(run, "p0", shield_val)
        if X > 0:
            buff_name = get_locale_text("i18n_cards_neutral.neutral.special.ancient_wisdom.buff_name_upgraded") if self.upgraded else get_locale_text("i18n_cards_neutral.neutral.special.ancient_wisdom.buff_name")
            buff_desc = get_locale_text("i18n_cards_neutral.neutral.special.ancient_wisdom.buff_desc_upgraded") if self.upgraded else get_locale_text("i18n_cards_neutral.neutral.special.ancient_wisdom.buff_desc")
            engine._add_buff_to(run.player, "ancient_wisdom_buff", buff_name, buff_desc, X)
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(shield=shield_val, stacks=X)
        return get_locale_text("i18n_cards_neutral.neutral.special.ancient_wisdom.result", shield=shield_val, stacks=X)

@register_card("merchant_collection")
class MerchantCollectionCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        resonance_stacks = getattr(self, "buff_stacks", 1)
        engine._add_buff_to(p, "all_resonance", get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.desc"), resonance_stacks)
        from .base import ALL_CARDS
        card_pool = list(ALL_CARDS.keys())
        p_class = getattr(engine.save_manager.load_stats(run.user_id), "selected_class", "法师")
        target_color = "warrior" if p_class == "战士" else "wizard"
        from ...entities.cards.market import is_card_available
        stats = engine.save_manager.load_stats(run.user_id)
        class_cards = [
            cid for cid in card_pool
            if ALL_CARDS[cid].rarity in ("legendary", "mythic")
            and not cid.startswith("curse_")
            and not cid.startswith("duel_")
            and ALL_CARDS[cid].color == target_color
            and is_card_available(cid, stats)
        ]
        if not class_cards:
            class_cards = [
                cid for cid in card_pool
                if ALL_CARDS[cid].rarity in ("legendary", "mythic")
                and not cid.startswith("curse_")
                and not cid.startswith("duel_")
            ]
        import random
        max_count = getattr(self, "hit_count", 2)
        chosen = random.sample(class_cards, min(max_count, len(class_cards)))
        added_names = []
        from ...models.state import CardState
        for cid in chosen:
            cstate = CardState(id=cid, upgraded=True)
            p.hand.append(cstate)
            added_names.append(ALL_CARDS[cid].name)
            run.node_data.setdefault("merchant_collection_free_cards", []).append(cid)
        return get_locale_text("i18n_cards_neutral.neutral.special.merchant_collection.result", names=get_locale_text("i18n_cards_neutral.neutral.special.merchant_collection.names_joiner").join(added_names))

@register_card("bard_epic")
class BardEpicCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        strength_gain = getattr(self, "strength_gain", 2)
        double_tap_stacks = getattr(self, "replay_amount", 1)
        resonance_stacks = getattr(self, "resonance_stacks", 1)
        engine._add_buff_to(p, "all_resonance", get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.desc"), resonance_stacks)
        engine._add_buff_to(p, "strength", get_locale_text("i18n_cards_neutral.neutral.buffs.strength.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.strength.desc"), strength_gain)
        engine._add_buff_to(p, "double_tap_buff", get_locale_text("i18n_cards_neutral.neutral.buffs.double_tap.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.double_tap.desc"), double_tap_stacks)
        return get_locale_text("i18n_cards_neutral.neutral.special.bard_epic.result")

@register_card("jack_brew")
class JackBrewCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        heal_amount = getattr(self, "heal_amount", 15)
        gain_a = getattr(self, "gain_a", 1)
        gain_ba = getattr(self, "gain_ba", 1)
        resonance_stacks = getattr(self, "buff_stacks", 1)
        engine._add_buff_to(p, "all_resonance", get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.desc"), resonance_stacks)
        engine._heal_target(run, "p0", heal_amount)
        p.actions += gain_a
        p.bonus_actions += gain_ba
        return get_locale_text("i18n_cards_neutral.neutral.special.jack_brew.result")
