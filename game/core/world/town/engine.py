import os
import random
from typing import Optional, List, Dict, Any, Tuple
from ....models.state import UserStats, GameRun, PlayerState, EnemyState, BuffState
from ....json_codec import load
from ....entities import ALL_CARDS
from ....entities.cards.market import MARKET_SHELF_CARDS, is_card_available
from ....data.locale_data import get_locale_text
from ....data.starting_deck_config import CLASS_STARTING_CARDS, LOCK_SLOT_LIMIT, STARTING_ROLL_COUNTS
from ...inventory.bag_service import get_item_display_name

from ....data.yog_quest_config import YOG_SIGIL_ITEM
from ....data.world_social_config import WORLD_TOWN
from ....data.town_map_config import TOWN_ROOM_COORDS
from ..presence import sync_active

class TownEngine:
    def __init__(self, save_manager, engine):
        self.save_manager = save_manager
        self.engine = engine
        self.world_social: Any = None
        from ..outer_plane.engine import OuterPlaneEngine
        self.outer_plane_engine = OuterPlaneEngine(save_manager, engine, self)

    def _load_zh_cn(self) -> Dict[str, Any]:
        from ...i18n.locale_manager import LocaleManager
        return LocaleManager.get_all_translations()

    def _load_room_data(self, room_id: str) -> Dict[str, Any]:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), "data", "town", f"{room_id}.json")
        if not os.path.exists(data_path):
            return {"id": room_id, "name_key": room_id, "exits": {}, "npcs": [], "items": [], "interactive": {}}
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = load(f)
            if not isinstance(data, dict):
                raise ValueError("room data must be a mapping")
            if room_id == "alley":
                from ....models.state import get_user_id
                uid = get_user_id()
                if uid:
                    stats = self.save_manager.load_stats(uid)
                    if stats.town_flags.get("quest_hammer_state") == "started" and not stats.town_flags.get("taken_smith_hammer"):
                        if "smith_hammer" not in data.get("items", []):
                            data.setdefault("items", []).append("smith_hammer")
            return data
        except Exception:
            return {"id": room_id, "name_key": room_id, "exits": {}, "npcs": [], "items": [], "interactive": {}}

    def record_visited_room(self, stats: UserStats, room_id: Optional[str] = None) -> bool:
        target = room_id or getattr(stats, "town_pos", "") or "square"
        flags = stats.town_flags if isinstance(stats.town_flags, dict) else {}
        stats.town_flags = flags
        visited = flags.get("visited_rooms")
        changed = False
        if not isinstance(visited, list):
            visited = []
            changed = True
        tour_visited = flags.get("quest_town_tour_visited")
        if isinstance(tour_visited, list):
            for rid in tour_visited:
                if rid and rid not in visited:
                    visited.append(rid)
                    changed = True
        if target and target not in visited:
            visited.append(target)
            changed = True
        flags["visited_rooms"] = visited
        return changed

    def get_visited_rooms(self, stats: UserStats) -> List[str]:
        self.record_visited_room(stats)
        return list(stats.town_flags.get("visited_rooms", []))

    def render_current_room(self, user_id: str, stats: UserStats) -> str:
        from ....data.outer_plane_config import OUTER_PLANE_ACTIVE_FLAG
        if stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG):
            return self.outer_plane_engine.render(user_id, stats)
        sync_active(user_id, stats=stats)
        from ..yog_quest.service import ensure_sigil
        zh_cn = self._load_zh_cn()
        dirty = self.record_visited_room(stats)
        if ensure_sigil(stats):
            dirty = True
        if stats.town_pos == "market":
            self._get_market_shelf(stats)
            dirty = True
        if dirty:
            self.save_manager.save_stats(user_id, stats)

        active_dialog = stats.town_flags.get("current_dialog")
        if active_dialog:
            return self._render_dialog_window(stats, active_dialog, zh_cn)

        from ....renderer.town import render_town
        room_data = self._load_room_data(stats.town_pos)
        return render_town(stats, room_data)

    def _render_dialog_window(self, stats: UserStats, npc_id: str, zh_cn: Dict[str, Any]) -> str:
        from .dialog_handler import build_dialog_menu
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
        from ....data.town_map_config import TOWN_ROOM_COORDS
        from ..grid_map_generator import coord_to_xy, xy_to_coord
        stats = self.save_manager.load_stats(user_id)
        dir_map = {"up": "w", "down": "s", "left": "a", "right": "d"}
        dir_key = dir_map.get(direction.lower(), direction.lower())
        deltas = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
        if dir_key not in deltas:
            return get_locale_text("global.move_no_way", exits="W, S, A, D")
        coord = TOWN_ROOM_COORDS.get(stats.town_pos, "C2")
        x, y = coord_to_xy(coord)
        dx, dy = deltas[dir_key]
        target_coord = xy_to_coord(x + dx, y + dy)
        target_room = next((rid for rid, c in TOWN_ROOM_COORDS.items() if c == target_coord), None)
        if target_room is None:
            available = [
                dk.upper()
                for dk, (ddx, ddy) in deltas.items()
                if xy_to_coord(x + ddx, y + ddy) in TOWN_ROOM_COORDS.values()
            ]
            return get_locale_text("global.move_no_way", exits=", ".join(available))

        self.record_visited_room(stats, stats.town_pos)
        stats.town_pos = target_room
        self.record_visited_room(stats, target_room)

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
        sync_active(user_id, stats=stats)
        target_room_data = self._load_room_data(target_room)
        from ....renderer.town import render_town
        return render_town(stats, target_room_data)

    def teleport(self, user_id: str, target_query: str) -> str:
        from ....data.town_map_config import TOWN_ROOM_COORDS
        from ...cli.base import find_entry_by_query
        stats = self.save_manager.load_stats(user_id)
        dirty = self.record_visited_room(stats)
        visited = list(stats.town_flags.get("visited_rooms", []))
        zh_cn = self._load_zh_cn()
        rooms_loc = zh_cn.get("rooms", {})
        sep = get_locale_text("renderer_town.list_separator")
        visited_entries = [
            (rid, f"{rooms_loc.get(rid, {}).get('name', rid)}({TOWN_ROOM_COORDS.get(rid, '?')})")
            for rid in visited
            if rid in rooms_loc
        ]
        visited_names = sep.join(name for _, name in visited_entries)
        query = str(target_query or "").strip()
        if not query:
            if dirty:
                self.save_manager.save_stats(user_id, stats)
            return get_locale_text("i18n_cli_commands.town_tp_usage", visited=visited_names)
        coord = query.upper()
        is_coord = len(coord) >= 2 and coord[0].isalpha() and coord[1:].isdigit()
        target_room = None
        if is_coord:
            target_room = next((rid for rid, c in TOWN_ROOM_COORDS.items() if c == coord), None)
            if target_room is None:
                if dirty:
                    self.save_manager.save_stats(user_id, stats)
                return get_locale_text("i18n_cli_commands.town_tp_coord_not_found", query=query, visited=visited_names)
            if target_room not in visited:
                if dirty:
                    self.save_manager.save_stats(user_id, stats)
                name = rooms_loc.get(target_room, {}).get("name", target_room)
                return get_locale_text("i18n_cli_commands.town_tp_unvisited", name=name)
        else:
            target_room = find_entry_by_query(visited_entries, query)
            if not target_room:
                if dirty:
                    self.save_manager.save_stats(user_id, stats)
                unvisited_entries = [
                    (rid, info.get("name", rid))
                    for rid, info in rooms_loc.items()
                    if rid not in visited and isinstance(info, dict)
                ]
                unvisited_room = find_entry_by_query(unvisited_entries, query)
                if unvisited_room:
                    unvisited_name = rooms_loc.get(unvisited_room, {}).get("name", unvisited_room)
                    return get_locale_text("i18n_cli_commands.town_tp_unvisited", name=unvisited_name)
                return get_locale_text("i18n_cli_commands.town_tp_not_found", query=query, visited=visited_names)
        stats.town_pos = target_room
        self.record_visited_room(stats, target_room)
        quest_state = stats.town_flags.get("quest_town_tour_state", "unstarted")
        if quest_state == "started":
            tour_visited = stats.town_flags.setdefault("quest_town_tour_visited", [])
            if target_room not in tour_visited:
                tour_visited.append(target_room)
        self.save_manager.save_stats(user_id, stats)
        target_name = rooms_loc.get(target_room, {}).get("name", target_room)
        rendered = self.render_current_room(user_id, stats)
        return get_locale_text(
            "i18n_cli_commands.town_tp_success",
            name=target_name,
            coord=TOWN_ROOM_COORDS.get(target_room, "?"),
        ) + "\n\n" + rendered

    def _visible_entity_ids(self, stats: UserStats, room_data: Dict[str, Any]) -> List[str]:
        visible = list(room_data.get("npcs", []))
        for npc_id in ("Gamer_Boy", "Crypto_Whale", "Lost_Bard", "Town_Guard", "Naughty_Child"):
            if stats.town_flags.get(f"pos_{npc_id}", "square") == stats.town_pos and npc_id not in visible:
                visible.append(npc_id)
        return visible

    def _resolve_visible_entity(self, stats: UserStats, room_data: Dict[str, Any], target_name: str) -> Optional[str]:
        target_lower = (target_name or "").strip().lower()
        if not target_lower:
            return None
        zh_cn = self._load_zh_cn()
        entities = zh_cn.get("interactive_entities", {})
        from ....data.mercenary_data import MERCENARY_CONFIG
        for ent_id in self._visible_entity_ids(stats, room_data):
            ent_data = entities.get(ent_id, {})
            names = [ent_id.lower(), str(ent_data.get("name", "")).lower()]
            if ent_id == "Harry_Du_Bois":
                names.extend(a.lower() for a in MERCENARY_CONFIG["harry_du_bois"].get("aliases", []))
            if target_lower in names:
                return ent_id
        return None

    def _open_dialog(self, user_id: str, stats: UserStats, target_id: str) -> str:
        from ..yog_quest.service import ensure_sigil
        ensure_sigil(stats)
        stats.town_flags["current_dialog"] = target_id
        stats.town_flags.pop("market_sub_menu", None)
        self.save_manager.save_stats(user_id, stats)
        return self._render_dialog_window(stats, target_id, self._load_zh_cn())

    def talk_npc(self, user_id: str, target_name: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        room_data = self._load_room_data(stats.town_pos)
        if self.world_social is not None:
            coord = TOWN_ROOM_COORDS.get(stats.town_pos, "C2")
            target_entry, _ = self.world_social.resolve_target(WORLD_TOWN, coord, target_name, user_id)
            if target_entry is not None:
                return self.world_social.say_to_world(user_id, WORLD_TOWN, coord, target_name)
        target_id = self._resolve_visible_entity(stats, room_data, target_name)
        if not target_id:
            return get_locale_text("global.interact_not_found", target=target_name)
        return self._open_dialog(user_id, stats, target_id)

    def touch_target(self, user_id: str, target_name: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        room_data = self._load_room_data(stats.town_pos)
        target_id = self._resolve_visible_entity(stats, room_data, target_name)
        if target_id:
            return self._open_dialog(user_id, stats, target_id)
        from ...inventory.bag_service import get_item_desc, resolve_item_query
        items = [
            item_id
            for item_id in room_data.get("items", [])
            if not stats.town_flags.get(f"taken_{item_id}", 0)
        ]
        item_id = resolve_item_query(target_name, items)
        if item_id:
            return get_locale_text(
                "i18n_town.touch_item",
                name=get_item_display_name(item_id),
                desc=get_item_desc(item_id),
            )
        return get_locale_text("global.interact_not_found", target=target_name)

    def attack_target(self, user_id: str, target_name: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        room_data = self._load_room_data(stats.town_pos)
        target_id = self._resolve_visible_entity(stats, room_data, target_name)
        if not target_id:
            return get_locale_text("global.interact_not_found", target=target_name)
        if target_id in ("Dummy", "NoobSlayer99", "xXx_SniperElite_xXx", "pppopipupu"):
            stats.town_flags.pop("current_dialog", None)
            self.save_manager.save_stats(user_id, stats)
            return self.challenge_npc(user_id, target_id)
        zh_cn = self._load_zh_cn()
        name = zh_cn.get("interactive_entities", {}).get(target_id, {}).get("name", target_id)
        return get_locale_text("i18n_town.attack_not_challengeable", name=name)

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

        from .dialog_handler import process_dialog_choice
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
        
        return get_locale_text("global.take_success", target=get_item_display_name(target_id))

    def use_item(self, user_id: str, item_name: str) -> str:
        from ..yog_quest.service import ensure_sigil
        stats = self.save_manager.load_stats(user_id)
        if ensure_sigil(stats):
            self.save_manager.save_stats(user_id, stats)
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

        if target_id == YOG_SIGIL_ITEM:
            return self.engine.start_quest_run(user_id)

        if target_id == "lost_notebook":
            return get_locale_text("global.lost_notebook_use_desc")

        from ....data.outer_plane_config import NECRONOMICON_ITEM
        if target_id == NECRONOMICON_ITEM:
            return self.outer_plane_engine.enter_wip(user_id, stats)

        return get_locale_text("global.use_cannot_use", target=item_name)

    def build_combat_player(self, user_id: str, stats: UserStats, hp: int = None, max_hp: int = None) -> PlayerState:
        selected_class = getattr(stats, "selected_class", "法师")
        selected_subclass = getattr(stats, "selected_subclass", "")
        if selected_class == "战士":
            selected_subclass = ""
            allowed_colors = ("warrior", "neutral")
        else:
            allowed_colors = ("wizard", "neutral")
        if hp is None:
            hp = 80 if selected_class == "战士" else 45
            hp += getattr(stats, "town_health_bonus", 0)
        if max_hp is None:
            max_hp = hp
        if self.outer_plane_engine.apply_max_hp_zero(stats):
            hp = 0
            max_hp = 0
        commons = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "common" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and not getattr(c, "coop_only", False) and not getattr(c, "token", False) and not getattr(c, "event_only", False) and not getattr(c, "life_merchant_only", False) and is_card_available(cid, stats)]
        rares = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "rare" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and not getattr(c, "coop_only", False) and not getattr(c, "token", False) and not getattr(c, "event_only", False) and not getattr(c, "life_merchant_only", False) and is_card_available(cid, stats)]
        epics = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "epic" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and not getattr(c, "coop_only", False) and not getattr(c, "token", False) and not getattr(c, "event_only", False) and not getattr(c, "life_merchant_only", False) and is_card_available(cid, stats)]
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
        return PlayerState(
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

    def challenge_npc(self, user_id: str, npc_id: str) -> str:
        stats = self.save_manager.load_stats(user_id)
        zh_cn = self._load_zh_cn()
        npc_name = zh_cn.get("interactive_entities", {}).get(npc_id, {}).get("name", npc_id)

        p_state = self.build_combat_player(user_id, stats)

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
        
        from ....renderer import GameRenderer
        render_res = GameRenderer.render_game(run)
        if npc_id == "Gate_Guardian":
            return get_locale_text("global.challenge_start_guardian", render_res=render_res)
        return get_locale_text("global.challenge_start_normal", name=npc_name, render_res=render_res)
