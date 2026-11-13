from typing import Iterable, Optional
from ...data.buff_data import BUFF_CONFIG
from ...data.grid_map_config import EXHAUSTION_CONFIG
from ...data.locale_data import get_locale_text
from ...models.state import BuffState


def _exhaustion_desc(level: int) -> str:
    lvl = max(0, int(level or 0))
    if lvl <= 0:
        return get_locale_text("i18n_grid_map.exhaustion_desc_0")
    parts = []
    for i in range(1, min(lvl, 5) + 1):
        parts.append(get_locale_text(f"i18n_grid_map.exhaustion_desc_{i}"))
    return "；".join(parts)


def get_persistent_buff(player, buff_id: str) -> Optional[BuffState]:
    for b in getattr(player, "persistent_buffs", None) or []:
        if b.id == buff_id:
            return b
    return None


def get_persistent_buff_stacks(player, buff_id: str) -> int:
    b = get_persistent_buff(player, buff_id)
    return int(b.stacks) if b is not None else 0


def set_persistent_buff(
    player,
    buff_id: str,
    stacks: int,
    name: Optional[str] = None,
    desc: Optional[str] = None,
) -> Optional[BuffState]:
    pbuffs = getattr(player, "persistent_buffs", None)
    if pbuffs is None:
        pbuffs = []
        player.persistent_buffs = pbuffs
    val = int(stacks or 0)
    if buff_id == "exhaustion":
        val = min(int(EXHAUSTION_CONFIG.get("max_level", 5)), max(0, val))
    existing = get_persistent_buff(player, buff_id)
    if val <= 0:
        if existing is not None:
            pbuffs.remove(existing)
        return None
    cfg = BUFF_CONFIG.get(buff_id, {})
    b_name = name or cfg.get("name", buff_id)
    if desc is not None:
        b_desc = desc
    elif buff_id == "exhaustion":
        b_desc = _exhaustion_desc(val)
    else:
        b_desc = cfg.get("desc", "")
    if existing is not None:
        existing.stacks = val
        existing.name = b_name
        existing.desc = b_desc
        existing.persistent = True
        return existing
    entry = BuffState(id=buff_id, name=b_name, stacks=val, desc=b_desc, persistent=True)
    pbuffs.append(entry)
    return entry


def add_persistent_buff(
    player,
    buff_id: str,
    stacks: int = 1,
    name: Optional[str] = None,
    desc: Optional[str] = None,
) -> Optional[BuffState]:
    cur = get_persistent_buff_stacks(player, buff_id)
    return set_persistent_buff(player, buff_id, cur + max(0, int(stacks)), name=name, desc=desc)


def remove_persistent_buff(player, buff_id: str, stacks: Optional[int] = None) -> int:
    existing = get_persistent_buff(player, buff_id)
    if existing is None:
        return 0
    if stacks is None:
        player.persistent_buffs.remove(existing)
        return 0
    nxt = max(0, int(existing.stacks) - max(0, int(stacks)))
    set_persistent_buff(player, buff_id, nxt)
    return nxt


def cure_persistent_debuffs(
    player,
    stacks: int = 1,
    exclude_ids: Iterable[str] = ("exhaustion",),
) -> list[str]:
    cured = []
    excluded = set(exclude_ids or ())
    for b in list(getattr(player, "persistent_buffs", None) or []):
        if b.id in excluded:
            continue
        cfg = BUFF_CONFIG.get(b.id, {})
        if cfg.get("is_debuff"):
            bname = b.name
            remove_persistent_buff(player, b.id, stacks)
            cured.append(bname)
    return cured


def sync_persistent_buffs_to_battle(player) -> None:
    pbuffs = getattr(player, "persistent_buffs", None) or []
    for pb in pbuffs:
        if pb.stacks <= 0:
            continue
        existing = next((b for b in player.buffs if b.id == pb.id), None)
        if existing is not None:
            existing.stacks = pb.stacks
            existing.stacks2 = pb.stacks2
            existing.desc = pb.desc
            existing.persistent = True
        else:
            player.buffs.append(
                BuffState(
                    id=pb.id,
                    name=pb.name,
                    stacks=pb.stacks,
                    stacks2=pb.stacks2,
                    desc=pb.desc,
                    source_uid=pb.source_uid,
                    persistent=True,
                )
            )


def consume_persistent_buff_in_battle(player, buff_id: str, stacks: int = 1) -> int:
    remaining = remove_persistent_buff(player, buff_id, stacks)
    b_entry = next((b for b in getattr(player, "buffs", []) if b.id == buff_id), None)
    if b_entry is not None:
        if remaining <= 0:
            player.buffs.remove(b_entry)
        else:
            b_entry.stacks = remaining
    return remaining
