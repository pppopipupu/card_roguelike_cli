NEUTRAL_CARD_MINIONS = {
    "mercenary": {
        "name": "雇佣兵",
        "color": "neutral",
        "type": "minion",
        "cost_a": 1,
        "cost_ba": 0,
        "desc": "生命 10，攻击 4。拥有普通攻击（消耗 1A）。",
        "rarity": "rare",
        "minion_hp": 10,
        "minion_atk": 4,
        "feedback_success": "在格子 [{grid}] 召唤了【{name}】。",
        "feedback_fail": "战场已满，召唤失败。"
    },
    "shield_guard": {
        "name": "盾卫",
        "color": "neutral",
        "type": "minion",
        "cost_a": 1,
        "cost_ba": 0,
        "desc": "生命 15，攻击 1。技能：重整防线（消耗 1BA，为你提供 2 点护盾）。",
        "rarity": "rare",
        "minion_hp": 15,
        "minion_atk": 1,
        "feedback_success": "在格子 [{grid}] 召唤了【{name}】。",
        "feedback_fail": "战场已满，召唤失败。"
    },
    "minion_icerainboww": {
        "name": "Icerainboww",
        "color": "neutral",
        "type": "minion",
        "cost_a": 1,
        "cost_ba": 1,
        "desc": "生命 24，攻击 6。拥有技能：冰雨散射与极光屏障。",
        "rarity": "legendary",
        "minion_hp": 24,
        "minion_atk": 6,
        "feedback_success": "在格子 [{grid}] 召唤了【{name}】。",
        "feedback_fail": "战场已满，召唤失败。"
    },
    "gate_guard": {
        "name": "门扉守卫",
        "color": "neutral",
        "type": "minion",
        "cost_a": 1,
        "cost_ba": 0,
        "desc": "生命 12，攻击 2。入场曲：使一个敌人眩晕 1 回合。技能：守卫痛击（消耗 2A，造成 6 点钝击伤害并使目标下回合动作 A 减少 1）。",
        "rarity": "rare",
        "minion_hp": 12,
        "minion_atk": 2,
        "feedback_success": "在格子 [{grid}] 召唤了【{name}】并使【{target}】眩晕。"
    },
    "elf_archer_xiaomei": {
        "name": "精灵射手小梅",
        "color": "neutral",
        "type": "minion",
        "cost_a": 0,
        "cost_ba": 1,
        "desc": "生命 4，攻击 1。进入战场时，若本回合你已打出的卡牌数量达到 4，对随机敌人造成 16 点穿刺伤害；达到 6 再造成 16 点；达到 8 再造成 16 点。瞬念召唤：本回合第 4、6、8 张牌被打出时，从弃牌堆或抽牌堆跃入战场，不消耗费用。",
        "rarity": "rare",
        "minion_hp": 4,
        "minion_atk": 1,
        "instant_summon": True,
        "instant_summon_thresholds": [4, 6, 8],
        "feedback_success": "在格子 [{grid}] 召唤了【{name}】。",
        "feedback_fail": "战场已满，召唤失败。"
    }
}
