from ...data.grid_map_config import EXHAUSTION_CONFIG, SP_CONFIG
from ...data.locale_data import get_locale_text


def effective_max_hp_for_player(player, in_battle: bool = False) -> int:
    base = max(1, int(getattr(player, "max_hp", 1)))
    for b in getattr(player, "buffs", []) or []:
        if b.id == "iron_will":
            base += b.stacks * 10
        elif b.id == "iron_will+":
            base += b.stacks * 15
    if in_battle and getattr(player, "exhaustion", 0) >= 4:
        divisor = EXHAUSTION_CONFIG.get("level4_max_hp_divisor", 2)
        base = max(1, base // divisor)
    return base


def add_exhaustion(player, levels: int = 1) -> int:
    max_lvl = EXHAUSTION_CONFIG.get("max_level", 5)
    cur = int(getattr(player, "exhaustion", 0) or 0)
    nxt = min(max_lvl, cur + max(0, levels))
    player.exhaustion = nxt
    return nxt


def reduce_exhaustion(player, levels: int = 1) -> int:
    cur = int(getattr(player, "exhaustion", 0) or 0)
    nxt = max(0, cur - max(0, levels))
    player.exhaustion = nxt
    return nxt


def restore_sp(player, amount: int) -> int:
    if amount <= 0:
        return 0
    max_sp = int(getattr(player, "max_sp", SP_CONFIG["default_max_sp"]))
    cur = int(getattr(player, "sp", max_sp))
    nxt = min(max_sp, cur + amount)
    gained = max(0, nxt - cur)
    player.sp = nxt
    return gained


def consume_sp(player, amount: int, allow_overdraft: bool = True) -> dict:
    cur = int(getattr(player, "sp", 0) or 0)
    if cur >= amount:
        player.sp = cur - amount
        return {"paid": amount, "overdraft": False, "exhaustion_added": 0, "new_exhaustion": int(getattr(player, "exhaustion", 0) or 0)}
    if not allow_overdraft:
        return {"paid": 0, "overdraft": True, "exhaustion_added": 0, "new_exhaustion": int(getattr(player, "exhaustion", 0) or 0)}
    player.sp = 0
    new_ex = add_exhaustion(player, 1)
    return {"paid": cur, "overdraft": True, "exhaustion_added": 1, "new_exhaustion": new_ex}


def check_exhaustion_death(save_manager, run, player) -> tuple[bool, str]:
    max_lvl = EXHAUSTION_CONFIG.get("max_level", 5)
    if int(getattr(player, "exhaustion", 0) or 0) < max_lvl:
        return False, ""
    player.hp = 0
    run.node_data["death_cause"] = get_locale_text("i18n_grid_map.exhaustion_death_cause")
    uid = run.uid_for(player)
    msg = save_manager.settle_game_and_delete(uid, run, is_victory=False, create_corpse=True)
    return True, msg


def format_exhaustion_effects(exhaustion: int) -> str:
    lvl = max(0, int(exhaustion or 0))
    if lvl == 0:
        return get_locale_text("i18n_grid_map.exhaustion_desc_0")
    parts = []
    for i in range(1, min(lvl, 5) + 1):
        parts.append(get_locale_text(f"i18n_grid_map.exhaustion_desc_{i}"))
    return "；".join(parts)
