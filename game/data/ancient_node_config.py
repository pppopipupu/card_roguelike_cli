ANCIENT_STYLE_CHOICES = {
    "战士": ["default", "abyss"],
    "default": ["default", "abyss", "glacier"],
}

ANCIENT_BLESSING_POOLS = {
    "战士": {
        "default": {
            "legends": ["demon_form", "impervious"],
            "relics": ["ancient_eye", "gold_compass", "dragon_blood", "energy_core", "heavy_armor"],
        },
        "abyss": {
            "legends": ["abyss_collapse", "demon_contract", "abyss_erosion", "abyss_altar"],
            "relics": ["abyss_whisper", "gold_compass", "dragon_blood", "abyss_contract"],
        },
    },
    "default": {
        "default": {
            "legends": ["doomsday_judgment", "time_warp", "magic_network", "meteor_swarm", "archmage_wish"],
            "relics": ["ancient_eye", "gold_compass", "dragon_blood", "energy_core", "heavy_armor"],
        },
        "abyss": {
            "legends": ["abyss_collapse", "demon_contract", "abyss_erosion", "abyss_altar"],
            "relics": ["abyss_whisper", "gold_compass", "dragon_blood", "abyss_contract"],
        },
        "glacier": {
            "legends": ["frost_nova", "glacier_fortress", "glacier_tempest"],
            "relics": ["frost_blade", "energy_core", "heavy_armor", "glacier_core"],
        },
    },
}

ANCIENT_LEGEND_APPENDS = ["break_limits", "unmined_gem"]

ANCIENT_ICERAINBOWW_LEGEND = "minion_icerainboww"

ANCIENT_REWARD_OPTION_TYPE = "blessing"
