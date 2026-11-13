from ...data.relic_data import RELIC_CONFIG


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
    counters.setdefault(relic_id, int(cfg["counter_init"]))


def grant_relic(player, relic_id: str) -> bool:
    if player is None or not relic_id:
        return False
    if relic_id not in player.relics:
        player.relics.append(relic_id)
        init_relic_counter(player, relic_id)
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
