from typing import Dict

from ....data.world.yog_quest_config import YOG_BOSS_HP_MODIFIERS, YOG_ENCOUNTERS, YOG_MAPS
from ....models.state import EnemyState, FloorMapState, GameRun, RoomState
from ..grid_map_generator import xy_to_coord


def _room_state(coord: str, cfg: dict) -> RoomState:
    room = RoomState(
        coord=coord,
        room_type=cfg.get("type", "empty"),
        env_id=cfg.get("env", ""),
        landmark_id=cfg.get("landmark", ""),
        items=list(cfg.get("items", [])),
        props=list(cfg.get("props", [])),
        locked=bool(cfg.get("locked")),
    )
    name_key = cfg.get("name_key")
    if name_key:
        room.shared_payload["name_key"] = name_key
    encounter = cfg.get("encounter")
    if encounter:
        room.shared_payload["yog_encounter"] = encounter
    return room


def generate_yog_quest_floor(run: GameRun, floor_index: int) -> FloorMapState:
    map_cfg = YOG_MAPS[floor_index]
    width = int(map_cfg["width"])
    height = int(map_cfg["height"])
    rooms: Dict[str, RoomState] = {}
    for y in range(height):
        for x in range(width):
            coord = xy_to_coord(x, y)
            rooms[coord] = RoomState(coord=coord, room_type="wall")
    for coord, cfg in map_cfg["rooms"].items():
        if coord in rooms:
            rooms[coord] = _room_state(coord, cfg)
    start = map_cfg["start"]
    rooms[start].room_type = "spawn"
    rooms[start].explored = True
    rooms[start].cleared = True
    boss_coord = next((coord for coord, room in rooms.items() if room.room_type == "boss"), "")
    player_coords = {uid: start for uid in run.all_human_uids()}
    return FloorMapState(
        floor_index=floor_index,
        width=width,
        height=height,
        rooms=rooms,
        revealed_coords=[start],
        player_coords=player_coords,
        active_sessions={},
        player_session_map={},
        boss_coord=boss_coord,
        secret_boss_coord="",
        ritual_coord="",
        ritual_protocol="",
        secret_unlocked=False,
        secret_clue_found=False,
        floor_flags={"yog_quest": True, "yog_flags": {}},
    )


def apply_quest_encounter(run: GameRun, room: RoomState) -> None:
    encounter_id = room.shared_payload.get("yog_encounter", "")
    if not encounter_id:
        return
    cfg = YOG_ENCOUNTERS[encounter_id]
    fm = run.floor_map
    if fm is None:
        return
    flags = fm.floor_flags.setdefault("yog_flags", {})
    is_boss = bool(cfg.get("boss"))
    boss_mod = 0
    if is_boss:
        for name, delta in YOG_BOSS_HP_MODIFIERS.items():
            if flags.get(name):
                boss_mod += delta
    enemies = []
    for name, base_hp in cfg["enemies"]:
        hp = max(1, int(base_hp) + (boss_mod if is_boss else 0))
        enemies.append(EnemyState(
            name=name,
            hp=hp,
            max_hp=hp,
            shield=0,
            actions=1,
            bonus_actions=1 if is_boss else 0,
            max_actions=1,
            max_bonus_actions=1 if is_boss else 0,
        ))
    run.enemies = enemies
    run.node_data["yog_encounter"] = encounter_id
    run.node_data["yog_cultist_turn"] = 0
    run.node_data["yog_boss_turn"] = 0
