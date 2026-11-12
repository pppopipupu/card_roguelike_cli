import random
from .base import EventOption
from ...data.card_upgrade_data import CARD_UPGRADE_CONFIG
from ...data.event_data import EVENT_CONFIG
from ...data.relic_data import RELIC_CONFIG
from ..cards import ALL_CARDS
from ..relics import get_relic_name
from ...models.state import BuffState, ensure_card_state
from ...core.deck_service import DeckService
from ...data.locale_data import get_locale_text

class ForgeFireOption(EventOption, action="forge_fire", text=get_locale_text("i18n_events_a.forge_fire_text")):
    def _run_effect(self, run, engine) -> str:
        run.node_data["upgrade_source"] = "event"
        return "UPGRADE_FLOW"

class OverloadForgeOption(EventOption, action="overload_forge", text=get_locale_text("i18n_events_a.forge_overload_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("forge_furnace", {})
        if random.random() < cfg.get("overload_success_chance", 0.8):
            upgradable_cards = []
            for card_state in p.deck:
                if not card_state.upgraded and card_state.id in CARD_UPGRADE_CONFIG:
                    upgradable_cards.append(card_state)
            if not upgradable_cards:
                res = get_locale_text("i18n_events_a.forge_overload_no_cards")
            else:
                upgraded_names = []
                upgrade_count = cfg.get("overload_upgrade_count", 2)
                to_upgrade = random.sample(upgradable_cards, min(upgrade_count, len(upgradable_cards)))
                for card_state in to_upgrade:
                    card_state.upgraded = True
                    upgraded_names.append(ALL_CARDS[card_state.id].name)
                res = get_locale_text("i18n_events_a.forge_overload_success", names=get_locale_text("i18n_events_a.names_join_and").join(upgraded_names))
        else:
            p.hp -= cfg.get("overload_hp_cost", 8)
            DeckService.add_card_to_deck(p, ensure_card_state("curse_agony"))
            res = get_locale_text("i18n_events_a.forge_overload_backfire")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res

class ForgeBackfireOption(EventOption, action="forge_backfire", text=get_locale_text("i18n_events_a.forge_backfire_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("forge_furnace", {})
        p.max_hp += cfg.get("backfire_max_hp_gain", 5)
        p.hp = min(p.max_hp, p.hp + cfg.get("backfire_heal", 10))
        buff_stacks = cfg.get("backfire_buff_stacks", 2)
        found = False
        for b in p.buffs:
            if b.id == "forge_backfire":
                b.stacks += buff_stacks
                found = True
                break
        if not found:
            p.buffs.append(BuffState("forge_backfire", get_locale_text("i18n_events_a.forge_backfire_buff_name"), buff_stacks, get_locale_text("i18n_events_a.forge_backfire_buff_desc")))
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.forge_backfire_result")

class ShatterForgeOption(EventOption, action="shatter_forge", text=get_locale_text("i18n_events_a.forge_shatter_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("forge_furnace", {})
        p.gold += cfg.get("shatter_gold", 50)
        p.hp -= cfg.get("shatter_hp_cost", 6)
        DeckService.add_card_to_deck(p, ensure_card_state("curse_dazed"))
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
        relic_msg = get_locale_text("i18n_events_a.forge_shatter_relic_suffix", relic_name=get_relic_name(got_relic)) if got_relic else ""
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.forge_shatter_result", relic_msg=relic_msg)
