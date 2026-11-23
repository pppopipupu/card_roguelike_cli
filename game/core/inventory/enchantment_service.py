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


_FLAG_EFFECT_KEYS: tuple[str, ...] = (
    "only_attacks_in_hand",
    "only_skills_in_hand",
    "purify_hand",
    "reshuffle_to_draw",
    "pierce_shield",
    "grave",
    "extra_hits_per_enemy",
    "mantra_by_cost",
    "double_dmg_lowest_hp",
    "must_play_first",
    "duplicate_on_draw",
    "enter_wrath",
    "discard_first_draw",
    "randomize_cost_on_draw",
    "next_attack_free",
    "exhaust_on_hp_loss",
    "block_equal_unblocked_dmg",
    "die_next_turn",
    "infinite_copy_each_turn",
    "invert_dmg_shield",
    "jank_swap_nums",
    "poison_equal_unblocked_dmg",
    "multi_upgrade",
    "only_attack_in_hand",
    "x_cost_repeat",
    "autoplay_on_draw",
    "make_playable",
)

_COUNT_EFFECT_KEYS: tuple[str, ...] = (
    "bonus_shield",
    "bonus_heal",
    "self_hp_loss",
    "draw",
    "discard_random",
    "next_turn_a",
    "next_turn_draw",
    "gain_strength",
    "gain_temp_strength",
    "self_weak",
    "self_vuln",
    "enemy_strength",
    "add_curse_draw",
    "apply_vuln",
    "apply_weak",
    "apply_poison",
    "apply_poison_all",
    "aoe_dmg",
    "copy_to_discard",
    "kill_gold",
    "low_hp_dmg_pct",
    "enemy_debuff_dmg",
    "self_debuff_shield",
    "channel_lightning",
    "gain_a_if_prev_attack",
    "channel_frost",
    "exhaust_random_hand",
    "grant_miracle_a",
    "scry_before_draw",
    "next_turn_shield",
    "self_frail",
    "play_cost_reduce",
    "upgrade_random_hand",
    "ramp_shield",
    "claw_scale",
    "curse_deck_dmg",
    "random_extra_hit",
    "channel_dark",
    "bonus_vs_attacking_dmg",
    "strength_mult",
    "apply_lock_on",
    "on_exhaust_draw",
    "ramp_dmg",
    "add_base_copies_hand",
    "delayed_burst_turns",
    "return_zero_cost_from_discard",
    "channel_plasma",
    "kill_perm_dmg",
    "obscure_intents_turns",
    "draw_if_prev_skill",
    "gain_intangible",
    "draw_gain_a",
    "draw_lose_a",
)

_FLAG_ATTR_KEYS: tuple[str, ...] = ("exhaust", "ethereal", "innate", "retain", "cant_upgrade")


def _compose_enchantment_effect_desc(card, folded: list[tuple[str, int]], before: dict[str, bool]) -> str:
    if not folded:
        return ""
    parts: list[str] = []
    for key in _FLAG_EFFECT_KEYS:
        if any(ENCHANTMENT_CONFIG[eid].get(key) for eid, _ in folded):
            parts.append(get_locale_text(f"i18n_enchantment.dyn.{key}"))
    for key in _COUNT_EFFECT_KEYS:
        total = sum(int(ENCHANTMENT_CONFIG[eid].get(key, 0)) * cnt for eid, cnt in folded)
        if total > 0:
            parts.append(get_locale_text(f"i18n_enchantment.dyn.{key}", n=total))
    if any(ENCHANTMENT_CONFIG[eid].get("add_card_hand") for eid, _ in folded):
        parts.append(get_locale_text("i18n_enchantment.dyn.add_card_hand"))
    for eid, _ in folded:
        nxt = ENCHANTMENT_CONFIG[eid].get("shuffle_transformed_enchant")
        if nxt in ("beta", "omega"):
            parts.append(get_locale_text(f"i18n_enchantment.dyn.shuffle_transformed_enchant_{nxt}"))
    for key in _FLAG_ATTR_KEYS:
        if getattr(card, key, False) and not before[key]:
            parts.append(get_locale_text(f"i18n_enchantment.dyn.{key}"))
    if not parts:
        return ""
    prefix = get_locale_text("i18n_enchantment.dyn.prefix")
    sep = get_locale_text("i18n_enchantment.dyn.sep")
    period = get_locale_text("i18n_card_runtime.cards.sentence_period")
    return f"{prefix}{sep.join(parts)}{period}"


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


def has_multi_upgrade_enchantment(card_state) -> bool:
    st = ensure_card_state(card_state)
    for eid in st.enchantments or ():
        if ENCHANTMENT_CONFIG.get(eid, {}).get("multi_upgrade"):
            return True
    return False


