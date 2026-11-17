import random

from ...data.balance_config import (
    ELITE_BATTLE_GOLD_BASE,
    ELITE_BATTLE_GOLD_MAX,
    ELITE_BATTLE_GOLD_MIN,
    ELITE_POTION_CHANCE,
    NORMAL_BATTLE_GOLD_BASE,
    NORMAL_BATTLE_GOLD_MAX,
    NORMAL_BATTLE_GOLD_MIN,
    NORMAL_POTION_CHANCE,
    REWARD_CARD_COUNT,
)
from ...data.potion_data import roll_potion as _roll_potion
from ...data.reward_config import ELITE_RELIC_MAP
from ..inventory.card_distribution import CardDistributor


def base_enemy_name(name: str) -> str:
    parts = name.rsplit(" ", 1)
    if len(parts) == 2 and len(parts[1]) == 1 and parts[1].isalpha():
        return parts[0]
    return name


def roll_battle_gold(difficulty):
    if difficulty == "elite":
        return ELITE_BATTLE_GOLD_BASE + random.randint(ELITE_BATTLE_GOLD_MIN, ELITE_BATTLE_GOLD_MAX)
    return NORMAL_BATTLE_GOLD_BASE + random.randint(NORMAL_BATTLE_GOLD_MIN, NORMAL_BATTLE_GOLD_MAX)


def roll_potion(stats, difficulty):
    chance = ELITE_POTION_CHANCE if difficulty == "elite" else NORMAL_POTION_CHANCE
    if random.random() < chance:
        return _roll_potion(getattr(stats, "selected_class", "法师"))
    return None


def elite_relic_id(elite_name, player, exact=False):
    name = elite_name if exact else base_enemy_name(str(elite_name))
    rid = ELITE_RELIC_MAP.get(name, "")
    if rid and rid not in player.relics:
        return rid
    return ""


def _reward_card_item(run, player, stats, include_coop, difficulty="normal"):
    channel = CardDistributor.resolve_battle_channel(difficulty)
    final_cards = CardDistributor.roll(
        channel,
        run,
        player,
        stats,
        count=REWARD_CARD_COUNT,
        include_coop=include_coop,
    )
    return {"type": "card_reward", "cards": final_cards, "taken": False, "force": False}


def battle_gold_skipped(run):
    if int(run.node_data.get("banished_total", 0) or 0) <= 0:
        return False
    enemies = getattr(run, "enemies", None) or []
    return not any(enemy.hp > 0 for enemy in enemies)


def build_reward_items(save_manager, run, player, difficulty):
    coop = run.player_count() > 1
    stats = save_manager.load_stats(run.user_id)
    gold = roll_battle_gold(difficulty)
    if run.node_data.get("is_high_danger"):
        from ...data.grid_map_config import HIGH_DANGER_CONFIG
        gold += random.randint(HIGH_DANGER_CONFIG["bonus_gold_min"], HIGH_DANGER_CONFIG["bonus_gold_max"])
    skip_gold = battle_gold_skipped(run)
    relic_id = ""
    if not coop and difficulty == "elite":
        relic_id = elite_relic_id(str(run.node_data.get("elite_name", "")), player, exact=True)
    items = []
    if coop:
        if skip_gold:
            items.append({"type": "gold_skip", "taken": True})
        else:
            items.append({"type": "gold", "amount": gold, "taken": False})
        items.append(_reward_card_item(run, player, stats, True, difficulty))
        potion_id = roll_potion(stats, difficulty)
        if potion_id:
            items.append({"type": "potion", "potion_id": potion_id, "taken": False})
    else:
        if relic_id:
            items.append({"type": "relic", "relic_id": relic_id, "taken": False})
        if skip_gold:
            items.append({"type": "gold_skip", "taken": True})
        else:
            items.append({"type": "gold", "amount": gold, "taken": False})
        potion_id = roll_potion(stats, difficulty)
        if potion_id:
            items.append({"type": "potion", "potion_id": potion_id, "taken": False})
        items.append(_reward_card_item(run, player, stats, False, difficulty))
    return items
