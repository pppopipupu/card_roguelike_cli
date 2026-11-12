import re
from ..data.checkin_data import DAILY_BLESSINGS
from ..data.minion_data import MINION_CONFIG
from ..data.locale_data import get_locale_text
from ..data.buff_data import BUFF_CONFIG
from ..data.damage_type_data import is_physical_damage
from ..entities.cards.base import get_gem_numeric_modifiers, replace_structured_number


CONDITION_PATTERN = re.compile(r"(若|如果|每当|当(?![前后做]))")
PLACEHOLDER_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

CARD_TEMPLATE_ALIASES = {
    "dmg": "base_dmg",
    "damage": "base_dmg",
    "shield": "shield_amount",
    "heal": "heal_amount",
    "draw": "draw_count",
    "stacks": "buff_stacks",
    "turns": "buff_turns",
}


def highlight_conditions(text: str) -> str:
    parts = re.split(r"([，。；])", text)
    result = []
    for part in parts:
        if not part:
            continue
        if part in ("，", "。", "；"):
            result.append(part)
            continue
        if CONDITION_PATTERN.search(part) and "（" not in part and "）" not in part:
            prefix = ""
            body = part
            for candidate in ("并且", "并", "且"):
                if part.startswith(candidate) and len(part) > len(candidate):
                    prefix = candidate
                    body = part[len(candidate):]
                    break
            result.append(get_locale_text("i18n_card_runtime.preview.condition_wrapped", prefix=prefix, body=body))
        else:
            result.append(part)
    return "".join(result)


def _daily_effects(run):
    blessing_id = getattr(run.player, "daily_blessing_id", "") or run.node_data.get("daily_blessing_id", "")
    return DAILY_BLESSINGS.get(blessing_id, {}).get("effects", [])


def _int_value(card, *names) -> int:
    for name in names:
        value = getattr(card, name, None)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    return 0


def _card_damage_bonus(card, run) -> int:
    bonus = 0
    damage_type = getattr(card, "damage_type", "effect")
    physical = is_physical_damage(damage_type)
    card_id = getattr(card, "id", "")
    for marker in (":replay:", ":fragile:"):
        card_id = card_id.split(marker)[0]
    card_id = card_id.rstrip("+")
    if card_id.startswith("duel_"):
        card_id = card_id[5:]
    if physical:
        for buff in run.player.buffs:
            if buff.id == "strength":
                bonus += buff.stacks
    elif card_id == "neutral_astral_strike":
        strength_cfg = BUFF_CONFIG.get("strength", {})
        key = "astral_strike_upgraded_multiplier" if getattr(card, "upgraded", False) else "astral_strike_multiplier"
        multiplier = strength_cfg.get(key, strength_cfg.get("default_multiplier", 1))
        for buff in run.player.buffs:
            if buff.id == "strength":
                bonus += buff.stacks * multiplier
    if getattr(card, "type", "") == "spell":
        for buff in run.player.buffs:
            if buff.id == "arcane_charge":
                bonus += buff.stacks * BUFF_CONFIG.get("arcane_charge", {}).get("dmg_per_stack", 3)
    if damage_type == "fire":
        for buff in run.player.buffs:
            if buff.id == "fire_grow":
                bonus += buff.stacks
    if card.type == "spell":
        if "arcane_rune" in run.player.relics:
            bonus += 1
        if "mark_of_fury" in run.player.relics:
            bonus += 2
        if "unstable_crystal" in run.player.relics:
            bonus += 1
    for effect in _daily_effects(run):
        effect_type = effect.get("type")
        if effect_type == "damage_type_bonus" and effect.get("damage_type") == damage_type:
            bonus += int(effect.get("value", 0))
        elif effect_type == "card_name_bonus" and effect.get("keyword", "") in card.name:
            bonus += int(effect.get("value", 0))
    return bonus


