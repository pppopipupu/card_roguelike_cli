ULTIMATE_PRISM_CARD_ID = "ultimate_prism"
ULTIMATE_PRISM_MERC_ID = "ultimate_prism"
GLASS_SHARD_ITEM_ID = "glass_shard"
BLIND_BUFF_ID = "blind"
ULTIMATE_PRISM_ACHIEVEMENT_ID = "ultimate_prism_awakened"

ULTIMATE_PRISM_FLAG_UNLOCKED = "ultimate_prism_unlocked"
ULTIMATE_PRISM_FLAG_DEPARTED = "ultimate_prism_departed"
ULTIMATE_PRISM_FLAG_IDLE_BATTLES = "ultimate_prism_idle_battles"
CHIREIDEN_QUEST_COMPLETED_FLAG = "chireiden_quest_completed"

ULTIMATE_PRISM_CONFIG = {
    "cost_a": 999,
    "cost_ba": 0,
    "refract_count": 5,
    "stun_turns": 2,
    "radiant_damage": 666,
    "yog_radiant_damage": 17320508075688772,
    "blind_turns": 1,
    "echo_cost_reduction": 10,
    "replay_cost_reduction": 15,
    "prism_cost_reduction": 20,
    "idle_leave_battles": 5,
    "unlock_price_gp": 7891,
    "relock_price_gp": 666,
    "merc_hp": 120,
    "merc_beam_damage": 18,
    "merc_ward_shield": 14,
    "merc_facet_draw": 2,
    "merc_facet_damage": 10,
}

ULTIMATE_PRISM_YOG_MARKERS = ("尤格-索托斯", "尤格索托斯")

ULTIMATE_PRISM_CARD_CONFIG = {
    "ultimate_prism": {
        "name": "终极棱镜",
        "color": "neutral",
        "type": "spell",
        "cost_a": ULTIMATE_PRISM_CONFIG["cost_a"],
        "cost_ba": ULTIMATE_PRISM_CONFIG["cost_ba"],
        "rarity": "artifact",
        "exhaust": True,
        "eternal": True,
        "event_only": True,
        "sentient": True,
        "cant_upgrade": True,
        "target_type": "all_enemies",
        "damage_type": "radiant",
        "base_dmg": ULTIMATE_PRISM_CONFIG["radiant_damage"],
        "stun_turns": ULTIMATE_PRISM_CONFIG["stun_turns"],
        "desc": "当打出与此牌序号相邻的卡牌时，免费自动打出另一张序号相邻的卡牌 5 次并消耗。打出时眩晕全体敌人 2 回合，剥夺全体敌人的所有正面状态，对全体敌人造成 666 点光耀伤害；若敌人为尤格索托斯，则改为造成 17320508075688772 点光耀伤害，并使你获得 1 回合【盲目】。位于手牌中时，每触发一次回响费用降低 10A，每触发一次重放费用降低 15A，每触发一次棱镜折射效果费用降低 20A。永恒。消耗。",
        "lore_key": "i18n_prism.card.lore",
    },
    "prism_refraction_beam": {
        "name": "终极折射束",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "epic",
        "event_only": True,
        "token": True,
        "target_type": "all_enemies",
        "damage_type": "radiant",
        "base_dmg": ULTIMATE_PRISM_CONFIG["merc_beam_damage"],
        "desc": "向全体敌人倾泻多面折射光束，造成 18 点光耀伤害。",
    },
    "prism_mirror_ward": {
        "name": "晶面光幕",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 0,
        "cost_ba": 1,
        "rarity": "rare",
        "event_only": True,
        "token": True,
        "target_type": "self",
        "shield_amount": ULTIMATE_PRISM_CONFIG["merc_ward_shield"],
        "desc": "展开折射晶幕，使自身与雇主各获得 14 点护盾。",
    },
    "prism_resonant_facet": {
        "name": "棱面共鸣",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "event_only": True,
        "token": True,
        "target_type": "enemy",
        "damage_type": "radiant",
        "base_dmg": ULTIMATE_PRISM_CONFIG["merc_facet_damage"],
        "draw_count": ULTIMATE_PRISM_CONFIG["merc_facet_draw"],
        "desc": "对目标敌人造成 10 点光耀伤害并抽 2 张牌。",
    },
}

GLASS_SHARD_ITEM_CONFIG = {
    GLASS_SHARD_ITEM_ID: {
        "name_key": "i18n_prism.glass_shard.name",
        "desc_key": "i18n_prism.glass_shard.desc",
        "rarity": "common",
        "weight": 0,
        "carryover": True,
        "usable": True,
        "aliases": ["玻璃碎块", "碎玻璃", "棱镜碎片", "glass_shard", "shard"],
    },
}

GLASS_SHARD_LORE_CONFIG = {
    GLASS_SHARD_ITEM_ID: {
        "intro_key": "i18n_prism.glass_shard.lore",
    },
}

PRISM_TALK_PREFIXES = ("card", "卡牌", "牌", "c")
