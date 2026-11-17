YOG_QUEST_FLAG = "quest_yog_death_state"
YOG_INFO_FLAG = "yog_quest_info_received"
YOG_SIGIL_ITEM = "star_sigil"
FOUNTAIN_GP_TOSSED_FLAG = "fountain_1gp_tossed"
FOUNTAIN_OUTER_PLANE_COST_GP = 1

YOG_FLOOR_WILDS = 5
YOG_FLOOR_TEMPLE = 6

YOG_CULTISTS = (
    "星辉教团·持烛教徒",
    "星辉教团·咏唱者",
    "星辉教团·执刃者",
    "星辉教团·守夜人",
    "星辉教团·疯癫祭司",
    "星辉教团·内殿守卫",
    "镜中残影",
    "叛教哨兵",
)
YOG_BOSS_NAME = "冰封少女·欧吕尔的化身"

YOG_BOSS_INTENTS = {
    "cultist": {"ember": 8, "chant": 10, "ward": 12},
    "auril": {"frost_lance": 14, "winter_veil": 18, "aurora_gaze": 7, "absolute_zero": 20},
}

YOG_BOSS_HP_MODIFIERS = {"blade_offered": -30, "altar_defiled": 30}

YOG_ENCOUNTERS = {
    "wilds_scouts": {
        "enemies": [("星辉教团·持烛教徒", 40), ("叛教哨兵", 38)],
    },
    "wilds_wolves": {
        "enemies": [("雪原狼", 42), ("雪原狼", 42)],
    },
    "wilds_altar": {
        "enemies": [("星辉教团·疯癫祭司", 62), ("星辉教团·执刃者", 40)],
    },
    "wilds_alpha": {
        "enemies": [("霜牙巨狼", 95)],
    },
    "temple_patrol": {
        "enemies": [("星辉教团·持烛教徒", 34), ("星辉教团·咏唱者", 30)],
    },
    "temple_pair": {
        "enemies": [("星辉教团·执刃者", 36), ("星辉教团·持烛教徒", 32)],
    },
    "temple_preacher": {
        "enemies": [("星辉教团·疯癫祭司", 60)],
    },
    "mirror_wraith": {
        "enemies": [("镜中残影", 52)],
    },
    "temple_elite": {
        "enemies": [("星辉教团·守夜人", 40), ("星辉教团·执刃者", 38), ("星辉教团·咏唱者", 36)],
    },
    "ritual_wave": {
        "enemies": [("星辉教团·持烛教徒", 38), ("星辉教团·咏唱者", 38), ("星辉教团·执刃者", 40), ("星辉教团·守夜人", 36)],
    },
    "frost_sentinels": {
        "enemies": [("星辉教团·内殿守卫", 58), ("星辉教团·内殿守卫", 58)],
    },
    "temple_boss": {
        "enemies": [(YOG_BOSS_NAME, 130)],
        "boss": True,
    },
}

