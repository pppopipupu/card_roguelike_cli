BIG_ROOM_MIN_DIM = 1
BIG_ROOM_MAX_DIM = 10

BIG_ROOM_SHAPES: dict[str, list[tuple[int, int]]] = {
    "rect_1x2": [(0, 0), (1, 0)],
    "rect_2x1": [(0, 0), (0, 1)],
    "rect_2x2": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "rect_2x3": [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)],
    "rect_3x2": [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)],
    "rect_1x3": [(0, 0), (1, 0), (2, 0)],
    "l_4_tr": [(0, 0), (1, 0), (0, 1), (0, 2)],
    "l_4_tl": [(0, 0), (1, 0), (1, 1), (1, 2)],
    "l_4_br": [(0, 0), (0, 1), (0, 2), (1, 2)],
    "l_4_bl": [(1, 0), (1, 1), (0, 2), (1, 2)],
}


def build_rect_offsets(width: int, height: int) -> list[tuple[int, int]]:
    w = int(width)
    h = int(height)
    if not (BIG_ROOM_MIN_DIM <= w <= BIG_ROOM_MAX_DIM and BIG_ROOM_MIN_DIM <= h <= BIG_ROOM_MAX_DIM):
        raise ValueError(f"Big room dimensions must be {BIG_ROOM_MIN_DIM}..{BIG_ROOM_MAX_DIM}, got {w}x{h}")
    return [(x, y) for y in range(h) for x in range(w)]


def compute_offsets_bbox(offsets: list[tuple[int, int]]) -> tuple[int, int]:
    if not offsets:
        return 0, 0
    xs = [p[0] for p in offsets]
    ys = [p[1] for p in offsets]
    return max(xs) - min(xs) + 1, max(ys) - min(ys) + 1


def is_valid_big_room_offsets(offsets: list[tuple[int, int]]) -> bool:
    if len(offsets) < 2:
        return False
    w, h = compute_offsets_bbox(offsets)
    if not (BIG_ROOM_MIN_DIM <= w <= BIG_ROOM_MAX_DIM and BIG_ROOM_MIN_DIM <= h <= BIG_ROOM_MAX_DIM):
        return False
    coord_set = set(offsets)
    visited = set()
    stack = [next(iter(coord_set))]
    while stack:
        cx, cy = stack.pop()
        if (cx, cy) in visited:
            continue
        visited.add((cx, cy))
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nxt = (cx + dx, cy + dy)
            if nxt in coord_set and nxt not in visited:
                stack.append(nxt)
    return len(visited) == len(coord_set)


BIG_ROOM_FLOOR_RULES: dict[int | float, tuple[int, int]] = {
    1: (1, 2),
    2: (1, 2),
    3: (1, 2),
    4: (0, 1),
}

