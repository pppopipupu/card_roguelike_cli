import os
import json
import random
from typing import Optional, List, Dict, Any, Tuple
from ..models.state import UserStats, GameRun, PlayerState, EnemyState, BuffState
from ..entities import ALL_CARDS
from ..entities.cards.market import MARKET_SHELF_CARDS, get_market_price, is_card_available

class TownEngine:
    def __init__(self, save_manager, engine):
        self.save_manager = save_manager
        self.engine = engine

    def _load_zh_cn(self) -> Dict[str, Any]:
        from ..core.locale_manager import LocaleManager
        return LocaleManager.get_all_translations()

    def _load_room_data(self, room_id: str) -> Dict[str, Any]:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(os.path.dirname(current_dir), "data", "town", f"{room_id}.json")
        if not os.path.exists(data_path):
            return {"id": room_id, "name_key": room_id, "exits": {}, "npcs": [], "items": [], "interactive": {}}
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if room_id == "alley":
                from ..models.state import get_user_id
                uid = get_user_id()
                if uid:
                    stats = self.save_manager.load_stats(uid)
                    if stats.town_flags.get("quest_hammer_state") == "started" and not stats.town_flags.get("taken_smith_hammer"):
                        if "smith_hammer" not in data.get("items", []):
                            data.setdefault("items", []).append("smith_hammer")
            return data
        except:
            return {"id": room_id, "name_key": room_id, "exits": {}, "npcs": [], "items": [], "interactive": {}}

    def render_current_room(self, user_id: str, stats: UserStats) -> str:
        zh_cn = self._load_zh_cn()
        if stats.town_pos == "market":
            self._get_market_shelf(stats)
            self.save_manager.save_stats(user_id, stats)

        active_dialog = stats.town_flags.get("current_dialog")
        if active_dialog:
            return self._render_dialog_window(stats, active_dialog, zh_cn)

        from ..renderer.town import render_town
        room_data = self._load_room_data(stats.town_pos)
        return render_town(stats, room_data)

    def _render_dialog_window(self, stats: UserStats, npc_id: str, zh_cn: Dict[str, Any]) -> str:
        entities = zh_cn.get("interactive_entities", {})
        npc_data = entities.get(npc_id, {})
        npc_name = npc_data.get("name", npc_id)
        welcome_text = npc_data.get("welcome", "")
        player_name = getattr(stats, "player_name", "玩家")
        welcome_text = welcome_text.replace("{player_name}", player_name)

        options = []
        sub_menu = stats.town_flags.get("market_sub_menu")
        jack_riddle_step = stats.town_flags.get("jack_riddle_step")
        jack_agreement_menu = stats.town_flags.get("jack_agreement_menu")

        if npc_id == "Bartender_Jack" and jack_riddle_step:
            welcome_text = zh_cn.get("global", {}).get("jack_riddle_intro", "")
            if jack_riddle_step == 1:
                welcome_text += "\n\n" + zh_cn.get("global", {}).get("jack_riddle_1", "")
                options.append("1. 汽水")
                options.append("2. 薪水")
                options.append("3. 井水")
                options.append("4. 泪水")
            elif jack_riddle_step == 2:
                welcome_text += "\n\n" + zh_cn.get("global", {}).get("jack_riddle_2", "")
                options.append("1. 铁匠")
                options.append("2. 雪人")
                options.append("3. 卫兵")
                options.append("4. 诗人")
            options.append(f"{len(options)+1}. " + zh_cn.get("global", {}).get("back_to_previous", "返回上一级"))
        elif npc_id == "Bartender_Jack" and jack_agreement_menu:
            welcome_text = npc_data.get("welcome", "")
            if "lost_notebook" in stats.town_inventory:
                options.append(f"1. {npc_data.get('option_sign_by_notebook')}")
            options.append(f"{len(options)+1}. {npc_data.get('option_sign_by_riddle')}")
            options.append(f"{len(options)+1}. " + zh_cn.get("global", {}).get("back_to_previous", "返回上一级"))
        elif npc_id == "Market_Merchant" and sub_menu == "buy":
            shelf = self._get_market_shelf(stats)
            for idx, cid in enumerate(shelf):
                if not cid:
                    options.append(f"{idx+1}. " + zh_cn.get("global", {}).get("market_sold_out", "【已售罄】"))
                else:
                    c_name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
                    card_obj = ALL_CARDS.get(cid)
                    rarity_str = "普通"
                    price = 100
                    if card_obj:
                        r = getattr(card_obj, "rarity", "common")
                        if r == "common":
                            rarity_str = "普通"
                        elif r == "rare":
                            rarity_str = "稀有"
                        else:
                            rarity_str = "珍奇"
                    price = get_market_price(cid, card_obj)
                    options.append(zh_cn.get("global", {}).get("market_buy_option", "").format(idx=idx+1, name=c_name, rarity=rarity_str, price=price))
            options.append(f"{len(shelf)+1}. " + zh_cn.get("global", {}).get("back_to_previous", "返回上一级"))
        elif npc_id == "Market_Merchant" and sub_menu == "lock":
            options.append(zh_cn.get("global", {}).get("lock_instructions", "ℹ️ 请直接输入你想锁定的卡牌名称（例如输入 痛击 ）进行绑定。"))
            options.append(zh_cn.get("global", {}).get("back_to_previous_1", "1. 返回上一级"))
        elif npc_id == "Shopkeeper_Jack" and stats.town_flags.get("shop_sub_menu") == "buy_subclass":
            unlocked = getattr(stats, "unlocked_subclasses", [])
            has_gatekey = getattr(stats, "unlocked_gatekey", False)
            from ..models.manager import SaveManager
            boss_cfg = SaveManager().load_admin_config()
            icerainboww_enabled = boss_cfg.get("icerainboww_enabled", True)
            from ..data.shop_data import SHOP_ITEMS
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
            for idx, (name, price, is_unlocked, buyable) in enumerate(items_list):
                if buyable:
                    if is_unlocked:
                        options.append(f"{idx+1}. 购买 【{name}】 ({zh_cn.get('global', {}).get('unlocked_status', '已解锁')})")
                    else:
                        options.append(f"{idx+1}. 购买 【{name}】 ({price} GP)")
                else:
                    status_str = zh_cn.get('global', {}).get('unlocked_status', '已解锁') if is_unlocked else "未解锁"
                    options.append(f"{idx+1}. 【{name}】 ({status_str})")
            options.append(f"{len(items_list)+1}. " + zh_cn.get("global", {}).get("back_to_previous", "返回上一级"))
        else:
            if npc_id == "Crypto_Whale" and stats.town_flags.get("reported_whale"):
                welcome_text = zh_cn.get("global", {}).get("whale_reported_refuse", "")
            if npc_id not in ("Chest", "Fountain", "West_Gate"):
                if npc_id == "Crypto_Whale" and stats.town_flags.get("reported_whale"):
                    pass
                else:
                    options.append(f"1. {npc_data.get('option_idle', zh_cn.get('global', {}).get('idle_talk_default', '闲聊'))}")
            if npc_id == "Guide_Elder":
                quest_state = stats.town_flags.get("quest_town_tour_state", "unstarted")
                if quest_state == "unstarted":
                    options.append(f"{len(options)+1}. {npc_data.get('option_quest_accept')}")
                elif quest_state == "started":
                    visited = stats.town_flags.get("quest_town_tour_visited", [])
                    if len(visited) >= 11:
                        options.append(f"{len(options)+1}. {npc_data.get('option_quest_complete')}")
                    else:
                        options.append(f"{len(options)+1}. {npc_data.get('option_quest_status')}")
            elif npc_id == "Bartender_Jack":
                if "wine_glass" in stats.town_inventory and not stats.town_flags.get("jack_gift_given", 0):
                    options.append(f"{len(options)+1}. {npc_data.get('option_gift_glass')}")
                options.append(f"{len(options)+1}. {npc_data.get('option_buy_beer')}")
                q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
                if q_brew == "unstarted":
                    options.append(f"{len(options)+1}. {npc_data.get('option_brew_quest_accept')}")
                elif q_brew == "started":
                    if "wishing_dew" in stats.town_inventory:
                        options.append(f"{len(options)+1}. {npc_data.get('option_give_wishing_dew')}")
                    if "promotional_agreement" not in stats.town_inventory and "void_herb" not in stats.town_inventory and "wishing_dew" not in stats.town_inventory:
                        options.append(f"{len(options)+1}. {npc_data.get('option_dialog_sign_agreement')}")
            elif npc_id == "Blacksmith_Ironclad":
                if "strange_ore" in stats.town_inventory and not stats.town_flags.get("ironclad_gift_given", 0):
                    options.append(f"{len(options)+1}. {npc_data.get('option_gift_ore')}")
                q_ham = stats.town_flags.get("quest_hammer_state", "unstarted")
                if q_ham == "unstarted":
                    options.append(f"{len(options)+1}. {npc_data.get('option_quest_hammer_accept')}")
                elif q_ham == "started":
                    if stats.town_flags.get("noob_coerced_hammer"):
                        options.append(f"{len(options)+1}. {npc_data.get('option_return_hammer_force')}")
                    elif "smith_hammer" in stats.town_inventory:
                        options.append(f"{len(options)+1}. {npc_data.get('option_return_hammer_real')}")
                    if "fake_hammer" in stats.town_inventory:
                        options.append(f"{len(options)+1}. {npc_data.get('option_return_hammer_fake')}")
                    options.append(f"{len(options)+1}. {npc_data.get('option_quest_hammer_clue')}")
            elif npc_id == "Market_Merchant":
                options.append(f"{len(options)+1}. {npc_data.get('option_buy_shelf')}")
                options.append(f"{len(options)+1}. {npc_data.get('option_lock_card')}")
            elif npc_id == "Shopkeeper_Jack":
                options.append(f"{len(options)+1}. {npc_data.get('option_buy_subclass', '购买新子职业/门之钥匙...')}")
                q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
                if q_brew == "started" and "wishing_dew" in stats.town_inventory:
                    options.append(f"{len(options)+1}. {npc_data.get('option_sell_wishing_dew')}")
            elif npc_id == "Lost_Bard":
                q_ham = stats.town_flags.get("quest_hammer_state", "unstarted")
                if q_ham == "started" and not stats.town_flags.get("taken_smith_hammer") and not stats.town_flags.get("noob_coerced_hammer"):
                    options.append(f"{len(options)+1}. {npc_data.get('option_ask_hammer')}")
                    if "beer" in stats.town_inventory:
                        options.append(f"{len(options)+1}. {npc_data.get('option_give_beer')}")
            elif npc_id == "Crypto_Whale":
                if not stats.town_flags.get("reported_whale"):
                    q_ham = stats.town_flags.get("quest_hammer_state", "unstarted")
                    if q_ham == "started" and "smith_hammer" not in stats.town_inventory and "fake_hammer" not in stats.town_inventory and not stats.town_flags.get("noob_coerced_hammer"):
                        options.append(f"{len(options)+1}. {npc_data.get('option_buy_fake_hammer')}")
                    q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
                    if q_brew == "started" and "void_herb" not in stats.town_inventory and "wishing_dew" not in stats.town_inventory:
                        options.append(f"{len(options)+1}. {npc_data.get('option_buy_void_herb')}")
                        if "promotional_agreement" in stats.town_inventory:
                            options.append(f"{len(options)+1}. {npc_data.get('option_trade_void_herb')}")
            elif npc_id == "Town_Guard":
                q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
                if q_brew == "started" and "void_herb" not in stats.town_inventory and "wishing_dew" not in stats.town_inventory:
                    if not stats.town_flags.get("reported_whale"):
                        options.append(f"{len(options)+1}. {npc_data.get('option_report_whale')}")
            elif npc_id == "Chest":
                if "rusty_key" in stats.town_inventory and not stats.town_flags.get("box_opened", 0):
                    options.append(f"{len(options)+1}. {npc_data.get('option_open')}")
            elif npc_id == "Fountain":
                if "lucky_coin" in stats.town_inventory:
                    options.append(f"{len(options)+1}. {npc_data.get('option_wish')}")
                q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
                if q_brew == "started" and "void_herb" in stats.town_inventory:
                    options.append(f"{len(options)+1}. {npc_data.get('option_wash_herb')}")
            elif npc_id == "West_Gate":
                options.append(f"{len(options)+1}. {npc_data.get('option_knock')}")
            elif npc_id in ("Dummy", "NoobSlayer99", "xXx_SniperElite_xXx", "pppopipupu"):
                options.append(f"{len(options)+1}. {npc_data.get('option_challenge')}")

            leave_label = npc_data.get("option_leave", zh_cn.get("global", {}).get("leave_default", "离开"))
            options.append(f"{len(options)+1}. {leave_label}")

        menu_lines = "\n".join(options)
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            zh_cn.get("global", {}).get("dialog_title", "💬 与【{name}】对话中").format(name=npc_name),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            welcome_text,
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            menu_lines,
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            zh_cn.get("global", {}).get("dialog_help", "💡 输入选项编号(如 1, 2)进行互动，输入 离开/exit/quit 结束交谈。"),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        return "\n".join(lines)

    def _get_market_shelf(self, stats: UserStats) -> List[str]:
        already_bought = set(getattr(stats, "purchased_pool", []) or []) | set(getattr(stats, "unlocked_new_cards", []) or [])
        shelf = stats.town_flags.get("market_shelf")
        if not isinstance(shelf, list) or len(shelf) != len(MARKET_SHELF_CARDS) or any(c and c not in MARKET_SHELF_CARDS for c in shelf):
            shelf = [c if c not in already_bought else "" for c in MARKET_SHELF_CARDS]
        else:
            shelf = [c if (c and c not in already_bought) else "" for c in shelf]
        stats.town_flags["market_shelf"] = shelf
        return shelf

    def move(self, user_id: str, direction: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        room_data = self._load_room_data(stats.town_pos)
        exits = room_data.get("exits", {})
        dir_map = {"up": "w", "down": "s", "left": "a", "right": "d"}
        dir_key = direction.lower()
        dir_key = dir_map.get(dir_key, dir_key)

        if dir_key not in exits:
            zh_cn = self._load_zh_cn()
            return zh_cn.get("global", {}).get("move_no_way", "").format(exits=', '.join(exits.keys()).upper())

        target_room = exits[dir_key]
        stats.town_pos = target_room

        quest_state = stats.town_flags.get("quest_town_tour_state", "unstarted")
        if quest_state == "started":
            visited = stats.town_flags.setdefault("quest_town_tour_visited", [])
            if target_room not in visited:
                visited.append(target_room)

        if random.random() < 0.5:
            wandering_npcs = ["Gamer_Boy", "Crypto_Whale", "Lost_Bard", "Town_Guard", "Naughty_Child"]
            wandering_rooms = ["square", "fountain", "shop", "tavern", "alley"]
            for npc in wandering_npcs:
                if random.random() < 0.5:
                    stats.town_flags[f"pos_{npc}"] = random.choice(wandering_rooms)

        self.save_manager.save_stats(user_id, stats)
        target_room_data = self._load_room_data(target_room)
        from ..renderer.town import render_town
        return render_town(stats, target_room_data)

    def talk_npc(self, user_id: str, target_name: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        current_room = stats.town_pos
        room_data = self._load_room_data(current_room)
        zh_cn = self._load_zh_cn()

        visible_ids = []
        for n in room_data.get("npcs", []):
            visible_ids.append(n)

        wandering_npcs_config = ["Gamer_Boy", "Crypto_Whale", "Lost_Bard", "Town_Guard", "Naughty_Child"]
        for npc_id in wandering_npcs_config:
            npc_pos = stats.town_flags.get(f"pos_{npc_id}", "square")
            if npc_pos == current_room:
                visible_ids.append(npc_id)

        target_id = None
        target_lower = target_name.lower()
        entities = zh_cn.get("interactive_entities", {})
        for ent_id in visible_ids:
            ent_data = entities.get(ent_id, {})
            names = [ent_id.lower(), ent_data.get("name", "").lower()]
            if target_lower in names:
                target_id = ent_id
                break

        if not target_id:
            return zh_cn.get("global", {}).get("interact_not_found", "").format(target=target_name)

        stats.town_flags["current_dialog"] = target_id
        stats.town_flags.pop("market_sub_menu", None)
        self.save_manager.save_stats(user_id, stats)
        return self._render_dialog_window(stats, target_id, zh_cn)

    def handle_dialog_input(self, user_id: str, choice: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        npc_id = stats.town_flags.get("current_dialog")
        zh_cn = self._load_zh_cn()
        if not npc_id:
            return zh_cn.get("global", {}).get("not_in_dialog", "❌ 没有处于交谈状态。")

        entities = zh_cn.get("interactive_entities", {})
        npc_data = entities.get(npc_id, {})
        choice_lower = choice.lower().strip()

        if choice_lower in ("离开", "退出", "返回", "exit", "quit"):
            stats.town_flags.pop("current_dialog", None)
            stats.town_flags.pop("market_sub_menu", None)
            stats.town_flags.pop("shop_sub_menu", None)
            stats.town_flags.pop("jack_agreement_menu", None)
            stats.town_flags.pop("jack_riddle_step", None)
            self.save_manager.save_stats(user_id, stats)
            return zh_cn.get("global", {}).get("dialog_exit", "").format(name=npc_data.get("name", npc_id)) + "\n\n" + self.render_current_room(user_id, stats)

        from .town.dialog_handler import handle_sub_dialog, process_dialog_action
        sub_res = handle_sub_dialog(self, stats, npc_id, choice_lower, choice, user_id, zh_cn)
        if sub_res is not None:
            return sub_res

        options_map = self._get_options_map(stats, npc_id)
        if choice_lower not in options_map:
            return zh_cn.get("global", {}).get("invalid_option", "")

        action = options_map[choice_lower]
        if action == "leave":
            stats.town_flags.pop("current_dialog", None)
            stats.town_flags.pop("market_sub_menu", None)
            stats.town_flags.pop("shop_sub_menu", None)
            stats.town_flags.pop("jack_agreement_menu", None)
            stats.town_flags.pop("jack_riddle_step", None)
            self.save_manager.save_stats(user_id, stats)
            return zh_cn.get("global", {}).get("dialog_exit", "").format(name=npc_data.get("name", npc_id)) + "\n\n" + self.render_current_room(user_id, stats)

        return process_dialog_action(self, stats, npc_id, action, choice_lower, user_id, zh_cn)

    def _get_options_map(self, stats: UserStats, npc_id: str) -> Dict[str, str]:
        options_map = {}
        opt_idx = 1
        if npc_id == "Crypto_Whale" and stats.town_flags.get("reported_whale"):
            pass
        else:
            options_map[str(opt_idx)] = "idle"
            opt_idx += 1

        if npc_id == "Guide_Elder":
            quest_state = stats.town_flags.get("quest_town_tour_state", "unstarted")
            if quest_state == "unstarted":
                options_map[str(opt_idx)] = "quest_accept"
                opt_idx += 1
            elif quest_state == "started":
                visited = stats.town_flags.get("quest_town_tour_visited", [])
                if len(visited) >= 11:
                    options_map[str(opt_idx)] = "quest_complete"
                else:
                    options_map[str(opt_idx)] = "quest_status"
                opt_idx += 1
        elif npc_id == "Bartender_Jack":
            if "wine_glass" in stats.town_inventory and not stats.town_flags.get("jack_gift_given", 0):
                options_map[str(opt_idx)] = "gift_glass"
                opt_idx += 1
            options_map[str(opt_idx)] = "buy_beer"
            opt_idx += 1
            q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
            if q_brew == "unstarted":
                options_map[str(opt_idx)] = "brew_quest_accept"
                opt_idx += 1
            elif q_brew == "started":
                if "wishing_dew" in stats.town_inventory:
                    options_map[str(opt_idx)] = "give_wishing_dew"
                    opt_idx += 1
                if "promotional_agreement" not in stats.town_inventory and "void_herb" not in stats.town_inventory and "wishing_dew" not in stats.town_inventory:
                    options_map[str(opt_idx)] = "dialog_sign_agreement"
                    opt_idx += 1
        elif npc_id == "Blacksmith_Ironclad":
            if "strange_ore" in stats.town_inventory and not stats.town_flags.get("ironclad_gift_given", 0):
                options_map[str(opt_idx)] = "gift_ore"
                opt_idx += 1
            q_ham = stats.town_flags.get("quest_hammer_state", "unstarted")
            if q_ham == "unstarted":
                options_map[str(opt_idx)] = "quest_hammer_accept"
                opt_idx += 1
            elif q_ham == "started":
                if stats.town_flags.get("noob_coerced_hammer"):
                    options_map[str(opt_idx)] = "quest_hammer_return_force"
                    opt_idx += 1
                elif "smith_hammer" in stats.town_inventory:
                    options_map[str(opt_idx)] = "quest_hammer_return_real"
                    opt_idx += 1
                if "fake_hammer" in stats.town_inventory:
                    options_map[str(opt_idx)] = "quest_hammer_return_fake"
                    opt_idx += 1
                options_map[str(opt_idx)] = "quest_hammer_clue"
                opt_idx += 1
        elif npc_id == "Market_Merchant":
            options_map[str(opt_idx)] = "buy_shelf"
            opt_idx += 1
            options_map[str(opt_idx)] = "lock_card"
            opt_idx += 1
        elif npc_id == "Shopkeeper_Jack":
            options_map[str(opt_idx)] = "buy_subclass"
            opt_idx += 1
            q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
            if q_brew == "started" and "wishing_dew" in stats.town_inventory:
                options_map[str(opt_idx)] = "sell_wishing_dew"
                opt_idx += 1
        elif npc_id == "Lost_Bard":
            q_ham = stats.town_flags.get("quest_hammer_state", "unstarted")
            if q_ham == "started" and not stats.town_flags.get("taken_smith_hammer") and not stats.town_flags.get("noob_coerced_hammer"):
                options_map[str(opt_idx)] = "ask_hammer"
                opt_idx += 1
                if "beer" in stats.town_inventory:
                    options_map[str(opt_idx)] = "give_beer"
                    opt_idx += 1
        elif npc_id == "Crypto_Whale":
            if not stats.town_flags.get("reported_whale"):
                q_ham = stats.town_flags.get("quest_hammer_state", "unstarted")
                if q_ham == "started" and "smith_hammer" not in stats.town_inventory and "fake_hammer" not in stats.town_inventory and not stats.town_flags.get("noob_coerced_hammer"):
                    options_map[str(opt_idx)] = "buy_fake_hammer"
                    opt_idx += 1
                q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
                if q_brew == "started" and "void_herb" not in stats.town_inventory and "wishing_dew" not in stats.town_inventory:
                    options_map[str(opt_idx)] = "buy_void_herb"
                    opt_idx += 1
                    if "promotional_agreement" in stats.town_inventory:
                        options_map[str(opt_idx)] = "trade_void_herb"
                        opt_idx += 1
        elif npc_id == "Town_Guard":
            q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
            if q_brew == "started" and "void_herb" not in stats.town_inventory and "wishing_dew" not in stats.town_inventory:
                if not stats.town_flags.get("reported_whale"):
                    options_map[str(opt_idx)] = "report_whale"
                    opt_idx += 1
        elif npc_id == "Chest":
            options_map = {}
            opt_idx = 1
            if "rusty_key" in stats.town_inventory and not stats.town_flags.get("box_opened", 0):
                options_map[str(opt_idx)] = "open_box"
                opt_idx += 1
        elif npc_id == "Fountain":
            options_map = {}
            opt_idx = 1
            if "lucky_coin" in stats.town_inventory:
                options_map[str(opt_idx)] = "wish"
                opt_idx += 1
            q_brew = stats.town_flags.get("quest_brew_state", "unstarted")
            if q_brew == "started" and "void_herb" in stats.town_inventory:
                options_map[str(opt_idx)] = "wash_herb"
                opt_idx += 1
        elif npc_id == "West_Gate":
            options_map = {}
            opt_idx = 1
            options_map[str(opt_idx)] = "knock"
            opt_idx += 1
        elif npc_id in ("Dummy", "NoobSlayer99", "xXx_SniperElite_xXx", "pppopipupu"):
            options_map[str(opt_idx)] = "challenge"
            opt_idx += 1

        options_map[str(opt_idx)] = "leave"
        return options_map

    def pick_item(self, user_id: str, item_name: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        current_room = stats.town_pos
        room_data = self._load_room_data(current_room)
        items = room_data.get("items", [])
        zh_cn = self._load_zh_cn()

        target_id = None
        target_lower = item_name.lower()
        items_config = zh_cn.get("items", {})
        for key, names in items_config.items():
            if target_lower in [x.lower() for x in names]:
                target_id = key
                break

        if not target_id or target_id not in items:
            return zh_cn.get("global", {}).get("take_not_found", "").format(target=item_name)
            
        if stats.town_flags.get(f"taken_{target_id}", 0):
            return zh_cn.get("global", {}).get("take_already_taken", "").format(target=item_name)

        stats.town_inventory.append(target_id)
        stats.town_flags[f"taken_{target_id}"] = 1
        self.save_manager.save_stats(user_id, stats)
        
        display_name = items_config[target_id][0]
        return zh_cn.get("global", {}).get("take_success", "").format(target=display_name)

    def use_item(self, user_id: str, item_name: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        zh_cn = self._load_zh_cn()

        target_id = None
        target_lower = item_name.lower()
        items_config = zh_cn.get("items", {})
        for key, names in items_config.items():
            if target_lower in [x.lower() for x in names]:
                target_id = key
                break

        if not target_id or target_id not in stats.town_inventory:
            return zh_cn.get("global", {}).get("use_not_found", "").format(target=item_name)

        if target_id == "lost_notebook":
            return zh_cn.get("global", {}).get("lost_notebook_use_desc", "")

        return zh_cn.get("global", {}).get("use_cannot_use", "").format(target=item_name)

    def challenge_npc(self, user_id: str, npc_id: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        zh_cn = self._load_zh_cn()
        npc_name = zh_cn.get("interactive_entities", {}).get(npc_id, {}).get("name", npc_id)

        selected_class = getattr(stats, "selected_class", "法师")
        selected_subclass = getattr(stats, "selected_subclass", "")
        if selected_class == "战士":
            selected_subclass = ""
            allowed_colors = ("warrior", "neutral")
            hp = 80
            max_hp = 80
        else:
            allowed_colors = ("wizard", "neutral")
            hp = 45
            max_hp = 45
        hp_bonus = getattr(stats, "town_health_bonus", 0)
        hp += hp_bonus
        max_hp += hp_bonus
        commons = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "common" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and is_card_available(cid, stats)]
        rares = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "rare" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and is_card_available(cid, stats)]
        epics = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "epic" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and is_card_available(cid, stats)]
        locked_cards = list(getattr(stats, "locked_cards", []) or [])
        g_card = getattr(stats, "guaranteed_card", None)
        if g_card:
            if g_card not in locked_cards:
                locked_cards.append(g_card)
            stats.guaranteed_card = None
        p_pool = getattr(stats, "purchased_pool", [])
        if p_pool:
            locked_cards.extend(p_pool)
            stats.purchased_pool = []
        stats.locked_cards = locked_cards
        self.save_manager.save_stats(user_id, stats)
        target_counts = {"common": 5, "rare": 2, "epic": 1}
        for cid in locked_cards:
            c_obj = ALL_CARDS.get(cid)
            r = getattr(c_obj, "rarity", "common") if c_obj else "common"
            if r not in target_counts:
                r = "common"
            if target_counts[r] > 0:
                target_counts[r] -= 1
            else:
                if target_counts["common"] > 0:
                    target_counts["common"] -= 1
                elif target_counts["rare"] > 0:
                    target_counts["rare"] -= 1
                elif target_counts["epic"] > 0:
                    target_counts["epic"] -= 1
        deck = list(locked_cards)
        for _ in range(target_counts["common"]):
            deck.append(random.choice(commons))
        for _ in range(target_counts["rare"]):
            deck.append(random.choice(rares))
        for _ in range(target_counts["epic"]):
            deck.append(random.choice(epics))
        if selected_class == "法师" and selected_subclass == "时序法师":
            deck.append("time_stop")
            
        p_state = PlayerState(
            hp=hp,
            max_hp=max_hp,
            shield=0,
            gold=0,
            stage=1,
            name=getattr(stats, "player_name", "玩家"),
            deck=deck,
            draw_pile=list(deck),
            discard_pile=[],
            hand=[],
            actions=1,
            bonus_actions=1,
            minions={},
            amulets={},
            abilities=[],
            subclass="",
            selected_class=selected_class
        )

        if npc_id == "Dummy":
            enemy = EnemyState(name="训练假人", hp=200, max_hp=200, shield=0)
        elif npc_id == "NoobSlayer99":
            enemy = EnemyState(name="NoobSlayer99", hp=100, max_hp=100, shield=0)
        elif npc_id == "xXx_SniperElite_xXx":
            enemy = EnemyState(name="xXx_SniperElite_xXx", hp=120, max_hp=120, shield=0)
        elif npc_id == "pppopipupu":
            enemy = EnemyState(name="pppopipupu", hp=1, max_hp=1, shield=0)
        elif npc_id == "Gate_Guardian":
            enemy = EnemyState(name="Gate_Guardian", hp=300, max_hp=300, shield=0)
        else:
            return zh_cn.get("global", {}).get("cannot_challenge_unknown", "").format(name=npc_name)

        random.shuffle(p_state.draw_pile)
        for _ in range(min(5, len(p_state.draw_pile))):
            p_state.hand.append(p_state.draw_pile.pop(0))

        run = GameRun(
            user_id=user_id,
            node_type="battle",
            player=p_state,
            enemies=[enemy],
            node_data={"is_town_combat": True, "npc_name": npc_id}
        )
        self.engine.battle_engine.enemy_controller.roll_enemy_intent(run)
        self.save_manager.save_save(user_id, run)
        
        from ..renderer import GameRenderer
        render_res = GameRenderer.render_game(run)
        if npc_id == "Gate_Guardian":
            return zh_cn.get("global", {}).get("challenge_start_guardian", "").format(render_res=render_res)
        return zh_cn.get("global", {}).get("challenge_start_normal", "").format(name=npc_name, render_res=render_res)
