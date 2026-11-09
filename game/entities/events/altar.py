import random
from .base import EventOption
from ...data.event_data import EVENT_CONFIG, EVENT_MIN_HP, EVENT_MIN_PRICE
from ...core.deck_service import DeckService
from ...data.locale_data import get_locale_text

class AbsorbAltarOption(EventOption, action="absorb_altar", text=get_locale_text("i18n_events_a.altar_absorb_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        DeckService.add_card_to_deck(p, "arcane_charge")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.altar_absorb_result")

class BreakAltarOption(EventOption, action="break_altar", text=get_locale_text("i18n_events_a.altar_break_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("altar", {})
        p.gold += cfg.get("break_gold", 20)
        p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("break_hp_cost", 4))
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.altar_break_result")

class MeditateAltarOption(EventOption, action="meditate_altar", text=get_locale_text("i18n_events_a.altar_meditate_text")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG["altar_portal"]
        run.node_data["event_id"] = "altar_portal"
        run.node_data["description"] = cfg["description"]
        run.node_data["options"] = [{"text": o["text"], "action": o["action"]} for o in cfg["options"]]
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.altar_meditate_result")

class EnterPortalOption(EventOption, action="enter_portal", text=get_locale_text("i18n_events_a.altar_enter_portal_text")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG.get("altar_portal", {})
        if random.random() < cfg.get("shop_chance", 0.5):
            run.node_type = "shop"
            engine.explore_engine._init_shop_node(run)
            if "items" in run.node_data:
                price_multiplier = cfg.get("price_multiplier", 0.5)
                for item in run.node_data["items"]:
                    item["price"] = max(EVENT_MIN_PRICE, int(item["price"] * price_multiplier))
            engine.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_events_a.altar_enter_portal_shop")
        else:
            run.node_type = "battle"
            engine.battle_engine._init_battle_node(run, "elite")
            if run.enemies:
                run.enemies[0].name = get_locale_text("i18n_events_a.altar_guardian_name")
            engine.save_manager.save_save(run.user_id, run)
            return engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_events_a.altar_enter_portal_battle"))

class ShatterPortalOption(EventOption, action="shatter_portal", text=get_locale_text("i18n_events_a.altar_shatter_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("altar_portal", {})
        p.gold += cfg.get("shatter_gold", 40)
        DeckService.add_card_to_deck(p, "curse_agony")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.altar_shatter_result")
