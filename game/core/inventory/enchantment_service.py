import random
from ...data.entities.enchantment_data import (
    ENCHANTMENT_CONFIG,
    ENCHANTMENT_RARITY_WEIGHTS,
    START_ENCHANT_CHANCE,
    START_ENCHANT_MAX_CARDS,
    START_ENCHANT_MIN_CARDS,
    START_ENCHANT_POOL,
)
from ...data.text.locale_data import get_locale_text
from ...models.state import CardState, ensure_card_state


def get_enchantment_name(eid: str) -> str:
    return get_locale_text(f"i18n_enchantment.names.{eid}")


def get_enchantment_desc(eid: str) -> str:
    return get_locale_text(f"i18n_enchantment.descs.{eid}")


def get_enchantment_rarity_label(eid: str) -> str:
    rarity = str(ENCHANTMENT_CONFIG.get(eid, {}).get("rarity", "common"))
    return get_locale_text(f"i18n_enchantment.rarities.{rarity}")


def fold_enchantments(enchantments: list[str] | tuple[str, ...] | None) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    order: list[str] = []
    for eid in enchantments or ():
        if eid not in ENCHANTMENT_CONFIG:
            continue
        if eid not in counts:
            order.append(eid)
            counts[eid] = 1
        else:
            counts[eid] += 1
    return [(eid, counts[eid]) for eid in order]


def format_enchantment_tags(enchantments: list[str] | tuple[str, ...] | None) -> str:
    folded = fold_enchantments(enchantments)
    if not folded:
        return ""
    sep = get_locale_text("i18n_enchantment.ui.tag_sep")
    parts = []
    for eid, cnt in folded:
        name = get_enchantment_name(eid)
        parts.append(f"{name}x{cnt}" if cnt > 1 else name)
    return sep.join(parts)


def is_card_enchantable(card_state) -> bool:
    from ...entities.cards.base import ALL_CARDS
    st = ensure_card_state(card_state)
    card = ALL_CARDS.get(st.id)
    if card is None:
        return False
    if getattr(card, "color", "") == "curse":
        return False
    if getattr(card, "unplayable", False) or getattr(card, "token", False):
        return False
    return True


def has_cant_upgrade_enchantment(card_state) -> bool:
    st = ensure_card_state(card_state)
    for eid in st.enchantments or ():
        if ENCHANTMENT_CONFIG.get(eid, {}).get("cant_upgrade"):
            return True
    return False


def roll_enchantments(count: int, pool: tuple[str, ...] | None = None) -> list[str]:
    candidates = [eid for eid in (pool if pool is not None else tuple(ENCHANTMENT_CONFIG.keys())) if eid in ENCHANTMENT_CONFIG]
    if not candidates or count <= 0:
        return []
    picked: list[str] = []
    remaining = list(candidates)
    for _ in range(min(count, len(remaining))):
        weights = [
            int(ENCHANTMENT_RARITY_WEIGHTS.get(str(ENCHANTMENT_CONFIG[eid].get("rarity", "common")), 10))
            for eid in remaining
        ]
        chosen = random.choices(remaining, weights=weights, k=1)[0]
        picked.append(chosen)
        remaining.remove(chosen)
    return picked


def _compose_enchanted_name(base_name: str, folded: list[tuple[str, int]]) -> str:
    upgraded_plus = base_name.endswith("+")
    core = base_name[:-1] if upgraded_plus else base_name
    prefixes: list[str] = []
    suffixes: list[str] = []
    for eid, _ in folded:
        cfg = ENCHANTMENT_CONFIG.get(eid, {})
        mode = cfg.get("name_mode", "none")
        if mode == "prefix":
            affix = get_locale_text(f"i18n_enchantment.affixes.{eid}")
            if affix and affix not in prefixes:
                prefixes.append(affix)
        elif mode == "suffix":
            affix = get_locale_text(f"i18n_enchantment.affixes.{eid}")
            if affix and affix not in suffixes:
                suffixes.append(affix)
    new_core = f"{''.join(prefixes)}{core}{''.join(suffixes)}"
    return f"{new_core}+" if upgraded_plus else new_core


