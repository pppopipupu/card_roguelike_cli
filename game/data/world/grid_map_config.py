from typing import Any

ALLY_SUMMON_SP_COST = 1

ACT1_FLOOR = 1
GATE_BOSS_FLOOR = 2
AVERGOMON_FLOOR = 3
FINAL_BOSS_FLOOR = 4

FLOOR_CONFIGS: dict[int | float, dict[str, Any]] = {
    0: {
        "width": 5,
        "height": 3,
        "difficulty_scale": 1,
        "display_floor": 0,
        "name_key": "i18n_tutorial.floor_name",
        "has_cafe": False,
        "has_shop": True,
        "has_secret_boss": False,
        "secret_mode": "",
        "landmarks": ["tutorial_shrine", "tutorial_exit"],
        "secret_boss_name": "",
        "obstacle_count": 1,
        "high_danger_count": 0,
        "elite_count": 0,
        "treasure_count": 1,
        "rest_count": 1,
        "event_count": 0,
    },
    1: {
        "width": 8,
        "height": 6,
        "difficulty_scale": 3,
        "boss_pool": "early",
        "name_key": "i18n_grid_map.floor_1_name",
        "has_cafe": True,
        "has_shop": True,
        "has_secret_boss": True,
        "secret_mode": "floor_ritual",
        "landmarks": ["observatory", "broken_sword_camp"],
        "secret_boss_name": "裂隙暗影领主",
        "obstacle_count": 2,
        "high_danger_count": 2,
        "elite_count": 2,
        "treasure_count": 2,
        "rest_count": 1,
        "event_count": 4,
    },
    2: {
        "width": 9,
        "height": 7,
        "difficulty_scale": 18,
        "boss_pool": "gate",
        "name_key": "i18n_grid_map.floor_2_name",
        "has_cafe": True,
        "has_shop": True,
        "has_secret_boss": True,
        "secret_mode": "floor_ritual",
        "landmarks": ["observatory", "ancient_stele"],
        "secret_boss_name": "星渊审判官",
        "obstacle_count": 3,
        "high_danger_count": 2,
        "elite_count": 2,
        "treasure_count": 2,
        "rest_count": 1,
        "event_count": 5,
    },
    3: {
        "width": 8,
        "height": 6,
        "difficulty_scale": 29,
        "boss_pool": "aforgomon",
        "name_key": "i18n_grid_map.floor_3_name",
        "has_cafe": True,
        "has_shop": True,
        "has_secret_boss": True,
        "secret_mode": "cross_floor_relic",
        "landmarks": ["ancient_stele"],
        "secret_boss_name": "深渊原初回响",
        "obstacle_count": 2,
        "high_danger_count": 2,
        "elite_count": 2,
        "treasure_count": 1,
        "rest_count": 1,
        "event_count": 4,
    },
    3.5: {
        "name_key": "i18n_grid_map.floor_3_5_name",
        "difficulty_scale": 31,
        "boss_name": "彭宁离子井·超级传送门·初阶裂隙",
        "secret_boss_name": "灵乌路空",
        "landmarks": ["chireiden_fusion_terminal", "chireiden_penning_stabilizer"],
        "big_rooms": [
            "lunar_he3_elevator_hub",
            "pb_bi_fast_reactor_chamber",
            "d_he3_tokamak_array",
            "penning_ion_well_sanctum",
        ],
    },
    4: {
        "width": 6,
        "height": 5,
        "difficulty_scale": 32,
        "boss_pool": "final",
        "name_key": "i18n_grid_map.floor_4_name",
        "has_cafe": False,
        "has_shop": False,
        "has_secret_boss": False,
        "secret_mode": "",
        "landmarks": [],
        "secret_boss_name": "",
        "obstacle_count": 1,
        "high_danger_count": 2,
        "elite_count": 1,
        "treasure_count": 1,
        "rest_count": 1,
        "event_count": 2,
    },
    5: {
        "width": 16,
        "height": 12,
        "difficulty_scale": 34,
        "display_floor": 1,
        "name_key": "i18n_yog_quest.map.frost_wilds",
        "has_cafe": False,
        "has_shop": False,
        "has_secret_boss": False,
        "secret_mode": "",
        "landmarks": [],
        "secret_boss_name": "",
        "obstacle_count": 0,
        "high_danger_count": 0,
        "elite_count": 0,
        "treasure_count": 0,
        "rest_count": 0,
        "event_count": 0,
    },
    6: {
        "width": 10,
        "height": 8,
        "difficulty_scale": 40,
        "display_floor": 1,
        "name_key": "i18n_yog_quest.map.yog_temple",
        "has_cafe": False,
        "has_shop": False,
        "has_secret_boss": False,
        "secret_mode": "",
        "landmarks": [],
        "secret_boss_name": "",
        "obstacle_count": 0,
        "high_danger_count": 0,
        "elite_count": 0,
        "treasure_count": 0,
        "rest_count": 0,
        "event_count": 0,
    },
    1.5: {
        "width": 6,
        "height": 5,
        "difficulty_scale": 8,
        "display_floor": 1.5,
        "name_key": "i18n_bleak_falls.floor_1_5_name",
        "has_cafe": False,
        "has_shop": False,
        "has_secret_boss": False,
        "secret_mode": "",
        "landmarks": [],
        "secret_boss_name": "",
        "obstacle_count": 0,
        "high_danger_count": 0,
        "elite_count": 0,
        "treasure_count": 0,
        "rest_count": 0,
        "event_count": 0,
    },
    1.67777: {
        "width": 6,
        "height": 3,
        "difficulty_scale": 11,
        "display_floor": 1.67777,
        "name_key": "i18n_bleak_falls.floor_1_67777_name",
        "has_cafe": False,
        "has_shop": False,
        "has_secret_boss": False,
        "secret_mode": "",
        "landmarks": [],
        "secret_boss_name": "",
        "obstacle_count": 0,
        "high_danger_count": 0,
        "elite_count": 0,
        "treasure_count": 0,
        "rest_count": 0,
        "event_count": 0,
    },
}