def build_card_template_values(card, run) -> dict:
    gems = list(getattr(card, "gems", []) or [])
    modifiers = get_gem_numeric_modifiers(gems)
    base_dmg = _int_value(card, "base_dmg")
    pre_bonus_damage = (base_dmg + modifiers["dmg_add"]) * modifiers["dmg_mul"]
    damage_bonus = _card_damage_bonus(card, run) if run is not None else 0
    values = {
        "base_dmg": pre_bonus_damage + damage_bonus,
        "hit_count": _int_value(card, "hit_count", "hits"),
        "shield_amount": _int_value(card, "shield_amount") + modifiers["shield_add"],
        "heal_amount": _int_value(card, "heal_amount") + modifiers["heal_add"],
        "draw_count": _int_value(card, "draw_count"),
        "discard_count": _int_value(card, "discard_count"),
        "self_hp_cost": _int_value(card, "self_hp_cost", "hp_loss"),
        "gain_a": _int_value(card, "gain_a", "action_gain") + modifiers["gain_a"],
        "gain_ba": _int_value(card, "gain_ba", "bonus_action_gain") + modifiers["gain_ba"],
        "buff_stacks": _int_value(card, "buff_stacks"),
        "buff_turns": _int_value(card, "buff_turns"),
    }
    values["pre_bonus_damage"] = pre_bonus_damage
    return values


def render_description_template(text: str, values: dict) -> str:
    if not text or not PLACEHOLDER_PATTERN.search(text):
        return text

    def replace(match):
        key = match.group(1)
        if key in values:
            return str(values[key])
        alias = CARD_TEMPLATE_ALIASES.get(key)
        if alias and alias in values:
            return str(values[alias])
        return match.group(0)

    return PLACEHOLDER_PATTERN.sub(replace, text)


def _replace_damage_numbers(text: str, pre_bonus: int, final_damage: int) -> str:
    if pre_bonus <= 0 or final_damage == pre_bonus:
        return text
    return replace_structured_number(text, pre_bonus, get_locale_text("i18n_card_runtime.preview.annotated_number", pre=pre_bonus, final=final_damage), ("造成",), ("点",), True)


def _cards_played_entry_description(card, run, text) -> str:
    card_id = getattr(card, "id", "").rstrip("+")
    cfg = MINION_CONFIG.get(card_id, {})
    thresholds = cfg.get("enter_hit_thresholds") or []
    damage = int(cfg.get("enter_damage", 0))
    if not thresholds or damage <= 0:
        return text
    damage_name = cfg.get("enter_damage_name", get_locale_text("i18n_card_runtime.preview.default_damage_name"))
    damage_type = cfg.get("enter_damage_type", "effect")
    count = run.node_data.get(run.turn_key("cards_played_this_turn", run.player), 0)
    hits = sum(1 for threshold in thresholds if count >= threshold)
    damage_bonus = 0
    for effect in _daily_effects(run):
        if effect.get("type") == "damage_type_bonus" and effect.get("damage_type") == damage_type:
            damage_bonus += int(effect.get("value", 0))
    actual = damage + damage_bonus
    if actual != damage:
        text = replace_structured_number(text, damage, get_locale_text("i18n_card_runtime.preview.annotated_number", pre=damage, final=actual), ("造成",), ("点",))
    if hits:
        text += get_locale_text("i18n_card_runtime.preview.cards_played_hits", count=count, hits=hits, damage=damage_name)
    else:
        text += get_locale_text("i18n_card_runtime.preview.cards_played_pending", count=count, threshold=min(thresholds))
    return text


def render_card_description(card, run) -> str:
    card_id = getattr(card, "id", "").rstrip("+")
    cfg = MINION_CONFIG.get(card_id, {})
    values = build_card_template_values(card, run)
    has_placeholders = bool(PLACEHOLDER_PATTERN.search(card.desc))
    text = render_description_template(card.desc, values)
    if cfg.get("enter_hit_thresholds") and cfg.get("enter_damage"):
        text = _cards_played_entry_description(card, run, text)
    elif not has_placeholders:
        text = _replace_damage_numbers(text, values["pre_bonus_damage"], values["base_dmg"])
    return highlight_conditions(text)
