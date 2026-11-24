import re
from typing import Any, Optional, Tuple

from ...data.enemies.enemy_data import ENEMY_CONFIG
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.entities.enchantment_data import ENCHANTMENT_CONFIG
from ...data.entities.gem_data import GEM_CONFIG
from ...data.entities.mercenary_data import MERCENARY_CONFIG
from ...data.entities.minions.minion_data import MINION_CONFIG
from ...data.entities.potion_data import POTION_CONFIG, get_potion_name
from ...data.entities.relic_data import RELIC_CONFIG
from ...data.progression.achievement_data import ACHIEVEMENTS_CONFIG
from ...data.text.locale_data import get_locale_text
from ...data.world.grid_map_config import QUEST_RELIC_CONFIG
from ...data.world.room_interact_data import ROGUE_ITEMS, ROOM_NPCS, ROOM_PROPS
from ...entities.enemies.base import ALL_ENEMIES
from ...json_codec import loads
from ...models.state import GameRun
from ..cli.base.pinyin_match import find_entry_by_query
from ..inventory.enchantment_service import get_enchantment_name
from ..party.mercenary import resolve_mercenary_id

TRUE_ALIASES = frozenset({"true", "1", "on", "yes", "y", "enable", "enabled", "开", "开启", "是"})
FALSE_ALIASES = frozenset({"false", "0", "off", "no", "n", "disable", "disabled", "关", "关闭", "否"})
NULL_ALIASES = frozenset({"null", "none", "nil"})


def parse_bool(raw: str) -> Optional[bool]:
    low = str(raw or "").strip().lower()
    if low in TRUE_ALIASES:
        return True
    if low in FALSE_ALIASES:
        return False
    return None


