import random
from typing import Optional, Dict, Any
from ...models.state import UserStats
from ...cards import ALL_CARDS
from ...entities.cards.market import get_market_price

def handle_sub_dialog(town_engine, stats: UserStats, npc_id: str, choice_lower: str, choice: str, user_id: str, zh_cn: Dict[str, Any]) -> Optional[str]:
    jack_riddle_step = stats.town_flags.get("jack_riddle_step")
    if npc_id == "Bartender_Jack" and jack_riddle_step:
        if choice_lower == "5":
            stats.town_flags.pop("jack_riddle_step", None)
            town_engine.save_manager.save_stats(user_id, stats)
            return town_engine._render_dialog_window(stats, npc_id, zh_cn)
        if jack_riddle_step == 1:
            if choice_lower == "2":
                stats.town_flags["jack_riddle_step"] = 2
                town_engine.save_manager.save_stats(user_id, stats)
                return town_engine._render_dialog_window(stats, npc_id, zh_cn)
            elif choice_lower in ("1", "3", "4"):
                stats.town_flags.pop("jack_riddle_step", None)
                town_engine.save_manager.save_stats(user_id, stats)
                return zh_cn.get("global", {}).get("jack_riddle_wrong", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)
        elif jack_riddle_step == 2:
            if choice_lower == "2":
                stats.town_flags.pop("jack_riddle_step", None)
                stats.town_inventory.append("promotional_agreement")
                town_engine.save_manager.save_stats(user_id, stats)
                return zh_cn.get("global", {}).get("jack_riddle_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)
            elif choice_lower in ("1", "3", "4"):
                stats.town_flags.pop("jack_riddle_step", None)
                town_engine.save_manager.save_stats(user_id, stats)
                return zh_cn.get("global", {}).get("jack_riddle_wrong", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)
        return zh_cn.get("global", {}).get("invalid_option", "")

    jack_agreement_menu = stats.town_flags.get("jack_agreement_menu")
    if npc_id == "Bartender_Jack" and jack_agreement_menu:
        options_count = 2 if "lost_notebook" in stats.town_inventory else 1
        if choice_lower == str(options_count + 1):
            stats.town_flags.pop("jack_agreement_menu", None)
            town_engine.save_manager.save_stats(user_id, stats)
            return town_engine._render_dialog_window(stats, npc_id, zh_cn)
        if "lost_notebook" in stats.town_inventory:
            if choice_lower == "1":
                stats.town_flags.pop("jack_agreement_menu", None)
                stats.town_inventory.remove("lost_notebook")
                stats.town_inventory.append("promotional_agreement")
                town_engine.save_manager.save_stats(user_id, stats)
                return zh_cn.get("global", {}).get("jack_notebook_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)
            elif choice_lower == "2":
                stats.town_flags.pop("jack_agreement_menu", None)
                stats.town_flags["jack_riddle_step"] = 1
                town_engine.save_manager.save_stats(user_id, stats)
                return town_engine._render_dialog_window(stats, npc_id, zh_cn)
        else:
            if choice_lower == "1":
                stats.town_flags.pop("jack_agreement_menu", None)
                stats.town_flags["jack_riddle_step"] = 1
                town_engine.save_manager.save_stats(user_id, stats)
                return town_engine._render_dialog_window(stats, npc_id, zh_cn)
        return zh_cn.get("global", {}).get("invalid_option", "")

    sub_menu = stats.town_flags.get("market_sub_menu")
    if npc_id == "Market_Merchant" and sub_menu == "lock":
        if choice_lower == "1":
            stats.town_flags.pop("market_sub_menu", None)
            town_engine.save_manager.save_stats(user_id, stats)
            return town_engine._render_dialog_window(stats, npc_id, zh_cn)
        target_cid = None
        from ...entities.cards.base import _get_card_config
        card_config = _get_card_config()
        for cid, cfg in card_config.items():
            if cfg.get("name") == choice:
                target_cid = cid
                break
        if not target_cid:
            return zh_cn.get("global", {}).get("card_lock_failed_not_found", "").format(name=choice)
        c_obj = ALL_CARDS[target_cid]
        if getattr(c_obj, "rarity", "common") in ("legendary", "mythic", "artifact", "curse"):
            return zh_cn.get("global", {}).get("card_lock_failed_legendary", "")
        if target_cid in getattr(stats, "locked_cards", []):
            return f"❌ 锁定失败：卡牌【{choice}】已经在你的锁定列表中了。"
        if len(getattr(stats, "locked_cards", [])) >= 8:
            return "❌ 锁定失败：最多只能同时锁定 8 张卡牌。"
        if stats.gp < 300:
            return zh_cn.get("global", {}).get("gp_insufficient", "").format(req=300, owned=stats.gp)
        stats.gp -= 300
        if not hasattr(stats, "locked_cards") or stats.locked_cards is None:
            stats.locked_cards = []
        stats.locked_cards.append(target_cid)
        stats.town_flags.pop("market_sub_menu", None)
        town_engine.save_manager.save_stats(user_id, stats)
        res_msg = zh_cn.get("global", {}).get("card_lock_success", "").format(name=choice)
        return res_msg + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    if npc_id == "Market_Merchant" and sub_menu == "buy":
        shelf = town_engine._get_market_shelf(stats)
        if choice_lower == str(len(shelf) + 1):
            stats.town_flags.pop("market_sub_menu", None)
            town_engine.save_manager.save_stats(user_id, stats)
            return town_engine._render_dialog_window(stats, npc_id, zh_cn)
        if choice_lower.isdigit() and 1 <= int(choice_lower) <= len(shelf):
            idx = int(choice_lower) - 1
            cid = shelf[idx]
            if not cid:
                return zh_cn.get("global", {}).get("card_buy_not_on_shelf", "").format(name="")
            
            card_obj = ALL_CARDS.get(cid)
            price = get_market_price(cid, card_obj)

            if stats.gp < price:
                return zh_cn.get("global", {}).get("gp_insufficient", "").format(req=price, owned=stats.gp)
            c_name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
            stats.gp -= price
            stats.purchased_pool.append(cid)
            if not hasattr(stats, "unlocked_new_cards"):
                stats.unlocked_new_cards = []
            if cid not in stats.unlocked_new_cards:
                stats.unlocked_new_cards.append(cid)
            shelf[idx] = ""
            stats.town_flags["market_shelf"] = shelf
            town_engine.save_manager.save_stats(user_id, stats)
            res_msg = zh_cn.get("global", {}).get("card_buy_success", "").format(price=price, name=c_name)
            return res_msg + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)
        return zh_cn.get("global", {}).get("invalid_option", "")

    shop_sub = stats.town_flags.get("shop_sub_menu")
    if npc_id == "Shopkeeper_Jack" and shop_sub == "buy_subclass":
        from ...models.manager import SaveManager
        boss_cfg = SaveManager().load_admin_config()
        icerainboww_enabled = boss_cfg.get("icerainboww_enabled", True)
        from ...data.shop_data import SHOP_ITEMS
        unlocked = getattr(stats, "unlocked_subclasses", [])
        has_gatekey = getattr(stats, "unlocked_gatekey", False)
        items_list = [
            ("时序法师", SHOP_ITEMS["时序法师"]["price"], "时序法师" in unlocked, True),
            ("塑能法师", SHOP_ITEMS["塑能法师"]["price"], "塑能法师" in unlocked, True),
            ("秘钥学者", SHOP_ITEMS["秘钥学者"]["price"], "秘钥学者" in unlocked, True),
            ("门之钥匙", SHOP_ITEMS["门之钥匙"]["price"], has_gatekey, True),
            ("神秘物品", SHOP_ITEMS["神秘物品"]["price"], "神秘物品" in unlocked, True)
        ]
        if icerainboww_enabled:
            killed_icerainboww = getattr(stats, "killed_icerainboww", False)
            items_list.append(("Icerainboww" if killed_icerainboww else "？？？", None, killed_icerainboww, False))
        killed_yog = getattr(stats, "yog_sothoth_kill_count", 0) > 0
        items_list.append(("尤格-索托斯" if killed_yog else "？？？", None, killed_yog, False))
        back_idx = len(items_list) + 1
        if choice_lower == str(back_idx):
            stats.town_flags.pop("shop_sub_menu", None)
            town_engine.save_manager.save_stats(user_id, stats)
            return town_engine._render_dialog_window(stats, npc_id, zh_cn)
        try:
            choice_val = int(choice_lower)
            if 1 <= choice_val <= len(items_list):
                name, price, is_unlocked, buyable = items_list[choice_val - 1]
                if not buyable:
                    return f"❌ 【{name}】为通关解锁内容，无需在此处购买。"
                if name == "门之钥匙":
                    if has_gatekey:
                        return zh_cn.get("global", {}).get("already_unlocked_error", "❌ 你已经解锁了【{name}】。").format(name=name)
                else:
                    if name in unlocked:
                        return zh_cn.get("global", {}).get("already_unlocked_error", "❌ 你已经解锁了【{name}】。").format(name=name)
                if stats.gp < price:
                    return zh_cn.get("global", {}).get("gp_insufficient", "").format(req=price, owned=stats.gp)
                stats.gp -= price
                if name == "门之钥匙":
                    stats.unlocked_gatekey = True
                else:
                    stats.unlocked_subclasses.append(name)
                town_engine.save_manager.save_stats(user_id, stats)
                success_msg = zh_cn.get("global", {}).get("shop_buy_success", "").format(name=name, price=price)
                return success_msg + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)
        except ValueError:
            pass
        return zh_cn.get("global", {}).get("invalid_option", "")

    return None

