import random
from .base import EventOption
from ...core.inventory.deck_service import DeckService
from ...core.inventory.relic_service import grant_relic
from ...data.locale_data import get_locale_text
from ...data.ninja_card_data_rare import NINJA_CARD_CONFIG_RARE
from ...data.ninja_card_data_uncommon import NINJA_CARD_CONFIG_UNCOMMON
from ...data.relic_data import RELIC_CONFIG
from ...models.state import CardState
from ..cards import ALL_CARDS
from ..relics import get_relic_name


class NinjaSpectreAcceptOption(EventOption, action="ninja_spectre_accept", text=get_locale_text("i18n_ninja_events.spectre_opt_accept")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        p.hp = min(p.max_hp, p.hp + 10)
        DeckService.add_card_to_deck(p, CardState(id="ninja_i_see_you"))
        pool = list(NINJA_CARD_CONFIG_RARE.keys())
        cid = random.choice(pool)
        DeckService.add_card_to_deck(p, CardState(id=cid))
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_ninja_events.spectre_accept_res", card=ALL_CARDS[cid].name)


class NinjaSpectreAlanOption(EventOption, action="ninja_spectre_alan", text=get_locale_text("i18n_ninja_events.spectre_opt_alan")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        p.hp = max(1, p.hp - 6)
        DeckService.add_card_to_deck(p, CardState(id="ninja_alan_walker"))
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_ninja_events.spectre_alan_res")


class NinjaSealRelicsOption(EventOption, action="ninja_seal_relics", text=get_locale_text("i18n_ninja_events.seal_opt_relics")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        DeckService.add_card_to_deck(p, CardState(id="curse_dazed"))
        candidates = [rid for rid, cfg in RELIC_CONFIG.items() if cfg.get("rarity") == "rare" and rid not in p.relics]
        picked = random.sample(candidates, min(2, len(candidates)))
        for rid in picked:
            grant_relic(p, rid)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        names = "、".join(get_relic_name(r) for r in picked)
        return get_locale_text("i18n_ninja_events.seal_relics_res", relics=names)


class NinjaSealRemoveOption(EventOption, action="ninja_seal_remove", text=get_locale_text("i18n_ninja_events.seal_opt_remove")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        p.hp = max(1, p.hp - 8)
        removed = 0
        for _ in range(2):
            if len(p.deck) <= 4:
                break
            c = random.choice(p.deck)
            p.deck.remove(c)
            removed += 1
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_ninja_events.seal_remove_res", count=removed)


class NinjaSealHamoodOption(EventOption, action="ninja_seal_hamood", text=get_locale_text("i18n_ninja_events.seal_opt_hamood")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        DeckService.add_card_to_deck(p, CardState(id="ninja_hamood_kill_all"))
        p.gold += 120
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_ninja_events.seal_hamood_res")


class NinjaDrinkSipOption(EventOption, action="ninja_drink_sip", text=get_locale_text("i18n_ninja_events.drink_opt_sip")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        before = p.hp
        p.hp = min(p.max_hp, p.hp + 12)
        heal = p.hp - before
        extra = ""
        if len(p.deck) > 5 and random.random() < 0.45:
            c = random.choice(p.deck)
            name = ALL_CARDS[c].name
            p.deck.remove(c)
            extra = get_locale_text("i18n_ninja_events.drink_removed_suffix", name=name)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_ninja_events.drink_sip_res", heal=heal, extra=extra)


class NinjaEelBuyOption(EventOption, action="ninja_eel_buy", text=get_locale_text("i18n_ninja_events.eel_opt_buy")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        if p.gold < 220:
            return get_locale_text("i18n_ninja_events.eel_no_gold", gold=p.gold)
        p.gold -= 220
        before = p.hp
        p.hp = min(p.max_hp, p.hp + 30)
        cid = random.choice(list(NINJA_CARD_CONFIG_UNCOMMON.keys()))
        DeckService.add_card_to_deck(p, CardState(id=cid))
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_ninja_events.eel_buy_res", heal=p.hp - before, card=ALL_CARDS[cid].name)


class NinjaEelFightOption(EventOption, action="ninja_eel_fight", text=get_locale_text("i18n_ninja_events.eel_opt_fight")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        p.hp = max(1, p.hp - 6)
        if "toilet_water" not in p.relics:
            grant_relic(p, "toilet_water")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_ninja_events.eel_fight_res")


class NinjaEelLeaveOption(EventOption, action="ninja_eel_leave", text=get_locale_text("i18n_ninja_events.eel_opt_leave")):
    def _run_effect(self, run, engine) -> str:
        DeckService.add_card_to_deck(run.player, CardState(id="ninja_mosquito_hand"))
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_ninja_events.eel_leave_res")