YOG_MAPS = {
    YOG_FLOOR_WILDS: {
        "width": 16,
        "height": 12,
        "name_key": "i18n_yog_quest.map.frost_wilds",
        "start": "B11",
        "rooms": {
            "B11": {"type": "spawn", "name_key": "i18n_yog_quest.room.wilds_entry.name", "env": "yog_wilds_start"},
            "C11": {"type": "empty", "env": "yog_wilds_path"},
            "D11": {"type": "empty", "env": "yog_wilds_path"},
            "E11": {"type": "empty", "env": "yog_wilds_path"},
            "E10": {"type": "rest", "name_key": "i18n_yog_quest.room.wilds_camp.name", "env": "yog_wilds_camp"},
            "E9": {"type": "empty", "env": "yog_wilds_path"},
            "E8": {"type": "empty", "env": "yog_wilds_path"},
            "D8": {"type": "battle", "name_key": "i18n_yog_quest.room.wilds_ruins.name", "env": "yog_wilds_ruins", "encounter": "wilds_scouts"},
            "C8": {"type": "empty", "env": "yog_wilds_path"},
            "B8": {"type": "empty", "env": "yog_wilds_path"},
            "B7": {"type": "treasure", "name_key": "i18n_yog_quest.room.wilds_cave.name", "env": "yog_wilds_cave"},
            "B6": {"type": "empty", "env": "yog_wilds_path"},
            "C6": {"type": "empty", "env": "yog_wilds_path"},
            "D6": {"type": "empty", "env": "yog_wilds_path"},
            "E6": {"type": "empty", "env": "yog_wilds_path"},
            "F6": {"type": "empty", "env": "yog_wilds_path"},
            "F5": {"type": "empty", "env": "yog_wilds_path"},
            "F4": {"type": "landmark", "landmark": "yog_shrine", "name_key": "i18n_yog_quest.room.wilds_shrine.name", "env": "yog_wilds_shrine"},
            "F7": {"type": "landmark", "landmark": "yog_lake", "name_key": "i18n_yog_quest.room.wilds_lake.name", "env": "yog_wilds_lake"},
            "G6": {"type": "empty", "env": "yog_wilds_path"},
            "H6": {"type": "empty", "env": "yog_wilds_path"},
            "H7": {"type": "empty", "env": "yog_wilds_path"},
            "H8": {"type": "empty", "env": "yog_wilds_path"},
            "I8": {"type": "empty", "env": "yog_wilds_path"},
            "I9": {"type": "battle", "name_key": "i18n_yog_quest.room.wilds_wolves.name", "env": "yog_wilds_woods", "encounter": "wilds_wolves"},
            "J9": {"type": "empty", "env": "yog_wilds_path"},
            "K9": {"type": "empty", "env": "yog_wilds_path"},
            "K8": {"type": "treasure", "name_key": "i18n_yog_quest.room.wilds_cache.name", "env": "yog_wilds_cache"},
            "K7": {"type": "empty", "env": "yog_wilds_path"},
            "K6": {"type": "empty", "env": "yog_wilds_path"},
            "L6": {"type": "elite", "name_key": "i18n_yog_quest.room.wilds_altar.name", "env": "yog_wilds_altar", "encounter": "wilds_altar"},
            "M6": {"type": "empty", "env": "yog_wilds_path"},
            "N6": {"type": "empty", "env": "yog_wilds_path"},
            "N5": {"type": "empty", "env": "yog_wilds_path"},
            "N4": {"type": "empty", "env": "yog_wilds_path"},
            "N3": {"type": "elite", "name_key": "i18n_yog_quest.room.wilds_alpha.name", "env": "yog_wilds_den", "encounter": "wilds_alpha"},
            "O3": {"type": "empty", "env": "yog_wilds_path"},
            "O2": {"type": "downstairs", "name_key": "i18n_yog_quest.room.wilds_gate.name", "env": "yog_wilds_gate", "props": ["temple_gate"]},
            "P2": {"type": "empty", "name_key": "i18n_yog_quest.room.wilds_forecourt.name", "env": "yog_wilds_forecourt"},
        },
    },
    YOG_FLOOR_TEMPLE: {
        "width": 10,
        "height": 8,
        "name_key": "i18n_yog_quest.map.yog_temple",
        "start": "A1",
        "rooms": {
            "A1": {"type": "spawn", "name_key": "i18n_yog_quest.room.temple_gate.name", "env": "yog_temple_gate"},
            "B1": {"type": "battle", "name_key": "i18n_yog_quest.room.temple_colonnade.name", "env": "yog_temple_hall", "encounter": "temple_patrol"},
            "C1": {"type": "landmark", "landmark": "yog_spy", "name_key": "i18n_yog_quest.room.temple_guard_post.name", "env": "yog_temple_guard"},
            "D1": {"type": "treasure", "name_key": "i18n_yog_quest.room.temple_left_aisle.name", "env": "yog_temple_aisle", "items": ["frost_offering"]},
            "E1": {"type": "battle", "name_key": "i18n_yog_quest.room.temple_right_aisle.name", "env": "yog_temple_aisle", "encounter": "temple_pair"},
            "F1": {"type": "landmark", "landmark": "yog_memory", "name_key": "i18n_yog_quest.room.temple_undercrypt.name", "env": "yog_temple_crypt"},
            "G1": {"type": "rest", "name_key": "i18n_yog_quest.room.temple_fountain.name", "env": "yog_temple_fountain"},
            "H1": {"type": "battle", "name_key": "i18n_yog_quest.room.temple_hall.name", "env": "yog_temple_hall", "encounter": "temple_preacher"},
            "I1": {"type": "landmark", "landmark": "yog_archive", "name_key": "i18n_yog_quest.room.temple_archive.name", "env": "yog_temple_archive"},
            "J1": {"type": "battle", "name_key": "i18n_yog_quest.room.temple_mirror.name", "env": "yog_temple_mirror", "encounter": "mirror_wraith"},
            "F2": {"type": "battle", "name_key": "i18n_yog_quest.room.temple_barracks.name", "env": "yog_temple_barracks", "encounter": "temple_elite"},
            "G2": {"type": "battle", "name_key": "i18n_yog_quest.room.temple_ritual.name", "env": "yog_temple_ritual", "encounter": "ritual_wave"},
            "H2": {"type": "landmark", "landmark": "yog_cage", "name_key": "i18n_yog_quest.room.temple_cage.name", "env": "yog_temple_cage"},
            "I2": {"type": "landmark", "landmark": "yog_altar", "name_key": "i18n_yog_quest.room.temple_altar.name", "env": "yog_temple_altar"},
            "J2": {"type": "rest", "name_key": "i18n_yog_quest.room.temple_stair.name", "env": "yog_temple_stair"},
            "J3": {"type": "landmark", "landmark": "yog_temple_shrine", "name_key": "i18n_yog_quest.room.temple_shrine.name", "env": "yog_temple_shrine"},
            "J4": {"type": "landmark", "landmark": "yog_bridge", "name_key": "i18n_yog_quest.room.temple_bridge.name", "env": "yog_temple_bridge"},
            "J5": {"type": "battle", "name_key": "i18n_yog_quest.room.temple_sentinels.name", "env": "yog_temple_sentinel", "encounter": "frost_sentinels"},
            "J6": {"type": "boss", "name_key": "i18n_yog_quest.room.temple_throne.name", "env": "yog_temple_throne", "encounter": "temple_boss"},
            "J7": {"type": "landmark", "landmark": "yog_necronomicon", "name_key": "i18n_yog_quest.room.temple_chamber.name", "env": "yog_temple_chamber", "locked": True},
        },
    },
}

