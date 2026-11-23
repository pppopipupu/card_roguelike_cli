BLEAK_FALLS_FLOOR_INDEX = 1.5
BLEAK_SANCTUARY_FLOOR_INDEX = 1.67777
NEXT_FLOOR_AFTER_BLEAK_FALLS = 2

ITEM_QGP_BOMB = "qgp_bomb"
ITEM_GOLDEN_CLAW = "golden_claw"
ITEM_DRAGONSTONE = "dragonstone"
ITEM_ARVEL_JOURNAL = "arvel_journal"
ITEM_NORDIC_MEAD = "nordic_mead"
ITEM_SURVEY_CHART = "survey_chart"

NPC_FARENGAR_ROOM = "farengar_court_mage"
NPC_FARENGAR_TOWN = "Farengar_Secret_Fire"
NPC_ARVEL_TRAPPED = "arvel_trapped"
NPC_MAP_SURVEYOR = "map_surveyor"
NPC_BRAZIER_KEEPER = "brazier_keeper"

PROP_NORDIC_URN = "nordic_urn"
PROP_BLEAK_CLUE = "bleak_clue_tablet"
PROP_NORDIC_BRAZIER = "nordic_brazier"

ROOM_SOLID_WALL = "solid_wall"
ROOM_BLEAK_ENTRANCE = "bleak_falls_entrance"
ROOM_PILLAR_PUZZLE = "bleak_pillar_puzzle"
ROOM_SANCTUARY_GATE = "bleak_sanctuary_gate"
ROOM_CLAW_DOOR = "golden_claw_door"
ROOM_WORD_WALL = "word_wall"
ROOM_BARROW_EXIT = "barrow_exit"

CARD_FUS_RO_DAH = "fus_ro_dah"

QUEST_BLEAK_FALLS = "bleak_falls"
QUEST_RUNIC_ECHOES = "runic_echoes"
QUEST_ANCIENT_CARTOGRAPHER = "ancient_cartographer"

BLEAK_FALLS_STAGE_ORDER = (
    "need_bomb",
    "wall_breached",
    "in_barrow",
    "got_claw",
    "in_sanctuary",
    "door_opened",
    "dragonstone_taken",
    "back_on_surface",
    "tavern_ready",
)

BLEAK_FALLS_REWARDS = {
    "pillar_gold": 45,
    "pillar_heal": 15,
    "pillar_trap_damage": 4,
    "urn_gold": 18,
    "brazier_heal": 4,
    "word_wall_heal": 25,
    "word_wall_sp": 5,
    "word_wall_gold": 35,
    "dragonstone_gold": 60,
    "tavern_gp_reward": 150,
    "mead_heal": 12,
    "mead_sp": 4,
}

RANDOM_QUEST_CONFIG = {
    QUEST_RUNIC_ECHOES: {
        "kind": "single",
        "target": 3,
        "reward_gold": 55,
        "reward_heal": 12,
        "npc_id": NPC_BRAZIER_KEEPER,
    },
    QUEST_ANCIENT_CARTOGRAPHER: {
        "kind": "multi",
        "target": 5,
        "reward_gold": 80,
        "reward_gp": 20,
        "reward_item": ITEM_SURVEY_CHART,
        "npc_id": NPC_MAP_SURVEYOR,
    },
}

BLEAK_FALLS_MAP_WIDTH = 6
BLEAK_FALLS_MAP_HEIGHT = 5
BLEAK_FALLS_START_COORD = "A3"

BLEAK_FALLS_ROOMS = {
    "A3": {
        "room_type": "spawn",
        "props": [PROP_NORDIC_URN],
        "env": "spawn_sanctum",
    },
    "B3": {
        "room_type": "battle",
        "encounter": ["荒爆强盗", "强盗掠夺者"],
        "props": [PROP_NORDIC_BRAZIER],
        "env": "bone_alcove",
    },
    "B2": {
        "room_type": "empty",
        "props": [PROP_BLEAK_CLUE],
        "env": "mossy_vault",
    },
    "C2": {
        "room_type": ROOM_PILLAR_PUZZLE,
        "landmark_id": ROOM_PILLAR_PUZZLE,
        "env": "landmark_hall",
    },
    "C3": {
        "room_type": "elite",
        "encounter": ["巨型冰霜蜘蛛"],
        "elite_name": "巨型冰霜蜘蛛",
        "arvel_pending": True,
        "env": "elite_sanctuary",
    },
    "D3": {
        "room_type": "rest",
        "env": "rest_hearth",
    },
    "D4": {
        "room_type": "treasure",
        "bonus_item": ITEM_NORDIC_MEAD,
        "env": "gilded_crypt",
    },
    "E3": {
        "room_type": ROOM_SANCTUARY_GATE,
        "landmark_id": ROOM_SANCTUARY_GATE,
        "env": "landmark_hall",
    },
}

BLEAK_SANCTUARY_MAP_WIDTH = 6
BLEAK_SANCTUARY_MAP_HEIGHT = 3
BLEAK_SANCTUARY_START_COORD = "A2"

BLEAK_SANCTUARY_ROOMS = {
    "A2": {
        "room_type": "spawn",
        "props": [PROP_NORDIC_URN],
        "env": "dungeon_corridor",
    },
    "B2": {
        "room_type": "battle",
        "encounter": ["古诺德尸鬼", "尸鬼幽魂"],
        "env": "bone_alcove",
    },
    "C2": {
        "room_type": ROOM_CLAW_DOOR,
        "landmark_id": ROOM_CLAW_DOOR,
        "blocks_coords": ["D2"],
        "env": "landmark_hall",
    },
    "D2": {
        "room_type": ROOM_WORD_WALL,
        "landmark_id": ROOM_WORD_WALL,
        "env": "landmark_hall",
    },
    "D1": {
        "room_type": "treasure",
        "props": [PROP_NORDIC_URN],
        "env": "gilded_crypt",
    },
    "E2": {
        "room_type": "boss",
        "encounter": ["尸鬼领主·米洛克", "古诺德尸鬼"],
        "boss_name": "尸鬼领主·米洛克",
        "is_high_danger": True,
        "env": "boss_throne",
    },
}

TOWN_FLAG_BLEAK_STATE = "quest_bleak_falls_state"
TOWN_FLAG_BLEAK_STAGE = "quest_bleak_falls_stage"
TOWN_FLAG_BLEAK_OUTCOME = "quest_bleak_falls_outcome"
TOWN_FLAG_BLEAK_TAVERN_READY = "bleak_falls_tavern_ready"
TOWN_FLAG_BLEAK_ITEMS = "bleak_falls_retained_items"
TOWN_FLAG_MULTI_QUESTS = "multi_run_quests"
FLOOR5_KEY_ITEM = "floor5_ancient_key"
ANCIENT_CYCLE_ACHIEVEMENT_ID = "ancient_cycle_breaker"
BLEAK_FALLS_FUS_RO_DAH_ACHIEVEMENT_ID = "bleak_falls_fus_ro_dah"
BLEAK_FALLS_COMPLETED_ACHIEVEMENT_ID = "bleak_falls_completed"
