import random

from ..entities import ALL_CARDS, get_relic_name
from ..entities.events import get_option_by_action
from ..data.balance_config import REST_HEAL_RATIO, TREASURE_GOLD_MAX, TREASURE_GOLD_MIN
from ..data.reward_config import TREASURE_RELIC_POOL
from ..data.locale_data import get_locale_text
from .deck_service import DeckService


class _CoopEventProxy:
    def __init__(self, map_engine):
        self._map_engine = map_engine
        self.finished = False

    def __getattr__(self, name):
        return getattr(self._map_engine, name)

    def enter_next_stage(self, run):
        self.finished = True


def handle_start_ancient(engine, run, option_idx, target=None) -> str | None:
    p = run.player
    options = run.node_data.get("options", [])
    if getattr(run, "coop_id", ""):
        if option_idx < 1 or option_idx > len(options):
            return get_locale_text("err_invalid_option_idx")
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
        bonus_str = get_locale_text("i18n_explore_core.ancient_relic_bonus", relic_name=get_relic_name(rid))
        if chosen["type"] == "contract":
            cid = chosen["card"]
            from ..models.state import ensure_card_state
            p.deck.append(ensure_card_state(cid))
            bonus_str += get_locale_text("i18n_explore_core.ancient_card_bonus", card_name=ALL_CARDS[cid].name)
        return engine._coop_finish(run, get_locale_text("i18n_explore_core.ancient_contract_coop", bonus=bonus_str))
    if option_idx < 1 or option_idx > len(options):
        return get_locale_text("err_invalid_option_idx")
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
    bonus_str = get_locale_text("i18n_explore_core.ancient_relic_bonus", relic_name=get_relic_name(rid))
    if chosen["type"] == "contract":
        cid = chosen["card"]
        from ..models.state import ensure_card_state
        p.deck.append(ensure_card_state(cid))
        bonus_str += get_locale_text("i18n_explore_core.ancient_card_bonus", card_name=ALL_CARDS[cid].name)
    engine.map_engine.enter_next_stage(run)
    engine.save_manager.save_save(run.user_id, run)
    return get_locale_text("i18n_explore_core.ancient_contract_start", bonus=bonus_str)


def handle_ancient(engine, run, option_idx, target=None) -> str | None:
    p = run.player
    options = run.node_data.get("options", [])
    if option_idx < 1 or option_idx > len(options):
        return get_locale_text("err_invalid_option_idx")
    chosen = options[option_idx - 1]
    rid = chosen["relic"]
    cid = chosen.get("card")
    p.relics.append(rid)
    if cid:
        from ..models.state import ensure_card_state
        p.deck.append(ensure_card_state(cid))
        bonus_str = get_locale_text("i18n_explore_core.ancient_blessing_card_relic", card_name=ALL_CARDS[cid].name, relic_name=get_relic_name(rid))
    else:
        bonus_str = get_locale_text("i18n_explore_core.ancient_blessing_relic", relic_name=get_relic_name(rid))
    engine.map_engine.enter_next_stage(run)
    engine.save_manager.save_save(run.user_id, run)
    return get_locale_text("i18n_explore_core.ancient_blessing", bonus=bonus_str)


