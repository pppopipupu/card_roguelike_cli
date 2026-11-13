import random

from ...entities import ALL_CARDS, get_relic_name
from ...entities.events import get_option_by_action
from ...data.balance_config import (
    COOP_AUTO_TARGET_CANDIDATE_COUNT,
    COOP_BUFF_STACKS_MIN,
    COOP_DOWNED_HP,
    COOP_MEND_CLEANSE_STACKS,
    COOP_PERCENT_BASE,
    COOP_REST_HEAL_PERCENT,
    COOP_REST_MEND_PERCENT,
    REST_HEAL_RATIO,
    REWARD_CARD_COUNT,
    TREASURE_GOLD_MAX,
    TREASURE_GOLD_MIN,
)
from ...data.reward_config import TREASURE_RELIC_POOL
from ...data.locale_data import get_locale_text
from ..inventory.deck_service import DeckService
from ..party.coordinator import add_notice, finish_player_node, restore_player, swap_player, vote_option

class _TeamEventSaveManager:
    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def save_save(self, *args, **kwargs):
        return False



class _TeamEventBattleEngine:
    def __init__(self, real, owner):
        self._real = real
        self._owner = owner

    def __getattr__(self, name):
        return getattr(self._real, name)

    def _init_battle_node(self, run, difficulty="normal"):
        if self._owner.suppress:
            return
        self._owner.battle_done = True
        return self._real._init_battle_node(run, difficulty)


class _TeamEventExploreEngine:
    def __init__(self, real, owner):
        self._real = real
        self._owner = owner

    def __getattr__(self, name):
        return getattr(self._real, name)

    def _init_shop_node(self, run):
        if self._owner.suppress:
            return
        self._owner.shop_done = True
        return self._real._init_shop_node(run)

    def start_gem_insert_flow(self, run, gem_id, next_type, next_data):
        if self._owner.suppress:
            return ""
        self._owner.gem_id = gem_id
        from ...data.gem_data import GEM_CONFIG
        return get_locale_text("i18n_explore_core.gem_gained", gem_name=GEM_CONFIG[gem_id]["name"])


class _TeamEventProxy:
    def __init__(self, map_engine):
        self._map_engine = map_engine
        self.advance = False
        self.suppress = False
        self.battle_done = False
        self.shop_done = False
        self.gem_id = ""

    def __getattr__(self, name):
        return getattr(self._map_engine, name)

    @property
    def save_manager(self):
        return _TeamEventSaveManager(self._map_engine.save_manager)

    @property
    def battle_engine(self):
        return _TeamEventBattleEngine(self._map_engine.battle_engine, self)

    @property
    def explore_engine(self):
        return _TeamEventExploreEngine(self._map_engine.explore_engine, self)

    def enter_next_stage(self, run):
        self.advance = True


def _team_auto_flow(run, flow, gem_id):
    from ...models.state import ensure_card_state
    from ...entities.cards.base import ALL_CARDS
    if flow == "UPGRADE_FLOW":
        from ...data.card_upgrade_data import CARD_UPGRADE_CONFIG
        for player in [run.players[u] for u in run.human_uids() if u in run.players]:
            for card_state in player.deck:
                if not card_state.upgraded and card_state.id in CARD_UPGRADE_CONFIG:
                    card_state.upgraded = True
                    break
        return get_locale_text("i18n_explore_core.event_team_upgrade")
    if flow == "REMOVE_FLOW":
        return ""
    if run.node_type == "card_select":
        cards = run.node_data.get("cards", [])
        if not cards:
            return ""
        cid = cards[0]
        for player in [run.players[u] for u in run.human_uids() if u in run.players]:
            player.deck.append(ensure_card_state(cid))
        return get_locale_text("i18n_explore_core.event_team_card", card_name=ALL_CARDS[cid].name if cid in ALL_CARDS else cid)
    if gem_id:
        from ...data.gem_data import GEM_CONFIG
        for player in [run.players[u] for u in run.human_uids() if u in run.players]:
            for card_state in player.deck:
                card_obj = ALL_CARDS.get(card_state)
                if card_obj and len(card_state.gems or []) < card_obj.get_gem_slots_count():
                    card_state.gems = list(card_state.gems or []) + [gem_id]
                    break
        return get_locale_text("i18n_explore_core.event_team_gem", gem_name=GEM_CONFIG[gem_id]["name"])
    return ""


