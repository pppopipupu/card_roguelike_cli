PLAYER_NAME_MAX_LENGTH = 16
IM_ACCOUNT_MAX_LENGTH = 40
FRIEND_SEARCH_LIMIT = 10
LOBBY_ID_LENGTH = 6
TEAM_MIN_PLAYERS = 2
TEAM_MAX_MEMBERS = 4
DEFAULT_PLAYER_NAME = "玩家"
DEFAULT_CLASS_NAME = "法师"
CHECKIN_STAMPS_PER_CLAIM = 1
CHECKIN_STAMP_REQUIRED_FALLBACK = 1

DAILY_BLESSINGS = {
    "life_domain": {
        "name": "生命领域",
        "desc": "下一局最大生命 +8，并回复 8 点生命。",
        "effects": [{"type": "max_hp", "value": 8}]
    },
    "guard_domain": {
        "name": "守护领域",
        "desc": "下一局每场战斗开始时获得 10 点护盾。",
        "effects": [{"type": "battle_shield", "value": 10}]
    },
    "action_domain": {
        "name": "动作领域",
        "desc": "下一局每场战斗开始时获得 1A。",
        "effects": [{"type": "battle_actions", "value": 1}]
    },
    "bonus_domain": {
        "name": "附赠领域",
        "desc": "下一局每场战斗开始时获得 1BA。",
        "effects": [{"type": "battle_bonus_actions", "value": 1}]
    },
    "draw_domain": {
        "name": "抽牌领域",
        "desc": "下一局每场战斗开始时额外抽 2 张牌。",
        "effects": [{"type": "battle_draw", "value": 2}]
    },
    "strength_domain": {
        "name": "力量领域",
        "desc": "下一局每场战斗开始时获得 2 层力量。",
        "effects": [{"type": "battle_buff", "buff_id": "strength", "buff_name": "力量", "buff_desc": "造成的伤害增加", "stacks": 2}]
    },
    "arcane_domain": {
        "name": "奥术领域",
        "desc": "下一局每场战斗开始时获得 2 层奥术充能。",
        "effects": [{"type": "battle_buff", "buff_id": "arcane_charge", "buff_name": "奥术充能", "buff_desc": "法术伤害 +3", "stacks": 2}]
    },
    "flame_domain": {
        "name": "火焰领域",
        "desc": "下一局你造成的火焰伤害 +4。",
        "effects": [{"type": "damage_type_bonus", "damage_type": "fire", "value": 4}]
    },
    "piercing_domain": {
        "name": "穿刺领域",
        "desc": "下一局你造成的穿刺伤害 +4。",
        "effects": [{"type": "damage_type_bonus", "damage_type": "piercing", "value": 4}]
    },
    "summon_domain": {
        "name": "召唤领域",
        "desc": "下一局初始牌组加入一张随机稀有随从牌。",
        "effects": [{"type": "add_random_card", "filter": "rare_minion"}]
    },
    "wealth_domain": {
        "name": "财富领域",
        "desc": "下一局开局获得 80 金币。",
        "effects": [{"type": "gold", "value": 80}]
    },
    "rare_domain": {
        "name": "卡牌领域",
        "desc": "下一局初始牌组加入一张随机稀有卡牌。",
        "effects": [{"type": "add_random_card", "filter": "rare"}]
    },
    "forge_domain": {
        "name": "锻造领域",
        "desc": "下一局初始牌组中随机一张牌升级。",
        "effects": [{"type": "upgrade_random"}]
    },
    "exhaust_domain": {
        "name": "消耗领域",
        "desc": "下一局每场战斗第一次打出消耗牌时，抽 1 张牌并获得 1A。",
        "effects": [{"type": "first_exhaust_draw", "draw": 1, "actions": 1}]
    },
    "strike_domain": {
        "name": "打击领域",
        "desc": "下一局所有名称含【打击】的卡牌伤害 +4。",
        "effects": [{"type": "card_name_bonus", "keyword": "打击", "value": 4}]
    }
}

COLLECTION_CARDS = {
    "elf_archer_xiaomei": {
        "name": "精灵射手小梅",
        "required": 2,
        "unlock_card": "elf_archer_xiaomei",
        "desc": "集换章达到 2 枚后解锁。"
    }
}

COLLECTION_ORDER = ["elf_archer_xiaomei"]
