AMULET_CONFIG = {
    "energy_core": {
        "name": "能量核心",
        "countdown": 1,
        "desc": "谢幕曲：你获得 1A 1BA。",
        "actions": 1,
        "upgraded_actions": 2,
        "bonus_actions": 1,
        "token": True
    },
    "energy_core+": {
        "name": "能量核心+",
        "countdown": 1,
        "desc": "谢幕曲：你获得 2A 1BA。",
        "actions": 2,
        "bonus_actions": 1,
        "token": True
    },
    "lucky_coin": {
        "name": "幸运金币",
        "countdown": 3,
        "desc": "每回合结束时，你获得 3 金币。",
        "gold_on_end": 3,
        "upgraded_gold_on_end": 4,
        "upgraded_draw_on_end": 1,
        "gold_on_death": 10,
        "upgraded_gold_on_death": 15,
        "upgraded_draw_on_death": 1
    },
    "thorns_necklace": {
        "name": "荆棘项链",
        "countdown": 2,
        "desc": "受到伤害时，向伤害源反弹 2 点伤害。",
        "damage_on_hit": 2,
        "upgraded_damage_on_hit": 4,
        "upgraded_shield_on_hit": 1,
        "death_damage": 4,
        "upgraded_death_damage": 4
    },
    "ring_of_elements": {
        "name": "元素指环",
        "countdown": 4,
        "desc": "火焰伤害 +2",
        "fire_dmg_bonus": 2,
        "upgraded_fire_dmg_bonus": 3,
        "death_damage": 4,
        "upgraded_death_damage": 8
    },
    "void_beacon": {
        "name": "虚空信标",
        "countdown": 2,
        "desc": "每回合开始时，对所有敌人施加 1 层易伤，并对随机敌人造成 5 点力场伤害。",
        "damage": 5,
        "upgraded_damage": 8,
        "vulnerable_stacks": 1
    },
    "arcane_crystal": {
        "name": "奥术水晶",
        "countdown": 3,
        "desc": "每使用一张法术牌回复 2 点生命值",
        "heal_on_spell": 2,
        "upgraded_heal_on_spell": 3,
        "upgraded_shield_on_spell": 2,
        "heal_on_death": 4,
        "upgraded_heal_on_death": 8
    },
    "mage_ward": {
        "name": "法师护盾",
        "countdown": 3,
        "desc": "你的回合结束时获得 4 点护盾",
        "shield_on_end": 4,
        "upgraded_shield_on_end": 6,
        "upgraded_countdown_refund": 1,
        "shield_on_death": 5,
        "upgraded_shield_on_death": 10
    },
    "abyss_altar": {
        "name": "深渊祭坛",
        "countdown": 1,
        "desc": "谢幕曲：召唤【苏醒的深渊祭坛】。"
    },
    "abyss_altar_awaken": {
        "name": "苏醒的深渊祭坛",
        "countdown": 1,
        "desc": "谢幕曲：召唤【汇集的深渊祭坛】。",
        "token": True
    },
    "abyss_altar_converge": {
        "name": "汇集的深渊祭坛",
        "countdown": 1,
        "desc": "谢幕曲：召唤【爆发的深渊祭坛】。",
        "token": True
    },
    "abyss_altar_burst": {
        "name": "爆发的深渊祭坛",
        "countdown": 1,
        "desc": "谢幕曲：召唤【终结的深渊祭坛】。",
        "token": True
    },
    "abyss_altar_end": {
        "name": "终结的深渊祭坛",
        "countdown": 1,
        "desc": "谢幕曲对场上所有敌人造成 500 点真实伤害，你受到 10 点真实伤害。",
        "enemy_damage": 500,
        "upgraded_enemy_damage": 600,
        "player_damage": 10,
        "upgraded_player_damage": 5,
        "token": True
    },
    "tactical_barrack": {
        "name": "战术兵营",
        "countdown": 3,
        "desc": "回合开始时若协作达到 5 以上召唤【步兵轻卒】。",
        "shield_on_death": 4,
        "upgraded_shield_on_death": 8,
        "max_hand": 12
    },
    "iron_phalanx_seal": {
        "name": "铁阵方盟",
        "countdown": 3,
        "desc": "我方士兵随从进场时你获得 3 护盾，且随从最大生命值 +2 获得 1 层缓冲。",
        "max_hp_bonus": 3,
        "upgraded_max_hp_bonus": 4,
        "shield_bonus": 3,
        "upgraded_shield_bonus": 4
    },
    "grand_coronation": {
        "name": "辉光加冕仪式",
        "countdown": 2,
        "desc": "打出指挥官随从牌时我方其他随从本回合攻击 +2 且抽 1 张牌。",
        "atk_bonus": 2,
        "upgraded_atk_bonus": 4,
        "hp_gain": 4,
        "upgraded_hp_gain": 8
    },
    "blade_regiment_banner": {
        "name": "白刃军团战旗",
        "countdown": 4,
        "desc": "我方随从或你造成的物理伤害额外增加 3 点。",
        "physical_damage_bonus": 3,
        "upgraded_physical_damage_bonus": 5,
        "death_damage": 6,
        "upgraded_death_damage": 10,
        "death_heal": 6,
        "upgraded_death_heal": 10
    }
}
