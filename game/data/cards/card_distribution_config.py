from ..progression.balance_config import KEY_SCHOLAR_REPLACE_CHANCE, REWARD_CARD_COUNT
from ..progression.reward_config import EPIC_CARD_RARITY, NORMAL_CARD_RARITIES, NORMAL_REWARD_EXCLUDED_RARITIES

LATE_FLOOR_THRESHOLD = 3
UPGRADE_SUFFIX = "+"

CLASS_TO_CARD_COLOR: dict[str, str] = {
    "战士": "warrior",
    "法师": "wizard",
    "蕾忍": "ninja",
    "雇佣兵": "mercenary",
}
DEFAULT_CARD_COLOR = "wizard"

KEY_SCHOLAR_REPLACE_CONFIG: dict = {
    "subclass": "秘钥学者",
    "source_color": "wizard",
    "target_card": "key_resonance",
    "excluded_rarities": NORMAL_REWARD_EXCLUDED_RARITIES,
    "chance": KEY_SCHOLAR_REPLACE_CHANCE,
}

RARITY_ORDER: tuple[str, ...] = ("common", "rare", "epic", "legendary", "mythic", "artifact")

DEFAULT_RARITY_WEIGHTS: dict[str, float] = {
    "common": 60.0,
    "rare": 30.0,
    "epic": 12.0,
    "legendary": 2.5,
    "mythic": 1.0,
    "artifact": 0.5,
}

BATTLE_DIFFICULTY_CHANNEL_MAP: dict[str, str] = {
    "normal": "battle_normal",
    "ghost": "battle_normal",
    "elite": "battle_elite",
    "boss": "battle_elite",
    "secret_boss": "battle_elite",
}

CHANNEL_POLICIES: dict[str, dict] = {
    "battle_normal": {
        "early_rarities": ("common", "rare"),
        "late_rarities": ("common", "rare", "epic"),
        "color_mode": "player_and_neutral",
        "count": REWARD_CARD_COUNT,
        "weighted": True,
        "append_coop_cards": True,
        "modifiers": ("fireball_replace", "key_scholar_replace"),
    },
    "battle_elite": {
        "early_rarities": ("common", "rare", "epic"),
        "late_rarities": ("common", "rare", "epic", "legendary"),
        "color_mode": "player_and_neutral",
        "count": REWARD_CARD_COUNT,
        "weighted": True,
        "append_coop_cards": True,
        "modifiers": ("fireball_replace", "key_scholar_replace"),
    },
    "shop": {
        "early_rarities": NORMAL_CARD_RARITIES,
        "late_rarities": NORMAL_CARD_RARITIES,
        "color_mode": "player_and_neutral",
        "count": REWARD_CARD_COUNT,
        "weighted": True,
        "allow_coop_when_flag": True,
        "modifiers": ("fireball_replace",),
    },
    "treasure": {
        "early_rarities": (EPIC_CARD_RARITY,),
        "late_rarities": (EPIC_CARD_RARITY, "legendary"),
        "color_mode": "player_and_neutral",
        "count": REWARD_CARD_COUNT,
        "weighted": True,
        "modifiers": ("fireball_replace",),
    },
    "rest_meditate": {
        "early_rarities": NORMAL_CARD_RARITIES,
        "late_rarities": NORMAL_CARD_RARITIES,
        "color_mode": "player_only",
        "card_types": ("spell",),
        "count": REWARD_CARD_COUNT,
        "weighted": True,
        "allow_coop_when_flag": True,
        "modifiers": ("fireball_replace",),
    },
    "cafe_cross_class": {
        "early_rarities": NORMAL_CARD_RARITIES,
        "late_rarities": NORMAL_CARD_RARITIES,
        "color_mode": "custom",
        "count": REWARD_CARD_COUNT,
        "weighted": True,
    },
    "event_fountain": {
        "early_rarities": NORMAL_CARD_RARITIES,
        "late_rarities": NORMAL_CARD_RARITIES,
        "color_mode": "fixed",
        "colors": ("wizard",),
        "count": REWARD_CARD_COUNT,
        "weighted": True,
    },
    "event_phantom": {
        "early_rarities": NORMAL_CARD_RARITIES,
        "late_rarities": NORMAL_CARD_RARITIES,
        "color_mode": "all",
        "card_types": ("spell",),
        "count": 1,
        "weighted": True,
        "fallback": "dagger_throw",
    },
    "npc_scholar": {
        "early_rarities": ("rare",),
        "late_rarities": ("rare",),
        "color_mode": "fixed",
        "colors": ("wizard", "neutral"),
        "count": 1,
        "weighted": True,
        "fallback": "fireball",
    },
    "npc_combat": {
        "early_rarities": ("common", "rare"),
        "late_rarities": ("common", "rare"),
        "color_mode": "fixed",
        "colors": ("wizard", "warrior", "ninja", "neutral"),
        "count": REWARD_CARD_COUNT,
        "weighted": True,
    },
    "word_wall": {
        "early_rarities": ("rare",),
        "late_rarities": ("rare",),
        "color_mode": "player_and_neutral",
        "count": 1,
        "weighted": True,
        "fallback_all_colors": True,
    },
}