def get_display_floor(floor_index: int | float) -> int | float:
    cfg = FLOOR_CONFIGS.get(floor_index)
    if cfg is not None and "display_floor" in cfg:
        return cfg["display_floor"]
    return floor_index


def format_display_floor(floor_index: int | float) -> str:
    display = get_display_floor(floor_index)
    if isinstance(display, float) and not display.is_integer():
        return f"{display:g}"
    return str(int(display))


def get_run_floor_index(run) -> int | float:
    fm = getattr(run, "floor_map", None) if run is not None else None
    if fm is not None:
        return fm.floor_index
    return 1


def get_floor_difficulty_scale(floor_index: int | float) -> int:
    cfg = FLOOR_CONFIGS.get(floor_index)
    if cfg is not None and "difficulty_scale" in cfg:
        return int(cfg["difficulty_scale"])
    return int(FLOOR_CONFIGS[1]["difficulty_scale"])


def get_run_difficulty_scale(run) -> int:
    return get_floor_difficulty_scale(get_run_floor_index(run))


SP_CONFIG = {
    "default_max_sp": 10,
    "obstacle_cost_min": 2,
    "obstacle_cost_max": 3,
    "forced_obstacle_hp_loss": 3,
    "rest_sp_gain": 4,
    "rest_exhaustion_cure": 1,
    "cafe_drink_sp_gain": 5,
    "cafe_drink_exhaustion_cure": 1,
    "cafe_drink_price": 25,
    "observatory_gold_cost": 15,
    "observatory_sp_cost": 2,
    "observatory_reveal_count": 3,
    "stele_charge_max_sp_cost": 2,
    "stele_charge_hp_cost": 10,
    "ritual_sp_cost": 3,
    "ritual_hp_cost": 5,
}

EXHAUSTION_CONFIG = {
    "max_level": 5,
    "level1_draw_penalty": 1,
    "level1_obstacle_hp_loss": 3,
    "level2_shield_multiplier": 0.75,
    "level3_ba_loss": 1,
    "level3_damage_multiplier": 0.80,
    "level4_draw_penalty": 1,
    "level4_max_hp_divisor": 2,
}

HIGH_DANGER_CONFIG = {
    "hazard_hp_ratio": 0.15,
    "hazard_hp_min": 4,
    "bonus_gold_min": 25,
    "bonus_gold_max": 45,
}

QUEST_RELIC_CONFIG = {
    "broken_rift_compass": {
        "name_key": "i18n_grid_map.quest_relic.broken_rift_compass.name",
        "desc_key": "i18n_grid_map.quest_relic.broken_rift_compass.desc",
    },
    "awakened_rift_compass": {
        "name_key": "i18n_grid_map.quest_relic.awakened_rift_compass.name",
        "desc_key": "i18n_grid_map.quest_relic.awakened_rift_compass.desc",
    },
    "camp_ember": {
        "name_key": "i18n_grid_map.quest_relic.camp_ember.name",
        "desc_key": "i18n_grid_map.quest_relic.camp_ember.desc",
    },
}

