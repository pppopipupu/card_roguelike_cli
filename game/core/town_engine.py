import os
import json
import random
from typing import Optional, List, Dict, Any, Tuple
from ..models.state import UserStats, GameRun, PlayerState, EnemyState, BuffState
from ..entities import ALL_CARDS
from ..entities.cards.market import MARKET_SHELF_CARDS, is_card_available
from ..data.locale_data import get_locale_text
from ..data.starting_deck_config import CLASS_STARTING_CARDS, LOCK_SLOT_LIMIT, STARTING_ROLL_COUNTS

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
        except Exception:
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
        from .town.dialog_handler import build_dialog_menu
        menu = build_dialog_menu(self, stats, npc_id, zh_cn)
        menu_lines = "\n".join(option["text"] for option in menu["options"])
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("global.dialog_title", name=menu["npc_name"]),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            menu["welcome"],
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            menu_lines,
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("global.dialog_help"),
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
            return get_locale_text("global.move_no_way", exits=', '.join(exits.keys()).upper())

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
        from ..data.mercenary_data import MERCENARY_CONFIG
        for ent_id in visible_ids:
            ent_data = entities.get(ent_id, {})
            names = [ent_id.lower(), ent_data.get("name", "").lower()]
            if ent_id == "Harry_Du_Bois":
                names.extend(a.lower() for a in MERCENARY_CONFIG["harry_du_bois"].get("aliases", []))
            if target_lower in names:
                target_id = ent_id
                break
        if not target_id:
            return get_locale_text("global.interact_not_found", target=target_name)

        stats.town_flags["current_dialog"] = target_id
        stats.town_flags.pop("market_sub_menu", None)
        self.save_manager.save_stats(user_id, stats)
        return self._render_dialog_window(stats, target_id, zh_cn)

    def handle_dialog_input(self, user_id: str, choice: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        npc_id = stats.town_flags.get("current_dialog")
        zh_cn = self._load_zh_cn()
        if not npc_id:
            return get_locale_text("global.not_in_dialog")

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
            return get_locale_text("global.dialog_exit", name=npc_data.get("name", npc_id)) + "\n\n" + self.render_current_room(user_id, stats)

        from .town.dialog_handler import process_dialog_choice
        return process_dialog_choice(self, stats, npc_id, choice_lower, choice, user_id, zh_cn)

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
            return get_locale_text("global.take_not_found", target=item_name)
            
        if stats.town_flags.get(f"taken_{target_id}", 0):
            return get_locale_text("global.take_already_taken", target=item_name)

        stats.town_inventory.append(target_id)
        stats.town_flags[f"taken_{target_id}"] = 1
        self.save_manager.save_stats(user_id, stats)
        
        display_name = items_config[target_id][0]
        return get_locale_text("global.take_success", target=display_name)

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
            return get_locale_text("global.use_not_found", target=item_name)

        if target_id == "lost_notebook":
            return get_locale_text("global.lost_notebook_use_desc")

        return get_locale_text("global.use_cannot_use", target=item_name)

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
        commons = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "common" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and not getattr(c, "coop_only", False) and is_card_available(cid, stats)]
        rares = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "rare" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and not getattr(c, "coop_only", False) and is_card_available(cid, stats)]
        epics = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "epic" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and not getattr(c, "coop_only", False) and is_card_available(cid, stats)]
        locked_cards = list(getattr(stats, "locked_cards", []) or [])[:LOCK_SLOT_LIMIT]
        g_card = getattr(stats, "guaranteed_card", None)
        if g_card:
            if g_card not in locked_cards:
                locked_cards.append(g_card)
            stats.guaranteed_card = None
        p_pool = getattr(stats, "purchased_pool", [])
        if p_pool:
            locked_cards.extend(p_pool)
            stats.purchased_pool = []
        stats.locked_cards = locked_cards[:LOCK_SLOT_LIMIT]
        self.save_manager.save_stats(user_id, stats)
        target_counts = dict(STARTING_ROLL_COUNTS)
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
        deck = list(CLASS_STARTING_CARDS.get(selected_class, CLASS_STARTING_CARDS["法师"])) + list(locked_cards)
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
            name=getattr(stats, "player_name", get_locale_text("i18n_town.player_default_name")),
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
            enemy = EnemyState(name=get_locale_text("i18n_town.dummy_enemy_name"), hp=200, max_hp=200, shield=0)
        elif npc_id == "NoobSlayer99":
            enemy = EnemyState(name="NoobSlayer99", hp=100, max_hp=100, shield=0)
        elif npc_id == "xXx_SniperElite_xXx":
            enemy = EnemyState(name="xXx_SniperElite_xXx", hp=120, max_hp=120, shield=0)
        elif npc_id == "pppopipupu":
            enemy = EnemyState(name="pppopipupu", hp=1, max_hp=1, shield=0)
        elif npc_id == "Gate_Guardian":
            enemy = EnemyState(name="Gate_Guardian", hp=300, max_hp=300, shield=0)
        else:
            return get_locale_text("global.cannot_challenge_unknown", name=npc_name)

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
            return get_locale_text("global.challenge_start_guardian", render_res=render_res)
        return get_locale_text("global.challenge_start_normal", name=npc_name, render_res=render_res)
