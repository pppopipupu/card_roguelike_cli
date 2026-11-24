import random
from typing import Optional, List, Dict
from ...models.state import GameRun, PlayerState
from ...models.coop_view import strip_shared
from ...data.battle.battle_mode_config import BATTLE_MODE_FORCED_SOLO, BATTLE_MODE_SOLO, BATTLE_MODE_TEAM
from ...data.world.event_data import TEAM_EVENT_IDS
from ...data.world.grid_map_config import get_run_floor_index
from ...entities import ALL_CARDS, get_relic_name
from ...entities.events import ALL_EVENTS
from ...data.progression.balance_config import (
    GOLD_COMPASS_DISCOUNT,
    GREEDY_CONTRACT_DISCOUNT,
    SHOP_CARD_BASE_PRICE,
    SHOP_CARD_COLOR_SURCHARGE,
    SHOP_CARD_TYPE_SURCHARGE,
    SHOP_REMOVE_PRICE,
    SHOP_UPGRADE_PRICE,
    TREASURE_GOLD_MAX,
    TREASURE_GOLD_MIN,
)
from ...data.progression.reward_config import TREASURE_RELIC_POOL
from ...data.text.locale_data import get_locale_text
from ..inventory.card_distribution import CardDistributor
from ..inventory.relic_service import has_relic_flag
from .explore_nodes import resolve_node_handler
from ..party.coordinator import apply_and_scope, begin_party_gem, end_party_gem, finish_player_node, restore_player, swap_player

