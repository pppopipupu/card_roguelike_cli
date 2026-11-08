import re
from ..data.checkin_data import DAILY_BLESSINGS
from ..data.minion_data import MINION_CONFIG


CONDITION_PATTERN = re.compile(r"(若|如果|每当|当(?![前后做]))")


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
            match = re.match(r"^(且|并且|并)(.+)$", part)
            if match:
                prefix = match.group(1)
                body = match.group(2)
            result.append(f"{prefix}（{body}）")
        else:
            result.append(part)
    return "".join(result)


def _daily_effects(run):
    blessing_id = getattr(run.player, "daily_blessing_id", "") or run.node_data.get("daily_blessing_id", "")
    return DAILY_BLESSINGS.get(blessing_id, {}).get("effects", [])


def _card_damage_bonus(card, run) -> int:
    bonus = 0
    damage_type = getattr(card, "damage_type", "effect")
    physical = damage_type in ("slashing", "bludgeoning", "piercing")
    if physical:
        for buff in run.player.buffs:
            if buff.id == "strength":
                bonus += buff.stacks
    if damage_type == "spell":
        for buff in run.player.buffs:
            if buff.id == "arcane_charge":
                bonus += buff.stacks * 3
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


def _replace_damage_numbers(text: str, bonus: int) -> str:
    if bonus == 0:
        return text
    def repl(match):
        base = int(match.group(1))
        actual = base + bonus
        if actual == base:
            return match.group(0)
        return f"造成 {base}（{actual}）点"
    return re.sub(r"造成\s*(\d+)\s*点", repl, text)


def _cards_played_entry_description(card, run) -> str:
    card_id = getattr(card, "id", "").rstrip("+")
    cfg = MINION_CONFIG.get(card_id, {})
    thresholds = cfg.get("enter_hit_thresholds") or []
    damage = int(cfg.get("enter_damage", 0))
    if not thresholds or damage <= 0:
        return card.desc
    damage_name = cfg.get("enter_damage_name", "伤害")
    damage_type = cfg.get("enter_damage_type", "effect")
    count = run.node_data.get("cards_played_this_turn", 0)
    hits = sum(1 for threshold in thresholds if count >= threshold)
    damage_bonus = 0
    for effect in _daily_effects(run):
        if effect.get("type") == "damage_type_bonus" and effect.get("damage_type") == damage_type:
            damage_bonus += int(effect.get("value", 0))
    actual = damage + damage_bonus
    desc = card.desc
    if actual != damage:
        desc = desc.replace(f"{damage} 点", f"{damage}（{actual}）点")
    if hits:
        desc += f"（当前本回合已打出 {count} 张，进入战场将触发 {hits} 次{damage_name}伤害）"
    else:
        desc += f"（当前本回合已打出 {count} 张，尚未达到 {min(thresholds)} 张）"
    return desc


def render_card_description(card, run) -> str:
    card_id = getattr(card, "id", "").rstrip("+")
    cfg = MINION_CONFIG.get(card_id, {})
    if cfg.get("enter_hit_thresholds") and cfg.get("enter_damage"):
        text = _cards_played_entry_description(card, run)
    else:
        text = _replace_damage_numbers(card.desc, _card_damage_bonus(card, run))
    return highlight_conditions(text)
