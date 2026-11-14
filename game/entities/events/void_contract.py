import random
from .base import EventOption
from ...data.event_data import EVENT_CONFIG, EVENT_MIN_HP, EVENT_MIN_MAX_HP
from ...data.relic_data import RELIC_CONFIG
from ..relics import get_relic_name
from ..cards import ALL_CARDS
from ...core.inventory.deck_service import DeckService
from ...data.locale_data import get_locale_text

class ContractRelicOption(EventOption, action="contract_relic", text=get_locale_text("i18n_events_c.opt_contract_relic")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("void_contract", {})
        p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("relic_hp_cost", 10))
        relics_pool = ["lucky_coin", "red_bottle", "leather_armor", "whetstone", "ready_pack", "arcane_rune", "ancient_eye", "gold_compass", "dragon_blood", "energy_core", "heavy_armor"]
        available_relics = [r for r in relics_pool if r not in p.relics]
        got_relic = ""
        if available_relics:
            got_relic = random.choice(available_relics)
            p.relics.append(got_relic)
            if got_relic == "red_bottle":
                red_bottle_cfg = RELIC_CONFIG.get("red_bottle", {})
                p.max_hp += red_bottle_cfg.get("max_hp_gain", 5)
                p.hp += red_bottle_cfg.get("heal_amount", 5)
        relic_msg = get_locale_text("i18n_events_c.relic_gained", name=get_relic_name(got_relic)) if got_relic else get_locale_text("i18n_events_c.relic_none")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_c.result_contract_relic", relic_msg=relic_msg)

class ContractLegendOption(EventOption, action="contract_legend", text=get_locale_text("i18n_events_c.opt_contract_legend")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("void_contract", {})
        p.max_hp = max(EVENT_MIN_MAX_HP, p.max_hp - cfg.get("legend_max_hp_cost", 3))
        p.hp = min(p.hp, p.max_hp)
        stats = None
        if hasattr(engine.save_manager, "load_stats"):
            stats = engine.save_manager.load_stats(run.user_id)
        killed_yog = False
        if stats and getattr(stats, "yog_sothoth_kill_count", 0) > 0:
            killed_yog = True
        legends = [cid for cid, c in ALL_CARDS.items() if not cid.endswith("+") and c.rarity in ("legendary", "mythic", "artifact") and not cid.startswith("curse_") and not getattr(c, "life_merchant_only", False) and not getattr(c, "token", False) and not getattr(c, "event_only", False)]
        if not killed_yog:
            legends = [cid for cid in legends if cid != "neutral_button_magic"]
        got_card = random.choice(legends) if legends else "doomsday_judgment"
        DeckService.add_card_to_deck(p, got_card)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_c.result_contract_legend", card_name=ALL_CARDS[got_card].name)

class AbsorbVoidOption(EventOption, action="absorb_void", text=get_locale_text("i18n_events_c.opt_absorb_void")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("void_contract", {})
        p.gold += cfg.get("absorb_gold", 35)
        DeckService.add_card_to_deck(p, "curse_agony")
        heal_msg = ""
        if "wither_seed" not in p.relics:
            p.hp = min(p.max_hp, p.hp + cfg.get("absorb_heal", 6))
            heal_msg = get_locale_text("i18n_events_c.absorb_void_heal")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_c.result_absorb_void", heal_msg=heal_msg)