def apply_enchantments_to_card(card, card_state: CardState) -> int:
    enchants = list(getattr(card_state, "enchantments", None) or [])
    card.enchantments = enchants
    folded = fold_enchantments(enchants)
    if not folded:
        return 0

    card.name = _compose_enchanted_name(card.name, folded)

    cost_a_delta = 0
    cost_ba_delta = 0
    replay_bonus = 0
    dmg_pct = 0
    shield_pct = 0
    heal_pct = 0
    dmg_add = 0

    for eid, cnt in folded:
        cfg = ENCHANTMENT_CONFIG[eid]
        cost_a_delta += int(cfg.get("cost_a_delta", 0)) * cnt
        cost_ba_delta += int(cfg.get("cost_ba_delta", 0)) * cnt
        replay_bonus += int(cfg.get("replay_add", 0)) * cnt
        all_pct = int(cfg.get("all_num_pct", 0)) * cnt
        dmg_pct += int(cfg.get("dmg_pct", 0)) * cnt + all_pct
        shield_pct += int(cfg.get("shield_pct", 0)) * cnt + all_pct
        heal_pct += int(cfg.get("heal_pct", 0)) * cnt + all_pct
        dmg_add += int(cfg.get("dmg_add", 0)) * cnt
        if cfg.get("innate"):
            card.innate = True
        if cfg.get("retain"):
            card.retain = True
        if cfg.get("exhaust"):
            card.exhaust = True
        if cfg.get("ethereal"):
            card.ethereal = True
        if cfg.get("cant_upgrade"):
            card.cant_upgrade = True

    if cost_a_delta != 0:
        card.cost_a = max(0, int(card.cost_a) + cost_a_delta)
    if cost_ba_delta != 0:
        card.cost_ba = max(0, int(card.cost_ba) + cost_ba_delta)

    base_dmg = int(getattr(card, "base_dmg", 0) or 0)
    if base_dmg > 0 and (dmg_pct != 0 or dmg_add != 0):
        card.base_dmg = max(1, int(round((base_dmg + dmg_add) * max(0.1, 1.0 + dmg_pct / 100.0))))

    base_shield = int(getattr(card, "shield_amount", 0) or 0)
    if base_shield > 0 and shield_pct != 0:
        card.shield_amount = max(1, int(round(base_shield * max(0.1, 1.0 + shield_pct / 100.0))))

    base_heal = int(getattr(card, "heal_amount", 0) or 0)
    if base_heal > 0 and heal_pct != 0:
        card.heal_amount = max(1, int(round(base_heal * max(0.1, 1.0 + heal_pct / 100.0))))

    tags_str = format_enchantment_tags(enchants)
    if tags_str:
        card.desc = card.desc + get_locale_text("i18n_enchantment.ui.card_tag_prefix", tags=tags_str)
    return replay_bonus


def apply_starting_enchantments(deck: list[CardState]) -> list[tuple[CardState, str]]:
    if not deck:
        return []
    state = random.getstate()
    rng = random.Random(hash((state[1][0], state[1][1], state[1][-1], len(deck), tuple(c.id for c in deck))))
    if rng.random() >= START_ENCHANT_CHANCE:
        return []
    eligible = [c for c in deck if is_card_enchantable(c)]
    if not eligible:
        return []
    count = rng.randint(START_ENCHANT_MIN_CARDS, min(START_ENCHANT_MAX_CARDS, len(eligible)))
    chosen_cards = rng.sample(eligible, count)
    pool = [eid for eid in START_ENCHANT_POOL if eid in ENCHANTMENT_CONFIG]
    weights = [int(ENCHANTMENT_RARITY_WEIGHTS.get(str(ENCHANTMENT_CONFIG[eid].get("rarity", "common")), 10)) for eid in pool]
    results: list[tuple[CardState, str]] = []
    for c_state in chosen_cards:
        if not pool:
            continue
        eid = rng.choices(pool, weights=weights, k=1)[0]
        c_state.enchantments = list(c_state.enchantments or []) + [eid]
        results.append((c_state, eid))
    return results


def preview_enchant_card(card_state: CardState, enchantment_id: str) -> dict:
    from ...entities.cards.base import ALL_CARDS
    from ...renderer.menu import get_card_cost_str
    from .deck_service import DeckService
    before_state = DeckService.clone_state(card_state)
    after_state = DeckService.clone_state(card_state)
    after_state.enchantments = list(after_state.enchantments or []) + [enchantment_id]
    before_card = ALL_CARDS[before_state]
    after_card = ALL_CARDS[after_state]
    return {
        "before_name": before_card.name,
        "after_name": after_card.name,
        "before_cost": get_card_cost_str(before_card),
        "after_cost": get_card_cost_str(after_card),
        "before_desc": before_card.desc,
        "after_desc": after_card.desc,
        "name_changed": before_card.name != after_card.name,
    }
