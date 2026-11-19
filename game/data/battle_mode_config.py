BATTLE_MODE_SOLO = "solo"
BATTLE_MODE_TEAM = "team"
BATTLE_MODE_FORCED_SOLO = "forced_solo"

TEAM_BATTLE_ROOM_TYPES = frozenset({"boss", "secret_boss"})
TEAM_BATTLE_DIFFICULTIES = frozenset({"boss", "secret_boss"})
FORCED_SOLO_BATTLE_ROOM_TYPES = frozenset({"event"})
FORCED_SOLO_BATTLE_DIFFICULTIES = frozenset({"npc_combat"})


def resolve_battle_mode(room_type: str, difficulty: str = "") -> str:
    if room_type in TEAM_BATTLE_ROOM_TYPES or difficulty in TEAM_BATTLE_DIFFICULTIES:
        return BATTLE_MODE_TEAM
    if room_type in FORCED_SOLO_BATTLE_ROOM_TYPES or difficulty in FORCED_SOLO_BATTLE_DIFFICULTIES:
        return BATTLE_MODE_FORCED_SOLO
    return BATTLE_MODE_SOLO


def session_battle_mode(node_data: dict | None) -> str:
    mode = str((node_data or {}).get("battle_mode") or "")
    return mode or BATTLE_MODE_SOLO