def roll_enchantments(count: int, pool: tuple[str, ...] | None = None) -> list[str]:
    if pool is not None:
        candidates = [eid for eid in pool if eid in ENCHANTMENT_CONFIG]
    else:
        candidates = [eid for eid, cfg in ENCHANTMENT_CONFIG.items() if not cfg.get("pool_exclude")]
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

    before: dict[str, bool] = {
        "exhaust": bool(getattr(card, "exhaust", False)),
        "ethereal": bool(getattr(card, "ethereal", False)),
        "innate": bool(getattr(card, "innate", False)),
        "retain": bool(getattr(card, "retain", False)),
        "cant_upgrade": bool(getattr(card, "cant_upgrade", False)),
    }

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

    set_cost_a = None
    for eid, _ in folded:
        cfg = ENCHANTMENT_CONFIG[eid]
        if "set_cost_a" in cfg:
            set_cost_a = int(cfg["set_cost_a"])
        if cfg.get("make_playable"):
            card.unplayable = False
        if cfg.get("invert_dmg_shield"):
            d0 = int(getattr(card, "base_dmg", 0) or 0)
            s0 = int(getattr(card, "shield_amount", 0) or 0)
            if d0 > 0 or s0 > 0:
                card.base_dmg = s0
                card.shield_amount = d0
        if cfg.get("jank_swap_nums"):
            d0 = int(getattr(card, "base_dmg", 0) or 0)
            s0 = int(getattr(card, "shield_amount", 0) or 0)
            h0 = int(getattr(card, "heal_amount", 0) or 0)
            vals = [v for v in (d0, s0, h0) if v > 0]
            if len(vals) >= 2:
                rot = vals[1:] + vals[:1]
                it = iter(rot)
                if d0 > 0:
                    card.base_dmg = next(it)
                if s0 > 0:
                    card.shield_amount = next(it)
                if h0 > 0:
                    card.heal_amount = next(it)
    if set_cost_a is not None:
        card.cost_a = set_cost_a
    elif cost_a_delta != 0:
        card.cost_a = max(0, int(card.cost_a) + cost_a_delta)
    if cost_ba_delta != 0:
        card.cost_ba = max(0, int(card.cost_ba) + cost_ba_delta)

    from ...entities.cards.base import (
        append_card_suffix,
        get_gem_numeric_modifiers,
        replace_structured_number,
    )
    gem_mods = get_gem_numeric_modifiers(getattr(card, "gems", None) or [])

    base_dmg = int(getattr(card, "base_dmg", 0) or 0)
    if base_dmg > 0 and (dmg_pct != 0 or dmg_add != 0):
        new_base_dmg = max(1, int(round((base_dmg + dmg_add) * max(0.1, 1.0 + dmg_pct / 100.0))))
        card.base_dmg = new_base_dmg
        old_shown = (base_dmg + gem_mods["dmg_add"]) * gem_mods["dmg_mul"]
        new_shown = (new_base_dmg + gem_mods["dmg_add"]) * gem_mods["dmg_mul"]
        if new_shown != old_shown:
            card.desc = replace_structured_number(card.desc, old_shown, new_shown, ("造成",), ("点",))

    base_shield = int(getattr(card, "shield_amount", 0) or 0)
    if base_shield > 0 and shield_pct != 0:
        new_base_shield = max(1, int(round(base_shield * max(0.1, 1.0 + shield_pct / 100.0))))
        card.shield_amount = new_base_shield
        old_shown = base_shield + gem_mods["shield_add"]
        new_shown = new_base_shield + gem_mods["shield_add"]
        if new_shown != old_shown:
            card.desc = replace_structured_number(card.desc, old_shown, new_shown, ("获得", "提供", "产生"), ("点护盾",))

    base_heal = int(getattr(card, "heal_amount", 0) or 0)
    if base_heal > 0 and heal_pct != 0:
        new_base_heal = max(1, int(round(base_heal * max(0.1, 1.0 + heal_pct / 100.0))))
        card.heal_amount = new_base_heal
        old_shown = base_heal + gem_mods["heal_add"]
        new_shown = new_base_heal + gem_mods["heal_add"]
        if new_shown != old_shown:
            card.desc = replace_structured_number(card.desc, old_shown, new_shown, ("回复", "治疗", "恢复"), ("点生命",))

    gem_inlay_marker = get_locale_text("i18n_card_runtime.cards.gem_inlay", gems="__SPLIT__").split("__SPLIT__")[0]
    inlay_tail = ""
    body_desc = card.desc
    if gem_inlay_marker and gem_inlay_marker in body_desc:
        split_idx = body_desc.index(gem_inlay_marker)
        inlay_tail = body_desc[split_idx:]
        body_desc = body_desc[:split_idx]

    effect_desc = _compose_enchantment_effect_desc(card, folded, before)
    if effect_desc:
        body_desc = append_card_suffix(body_desc, effect_desc)

    card.desc = f"{body_desc}{inlay_tail}"
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
