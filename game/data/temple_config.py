TEMPLE_QUEST_FLAG = "quest_yog_death_state"
TEMPLE_ROOM_FLAG = "temple_room"
TEMPLE_FLAGS_KEY = "temple_flags"
TEMPLE_HP_KEY = "temple_hp"
TEMPLE_MAX_HP_KEY = "temple_max_hp"
TEMPLE_VISITED_KEY = "temple_visited"
TEMPLE_PENDING_KEY = "temple_pending_option"
TEMPLE_COMBAT_FLAG = "temple_encounter"
TEMPLE_INFO_FLAG = "temple_info_received"
TEMPLE_ACTIVE_FLAG = "temple_active"

TEMPLE_START_HP = 120
TEMPLE_WIN_HEAL = 15
BUTCHER_BONUS_CARDS = ("fireball",) * 8
TEMPLE_ENTER_ROOM = "temple_gate"
TEMPLE_BOSS_ROOM = "frozen_throne"
TEMPLE_FINAL_ROOM = "necronomicon_chamber"

ZONE_ORDER = ("gate", "outer", "inner", "sanctum", "finale")
ZONE_NAME_KEYS = {
    "gate": "i18n_temple.zone.gate",
    "outer": "i18n_temple.zone.outer",
    "inner": "i18n_temple.zone.inner",
    "sanctum": "i18n_temple.zone.sanctum",
    "finale": "i18n_temple.zone.finale",
}

CULTIST_NAMES = (
    "星辉教团·持烛教徒",
    "星辉教团·咏唱者",
    "星辉教团·执刃者",
    "星辉教团·守夜人",
    "星辉教团·疯癫祭司",
    "冰封圣所·霜卫",
    "镜中残影",
    "叛教哨兵",
)
BOSS_NAME = "冰封少女·欧吕尔的化身"

TEMPLE_INTENTS = {
    "cultist": {"ember": 8, "chant": 10, "ward": 12},
    "auril": {"frost_lance": 14, "winter_veil": 18, "aurora_gaze": 7, "absolute_zero": 20},
}

TEMPLE_ENCOUNTERS = {
    "cultist_patrol": {
        "enemies": [(CULTIST_NAMES[0], 34), (CULTIST_NAMES[1], 30)],
    },
    "spy_fight": {
        "enemies": [(CULTIST_NAMES[7], 50)],
    },
    "cultist_pair": {
        "enemies": [(CULTIST_NAMES[2], 36), (CULTIST_NAMES[0], 32)],
    },
    "preacher_fight": {
        "enemies": [(CULTIST_NAMES[4], 60)],
    },
    "mirror_wraith": {
        "enemies": [(CULTIST_NAMES[6], 52)],
    },
    "cultist_elite": {
        "enemies": [(CULTIST_NAMES[3], 40), (CULTIST_NAMES[2], 38), (CULTIST_NAMES[1], 36)],
    },
    "ritual_wave": {
        "enemies": [(CULTIST_NAMES[0], 38), (CULTIST_NAMES[1], 38), (CULTIST_NAMES[2], 40), (CULTIST_NAMES[3], 36)],
    },
    "frost_sentinel": {
        "enemies": [(CULTIST_NAMES[5], 58), (CULTIST_NAMES[5], 58)],
    },
    "auril_avatar": {
        "enemies": [(BOSS_NAME, 130)],
        "boss": True,
    },
}

TEMPLE_BOSS_HP_MODIFIERS = {"blade_offered": -30, "altar_defiled": 30}

