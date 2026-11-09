import math
from .base import EventOption
from ...data.event_data import EVENT_CONFIG, EVENT_MIN_MAX_HP
from ...core.deck_service import DeckService
from ...data.locale_data import get_locale_text

class ContractPortalOption(EventOption, action="contract_portal", text=get_locale_text("i18n_events_c.opt_contract_portal")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("portal_chamber", {})
        cost_hp = math.ceil(p.max_hp * cfg.get("contract_max_hp_ratio", 0.05))
        p.max_hp = max(EVENT_MIN_MAX_HP, p.max_hp - cost_hp)
        p.hp = min(p.hp, p.max_hp)
        if "portal_fragment" not in p.relics:
            p.relics.append("portal_fragment")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_c.result_contract_portal", cost_hp=cost_hp)

class ArcanePortalOption(EventOption, action="arcane_portal", text=get_locale_text("i18n_events_c.opt_arcane_portal")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        DeckService.add_card_to_deck(p, "master_key")
        DeckService.add_card_to_deck(p, "curse_dimensional_tear")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_c.result_arcane_portal")
