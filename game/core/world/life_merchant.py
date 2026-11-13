import copy
import math
import random

from ...data.balance_config import (
    LIFE_MERCHANT_ITEM_RATIO,
    LIFE_MERCHANT_LEGENDARY_RATIO,
    LIFE_MERCHANT_MIN_MAX_HP,
    LIFE_MERCHANT_MYTHIC_RATIO,
    LIFE_MERCHANT_SHOU_HUI_CHANCE,
    LIFE_MERCHANT_SHOU_HUI_HP_BONUS,
    LIFE_MERCHANT_UPGRADE_COUNT,
    LIFE_MERCHANT_UPGRADE_RATIO,
)
from ...data.card_upgrade_data import CARD_UPGRADE_CONFIG
from ...data.gem_data import GEM_CONFIG
from ...data.locale_data import get_locale_text
from ...data.potion_data import POTION_SLOT_LIMIT, get_potion_name
from ...data.relic_data import RELIC_CONFIG
from ...data.reward_config import (
    LIFE_MERCHANT_EXCLUDED_MYTHIC_CARDS,
    LIFE_MERCHANT_EXCLUSIVE_CARDS,
    LIFE_MERCHANT_EXCLUSIVE_RELICS,
    LIFE_MERCHANT_LEGENDARY_GEMS,
    LIFE_MERCHANT_LEGENDARY_RELICS,
    LIFE_MERCHANT_MYTHIC_RELICS,
    LIFE_MERCHANT_POWER_POTIONS,
)
from ...entities import ALL_CARDS, get_relic_name
from ...models.events import CardObtainEvent
from ...models.state import ensure_card_state
from ..progress.achievement_service import AchievementService
from ..inventory.deck_service import DeckService


def calc_life_merchant_price(max_hp: int, item: dict) -> int:
    if item.get("fixed_price") is not None:
        return int(item["fixed_price"])
    ratio = float(item.get("ratio", 0.0) or 0.0)
    if ratio <= 0:
        return 0
    return max(1, math.ceil(max_hp * ratio))


def _ratio_for_card(cid: str) -> float:
    card = ALL_CARDS.get(cid)
    rarity = getattr(card, "rarity", "legendary") if card else "legendary"
    if rarity == "mythic":
        return LIFE_MERCHANT_MYTHIC_RATIO
    return LIFE_MERCHANT_LEGENDARY_RATIO


def _ratio_for_relic(rid: str) -> float:
    rarity = RELIC_CONFIG.get(rid, {}).get("rarity", "legendary")
    if rarity == "mythic":
        return LIFE_MERCHANT_MYTHIC_RATIO
    return LIFE_MERCHANT_LEGENDARY_RATIO