def handle_treasure(engine, run, option_idx, target=None) -> str | None:
    p = run.player
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
            gold_gain = random.randint(TREASURE_GOLD_MIN, TREASURE_GOLD_MAX)
            p.gold += gold_gain
            relics_pool = TREASURE_RELIC_POOL
            available_relics = [r for r in relics_pool if r not in p.relics]
            got_relic = random.choice(available_relics) if available_relics else ""
            if got_relic:
                p.relics.append(got_relic)
                if got_relic == "red_bottle":
                    p.max_hp += 5
                    p.hp += 5
            stats = engine.save_manager.load_stats(run.user_id)
            card_pool = DeckService.get_epic_card_pool(run, p, stats)
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
            engine.map_engine.battle_engine.event_bus.dispatch(evt)
            from ..models.events import CardSelectInitEvent
            card_select_evt = CardSelectInitEvent(run, reward_cards)
            engine.map_engine.battle_engine.event_bus.dispatch(card_select_evt)
            next_node_data = {
                "title": get_locale_text("render_card_select_title"),
                "cards": reward_cards,
                "can_skip": card_select_evt.can_skip,
                "force_upgraded": card_select_evt.upgraded,
                "items": box_items
            }
            run.node_data["state"] = "opened"
            run.node_data["items"] = box_items
            engine.start_gem_insert_flow(run, gift_gem_id, "card_select", next_node_data)
            return get_locale_text("msg_sacrifice_success", removed_name=removed_name)
        available_items = [it for it in items if not it.get("taken")]
        if option_idx < 1 or option_idx > len(available_items):
            return get_locale_text("err_invalid_option_idx")
        chosen = available_items[option_idx - 1]
        if chosen.get("type") == "sacrifice":
            run.node_data["pending_remove"] = True
            run.node_data["remove_source"] = "treasure"
            engine.save_manager.save_save(run.user_id, run)
            return get_locale_text("msg_sacrifice_started")
    else:
        available_items = [it for it in items if not it.get("taken")]
        if option_idx < 1 or option_idx > len(available_items):
            return get_locale_text("err_invalid_option_idx")
        chosen = available_items[option_idx - 1]
        real_idx = items.index(chosen)
        res = engine._claim_single_item(run, real_idx)
        if run.node_type != "treasure":
            engine.save_manager.save_save(run.user_id, run)
            return res
        available = [it for it in items if not it.get("taken")]
        if not available:
            if getattr(run, "coop_id", ""):
                return engine._coop_finish(run, f"{res}\n{get_locale_text('msg_rewards_claimed_finished')}")
            engine.map_engine.enter_next_stage(run)
            engine.save_manager.save_save(run.user_id, run)
            return f"{res}\n{get_locale_text('msg_rewards_claimed_finished')}"
        engine.save_manager.save_save(run.user_id, run)
        return res


def handle_boss_chest(engine, run, option_idx, target=None) -> str | None:
    items = run.node_data.setdefault("items", [])
    available_items = [it for it in items if not it.get("taken")]
    if option_idx < 1 or option_idx > len(available_items):
        return get_locale_text("err_invalid_option_idx")
    chosen = available_items[option_idx - 1]
    real_idx = items.index(chosen)
    res = engine._claim_single_item(run, real_idx)
    if run.node_type != "boss_chest":
        engine.save_manager.save_save(run.user_id, run)
        return res
    available = [it for it in items if not it.get("taken")]
    if not available:
        if getattr(run, "coop_id", ""):
            return engine._coop_finish(run, f"{res}\n{get_locale_text('msg_boss_chest_finished')}")
        engine.map_engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return f"{res}\n{get_locale_text('msg_boss_chest_finished')}"
    engine.save_manager.save_save(run.user_id, run)
    return res


def handle_reward(engine, run, option_idx, target=None) -> str | None:
    if run.node_data.get("no_reward"):
        engine.map_engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("msg_escape_battle_win")
    items = run.node_data.setdefault("items", [])
    available_items = [it for it in items if not it.get("taken")]
    if option_idx < 1 or option_idx > len(available_items):
        return get_locale_text("err_invalid_option_idx")
    chosen = available_items[option_idx - 1]
    real_idx = items.index(chosen)
    res = engine._claim_single_item(run, real_idx)
    if run.node_type != "reward":
        engine.save_manager.save_save(run.user_id, run)
        return res
    available = [it for it in items if not it.get("taken")]
    if not available:
        engine.map_engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return f"{res}\n{get_locale_text('msg_rewards_claimed_finished')}"
    engine.save_manager.save_save(run.user_id, run)
    return res