BIG_ROOM_TEMPLATES: dict[str, dict] = {
    "forgotten_armory": {
        "name_key": "i18n_big_room.templates.forgotten_armory.name",
        "desc_key": "i18n_big_room.templates.forgotten_armory.desc",
        "icon": "🛡️",
        "shapes": ["rect_1x2", "rect_2x1", "rect_2x2"],
        "env_id": "big_armory_hall",
        "reveal_mode": "whole",
        "share_npcs": True,
        "share_items": False,
        "share_props": False,
        "keep_icon_on_clear": True,
        "direct_reveal_adjacent": False,
        "shared_npcs": ["armory_automaton"],
        "item_pool": ["field_bandage", "rusty_pickaxe", "smuggler_token", "sugar_cube_pack"],
        "prop_pool": ["bloodied_pack", "ancient_brazier", "smuggler_cache"],
        "item_chance_per_cell": 0.75,
        "prop_chance_per_cell": 0.65,
    },
    "sunken_scriptorium": {
        "name_key": "i18n_big_room.templates.sunken_scriptorium.name",
        "desc_key": "i18n_big_room.templates.sunken_scriptorium.desc",
        "icon": "📖",
        "shapes": ["rect_2x2", "l_4_tr", "l_4_tl", "l_4_br", "l_4_bl"],
        "env_id": "big_scriptorium_hall",
        "reveal_mode": "whole",
        "share_npcs": True,
        "share_items": False,
        "share_props": False,
        "keep_icon_on_clear": True,
        "direct_reveal_adjacent": True,
        "shared_npcs": ["lost_scholar"],
        "item_pool": ["ancient_notes", "glowing_runestone", "espresso_beans"],
        "prop_pool": ["dusty_bookshelf", "arcane_mirror", "runic_wall"],
        "item_chance_per_cell": 0.70,
        "prop_chance_per_cell": 0.75,
    },
    "labyrinth_catacomb": {
        "name_key": "i18n_big_room.templates.labyrinth_catacomb.name",
        "desc_key": "i18n_big_room.templates.labyrinth_catacomb.desc",
        "icon": "⚰️",
        "shapes": ["l_4_tr", "l_4_tl", "l_4_br", "l_4_bl", "rect_2x2"],
        "env_id": "big_catacomb_hall",
        "reveal_mode": "cell",
        "share_npcs": False,
        "share_items": False,
        "share_props": False,
        "keep_icon_on_clear": False,
        "direct_reveal_adjacent": False,
        "cell_hostile_pool": ["crypt_warden", "dungeon_raiders"],
        "cell_hostile_count": (1, 2),
        "item_pool": ["skeleton_key", "ancient_notes", "field_bandage", "smuggler_token"],
        "prop_pool": ["cracked_statue", "forgotten_shrine", "bloodied_pack"],
        "item_chance_per_cell": 0.65,
        "prop_chance_per_cell": 0.60,
    },
    "smuggler_bazaar": {
        "name_key": "i18n_big_room.templates.smuggler_bazaar.name",
        "desc_key": "i18n_big_room.templates.smuggler_bazaar.desc",
        "icon": "🏮",
        "shapes": ["rect_1x2", "rect_2x1", "rect_2x2"],
        "env_id": "big_bazaar_hall",
        "reveal_mode": "whole",
        "share_npcs": True,
        "share_items": True,
        "share_props": False,
        "keep_icon_on_clear": True,
        "direct_reveal_adjacent": True,
        "shared_npcs": ["smuggler_broker"],
        "shared_items": ["smuggler_token", "sugar_cube_pack"],
        "prop_pool": ["smuggler_cache", "shop_scale", "alchemy_desk"],
        "item_chance_per_cell": 0.0,
        "prop_chance_per_cell": 0.65,
    },
    "shattered_observatory_wing": {
        "name_key": "i18n_big_room.templates.shattered_observatory_wing.name",
        "desc_key": "i18n_big_room.templates.shattered_observatory_wing.desc",
        "icon": "🔭",
        "shapes": ["rect_1x2", "rect_2x1", "l_4_tr", "l_4_bl"],
        "env_id": "big_observatory_hall",
        "reveal_mode": "cell",
        "share_npcs": True,
        "share_items": False,
        "share_props": True,
        "keep_icon_on_clear": True,
        "direct_reveal_adjacent": False,
        "shared_npcs": ["rift_sentinel"],
        "shared_props": ["arcane_mirror", "runic_wall"],
        "item_pool": ["glowing_runestone", "ancient_notes", "espresso_beans"],
        "prop_pool": [],
        "item_chance_per_cell": 0.70,
        "prop_chance_per_cell": 0.0,
    },
    "abandoned_treasury_hall": {
        "name_key": "i18n_big_room.templates.abandoned_treasury_hall.name",
        "desc_key": "i18n_big_room.templates.abandoned_treasury_hall.desc",
        "icon": "👑",
        "shapes": ["rect_2x2", "l_4_br", "l_4_tl"],
        "env_id": "big_treasury_hall",
        "reveal_mode": "whole",
        "share_npcs": False,
        "share_items": False,
        "share_props": False,
        "keep_icon_on_clear": True,
        "direct_reveal_adjacent": True,
        "cell_hostile_pool": ["elite_guardian"],
        "cell_hostile_count": (1, 1),
        "guaranteed_cell_prop": "treasure_chest",
        "item_pool": ["merchant_ledger", "smuggler_token", "skeleton_key", "espresso_beans"],
        "prop_pool": ["cracked_statue", "crystal_cluster", "forgotten_shrine"],
        "item_chance_per_cell": 0.80,
        "prop_chance_per_cell": 0.55,
    },
}

from .chaos_expansion_data import CHAOS_BIG_ROOM_TEMPLATES
from .chireiden_data import CHIREIDEN_BIG_ROOM_TEMPLATES

BIG_ROOM_TEMPLATES.update(CHAOS_BIG_ROOM_TEMPLATES)
BIG_ROOM_TEMPLATES.update(CHIREIDEN_BIG_ROOM_TEMPLATES)