def _resolve_coop_event(engine, run, option_idx):
    import copy
    options = run.node_data.get("options", [])
    opt = options[option_idx - 1]
    executor = get_option_by_action(opt.get("action"))
    if not executor:
        engine.map_engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.event_leave_coop")
    proxy = _TeamEventProxy(engine.map_engine)
    results = []
    first_result = ""
    order = [uid for uid in run.human_uids() if uid in run.players]
    for index, uid in enumerate(order):
        player = run.players[uid]
        previous, previous_user = swap_player(run, player)
        snapshot = None
        saved_type = None
        if index > 0:
            proxy.suppress = True
            snapshot = copy.deepcopy(run.node_data)
            saved_type = run.node_type
        try:
            res = executor.execute(run, proxy)
        finally:
            if index > 0:
                run.node_data = snapshot
                run.node_type = saved_type
            restore_player(run, previous, previous_user)
        if index == 0:
            first_result = res or ""
        if res and res not in ("UPGRADE_FLOW", "REMOVE_FLOW"):
            results.append((player.name, res))
    from ..battle.party_battle import mark_downed
    for player in run.players.values():
        if player.hp <= 0 and not player.downed:
            mark_downed(engine.map_engine.battle_engine, run, player)
    run.node_data["votes"] = {}
    if proxy.battle_done:
        engine.save_manager.save_save(run.user_id, run)
    elif proxy.shop_done:
        from ...models import coop_view
        coop_view.apply_view(run, run.user_id)
        engine.save_manager.save_save(run.user_id, run)
    elif proxy.advance or first_result in ("UPGRADE_FLOW", "REMOVE_FLOW") or proxy.gem_id or run.node_type in ("card_select", "gem_insert"):
        extra = _team_auto_flow(run, first_result, proxy.gem_id)
        if extra:
            results.append(("", extra))
        engine.map_engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
    else:
        engine.save_manager.save_save(run.user_id, run)
    lines = [get_locale_text("i18n_explore_core.event_team_result_header")]
    for name, res in results:
        if name:
            lines.append(get_locale_text("i18n_explore_core.event_result_entry", name=name, result=res))
        else:
            lines.append(res)
    return "\n".join(lines)


def handle_start_ancient(engine, run, option_idx, target=None) -> str | None:
    p = run.player
    if run.node_data.get("coop_done"):
        return get_locale_text("i18n_coop_explore.coop_done_waiting")
    options = run.node_data.get("options", [])
    if option_idx < 1 or option_idx > len(options):
        return get_locale_text("err_invalid_option_idx")
    chosen = options[option_idx - 1]
    rid = chosen["relic"]
    p.relics.append(rid)
    if rid == "mark_of_fury":
        p.max_hp = max(5, p.max_hp - 3)
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
        from ...models.state import ensure_card_state
        p.deck.append(ensure_card_state(cid))
        bonus_str += get_locale_text("i18n_explore_core.ancient_card_bonus", card_name=ALL_CARDS[cid].name)
    msg = get_locale_text("i18n_explore_core.ancient_contract_coop", bonus=bonus_str) if run.player_count() > 1 else get_locale_text("i18n_explore_core.ancient_contract_start", bonus=bonus_str)
    return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, msg)


def handle_ancient(engine, run, option_idx, target=None) -> str | None:
    p = run.player
    if run.node_data.get("coop_done"):
        return get_locale_text("i18n_coop_explore.coop_done_waiting")
    options = run.node_data.get("options", [])
    if option_idx < 1 or option_idx > len(options):
        return get_locale_text("err_invalid_option_idx")
    chosen = options[option_idx - 1]
    rid = chosen["relic"]
    cid = chosen.get("card")
    p.relics.append(rid)
    if cid:
        from ...models.state import ensure_card_state
        p.deck.append(ensure_card_state(cid))
        bonus_str = get_locale_text("i18n_explore_core.ancient_blessing_card_relic", card_name=ALL_CARDS[cid].name, relic_name=get_relic_name(rid))
    else:
        bonus_str = get_locale_text("i18n_explore_core.ancient_blessing_relic", relic_name=get_relic_name(rid))
    msg = get_locale_text("i18n_explore_core.ancient_blessing", bonus=bonus_str)
    return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, msg)