def process_dialog_action(town_engine, stats: UserStats, npc_id: str, action: str, choice_lower: str, user_id: str, zh_cn: Dict[str, Any]) -> str:
    entities = zh_cn.get("interactive_entities", {})
    npc_data = entities.get(npc_id, {})

    if action == "idle":
        quotes = npc_data.get("idle_talk", [])
        q = random.choice(quotes) if quotes else "..."
        return q + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "quest_accept":
        stats.town_flags["quest_town_tour_state"] = "started"
        stats.town_flags["quest_town_tour_visited"] = ["square"]
        town_engine.save_manager.save_stats(user_id, stats)
        return npc_data.get("quest_accepted", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "quest_status":
        visited = stats.town_flags.get("quest_town_tour_visited", [])
        return npc_data.get("quest_doing", "").format(progress=len(visited)) + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "quest_complete":
        stats.town_flags["quest_town_tour_state"] = "completed"
        stats.gp += 2000
        town_engine.save_manager.save_stats(user_id, stats)
        return npc_data.get("quest_completed_msg", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "gift_glass":
        stats.town_inventory.remove("wine_glass")
        stats.town_flags["jack_gift_given"] = 1
        stats.gp += 150
        town_engine.save_manager.save_stats(user_id, stats)
        return npc_data.get("gift_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "gift_ore":
        stats.town_inventory.remove("strange_ore")
        stats.town_flags["ironclad_gift_given"] = 1
        stats.gp += 200
        town_engine.save_manager.save_stats(user_id, stats)
        return npc_data.get("gift_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "buy_shelf":
        stats.town_flags["market_sub_menu"] = "buy"
        town_engine.save_manager.save_stats(user_id, stats)
        return town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "lock_card":
        stats.town_flags["market_sub_menu"] = "lock"
        town_engine.save_manager.save_stats(user_id, stats)
        return town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "buy_subclass":
        stats.town_flags["shop_sub_menu"] = "buy_subclass"
        town_engine.save_manager.save_stats(user_id, stats)
        return town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "open_box":
        stats.town_inventory.remove("rusty_key")
        stats.town_flags["box_opened"] = 1
        stats.gp += 300
        if not hasattr(stats, "locked_cards") or stats.locked_cards is None:
            stats.locked_cards = []
        if "discover" not in stats.locked_cards and len(stats.locked_cards) < 8:
            stats.locked_cards.append("discover")
        town_engine.save_manager.save_stats(user_id, stats)
        return npc_data.get("open_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "wish":
        stats.town_inventory.remove("lucky_coin")
        effects = ["gp", "card", "hp"]
        c_effect = random.choice(effects)
        if c_effect == "gp":
            stats.gp += 200
            res = npc_data.get("wish_success_gp", "")
        elif c_effect == "card":
            if not hasattr(stats, "locked_cards") or stats.locked_cards is None:
                stats.locked_cards = []
            if "discover" not in stats.locked_cards and len(stats.locked_cards) < 8:
                stats.locked_cards.append("discover")
            res = npc_data.get("wish_success_card", "")
        else:
            stats.town_health_bonus += 5
            res = npc_data.get("wish_success_hp", "")
        town_engine.save_manager.save_stats(user_id, stats)
        return res + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "knock":
        count = stats.town_flags.get("knock_count", 0) + 1
        stats.town_flags["knock_count"] = count
        town_engine.save_manager.save_stats(user_id, stats)
        if count == 3:
            if not stats.town_flags.get("west_gate_bonus_claimed", 0):
                stats.town_flags["west_gate_bonus_claimed"] = 1
                stats.gp += 100
                town_engine.save_manager.save_stats(user_id, stats)
            return npc_data.get("knock_bonus_3", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)
        elif count == 10:
            stats.town_flags.pop("current_dialog", None)
            town_engine.save_manager.save_stats(user_id, stats)
            return town_engine.challenge_npc(user_id, "Gate_Guardian")
        return npc_data.get("knock_normal", "").format(count=count) + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "challenge":
        stats.town_flags.pop("current_dialog", None)
        town_engine.save_manager.save_stats(user_id, stats)
        return town_engine.challenge_npc(user_id, npc_id)

    elif action == "buy_beer":
        if stats.gp < 50:
            return zh_cn.get("global", {}).get("beer_buy_insufficient", "")
        stats.gp -= 50
        stats.town_inventory.append("beer")
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("beer_buy_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "brew_quest_accept":
        stats.town_flags["quest_brew_state"] = "started"
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("quest_brew_started", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "give_wishing_dew":
        stats.town_flags["quest_brew_state"] = "completed"
        stats.town_inventory.remove("wishing_dew")
        stats.gp += 1500
        stats.town_health_bonus = getattr(stats, "town_health_bonus", 0) + 5
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("quest_brew_real_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "dialog_sign_agreement":
        stats.town_flags["jack_agreement_menu"] = True
        town_engine.save_manager.save_stats(user_id, stats)
        return town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "quest_hammer_accept":
        stats.town_flags["quest_hammer_state"] = "started"
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("quest_hammer_started", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "quest_hammer_clue":
        return zh_cn.get("global", {}).get("quest_hammer_clue_msg", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "quest_hammer_return_real":
        stats.town_flags["quest_hammer_state"] = "completed"
        stats.town_inventory.remove("smith_hammer")
        stats.gp += 1500
        stats.town_health_bonus = getattr(stats, "town_health_bonus", 0) + 5
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("quest_hammer_real_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "quest_hammer_return_fake":
        stats.town_flags["quest_hammer_state"] = "completed"
        stats.town_inventory.remove("fake_hammer")
        stats.gp += 200
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("quest_hammer_fake_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "quest_hammer_return_force":
        stats.town_flags["quest_hammer_state"] = "completed"
        stats.gp += 1200
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("quest_hammer_force_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "ask_hammer":
        return zh_cn.get("global", {}).get("lost_bard_tell_clue", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "give_beer":
        stats.town_inventory.remove("beer")
        stats.town_inventory.append("smith_hammer")
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("lost_bard_give_beer_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "buy_fake_hammer":
        if stats.gp < 500:
            return zh_cn.get("global", {}).get("gp_insufficient", "").format(req=500, owned=stats.gp)
        stats.gp -= 500
        stats.town_inventory.append("fake_hammer")
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("buy_fake_hammer_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "buy_void_herb":
        if stats.gp < 800:
            return zh_cn.get("global", {}).get("gp_insufficient", "").format(req=800, owned=stats.gp)
        stats.gp -= 800
        stats.town_inventory.append("void_herb")
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("buy_void_herb_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "trade_void_herb":
        stats.town_inventory.remove("promotional_agreement")
        stats.town_inventory.append("void_herb")
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("trade_void_herb_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "report_whale":
        stats.town_flags["reported_whale"] = True
        stats.town_inventory.append("void_herb")
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("report_whale_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "wash_herb":
        stats.town_inventory.remove("void_herb")
        stats.town_inventory.append("wishing_dew")
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("wash_herb_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    elif action == "sell_wishing_dew":
        stats.town_flags["quest_brew_state"] = "completed"
        stats.town_inventory.remove("wishing_dew")
        stats.gp += 2000
        town_engine.save_manager.save_stats(user_id, stats)
        return zh_cn.get("global", {}).get("sell_dew_success", "") + "\n\n" + town_engine._render_dialog_window(stats, npc_id, zh_cn)

    return zh_cn.get("global", {}).get("invalid_option", "")