def handle_corpse_reward(engine, run, option_idx, target=None) -> str | None:
    p = run.player
    cards = run.node_data.get("cards", [])
    picks_left = int(run.node_data.get("picks_left", 0))
    skip_idx = len(cards) + 1
    if picks_left <= 0:
        stage = p.stage
        engine.map_engine.return_to_map_select(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.corpse_search_complete", stage=stage)
    if option_idx < 1 or option_idx > skip_idx:
        return get_locale_text("err_invalid_option_idx")
    if option_idx == skip_idx:
        msg = get_locale_text("i18n_explore_core.corpse_skip")
    else:
        from ..models.state import ensure_card_state
        c_state = ensure_card_state(cards[option_idx - 1])
        from ..models.events import CardObtainEvent
        obtain_evt = CardObtainEvent(run, c_state)
        engine.map_engine.battle_engine.event_bus.dispatch(obtain_evt)
        p.deck.append(c_state)
        cards.pop(option_idx - 1)
        card = ALL_CARDS.get(c_state)
        msg = get_locale_text("i18n_explore_core.corpse_taken", card_name=card.name if card else c_state.id)
    picks_left -= 1
    run.node_data["picks_left"] = picks_left
    run.node_data["cards"] = cards
    if picks_left <= 0:
        corpse_id = run.node_data.get("corpse_id")
        if corpse_id:
            engine.save_manager.corpses.remove(corpse_id)
        stage = p.stage
        engine.map_engine.return_to_map_select(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.corpse_return", msg=msg, stage=stage)
    engine.save_manager.save_save(run.user_id, run)
    return get_locale_text("i18n_explore_core.corpse_remaining", msg=msg, picks_left=picks_left)


def handle_card_select(engine, run, option_idx, target=None) -> str | None:
    p = run.player
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
        engine.map_engine.battle_engine.event_bus.dispatch(obtain_evt)
        p.deck.append(c_state)
        card = ALL_CARDS.get(cid)
        msg = get_locale_text("msg_card_added_to_deck", card_name=card.name if card else cid)
    next_type = run.node_data.get("next_node_type")
    next_data = run.node_data.get("next_node_data")
    if next_type:
        run.node_type = next_type
        run.node_data = next_data
        engine.save_manager.save_save(run.user_id, run)
        available = [it for it in run.node_data.setdefault("items", []) if not it.get("taken")]
        if not available:
            if getattr(run, "coop_id", ""):
                return engine._coop_finish(run, f"{msg}\n{get_locale_text('msg_rewards_claimed_finished')}")
            engine.map_engine.enter_next_stage(run)
            engine.save_manager.save_save(run.user_id, run)
            return f"{msg}\n{get_locale_text('msg_rewards_claimed_finished')}"
        return msg
    else:
        if getattr(run, "coop_id", ""):
            return engine._coop_finish(run, msg)
        engine.map_engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.next_stage_suffix", msg=msg)


def handle_rest(engine, run, option_idx, target=None) -> str | None:
    p = run.player
    items = run.node_data.setdefault("items", [])
    if not items:
        engine._init_rest_node(run)
        items = run.node_data["items"]
    itype = None
    if option_idx == 1:
        itype = "rest_heal"
    elif option_idx == 2:
        itype = "rest_meditate"
    elif option_idx in (3, 4):
        itype = "rest_upgrade"
    else:
        return get_locale_text("err_invalid_option_idx")
    if itype != "rest_upgrade":
        for it in items:
            it["taken"] = True
    if itype == "rest_heal":
        heal = int(p.max_hp * REST_HEAL_RATIO)
        p.hp = min(p.max_hp, p.hp + heal)
        engine.map_engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("msg_rest_heal", heal=heal)
    elif itype == "rest_meditate":
        stats = engine.save_manager.load_stats(run.user_id)
        class_cards = DeckService.get_class_spell_pool(p, stats)
        reward_cards = random.sample(class_cards, 3) if len(class_cards) >= 3 else class_cards
        from ..models.state import check_and_replace_fireball
        reward_cards = [check_and_replace_fireball(run, cid) for cid in reward_cards]
        run.node_type = "card_select"
        run.node_data = {
            "title": get_locale_text("i18n_explore_core.meditate_title"),
            "desc": get_locale_text("i18n_explore_core.meditate_desc"),
            "cards": reward_cards,
            "next_node_type": "rest",
            "next_node_data": run.node_data
        }
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("msg_rest_meditate")
    elif itype == "rest_upgrade":
        run.node_data["upgrade_source"] = "rest"
        engine.save_manager.save_save(run.user_id, run)
        return "UPGRADE_FLOW"


def handle_event(engine, run, option_idx, target=None) -> str | None:
    if getattr(run, "coop_id", ""):
        if run.node_data.get("coop_done"):
            return get_locale_text("i18n_explore_core.coop_node_waiting")
        options = run.node_data.get("options", [])
        if option_idx < 1 or option_idx > len(options):
            return get_locale_text("err_invalid_option_idx")
        opt = options[option_idx - 1]
        option_executor = get_option_by_action(opt.get("action"))
        if not option_executor:
            return engine._coop_finish(run, get_locale_text("i18n_explore_core.event_leave_coop"))
        proxy = _CoopEventProxy(engine.map_engine)
        res = option_executor.execute(run, proxy)
        if proxy.finished:
            return engine._coop_finish(run, res)
        engine._coop(run).persist_view(run, run.user_id)
        engine.save_manager.save_coop_save(run.user_id, run)
        return res
    options = run.node_data.get("options", [])
    if option_idx < 1 or option_idx > len(options):
        return get_locale_text("err_invalid_option_idx")
    opt = options[option_idx - 1]
    act = opt.get("action")
    option_executor = get_option_by_action(act)
    if option_executor:
        return option_executor.execute(run, engine.map_engine)
    else:
        engine.map_engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.event_leave_next")


def handle_shop(engine, run, option_idx, target=None) -> str | None:
    p = run.player
    items = run.node_data.get("items", [])
    if option_idx < 1 or option_idx > len(items):
        return get_locale_text("i18n_explore_core.err_invalid_shop_item")
    item = items[option_idx - 1]
    if item.get("sold"):
        return get_locale_text("i18n_explore_core.err_shop_sold_out")
    price = item.get("price")
    if p.gold < price:
        return get_locale_text("i18n_explore_core.err_not_enough_gold", price=price, gold=p.gold)
    itype = item.get("type")
    if itype == "card":
        p.gold -= price
        cid = item.get("card_id")
        from ..models.state import ensure_card_state
        c_state = ensure_card_state(cid)
        from ..models.events import CardObtainEvent
        engine.map_engine.battle_engine.event_bus.dispatch(CardObtainEvent(run, c_state))
        p.deck.append(c_state)
        item["sold"] = True
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.shop_card_bought", card_name=ALL_CARDS[cid].name)
    elif itype == "relic":
        p.gold -= price
        rid = item.get("relic_id")
        p.relics.append(rid)
        item["sold"] = True
        if rid == "red_bottle":
            p.max_hp += 5
            p.hp += 5
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.shop_relic_bought", relic_name=get_relic_name(rid))
    elif itype == "gem":
        p.gold -= price
        gem_id = item.get("gem_id")
        item["sold"] = True
        shop_node_data = {"items": items}
        res = engine.start_gem_insert_flow(run, gem_id, "shop", shop_node_data)
        return get_locale_text("i18n_explore_core.shop_purchase_prefix", result=res)
    elif itype == "remove":
        return "REMOVE_FLOW"
    elif itype == "upgrade":
        run.node_data["upgrade_price"] = price
        run.node_data["upgrade_source"] = "shop"
        return "UPGRADE_FLOW"
    elif itype == "leave":
        if getattr(run, "coop_id", ""):
            return engine._coop_finish(run, get_locale_text("i18n_explore_core.shop_leave_coop"))
        engine.map_engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.shop_leave_next")


NODE_HANDLERS = {
    "start_ancient": handle_start_ancient,
    "ancient": handle_ancient,
    "treasure": handle_treasure,
    "boss_chest": handle_boss_chest,
    "reward": handle_reward,
    "corpse_reward": handle_corpse_reward,
    "card_select": handle_card_select,
    "rest": handle_rest,
    "event": handle_event,
    "shop": handle_shop
}


def resolve_node_handler(node_type):
    return NODE_HANDLERS.get(node_type)
