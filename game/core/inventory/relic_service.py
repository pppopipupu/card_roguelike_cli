from ...data.relic_data import RELIC_CONFIG
from ...data.room_interact_data import BAG_DEFAULT_MAX_WEIGHT


def init_relic_counter_map(counters: dict, relic_id: str) -> None:
    cfg = RELIC_CONFIG.get(relic_id, {})
    if "counter_init" not in cfg:
        return
    counters.setdefault(relic_id, int(cfg["counter_init"]))


def init_relic_counter(player, relic_id: str) -> None:
    if player is None:
        return
    cfg = RELIC_CONFIG.get(relic_id, {})
    if "counter_init" not in cfg:
        return
    counters = getattr(player, "relic_counters", None)
    if not isinstance(counters, dict):
        counters = {}
        player.relic_counters = counters
    init_relic_counter_map(counters, relic_id)


def grant_relic(player, relic_id: str) -> bool:
    if player is None or not relic_id:
        return False
    if relic_id not in player.relics:
        player.relics.append(relic_id)
        init_relic_counter(player, relic_id)
        weight_bonus = int(RELIC_CONFIG.get(relic_id, {}).get("bag_weight_bonus", 0) or 0)
        if weight_bonus > 0:
            current_max = int(getattr(player, "bag_max_weight", BAG_DEFAULT_MAX_WEIGHT) or BAG_DEFAULT_MAX_WEIGHT)
            player.bag_max_weight = max(BAG_DEFAULT_MAX_WEIGHT, current_max) + weight_bonus
        return True
    init_relic_counter(player, relic_id)
    return False


def get_relic_counter(player, relic_id: str) -> int:
    cfg = RELIC_CONFIG.get(relic_id, {})
    default_val = int(cfg.get("counter_init", 0))
    if player is None:
        return default_val
    counters = getattr(player, "relic_counters", None)
    if not isinstance(counters, dict):
        return default_val
    if relic_id not in counters:
        return default_val
    return int(counters[relic_id])


def set_relic_counter(player, relic_id: str, value: int) -> None:
    if player is None:
        return
    counters = getattr(player, "relic_counters", None)
    if not isinstance(counters, dict):
        counters = {}
        player.relic_counters = counters
    counters[relic_id] = int(value)