def handle_treasure(engine, run, option_idx, target=None) -> str | None:
    p = run.player
    items = run.node_data.setdefault("items", [])
    if not items:
        items.append({"type": "sacrifice", "taken": False})
        run.node_data["items"] = items
    state = run.node_data.get("state", "pending_remove")
    if state == "pending_remove":
        if option_idx > 1:
            from ...models.state import ensure_card_state
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
            got_relic = ""
            if run.player_count() <= 1:
                available_relics = [r for r in relics_pool if r not in p.relics]
                got_relic = random.choice(available_relics) if available_relics else ""
            if got_relic:
                p.relics.append(got_relic)
                if got_relic == "red_bottle":
                    p.max_hp += 5
                    p.hp += 5
            stats = engine.save_manager.load_stats(run.user_id) if hasattr(engine.save_manager, "load_stats") else None
            card_pool = DeckService.get_epic_card_pool(run, p, stats)
            reward_cards = random.sample(card_pool, 3) if len(card_pool) >= 3 else card_pool
            from ...models.state import check_and_replace_fireball
            reward_cards = [check_and_replace_fireball(run, cid_) for cid_ in reward_cards]
            from ...data.gem_data import GEM_CONFIG
            gift_gem_id = random.choice(list(GEM_CONFIG.keys()))
            box_items = [
                {"type": "gold", "amount": gold_gain, "taken": True},
                {"type": "card_reward", "cards": reward_cards, "taken": False, "force": False},
                {"type": "gem", "gem_id": gift_gem_id, "taken": False}
            ]
            if got_relic:
                box_items.append({"type": "relic", "relic_id": got_relic, "taken": True})
            from ...models.events import RewardGenerateEvent
            evt = RewardGenerateEvent(run, box_items)
            engine.map_engine.battle_engine.event_bus.dispatch(evt)
            from ...models.events import CardSelectInitEvent
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
        pool = run.node_data.get("coop_relic_pool") or []
        if 1 <= option_idx <= len(pool):
            return _claim_coop_relic(engine, run, option_idx - 1)
        option_idx -= len(pool)
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
            return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, f"{res}\n{get_locale_text('msg_rewards_claimed_finished')}")
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
        return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, f"{res}\n{get_locale_text('msg_boss_chest_finished')}")
    engine.save_manager.save_save(run.user_id, run)
    return res


def _coop_relic_limit(run, pool):
    total = len(pool)
    if total <= 0:
        return 0
    humans = 0
    mercenaries = 0
    for uid in run.party_order or list(run.players):
        player = run.players.get(uid)
        if player is None or player.downed or player.hp <= 0:
            continue
        if getattr(player, "is_mercenary", False):
            mercenaries += 1
        else:
            humans += 1
    if humans <= 0:
        return 0
    share = max(1, total - mercenaries)
    return -(-share // humans)


def _claim_coop_relic(engine, run, pool_idx):
    data = run.node_data
    pool = data.get("coop_relic_pool") or []
    if pool_idx < 0 or pool_idx >= len(pool):
        return get_locale_text("i18n_coop_explore.err_invalid_reward_idx")
    entry = pool[pool_idx]
    rid = entry.get("relic_id")
    if entry.get("claimed_by"):
        claimant = run.players.get(entry["claimed_by"])
        player_name = claimant.name if claimant else entry["claimed_by"]
        return get_locale_text(
            "i18n_coop_explore.relic_claimed_by_other",
            relic_name=get_relic_name(rid),
            player_name=player_name,
        )
    uid = run.user_id
    limit = _coop_relic_limit(run, pool)
    if sum(1 for item in pool if item.get("claimed_by") == uid) >= limit:
        return get_locale_text("i18n_coop_explore.relic_limit_reached", limit=limit)
    player = run.players.get(uid) or run.player
    if rid in player.relics:
        return get_locale_text("i18n_coop_explore.relic_already_owned", relic_name=get_relic_name(rid))
    entry["claimed_by"] = uid
    player.relics.append(rid)
    if rid == "red_bottle":
        player.max_hp += 5
        player.hp += 5
    notice = get_locale_text(
        "i18n_coop_explore.relic_taken_notice",
        player_name=player.name,
        relic_name=get_relic_name(rid),
    )
    for other_uid in run.party_order:
        if other_uid != uid:
            add_notice(run, other_uid, notice)
    msg = get_locale_text("i18n_coop_explore.relic_gained", relic_name=get_relic_name(rid))
    items = data.get("items", [])
    if not [item for item in items if not item.get("taken")]:
        return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, msg)
    engine.save_manager.save_save(run.user_id, run)
    return msg