def build_life_merchant_items(save_manager, run) -> list[dict]:
    p = run.player
    stats = save_manager.load_stats(run.user_id) if hasattr(save_manager, "load_stats") else None
    items = []

    exclusive_cid = random.choice(LIFE_MERCHANT_EXCLUSIVE_CARDS)
    items.append({
        "type": "card",
        "card_id": exclusive_cid,
        "ratio": _ratio_for_card(exclusive_cid),
        "sold": False,
    })

    owned_relics = set(p.relics or [])
    exclusive_relics = [rid for rid in LIFE_MERCHANT_EXCLUSIVE_RELICS if rid not in owned_relics]
    chosen_exclusive_relic = ""
    if exclusive_relics:
        chosen_exclusive_relic = random.choice(exclusive_relics)
        items.append({
            "type": "relic",
            "relic_id": chosen_exclusive_relic,
            "ratio": _ratio_for_relic(chosen_exclusive_relic),
            "sold": False,
        })
    else:
        fallback_relics = [
            rid for rid in (LIFE_MERCHANT_MYTHIC_RELICS + LIFE_MERCHANT_LEGENDARY_RELICS)
            if rid not in owned_relics
        ]
        if fallback_relics:
            chosen_exclusive_relic = random.choice(fallback_relics)
            items.append({
                "type": "relic",
                "relic_id": chosen_exclusive_relic,
                "ratio": _ratio_for_relic(chosen_exclusive_relic),
                "sold": False,
            })

    class_color = DeckService._class_color(p)
    mythic_pool = DeckService.eligible_card_ids(
        stats,
        colors=(class_color, "neutral"),
        rarities=("mythic",),
        allow_coop=run.player_count() > 1,
        require_available=False,
    )
    killed_yog = bool(stats and getattr(stats, "yog_sothoth_kill_count", 0) > 0)
    mythic_pool = [
        cid for cid in mythic_pool
        if cid not in LIFE_MERCHANT_EXCLUDED_MYTHIC_CARDS
        and (killed_yog or cid != "neutral_button_magic")
    ]
    non_dup_mythic = [cid for cid in mythic_pool if cid != exclusive_cid]
    if non_dup_mythic:
        mythic_cid = random.choice(non_dup_mythic)
    elif mythic_pool:
        mythic_cid = random.choice(mythic_pool)
    else:
        mythic_cid = "neutral_omega"
    items.append({
        "type": "card",
        "card_id": mythic_cid,
        "ratio": LIFE_MERCHANT_MYTHIC_RATIO,
        "sold": False,
    })

    relic_pool = []
    for rid in (LIFE_MERCHANT_MYTHIC_RELICS + LIFE_MERCHANT_LEGENDARY_RELICS):
        if rid not in owned_relics and rid != chosen_exclusive_relic and rid not in relic_pool:
            relic_pool.append(rid)
    if relic_pool:
        random_rid = random.choice(relic_pool)
        items.append({
            "type": "relic",
            "relic_id": random_rid,
            "ratio": _ratio_for_relic(random_rid),
            "sold": False,
        })
    else:
        legendary_pool = DeckService.eligible_card_ids(
            stats,
            colors=(class_color, "neutral"),
            rarities=("legendary",),
            allow_coop=run.player_count() > 1,
            require_available=False,
        )
        if legendary_pool:
            leg_cid = random.choice(legendary_pool)
            items.append({
                "type": "card",
                "card_id": leg_cid,
                "ratio": LIFE_MERCHANT_LEGENDARY_RATIO,
                "sold": False,
            })

    if random.random() < 0.5:
        gid = random.choice(LIFE_MERCHANT_LEGENDARY_GEMS)
        items.append({
            "type": "gem",
            "gem_id": gid,
            "ratio": LIFE_MERCHANT_ITEM_RATIO,
            "sold": False,
        })
    else:
        pid = random.choice(LIFE_MERCHANT_POWER_POTIONS)
        items.append({
            "type": "potion",
            "potion_id": pid,
            "ratio": LIFE_MERCHANT_ITEM_RATIO,
            "sold": False,
        })

    items.append({
        "type": "life_upgrade",
        "ratio": LIFE_MERCHANT_UPGRADE_RATIO,
        "count": LIFE_MERCHANT_UPGRADE_COUNT,
        "sold": False,
    })

    if random.random() < LIFE_MERCHANT_SHOU_HUI_CHANCE:
        items.append({
            "type": "card",
            "card_id": "curse_shou_hui",
            "fixed_price": -LIFE_MERCHANT_SHOU_HUI_HP_BONUS,
            "sold": False,
        })

    items.append({
        "type": "leave",
        "fixed_price": 0,
        "sold": False,
    })
    return items


def init_life_merchant_node(explore_engine, run):
    from ..party.coordinator import apply_and_scope, restore_player, swap_player
    ach = AchievementService(explore_engine.save_manager)
    views = {}
    ready = {}
    shop_map = {}
    for uid in run.party_order:
        player = run.players.get(uid)
        if player is None:
            continue
        if getattr(player, "is_mercenary", False):
            views[uid] = {"node_type": "life_merchant", "data": {"items": [], "coop_done": True}}
            shop_map[uid] = []
            ready[uid] = True
            continue
        previous, previous_user = swap_player(run, player)
        ach.record_stat(uid, "life_merchant_visits", 1)
        items = build_life_merchant_items(explore_engine.save_manager, run)
        views[uid] = {"node_type": "life_merchant", "data": {"items": items}}
        shop_map[uid] = items
        ready[uid] = player.downed
        restore_player(run, previous, previous_user)
    run.node_type = "life_merchant"
    run.node_data = {
        "coop_node_type": "life_merchant",
        "player_views": views,
        "player_shops": shop_map,
        "stage_ready": ready,
    }
    apply_and_scope(run, run.user_id)


