import random
from .base import EventOption
from ...data.event_data import EVENT_CONFIG, EVENT_MIN_HP
from ...data.locale_data import get_locale_text

class GambleSmallOption(EventOption, action="gamble_small", text=get_locale_text("i18n_events_b.option_gamble_small")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("goblin_gamble", {})
        small_cost = cfg.get("small_cost", 15)
        if p.gold < small_cost:
            return get_locale_text("i18n_events_b.err_gold_not_enough_15")
        p.gold -= small_cost
        if random.random() < cfg.get("small_win_chance", 0.5):
            p.gold += cfg.get("small_win_gold", 30)
            res = get_locale_text("i18n_events_b.msg_gamble_small_win")
        else:
            res = get_locale_text("i18n_events_b.msg_gamble_small_lose")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res

class GambleLargeOption(EventOption, action="gamble_large", text=get_locale_text("i18n_events_b.option_gamble_large")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("goblin_gamble", {})
        large_cost = cfg.get("large_cost", 30)
        if p.gold < large_cost:
            return get_locale_text("i18n_events_b.err_gold_not_enough_30")
        p.gold -= large_cost
        if random.random() < cfg.get("large_win_chance", 0.4):
            p.gold += cfg.get("large_win_gold", 60)
            res = get_locale_text("i18n_events_b.msg_gamble_large_win")
        else:
            res = get_locale_text("i18n_events_b.msg_gamble_large_lose")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res

class RobGoblinOption(EventOption, action="rob_goblin", text=get_locale_text("i18n_events_b.option_rob_goblin")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("goblin_gamble", {})
        if random.random() < cfg.get("rob_success_chance", 0.7):
            p.gold += cfg.get("rob_gold", 40)
            res = get_locale_text("i18n_events_b.msg_rob_success")
        else:
            p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("rob_fail_hp_loss", 8))
            res = get_locale_text("i18n_events_b.msg_rob_fail")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res
