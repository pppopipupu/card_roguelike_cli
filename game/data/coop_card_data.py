COOP_CARD_CONFIG = {
    "coop_tactical_command": {
        "name": "战术指挥",
        "color": "neutral",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "common",
        "coop_only": True,
        "desc": "指定一名队友，使其立即获得 1A 与 1BA，并抽 1 张牌。"
    },
    "coop_phalanx_bulwark": {
        "name": "方阵掩护",
        "color": "neutral",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "common",
        "coop_only": True,
        "desc": "你与指定队友各获得 8 点护盾；本回合该队友获得 1 层【援护】（受到的单体攻击伤害降低 25%）。"
    },
    "coop_resonance_hymn": {
        "name": "共鸣圣歌",
        "color": "neutral",
        "type": "spell",
        "cost_a": 0,
        "cost_ba": 1,
        "rarity": "rare",
        "coop_only": True,
        "desc": "为指定队友付与 2 层【力量】与 1 层【奥术充能】（法术伤害 +3）。"
    },
    "coop_soul_link": {
        "name": "灵魂链接",
        "color": "neutral",
        "type": "ability",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "coop_only": True,
        "desc": "为指定队友恢复 6 点生命值，并赋予 2 层【灵魂共鸣】（该队友下 2 次打出的攻击或法术牌伤害额外 +4，且每次触发为你恢复 2 点生命）。"
    },
    "coop_unison_crusade": {
        "name": "同心协力",
        "color": "neutral",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 1,
        "rarity": "epic",
        "coop_only": True,
        "exhaust": True,
        "damage_type": "force",
        "base_dmg": 8,
        "desc": "全体存活队友各抽 1 张牌并获得 1BA。对目标敌人造成等同于（存活玩家总数 × 8）点力场伤害，并施加等同于存活玩家总数的【全属性轻度易伤】。消耗。"
    },
}

COOP_UPGRADE_CONFIG = {
    "coop_tactical_command": {
        "desc": "指定一名队友，使其立即获得 1A 与 2BA，且你与该队友各抽 1 张牌。"
    },
    "coop_phalanx_bulwark": {
        "desc": "你与全体存活队友各获得 10 点护盾；本回合指定队友获得 1 层【援护】。"
    },
    "coop_resonance_hymn": {
        "desc": "为全体队友（含自身）付与 2 层【力量】与 1 层【奥术充能】，并抽 1 张牌。"
    },
    "coop_soul_link": {
        "cost_a": 0,
        "cost_ba": 1,
        "desc": "为指定队友恢复 9 点生命值，并赋予 3 层【灵魂共鸣】（该队友下 3 次打出的攻击或法术牌伤害额外 +6，且每次触发为你恢复 3 点生命）。"
    },
    "coop_unison_crusade": {
        "desc": "全体存活队友各抽 2 张牌并获得 1A。对目标敌人造成等同于（存活玩家总数 × 12）点力场伤害，并施加等同于存活玩家总数的【全属性易伤】。消耗。"
    },
}
