import random
from typing import Optional, List, Dict
from ..models.state import GameRun, PlayerState
from ..data.map_config import MapConfig
from ..entities import ALL_CARDS, get_relic_name
from ..entities.events import ALL_EVENTS, get_option_by_action
from ..entities.cards.market import is_coop_only
from ..data.locale_data import get_locale_text
from .coop_explore import CoopExploreMixin

class ExploreEngine(CoopExploreMixin):
    def __init__(self, save_manager, map_engine):
        self.save_manager = save_manager
        self.map_engine = map_engine

    def _init_rest_node(self, run: GameRun):
        if getattr(run, "coop_id", ""):
            views = {}
            ready = {}
            for uid in run.party_order:
                views[uid] = {
                    "node_type": "rest",
                    "data": {
                        "items": [
                            {"type": "rest_heal", "taken": False},
                            {"type": "rest_meditate", "taken": False},
                            {"type": "rest_upgrade", "taken": False},
                            {"type": "rest_mend", "taken": False},
                        ]
                    },
                }
                ready[uid] = run.players[uid].downed
            run.node_type = "rest"
            run.node_data = {
                "coop_node_type": "rest",
                "player_views": views,
                "stage_ready": ready,
            }
            self._coop(run).apply_view(run, run.user_id)
            return
        run.node_data = {
            "items": [
                {"type": "rest_heal", "taken": False},
                {"type": "rest_meditate", "taken": False},
                {"type": "rest_upgrade", "taken": False}
            ]
        }

    def _claim_single_item(self, run: GameRun, item_idx: int) -> str:
        p = run.player
        items = run.node_data.setdefault("items", [])
        if item_idx < 0 or item_idx >= len(items):
            return get_locale_text("err_invalid_option_idx")
        item = items[item_idx]
        if item.get("taken"):
            return "❌ 已拿取。"
        
        item["taken"] = True
        itype = item.get("type")
        res = ""
        
        if itype == "potion":
            pid = item.get("potion_id")
            if not hasattr(p, "potions"):
                p.potions = []
            if len(p.potions) >= 3:
                item["taken"] = False
                from ..data.potion_data import get_potion_name
                return f"❌ 药水槽已满！无法拿取【{get_potion_name(pid)}】。请先使用或丢弃现有药水。"
            p.potions.append(pid)
            from ..data.potion_data import get_potion_name
            res = f"获得药水【{get_potion_name(pid)}】并放入药水槽。"
        elif itype == "gold":
            amt = item.get("amount", 0)
            p.gold += amt
            res = f"获得金币 🪙 {amt}。"
        elif itype in ("relic", "quest_relic", "boss_relic"):
            rid = item.get("relic_id") or item.get("id")
            p.relics.append(rid)
            if rid == "red_bottle":
                p.max_hp += 5
                p.hp += 5
            res = f"获得遗物【{get_relic_name(rid)}】。"
        elif itype in ("quest_card", "boss_card"):
            cid = item.get("card_id") or item.get("id")
            from ..models.state import CardState
            c_state = CardState(id=cid)
            from ..models.events import CardObtainEvent
            obtain_evt = CardObtainEvent(run, c_state)
            self.map_engine.battle_engine.event_bus.dispatch(obtain_evt)
            p.deck.append(c_state)
            res = f"获得卡牌【{ALL_CARDS[cid].name if cid in ALL_CARDS else cid}】并加入卡组。"
        elif itype == "gem":
            gem_id = item.get("gem_id")
            self.start_gem_insert_flow(run, gem_id, run.node_type, run.node_data)
            from ..entities import get_gem_name
            res = f"开启宝石【{get_gem_name(gem_id)}】的强制镶嵌。"
        elif itype == "shared_relic":
            rid = item.get("relic_id")
            uid = run.uid_for(p)
            count = self._coop(run).gain_shared_relic(run, uid, rid)
            res = f"🎒 你登记争夺共享遗物【{get_relic_name(rid)}】（当前 {count} 人争夺，全队完成本节点后猜拳裁决）。"
        elif itype == "card_reward":
            reward_cards = item.get("cards", [])
            from ..models.events import CardSelectInitEvent
            init_evt = CardSelectInitEvent(run, reward_cards)
            self.map_engine.battle_engine.event_bus.dispatch(init_evt)
            previous_node_type = run.node_type
            previous_node_data = run.node_data
            run.node_type = "card_select"
            run.node_data = {
                "title": get_locale_text("render_card_select_title"),
                "desc": "请从以下卡牌中挑选一张加入卡组：",
                "cards": reward_cards,
                "can_skip": init_evt.can_skip,
                "force_upgraded": init_evt.upgraded,
                "next_node_type": "treasure" if previous_node_type == "treasure" else "reward",
                "next_node_data": previous_node_data
            }
            res = "开启卡牌三选一奖励。"
        
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

    def _init_event_node(self, run: GameRun):
        stage = run.player.stage
        valid_events = [e for e in ALL_EVENTS if getattr(e, "min_stage", 2) <= stage <= getattr(e, "max_stage", MapConfig.COMMON_EVENT_MAX_STAGE)]
        if not valid_events:
            valid_events = ALL_EVENTS
        event = random.choice(valid_events)
        run.node_data = {
            "event_id": event.id,
            "description": event.description,
            "options": [{"text": opt.text, "action": opt.action} for opt in event.options]
        }

    def _init_shop_node(self, run: GameRun):
        if getattr(run, "coop_id", ""):
            views = {}
            ready = {}
            shop_map = {}
            for uid in run.party_order:
                previous = run.player
                previous_user = run.user_id
                run.player = run.players[uid]
                run.user_id = uid
                items = self._build_shop_items(run)
                views[uid] = {"node_type": "shop", "data": {"items": items}}
                shop_map[uid] = items
                ready[uid] = run.players[uid].downed
                run.player = previous
                run.user_id = previous_user
            run.node_type = "shop"
            run.node_data = {
                "coop_node_type": "shop",
                "player_views": views,
                "player_shops": shop_map,
                "stage_ready": ready,
            }
            self._coop(run).apply_view(run, run.user_id)
            return
        run.node_data = {"items": self._build_shop_items(run)}

    def _build_shop_items(self, run: GameRun):
        allowed_colors = ("warrior", "neutral") if getattr(run.player, "selected_class", "法师") == "战士" else ("wizard", "neutral")
        unlocked_new = set()
        stats = None
        if hasattr(self.save_manager, "load_stats"):
            stats = self.save_manager.load_stats(run.user_id)
        from ..entities.cards.market import is_card_available
        card_pool = [
            cid for cid, c in ALL_CARDS.items()
            if c.rarity not in ("legendary", "mythic", "artifact")
            and getattr(c, "color", "") in allowed_colors
            and not cid.startswith("curse_")
            and not cid.startswith("duel_")
            and (getattr(run, "coop_id", "") or not is_coop_only(cid))
            and is_card_available(cid, stats)
        ]
        shop_cards = random.sample(card_pool, min(3, len(card_pool)))
        from ..models.state import check_and_replace_fireball
        shop_cards = [check_and_replace_fireball(run, cid) for cid in shop_cards]
        items = []
        discount = 1.0
        if "gold_compass" in run.player.relics:
            discount *= 0.6
        if "greedy_contract" in run.player.relics:
            discount *= 0.6
            
        for cid in shop_cards:
            card = ALL_CARDS[cid]
            price = 15
            if card.color == "wizard":
                price += 10
            if card.type in ("ability", "minion"):
                price += 5
            price = int(price * discount)
            items.append({
                "type": "card",
                "card_id": cid,
                "price": price,
                "sold": False
            })
            
        available_relics = [rid for rid in ["lucky_coin", "red_bottle", "leather_armor", "whetstone", "ready_pack", "arcane_rune"] if rid not in run.player.relics]
        if available_relics:
            rid = random.choice(available_relics)
            from ..data.relic_data import RELIC_CONFIG
            r_cfg = RELIC_CONFIG[rid]
            r_price = int(r_cfg["price"] * discount)
            items.append({
                "type": "relic",
                "relic_id": rid,
                "price": r_price,
                "sold": False
            })
            
        from ..data.gem_data import GEM_CONFIG
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
            "price": int(30 * discount),
            "sold": False
        })
        items.append({
            "type": "upgrade",
            "price": int(30 * discount),
            "sold": False
        })
        items.append({
            "type": "leave",
            "price": 0,
            "sold": False
        })
        return items

    def _init_treasure_node(self, run: GameRun):
        if getattr(run, "coop_id", ""):
            views = {}
            ready = {}
            text = "你面前放着一个巨大的【古老宝箱】。宝箱上缠绕着锁链，上面刻着契约符文：‘欲获秘宝，必献此身部分知识。’\n请选择你想要献祭（移除）的卡牌序号（使用 选择 <卡牌序号>，可输入 /rogue 牌组 查看）："
            for uid in run.party_order:
                views[uid] = {
                    "node_type": "treasure",
                    "data": {"state": "pending_remove", "text": text},
                }
                ready[uid] = run.players[uid].downed
            from .coop_engine import TREASURE_RELIC_POOL
            run.node_type = "treasure"
            run.node_data = {
                "coop_node_type": "treasure",
                "player_views": views,
                "stage_ready": ready,
                "coop_shared_relic": random.choice(TREASURE_RELIC_POOL),
            }
            self._coop(run).apply_view(run, run.user_id)
            return
        run.node_data = {
            "state": "pending_remove",
            "text": "你面前放着一个巨大的【古老宝箱】。宝箱上缠绕着锁链，上面刻着契约符文：‘欲获秘宝，必献此身部分知识。’\n请选择你想要献祭（移除）的卡牌序号（使用 选择 <卡牌序号>，可输入 /rogue 牌组 查看）："
        }

    def choose_option(self, run: GameRun, option_idx: int, target: Optional[str] = None) -> str:
        if getattr(run, "coop_id", "") and run.node_type == "reward":
            return self._choose_coop_reward(run, option_idx)
        if getattr(run, "coop_id", "") and run.node_type == "rest":
            return self._choose_coop_rest(run, option_idx, target)
        p = run.player
        if run.node_type == "start_ancient":
            options = run.node_data.get("options", [])
            if getattr(run, "coop_id", ""):
                if option_idx < 1 or option_idx > len(options):
                    return "❌ 无效的选择序号。"
                chosen = options[option_idx - 1]
                rid = chosen["relic"]
                p.relics.append(rid)
                if rid == "mark_of_fury":
                    p.max_hp = max(5, p.max_hp - 5)
                    p.hp = min(p.hp, p.max_hp)
                elif rid == "vampiric_touch":
                    p.max_hp = max(5, p.max_hp - 4)
                    p.hp = min(p.hp, p.max_hp)
                elif rid == "glacier_armor":
                    p.max_hp = max(5, p.max_hp - 6)
                    p.hp = min(p.hp, p.max_hp)
                bonus_str = f"获得了先古遗物：【{get_relic_name(rid)}】"
                if chosen["type"] == "contract":
                    cid = chosen["card"]
                    from ..models.state import ensure_card_state
                    p.deck.append(ensure_card_state(cid))
                    bonus_str += f" ➕ 先古卡牌：【{ALL_CARDS[cid].name}】"
                return self._coop_finish(run, f"🌌 契约达成！你{bonus_str}。")
            if option_idx < 1 or option_idx > len(options):
                return "❌ 无效的选择序号。"
            chosen = options[option_idx - 1]
            
            rid = chosen["relic"]
            p.relics.append(rid)
            if rid == "mark_of_fury":
                p.max_hp = max(5, p.max_hp - 5)
                p.hp = min(p.hp, p.max_hp)
            elif rid == "vampiric_touch":
                p.max_hp = max(5, p.max_hp - 4)
                p.hp = min(p.hp, p.max_hp)
            elif rid == "glacier_armor":
                p.max_hp = max(5, p.max_hp - 6)
                p.hp = min(p.hp, p.max_hp)
            
            bonus_str = f"获得了先古遗物：【{get_relic_name(rid)}】"
            if chosen["type"] == "contract":
                cid = chosen["card"]
                from ..models.state import ensure_card_state
                p.deck.append(ensure_card_state(cid))
                bonus_str += f" ➕ 先古卡牌：【{ALL_CARDS[cid].name}】"
                
            self.map_engine.enter_next_stage(run)
            self.save_manager.save_save(run.user_id, run)
            return f"🌌 契约达成！你{bonus_str}。冒险正式开始！"

        elif run.node_type == "ancient":
            options = run.node_data.get("options", [])
            if option_idx < 1 or option_idx > len(options):
                return "❌ 无效的选择序号。"
            chosen = options[option_idx - 1]
            
            rid = chosen["relic"]
            cid = chosen.get("card")
            p.relics.append(rid)
            if cid:
                from ..models.state import ensure_card_state
                p.deck.append(ensure_card_state(cid))
                bonus_str = f"传奇卡牌【{ALL_CARDS[cid].name}】与珍奇遗物【{get_relic_name(rid)}】"
            else:
                bonus_str = f"珍奇遗物【{get_relic_name(rid)}】"
            
            self.map_engine.enter_next_stage(run)
            self.save_manager.save_save(run.user_id, run)
            return f"🌟 先古赐福！你获得了{bonus_str}！"

        elif run.node_type == "treasure":
            items = run.node_data.setdefault("items", [])
            if not items:
                items.append({"type": "sacrifice", "taken": False})
                run.node_data["items"] = items
            state = run.node_data.get("state", "pending_remove")
            if state == "pending_remove":
                if option_idx > 1:
                    from ..models.state import ensure_card_state
                    counts = {}
                    for c_id in p.deck:
                        c_state = ensure_card_state(c_id)
                        counts[c_state] = counts.get(c_state, 0) + 1
                    def get_sort_key(item):
                        return (item[0].id, 1 if item[0].upgraded else 0, tuple(item[0].gems or []))
                    sorted_items = sorted(counts.items(), key=get_sort_key)
                    if option_idx > len(sorted_items):
                        return get_locale_text("err_invalid_option_idx")
                    cid = sorted_items[option_idx - 1][0]
                    removed_name = ALL_CARDS[cid].name
                    p.deck.remove(cid)
                    
                    gold_gain = random.randint(20, 40)
                    p.gold += gold_gain
                    
                    relics_pool = ["lucky_coin", "red_bottle", "leather_armor", "whetstone", "ready_pack", "arcane_rune", "ancient_eye", "gold_compass", "dragon_blood", "energy_core", "heavy_armor"]
                    available_relics = [r for r in relics_pool if r not in p.relics]
                    got_relic = random.choice(available_relics) if available_relics else ""
                    if got_relic:
                        p.relics.append(got_relic)
                        if got_relic == "red_bottle":
                            p.max_hp += 5
                            p.hp += 5
                    
                    allowed_colors = ("warrior", "neutral") if getattr(p, "selected_class", "法师") == "战士" else ("wizard", "neutral")
                    stats = self.save_manager.load_stats(run.user_id)
                    from ..entities.cards.market import is_card_available
                    card_pool = [
                        cid_ for cid_ in ALL_CARDS.keys()
                        if ALL_CARDS[cid_].rarity == "epic"
                        and getattr(ALL_CARDS[cid_], "color", "") in allowed_colors
                        and not cid_.startswith("curse_")
                        and not cid_.startswith("duel_")
                        and not is_coop_only(cid_)
                        and is_card_available(cid_, stats)
                    ]
                    reward_cards = random.sample(card_pool, 3) if len(card_pool) >= 3 else card_pool
                    from ..models.state import check_and_replace_fireball
                    reward_cards = [check_and_replace_fireball(run, cid_) for cid_ in reward_cards]
                    
                    from ..data.gem_data import GEM_CONFIG
                    gift_gem_id = random.choice(list(GEM_CONFIG.keys()))
                    
                    box_items = [
                        {"type": "gold", "amount": gold_gain, "taken": True},
                        {"type": "card_reward", "cards": reward_cards, "taken": False, "force": False},
                        {"type": "gem", "gem_id": gift_gem_id, "taken": False}
                    ]
                    if got_relic:
                        box_items.append({"type": "relic", "relic_id": got_relic, "taken": True})
                        
                    from ..models.events import RewardGenerateEvent
                    evt = RewardGenerateEvent(run, box_items)
                    self.map_engine.battle_engine.event_bus.dispatch(evt)
                    
                    from ..models.events import CardSelectInitEvent
                    card_select_evt = CardSelectInitEvent(run, reward_cards)
                    self.map_engine.battle_engine.event_bus.dispatch(card_select_evt)
                    
                    next_node_data = {
                        "title": get_locale_text("render_card_select_title"),
                        "cards": reward_cards,
                        "can_skip": card_select_evt.can_skip,
                        "force_upgraded": card_select_evt.upgraded,
                        "items": box_items
                    }
                    run.node_data["state"] = "opened"
                    run.node_data["items"] = box_items
                    self.start_gem_insert_flow(run, gift_gem_id, "card_select", next_node_data)
                    return get_locale_text("msg_sacrifice_success", removed_name=removed_name)
                
                available_items = [it for it in items if not it.get("taken")]
                if option_idx < 1 or option_idx > len(available_items):
                    return get_locale_text("err_invalid_option_idx")
                chosen = available_items[option_idx - 1]
                if chosen.get("type") == "sacrifice":
                    run.node_data["pending_remove"] = True
                    run.node_data["remove_source"] = "treasure"
                    self.save_manager.save_save(run.user_id, run)
                    return get_locale_text("msg_sacrifice_started")
            else:
                available_items = [it for it in items if not it.get("taken")]
                if option_idx < 1 or option_idx > len(available_items):
                    return get_locale_text("err_invalid_option_idx")
                chosen = available_items[option_idx - 1]
                real_idx = items.index(chosen)
                res = self._claim_single_item(run, real_idx)
                if run.node_type != "treasure":
                    self.save_manager.save_save(run.user_id, run)
                    return res
                available = [it for it in items if not it.get("taken")]
                if not available:
                    if getattr(run, "coop_id", ""):
                        return self._coop_finish(run, f"{res}\n{get_locale_text('msg_rewards_claimed_finished')}")
                    self.map_engine.enter_next_stage(run)
                    self.save_manager.save_save(run.user_id, run)
                    return f"{res}\n{get_locale_text('msg_rewards_claimed_finished')}"
                self.save_manager.save_save(run.user_id, run)
                return res

        elif run.node_type == "boss_chest":
            items = run.node_data.setdefault("items", [])
            available_items = [it for it in items if not it.get("taken")]
            if option_idx < 1 or option_idx > len(available_items):
                return get_locale_text("err_invalid_option_idx")
            chosen = available_items[option_idx - 1]
            real_idx = items.index(chosen)
            res = self._claim_single_item(run, real_idx)
            if run.node_type != "boss_chest":
                self.save_manager.save_save(run.user_id, run)
                return res
            available = [it for it in items if not it.get("taken")]
            if not available:
                if getattr(run, "coop_id", ""):
                    return self._coop_finish(run, f"{res}\n{get_locale_text('msg_boss_chest_finished')}")
                self.map_engine.enter_next_stage(run)
                self.save_manager.save_save(run.user_id, run)
                return f"{res}\n{get_locale_text('msg_boss_chest_finished')}"
            self.save_manager.save_save(run.user_id, run)
            return res

        elif run.node_type == "reward":
            if run.node_data.get("no_reward"):
                self.map_engine.enter_next_stage(run)
                self.save_manager.save_save(run.user_id, run)
                return get_locale_text("msg_escape_battle_win")
            items = run.node_data.setdefault("items", [])
            available_items = [it for it in items if not it.get("taken")]
            if option_idx < 1 or option_idx > len(available_items):
                return get_locale_text("err_invalid_option_idx")
            chosen = available_items[option_idx - 1]
            real_idx = items.index(chosen)
            res = self._claim_single_item(run, real_idx)
            if run.node_type != "reward":
                self.save_manager.save_save(run.user_id, run)
                return res
            available = [it for it in items if not it.get("taken")]
            if not available:
                self.map_engine.enter_next_stage(run)
                self.save_manager.save_save(run.user_id, run)
                return f"{res}\n{get_locale_text('msg_rewards_claimed_finished')}"
            self.save_manager.save_save(run.user_id, run)
            return res

        elif run.node_type == "corpse_reward":
            cards = run.node_data.get("cards", [])
            picks_left = int(run.node_data.get("picks_left", 0))
            skip_idx = len(cards) + 1
            if picks_left <= 0:
                stage = p.stage
                self.map_engine.return_to_map_select(run)
                self.save_manager.save_save(run.user_id, run)
                return f"搜刮已经完成，你回到了第 {stage} 层地图。"
            if option_idx < 1 or option_idx > skip_idx:
                return get_locale_text("err_invalid_option_idx")
            if option_idx == skip_idx:
                msg = "你跳过了这次选卡。"
            else:
                from ..models.state import ensure_card_state
                c_state = ensure_card_state(cards[option_idx - 1])
                from ..models.events import CardObtainEvent
                obtain_evt = CardObtainEvent(run, c_state)
                self.map_engine.battle_engine.event_bus.dispatch(obtain_evt)
                p.deck.append(c_state)
                cards.pop(option_idx - 1)
                card = ALL_CARDS.get(c_state)
                msg = f"你从尸体中取走了【{card.name if card else c_state.id}】。"
            picks_left -= 1
            run.node_data["picks_left"] = picks_left
            run.node_data["cards"] = cards
            if picks_left <= 0:
                corpse_id = run.node_data.get("corpse_id")
                if corpse_id:
                    self.save_manager.corpses.remove(corpse_id)
                stage = p.stage
                self.map_engine.return_to_map_select(run)
                self.save_manager.save_save(run.user_id, run)
                return f"{msg}\n搜刮完毕，你回到了第 {stage} 层地图。"
            self.save_manager.save_save(run.user_id, run)
            return f"{msg}\n你还可以从尸体中挑选 {picks_left} 张卡牌，或跳过。"

        elif run.node_type == "card_select":
            cards = run.node_data.get("cards", [])
            can_skip = run.node_data.get("can_skip", True)
            skip_idx = len(cards) + 1
            if not can_skip:
                if option_idx < 1 or option_idx > len(cards):
                    return get_locale_text("err_cannot_skip_card_select")
            else:
                if option_idx < 1 or option_idx > skip_idx:
                    return get_locale_text("err_invalid_option_idx")
            if option_idx == skip_idx:
                msg = get_locale_text("msg_card_select_skipped")
            else:
                cid = cards[option_idx - 1]
                from ..models.state import ensure_card_state
                c_state = ensure_card_state(cid)
                from ..models.events import CardObtainEvent
                obtain_evt = CardObtainEvent(run, c_state)
                self.map_engine.battle_engine.event_bus.dispatch(obtain_evt)
                p.deck.append(c_state)
                card = ALL_CARDS.get(cid)
                msg = get_locale_text("msg_card_added_to_deck", card_name=card.name if card else cid)
            next_type = run.node_data.get("next_node_type")
            next_data = run.node_data.get("next_node_data")
            if next_type:
                run.node_type = next_type
                run.node_data = next_data
                self.save_manager.save_save(run.user_id, run)
                available = [it for it in run.node_data.setdefault("items", []) if not it.get("taken")]
                if not available:
                    if getattr(run, "coop_id", ""):
                        return self._coop_finish(run, f"{msg}\n{get_locale_text('msg_rewards_claimed_finished')}")
                    self.map_engine.enter_next_stage(run)
                    self.save_manager.save_save(run.user_id, run)
                    return f"{msg}\n{get_locale_text('msg_rewards_claimed_finished')}"
                return msg
            else:
                if getattr(run, "coop_id", ""):
                    return self._coop_finish(run, msg)
                self.map_engine.enter_next_stage(run)
                self.save_manager.save_save(run.user_id, run)
                return f"{msg}开启下一关。"

        elif run.node_type == "rest":
            items = run.node_data.setdefault("items", [])
            if not items:
                self._init_rest_node(run)
                items = run.node_data["items"]
            
            # 支持旧用例的选项映射
            itype = None
            if option_idx == 1:
                itype = "rest_heal"
            elif option_idx == 2:
                itype = "rest_meditate"
            elif option_idx in (3, 4):
                itype = "rest_upgrade"
            else:
                return "❌ 无效的选择序号。"
            
            if itype != "rest_upgrade":
                for it in items:
                    it["taken"] = True
            if itype == "rest_heal":
                heal = p.max_hp // 2
                p.hp = min(p.max_hp, p.hp + heal)
                self.map_engine.enter_next_stage(run)
                self.save_manager.save_save(run.user_id, run)
                return f"你感到精力充沛，恢复了 {heal} 点生命值。\n整顿完毕，开启下一关。"
            elif itype == "rest_meditate":
                class_color = "warrior" if getattr(p, "selected_class", "法师") == "战士" else "wizard"
                stats = self.save_manager.load_stats(run.user_id)
                from ..entities.cards.market import is_card_available
                class_cards = [
                    cid for cid, c in ALL_CARDS.items()
                    if c.color == class_color
                    and c.type == "spell"
                    and c.rarity not in ("legendary", "mythic", "artifact")
                    and not cid.startswith("curse_")
                    and not cid.startswith("duel_")
                    and is_card_available(cid, stats)
                ]
                reward_cards = random.sample(class_cards, 3) if len(class_cards) >= 3 else class_cards
                from ..models.state import check_and_replace_fireball
                reward_cards = [check_and_replace_fireball(run, cid) for cid in reward_cards]
                run.node_type = "card_select"
                run.node_data = {
                    "title": "冥想感悟：请选择你想领悟的卡牌",
                    "desc": "你面对篝火静静冥想，脑海中浮现出了三道奥术灵光：",
                    "cards": reward_cards,
                    "next_node_type": "rest",
                    "next_node_data": run.node_data
                }
                self.save_manager.save_save(run.user_id, run)
                return "你开始冥想，寻找领悟。"
            elif itype == "rest_upgrade":
                run.node_data["upgrade_source"] = "rest"
                self.save_manager.save_save(run.user_id, run)
                return "UPGRADE_FLOW"

        elif run.node_type == "event":
            options = run.node_data.get("options", [])
            if option_idx < 1 or option_idx > len(options):
                return "❌ 无效的选择序号。"
            opt = options[option_idx - 1]
            act = opt.get("action")
            
            option_executor = get_option_by_action(act)
            if option_executor:
                return option_executor.execute(run, self.map_engine)
            else:
                self.map_engine.enter_next_stage(run)
                self.save_manager.save_save(run.user_id, run)
                return "你决定不节外生枝，继续赶路。已前往下一关。"

        elif run.node_type == "shop":
            items = run.node_data.get("items", [])
            if option_idx < 1 or option_idx > len(items):
                return "❌ 无效的商品序号。"
            item = items[option_idx - 1]
            if item.get("sold"):
                return "❌ 该商品已经售罄。"
            price = item.get("price")
            if p.gold < price:
                return f"❌ 你的金币不足，该商品售价为 {price} 金币（当前 {p.gold}）。"
            itype = item.get("type")
            if itype == "card":
                p.gold -= price
                cid = item.get("card_id")
                from ..models.state import ensure_card_state
                c_state = ensure_card_state(cid)
                from ..models.events import CardObtainEvent
                self.map_engine.battle_engine.event_bus.dispatch(CardObtainEvent(run, c_state))
                p.deck.append(c_state)
                item["sold"] = True
                self.save_manager.save_save(run.user_id, run)
                return f"购买成功！已将【{ALL_CARDS[cid].name}】加入你的卡组。"
            elif itype == "relic":
                p.gold -= price
                rid = item.get("relic_id")
                p.relics.append(rid)
                item["sold"] = True
                if rid == "red_bottle":
                    p.max_hp += 5
                    p.hp += 5
                self.save_manager.save_save(run.user_id, run)
                return f"购买成功！获得了遗物【{get_relic_name(rid)}】。"
            elif itype == "gem":
                p.gold -= price
                gem_id = item.get("gem_id")
                item["sold"] = True
                shop_node_data = {"items": items}
                res = self.start_gem_insert_flow(run, gem_id, "shop", shop_node_data)
                return f"购买成功！{res}"
            elif itype == "remove":
                return "REMOVE_FLOW"
            elif itype == "upgrade":
                run.node_data["upgrade_price"] = price
                run.node_data["upgrade_source"] = "shop"
                return "UPGRADE_FLOW"
            elif itype == "leave":
                if getattr(run, "coop_id", ""):
                    return self._coop_finish(run, "你离开了商店。")
                self.map_engine.enter_next_stage(run)
                self.save_manager.save_save(run.user_id, run)
                return "你离开了商店，继续冒险。已开启下一关。"
        return "未知的操作。"

    def remove_card_from_deck(self, run: GameRun, deck_idx: int) -> str:
        p = run.player
        from ..models.state import ensure_card_state
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
        removed_name = ALL_CARDS[c_state].name
        p.deck.remove(c_state)
        
        source = run.node_data.get("remove_source", "shop")
        if source == "treasure":
            gold_gain = random.randint(20, 40)
            relics_pool = ["lucky_coin", "red_bottle", "leather_armor", "whetstone", "ready_pack", "arcane_rune", "ancient_eye", "gold_compass", "dragon_blood", "energy_core", "heavy_armor"]
            available_relics = [r for r in relics_pool if r not in p.relics]
            got_relic = random.choice(available_relics) if available_relics else ""
            
            allowed_colors = ("warrior", "neutral") if getattr(p, "selected_class", "法师") == "战士" else ("wizard", "neutral")
            stats = self.save_manager.load_stats(run.user_id)
            from ..entities.cards.market import is_card_available
            card_pool = [
                cid for cid, c in ALL_CARDS.items()
                if c.rarity == "epic"
                and getattr(c, "color", "") in allowed_colors
                and not cid.startswith("curse_")
                and not cid.startswith("duel_")
                and not is_coop_only(cid)
                and is_card_available(cid, stats)
            ]
            reward_cards = random.sample(card_pool, 3) if len(card_pool) >= 3 else card_pool
            from ..models.state import check_and_replace_fireball
            reward_cards = [check_and_replace_fireball(run, cid) for cid in reward_cards]
            
            from ..data.gem_data import GEM_CONFIG
            gift_gem_id = random.choice(list(GEM_CONFIG.keys()))
            
            items = [
                {"type": "gold", "amount": gold_gain, "taken": False},
                {"type": "card_reward", "cards": reward_cards, "taken": False, "force": False},
                {"type": "gem", "gem_id": gift_gem_id, "taken": False}
            ]
            if got_relic:
                items.append({"type": "relic", "relic_id": got_relic, "taken": False})
            if getattr(run, "coop_id", ""):
                shared_rid = run.node_data.get("coop_shared_relic")
                if shared_rid:
                    items.append({"type": "shared_relic", "relic_id": shared_rid, "taken": False})
                
            from ..models.events import RewardGenerateEvent
            evt = RewardGenerateEvent(run, items)
            self.map_engine.battle_engine.event_bus.dispatch(evt)
            
            run.node_data = {
                "state": "opened",
                "items": items,
                "text": f"🔓 宝箱上的锁链崩解脱落！你成功献祭了【{removed_name}】。\n宝箱缓缓开启，里面露出了丰厚的秘宝奖励！请选择拿取："
            }
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_sacrifice_success", removed_name=removed_name)
        else:
            discount = 1.0
            if "gold_compass" in p.relics:
                discount *= 0.6
            if "greedy_contract" in p.relics:
                discount *= 0.6
            p.gold -= int(30 * discount)
            
            items = run.node_data.get("items", [])
            for item in items:
                if item.get("type") == "remove":
                    item["sold"] = True
            run.node_data["pending_remove"] = False
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_card_removed_success", removed_name=removed_name)

    def upgrade_card_in_deck(self, run: GameRun, deck_idx: int) -> str:
        p = run.player
        from ..models.state import ensure_card_state
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
        if c_state.upgraded:
            return get_locale_text("err_card_already_upgraded")
            
        from ..data.card_upgrade_data import CARD_UPGRADE_CONFIG
        if c_state.id not in CARD_UPGRADE_CONFIG:
            return get_locale_text("err_card_cannot_upgrade")
            
        import copy
        new_state = copy.copy(c_state)
        new_state.upgraded = True
        p.deck.remove(c_state)
        p.deck.append(new_state)
        
        source = run.node_data.get("upgrade_source", "rest")
        run.node_data["pending_upgrade"] = False
        
        old_card_name = ALL_CARDS[c_state].name
        new_card_name = ALL_CARDS[new_state].name
        
        if source == "rest":
            if "items" in run.node_data:
                for it in run.node_data["items"]:
                    it["taken"] = True
            if getattr(run, "coop_id", ""):
                msg = get_locale_text("msg_upgrade_success_rest", old_card_name=old_card_name, new_card_name=new_card_name)
                return self._coop_finish(run, msg)
            self.map_engine.enter_next_stage(run)
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_upgrade_success_rest", old_card_name=old_card_name, new_card_name=new_card_name)
        elif source == "event":
            self.map_engine.enter_next_stage(run)
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_upgrade_success_event", old_card_name=old_card_name, new_card_name=new_card_name)
        else:
            items = run.node_data.get("items", [])
            for item in items:
                if item.get("type") == "upgrade":
                    item["sold"] = True
            price = run.node_data.get("upgrade_price", 30)
            p.gold -= price
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_upgrade_success_shop", old_card_name=old_card_name, new_card_name=new_card_name)

    def start_gem_insert_flow(self, run: GameRun, gem_id: str, next_node_type: str, next_node_data: dict) -> str:
        from ..data.gem_data import GEM_CONFIG
        gem_name = GEM_CONFIG[gem_id]["name"]
        gem_desc = GEM_CONFIG[gem_id]["desc"]
        previous = run.node_data if getattr(run, "coop_id", "") else None
        run.node_type = "gem_insert"
        run.node_data = {
            "pending_gem": gem_id,
            "next_node_type": next_node_type,
            "next_node_data": next_node_data,
            "text": f"💎 你获得了宝石：【{gem_name}】（{gem_desc}）。\n当前无法将宝石放入行囊，必须立即进行强制镶嵌！\n请选择你要镶嵌的卡牌序号（输入 c <卡牌序号> 镶嵌，可输入 c 0 或是 c 取消 选择跳过镶嵌）："
        }
        self._begin_coop_gem(run, previous)
        self.save_manager.save_save(run.user_id, run)
        return f"你获得了宝石：【{gem_name}】。"

    def gem_insert_cancel(self, run: GameRun) -> str:
        gem_data = run.node_data
        next_type = gem_data["next_node_type"]
        next_data = gem_data["next_node_data"]
        self._end_coop_gem(run, gem_data, next_type, next_data)
        self.save_manager.save_save(run.user_id, run)
        return "你决定不进行镶嵌，丢弃了该宝石。继续前进。"

    def gem_insert_choose(self, run: GameRun, deck_idx: int) -> str:
        p = run.player
        from ..models.state import ensure_card_state
        counts = {}
        for c_id in p.deck:
            c_state = ensure_card_state(c_id)
            counts[c_state] = counts.get(c_state, 0) + 1
        def get_sort_key(item):
            return (item[0].id, 1 if item[0].upgraded else 0, tuple(item[0].gems or []))
        sorted_items = sorted(counts.items(), key=get_sort_key)
        if deck_idx < 1 or deck_idx > len(sorted_items):
            return "❌ 无效的卡牌序号。"
        cid = sorted_items[deck_idx - 1][0]
        from ..entities.cards.base import ALL_CARDS
        card_obj = ALL_CARDS.get(cid)
        if not card_obj:
            return "❌ 卡牌不存在。"
        from ..models.state import ensure_card_state
        cid = ensure_card_state(cid)
        old_gems = list(cid.gems)
        max_slots = card_obj.get_gem_slots_count()
        if len(old_gems) >= max_slots:
            return f"❌ 该卡牌的宝石插槽已满（当前槽位数：{max_slots}，已镶嵌：{len(old_gems)}），无法继续镶嵌。"
        gem_data = run.node_data
        gem_id = gem_data["pending_gem"]
        from ..data.gem_data import GEM_CONFIG
        gem_name = GEM_CONFIG[gem_id]["name"]
        p.deck.remove(cid)
        import copy
        new_card_state = copy.copy(cid)
        new_card_state.gems = old_gems + [gem_id]
        p.deck.append(new_card_state)
        next_type = gem_data["next_node_type"]
        next_data = gem_data["next_node_data"]
        self._end_coop_gem(run, gem_data, next_type, next_data)
        self.save_manager.save_save(run.user_id, run)
        return f"💎 镶嵌成功！已将【{gem_name}】成功镶嵌到了卡牌【{card_obj.name}】上。"
