import random
from .base import EventOption
from ...data.card_upgrade_data import CARD_UPGRADE_CONFIG
from ...data.event_data import EVENT_CONFIG, EVENT_MIN_HP, EVENT_MIN_MAX_HP, EVENT_MIN_GOLD, EVENT_TIME_SAND_MIN_MAX_HP
from ..cards import ALL_CARDS
from ...core.inventory.deck_service import DeckService
from ...models.state import ensure_card_state
from ...data.locale_data import get_locale_text

class ReadVoidTomeOption(EventOption, action="read_void_tome", text=get_locale_text("i18n_events_a.chaos_read_void_tome_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("void_library", {})
        p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("read_hp_cost", 10))
        DeckService.add_card_to_deck(p, "curse_dimensional_tear")
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
        card_name = ALL_CARDS[got_card].name if got_card in ALL_CARDS else got_card
        return get_locale_text("i18n_events_a.chaos_read_void_tome_result", card_name=card_name)

class BurnVoidBooksOption(EventOption, action="burn_void_books", text=get_locale_text("i18n_events_a.chaos_burn_void_books_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("void_library", {})
        p.max_hp = max(EVENT_MIN_MAX_HP, p.max_hp - cfg.get("burn_max_hp_cost", 7))
        p.hp = min(p.hp, p.max_hp)
        if "doomsday_core" not in p.relics:
            p.relics.append("doomsday_core")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.chaos_burn_void_books_result")

class SacrificeMindOption(EventOption, action="sacrifice_mind", text=get_locale_text("i18n_events_a.chaos_sacrifice_mind_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("void_library", {})
        p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("sacrifice_hp_cost", 8))
        removed_names = []
        sacrifice_count = cfg.get("sacrifice_card_count", 2)
        if len(p.deck) > cfg.get("sacrifice_deck_threshold", 2):
            removed = random.sample(p.deck, sacrifice_count)
            for r in removed:
                p.deck.remove(r)
                from ...models.state import ensure_card_state
                base_cid = ensure_card_state(r).id
                if base_cid in ALL_CARDS:
                    removed_names.append(ALL_CARDS[base_cid].name)
        else:
            for r in list(p.deck):
                p.deck.remove(r)
                from ...models.state import ensure_card_state
                base_cid = ensure_card_state(r).id
                if base_cid in ALL_CARDS:
                    removed_names.append(ALL_CARDS[base_cid].name)
        DeckService.add_card_to_deck(p, "curse_dazed")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        rem_msg = get_locale_text("i18n_events_a.chaos_sacrifice_mind_removed", names=get_locale_text("i18n_events_a.names_join_and").join(removed_names)) if removed_names else get_locale_text("i18n_events_a.chaos_sacrifice_mind_none")
        return get_locale_text("i18n_events_a.chaos_sacrifice_mind_result", rem_msg=rem_msg)

class BuyBlackmarketRelicOption(EventOption, action="buy_blackmarket_relic", text=get_locale_text("i18n_events_a.chaos_buy_blackmarket_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("goblin_blackmarket", {})
        cost_msg = ""
        buy_gold_cost = cfg.get("buy_gold_cost", 50)
        if p.gold >= buy_gold_cost:
            p.gold -= buy_gold_cost
            cost_msg = get_locale_text("i18n_events_a.chaos_buy_blackmarket_paid")
        else:
            p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("buy_hp_penalty", 15))
            cost_msg = get_locale_text("i18n_events_a.chaos_buy_blackmarket_penalty")
        from ...data.relic_data import RELIC_CONFIG
        pool = [rid for rid, r in RELIC_CONFIG.items() if r.get("rarity") != "curse" and rid != "time_sand_blessing"]
        available = [rid for rid in pool if rid not in p.relics]
        got_relic = random.choice(available) if available else "lucky_coin"
        if got_relic not in p.relics:
            p.relics.append(got_relic)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        relic_name = RELIC_CONFIG.get(got_relic, {}).get("name", got_relic)
        return get_locale_text("i18n_events_a.chaos_buy_blackmarket_result", cost_msg=cost_msg, relic_name=relic_name)

class RobBlackmarketOption(EventOption, action="rob_blackmarket", text=get_locale_text("i18n_events_a.chaos_rob_blackmarket_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("goblin_blackmarket", {})
        if random.random() < cfg.get("rob_success_chance", 0.7):
            p.gold += cfg.get("rob_gold", 100)
            from ...data.gem_data import GEM_CONFIG
            gem_pool = list(GEM_CONFIG.keys())
            gem_id = random.choice(gem_pool)
            engine.enter_next_stage(run)
            next_type = run.node_type
            next_data = run.node_data.copy() if isinstance(run.node_data, dict) else {}
            msg = engine.explore_engine.start_gem_insert_flow(run, gem_id, next_type, next_data)
            engine.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_events_a.chaos_rob_blackmarket_success", msg=msg)
        else:
            engine.battle_engine._init_battle_node(run, "elite")
            run.node_type = "battle"
            engine.save_manager.save_save(run.user_id, run)
            return engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_events_a.chaos_rob_blackmarket_fail"))

class SellFleshOption(EventOption, action="sell_flesh", text=get_locale_text("i18n_events_a.chaos_sell_flesh_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("goblin_blackmarket", {})
        p.max_hp = max(EVENT_MIN_MAX_HP, p.max_hp - cfg.get("sell_max_hp_cost", 5))
        p.hp = min(p.hp, p.max_hp)
        p.gold += cfg.get("sell_gold", 80)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.chaos_sell_flesh_result")

class DrinkTimeSandOption(EventOption, action="drink_time_sand", text=get_locale_text("i18n_events_a.chaos_drink_time_sand_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("time_fountain_trial", {})
        hp_divisor = cfg.get("time_sand_max_hp_divisor", 4)
        p.max_hp = max(EVENT_TIME_SAND_MIN_MAX_HP, p.max_hp - p.max_hp // hp_divisor)
        p.hp = max(EVENT_MIN_HP, p.hp - p.hp // hp_divisor)
        if "time_sand_blessing" not in p.relics:
            p.relics.append("time_sand_blessing")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.chaos_drink_time_sand_result")

class AccelerateCinderOption(EventOption, action="accelerate_cinder", text=get_locale_text("i18n_events_a.chaos_accelerate_cinder_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("time_fountain_trial", {})
        p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("cinder_hp_cost", 12))
        DeckService.add_card_to_deck(p, "warrior_source_of_cinder")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.chaos_accelerate_cinder_result")

class TouchTimeRiftOption(EventOption, action="touch_time_rift", text=get_locale_text("i18n_events_a.chaos_touch_time_rift_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("time_fountain_trial", {})
        p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("rift_hp_cost", 6))
        DeckService.add_card_to_deck(p, "curse_dimensional_tear")
        upgraded_names = []
        counts = {}
        for entry in p.deck:
            state = ensure_card_state(entry)
            if not state.upgraded and state.id in CARD_UPGRADE_CONFIG:
                counts[state] = counts.get(state, 0) + 1
        upgradable = list(counts.keys())
        if upgradable:
            rift_upgrade_count = cfg.get("rift_upgrade_count", 3)
            to_upgrade = random.sample(upgradable, min(rift_upgrade_count, len(upgradable)))
            for state in to_upgrade:
                p.deck.remove(state)
                upg_state = DeckService.upgrade_state(state)
                DeckService.add_card_to_deck(p, upg_state)
                if state.id in ALL_CARDS:
                    upgraded_names.append(ALL_CARDS[state.id].name)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        up_msg = get_locale_text("i18n_events_a.chaos_touch_time_rift_upgraded", names=get_locale_text("i18n_events_a.names_join_enum").join(upgraded_names)) if upgraded_names else get_locale_text("i18n_events_a.chaos_touch_time_rift_none")
        return get_locale_text("i18n_events_a.chaos_touch_time_rift_result", up_msg=up_msg)

class LootWreckageOption(EventOption, action="loot_wreckage", text=get_locale_text("i18n_events_a.chaos_loot_wreckage_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("astral_caravan_disaster", {})
        p.gold += cfg.get("loot_gold", 120)
        p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("loot_hp_cost", 12))
        for _ in range(cfg.get("loot_curse_count", 2)):
            DeckService.add_card_to_deck(p, "curse_dazed")
        from ...data.gem_data import GEM_CONFIG
        gem_pool = list(GEM_CONFIG.keys())
        gem_id = random.choice(gem_pool)
        engine.enter_next_stage(run)
        next_type = run.node_type
        next_data = run.node_data.copy() if isinstance(run.node_data, dict) else {}
        msg = engine.explore_engine.start_gem_insert_flow(run, gem_id, next_type, next_data)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.chaos_loot_wreckage_result", msg=msg)

class RepairEngineOption(EventOption, action="repair_engine", text=get_locale_text("i18n_events_a.chaos_repair_engine_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("astral_caravan_disaster", {})
        p.gold = max(EVENT_MIN_GOLD, p.gold - cfg.get("repair_gold_cost", 30))
        p.max_hp = max(EVENT_MIN_MAX_HP, p.max_hp - cfg.get("repair_max_hp_cost", 5))
        p.hp = min(p.hp, p.max_hp)
        got_relic = random.choice(["doomsday_core", "energy_core"])
        if got_relic not in p.relics:
            p.relics.append(got_relic)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        from ...data.relic_data import RELIC_CONFIG
        relic_name = RELIC_CONFIG.get(got_relic, {}).get("name", got_relic)
        return get_locale_text("i18n_events_a.chaos_repair_engine_result", relic_name=relic_name)

class BraveStormOption(EventOption, action="brave_storm", text=get_locale_text("i18n_events_a.chaos_brave_storm_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("astral_caravan_disaster", {})
        loss = int(p.hp * cfg.get("storm_hp_ratio", 0.4))
        p.hp = max(EVENT_MIN_HP, p.hp - loss)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.chaos_brave_storm_result", loss=loss)

class DigGraveOption(EventOption, action="dig_grave", text=get_locale_text("i18n_events_a.chaos_dig_grave_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("nameless_tombstone", {})
        for _ in range(cfg.get("dig_curse_count", 2)):
            DeckService.add_card_to_deck(p, "curse_dimensional_tear")
        if "necromancer_skull" not in p.relics:
            p.relics.append("necromancer_skull")
        from ...data.gem_data import GEM_CONFIG
        gem_pool = list(GEM_CONFIG.keys())
        gem_id = random.choice(gem_pool)
        engine.enter_next_stage(run)
        next_type = run.node_type
        next_data = run.node_data.copy() if isinstance(run.node_data, dict) else {}
        msg = engine.explore_engine.start_gem_insert_flow(run, gem_id, next_type, next_data)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.chaos_dig_grave_result", msg=msg)

class ReadEpitaphOption(EventOption, action="read_epitaph", text=get_locale_text("i18n_events_a.chaos_read_epitaph_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("nameless_tombstone", {})
        p.max_hp += cfg.get("epitaph_max_hp_gain", 20)
        if "wither_seed" not in p.relics:
            p.hp = min(p.max_hp, p.hp + cfg.get("epitaph_heal", 20))
        p.gold = EVENT_MIN_GOLD
        DeckService.add_card_to_deck(p, "curse_agony")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.chaos_read_epitaph_result")

class CarveOwnNameOption(EventOption, action="carve_own_name", text=get_locale_text("i18n_events_a.chaos_carve_own_name_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("nameless_tombstone", {})
        p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("carve_hp_cost", 15))
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.chaos_carve_own_name_result")
