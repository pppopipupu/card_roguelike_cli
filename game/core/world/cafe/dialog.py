import random
from typing import Tuple
from ....models.state import GameRun
from ....cards import ALL_CARDS
from ....entities import get_relic_name
from ....data.gem_data import GEM_CONFIG
from ....data.cafe_data import (
    CAFE_MIN_HP,
    CAFE_MIN_MAX_HP,
    CAFE_PRICES,
    NPC_DIALOGS,
    NPC_TALKED_FALLBACK,
)
from ....data.locale_data import get_locale_text
from ...inventory.deck_service import DeckService

class CafeDialogMixin:
    def _close_dialog(self, cafe_data: dict, talked_npcs: list, npc: str):
        talked_npcs.append(npc)
        cafe_data["active_npc"] = None
        cafe_data["dialog_state"] = None

    def _get_dialog_content(self, run: GameRun, npc: str, state: str, talked: bool) -> Tuple[str, list[str]]:
        p = run.player
        shared_cafe = self._shared_cafe(run)

        if npc == "Barista_Bruno":
            from .barista import get_barista_dialog_content
            return get_barista_dialog_content(run, state)
        if talked:
            entry = NPC_DIALOGS.get(npc, {}).get("talked", NPC_TALKED_FALLBACK)
            return entry["text"], list(entry["options"])

        if npc == "杰斯":
            stock = shared_cafe.get("card_master_stock", [])
            opts = []
            for cid in stock:
                name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
                desc = ALL_CARDS[cid].desc if cid in ALL_CARDS else ""
                opts.append(get_locale_text("i18n_map_cafe.cafe_opt_buy_card", name=name, desc=desc))
            opts.append(get_locale_text("i18n_map_cafe.cafe_opt_leave_talk"))
            return get_locale_text("i18n_map_cafe.cafe_jace_greeting"), opts

        if npc == "艾琳":
            stock = shared_cafe.get("gemcutter_stock", [])
            opts = [
                get_locale_text("i18n_map_cafe.cafe_opt_gem_slot")
            ]
            for gid in stock:
                name = GEM_CONFIG[gid]["name"] if gid in GEM_CONFIG else gid
                desc = GEM_CONFIG[gid]["desc"] if gid in GEM_CONFIG else ""
                opts.append(get_locale_text("i18n_map_cafe.cafe_opt_buy_gem", name=name, desc=desc))
            opts.append(get_locale_text("i18n_map_cafe.cafe_opt_leave_talk"))
            return get_locale_text("i18n_map_cafe.cafe_erin_greeting"), opts

        if npc == "凯尔":
            opts = []
            if p.relics:
                opts.append(get_locale_text("i18n_map_cafe.cafe_opt_sell_relic", name=get_relic_name(p.relics[0])))
            else:
                opts.append(get_locale_text("i18n_map_cafe.cafe_opt_sell_relic_none"))
            opts.append(get_locale_text("i18n_map_cafe.cafe_opt_buy_relic"))
            opts.append(get_locale_text("i18n_map_cafe.cafe_opt_leave_talk"))
            return get_locale_text("i18n_map_cafe.cafe_kyle_greeting"), opts

        entry = NPC_DIALOGS.get(npc, {}).get(state)
        if entry:
            return entry["text"], list(entry["options"])
        return get_locale_text("i18n_map_cafe.cafe_unknown_traveler"), [get_locale_text("i18n_map_cafe.cafe_opt_leave_talk")]

    def _execute_dialog_logic(self, run: GameRun, npc: str, state: str, idx: int, talked: bool) -> str:
        p = run.player
        cafe_data = self._view_cafe(run)
        shared_cafe = self._shared_cafe(run)
        talked_npcs = shared_cafe.setdefault("talked_npcs", [])

        if npc == "Barista_Bruno":
            from .barista import execute_barista_dialog_choice
            return execute_barista_dialog_choice(self, run, idx)
        if talked:
            if run.player_count() > 1:
                self._release_npc_lock(shared_cafe, run.user_id, npc)
            cafe_data["active_npc"] = None
            cafe_data["dialog_state"] = None
            return get_locale_text("i18n_map_cafe.cafe_msg_dialog_ended")

        if npc == "Guide_Elder":
            if state == "start":
                if idx == 1:
                    cafe_data["dialog_state"] = "branch_a"
                    return get_locale_text("i18n_map_cafe.cafe_msg_guide_start_a") + "\n\n" + self.render_cafe(run)
                elif idx == 2:
                    cafe_data["dialog_state"] = "branch_b"
                    return get_locale_text("i18n_map_cafe.cafe_msg_guide_start_b") + "\n\n" + self.render_cafe(run)
                else:
                    return self.leave_npc(run)
            elif state == "branch_a":
                if idx == 1:
                    if p.gold < CAFE_PRICES["guide_tea_cost"]:
                        return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=40)
                    p.gold -= CAFE_PRICES["guide_tea_cost"]
                    DeckService.add_card_to_deck(p, "neutral_emperor_eye")
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_guide_tea_reward")
                elif idx == 2:
                    p.max_hp = max(CAFE_MIN_MAX_HP, p.max_hp - CAFE_PRICES["guide_spar_hp_cost"])
                    p.hp = min(p.hp, p.max_hp)
                    p.gold += CAFE_PRICES["guide_spar_gold_reward"]
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_guide_spar_reward")
                else:
                    return self.leave_npc(run)
            elif state == "branch_b":
                if idx == 1:
                    p.hp = max(CAFE_MIN_HP, p.hp - CAFE_PRICES["guide_rebuke_hp_cost"])
                    if p.deck:
                        unupgraded = [c for c in p.deck if not c.upgraded]
                        if unupgraded:
                            random.choice(unupgraded).upgraded = True
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_guide_rebuke_reward")
                elif idx == 2:
                    p.gold = max(0, p.gold - CAFE_PRICES["guide_apology_cost"])
                    if p.deck:
                        valid_cards = []
                        for c in p.deck:
                            card_obj = ALL_CARDS.get(c.id)
                            if card_obj:
                                max_slots = card_obj.get_gem_slots_count()
                                if len(c.gems) < max_slots:
                                    valid_cards.append(c)
                        if valid_cards:
                            random.choice(valid_cards).gems.append("empty")
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_guide_apology_reward")
                else:
                    return self.leave_npc(run)

        elif npc == "Bartender_Jack":
            if state == "start":
                if idx == 1:
                    if p.gold < CAFE_PRICES["bartender_drink_cost"]:
                        return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=50)
                    p.gold -= CAFE_PRICES["bartender_drink_cost"]
                    cafe_data["dialog_state"] = "branch_a"
                    return get_locale_text("i18n_map_cafe.cafe_bartender_drink_msg") + "\n\n" + self.render_cafe(run)
                elif idx == 2:
                    if p.gold < CAFE_PRICES["bartender_tea_cost"]:
                        return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=15)
                    p.gold -= CAFE_PRICES["bartender_tea_cost"]
                    p.hp = min(p.max_hp, p.hp + CAFE_PRICES["bartender_tea_heal"])
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_bartender_tea_reward")
                else:
                    return self.leave_npc(run)
            elif state == "branch_a":
                if idx == 1:
                    p.hp = max(CAFE_MIN_HP, p.hp - CAFE_PRICES["bartender_drink_hp_cost"])
                    p.relics.append("espresso_relic")
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_bartender_drink_reward")
                elif idx == 2:
                    if p.gold < CAFE_PRICES["bartender_extra_cost"]:
                        return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=30)
                    p.gold -= CAFE_PRICES["bartender_extra_cost"]
                    attacks = []
                    for c in p.deck:
                        card_obj = ALL_CARDS.get(c.id)
                        if card_obj and card_obj.type == "attack" and "gem_copy_1" not in c.gems:
                            attacks.append(c)
                    if not attacks:
                        attacks = [c for c in p.deck if "gem_copy_1" not in c.gems]
                    if attacks:
                        random.choice(attacks).gems.append("gem_copy_1")
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_bartender_copy_reward")
                else:
                    return self.leave_npc(run)

        elif npc == "Blacksmith_Ironclad":
            if idx == 1:
                if p.gold < CAFE_PRICES["blacksmith_forge_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=70)
                p.gold -= CAFE_PRICES["blacksmith_forge_cost"]
                if p.deck:
                    from ....models.state import ensure_card_state
                    cid = ensure_card_state(random.choice(p.deck))
                    from ....data.card_upgrade_data import CARD_UPGRADE_CONFIG
                    if cid.id in CARD_UPGRADE_CONFIG and not cid.upgraded:
                        upg_cid = DeckService.upgrade_state(cid)
                        p.deck.remove(cid)
                        DeckService.add_card_to_deck(p, upg_cid)
                        cid = upg_cid
                    if random.random() < CAFE_PRICES["blacksmith_bonus_slot_chance"]:
                        card_obj = ALL_CARDS.get(cid.id)
                        if card_obj:
                            max_slots = card_obj.get_gem_slots_count()
                            old_gems = list(cid.gems)
                            if len(old_gems) < max_slots:
                                new_gems = old_gems + ["empty"]
                                upg_gem_cid = DeckService.clone_state(cid)
                                upg_gem_cid.gems = new_gems
                                p.deck.remove(cid)
                                DeckService.add_card_to_deck(p, upg_gem_cid)
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_blacksmith_forge_reward")
            elif idx == 2:
                if p.gold < CAFE_PRICES["blacksmith_slot_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=30)
                p.gold -= CAFE_PRICES["blacksmith_slot_cost"]
                if p.deck:
                    from ....models.state import ensure_card_state
                    cid = ensure_card_state(random.choice(p.deck))
                    card_obj = ALL_CARDS.get(cid.id)
                    if card_obj:
                        max_slots = card_obj.get_gem_slots_count()
                        old_gems = list(cid.gems)
                        if len(old_gems) < max_slots:
                            new_gems = old_gems + ["empty"]
                            new_cid = DeckService.clone_state(cid)
                            new_cid.gems = new_gems
                            p.deck.remove(cid)
                            DeckService.add_card_to_deck(p, new_cid)
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_blacksmith_slot_reward")
            else:
                return self.leave_npc(run)

        elif npc == "pppopipupu":
            if state == "start":
                if idx == 1:
                    cafe_data["dialog_state"] = "branch_a"
                    return get_locale_text("i18n_map_cafe.cafe_msg_fisher_start_a") + "\n\n" + self.render_cafe(run)
                elif idx == 2:
                    cafe_data["dialog_state"] = "branch_b"
                    return get_locale_text("i18n_map_cafe.cafe_msg_fisher_start_b") + "\n\n" + self.render_cafe(run)
                else:
                    return self.leave_npc(run)
            elif state == "branch_a":
                if idx == 1:
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    run.node_data["cafe_data"] = cafe_data
                    from ..explore_engine import ExploreEngine
                    expl = ExploreEngine(self.save_manager, self.map_engine)
                    expl.start_gem_insert_flow(run, "gem_return_5", "cafe", run.node_data.copy())
                    return get_locale_text("i18n_map_cafe.cafe_fisher_gem_reward")
                elif idx == 2:
                    p.gold = max(0, p.gold - CAFE_PRICES["pppopipupu_disturb_cost"])
                    from ....models.state import ensure_card_state
                    curses = [cid for cid in p.deck if ensure_card_state(cid).id.startswith("curse_")]
                    purged_msg = get_locale_text("i18n_map_cafe.cafe_fisher_purge_none")
                    if curses:
                        cur = curses[0]
                        p.deck.remove(cur)
                        purged_msg = get_locale_text("i18n_map_cafe.cafe_fisher_purge_curse", name=ALL_CARDS[cur].name)
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_fisher_disturb_reward", purged_msg=purged_msg)
                else:
                    return self.leave_npc(run)
            elif state == "branch_b":
                if idx == 1:
                    p.hp = max(CAFE_MIN_HP, p.hp - CAFE_PRICES["pppopipupu_hp_cost"])
                    p.relics.append("energy_core")
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_fisher_ice_reward")
                elif idx == 2:
                    p.gold = max(0, p.gold - CAFE_PRICES["pppopipupu_apology_cost"])
                    DeckService.add_card_to_deck(p, "neutral_hero_anthem")
                    self._close_dialog(cafe_data, talked_npcs, npc)
                    return get_locale_text("i18n_map_cafe.cafe_fisher_apology_reward")
                else:
                    return self.leave_npc(run)
        elif npc == "杰斯":
            stock = shared_cafe.get("card_master_stock", [])
            if idx <= len(stock):
                if p.gold < CAFE_PRICES["card_master_card_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=120)
                p.gold -= CAFE_PRICES["card_master_card_cost"]
                cid = stock[idx - 1]
                DeckService.add_card_to_deck(p, cid)
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_jace_buy_reward", name=ALL_CARDS[cid].name)
            else:
                return self.leave_npc(run)
        elif npc == "艾琳":
            stock = shared_cafe.get("gemcutter_stock", [])
            if idx == 1:
                if p.gold < CAFE_PRICES["gemcutter_slot_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=50)
                p.gold -= CAFE_PRICES["gemcutter_slot_cost"]
                if p.deck:
                    valid_cards = []
                    for c in p.deck:
                        card_obj = ALL_CARDS.get(c.id)
                        if card_obj:
                            max_slots = card_obj.get_gem_slots_count()
                            if len(c.gems) < max_slots:
                                valid_cards.append(c)
                    if valid_cards:
                        random.choice(valid_cards).gems.append("empty")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_erin_slot_reward")
            elif idx - 1 <= len(stock):
                if p.gold < CAFE_PRICES["gemcutter_gem_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=64)
                p.gold -= CAFE_PRICES["gemcutter_gem_cost"]
                gem_id = stock[idx - 2]
                self._close_dialog(cafe_data, talked_npcs, npc)
                run.node_data["cafe_data"] = cafe_data
                from ..explore_engine import ExploreEngine
                expl = ExploreEngine(self.save_manager, self.map_engine)
                expl.start_gem_insert_flow(run, gem_id, "cafe", run.node_data.copy())
                return get_locale_text("i18n_map_cafe.cafe_erin_gem_reward", name=GEM_CONFIG[gem_id]['name'])
            else:
                return self.leave_npc(run)
        elif npc == "雷恩":
            if idx == 1:
                if p.gold < CAFE_PRICES["gladiator_gold_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=50)
                p.gold -= CAFE_PRICES["gladiator_gold_cost"]
                p.max_hp += CAFE_PRICES["gladiator_max_hp_gain"]
                p.hp += CAFE_PRICES["gladiator_max_hp_gain"]
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_rain_training_reward")
            elif idx == 2:
                p.hp = max(CAFE_MIN_HP, p.hp - CAFE_PRICES["gladiator_hp_cost"])
                p.relics.append("gladiator_belt")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_rain_belt_reward")
            else:
                return self.leave_npc(run)
        elif npc == "露娜":
            if idx == 1:
                p.hp = max(CAFE_MIN_HP, p.hp - CAFE_PRICES["astrologer_hp_cost"])
                DeckService.add_card_to_deck(p, "neutral_astral_strike")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_luna_strike_reward")
            elif idx == 2:
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_luna_lore")
            else:
                return self.leave_npc(run)

        elif npc == "莫里":
            if idx == 1:
                if p.gold < CAFE_PRICES["cook_coffee_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=60)
                p.gold -= CAFE_PRICES["cook_coffee_cost"]
                p.relics.append("espresso_relic")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_mori_coffee_reward")
            elif idx == 2:
                if p.gold < CAFE_PRICES["cook_donut_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=40)
                p.gold -= CAFE_PRICES["cook_donut_cost"]
                p.hp = min(p.max_hp, p.hp + CAFE_PRICES["cook_donut_heal"])
                DeckService.add_card_to_deck(p, "curse_indigestion")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_mori_donut_reward")
            else:
                return self.leave_npc(run)

        elif npc == "凯尔":
            if idx == 1:
                if not p.relics:
                    return get_locale_text("i18n_map_cafe.cafe_err_no_relic_to_sell")
                rid = p.relics.pop(0)
                p.gold += CAFE_PRICES["hunter_sell_reward"]
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_kyle_sell_reward", name=get_relic_name(rid))
            elif idx == 2:
                if p.gold < CAFE_PRICES["hunter_buy_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=120)
                p.gold -= CAFE_PRICES["hunter_buy_cost"]
                rid = shared_cafe.get("hunter_stock")
                if not rid:
                    rid = "heavy_armor"
                p.relics.append(rid)
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_kyle_buy_reward", name=get_relic_name(rid))
            else:
                return self.leave_npc(run)

        elif npc == "咪咪":
            if idx == 1:
                self._close_dialog(cafe_data, talked_npcs, npc)
                if random.random() < CAFE_PRICES["cat_claw_chance"]:
                    p.hp = max(CAFE_MIN_HP, p.hp - CAFE_PRICES["cat_claw_hp_cost"])
                    from ..explore_engine import ExploreEngine
                    expl = ExploreEngine(self.save_manager, self.map_engine)
                    expl.start_gem_insert_flow(run, "gem_dmg_add_2", "cafe", run.node_data.copy())
                    return get_locale_text("i18n_map_cafe.cafe_mimi_claw_reward")
                else:
                    p.gold += CAFE_PRICES["cat_gold_reward"]
                    return get_locale_text("i18n_map_cafe.cafe_mimi_gold_reward")
            elif idx == 2:
                if p.gold < CAFE_PRICES["cat_fish_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=15)
                p.gold -= CAFE_PRICES["cat_fish_cost"]
                cafe_data["dialog_state"] = "branch_a"
                return get_locale_text("i18n_map_cafe.cafe_mimi_fish_msg") + "\n\n" + self.render_cafe(run)
            else:
                return self.leave_npc(run)

        elif npc == "咪咪" and state == "branch_a":
            if idx == 1:
                self._close_dialog(cafe_data, talked_npcs, npc)
                if random.random() < CAFE_PRICES["cat_gem_chance"]:
                    from ..explore_engine import ExploreEngine
                    expl = ExploreEngine(self.save_manager, self.map_engine)
                    expl.start_gem_insert_flow(run, "gem_shield_add_8", "cafe", run.node_data.copy())
                    return get_locale_text("i18n_map_cafe.cafe_mimi_gem_reward")
                else:
                    p.hp = max(CAFE_MIN_HP, p.hp - CAFE_PRICES["cat_pet_hp_cost"])
                    return get_locale_text("i18n_map_cafe.cafe_mimi_bite")
            elif idx == 2:
                from ....models.state import ensure_card_state
                curses = [cid for cid in p.deck if ensure_card_state(cid).id.startswith("curse_")]
                purged_msg = get_locale_text("i18n_map_cafe.cafe_mimi_purge_none")
                if curses:
                    cur = curses[0]
                    p.deck.remove(cur)
                    purged_msg = get_locale_text("i18n_map_cafe.cafe_mimi_purge_curse", name=ALL_CARDS[cur].name)
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_mimi_fish_reward", purged_msg=purged_msg)
            else:
                return self.leave_npc(run)

        elif npc == "萨拉":
            if idx == 1:
                non_retained = [c for c in p.deck if "gem_retain" not in c.gems]
                if not non_retained:
                    non_retained = p.deck.copy()
                if non_retained:
                    card_to_stitch = random.choice(non_retained)
                    card_to_stitch.gems.append("gem_retain")
                    card_to_stitch.power_penalty += CAFE_PRICES["tailor_penalty"]
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_sara_retain_reward")
            elif idx == 2:
                if p.gold < CAFE_PRICES["tailor_fission_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=80)
                p.gold -= CAFE_PRICES["tailor_fission_cost"]
                attacks = []
                for c in p.deck:
                    card_obj = ALL_CARDS.get(c.id)
                    if card_obj and card_obj.type == "attack" and "gem_copy_1" not in c.gems:
                        attacks.append(c)
                if not attacks:
                    attacks = [c for c in p.deck if "gem_copy_1" not in c.gems]
                if attacks:
                    random.choice(attacks).gems.append("gem_copy_1")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_sara_copy_reward")
            else:
                return self.leave_npc(run)

        elif npc == "辛普森":
            if idx == 1:
                p.relics.append("anthem_relic_3")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_simpson_anthem_reward")
            elif idx == 2:
                if p.gold < CAFE_PRICES["bard_song_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=30)
                p.gold -= CAFE_PRICES["bard_song_cost"]
                DeckService.add_card_to_deck(p, "neutral_hero_anthem")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_simpson_card_reward")
            else:
                return self.leave_npc(run)

        elif npc == "斯莱克":
            if idx == 1:
                if p.gold < CAFE_PRICES["black_market_gem_cost"]:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=240)
                p.gold -= CAFE_PRICES["black_market_gem_cost"]
                legendary_gems = [k for k, v in GEM_CONFIG.items() if v.get("rarity") == "legendary"]
                gem_id = random.choice(legendary_gems) if legendary_gems else "gem_dmg_mul_3"
                self._close_dialog(cafe_data, talked_npcs, npc)
                run.node_data["cafe_data"] = cafe_data
                from ..explore_engine import ExploreEngine
                expl = ExploreEngine(self.save_manager, self.map_engine)
                expl.start_gem_insert_flow(run, gem_id, "cafe", run.node_data.copy())
                return get_locale_text("i18n_map_cafe.cafe_slake_gem_reward", name=GEM_CONFIG[gem_id]['name'])
            elif idx == 2:
                epic_gems = [k for k, v in GEM_CONFIG.items() if v.get("rarity") == "epic"]
                gem_id = random.choice(epic_gems) if epic_gems else "gem_copy_1"
                DeckService.add_card_to_deck(p, "curse_mana_backflow")
                self._close_dialog(cafe_data, talked_npcs, npc)
                run.node_data["cafe_data"] = cafe_data
                from ..explore_engine import ExploreEngine
                expl = ExploreEngine(self.save_manager, self.map_engine)
                expl.start_gem_insert_flow(run, gem_id, "cafe", run.node_data.copy())
                return get_locale_text("i18n_map_cafe.cafe_slake_curse_gem_reward", name=GEM_CONFIG[gem_id]['name'])
            else:
                return self.leave_npc(run)

        elif npc == "编号7":
            if idx == 1:
                run.node_data["temp_minus_1a"] = True
                p.relics.append("shield_battery")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_unit7_battery_reward")
            elif idx == 2:
                self._close_dialog(cafe_data, talked_npcs, npc)
                if random.random() < CAFE_PRICES["guard_explode_chance"]:
                    p.gold += CAFE_PRICES["guard_gold_reward"]
                    return get_locale_text("i18n_map_cafe.cafe_unit7_explode_reward")
                else:
                    p.hp = max(CAFE_MIN_HP, p.hp - CAFE_PRICES["guard_explosion_hp_cost"])
                    return get_locale_text("i18n_map_cafe.cafe_unit7_explosion")
            else:
                return self.leave_npc(run)

        elif npc == "绯红":
            if idx == 1:
                loss = int(p.max_hp * CAFE_PRICES["crimson_hp_rate"])
                p.max_hp = max(CAFE_MIN_MAX_HP, p.max_hp - loss)
                p.hp = min(p.hp, p.max_hp)
                p.relics.append("crimson_heart")
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_crimson_drain_reward", loss=loss)
            elif idx == 2:
                removed_name = get_locale_text("i18n_map_cafe.cafe_none")
                if p.deck:
                    cid = random.choice(p.deck)
                    from ....models.state import ensure_card_state
                    card_obj = ALL_CARDS.get(ensure_card_state(cid).id)
                    removed_name = card_obj.name if card_obj else ensure_card_state(cid).id
                    p.deck.remove(cid)
                p.max_hp += CAFE_PRICES["crimson_max_hp_gain"]
                p.hp += CAFE_PRICES["crimson_max_hp_gain"]
                self._close_dialog(cafe_data, talked_npcs, npc)
                return get_locale_text("i18n_map_cafe.cafe_crimson_kiss_reward", removed_name=removed_name)
            else:
                return self.leave_npc(run)

        return self.leave_npc(run)