YOG_LANDMARKS = {
    "yog_shrine": {
        "name_key": "i18n_yog_quest.landmark.yog_shrine.name",
        "desc_key": "i18n_yog_quest.landmark.yog_shrine.desc",
        "options": [
            {
                "id": "pray",
                "text_key": "i18n_yog_quest.landmark.yog_shrine.opt_pray",
                "result_key": "i18n_yog_quest.landmark.yog_shrine.res_pray",
                "heal": 15,
                "set": {"lore_auril": True},
                "once": True,
            },
            {
                "id": "search",
                "text_key": "i18n_yog_quest.landmark.yog_shrine.opt_search",
                "result_key": "i18n_yog_quest.landmark.yog_shrine.res_search",
                "item": "ancient_notes",
                "once": True,
            },
        ],
    },
    "yog_lake": {
        "name_key": "i18n_yog_quest.landmark.yog_lake.name",
        "desc_key": "i18n_yog_quest.landmark.yog_lake.desc",
        "options": [
            {
                "id": "gaze",
                "text_key": "i18n_yog_quest.landmark.yog_lake.opt_gaze",
                "result_key": "i18n_yog_quest.landmark.yog_lake.res_gaze",
                "reveal_all": True,
                "set": {"lake_vision": True},
                "once": True,
            }
        ],
    },
    "yog_spy": {
        "name_key": "i18n_yog_quest.landmark.yog_spy.name",
        "desc_key": "i18n_yog_quest.landmark.yog_spy.desc",
        "options": [
            {
                "id": "question",
                "text_key": "i18n_yog_quest.landmark.yog_spy.opt_question",
                "result_key": "i18n_yog_quest.landmark.yog_spy.res_question",
                "set": {"spy_intel": True},
                "once": True,
            }
        ],
    },
    "yog_memory": {
        "name_key": "i18n_yog_quest.landmark.yog_memory.name",
        "desc_key": "i18n_yog_quest.landmark.yog_memory.desc",
        "options": [
            {
                "id": "read_memory",
                "text_key": "i18n_yog_quest.landmark.yog_memory.opt_read",
                "result_key": "i18n_yog_quest.landmark.yog_memory.res_read",
                "set": {"lore_auril": True},
                "once": True,
            }
        ],
    },
    "yog_archive": {
        "name_key": "i18n_yog_quest.landmark.yog_archive.name",
        "desc_key": "i18n_yog_quest.landmark.yog_archive.desc",
        "options": [
            {
                "id": "read_pages",
                "text_key": "i18n_yog_quest.landmark.yog_archive.opt_read",
                "result_key": "i18n_yog_quest.landmark.yog_archive.res_read",
                "item": "cult_pages",
                "set": {"pages_read": True},
                "once": True,
            }
        ],
    },
    "yog_cage": {
        "name_key": "i18n_yog_quest.landmark.yog_cage.name",
        "desc_key": "i18n_yog_quest.landmark.yog_cage.desc",
        "options": [
            {
                "id": "free_scholar",
                "text_key": "i18n_yog_quest.landmark.yog_cage.opt_free",
                "result_key": "i18n_yog_quest.landmark.yog_cage.res_free",
                "heal": 12,
                "set": {"scholar_saved": True},
                "once": True,
            }
        ],
    },
    "yog_altar": {
        "name_key": "i18n_yog_quest.landmark.yog_altar.name",
        "desc_key": "i18n_yog_quest.landmark.yog_altar.desc",
        "options": [
            {
                "id": "offer_blade",
                "text_key": "i18n_yog_quest.landmark.yog_altar.opt_offer",
                "result_key": "i18n_yog_quest.landmark.yog_altar.res_offer",
                "requires_item": "frost_offering",
                "consume_item": True,
                "set": {"blade_offered": True},
                "once": True,
            },
            {
                "id": "defile_altar",
                "text_key": "i18n_yog_quest.landmark.yog_altar.opt_defile",
                "result_key": "i18n_yog_quest.landmark.yog_altar.res_defile",
                "gp": 200,
                "set": {"altar_defiled": True},
                "once": True,
            },
        ],
    },
    "yog_temple_shrine": {
        "name_key": "i18n_yog_quest.landmark.yog_temple_shrine.name",
        "desc_key": "i18n_yog_quest.landmark.yog_temple_shrine.desc",
        "options": [
            {
                "id": "recall",
                "text_key": "i18n_yog_quest.landmark.yog_temple_shrine.opt_recall",
                "result_key": "i18n_yog_quest.landmark.yog_temple_shrine.res_recall",
                "set": {"auril_remembered": True},
                "once": True,
            }
        ],
    },
    "yog_bridge": {
        "name_key": "i18n_yog_quest.landmark.yog_bridge.name",
        "desc_key": "i18n_yog_quest.landmark.yog_bridge.desc",
        "options": [
            {
                "id": "cross",
                "text_key": "i18n_yog_quest.landmark.yog_bridge.opt_cross",
                "result_key": "i18n_yog_quest.landmark.yog_bridge.res_cross",
                "heal": 10,
                "set": {"bridge_careful": True},
                "once": True,
            }
        ],
    },
    "yog_necronomicon": {
        "name_key": "i18n_yog_quest.landmark.yog_necronomicon.name",
        "desc_key": "i18n_yog_quest.landmark.yog_necronomicon.desc",
        "options": [
            {
                "id": "read_book",
                "text_key": "i18n_yog_quest.landmark.yog_necronomicon.opt_read",
                "result_key": "i18n_yog_quest.landmark.yog_necronomicon.res_read",
                "ending": True,
            }
        ],
    },
}

YOG_ENDING_BRANCH_FLAGS = (
    "blade_offered",
    "altar_defiled",
    "scholar_saved",
    "spy_intel",
    "pages_read",
    "lore_auril",
    "auril_remembered",
    "bridge_careful",
    "lake_vision",
)

YOG_QUEST_ZONE_KEY = "yog_quest_zone"
YOG_QUEST_ROUTE_KEY = "yog_quest_route"
