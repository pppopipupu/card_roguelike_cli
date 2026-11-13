FLOOR_CONFIGS = {
    1: {
        "width": 8,
        "height": 6,
        "stage_min": 2,
        "stage_max": 12,
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
        "stage_min": 14,
        "stage_max": 25,
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
        "stage_min": 27,
        "stage_max": 31,
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
    4: {
        "width": 6,
        "height": 5,
        "stage_min": 32,
        "stage_max": 32,
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
}

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
    "teammate": "👥",
}

DIRECT_REVEAL_ADJACENT_TYPES = frozenset({
    "boss",
    "cafe",
    "shop",
    "rest",
    "treasure",
    "life_merchant",
    "downstairs",
})

PERMANENT_ICON_TYPES = frozenset({
    "cafe",
    "shop",
    "rest",
    "landmark",
    "life_merchant",
    "downstairs",
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
})