def handle_reward(engine, run, option_idx, target=None) -> str | None:
    if run.node_data.get("coop_done"):
        return get_locale_text("i18n_coop_explore.coop_done_waiting")
    if run.node_data.get("no_reward"):
        return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, get_locale_text("msg_escape_battle_win"))
    pool = run.node_data.get("coop_relic_pool") or []
    if 1 <= option_idx <= len(pool):
        return _claim_coop_relic(engine, run, option_idx - 1)
    local_idx = option_idx - len(pool)
    items = run.node_data.setdefault("items", [])
    available_items = [it for it in items if not it.get("taken")]
    if local_idx < 1 or local_idx > len(available_items):
        if pool:
            return get_locale_text("i18n_coop_explore.err_invalid_reward_idx")
        return get_locale_text("err_invalid_option_idx")
    chosen = available_items[local_idx - 1]
    real_idx = items.index(chosen)
    res = engine._claim_single_item(run, real_idx)
    if run.node_type != "reward":
        engine.save_manager.save_save(run.user_id, run)
        return res
    available = [it for it in items if not it.get("taken")]
    if not available:
        return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, f"{res}\n{get_locale_text('msg_rewards_claimed_finished')}")
    engine.save_manager.save_save(run.user_id, run)
    return res


def handle_corpse_reward(engine, run, option_idx, target=None) -> str | None:
    p = run.player
    cards = run.node_data.get("cards", [])
    picks_left = int(run.node_data.get("picks_left", 0))
    skip_idx = len(cards) + 1
    if picks_left <= 0:
        stage = p.stage
        engine.map_engine.return_to_grid_map(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_explore_core.corpse_search_complete", stage=stage)
    if option_idx < 1 or option_idx > skip_idx:
        return get_locale_text("err_invalid_option_idx")
    if option_idx == skip_idx:
        msg = get_locale_text("i18n_explore_core.corpse_skip")
    else:
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(cards[option_idx - 1])
        from ...models.events import CardObtainEvent
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
        engine.map_engine.return_to_grid_map(run)
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
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(cid)
        from ...models.events import CardObtainEvent
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
            return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, f"{msg}\n{get_locale_text('msg_rewards_claimed_finished')}")
        return msg
    else:
        suffix = msg if run.player_count() > 1 else get_locale_text("i18n_explore_core.next_stage_suffix", msg=msg)
        return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, suffix)


def handle_rest(engine, run, option_idx, target=None) -> str | None:
    if run.node_data.get("coop_done"):
        return get_locale_text("i18n_coop_explore.coop_done_waiting")
    p = run.player
    multi = run.player_count() > 1
    items = run.node_data.setdefault("items", [])
    if not items:
        engine._init_rest_node(run)
        items = run.node_data["items"]
    if option_idx == 1:
        for it in items:
            it["taken"] = True
        heal = (p.max_hp * COOP_REST_HEAL_PERCENT // COOP_PERCENT_BASE) if multi else int(p.max_hp * REST_HEAL_RATIO)
        p.hp = min(p.max_hp, p.hp + heal)
        from ...data.grid_map_config import SP_CONFIG
        from .persistent_buffs import cure_persistent_debuffs
        from .sp_system import reduce_exhaustion, restore_sp
        sp_gain = restore_sp(p, SP_CONFIG["rest_sp_gain"])
        old_ex = getattr(p, "exhaustion", 0)
        new_ex = reduce_exhaustion(p, SP_CONFIG["rest_exhaustion_cure"])
        cure_persistent_debuffs(p, 1)
        sp_suffix = get_locale_text("i18n_grid_map.rest_sp_suffix", sp_gain=sp_gain, exhaustion_cured=max(0, old_ex - new_ex))
        msg = (get_locale_text("i18n_coop_explore.rest_heal", heal=heal) if multi else get_locale_text("msg_rest_heal", heal=heal)) + sp_suffix
        return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, msg)
    if option_idx == 2:
        for it in items:
            it["taken"] = True
        stats = engine.save_manager.load_stats(run.user_id)
        class_cards = DeckService.get_class_spell_pool(p, stats, include_coop=multi)
        reward_cards = random.sample(class_cards, min(REWARD_CARD_COUNT, len(class_cards))) if class_cards else []
        from ...models.state import check_and_replace_fireball
        reward_cards = [check_and_replace_fireball(run, cid) for cid in reward_cards]
        engine.start_card_select(run, reward_cards, "rest", init_event=False, title_key="i18n_explore_core.meditate_title", desc_key="i18n_explore_core.meditate_desc")
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("msg_rest_meditate")
    if option_idx == 3:
        run.node_data["upgrade_source"] = "rest"
        run.node_data["pending_upgrade"] = True
        engine.save_manager.save_save(run.user_id, run)
        return "UPGRADE_FLOW"
    if option_idx == 4 and multi:
        current = run.uid_for(p)
        resolved = engine.map_engine.battle_engine.combat_resolver.resolve_ally(run, target)
        if not resolved or resolved[0] == current or resolved[2] is not None:
            candidates = [
                uid
                for uid in run.party_order
                if uid != current
                and uid in run.players
                and (run.players[uid].hp > COOP_DOWNED_HP or run.players[uid].downed)
            ]
            if len(candidates) != COOP_AUTO_TARGET_CANDIDATE_COUNT:
                names = get_locale_text("i18n_coop_explore.list_delimiter").join(f"a{run.party_order.index(uid) + 1}" for uid in candidates)
                return get_locale_text("i18n_coop_explore.mend_target_prompt", names=names)
            resolved = (candidates[0], run.players[candidates[0]], None)
        _, ally, _ = resolved
        heal = ally.max_hp * COOP_REST_MEND_PERCENT // COOP_PERCENT_BASE
        ally.hp = min(ally.max_hp, max(0, ally.hp) + heal)
        if ally.downed and ally.hp > 0:
            ally.downed = False
        from ...entities.buffs import is_debuff
        removed = ""
        for buff in list(ally.buffs):
            if is_debuff(buff.id):
                buff.stacks -= COOP_MEND_CLEANSE_STACKS
                removed = get_locale_text("i18n_coop_explore.mend_cleanse_suffix", buff_name=buff.name)
                if buff.stacks <= COOP_BUFF_STACKS_MIN:
                    ally.buffs.remove(buff)
                break
        msg = get_locale_text("i18n_coop_explore.mend_success", ally_name=ally.name, heal=heal, removed=removed)
        return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, msg)
    if option_idx == 4:
        run.node_data["upgrade_source"] = "rest"
        run.node_data["pending_upgrade"] = True
        engine.save_manager.save_save(run.user_id, run)
        return "UPGRADE_FLOW"
    return get_locale_text("err_invalid_option_idx")


