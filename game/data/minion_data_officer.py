MINION_OFFICER_CONFIG = {
    "officer_recruit_vanguard": {
        "name": "新兵前锋",
        "rally_threshold": 6,
        "atk_buff": 2,
        "skills": []
    },
    "officer_recruit_vanguard+": {
        "name": "新兵前锋+",
        "rally_threshold": 6,
        "atk_buff": 4,
        "shield": 2,
        "skills": []
    },
    "officer_banner_bearer": {
        "name": "执旗辅佐官",
        "max_count": 1,
        "attack_actions": 1,
        "atk_buff": 2,
        "skills": [
            {
                "id": "banner_buff",
                "name": "执旗振奋",
                "cost_a": 1,
                "cost_ba": 0,
                "desc": "消耗 1A，本回合使我方另一个随从攻击力 +2。",
                "atk_buff": 2,
                "feedback": "使我方另一个随从本回合攻击力提升了 2 点。"
            }
        ]
    },
    "officer_banner_bearer+": {
        "name": "执旗辅佐官+",
        "max_count": 1,
        "attack_actions": 1,
        "atk_buff": 3,
        "shield": 3,
        "skills": [
            {
                "id": "banner_buff",
                "name": "执旗振奋+",
                "cost_a": 1,
                "cost_ba": 0,
                "desc": "消耗 1A，本回合使我方另一个随从攻击力 +3，且自身获得 3 护盾。",
                "atk_buff": 3,
                "heal": 3,
                "feedback": "使我方另一个随从本回合攻击力提升了 3 点，且自身获得 3 护盾。"
            }
        ]
    },
    "commander_patrol_captain": {
        "name": "巡逻队队长",
        "token_hp": 3,
        "token_atk": 1,
        "skills": [
            {
                "id": "patrol_order",
                "name": "巡逻指令",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，为我方所有随从恢复 3 点生命值，并获得 3 点护盾。",
                "heal": 3,
                "shield": 3,
                "feedback": "发布巡逻指令，为我方所有随从恢复了 3 生命并提供了 3 点护盾。"
            }
        ]
    },
    "commander_patrol_captain+": {
        "name": "巡逻队队长+",
        "token_hp": 3,
        "token_atk": 1,
        "skills": [
            {
                "id": "patrol_order",
                "name": "巡逻指令+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，为我方所有随从恢复 5 点生命值，并获得 5 点护盾。",
                "heal": 5,
                "shield": 5,
                "feedback": "发布巡逻指令+，为我方所有随从恢复了 5 生命并提供了 5 点护盾。"
            }
        ]
    },
    "officer_royal_guard": {
        "name": "近卫铁骑",
        "atk_buff": 1,
        "damage": 2,
        "skills": []
    },
    "officer_royal_guard+": {
        "name": "近卫铁骑+",
        "atk_buff": 2,
        "damage": 3,
        "skills": []
    },
    "commander_garrison_leader": {
        "name": "要塞卫队长",
        "shield": 3,
        "skills": [
            {
                "id": "garrison_wall",
                "name": "要塞铁壁",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，为玩家提供 6 护盾，若有士兵则使其回复 3 生命。",
                "shield": 6,
                "heal": 3,
                "feedback": "为玩家提供了 6 点护盾，并为士兵随从回复了 3 生命值。"
            }
        ]
    },
    "commander_garrison_leader+": {
        "name": "要塞卫队长+",
        "shield": 5,
        "skills": [
            {
                "id": "garrison_wall",
                "name": "要塞铁壁+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，为玩家提供 9 护盾，若有士兵则使其回复 5 生命。",
                "shield": 9,
                "heal": 5,
                "feedback": "为玩家提供了 9 点护盾，并为士兵随从回复了 5 生命值。"
            }
        ]
    },
    "officer_squad_skirmisher": {
        "name": "突击轻步兵",
        "atk_buff": 2,
        "vulnerable_layers": 1,
        "skills": []
    },
    "officer_squad_skirmisher+": {
        "name": "突击轻步兵+",
        "atk_buff": 3,
        "vulnerable_layers": 1,
        "attack_actions": 2,
        "skills": []
    },
    "commander_valiant_herald": {
        "name": "英勇传令官",
        "skills": [
            {
                "id": "charge_signal",
                "name": "冲锋信号",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，使我方全体随从本回合攻击力 +2。",
                "atk_buff": 2,
                "feedback": "发出冲锋信号，我方全体随从本回合攻击力 +2。"
            }
        ]
    },
    "commander_valiant_herald+": {
        "name": "英勇传令官+",
        "skills": [
            {
                "id": "charge_signal",
                "name": "冲锋信号+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，使我方全体随从本回合攻击力 +3。",
                "atk_buff": 3,
                "feedback": "发出冲锋信号+，我方全体随从本回合攻击力 +3。"
            }
        ]
    },
    "commander_steelclad_tactician": {
        "name": "重甲战术家",
        "rally_threshold": 10,
        "coef": 1,
        "token_hp": 3,
        "token_atk": 1,
        "skills": [
            {
                "id": "tactical_strike",
                "name": "战术压制",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，造成 6 钝击伤害，斩杀时召唤两个【步兵轻卒】。",
                "damage": 6,
                "summon_count": 2,
                "feedback": "执行战术压制对【{target}】造成了 6 点伤害。"
            }
        ]
    },
    "commander_steelclad_tactician+": {
        "name": "重甲战术家+",
        "rally_threshold": 10,
        "coef": 2,
        "token_hp": 4,
        "token_atk": 2,
        "skills": [
            {
                "id": "tactical_strike",
                "name": "战术压制+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，造成 9 钝击伤害，斩杀时召唤两个【步兵轻卒+】。",
                "damage": 9,
                "summon_count": 2,
                "feedback": "执行战术压制+对【{target}】造成了 9 点伤害。"
            }
        ]
    },
    "officer_blade_dancer": {
        "name": "双刃轻卫",
        "coef": 1.5,
        "skills": [
            {
                "id": "double_slash",
                "name": "双重斩击",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，造成两次 4 点伤害。",
                "damage": 4,
                "hits": 2,
                "feedback": "对【{target}】发动双重斩击！"
            }
        ]
    },
    "officer_blade_dancer+": {
        "name": "双刃轻卫+",
        "coef": 2.0,
        "skills": [
            {
                "id": "double_slash",
                "name": "双重斩击+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，造成两次 6 点伤害。",
                "damage": 6,
                "hits": 2,
                "feedback": "对【{target}】发动双重斩击+！"
            }
        ]
    },
    "commander_aurora_emperor": {
        "name": "极光圣帝·阿奎斯",
        "skills": [
            {
                "id": "aurora_judgment",
                "name": "极光审判",
                "cost_a": 3,
                "cost_ba": 0,
                "desc": "消耗 3A，对所有敌人造成 8 点光耀伤害，若协作达到 15 以上，则转为 15 点真伤。",
                "damage": 8,
                "damage_high": 15,
                "rally_threshold": 15,
                "feedback": "降下极光审判净化敌方全体！"
            }
        ]
    },
    "commander_aurora_emperor+": {
        "name": "极光圣帝·阿奎斯+",
        "skills": [
            {
                "id": "aurora_judgment",
                "name": "极光审判+",
                "cost_a": 3,
                "cost_ba": 0,
                "desc": "消耗 3A，对所有敌人造成 12 点光耀伤害，若协作达到 15 以上，则转为 22 点真伤。",
                "damage": 12,
                "damage_high": 22,
                "rally_threshold": 15,
                "feedback": "降下极光审判+净化敌方全体！"
            }
        ]
    },
    "officer_soldier_token": {
        "name": "步兵轻卒",
        "hp": 3,
        "atk": 1,
        "skills": []
    },
    "officer_soldier_token+": {
        "name": "步兵轻卒+",
        "hp": 4,
        "atk": 2,
        "skills": []
    }
}
