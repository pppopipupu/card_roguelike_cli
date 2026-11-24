import random
from collections import deque
from ...data.progression.balance_config import LIFE_MERCHANT_FLOOR_CHANCE, LIFE_MERCHANT_MAX_PER_RUN
from ...data.world.big_room_config import BIG_ROOM_FLOOR_RULES, BIG_ROOM_SHAPES, BIG_ROOM_TEMPLATES
from ...data.world.grid_map_config import (
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
    if run is None or floor_index not in LIFE_MERCHANT_FLOOR_CHANCE:
        return False
    seen = int(run.map_data.get("life_merchant_count", 0) or 0)
    if seen >= LIFE_MERCHANT_MAX_PER_RUN:
        return False
    chance = float(LIFE_MERCHANT_FLOOR_CHANCE[floor_index])
    if random.random() < chance:
        run.map_data["life_merchant_count"] = seen + 1
        return True
    return False


def _plan_big_rooms(
    floor_index: int | float,
    width: int,
    height: int,
    rooms: dict[str, RoomState],
    spawn_xy: tuple[int, int],
    boss_xy: tuple[int, int],
) -> list[tuple[str, str, list[str]]]:
    min_cnt, max_cnt = BIG_ROOM_FLOOR_RULES.get(floor_index, (0, 0))
    if max_cnt <= 0:
        return []
    passable_coords = {c for c, r in rooms.items() if r.room_type != "wall"}
    sig = f"br:{floor_index}:{width}x{height}:{sorted(passable_coords)}"
    rng = random.Random(sig)
    target_cnt = rng.randint(min_cnt, max_cnt)
    if target_cnt <= 0:
        return []

    tpl_ids = [k for k, v in BIG_ROOM_TEMPLATES.items() if not v.get("chireiden_only")]
    rng.shuffle(tpl_ids)
    reserved = {spawn_xy, boss_xy}
    placed_cells: set[tuple[int, int]] = set()
    plans: list[tuple[str, str, list[str]]] = []

    occupied = {coord_to_xy(c) for c in passable_coords}
    for idx in range(target_cnt):
        if not tpl_ids:
            tpl_ids = [k for k, v in BIG_ROOM_TEMPLATES.items() if not v.get("chireiden_only")]
            rng.shuffle(tpl_ids)
        tpl_id = tpl_ids.pop(0)
        tpl = BIG_ROOM_TEMPLATES[tpl_id]
        shapes = list(tpl.get("shapes") or ["rect_2x2"])
        rng.shuffle(shapes)
        chosen_cells: list[tuple[int, int]] | None = None
        for shape_id in shapes:
            offsets = BIG_ROOM_SHAPES.get(shape_id)
            if not offsets:
                continue
            anchors = [(x, y) for y in range(height) for x in range(width)]
            rng.shuffle(anchors)
            for ax, ay in anchors:
                abs_cells = [(ax + dx, ay + dy) for dx, dy in offsets]
                if any(not (0 <= cx < width and 0 <= cy < height) for cx, cy in abs_cells):
                    continue
                cell_set = set(abs_cells)
                if cell_set & reserved or cell_set & placed_cells or cell_set & occupied:
                    continue
                connected = any(
                    any((nx, ny) in occupied and rooms[xy_to_coord(nx, ny)].room_type not in ("wall", "secret_boss", "obstacle") for nx, ny in neighbors_4(cx, cy, width, height))
                    for cx, cy in abs_cells
                )
                if not connected:
                    continue
                chosen_cells = abs_cells
                break
            if chosen_cells is not None:
                break
        if chosen_cells is not None:
            occupied.update(chosen_cells)
            placed_cells.update(chosen_cells)
            plans.append((f"br_{idx + 1}_{tpl_id}", tpl_id, [xy_to_coord(cx, cy) for cx, cy in chosen_cells]))
    return plans


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

    if cfg.get("has_cafe"):
        c = pop_candidate()
        if c:
            rooms[c].room_type = "cafe"
    if cfg.get("has_shop"):
        c = pop_candidate()
        if c:
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
        found_corpses = save_manager.corpses.list_at_floor(floor_index, exclude_user=caller_uid)
        if found_corpses:
            corpse = random.choice(found_corpses)
            c = pop_candidate()
            if c:
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

    big_room_plans = _plan_big_rooms(floor_index, width, height, rooms, spawn_xy, boss_xy)
    for _, _, cell_coords in big_room_plans:
        for c in cell_coords:
            rooms[c].room_type = "empty"

    _populate_room_details(rooms)
    player_coords = {}
    if run is not None:
        for uid in run.all_human_uids():
            player_coords[uid] = spawn_coord

    fm = FloorMapState(
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
        big_rooms={},
    )
    if big_room_plans:
        from .rooms.big_room import create_big_room_instance
        rng = random.Random(f"br:{floor_index}:{'|'.join(g for g, _, _ in big_room_plans)}:{len(rooms)}")
        for group_id, tpl_id, cell_coords in big_room_plans:
            create_big_room_instance(fm, group_id, tpl_id, cell_coords, rng=rng)
    from .rooms.forced_triggers import seed_floor_forced_triggers

    seed_floor_forced_triggers(fm, floor_index)
    return fm


def _populate_room_details(rooms: dict) -> None:
    from ...data.entities.potion_data import POTION_CONFIG
    from ...data.world.room_interact_data import (
        DUNGEON_NPC_POOL,
        DUNGEON_PROP_POOL,
        OBSTACLE_STYLES,
        ROOM_ENVIRONMENTS,
        ROOM_GROUND_ITEM_POOL,
        ROOM_POPULATE_CHANCES,
    )
    from .rooms.hostile_npc import ensure_room_hostile_npcs, ensure_treasure_chest_prop
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
        ensure_room_hostile_npcs(None, room)
        ensure_treasure_chest_prop(room)
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
        for prop_id in rng.sample(DUNGEON_PROP_POOL, rng.randint(pmin, pmax)):
            if prop_id not in room.props:
                room.props.append(prop_id)
        if room.room_type not in ("boss", "secret_boss", "downstairs"):
            if rng.random() < ROOM_POPULATE_CHANCES["npc_chance"]:
                npc_pick = rng.choice(DUNGEON_NPC_POOL)
                if npc_pick not in room.npcs:
                    room.npcs.append(npc_pick)
            if rng.random() < ROOM_POPULATE_CHANCES["item_chance"]:
                if rng.random() < ROOM_POPULATE_CHANCES["potion_drop_chance"] and neutral_potions:
                    room.items = [f"potion:{rng.choice(neutral_potions)}"]
                else:
                    room.items = [rng.choice(ROOM_GROUND_ITEM_POOL)]