def parse_flag_value(raw: str) -> Any:
    text = str(raw or "").strip()
    low = text.lower()
    if low in TRUE_ALIASES:
        return True
    if low in FALSE_ALIASES:
        return False
    if low in NULL_ALIASES:
        return None
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text)
    if re.fullmatch(r"[+-]?\d+\.\d+", text):
        return float(text)
    if (text.startswith("[") and text.endswith("]")) or (text.startswith("{") and text.endswith("}")):
        try:
            return loads(text)
        except Exception:
            return text
    if len(text) >= 2 and ((text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'")):
        return text[1:-1]
    return text


def resolve_target_user(save_manager, query: str, user_resolver=None) -> Optional[str]:
    q = str(query or "").strip()
    if not q:
        return None
    if callable(user_resolver):
        resolved = user_resolver(q)
        if resolved:
            return str(resolved)
    if save_manager.load_save(q) is not None:
        return q
    if hasattr(save_manager, "list_player_profiles"):
        profiles = save_manager.list_player_profiles()
        low = q.lower()
        prefix_matches: list[str] = []
        for prof in profiles:
            uid = str(getattr(prof, "user_id", "") or "")
            handle = str(getattr(prof, "handle", "") or "")
            name = str(getattr(prof, "player_name", "") or "")
            if q == uid or low == handle.lower() or low == name.lower():
                return uid
            if len(q) >= 4 and uid.lower().startswith(low):
                prefix_matches.append(uid)
        if len(prefix_matches) == 1:
            return prefix_matches[0]
        entries = []
        for prof in profiles:
            uid = str(getattr(prof, "user_id", "") or "")
            handle = str(getattr(prof, "handle", "") or "")
            name = str(getattr(prof, "player_name", "") or "")
            if handle:
                entries.append((uid, handle))
            if name:
                entries.append((uid, name))
        matched = find_entry_by_query(entries, q)
        if matched:
            return matched
    store = getattr(save_manager, "store", None)
    if store is not None and store.get_json("user_stats", q) is not None:
        return q
    return None


def resolve_buff(query: str) -> Optional[Tuple[str, str, str]]:
    raw = str(query or "").strip()
    if not raw:
        return None
    upgraded = False
    base_q = raw
    if base_q.endswith("+"):
        upgraded = True
        base_q = base_q[:-1]
    elif base_q.endswith("_upgraded"):
        upgraded = True
        base_q = base_q[: -len("_upgraded")]

    low = base_q.lower()
    if low in BUFF_CONFIG:
        cfg = BUFF_CONFIG[low]
        bid = f"{low}_upgraded" if upgraded else low
        name = cfg.get("name", low) + ("+" if upgraded else "")
        return bid, name, cfg.get("desc", "")

    for prefix in ("minor_vulnerable_", "vulnerable_", "resist_"):
        if low.startswith(prefix):
            return low, low, ""

    entries = []
    for bid, cfg in BUFF_CONFIG.items():
        entries.append((bid, bid))
        name = str(cfg.get("name", "") or "")
        if name:
            entries.append((bid, name))
    matched = find_entry_by_query(entries, base_q)
    if matched and matched in BUFF_CONFIG:
        cfg = BUFF_CONFIG[matched]
        bid = f"{matched}_upgraded" if upgraded else matched
        name = cfg.get("name", matched) + ("+" if upgraded else "")
        return bid, name, cfg.get("desc", "")
    return None


def resolve_enemy(query: str) -> Optional[str]:
    raw = str(query or "").strip()
    if not raw:
        return None
    if raw in ENEMY_CONFIG:
        return raw
    if raw in ALL_ENEMIES:
        return raw
    entries = []
    seen = set()
    for name in ENEMY_CONFIG:
        entries.append((name, name))
        seen.add(name)
    for name in ALL_ENEMIES:
        if name not in seen:
            entries.append((name, name))
    return find_entry_by_query(entries, raw)


def enemy_default_stats(name: str) -> Tuple[int, int, int]:
    cfg = ENEMY_CONFIG.get(name)
    if cfg:
        hp_match = re.match(r"^(\d+)", str(cfg.get("hp", "60")))
        actions_str = str(cfg.get("actions", "1A 1BA"))
        a_match = re.search(r"(\d+)A", actions_str)
        ba_match = re.search(r"(\d+)BA", actions_str)
        hp = int(hp_match.group(1)) if hp_match else 60
        actions = int(a_match.group(1)) if a_match else 1
        bonus = int(ba_match.group(1)) if ba_match else 0
        return max(1, hp), max(1, actions), max(0, bonus)
    return 60, 1, 1


def resolve_mercenary(query: str) -> Optional[str]:
    mid = resolve_mercenary_id(query)
    if mid:
        return mid
    entries = []
    for key, cfg in MERCENARY_CONFIG.items():
        entries.append((key, key))
        entries.append((key, cfg.get("name", key)))
        for alias in cfg.get("aliases", []):
            entries.append((key, alias))
    return find_entry_by_query(entries, query)


def resolve_minion(query: str) -> Optional[str]:
    raw = str(query or "").strip()
    if not raw:
        return None
    if raw in MINION_CONFIG:
        return raw
    entries = []
    for mid, cfg in MINION_CONFIG.items():
        entries.append((mid, mid))
        name = str(cfg.get("name", "") or "")
        if name:
            entries.append((mid, name))
    return find_entry_by_query(entries, raw)


def resolve_achievement(query: str) -> Optional[str]:
    raw = str(query or "").strip()
    if not raw:
        return None
    if raw in ACHIEVEMENTS_CONFIG:
        return raw
    entries = []
    for aid, cfg in ACHIEVEMENTS_CONFIG.items():
        entries.append((aid, aid))
        name = str(cfg.get("name", "") or "")
        if name:
            entries.append((aid, name))
    return find_entry_by_query(entries, raw)


def resolve_relic(query: str) -> Optional[str]:
    raw = str(query or "").strip()
    if not raw:
        return None
    if raw in RELIC_CONFIG:
        return raw
    entries = []
    for rid, cfg in RELIC_CONFIG.items():
        entries.append((rid, rid))
        name = str(cfg.get("name", "") or "")
        if name:
            entries.append((rid, name))
    return find_entry_by_query(entries, raw)


def resolve_item(query: str) -> Optional[Tuple[str, str, str]]:
    raw = str(query or "").strip()
    if not raw:
        return None
    if raw.startswith("potion:"):
        pid = raw.split(":", 1)[1]
        if pid in POTION_CONFIG:
            return raw, get_potion_name(pid), "bag"
    if raw in POTION_CONFIG:
        return f"potion:{raw}", get_potion_name(raw), "bag"
    if raw in ROGUE_ITEMS:
        return raw, get_locale_text(ROGUE_ITEMS[raw]["name_key"]), "bag"
    if raw in QUEST_RELIC_CONFIG:
        return raw, get_locale_text(QUEST_RELIC_CONFIG[raw]["name_key"]), "quest_relic"

    entries = []
    for pid in POTION_CONFIG:
        entries.append((f"potion:{pid}", pid))
        entries.append((f"potion:{pid}", get_potion_name(pid)))
    for iid, cfg in ROGUE_ITEMS.items():
        entries.append((iid, iid))
        entries.append((iid, get_locale_text(cfg["name_key"])))
        for alias in cfg.get("aliases", []):
            entries.append((iid, alias))
    for qid, cfg in QUEST_RELIC_CONFIG.items():
        entries.append((f"quest_relic:{qid}", qid))
        entries.append((f"quest_relic:{qid}", get_locale_text(cfg["name_key"])))

    matched = find_entry_by_query(entries, raw)
    if not matched:
        return None
    if matched.startswith("quest_relic:"):
        qid = matched.split(":", 1)[1]
        return qid, get_locale_text(QUEST_RELIC_CONFIG[qid]["name_key"]), "quest_relic"
    if matched.startswith("potion:"):
        pid = matched.split(":", 1)[1]
        return matched, get_potion_name(pid), "bag"
    return matched, get_locale_text(ROGUE_ITEMS[matched]["name_key"]), "bag"


def resolve_gem(query: str) -> Optional[str]:
    raw = str(query or "").strip()
    if not raw:
        return None
    if raw in GEM_CONFIG:
        return raw
    entries = []
    for gid, cfg in GEM_CONFIG.items():
        entries.append((gid, gid))
        entries.append((gid, str(cfg.get("name", "") or "")))
    return find_entry_by_query(entries, raw)


def resolve_enchantment(query: str) -> Optional[str]:
    raw = str(query or "").strip()
    if not raw:
        return None
    if raw in ENCHANTMENT_CONFIG:
        return raw
    entries = []
    for eid in ENCHANTMENT_CONFIG:
        entries.append((eid, eid))
        entries.append((eid, get_enchantment_name(eid)))
    return find_entry_by_query(entries, raw)


def resolve_npc(query: str) -> Optional[str]:
    raw = str(query or "").strip()
    if not raw:
        return None
    if raw in ROOM_NPCS:
        return raw
    entries = []
    for nid, cfg in ROOM_NPCS.items():
        entries.append((nid, nid))
        name_key = cfg.get("name_key", "")
        if name_key:
            entries.append((nid, get_locale_text(name_key)))
        for alias in cfg.get("aliases", []):
            entries.append((nid, alias))
    return find_entry_by_query(entries, raw)


def resolve_prop(query: str) -> Optional[str]:
    raw = str(query or "").strip()
    if not raw:
        return None
    if raw in ROOM_PROPS:
        return raw
    entries = []
    for pid, cfg in ROOM_PROPS.items():
        entries.append((pid, pid))
        name_key = cfg.get("name_key", "")
        if name_key:
            entries.append((pid, get_locale_text(name_key)))
        for alias in cfg.get("aliases", []):
            entries.append((pid, alias))
    return find_entry_by_query(entries, raw)


def resolve_battle_entities(run: GameRun, target_token: str) -> list[Tuple[str, Any]]:
    tok = str(target_token or "p0").strip().lower()
    if tok in ("p", "p0", "self", "player"):
        return [(run.player.name, run.player)]
    if tok in ("all_e", "enemies", "all_enemies"):
        return [(f"e{i} {e.name}", e) for i, e in enumerate(run.enemies, 1) if e.hp > 0]
    if tok in ("all_a", "allies", "party"):
        out = []
        for idx, uid in enumerate(run.party_order, 1):
            pl = run.players.get(uid)
            if pl is not None:
                out.append((f"a{idx} {pl.name}", pl))
        return out
    m_enemy = re.fullmatch(r"e(\d+)", tok)
    if m_enemy:
        idx = int(m_enemy.group(1)) - 1
        if 0 <= idx < len(run.enemies):
            e = run.enemies[idx]
            return [(f"e{idx + 1} {e.name}", e)]
        return []
    m_ally = re.fullmatch(r"a(\d+)", tok)
    if m_ally:
        idx = int(m_ally.group(1)) - 1
        if 0 <= idx < len(run.party_order):
            uid = run.party_order[idx]
            pl = run.players.get(uid)
            if pl is not None:
                return [(f"a{idx + 1} {pl.name}", pl)]
        return []
    m_minion = re.fullmatch(r"[pm](\d+)", tok)
    if m_minion:
        slot = m_minion.group(1)
        minion = run.player.minions.get(slot)
        if minion is not None:
            return [(f"m{slot} {minion.name}", minion)]
        return []
    return []
