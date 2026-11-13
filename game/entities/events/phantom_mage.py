import random
from .base import EventOption
from ...data.event_data import EVENT_CONFIG
from ..cards import ALL_CARDS
from ...core.inventory.deck_service import DeckService
from ...data.reward_config import NORMAL_CARD_RARITIES
from ...data.locale_data import get_locale_text

class ReadScrollOption(EventOption, action="read_scroll", text=get_locale_text("i18n_events_b.option_read_scroll")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("phantom_mage", {})
        if random.random() < cfg.get("read_success_chance", 0.5):
            DeckService.add_card_to_deck(p, "spell_surge")
            res = get_locale_text("i18n_events_b.msg_read_scroll_success")
        else:
            DeckService.add_card_to_deck(p, "curse_dazed")
            res = get_locale_text("i18n_events_b.msg_read_scroll_fail")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res

class ResonateScrollOption(EventOption, action="resonate_scroll", text=get_locale_text("i18n_events_b.option_resonate_scroll")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("phantom_mage", {})
        resonate_gold = cfg.get("resonate_gold", 15)
        if p.gold < resonate_gold:
            return get_locale_text("i18n_events_b.err_gold_not_enough_15")
        p.gold -= resonate_gold
        stats = engine.save_manager.load_stats(run.user_id) if hasattr(engine.save_manager, "load_stats") else None
        spells = DeckService.eligible_card_ids(stats, card_types=("spell",), rarities=NORMAL_CARD_RARITIES)
        got_card = random.choice(spells) if spells else "dagger_throw"
        DeckService.add_card_to_deck(p, got_card)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_resonate_scroll", card_name=ALL_CARDS[got_card].name)

class DispelPhantomOption(EventOption, action="dispel_phantom", text=get_locale_text("i18n_events_b.option_dispel_phantom")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("phantom_mage", {})
        if "wither_seed" not in p.relics:
            p.hp = min(p.max_hp, p.hp + cfg.get("dispel_heal", 15))
            res = get_locale_text("i18n_events_b.msg_dispel_heal")
        else:
            res = get_locale_text("i18n_events_b.msg_dispel_no_heal")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res
