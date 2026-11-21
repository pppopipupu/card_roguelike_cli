ITEM_LORE = {
    "espresso_beans": {
        "intro_key": "i18n_item_lore.items.espresso_beans.intro",
    },
    "rusty_pickaxe": {
        "intro_key": "i18n_item_lore.items.rusty_pickaxe.intro",
        "secret": {
            "reveal": "boss_yog_sothoth",
            "hint_key": "i18n_item_lore.items.rusty_pickaxe.hint",
            "reveal_key": "i18n_item_lore.items.rusty_pickaxe.secret",
        },
    },
    "glowing_runestone": {
        "intro_key": "i18n_item_lore.items.glowing_runestone.intro",
        "secret": {
            "reveal": "boss_yog_sothoth",
            "hint_key": "i18n_item_lore.items.glowing_runestone.hint",
            "reveal_key": "i18n_item_lore.items.glowing_runestone.secret",
        },
    },
    "field_bandage": {
        "intro_key": "i18n_item_lore.items.field_bandage.intro",
    },
    "ancient_notes": {
        "intro_key": "i18n_item_lore.items.ancient_notes.intro",
        "secret": {
            "reveal": "abyss_secret_clue",
            "hint_key": "i18n_item_lore.items.ancient_notes.hint",
            "reveal_key": "i18n_item_lore.items.ancient_notes.secret",
        },
    },
    "skeleton_key": {
        "intro_key": "i18n_item_lore.items.skeleton_key.intro",
    },
    "sugar_cube_pack": {
        "intro_key": "i18n_item_lore.items.sugar_cube_pack.intro",
    },
    "smuggler_token": {
        "intro_key": "i18n_item_lore.items.smuggler_token.intro",
        "secret": {
            "reveal": "boss_yog_sothoth",
            "hint_key": "i18n_item_lore.items.smuggler_token.hint",
            "reveal_key": "i18n_item_lore.items.smuggler_token.secret",
        },
    },
    "merchant_ledger": {
        "intro_key": "i18n_item_lore.items.merchant_ledger.intro",
        "secret": {
            "reveal": "boss_yog_sothoth",
            "hint_key": "i18n_item_lore.items.merchant_ledger.hint",
            "reveal_key": "i18n_item_lore.items.merchant_ledger.secret",
        },
    },
    "barista_seal": {
        "intro_key": "i18n_item_lore.items.barista_seal.intro",
        "hidden": "boss_yog_sothoth",
    },
    "qgp_bomb": {
        "intro_key": "i18n_bleak_falls.lore.qgp_bomb_lore",
    },
    "golden_claw": {
        "intro_key": "i18n_bleak_falls.lore.golden_claw_lore",
    },
    "dragonstone": {
        "intro_key": "i18n_bleak_falls.lore.dragonstone_lore",
    },
    "arvel_journal": {
        "intro_key": "i18n_bleak_falls.lore.arvel_journal_lore",
    },
    "nordic_mead": {
        "intro_key": "i18n_bleak_falls.lore.nordic_mead_lore",
    },
    "survey_chart": {
        "intro_key": "i18n_bleak_falls.lore.survey_chart_lore",
    },
}

from .chireiden_data import CHIREIDEN_LORE
from .ultimate_prism_data import GLASS_SHARD_LORE_CONFIG

ITEM_LORE.update(CHIREIDEN_LORE)
ITEM_LORE.update(GLASS_SHARD_LORE_CONFIG)
