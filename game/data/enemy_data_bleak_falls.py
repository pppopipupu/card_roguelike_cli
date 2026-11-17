BLEAK_DRAUGR_SUMMON_NAME = "古诺德尸鬼"

ENEMY_BLEAK_FALLS_CONFIG = {
    "荒爆强盗": {
        "name": "荒爆强盗",
        "size": "medium",
        "type": "normal",
        "hp": "24",
        "actions": "1A 1BA",
        "intents": [
            {"id": "bandit_slash", "val": 7, "desc": "战斧劈砍 (造成 7 点挥砍伤害)"},
            {"id": "bandit_throw", "val": 5, "desc": "生锈飞斧 (造成 5 点穿刺伤害)"},
            {"id": "bandit_shield", "val": 6, "desc": "木盾格挡 (获得 6 点护盾)"}
        ]
    },
    "强盗掠夺者": {
        "name": "强盗掠夺者",
        "size": "medium",
        "type": "normal",
        "hp": "28",
        "actions": "1A 1BA",
        "intents": [
            {"id": "bandit_slash", "val": 8, "desc": "凶狠重劈 (造成 8 点挥砍伤害)"},
            {"id": "bandit_warcry", "val": 1, "desc": "掠夺战吼 (敌方全体获得 1 层力量)"},
            {"id": "bandit_shield", "val": 7, "desc": "举盾戒备 (获得 7 点护盾)"}
        ]
    },
    "巨型冰霜蜘蛛": {
        "name": "巨型冰霜蜘蛛",
        "size": "large",
        "type": "elite",
        "hp": "48",
        "actions": "1A 1BA",
        "passive": "冻霜蛰伏 (攻击附加轻度寒冷易伤，会喷吐冰丝限制附赠动作)",
        "intents": [
            {"id": "spider_bite", "val": 8, "desc": "寒毒螯咬 (造成 8 点寒冷伤害并施加 1 层轻度寒冷易伤)"},
            {"id": "spider_web", "val": 5, "desc": "冰丝缠缚 (造成 5 点寒冷伤害并使玩家下回合失去 1BA)"},
            {"id": "spider_cocoon", "val": 8, "desc": "霜甲结茧 (获得 8 点护盾并回复 4 点生命)"}
        ]
    },
    "敏捷的阿尔维尔": {
        "name": "敏捷的阿尔维尔",
        "size": "medium",
        "type": "normal",
        "hp": "30",
        "actions": "1A 1BA",
        "intents": [
            {"id": "arvel_backstab", "val": 9, "desc": "偷袭背刺 (造成 9 点穿刺伤害)"},
            {"id": "arvel_smoke", "val": 8, "desc": "烟雾脱身 (获得 8 点护盾并获得 1 层力量)"},
            {"id": "bandit_throw", "val": 6, "desc": "投掷淬毒匕首 (造成 6 点穿刺伤害)"}
        ]
    },
    "古诺德尸鬼": {
        "name": "古诺德尸鬼",
        "size": "medium",
        "type": "normal",
        "hp": "26",
        "actions": "1A 1BA",
        "intents": [
            {"id": "draugr_cleave", "val": 7, "desc": "古诺德斩击 (造成 7 点挥砍伤害)"},
            {"id": "draugr_frost", "val": 5, "desc": "残缺寒息 (造成 5 点寒冷伤害)"},
            {"id": "draugr_armor", "val": 6, "desc": "古墓护甲 (获得 6 点护盾)"}
        ]
    },
    "尸鬼幽魂": {
        "name": "尸鬼幽魂",
        "size": "medium",
        "type": "normal",
        "hp": "22",
        "actions": "1A 1BA",
        "intents": [
            {"id": "wraith_drain", "val": 6, "desc": "寒灵汲取 (造成 6 点亡灵伤害并回复 3 点生命)"},
            {"id": "wraith_chant", "val": 5, "desc": "葬礼低吟 (全敌获得 5 点护盾与 1 层力量)"},
            {"id": "draugr_frost", "val": 5, "desc": "霜灵吐息 (造成 5 点寒冷伤害)"}
        ]
    },
    "尸鬼领主·米洛克": {
        "name": "尸鬼领主·米洛克",
        "size": "large",
        "type": "boss",
        "hp": "95",
        "actions": "2A 1BA",
        "passive": "古墓领主威仪 (精通残缺龙吼，会唤醒墓室内的古诺德尸鬼协助守卫龙石)",
        "intents": [
            {"id": "overlord_shout", "val": 10, "desc": "龙吼残响 (造成 10 点力场伤害并使玩家下回合失去 1A)"},
            {"id": "draugr_cleave", "val": 9, "desc": "领主重斩 (造成 9 点挥砍伤害)"},
            {"id": "draugr_armor", "val": 12, "desc": "古诺德战铠 (获得 12 点护盾)"},
            {"id": "overlord_summon", "val": 0, "desc": "唤醒棺椁 (召唤 1 名古诺德尸鬼加入战场)"}
        ]
    }
}
