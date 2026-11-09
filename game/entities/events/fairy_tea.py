import random
from .base import EventOption
from ...data.event_data import EVENT_CONFIG
from ..cards import ALL_CARDS
from ...core.deck_service import DeckService
from ...data.locale_data import get_locale_text

class DrinkNectarOption(EventOption, action="drink_nectar", text=get_locale_text("i18n_events_a.fairy_drink_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("fairy_tea", {})
        if "wither_seed" not in p.relics:
            p.hp = min(p.max_hp, p.hp + cfg.get("nectar_heal", 12))
            res = get_locale_text("i18n_events_a.fairy_drink_result_heal")
        else:
            res = get_locale_text("i18n_events_a.fairy_drink_result_wither")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res

class EatCookieOption(EventOption, action="eat_cookie", text=get_locale_text("i18n_events_a.fairy_cookie_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("fairy_tea", {})
        cookie_gain = cfg.get("cookie_max_hp_gain", 4)
        p.max_hp += cookie_gain
        p.hp += cookie_gain
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.fairy_cookie_result")

class ListenMusicOption(EventOption, action="listen_music", text=get_locale_text("i18n_events_a.fairy_music_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        agile_cards = [cid for cid, c in ALL_CARDS.items() if getattr(c, "agile", False) and not cid.startswith("curse_")]
        got_card = random.choice(agile_cards) if agile_cards else "agile_strike"
        DeckService.add_card_to_deck(p, got_card)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.fairy_music_result", card_name=ALL_CARDS[got_card].name)