LANDMARK_CONFIGS = {
    "observatory": {
        "name_key": "i18n_grid_map.landmarks.observatory.name",
        "desc_key": "i18n_grid_map.landmarks.observatory.desc",
        "npc_key": "i18n_grid_map.landmarks.observatory.npc",
    },
    "broken_sword_camp": {
        "name_key": "i18n_grid_map.landmarks.broken_sword_camp.name",
        "desc_key": "i18n_grid_map.landmarks.broken_sword_camp.desc",
        "npc_key": "i18n_grid_map.landmarks.broken_sword_camp.npc",
    },
    "ancient_stele": {
        "name_key": "i18n_grid_map.landmarks.ancient_stele.name",
        "desc_key": "i18n_grid_map.landmarks.ancient_stele.desc",
        "npc_key": "i18n_grid_map.landmarks.ancient_stele.npc",
    },
    "bleak_falls_entrance": {
        "name_key": "i18n_grid_map.room_name.bleak_falls_entrance",
        "desc_key": "i18n_bleak_falls.entrance.desc",
        "npc_key": "i18n_bleak_falls.entrance.desc",
    },
    "bleak_pillar_puzzle": {
        "name_key": "i18n_grid_map.room_name.bleak_pillar_puzzle",
        "desc_key": "i18n_bleak_falls.puzzles.pillar_desc",
        "npc_key": "i18n_bleak_falls.puzzles.pillar_desc",
    },
    "bleak_sanctuary_gate": {
        "name_key": "i18n_grid_map.room_name.bleak_sanctuary_gate",
        "desc_key": "i18n_bleak_falls.entrance.sanctuary_gate_desc",
        "npc_key": "i18n_bleak_falls.entrance.sanctuary_gate_desc",
    },
    "golden_claw_door": {
        "name_key": "i18n_grid_map.room_name.golden_claw_door",
        "desc_key": "i18n_bleak_falls.puzzles.claw_door_desc",
        "npc_key": "i18n_bleak_falls.puzzles.claw_door_desc",
    },
    "word_wall": {
        "name_key": "i18n_grid_map.room_name.word_wall",
        "desc_key": "i18n_bleak_falls.word_wall.desc",
        "npc_key": "i18n_bleak_falls.word_wall.desc",
    },
    "barrow_exit": {
        "name_key": "i18n_grid_map.room_name.barrow_exit",
        "desc_key": "i18n_bleak_falls.barrow_exit.desc",
        "npc_key": "i18n_bleak_falls.barrow_exit.desc",
    },
    "chireiden_fusion_terminal": {
        "name_key": "i18n_grid_map.landmarks.chireiden_fusion_terminal.name",
        "desc_key": "i18n_grid_map.landmarks.chireiden_fusion_terminal.desc",
        "npc_key": "i18n_grid_map.landmarks.chireiden_fusion_terminal.npc",
    },
    "chireiden_penning_stabilizer": {
        "name_key": "i18n_grid_map.landmarks.chireiden_penning_stabilizer.name",
        "desc_key": "i18n_grid_map.landmarks.chireiden_penning_stabilizer.desc",
        "npc_key": "i18n_grid_map.landmarks.chireiden_penning_stabilizer.npc",
    },
    "tutorial_shrine": {
        "name_key": "i18n_tutorial.shrine.title",
        "desc_key": "i18n_tutorial.shrine.desc",
        "npc_key": "i18n_tutorial.elder.name",
    },
    "tutorial_exit": {
        "name_key": "i18n_tutorial.exit.title",
        "desc_key": "i18n_tutorial.exit.desc",
        "npc_key": "i18n_tutorial.elder.name",
    },
}

SECRET_RITUAL_PROTOCOLS = (
    "exhaustion_or_curse",
    "camp_ember",
    "sp_sacrifice",
)

MAP_EVENT_IDS = (
    "ghostification",
    "collapsed_tunnel",
    "ancient_beacon",
    "mist_ferryman",
    "bladesinger_echo",
)

ROOM_ICONS = {
    "fog": "🌫️",
    "wall": "🧱",
    "obstacle": "⛏️",
    "unknown": "❔",
    "cleared": "▫️",
    "empty": "▫️",
    "spawn": "▫️",
    "battle": "⚔️",
    "elite": "💀",
    "high_danger": "🔥",
    "event": "❔",
    "landmark": "🏛️",
    "cafe": "☕",
    "shop": "🛒",
    "rest": "⛺",
    "treasure": "📦",
    "life_merchant": "⚖️",
    "boss": "👹",
    "downstairs": "🌀",
    "secret_boss": "👁️",
    "corpse": "❔",
    "player": "📍",
    "solid_wall": "🧱",
    "bleak_falls_entrance": "🕳️",
    "bleak_pillar_puzzle": "🗿",
    "bleak_sanctuary_gate": "🚪",
    "golden_claw_door": "🦁",
    "word_wall": "📜",
    "barrow_exit": "🪜",
    "big_room": "🏛️",
}

DIRECT_REVEAL_ADJACENT_TYPES = frozenset({
    "boss",
    "cafe",
    "shop",
    "rest",
    "treasure",
    "life_merchant",
    "downstairs",
    "solid_wall",
    "bleak_falls_entrance",
    "bleak_pillar_puzzle",
    "bleak_sanctuary_gate",
    "golden_claw_door",
    "word_wall",
    "barrow_exit",
    "big_room",
})

PERMANENT_ICON_TYPES = frozenset({
    "cafe",
    "shop",
    "rest",
    "landmark",
    "life_merchant",
    "downstairs",
    "solid_wall",
    "bleak_falls_entrance",
    "bleak_pillar_puzzle",
    "bleak_sanctuary_gate",
    "golden_claw_door",
    "word_wall",
    "barrow_exit",
    "big_room",
})

PASSABLE_ROOM_TYPES = frozenset({
    "empty",
    "spawn",
    "battle",
    "elite",
    "high_danger",
    "event",
    "landmark",
    "cafe",
    "shop",
    "rest",
    "treasure",
    "life_merchant",
    "boss",
    "downstairs",
    "corpse",
    "bleak_falls_entrance",
    "bleak_pillar_puzzle",
    "bleak_sanctuary_gate",
    "golden_claw_door",
    "word_wall",
    "barrow_exit",
    "big_room",
})