def handle_event(engine, run, option_idx, target=None) -> str | None:
    options = run.node_data.get("options", [])
    if option_idx < 1 or option_idx > len(options):
        return get_locale_text("err_invalid_option_idx")
    vote_result = vote_option(run, run.user_id, option_idx, "i18n_explore_core.event_vote_recorded")
    if vote_result is not None:
        engine.save_manager.save_save(run.user_id, run)
        return vote_result
    if run.player_count() > 1:
        return _resolve_coop_event(engine, run, option_idx)
    opt = options[option_idx - 1]
    act = opt.get("action")
    option_executor = get_option_by_action(act)
    if option_executor:
        return option_executor.execute(run, engine.map_engine)
    return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, get_locale_text("i18n_explore_core.event_leave_next"))


def handle_room_dialog(engine, run, option_idx, target=None) -> str | None:
    from .rooms.npc_dialog import handle_room_dialog_choice
    return handle_room_dialog_choice(engine.map_engine, run, option_idx)


def handle_shop(engine, run, option_idx, target=None) -> str | None:
    from .rooms.shop_dialog import handle_shop_lobby_or_dialog_choice
    handled = handle_shop_lobby_or_dialog_choice(engine, run, option_idx)
    if handled is not None:
        return handled
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
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(cid)
        from ...models.events import CardObtainEvent
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
        shop_node_data = {
            "items": items,
            "shop_mode": "wares",
            "entered_via_lobby": run.node_data.get("entered_via_lobby", False),
            "merchant_defeated": run.node_data.get("merchant_defeated", False),
            "haggled": run.node_data.get("haggled", False),
            "discount_mult": run.node_data.get("discount_mult", 1.0),
        }
        res = engine.start_gem_insert_flow(run, gem_id, "shop", shop_node_data)
        return get_locale_text("i18n_explore_core.shop_purchase_prefix", result=res)
    elif itype == "remove":
        return "REMOVE_FLOW"
    elif itype == "upgrade":
        run.node_data["upgrade_price"] = price
        run.node_data["upgrade_source"] = "shop"
        return "UPGRADE_FLOW"
    elif itype == "leave":
        if run.node_data.get("entered_via_lobby"):
            from .rooms.shop_dialog import render_shop_view
            run.node_data["shop_mode"] = "lobby"
            engine.save_manager.save_save(run.user_id, run)
            return render_shop_view(run)
        msg = get_locale_text("i18n_explore_core.shop_leave_coop") if run.player_count() > 1 else get_locale_text("i18n_explore_core.shop_leave_next")
        return finish_player_node(engine.save_manager, engine.map_engine, run, run.user_id, msg)


def handle_life_merchant(engine, run, option_idx, target=None) -> str | None:
    from .life_merchant import handle_life_merchant as _handle_life_merchant
    return _handle_life_merchant(engine, run, option_idx, target)


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
    "shop": handle_shop,
    "room_dialog": handle_room_dialog,
    "life_merchant": handle_life_merchant
}


def resolve_node_handler(node_type):
    return NODE_HANDLERS.get(node_type)