def handle_life_merchant(explore_engine, run, option_idx: int, target=None) -> str:
    from ..party.coordinator import finish_player_node
    p = run.player
    items = run.node_data.get("items", [])
    if option_idx < 1 or option_idx > len(items):
        return get_locale_text("i18n_explore_core.err_invalid_shop_item")
    item = items[option_idx - 1]
    if item.get("sold"):
        return get_locale_text("i18n_explore_core.err_shop_sold_out")
    itype = item.get("type")
    if itype == "leave":
        msg = get_locale_text("i18n_explore_core.life_merchant_leave_coop") if run.player_count() > 1 else get_locale_text("i18n_explore_core.life_merchant_leave_next")
        return finish_player_node(explore_engine.save_manager, explore_engine.map_engine, run, run.user_id, msg)
    if itype == "potion":
        pid = item.get("potion_id")
        if not hasattr(p, "potions") or p.potions is None:
            p.potions = []
        if len(p.potions) >= POTION_SLOT_LIMIT:
            return get_locale_text("i18n_explore_core.life_merchant_potion_full", potion_name=get_potion_name(pid))

    upgrade_candidates = []
    if itype == "life_upgrade":
        for idx, c in enumerate(p.deck):
            c_state = ensure_card_state(c)
            if not c_state.upgraded and c_state.id in CARD_UPGRADE_CONFIG:
                upgrade_candidates.append(idx)
        if not upgrade_candidates:
            return get_locale_text("i18n_explore_core.life_merchant_upgrade_none")

    cost = calc_life_merchant_price(p.max_hp, item)
    if cost > 0:
        if p.max_hp - cost < LIFE_MERCHANT_MIN_MAX_HP:
            return get_locale_text(
                "i18n_explore_core.err_life_merchant_min_hp",
                min_hp=LIFE_MERCHANT_MIN_MAX_HP,
                max_hp=p.max_hp,
                cost=cost,
            )
        p.max_hp -= cost
        p.hp = min(p.hp, p.max_hp)
    elif cost < 0:
        gain = -cost
        p.max_hp += gain
        p.hp += gain

    ach = AchievementService(explore_engine.save_manager)
    stats = explore_engine.save_manager.load_stats(run.user_id) if hasattr(explore_engine.save_manager, "load_stats") else None
    ach.record_stat(run.user_id, "life_merchant_purchases", 1, stats=stats, save=False)
    ach.record_stat(run.user_id, "min_max_hp_reached", p.max_hp, mode="min", stats=stats, save=True)

    if itype == "card":
        cid = item.get("card_id")
        c_state = ensure_card_state(cid)
        explore_engine.map_engine.battle_engine.event_bus.dispatch(CardObtainEvent(run, c_state))
        p.deck.append(c_state)
        item["sold"] = True
        explore_engine.save_manager.save_save(run.user_id, run)
        cname = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
        if cost < 0:
            return get_locale_text(
                "i18n_explore_core.life_merchant_card_bonus_bought",
                gain=-cost,
                card_name=cname,
            )
        return get_locale_text(
            "i18n_explore_core.life_merchant_card_bought",
            cost=cost,
            card_name=cname,
        )

    if itype == "relic":
        rid = item.get("relic_id")
        from ..inventory.relic_service import grant_relic
        grant_relic(p, rid)
        if rid == "red_bottle":
            p.max_hp += 5
            p.hp += 5
        item["sold"] = True
        explore_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text(
            "i18n_explore_core.life_merchant_relic_bought",
            cost=cost,
            relic_name=get_relic_name(rid),
        )

    if itype == "gem":
        gem_id = item.get("gem_id")
        item["sold"] = True
        next_data = {"items": items}
        res = explore_engine.start_gem_insert_flow(run, gem_id, "life_merchant", next_data)
        return get_locale_text(
            "i18n_explore_core.life_merchant_gem_bought",
            cost=cost,
            result=res,
        )

    if itype == "potion":
        pid = item.get("potion_id")
        p.potions.append(pid)
        item["sold"] = True
        explore_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text(
            "i18n_explore_core.life_merchant_potion_bought",
            cost=cost,
            potion_name=get_potion_name(pid),
        )

    if itype == "life_upgrade":
        limit = int(item.get("count", LIFE_MERCHANT_UPGRADE_COUNT))
        picked_indices = random.sample(upgrade_candidates, min(limit, len(upgrade_candidates)))
        upgraded_names = []
        for idx in picked_indices:
            c_state = ensure_card_state(p.deck[idx])
            new_state = copy.copy(c_state)
            new_state.upgraded = True
            p.deck[idx] = new_state
            upgraded_names.append(ALL_CARDS[new_state].name if new_state in ALL_CARDS else new_state.id)
        item["sold"] = True
        explore_engine.save_manager.save_save(run.user_id, run)
        sep = get_locale_text("i18n_explore_core.list_delimiter")
        return get_locale_text(
            "i18n_explore_core.life_merchant_upgrade_bought",
            cost=cost,
            names=sep.join(upgraded_names),
        )

    return get_locale_text("i18n_explore_core.err_unknown_action")
