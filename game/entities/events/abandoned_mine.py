import random
from .base import EventOption
from ...data.event_data import EVENT_CONFIG, EVENT_MIN_HP
from ...core.inventory.deck_service import DeckService
from ...data.relic_data import RELIC_CONFIG
from ..relics import get_relic_name
from ...data.locale_data import get_locale_text

class RideCartOption(EventOption, action="ride_cart", text=get_locale_text("i18n_events_a.mine_ride_cart_text")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG["mine_cart_crash"]
        run.node_data["event_id"] = "mine_cart_crash"
        run.node_data["description"] = cfg["description"]
        run.node_data["options"] = [{"text": o["text"], "action": o["action"]} for o in cfg["options"]]
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.mine_ride_cart_result")

class ClimbLadderOption(EventOption, action="climb_ladder", text=get_locale_text("i18n_events_a.mine_climb_ladder_text")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG["mine_ladder_body"]
        run.node_data["event_id"] = "mine_ladder_body"
        run.node_data["description"] = cfg["description"]
        run.node_data["options"] = [{"text": o["text"], "action": o["action"]} for o in cfg["options"]]
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.mine_climb_ladder_result")

class JumpCartOption(EventOption, action="jump_cart", text=get_locale_text("i18n_events_a.mine_jump_cart_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("mine_cart_crash", {})
        p.gold += cfg.get("jump_gold", 40)
        DeckService.add_card_to_deck(p, "curse_dazed")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.mine_jump_cart_result")

class StopCartSpellOption(EventOption, action="stop_cart_spell", text=get_locale_text("i18n_events_a.mine_stop_cart_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("mine_cart_crash", {})
        has_key_card = any(cid in p.deck for cid in ["shield_guard", "fireball", "thunderwave"])
        if has_key_card:
            relics_pool = ["lucky_coin", "red_bottle", "leather_armor", "whetstone", "ready_pack", "arcane_rune"]
            available_relics = [r for r in relics_pool if r not in p.relics]
            got_relic = ""
            if available_relics:
                got_relic = random.choice(available_relics)
                p.relics.append(got_relic)
                if got_relic == "red_bottle":
                    red_bottle_cfg = RELIC_CONFIG.get("red_bottle", {})
                    p.max_hp += red_bottle_cfg.get("max_hp_gain", 5)
                    p.hp += red_bottle_cfg.get("heal_amount", 5)
            relic_msg = get_locale_text("i18n_events_a.mine_stop_cart_relic_suffix", relic_name=get_relic_name(got_relic)) if got_relic else ""
            res = get_locale_text("i18n_events_a.mine_stop_cart_success", relic_msg=relic_msg)
        else:
            p.hp = max(EVENT_MIN_HP, p.hp - cfg.get("fail_hp_loss", 10))
            p.gold += cfg.get("fail_gold", 10)
            res = get_locale_text("i18n_events_a.mine_stop_cart_fail")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res

class LootBodyOption(EventOption, action="loot_body", text=get_locale_text("i18n_events_a.mine_loot_body_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("mine_ladder_body", {})
        p.gold += cfg.get("loot_gold", 25)
        DeckService.add_card_to_deck(p, "curse_agony")
        heal_msg = ""
        if "wither_seed" not in p.relics:
            p.hp = min(p.max_hp, p.hp + cfg.get("loot_heal", 4))
            heal_msg = get_locale_text("i18n_events_a.mine_loot_body_heal")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_a.mine_loot_body_result", heal_msg=heal_msg)

class DigOreOption(EventOption, action="dig_ore", text=get_locale_text("i18n_events_a.mine_dig_ore_text")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("mine_ladder_body", {})
        has_fire_or_thunder = any(cid in p.deck for cid in ["fireball", "thunderwave"])
        if has_fire_or_thunder:
            p.gold += cfg.get("dig_gold_success", 50)
            res = get_locale_text("i18n_events_a.mine_dig_ore_success")
        else:
            p.gold += cfg.get("dig_gold_fail", 15)
            res = get_locale_text("i18n_events_a.mine_dig_ore_fail")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res
