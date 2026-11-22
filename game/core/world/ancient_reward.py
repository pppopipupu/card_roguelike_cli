import random

from ...data.world.ancient_node_config import (
    ANCIENT_BLESSING_POOLS,
    ANCIENT_CLASS_LEGENDS,
    ANCIENT_ICERAINBOWW_LEGEND,
    ANCIENT_LEGEND_APPENDS,
    ANCIENT_REWARD_OPTION_TYPE,
    ANCIENT_START_POOLS,
    ANCIENT_STYLE_CHOICES,
)
from ...data.progression.balance_config import MAP_ANCIENT_OPTION_SLOTS, MAP_ANCIENT_RELIC_CHOICES
from ...data.text.locale_data import get_locale_text
from ...entities import ALL_CARDS, get_relic_name
from ...models.state import check_and_replace_fireball, ensure_card_state
from ..inventory.relic_service import grant_relic


def _resolve_pool_key(p_class: str) -> str:
    if p_class in ANCIENT_STYLE_CHOICES:
        return p_class
    return "default"


def _build_legend_candidates(base_legends: list[str], pool_key: str, stats, icerainboww_enabled: bool) -> list[str]:
    seen = set()
    pool = []
    class_extras = ANCIENT_CLASS_LEGENDS.get(pool_key, ANCIENT_CLASS_LEGENDS["default"])
    combined = list(base_legends) + list(class_extras) + list(ANCIENT_LEGEND_APPENDS)
    if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
        combined.append(ANCIENT_ICERAINBOWW_LEGEND)
    from ...entities.cards.market import is_card_available
    from ...data.world.map_quest_config import CARD_FUS_RO_DAH
    if is_card_available(CARD_FUS_RO_DAH, stats):
        combined.append(CARD_FUS_RO_DAH)
    for cid in combined:
        if cid in ALL_CARDS and cid not in seen:
            seen.add(cid)
            pool.append(cid)
    return pool


def build_start_ancient_options(run, save_manager, icerainboww_enabled: bool = True) -> dict:
    stats = save_manager.load_stats(run.user_id) if hasattr(save_manager, "load_stats") else None
    p_class = getattr(stats, "selected_class", "法师")
    pool_key = _resolve_pool_key(p_class)
    style = random.choice(ANCIENT_STYLE_CHOICES[pool_key])
    deity_pool = ANCIENT_START_POOLS[style]

    relics_pool = [{"type": "double", "relic": rid} for rid in deity_pool["relics"]]
    curse_relics = list(deity_pool["curse_relics"])
    legend_pool = _build_legend_candidates(list(deity_pool["legends"]), pool_key, stats, icerainboww_enabled)
    random.shuffle(relics_pool)
    random.shuffle(legend_pool)

    num_relics = min(len(relics_pool), random.choice(MAP_ANCIENT_RELIC_CHOICES))
    selected_relics = relics_pool[:num_relics]
    card_slots = max(0, MAP_ANCIENT_OPTION_SLOTS - len(selected_relics))
    selected_cards = []
    for i in range(card_slots):
        cid = check_and_replace_fireball(run, legend_pool[i % len(legend_pool)])
        curse_rid = curse_relics[i % len(curse_relics)]
        selected_cards.append({"type": "contract", "relic": curse_rid, "card": cid})

    options = selected_relics + selected_cards
    random.shuffle(options)
    return {"options": options, "style": style, "deity": style}


def build_ancient_options(run, save_manager) -> dict:
    p = run.player
    stats = save_manager.load_stats(run.user_id) if hasattr(save_manager, "load_stats") else None
    p_class = getattr(stats, "selected_class", "法师")
    admin_cfg = save_manager.load_admin_config() if hasattr(save_manager, "load_admin_config") else {}
    icerainboww_enabled = admin_cfg.get("icerainboww_enabled", True)
    pool_key = _resolve_pool_key(p_class)
    style = random.choice(ANCIENT_STYLE_CHOICES[pool_key])
    style_pools = ANCIENT_BLESSING_POOLS[style]

    legends_pool = _build_legend_candidates(list(style_pools["legends"]), pool_key, stats, icerainboww_enabled)
    available_relics = [r for r in style_pools["relics"] if r not in p.relics]
    if len(available_relics) < MAP_ANCIENT_OPTION_SLOTS:
        for r in style_pools["relics"]:
            if r not in available_relics:
                available_relics.append(r)

    random.shuffle(legends_pool)
    random.shuffle(available_relics)
    options = [
        {
            "type": ANCIENT_REWARD_OPTION_TYPE,
            "card": check_and_replace_fireball(run, legends_pool[i % len(legends_pool)]),
            "relic": available_relics[i % len(available_relics)],
            "deity": style,
        }
        for i in range(MAP_ANCIENT_OPTION_SLOTS)
    ]
    return {"options": options, "style": style, "deity": style}


def apply_ancient_relic_side_effects(p, rid: str) -> None:
    if rid == "mark_of_fury":
        p.max_hp = max(5, p.max_hp - 4)
        p.hp = min(p.hp, p.max_hp)
    elif rid == "vampiric_touch":
        p.max_hp = max(5, p.max_hp - 4)
        p.hp = min(p.hp, p.max_hp)
    elif rid == "glacier_armor":
        p.max_hp = max(5, p.max_hp - 5)
        p.hp = min(p.hp, p.max_hp)
    elif rid == "rainie_form":
        from ...data.entities.relic_data import RELIC_CONFIG
        grant_card = str(RELIC_CONFIG.get(rid, {}).get("grant_card", "rainie_love"))
        if grant_card and not any(ensure_card_state(card).id == grant_card for card in p.deck):
            p.deck.append(ensure_card_state(grant_card))


def grant_ancient_blessing(run, chosen, player=None) -> str:
    p = player if player is not None else run.player
    rid = chosen["relic"]
    cid = chosen.get("card")
    grant_relic(p, rid)
    apply_ancient_relic_side_effects(p, rid)
    if cid:
        p.deck.append(ensure_card_state(cid))
        bonus_str = get_locale_text(
            "i18n_explore_core.ancient_blessing_card_relic",
            card_name=ALL_CARDS[cid].name,
            relic_name=get_relic_name(rid),
        )
    else:
        bonus_str = get_locale_text("i18n_explore_core.ancient_blessing_relic", relic_name=get_relic_name(rid))
    return get_locale_text("i18n_explore_core.ancient_blessing", bonus=bonus_str)
