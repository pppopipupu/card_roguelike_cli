OUTER_PLANE_ACTIVE_FLAG = "outer_plane_active"
OUTER_PLANE_PHASE_KEY = "outer_plane_phase"
OUTER_PLANE_ROOM_KEY = "outer_plane_room"
OUTER_PLANE_VISITED_KEY = "outer_plane_visited"
OUTER_PLANE_FLAGS_KEY = "outer_plane_flags"
OUTER_PLANE_LUCIDITY_KEY = "outer_plane_lucidity"
OUTER_PLANE_COMBAT_FLAG = "outer_plane_encounter"
OUTER_PLANE_PENDING_KEY = "outer_plane_pending_option"
OUTER_PLANE_TRIGGER_FLAG = "dream_shard_triggered"

OUTER_PLANE_START_LUCIDITY = 12
OUTER_PLANE_MOVE_COST = 1
OUTER_PLANE_COMBAT_COST = 2
OUTER_PLANE_ECHO_GAIN = 3
OUTER_PLANE_START_HP = 80
OUTER_PLANE_START_ROOM = "drift_shore"
OUTER_PLANE_WIP_ROOM = "wip_room"
OUTER_PLANE_DREAM_ROOM = "zero_life"

PLANE_SHIFT_CARD = "neutral_plane_shift"
CALM_MIND_CARD = "calm_mind"
DREAM_SHARD_CARD = "dream_shard"
NECRONOMICON_ITEM = "necronomicon"

PHASE_QUEST = "quest"
PHASE_WIP = "wip"
PHASE_DREAM = "dream"

ZONE_ORDER = ("shore", "fringe", "core", "after")
ZONE_NAME_KEYS = {
    "shore": "i18n_outer_plane.zone.shore",
    "fringe": "i18n_outer_plane.zone.fringe",
    "core": "i18n_outer_plane.zone.core",
    "after": "i18n_outer_plane.zone.after",
}

OUTER_PLANE_INTENTS = {
    "wraith": {"gnaw": 9, "hush": 11, "veil": 10},
    "guardian": {"hammer": 15, "seal": 16, "gaze": 9, "collapse": 22},
}

OUTER_PLANE_ENCOUNTERS = {
    "mind_eater": {
        "enemies": [{"name_key": "i18n_outer_plane.enemy.mind_eater", "hp": 46}],
        "reward_card": PLANE_SHIFT_CARD,
        "reward_flag": "found_plane_shift",
    },
    "silent_warden": {
        "enemies": [{"name_key": "i18n_outer_plane.enemy.silent_warden", "hp": 52}],
        "reward_card": CALM_MIND_CARD,
        "reward_flag": "found_calm_mind",
    },
    "forge_guardian": {
        "enemies": [{"name_key": "i18n_outer_plane.enemy.forge_guardian", "hp": 60}],
        "boss": True,
    },
}

OUTER_PLANE_ROOMS = {
    "drift_shore": {
        "zone": "shore",
        "options": [
            {"id": "shore_to_reef", "to": "memory_reef"},
            {"id": "shore_to_gate", "to": "silent_gate"},
            {"id": "shore_to_echo", "to": "echo_hall"},
            {"id": "shore_to_forge", "to": "plane_forge"},
            {"id": "shore_observe", "once": True},
        ],
    },
    "memory_reef": {
        "zone": "fringe",
        "options": [
            {"id": "reef_fight", "encounter": "mind_eater", "butcher": True},
            {"id": "reef_back", "to": "drift_shore"},
        ],
    },
    "silent_gate": {
        "zone": "fringe",
        "options": [
            {"id": "gate_fight", "encounter": "silent_warden", "butcher": True},
            {"id": "gate_back", "to": "drift_shore"},
        ],
    },
    "echo_hall": {
        "zone": "fringe",
        "options": [
            {"id": "echo_gather", "lucidity": OUTER_PLANE_ECHO_GAIN, "once": True},
            {"id": "echo_back", "to": "drift_shore"},
        ],
    },
    "plane_forge": {
        "zone": "core",
        "options": [
            {"id": "forge_fuse", "requires": ["found_plane_shift", "found_calm_mind"], "fuse": True},
            {"id": "forge_smash", "encounter": "forge_guardian", "butcher": True, "set": {"forged_by_force": True}},
            {"id": "forge_back", "to": "drift_shore"},
        ],
    },
    "wip_room": {
        "zone": "after",
        "options": [
            {"id": "wip_touch_shard", "dream": True, "once": True},
            {"id": "wip_look", "once": True},
            {"id": "wip_leave", "leave": True},
        ],
    },
    "zero_life": {
        "zone": "after",
        "options": [
            {"id": "zero_wake", "wake": True},
        ],
    },
}

