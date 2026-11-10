COMMAND_SECTIONS = ("basic", "battle", "town", "cafe", "social")

COMMAND_SECTION_ORDER = {
    "basic": (
        "start",
        "help",
        "tutorial",
        "changelog",
        "status",
        "choose",
        "deck",
        "bag",
        "overview",
        "stats",
        "checkin",
        "class",
        "mode",
        "abandon"
    ),
    "battle": (
        "use",
        "potion",
        "minion",
        "skill",
        "special",
        "end_turn",
        "fold",
        "queue",
        "draw",
        "discard",
        "exhaust",
        "minion_graveyard",
        "enemy_graveyard"
    ),
    "town": (
        "town",
        "town_move",
        "town_home",
        "town_exit",
        "map_style",
        "take",
        "town_use",
        "town_talk"
    ),
    "cafe": (
        "cafe_look",
        "cafe_talk",
        "cafe_leave"
    ),
    "social": (
        "friend",
        "team",
        "logs",
        "logc",
        "projection",
        "quest_list",
        "query",
        "lock"
    )
}

GAME_STATE_ORDER = ("menu", "town", "explore", "battle", "dialog", "cafe")

POTION_LIST_ALIASES = ("list", "ls", "列表", "药水列表")
POTION_DRINK_ALIASES = ("drink", "喝", "饮用", "喝药水", "use_potion")
POTION_THROW_ALIASES = ("throw", "投掷", "投", "扔", "t")
POTION_DROP_ALIASES = ("drop", "drop_potion", "discard_potion", "丢弃", "丢弃药水", "丢药", "丢", "dp")
POTION_CONTAINER_ALIASES = ("药水", "potion", "pot")
