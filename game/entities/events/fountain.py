import random
from .base import EventOption
from ...data.event_data import EVENT_CONFIG
from ..cards import ALL_CARDS
from ...core.deck_service import DeckService
from ...data.reward_config import NORMAL_CARD_RARITIES
from ...data.locale_data import get_locale_text

class DrinkFountainOption(EventOption, action="drink_fountain", text=get_locale_text("i18n_events_b.option_drink_fountain")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("fountain", {})
        p.hp = min(p.max_hp, p.hp + cfg.get("hp_gain", 10))
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_drink_fountain")

class CoinFountainOption(EventOption, action="coin_fountain", text=get_locale_text("i18n_events_b.option_coin_fountain")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("fountain", {})
        gold_cost = cfg.get("gold_cost", 10)
        if p.gold < gold_cost:
            return get_locale_text("i18n_events_b.err_gold_not_enough_10")
        p.gold -= gold_cost
        stats = engine.save_manager.load_stats(run.user_id) if hasattr(engine.save_manager, "load_stats") else None
        wizards = DeckService.eligible_card_ids(stats, colors=("wizard",), rarities=NORMAL_CARD_RARITIES)
        sample_count = cfg.get("wizard_sample_count", 3)
        reward_cards = random.sample(wizards, sample_count) if len(wizards) >= sample_count else wizards
        run.node_type = "card_select"
        run.node_data = {
            "title": get_locale_text("i18n_events_b.wishing_title"),
            "desc": get_locale_text("i18n_events_b.wishing_desc"),
            "cards": reward_cards
        }
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_coin_fountain")

class ObserveFountainOption(EventOption, action="observe_fountain", text=get_locale_text("i18n_events_b.option_observe_fountain")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG["fountain_observe"]
        run.node_data["event_id"] = "fountain_observe"
        run.node_data["description"] = cfg["description"]
        run.node_data["options"] = [{"text": o["text"], "action": o["action"]} for o in cfg["options"]]
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_observe_fountain")

class TakeNecklaceOption(EventOption, action="take_necklace", text=get_locale_text("i18n_events_b.option_take_necklace")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("fountain_observe", {})
        if random.random() < cfg.get("success_chance", 0.5):
            p.relics.append("arcane_rune")
            res = get_locale_text("i18n_events_b.msg_necklace_success")
        else:
            DeckService.add_card_to_deck(p, "curse_dazed")
            res = get_locale_text("i18n_events_b.msg_necklace_trap")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res