class ExploreEngine:
    def __init__(self, save_manager, map_engine):
        self.save_manager = save_manager
        self.map_engine = map_engine

    def _finish_node(self, run: GameRun, prefix: str) -> str:
        return finish_player_node(self.save_manager, self.map_engine, run, run.user_id, prefix)

    def try_finish_loot_node(self, run: GameRun, prefix: str = "") -> str | None:
        if run.node_type not in ("treasure", "reward", "boss_chest"):
            return None
        if len(run.human_uids()) > 1:
            return None
        data = run.node_data or {}
        if data.get("coop_done"):
            return None
        if run.node_type == "treasure" and data.get("state", "pending_remove") == "pending_remove":
            return None
        items = data.get("items") or []
        if not items or any(not it.get("taken") for it in items):
            return None
        pool = data.get("coop_relic_pool") or []
        if any(not entry.get("claimed_by") for entry in pool):
            return None
        key = "msg_boss_chest_finished" if run.node_type == "boss_chest" else "msg_rewards_claimed_finished"
        done_text = get_locale_text(key)
        text = f"{prefix}\n{done_text}".strip() if prefix else done_text
        return finish_player_node(self.save_manager, self.map_engine, run, run.user_id, text)

    def _init_rest_node(self, run: GameRun):
        multi = run.player_count() > 1
        base_items = [
            {"type": "rest_heal", "taken": False},
            {"type": "rest_meditate", "taken": False},
            {"type": "rest_upgrade", "taken": False},
        ]
        if multi:
            base_items.append({"type": "rest_mend", "taken": False})
        base_items.append({"type": "rest_enchant", "taken": False})
        views = {}
        ready = {}
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            views[uid] = {"node_type": "rest", "data": {"items": [dict(item) for item in base_items]}}
            ready[uid] = player.downed or getattr(player, "is_mercenary", False)
        run.node_type = "rest"
        run.node_data = {
            "coop_node_type": "rest",
            "player_views": views,
            "stage_ready": ready,
        }
        apply_and_scope(run, run.user_id)
    def start_card_select(self, run: GameRun, cards: list, next_node_type: str = "", next_node_data: dict | None = None, init_event: bool = True, title_key: str = "render_card_select_title", desc_key: str = "i18n_explore_core.card_reward_desc") -> None:
        can_skip = True
        upgraded = False
        if init_event:
            from ...models.events import CardSelectInitEvent
            init_evt = CardSelectInitEvent(run, cards)
            self.map_engine.battle_engine.event_bus.dispatch(init_evt)
            can_skip = init_evt.can_skip
            upgraded = init_evt.upgraded
        if next_node_data is None:
            next_node_data = run.node_data
        next_node_data = strip_shared(next_node_data)
        run.node_type = "card_select"
        run.node_data = {
            "title": get_locale_text(title_key),
            "desc": get_locale_text(desc_key) if desc_key else "",
            "cards": cards,
            "can_skip": can_skip,
            "force_upgraded": upgraded,
            "next_node_type": next_node_type,
            "next_node_data": next_node_data,
        }

    def _claim_single_item(self, run: GameRun, item_idx: int) -> str:
        p = run.player
        items = run.node_data.setdefault("items", [])
        if item_idx < 0 or item_idx >= len(items):
            return get_locale_text("err_invalid_option_idx")
        item = items[item_idx]
        if item.get("taken"):
            return get_locale_text("i18n_explore_core.item_already_taken")
        
        item["taken"] = True
        itype = item.get("type")
        res = ""
        
        if itype == "potion":
            pid = item.get("potion_id")
            from ..inventory.bag_service import add_bag_item
            ok, msg = add_bag_item(p, f"potion:{pid}")
            if not ok:
                item["taken"] = False
                return msg
            res = msg
        elif itype == "gold":
            amt = item.get("amount", 0)
            p.gold += amt
            res = get_locale_text("i18n_explore_core.gold_gained", amount=amt)
        elif itype in ("relic", "quest_relic", "boss_relic"):
            rid = item.get("relic_id") or item.get("id")
            from ..inventory.relic_service import grant_relic
            grant_relic(p, rid)
            if rid == "red_bottle":
                p.max_hp += 5
                p.hp += 5
            res = get_locale_text("i18n_explore_core.relic_gained", relic_name=get_relic_name(rid))
        elif itype in ("quest_card", "boss_card"):
            cid = item.get("card_id") or item.get("id")
            from ...models.state import CardState
            c_state = CardState(id=cid)
            from ...models.events import CardObtainEvent
            obtain_evt = CardObtainEvent(run, c_state)
            self.map_engine.battle_engine.event_bus.dispatch(obtain_evt)
            p.deck.append(c_state)
            res = get_locale_text("i18n_explore_core.card_gained", card_name=ALL_CARDS[cid].name if cid in ALL_CARDS else cid)
        elif itype == "gem":
            gem_id = item.get("gem_id")
            next_node_data = strip_shared(run.node_data)
            self.start_gem_insert_flow(run, gem_id, run.node_type, next_node_data)
            from ...entities import get_gem_name
            res = get_locale_text("i18n_explore_core.gem_forced_insert_started", gem_name=get_gem_name(gem_id))
        elif itype == "card_reward":
            reward_cards = item.get("cards", [])
            previous_node_type = run.node_type
            next_type = "treasure" if previous_node_type == "treasure" else "reward"
            self.start_card_select(run, reward_cards, next_type)
            res = get_locale_text("i18n_explore_core.card_reward_started")
        
        bg = item.get("bind_group")
        if bg:
            bind_res_list = []
            for i, other in enumerate(items):
                if not other.get("taken") and other.get("bind_group") == bg:
                    other_res = self._claim_single_item(run, i)
                    if other_res:
                        bind_res_list.append(other_res)
            if bind_res_list:
                res += "\n" + "\n".join(bind_res_list)
                
        gi = item.get("group_id")
        if gi:
            for other in items:
                if not other.get("taken") and other.get("group_id") == gi:
                    other["taken"] = True
                    
        return res

    def resolve_event(self, run: GameRun, event_id: str = ""):
        floor_val = float(get_run_floor_index(run))
        if event_id:
            event = next((e for e in ALL_EVENTS if e.id == event_id), None)
            if event is not None:
                return event
        valid_events = [e for e in ALL_EVENTS if float(getattr(e, "min_floor", 1)) <= floor_val <= float(getattr(e, "max_floor", 2))]
        if not valid_events:
            valid_events = ALL_EVENTS
        return random.choice(valid_events)

    def _init_event_node(self, run: GameRun, event_id: str = "", event=None):
        if event is None:
            event = self.resolve_event(run, event_id)
        mode = BATTLE_MODE_TEAM if event.id in TEAM_EVENT_IDS else BATTLE_MODE_SOLO
        order = list(run.party_order) or list(run.players.keys())
        humans = [uid for uid in order if uid in run.players and not getattr(run.players[uid], "is_mercenary", False)]
        if mode == BATTLE_MODE_TEAM and len(humans) <= 1:
            mode = BATTLE_MODE_SOLO
        battle_mode = BATTLE_MODE_TEAM if mode == BATTLE_MODE_TEAM else BATTLE_MODE_FORCED_SOLO
        data = {
            "coop_node_type": "event",
            "battle_mode": battle_mode,
            "event_mode": mode,
            "player_views": {},
            "stage_ready": {uid: (run.players[uid].downed or getattr(run.players[uid], "is_mercenary", False)) for uid in order if uid in run.players},
            "votes": {},
            "event_id": event.id,
            "description": event.description,
            "options": [{"text": opt.text, "action": opt.action} for opt in event.options],
        }
        run.node_type = "event"
        if run.node_data is None:
            run.node_data = data
        else:
            run.node_data.clear()
            run.node_data.update(data)

    def _init_shop_node(self, run: GameRun, enter_lobby: bool = False):
        from .rooms.shop_dialog import init_shop_view_flags
        views = {}
        ready = {}
        shop_map = {}
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            if getattr(player, "is_mercenary", False):
                views[uid] = {"node_type": "shop", "data": {"items": [], "coop_done": True}}
                shop_map[uid] = []
                ready[uid] = True
                continue
            previous, previous_user = swap_player(run, player)
            items = self._build_shop_items(run)
            vdata = {"items": items}
            init_shop_view_flags(run, vdata, enter_lobby)
            views[uid] = {"node_type": "shop", "data": vdata}
            shop_map[uid] = items
            ready[uid] = player.downed
            restore_player(run, previous, previous_user)
        run.node_data = {
            "coop_node_type": "shop",
            "player_views": views,
            "player_shops": shop_map,
            "stage_ready": ready,
        }
        apply_and_scope(run, run.user_id)
    def _init_life_merchant_node(self, run: GameRun):
        from .life_merchant import init_life_merchant_node
        init_life_merchant_node(self, run)

    def _build_shop_items(self, run: GameRun):
        unlocked_new = set()
        stats = None
        if hasattr(self.save_manager, "load_stats"):
            stats = self.save_manager.load_stats(run.user_id)
        shop_cards = CardDistributor.roll(
            "shop",
            run,
            run.player,
            stats,
            count=3,
            include_coop=run.player_count() > 1,
        )
        items = []
        discount = 1.0
        if "gold_compass" in run.player.relics:
            discount *= GOLD_COMPASS_DISCOUNT
        if "greedy_contract" in run.player.relics:
            discount *= GREEDY_CONTRACT_DISCOUNT
            
        for cid in shop_cards:
            card = ALL_CARDS[cid]
            price = SHOP_CARD_BASE_PRICE
            from ...entities.cards.base import card_matches_color
            if card_matches_color(card, "wizard"):
                price += SHOP_CARD_COLOR_SURCHARGE
            if card.type in ("ability", "minion"):
                price += SHOP_CARD_TYPE_SURCHARGE
            price = int(price * discount)
            items.append({
                "type": "card",
                "card_id": cid,
                "price": price,
                "sold": False
            })
            
        available_relics = [rid for rid in ["lucky_coin", "red_bottle", "leather_armor", "whetstone", "ready_pack", "arcane_rune", "pen_nib", "prayer_wheel"] if rid not in run.player.relics]
        from ...data.entities.relic_data import BACKPACK_RELIC_IDS, RELIC_CONFIG
        if available_relics:
            rid = random.choice(available_relics)
            r_cfg = RELIC_CONFIG[rid]
            r_price = int(r_cfg["price"] * discount)
            items.append({
                "type": "relic",
                "relic_id": rid,
                "price": r_price,
                "sold": False
            })
        for backpack_rid in BACKPACK_RELIC_IDS:
            if backpack_rid not in run.player.relics:
                bp_cfg = RELIC_CONFIG[backpack_rid]
                items.append({
                    "type": "relic",
                    "relic_id": backpack_rid,
                    "price": int(bp_cfg["price"] * discount),
                    "sold": False
                })
            
        from ...data.entities.gem_data import GEM_CONFIG
        gem_pool = list(GEM_CONFIG.keys())
        shop_gems = random.sample(gem_pool, min(2, len(gem_pool)))
        for gid in shop_gems:
            g_cfg = GEM_CONFIG[gid]
            g_price = int(g_cfg["price"] * discount)
            items.append({
                "type": "gem",
                "gem_id": gid,
                "price": g_price,
                "sold": False
            })

        items.append({
            "type": "remove",
            "price": int(SHOP_REMOVE_PRICE * discount),
            "sold": False
        })
        items.append({
            "type": "upgrade",
            "price": int(SHOP_UPGRADE_PRICE * discount),
            "sold": False
        })
        from ...data.entities.enchantment_data import SHOP_ENCHANT_PRICE
        items.append({
            "type": "enchant",
            "price": int(SHOP_ENCHANT_PRICE * discount),
            "sold": False
        })
        items.append({
            "type": "leave",
            "price": 0,
            "sold": False
        })
        return items

    def _build_treasure_relic_pool(self, run):
        alive = [
            uid
            for uid in run.party_order
            if not run.players[uid].downed and run.players[uid].hp > 0
        ]
        if not alive:
            return []
        owned = set()
        for uid in run.party_order:
            owned.update(run.players[uid].relics)
        pool = [rid for rid in TREASURE_RELIC_POOL if rid not in owned]
        random.shuffle(pool)
        return [{"relic_id": rid, "claimed_by": ""} for rid in pool[: len(alive)]]

    def _init_treasure_node(self, run: GameRun):
        views = {}
        ready = {}
        text = get_locale_text("i18n_explore_core.treasure_pending_remove_text")
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            views[uid] = {
                "node_type": "treasure",
                "data": {"state": "pending_remove", "text": text},
            }
            ready[uid] = player.downed or getattr(player, "is_mercenary", False)
        run.node_type = "treasure"
        run.node_data = {
            "coop_node_type": "treasure",
            "player_views": views,
            "stage_ready": ready,
            "coop_relic_pool": self._build_treasure_relic_pool(run) if run.player_count() > 1 else [],
        }
        apply_and_scope(run, run.user_id)

    def choose_option(self, run: GameRun, option_idx: int, target: Optional[str] = None) -> str | None:
        handler = resolve_node_handler(run.node_type)
        if handler is None:
            return get_locale_text("i18n_explore_core.err_unknown_action")
        return handler(self, run, option_idx, target)

    def remove_card_from_deck(self, run: GameRun, deck_idx: int) -> str:
        p = run.player
        from ...models.state import ensure_card_state
        counts = {}
        for c in p.deck:
            c_state = ensure_card_state(c)
            counts[c_state] = counts.get(c_state, 0) + 1
        def get_sort_key(item):
            return (item[0].id, 1 if item[0].upgraded else 0, tuple(item[0].gems or []))
        sorted_items = sorted(counts.items(), key=get_sort_key)
        if deck_idx < 1 or deck_idx > len(sorted_items):
            return get_locale_text("err_invalid_option_idx")
        c_state = sorted_items[deck_idx - 1][0]
        card_obj = ALL_CARDS.get(c_state)
        removed_name = card_obj.name if card_obj else get_locale_text("i18n_battle_core.unknown_card")
        from ...entities.cards.base import is_card_eternal
        if is_card_eternal(c_state):
            return get_locale_text("i18n_prism.eternal.cannot_remove", name=removed_name)
        p.deck.remove(c_state)
        
        source = run.node_data.get("remove_source", "shop")
        if source == "treasure":
            gold_gain = random.randint(TREASURE_GOLD_MIN, TREASURE_GOLD_MAX)
            got_relic = ""
            if run.player_count() <= 1:
                available_relics = [r for r in TREASURE_RELIC_POOL if r not in p.relics]
                got_relic = random.choice(available_relics) if available_relics else ""
            
            stats = self.save_manager.load_stats(run.user_id)
            reward_cards = CardDistributor.roll("treasure", run, p, stats, count=3)
            
            from ...data.entities.gem_data import GEM_CONFIG
            gift_gem_id = random.choice(list(GEM_CONFIG.keys()))
            
            items = [
                {"type": "gold", "amount": gold_gain, "taken": False},
                {"type": "card_reward", "cards": reward_cards, "taken": False, "force": False},
                {"type": "gem", "gem_id": gift_gem_id, "taken": False}
            ]
            if got_relic:
                items.append({"type": "relic", "relic_id": got_relic, "taken": False})
                
            from ...models.events import RewardGenerateEvent
            evt = RewardGenerateEvent(run, items)
            self.map_engine.battle_engine.event_bus.dispatch(evt)
            
            run.node_data.update({
                "state": "opened",
                "items": items,
                "pending_remove": False,
                "text": get_locale_text("i18n_explore_core.treasure_opened_text", removed_name=removed_name)
            })
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_sacrifice_success", removed_name=removed_name)
        else:
            discount = 1.0
            if "gold_compass" in p.relics:
                discount *= GOLD_COMPASS_DISCOUNT
            if "greedy_contract" in p.relics:
                discount *= GREEDY_CONTRACT_DISCOUNT
            p.gold -= int(SHOP_REMOVE_PRICE * discount)
            
            items = run.node_data.get("items", [])
            for item in items:
                if item.get("type") == "remove":
                    item["sold"] = True
            run.node_data["pending_remove"] = False
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_card_removed_success", removed_name=removed_name)

    def upgrade_card_in_deck(self, run: GameRun, deck_idx: int) -> str:
        p = run.player
        from ...models.state import ensure_card_state
        counts = {}
        for c in p.deck:
            c_state = ensure_card_state(c)
            counts[c_state] = counts.get(c_state, 0) + 1
        def get_sort_key(item):
            return (item[0].id, 1 if item[0].upgraded else 0, tuple(item[0].gems or []))
        sorted_items = sorted(counts.items(), key=get_sort_key)
        
        if deck_idx < 1 or deck_idx > len(sorted_items):
            return get_locale_text("err_invalid_card_idx")
        
        c_state = sorted_items[deck_idx - 1][0]
        from ..inventory.enchantment_service import has_cant_upgrade_enchantment, has_multi_upgrade_enchantment
        multi_up = has_multi_upgrade_enchantment(c_state)
        if c_state.upgraded and not multi_up:
            return get_locale_text("err_card_already_upgraded")
            
        if has_cant_upgrade_enchantment(c_state):
            return get_locale_text("i18n_enchantment.ui.cant_upgrade_err", name=ALL_CARDS[c_state].name)
        from ...data.cards.card_upgrade_data import CARD_UPGRADE_CONFIG
        if c_state.id not in CARD_UPGRADE_CONFIG:
            return get_locale_text("err_card_cannot_upgrade")
            
        import copy
        new_state = copy.copy(c_state)
        if c_state.upgraded and multi_up:
            new_state.enchantments = list(c_state.enchantments or []) + ["searing"]
        else:
            new_state.upgraded = True
        p.deck.remove(c_state)
        p.deck.append(new_state)
        
        source = run.node_data.get("upgrade_source", "rest")
        run.node_data["pending_upgrade"] = False
        
        old_card_name = ALL_CARDS[c_state].name
        new_card_name = ALL_CARDS[new_state].name
        
        if source == "rest":
            msg = get_locale_text("msg_upgrade_success_rest", old_card_name=old_card_name, new_card_name=new_card_name)
            if has_relic_flag(p, "rest_all_options"):
                for it in run.node_data.get("items", []):
                    if it.get("type") == "rest_upgrade":
                        it["taken"] = True
                self.save_manager.save_save(run.user_id, run)
                from ...renderer.explore import render_rest
                return f"{msg}\n\n{render_rest(run)}"
            if "items" in run.node_data:
                for it in run.node_data["items"]:
                    it["taken"] = True
            return self._finish_node(run, msg)
        elif source == "event":
            msg = get_locale_text("msg_upgrade_success_event", old_card_name=old_card_name, new_card_name=new_card_name)
            return self._finish_node(run, msg)
        elif source == "room_dialog":
            from .rooms.npc_dialog import resume_room_dialog_after_flow
            msg = get_locale_text("msg_upgrade_success_event", old_card_name=old_card_name, new_card_name=new_card_name)
            return resume_room_dialog_after_flow(self.save_manager, run, msg, committed=True)
        elif source == "cafe":
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_upgrade_success_shop", old_card_name=old_card_name, new_card_name=new_card_name)
        else:
            items = run.node_data.get("items", [])
            for item in items:
                if item.get("type") == "upgrade":
                    item["sold"] = True
            price = run.node_data.get("upgrade_price", SHOP_UPGRADE_PRICE)
            p.gold -= price
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_upgrade_success_shop", old_card_name=old_card_name, new_card_name=new_card_name)

    def start_gem_insert_flow(self, run: GameRun, gem_id: str, next_node_type: str, next_node_data: dict) -> str:
        from ...data.entities.gem_data import GEM_CONFIG
        gem_name = GEM_CONFIG[gem_id]["name"]
        gem_desc = GEM_CONFIG[gem_id]["desc"]
        previous = run.node_data
        next_node_data = strip_shared(next_node_data)
        run.node_type = "gem_insert"
        run.node_data = {
            "pending_gem": gem_id,
            "next_node_type": next_node_type,
            "next_node_data": next_node_data,
            "text": get_locale_text("i18n_explore_core.gem_insert_prompt", gem_name=gem_name, gem_desc=gem_desc)
        }
        begin_party_gem(run, previous)
        self.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.gem_gained", gem_name=gem_name)

    def start_enchant_flow(self, run: GameRun, source: str, next_node_type: str, next_node_data: dict, price: int = 0, offers: list[str] | None = None) -> str:
        from .enchant_flow import start_enchant_flow
        return start_enchant_flow(self, run, source, next_node_type, next_node_data, price=price, offers=offers)

    def enchant_choose(self, run: GameRun, option_idx: int) -> str:
        from .enchant_flow import enchant_choose
        return enchant_choose(self, run, option_idx)

    def enchant_cancel(self, run: GameRun) -> str:
        from .enchant_flow import enchant_cancel
        return enchant_cancel(self, run)

    def gem_insert_cancel(self, run: GameRun) -> str:
        gem_data = run.node_data
        next_type = gem_data["next_node_type"]
        next_data = gem_data["next_node_data"]
        end_party_gem(run, gem_data, next_type, next_data)
        if next_type == "room_dialog":
            from .rooms.npc_dialog import resume_room_dialog_after_flow
            return resume_room_dialog_after_flow(self.save_manager, run, get_locale_text("i18n_explore_core.gem_insert_cancelled"), committed=False)
        finished = self.try_finish_loot_node(run, get_locale_text("i18n_explore_core.gem_insert_cancelled"))
        if finished is not None:
            return finished
        self.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.gem_insert_cancelled")

    def gem_insert_choose(self, run: GameRun, deck_idx: int) -> str:
        p = run.player
        from ...models.state import ensure_card_state
        counts = {}
        for c_id in p.deck:
            c_state = ensure_card_state(c_id)
            counts[c_state] = counts.get(c_state, 0) + 1
        def get_sort_key(item):
            return (item[0].id, 1 if item[0].upgraded else 0, tuple(item[0].gems or []))
        sorted_items = sorted(counts.items(), key=get_sort_key)
        if deck_idx < 1 or deck_idx > len(sorted_items):
            return get_locale_text("err_invalid_card_idx")
        cid = sorted_items[deck_idx - 1][0]
        from ...entities.cards.base import ALL_CARDS
        card_obj = ALL_CARDS.get(cid)
        if not card_obj:
            return get_locale_text("i18n_explore_core.err_card_not_found")
        from ...models.state import ensure_card_state
        cid = ensure_card_state(cid)
        old_gems = list(cid.gems)
        max_slots = card_obj.get_gem_slots_count()
        if len(old_gems) >= max_slots:
            return get_locale_text("i18n_explore_core.err_gem_slots_full", max_slots=max_slots, equipped=len(old_gems))
        gem_data = run.node_data
        gem_id = gem_data["pending_gem"]
        from ...data.entities.gem_data import GEM_CONFIG
        gem_name = GEM_CONFIG[gem_id]["name"]
        p.deck.remove(cid)
        import copy
        new_card_state = copy.copy(cid)
        new_card_state.gems = old_gems + [gem_id]
        p.deck.append(new_card_state)
        next_type = gem_data["next_node_type"]
        next_data = gem_data["next_node_data"]
        end_party_gem(run, gem_data, next_type, next_data)
        msg = get_locale_text("i18n_explore_core.gem_insert_success", gem_name=gem_name, card_name=card_obj.name)
        if next_type == "room_dialog":
            from .rooms.npc_dialog import resume_room_dialog_after_flow
            return resume_room_dialog_after_flow(self.save_manager, run, msg, committed=True)
        finished = self.try_finish_loot_node(run, msg)
        if finished is not None:
            return finished
        self.save_manager.save_save(run.user_id, run)
        return msg
