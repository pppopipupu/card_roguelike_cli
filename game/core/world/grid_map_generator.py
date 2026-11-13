import random
from collections import deque
from ...data.balance_config import LIFE_MERCHANT_MAX_PER_RUN, LIFE_MERCHANT_STAGE_CONFIG
from ...data.grid_map_config import (
    FLOOR_CONFIGS,
    MAP_EVENT_IDS,
    PASSABLE_ROOM_TYPES,
    SECRET_RITUAL_PROTOCOLS,
    SP_CONFIG,
)
from ...models.state import FloorMapState, RoomState


def coord_to_xy(coord: str) -> tuple[int, int]:
    if not coord or len(coord) < 2:
        return -1, -1
    col_ch = coord[0].upper()
    if not ("A" <= col_ch <= "Z"):
        return -1, -1
    try:
        row = int(coord[1:]) - 1
    except ValueError:
        return -1, -1
    return ord(col_ch) - ord("A"), row


def xy_to_coord(x: int, y: int) -> str:
    return f"{chr(ord('A') + x)}{y + 1}"


def neighbors_4(x: int, y: int, width: int, height: int) -> list[tuple[int, int]]:
    res = []
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            res.append((nx, ny))
    return res


def compute_effective_stage(floor_map: FloorMapState, coord: str) -> int:
    cfg = FLOOR_CONFIGS.get(floor_map.floor_index, FLOOR_CONFIGS[1])
    s_min = int(cfg["stage_min"])
    s_max = int(cfg["stage_max"])
    if s_min >= s_max:
        return s_min
    spawn_xy = (0, floor_map.height // 2)
    for c, r in floor_map.rooms.items():
        if r.room_type == "spawn":
            spawn_xy = coord_to_xy(c)
            break
    boss_xy = coord_to_xy(floor_map.boss_coord) if floor_map.boss_coord else (floor_map.width - 1, floor_map.height // 2)
    cur_xy = coord_to_xy(coord)
    max_dist = max(1, abs(boss_xy[0] - spawn_xy[0]) + abs(boss_xy[1] - spawn_xy[1]))
    cur_dist = abs(cur_xy[0] - spawn_xy[0]) + abs(cur_xy[1] - spawn_xy[1])
    ratio = min(1.0, max(0.0, cur_dist / max_dist))
    return int(round(s_min + ratio * (s_max - s_min)))


def _reachable_without_obstacles(rooms: dict[str, RoomState], start_coord: str, width: int, height: int) -> set[str]:
    visited = set()
    q = deque([start_coord])
    while q:
        cur = q.popleft()
        if cur in visited:
            continue
        r = rooms.get(cur)
        if r is None or r.room_type in ("wall", "obstacle", "secret_boss"):
            continue
        visited.add(cur)
        cx, cy = coord_to_xy(cur)
        for nx, ny in neighbors_4(cx, cy, width, height):
            nc = xy_to_coord(nx, ny)
            if nc not in visited:
                q.append(nc)
    return visited


def _carve_passable_set(width: int, height: int, spawn_xy: tuple[int, int], boss_xy: tuple[int, int]) -> set[tuple[int, int]]:
    passable = set()
    cx, cy = spawn_xy
    bx, by = boss_xy
    passable.add((cx, cy))
    while cx != bx or cy != by:
        options = []
        if cx < bx:
            options.append((cx + 1, cy))
        elif cx > bx:
            options.append((cx - 1, cy))
        if cy < by:
            options.append((cx, cy + 1))
        elif cy > by:
            options.append((cx, cy - 1))
        if random.random() < 0.25:
            for nx, ny in neighbors_4(cx, cy, width, height):
                options.append((nx, ny))
        cx, cy = random.choice(options)
        passable.add((cx, cy))

    target_count = max(len(passable) + 6, int(round(width * height * random.uniform(0.46, 0.56))))
    target_count = min(width * height - 2, target_count)
    frontier = list(passable)
    attempts = 0
    while len(passable) < target_count and frontier and attempts < width * height * 12:
        attempts += 1
        px, py = random.choice(frontier)
        nbrs = neighbors_4(px, py, width, height)
        random.shuffle(nbrs)
        added = False
        for nx, ny in nbrs:
            if (nx, ny) not in passable:
                adj_open = sum(1 for ax, ay in neighbors_4(nx, ny, width, height) if (ax, ay) in passable)
                if adj_open <= 2 or random.random() < 0.35:
                    passable.add((nx, ny))
                    frontier.append((nx, ny))
                    added = True
                    break
        if not added and len(frontier) > 1:
            frontier.remove((px, py))
    return passable


def _roll_life_merchant(run, floor_index: int) -> bool:
    if run is None or floor_index not in (1, 2, 3):
        return False
    seen = int(run.map_data.get("life_merchant_count", 0) or 0)
    if seen >= LIFE_MERCHANT_MAX_PER_RUN:
        return False
    cfg = FLOOR_CONFIGS.get(floor_index, FLOOR_CONFIGS[1])
    s_min, s_max = cfg["stage_min"], cfg["stage_max"]
    for stg in range(s_min, s_max + 1):
        if stg in LIFE_MERCHANT_STAGE_CONFIG:
            entry = LIFE_MERCHANT_STAGE_CONFIG[stg]
            chance = entry[2] if isinstance(entry, (tuple, list)) else entry
            if random.random() < float(chance):
                run.map_data["life_merchant_count"] = seen + 1
                return True
    return False


def generate_floor_map(run, floor_index: int, save_manager=None) -> FloorMapState:
    cfg = FLOOR_CONFIGS.get(floor_index, FLOOR_CONFIGS[1])
    width = int(cfg["width"])
    height = int(cfg["height"])
    spawn_xy = (0, height // 2)
    boss_xy = (width - 1, height // 2)
    spawn_coord = xy_to_coord(*spawn_xy)
    boss_coord = xy_to_coord(*boss_xy)

    passable_xys = _carve_passable_set(width, height, spawn_xy, boss_xy)
    rooms: dict[str, RoomState] = {}
    for y in range(height):
        for x in range(width):
            c = xy_to_coord(x, y)
            if (x, y) in passable_xys:
                rooms[c] = RoomState(coord=c, room_type="empty")
            else:
                rooms[c] = RoomState(coord=c, room_type="wall")

    rooms[spawn_coord].room_type = "spawn"
    rooms[spawn_coord].explored = True
    rooms[spawn_coord].cleared = (floor_index > 1)
    rooms[boss_coord].room_type = "boss"

    candidates = [
        xy_to_coord(x, y)
        for (x, y) in passable_xys
        if xy_to_coord(x, y) not in (spawn_coord, boss_coord)
    ]
    random.shuffle(candidates)

    def pop_candidate():
        return candidates.pop() if candidates else None

    if cfg.get("has_cafe") and candidates:
        c = pop_candidate()
        rooms[c].room_type = "cafe"
    if cfg.get("has_shop") and candidates:
        c = pop_candidate()
        rooms[c].room_type = "shop"
    for _ in range(int(cfg.get("rest_count", 1))):
        c = pop_candidate()
        if c:
            rooms[c].room_type = "rest"
    if _roll_life_merchant(run, floor_index):
        c = pop_candidate()
        if c:
            rooms[c].room_type = "life_merchant"

    landmark_coords = []
    for lm_id in cfg.get("landmarks", []):
        c = pop_candidate()
        if c:
            rooms[c].room_type = "landmark"
            rooms[c].landmark_id = lm_id
            landmark_coords.append(c)

    for _ in range(int(cfg.get("treasure_count", 1))):
        c = pop_candidate()
        if c:
            rooms[c].room_type = "treasure"

    for _ in range(int(cfg.get("elite_count", 1))):
        c = pop_candidate()
        if c:
            rooms[c].room_type = "elite"

    for _ in range(int(cfg.get("high_danger_count", 1))):
        c = pop_candidate()
        if c:
            rooms[c].room_type = "high_danger"
            rooms[c].is_high_danger = True

    event_pool = list(MAP_EVENT_IDS)
    random.shuffle(event_pool)
    for i in range(int(cfg.get("event_count", 2))):
        c = pop_candidate()
        if c:
            rooms[c].room_type = "event"
            if i < len(event_pool):
                rooms[c].shared_payload["event_id"] = event_pool[i]

    if save_manager is not None and hasattr(save_manager, "corpses"):
        caller_uid = getattr(run, "user_id", "") if run else ""
        found_corpses = []
        for stg in range(int(cfg["stage_min"]), int(cfg["stage_max"]) + 1):
            found_corpses.extend(save_manager.corpses.list_at_stage(stg, exclude_user=caller_uid))
        if found_corpses and candidates:
            corpse = random.choice(found_corpses)
            c = pop_candidate()
            rooms[c].room_type = "corpse"
            rooms[c].shared_payload["corpse_id"] = corpse.get("id", "")

    for c in list(candidates):
        if random.random() < 0.55:
            rooms[c].room_type = "battle"

    obstacles_target = int(cfg.get("obstacle_count", 0))
    obstacle_placed = 0
    for c in list(candidates):
        if obstacle_placed >= obstacles_target:
            break
        if rooms[c].room_type not in ("empty", "battle"):
            continue
        prev_type = rooms[c].room_type
        rooms[c].room_type = "obstacle"
        reach = _reachable_without_obstacles(rooms, spawn_coord, width, height)
        required_ok = all(
            rc in reach
            for rc, rr in rooms.items()
            if rr.room_type not in ("wall", "obstacle", "secret_boss")
        )
        if required_ok:
            rooms[c].obstacle_sp = random.randint(SP_CONFIG["obstacle_cost_min"], SP_CONFIG["obstacle_cost_max"])
            obstacle_placed += 1
        else:
            rooms[c].room_type = prev_type

    secret_boss_coord = ""
    ritual_coord = ""
    ritual_protocol = ""
    if cfg.get("has_secret_boss"):
        wall_adj = []
        for c, r in rooms.items():
            if r.room_type != "wall":
                continue
            wx, wy = coord_to_xy(c)
            if any(rooms[xy_to_coord(nx, ny)].room_type in PASSABLE_ROOM_TYPES for nx, ny in neighbors_4(wx, wy, width, height)):
                wall_adj.append(c)
        if wall_adj:
            secret_boss_coord = random.choice(wall_adj)
            rooms[secret_boss_coord].room_type = "secret_boss"
        if landmark_coords:
            ritual_coord = landmark_coords[-1]
        else:
            corridor_opts = [c for c, r in rooms.items() if r.room_type == "empty" and c != spawn_coord]
            if corridor_opts:
                ritual_coord = random.choice(corridor_opts)
        if cfg.get("secret_mode") == "cross_floor_relic":
            ritual_protocol = "awakened_compass"
        else:
            ritual_protocol = random.choice(SECRET_RITUAL_PROTOCOLS)

    _populate_room_details(rooms)
    player_coords = {}
    if run is not None:
        for uid in run.all_human_uids():
            player_coords[uid] = spawn_coord

    return FloorMapState(
        floor_index=floor_index,
        width=width,
        height=height,
        rooms=rooms,
        revealed_coords=[spawn_coord],
        player_coords=player_coords,
        active_sessions={},
        player_session_map={},
        boss_coord=boss_coord,
        secret_boss_coord=secret_boss_coord,
        ritual_coord=ritual_coord,
        ritual_protocol=ritual_protocol,
        secret_unlocked=False,
        secret_clue_found=False,
        floor_flags={},
    )


def _populate_room_details(rooms: dict) -> None:
    from ...data.potion_data import POTION_CONFIG
    from ...data.room_interact_data import (
        DUNGEON_NPC_POOL,
        DUNGEON_PROP_POOL,
        OBSTACLE_STYLES,
        ROOM_ENVIRONMENTS,
        ROOM_GROUND_ITEM_POOL,
        ROOM_POPULATE_CHANCES,
    )
    sig = "|".join(f"{c}:{rooms[c].room_type}" for c in sorted(rooms.keys()))
    rng = random.Random(sig)
    neutral_potions = [pid for pid in POTION_CONFIG.keys() if pid not in ("fury_potion", "intellect_potion")]
    style_keys = list(OBSTACLE_STYLES.keys())
    for coord in sorted(rooms.keys()):
        room = rooms[coord]
        if room.room_type == "wall":
            continue
        if room.room_type == "obstacle":
            room.obstacle_style = rng.choice(style_keys)
            continue
        envs = ROOM_ENVIRONMENTS.get(room.room_type, ROOM_ENVIRONMENTS["empty"])
        room.env_id = rng.choice(envs)
        if room.room_type == "shop":
            room.npcs = ["shop_merchant"]
            room.props = ["shop_scale", "shop_display"]
            if rng.random() < 0.5:
                room.items = [rng.choice(ROOM_GROUND_ITEM_POOL)]
            continue
        if room.room_type == "cafe":
            room.props = ["cafe_espresso_machine", "cafe_gramophone", "cafe_guestbook"]
            if rng.random() < 0.5:
                room.items = [rng.choice(["espresso_beans", "sugar_cube_pack"])]
            continue
        if room.room_type == "spawn":
            room.props = [rng.choice(["ancient_brazier", "runic_wall"])]
            continue
        pmin = ROOM_POPULATE_CHANCES["props_min"]
        pmax = min(len(DUNGEON_PROP_POOL), ROOM_POPULATE_CHANCES["props_max"])
        room.props = rng.sample(DUNGEON_PROP_POOL, rng.randint(pmin, pmax))
        if room.room_type not in ("boss", "secret_boss", "downstairs"):
            if rng.random() < ROOM_POPULATE_CHANCES["npc_chance"]:
                room.npcs = [rng.choice(DUNGEON_NPC_POOL)]
            if rng.random() < ROOM_POPULATE_CHANCES["item_chance"]:
                if rng.random() < ROOM_POPULATE_CHANCES["potion_drop_chance"] and neutral_potions:
                    room.items = [f"potion:{rng.choice(neutral_potions)}"]
                else:
                    room.items = [rng.choice(ROOM_GROUND_ITEM_POOL)]
