import random

from ...data.ancient_node_config import (
    ANCIENT_BLESSING_POOLS,
    ANCIENT_ICERAINBOWW_LEGEND,
    ANCIENT_LEGEND_APPENDS,
    ANCIENT_REWARD_OPTION_TYPE,
    ANCIENT_STYLE_CHOICES,
)
from ...data.balance_config import MAP_ANCIENT_OPTION_SLOTS
from ...data.locale_data import get_locale_text
from ...entities import ALL_CARDS, get_relic_name
from ...models.state import check_and_replace_fireball, ensure_card_state
from ..inventory.relic_service import grant_relic


def build_ancient_options(run, save_manager) -> dict:
    p = run.player
    stats = save_manager.load_stats(run.user_id) if hasattr(save_manager, "load_stats") else None
    p_class = getattr(stats, "selected_class", "法师")
    admin_cfg = save_manager.load_admin_config() if hasattr(save_manager, "load_admin_config") else {}
    icerainboww_enabled = admin_cfg.get("icerainboww_enabled", True)
    pool_key = "战士" if p_class == "战士" else "default"
    style = random.choice(ANCIENT_STYLE_CHOICES[pool_key])
    style_pools = ANCIENT_BLESSING_POOLS[pool_key][style]
    legends_pool = list(style_pools["legends"]) + list(ANCIENT_LEGEND_APPENDS)
    if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
        legends_pool.append(ANCIENT_ICERAINBOWW_LEGEND)
    available_relics = [r for r in style_pools["relics"] if r not in p.relics]
    if not available_relics:
        available_relics = list(style_pools["relics"])
    random.shuffle(legends_pool)
    random.shuffle(available_relics)
    options = [
        {
            "type": ANCIENT_REWARD_OPTION_TYPE,
            "card": check_and_replace_fireball(run, legends_pool[i % len(legends_pool)]),
            "relic": available_relics[i % len(available_relics)],
        }
        for i in range(MAP_ANCIENT_OPTION_SLOTS)
    ]
    return {"options": options, "style": style}


def grant_ancient_blessing(run, chosen, player=None) -> str:
    p = player if player is not None else run.player
    rid = chosen["relic"]
    cid = chosen.get("card")
    grant_relic(p, rid)
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