TEMPLE_ROOMS = {
    "temple_gate": {
        "zone": "gate",
        "options": [
            {"id": "show_sigil", "to": "colonnade", "set": {"sigil_shown": True}},
            {"id": "force_in", "to": "colonnade", "set": {"forced_entry": True}},
            {"id": "gate_observe", "once": True},
            {"id": "gate_retreat", "leave": True},
        ],
    },
    "colonnade": {
        "zone": "gate",
        "options": [
            {"id": "col_fight", "to": "guard_post", "encounter": "cultist_patrol", "set": {"patrol_cleared": True}},
            {"id": "col_sneak", "to": "left_aisle", "set": {"path_sneak": True}},
        ],
    },
    "guard_post": {
        "zone": "gate",
        "options": [
            {"id": "spy_question", "to": "right_aisle", "set": {"spy_intel": True}},
            {"id": "spy_spare", "to": "right_aisle", "set": {"spy_spared": True}},
            {"id": "spy_kill", "to": "right_aisle", "encounter": "spy_fight", "set": {"spy_killed": True}},
        ],
    },
    "left_aisle": {
        "zone": "outer",
        "options": [
            {"id": "take_blade", "to": "frozen_fountain", "set": {"blade_taken": True}},
            {"id": "leave_blade", "to": "frozen_fountain"},
            {"id": "open_crypt", "to": "undercrypt", "set": {"crypt_found": True}},
        ],
    },
    "right_aisle": {
        "zone": "outer",
        "options": [
            {"id": "aisle_fight", "to": "frozen_fountain", "encounter": "cultist_pair"},
            {"id": "aisle_hide", "to": "hall_of_whispers", "set": {"ambush_avoided": True}},
        ],
    },
    "undercrypt": {
        "zone": "outer",
        "options": [
            {"id": "read_memory", "to": "mirror_gallery", "set": {"lore_auril": True}},
            {"id": "take_key", "to": "mirror_gallery", "set": {"bone_key": True}},
        ],
    },
    "frozen_fountain": {
        "zone": "outer",
        "options": [
            {"id": "fountain_drink", "to": "hall_of_whispers", "heal": 18, "once": True},
            {"id": "fountain_gaze", "to": "hall_of_whispers"},
            {"id": "fountain_move", "to": "hall_of_whispers"},
        ],
    },
    "hall_of_whispers": {
        "zone": "outer",
        "options": [
            {"id": "hear_sermon", "to": "sealed_archive", "set": {"priest_heard": True}},
            {"id": "silence_priest", "to": "ritual_chamber", "encounter": "preacher_fight", "set": {"priest_silenced": True}},
        ],
    },
    "sealed_archive": {
        "zone": "outer",
        "options": [
            {"id": "read_pages", "to": "ritual_chamber", "requires": ["spy_intel"], "set": {"pages_read": True}},
            {"id": "steal_pages", "to": "ritual_chamber", "requires": ["spy_intel"], "gp": 120, "set": {"pages_taken": True}},
            {"id": "archive_back", "to": "hall_of_whispers", "forbids": ["spy_intel"]},
        ],
    },
    "mirror_gallery": {
        "zone": "inner",
        "options": [
            {"id": "face_mirror", "to": "cultists_barracks", "encounter": "mirror_wraith", "set": {"mirror_faced": True}},
            {"id": "avoid_mirror", "to": "cultists_barracks"},
        ],
    },
    "cultists_barracks": {
        "zone": "inner",
        "options": [
            {"id": "barracks_fight", "to": "ritual_chamber", "encounter": "cultist_elite"},
            {"id": "eavesdrop", "to": "ritual_chamber", "set": {"ritual_known": True}},
        ],
    },
    "ritual_chamber": {
        "zone": "inner",
        "options": [
            {"id": "ritual_wave", "to": "cage_of_scholars", "encounter": "ritual_wave", "set": {"cultists_defeated": True}},
            {"id": "side_door", "to": "cage_of_scholars", "requires": ["bone_key"], "set": {"side_door_used": True}},
        ],
    },
    "cage_of_scholars": {
        "zone": "inner",
        "options": [
            {"id": "free_scholar", "to": "altar_of_frost", "heal": 12, "set": {"scholar_saved": True}},
            {"id": "ignore_scholar", "to": "altar_of_frost"},
        ],
    },
    "altar_of_frost": {
        "zone": "inner",
        "options": [
            {"id": "offer_blade", "to": "frozen_stair", "requires": ["blade_taken"], "set": {"blade_offered": True}},
            {"id": "defile_altar", "to": "frozen_stair", "gp": 200, "set": {"altar_defiled": True}},
            {"id": "pass_altar", "to": "frozen_stair"},
        ],
    },
    "frozen_stair": {
        "zone": "sanctum",
        "options": [
            {"id": "stair_rest", "to": "auril_shrine", "heal": 30, "once": True},
            {"id": "stair_listen", "to": "auril_shrine"},
            {"id": "stair_climb", "to": "auril_shrine"},
        ],
    },
    "auril_shrine": {
        "zone": "sanctum",
        "options": [
            {"id": "shrine_pray", "to": "blizzard_bridge"},
            {"id": "shrine_touch", "to": "blizzard_bridge"},
            {"id": "shrine_recall", "to": "blizzard_bridge", "requires": ["lore_auril"], "set": {"auril_remembered": True}},
        ],
    },
    "blizzard_bridge": {
        "zone": "sanctum",
        "options": [
            {"id": "bridge_careful", "to": "sentinel_hall", "heal": 10, "set": {"bridge_careful": True}},
            {"id": "bridge_rush", "to": "sentinel_hall", "set": {"bridge_rushed": True}},
        ],
    },
    "sentinel_hall": {
        "zone": "sanctum",
        "options": [
            {"id": "sentinel_fight", "to": "frozen_throne", "encounter": "frost_sentinel"},
            {"id": "use_ward", "to": "frozen_throne", "requires": ["scholar_saved"], "set": {"ward_used": True}},
        ],
    },
    "frozen_throne": {
        "zone": "sanctum",
        "options": [
            {"id": "challenge_boss", "to": "necronomicon_chamber", "encounter": "auril_avatar", "set": {"temple_boss_defeated": True}},
            {"id": "throne_wait", "once": True},
        ],
    },
    "necronomicon_chamber": {
        "zone": "finale",
        "options": [
            {"id": "read_book", "ending": True},
            {"id": "chamber_look", "once": True},
        ],
    },
}

ENDING_BRANCH_FLAGS = (
    "blade_offered",
    "altar_defiled",
    "scholar_saved",
    "spy_spared",
    "spy_killed",
    "priest_heard",
    "priest_silenced",
    "pages_read",
    "pages_taken",
    "mirror_faced",
    "lore_auril",
    "auril_remembered",
    "sigil_shown",
    "forced_entry",
)
