TUTORIAL_FLOOR_INDEX = 0
TUTORIAL_MAP_WIDTH = 5
TUTORIAL_MAP_HEIGHT = 3
TUTORIAL_START_COORD = "A2"

TUTORIAL_STARTING_HP = 50
TUTORIAL_STARTING_MAX_HP = 50
TUTORIAL_STARTING_GOLD = 80
TUTORIAL_STARTING_SP = 10

TUTORIAL_DECK = (
    "magic_missile",
    "fire_bolt",
    "shield",
    "warrior_bash",
    "mercenary",
    "lucky_coin",
    "first_aid",
    "misty_step",
)

TUTORIAL_REWARD_GOLD = 40
TUTORIAL_REWARD_CARDS = ("arcane_intellect", "iron_wave", "dagger_throw")
TUTORIAL_REWARD_POTION = "healing_potion"

TUTORIAL_ENEMY = {
    "name": "新手训练木偶",
    "hp": 20,
    "actions": 1,
    "bonus_actions": 0,
    "atk": 4,
    "shield": 4,
}

TUTORIAL_ROOMS = {
    "A2": {
        "room_type": "spawn",
        "env": "spawn_sanctum",
        "npcs": ["tutorial_elder"],
        "name_key": "i18n_tutorial.room.spawn",
        "forced_triggers": [{"id": "tutorial_enter_spawn", "timing": "on_enter", "once": True, "chance": 1.0}],
    },
    "B2": {
        "room_type": "battle",
        "env": "battle_arena",
        "encounter": "tutorial_scarecrow",
        "name_key": "i18n_tutorial.room.battle",
        "forced_triggers": [{"id": "tutorial_enter_battle", "timing": "on_enter", "once": True, "chance": 1.0}],
    },
    "B1": {
        "room_type": "obstacle",
        "env": "dungeon_corridor",
        "obstacle_sp": 2,
        "obstacle_style": "collapsed_boulders",
        "name_key": "i18n_tutorial.room.obstacle",
    },
    "C1": {
        "room_type": "treasure",
        "env": "treasure_vault",
        "items": ["field_bandage"],
        "props": ["treasure_chest"],
        "name_key": "i18n_tutorial.room.treasure",
        "forced_triggers": [{"id": "tutorial_enter_treasure", "timing": "on_enter", "once": True, "chance": 1.0}],
    },
    "B3": {
        "room_type": "landmark",
        "env": "landmark_hall",
        "landmark_id": "tutorial_shrine",
        "npcs": ["tutorial_elder"],
        "name_key": "i18n_tutorial.room.shrine",
    },
    "C2": {
        "room_type": "rest",
        "env": "rest_hearth",
        "name_key": "i18n_tutorial.room.rest",
        "forced_triggers": [{"id": "tutorial_enter_rest", "timing": "on_enter", "once": True, "chance": 1.0}],
    },
    "D2": {
        "room_type": "shop",
        "env": "shop_parlor",
        "name_key": "i18n_tutorial.room.shop",
        "forced_triggers": [{"id": "tutorial_enter_shop", "timing": "on_enter", "once": True, "chance": 1.0}],
    },
    "E2": {
        "room_type": "landmark",
        "env": "downstairs_hall",
        "landmark_id": "tutorial_exit",
        "npcs": ["tutorial_elder"],
        "name_key": "i18n_tutorial.room.exit",
    },
}

TUTORIAL_NPCS = {
    "tutorial_elder": {
        "name_key": "i18n_tutorial.elder.name",
        "desc_key": "i18n_tutorial.elder.desc",
        "aliases": ["向导长老", "向导", "长老", "elder", "guide"],
        "non_hostile": True,
    },
}

TUTORIAL_LANDMARKS = {
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
