ANCIENT_DEITIES = {
    "default": {
        "style_key": "i18n_renderer_extra.map.style_default",
        "name_key": "i18n_renderer_extra.map.deity_default_name",
        "title_key": "i18n_renderer_extra.map.deity_default_title",
        "desc_key": "i18n_renderer_extra.map.deity_default_desc",
    },
    "abyss": {
        "style_key": "i18n_renderer_extra.map.style_abyss",
        "name_key": "i18n_renderer_extra.map.deity_abyss_name",
        "title_key": "i18n_renderer_extra.map.deity_abyss_title",
        "desc_key": "i18n_renderer_extra.map.deity_abyss_desc",
    },
    "glacier": {
        "style_key": "i18n_renderer_extra.map.style_glacier",
        "name_key": "i18n_renderer_extra.map.deity_glacier_name",
        "title_key": "i18n_renderer_extra.map.deity_glacier_title",
        "desc_key": "i18n_renderer_extra.map.deity_glacier_desc",
    },
    "warforge": {
        "style_key": "i18n_renderer_extra.map.style_warforge",
        "name_key": "i18n_renderer_extra.map.deity_warforge_name",
        "title_key": "i18n_renderer_extra.map.deity_warforge_title",
        "desc_key": "i18n_renderer_extra.map.deity_warforge_desc",
    },
    "fortune": {
        "style_key": "i18n_renderer_extra.map.style_fortune",
        "name_key": "i18n_renderer_extra.map.deity_fortune_name",
        "title_key": "i18n_renderer_extra.map.deity_fortune_title",
        "desc_key": "i18n_renderer_extra.map.deity_fortune_desc",
    },
}

ANCIENT_STYLE_CHOICES = {
    "战士": ["default", "abyss", "glacier", "warforge", "fortune"],
    "蕾忍": ["default", "abyss", "glacier", "warforge", "fortune"],
    "default": ["default", "abyss", "glacier", "warforge", "fortune"],
}

ANCIENT_CLASS_LEGENDS = {
    "战士": ["demon_form", "impervious", "neutral_astral_strike", "neutral_banish_slash"],
    "蕾忍": [
        "ninja_shen_wei",
        "ninja_radiation_annihilation",
        "ninja_power_jesus",
        "ninja_oh_fuck_flash",
        "ninja_take_your_heart",
    ],
    "default": ["doomsday_judgment", "time_warp", "magic_network", "meteor_swarm", "archmage_wish"],
}

ANCIENT_START_POOLS = {
    "default": {
        "relics": ["ancient_page", "mask_of_void", "unstable_crystal", "vampiric_touch", "mark_of_fury", "trash_mountain"],
        "curse_relics": ["rust_shackle", "blind_spot", "fool_oath", "tax_contract"],
        "legends": ["doomsday_judgment", "time_warp", "magic_network", "meteor_swarm", "archmage_wish"],
    },
    "abyss": {
        "relics": ["abyss_gaze", "abyss_contract", "vampiric_touch", "crimson_heart", "abyss_whisper"],
        "curse_relics": ["shadow_curse", "wither_seed", "rust_shackle"],
        "legends": ["abyss_collapse", "demon_contract", "abyss_erosion", "abyss_altar"],
    },
    "glacier": {
        "relics": ["glacier_armor", "frost_blade", "glacier_core", "heavy_armor", "shield_battery"],
        "curse_relics": ["glacier_chill", "blind_spot", "rust_shackle"],
        "legends": ["frost_nova", "glacier_fortress", "glacier_tempest"],
    },
    "warforge": {
        "relics": ["mark_of_fury", "vampiric_touch", "heavy_armor", "gladiator_belt", "unstable_crystal"],
        "curse_relics": ["rust_shackle", "fool_oath", "wither_seed"],
        "legends": ["demon_form", "impervious", "neutral_astral_strike", "neutral_banish_slash"],
    },
    "fortune": {
        "relics": ["greedy_contract", "chemical_x", "prayer_wheel", "mask_of_void", "trash_mountain"],
        "curse_relics": ["tax_contract", "blind_spot", "rust_shackle"],
        "legends": ["archmage_wish", "time_warp", "unmined_gem", "break_limits", "neutral_banish_slash"],
    },
}

ANCIENT_BLESSING_POOLS = {
    "default": {
        "legends": ["doomsday_judgment", "time_warp", "magic_network", "meteor_swarm", "archmage_wish"],
        "relics": ["ancient_eye", "energy_core", "portal_fragment", "ancient_sigil", "ancient_compass", "void_lens", "ancient_keyring"],
    },
    "abyss": {
        "legends": ["abyss_collapse", "demon_contract", "abyss_erosion", "abyss_altar"],
        "relics": ["abyss_whisper", "abyss_contract", "abyss_gaze", "necromancer_skull", "stalker_eye", "star_vampire_proboscis"],
    },
    "glacier": {
        "legends": ["frost_nova", "glacier_fortress", "glacier_tempest"],
        "relics": ["frost_blade", "glacier_core", "glacier_armor", "heavy_armor", "shield_battery", "energy_core"],
    },
    "warforge": {
        "legends": ["demon_form", "impervious", "neutral_astral_strike", "neutral_banish_slash"],
        "relics": ["dragon_blood", "heavy_armor", "energy_core", "mark_of_fury", "commander_medal", "gladiator_belt", "centurion_mail"],
    },
    "fortune": {
        "legends": ["archmage_wish", "time_warp", "unmined_gem", "break_limits", "neutral_banish_slash"],
        "relics": ["gold_compass", "chemical_x", "prayer_wheel", "ancient_eye", "doomsday_core", "arcanist_hand", "espresso_relic"],
    },
}

ANCIENT_LEGEND_APPENDS = ["break_limits", "unmined_gem"]

ANCIENT_ICERAINBOWW_LEGEND = "minion_icerainboww"

ANCIENT_REWARD_OPTION_TYPE = "blessing"
