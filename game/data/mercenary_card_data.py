MERCENARY_CARD_CONFIG = {
    "pale_interference": {
        "name": "灰域杂波",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "common",
        "base_dmg": 6,
        "buff_stacks": 2,
        "damage_type": "psychic",
        "desc": "造成 6 点灵能伤害，并赋予目标 2 层【灰域侵蚀】。",
        "feedback": "发射了一阵灰域杂波，【{target}】陷入认知静电。"
    },
    "pale_two_mm_hole": {
        "name": "两毫米的裂隙",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "base_dmg": 8,
        "draw_count": 1,
        "buff_stacks": 1,
        "damage_type": "psychic",
        "desc": "造成 8 点灵能伤害；若目标带有【灰域侵蚀】，额外抽 1 张牌并赋予其 1 层【虚弱】。",
        "feedback": "指向世界边缘那两毫米的寂静裂隙。"
    },
    "pale_crossing": {
        "name": "横渡灰域",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 1,
        "rarity": "epic",
        "self_hp_cost": 3,
        "shield_amount": 10,
        "buff_stacks": 3,
        "draw_count": 2,
        "target_type": "self",
        "desc": "失去 3 点生命，获得 10 点护盾，所有敌人获得 3 层【灰域侵蚀】，并抽 2 张牌。",
        "feedback": "屏住呼吸踏入灰白雾霭，在记忆剥落前带回 2 张牌。"
    },
    "pale_lathe_memory": {
        "name": "灰域记忆回流",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 0,
        "cost_ba": 1,
        "rarity": "rare",
        "heal_amount": 4,
        "draw_count": 2,
        "target_type": "any_other",
        "desc": "为自身或指定友方恢复 4 点生命，并抽 2 张牌。",
        "feedback": "一段不属于这个时代的温柔记忆回流进了身体。"
    },
    "pale_white_noise": {
        "name": "白噪屏障",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "common",
        "shield_amount": 8,
        "buff_stacks": 1,
        "target_type": "self",
        "desc": "获得 8 点护盾，对随机一名敌人施加 1 层【灰域侵蚀】。",
        "feedback": "无线电雪花声在周身织成屏障。"
    },
    "pale_porch_collapse": {
        "name": "苍白边界坍缩",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 2,
        "cost_ba": 0,
        "rarity": "legendary",
        "base_dmg": 12,
        "multiplier": 2,
        "damage_type": "psychic",
        "desc": "对所有敌人造成 12 点灵能伤害，并引爆其身上的【灰域侵蚀】（每层额外造成 2 点灵能伤害）。",
        "feedback": "苍白地平线向战场中心坍塌，所有过往一并坠落。"
    },
    "thought_aces_high": {
        "name": "居高临下",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "shield_amount": 10,
        "strength_gain": 2,
        "draw_count": 1,
        "target_type": "any_other",
        "desc": "为自身或指定友方提供 10 点护盾与 2 层【力量】；若目标生命高于一半，抽 1 张牌。",
        "feedback": "从高处俯瞰整座瑞瓦肖，姿态决定了结局。"
    },
    "thought_aces_low": {
        "name": "载誉而归",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 0,
        "cost_ba": 1,
        "rarity": "rare",
        "heal_amount": 6,
        "action_gain": 1,
        "draw_count": 1,
        "target_type": "self",
        "desc": "恢复 6 点生命并抽 1 张牌；若自身生命低于 60%，改为恢复 10 点生命并获得 1A。",
        "feedback": "哪怕满身泥泞，你依然完成了几乎不可能的默契配合。"
    },
    "thought_actual_art_degree": {
        "name": "正经的艺术学位",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "shield_amount": 8,
        "draw_count": 2,
        "buff_stacks": 2,
        "desc": "获得 8 点护盾，抽 2 张牌，并赋予目标 2 层【虚弱】。",
        "feedback": "用半吊子美术史讲座把敌人彻底讲晕了。"
    },
    "thought_advanced_race_theory": {
        "name": "先进的种族理论",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "common",
        "base_dmg": 7,
        "buff_stacks": 2,
        "self_hp_cost": 2,
        "damage_type": "psychic",
        "desc": "失去 2 点生命，对目标造成 7 点灵能伤害并施加 2 层【易伤】。",
        "feedback": "你大声背诵荒谬的颅相学词汇，双方大脑都受到了冲击。"
    },
    "thought_anti_object_task_force": {
        "name": "反物质特遣队",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "base_dmg": 11,
        "absorb_amount": 12,
        "bonus_action_gain": 1,
        "damage_type": "bludgeoning",
        "desc": "造成 11 点钝击伤害并摧毁目标最多 12 点护盾；若目标护盾归零，获得 1BA。",
        "feedback": "对着无辜的障碍物狠狠踹了一脚。"
    },
    "thought_apricot_chewing_gum": {
        "name": "杏子味的口香糖",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 0,
        "cost_ba": 1,
        "rarity": "epic",
        "self_hp_cost": 3,
        "buff_stacks": 2,
        "action_gain": 1,
        "bonus_action_gain": 1,
        "target_type": "self",
        "desc": "失去 3 点生命，获得 1A 1BA，并赋予所有敌人 2 层【灰域侵蚀】。",
        "feedback": "糖纸上的杏子香气刺痛了记忆，情绪像灰域一样漫过全场。"
    },
    "thought_arno_van_eyck": {
        "name": "阿诺·凡·艾克",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "base_dmg": 7,
        "bonus_action_gain": 1,
        "damage_type": "thunder",
        "desc": "对所有敌人造成 7 点雷鸣伤害，随机一名存活友方获得 1BA。",
        "feedback": "硬核到极致的合成器低音撕开了空气。HARDCORE!"
    },
    "thought_bankruptcy_sequence": {
        "name": "破产序列",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 0,
        "cost_ba": 0,
        "rarity": "rare",
        "gold_cost": 5,
        "self_hp_cost": 3,
        "action_gain": 1,
        "bonus_action_gain": 1,
        "draw_count": 2,
        "exhaust": True,
        "target_type": "self",
        "desc": "失去 5 金币（若不足则失去 3 点生命），获得 1A 1BA 并抽 2 张牌。消耗。",
        "feedback": "破产算什么，口袋空空正是自由的开始。"
    },
    "thought_boiadeiro": {
        "name": "牛仔",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "common",
        "base_dmg": 9,
        "bonus_damage": 5,
        "damage_type": "piercing",
        "desc": "造成 9 点穿刺伤害；若这是本回合打出的第 1 张牌，伤害提高至 14 点。",
        "feedback": "孤身一人的荒原枪手率先扣动扳机。"
    },
    "thought_bringing_of_the_law": {
        "name": "天降正义（法律的下巴）",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 2,
        "cost_ba": 0,
        "rarity": "epic",
        "base_dmg": 16,
        "buff_turns": 1,
        "buff_stacks": 2,
        "damage_type": "bludgeoning",
        "desc": "造成 16 点钝击伤害，有 60% 概率使目标晕眩 1 回合（若目标已带有【易伤】或【灰域侵蚀】则必定晕眩）。",
        "feedback": "我是法律！下巴就是我的徽章！"
    },
    "thought_caustic_echo": {
        "name": "尖刻的回音",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "base_dmg": 8,
        "hit_count": 1,
        "damage_type": "psychic",
        "desc": "造成 8 点灵能伤害，并额外触发 1 次目标身上的【灰域侵蚀】伤害（不消耗层数）。",
        "feedback": "那句刻薄至极的话在目标脑海里反复回响。"
    },
    "thought_cleaning_out_the_rooms": {
        "name": "打扫房间",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "shield_amount": 7,
        "draw_count": 2,
        "count": 1,
        "target_type": "self",
        "desc": "获得 7 点护盾，抽 2 张牌，并清除自身 1 个负面状态。",
        "feedback": "把脑海里的空酒瓶和旧纸片全部扫出房间。"
    },
    "thought_coach_physical_instrument": {
        "name": "强健身体教练",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "common",
        "strength_gain": 2,
        "shield_amount": 6,
        "target_type": "self",
        "desc": "获得 2 层【力量】与 6 点护盾。",
        "feedback": "动起来，废柴！你的胸大肌可不是装饰品！"
    },
    "thought_col_do_ma_ma_daqua": {
        "name": "哈库多玛达塔",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 0,
        "cost_ba": 1,
        "rarity": "epic",
        "buff_stacks": 2,
        "draw_count": 1,
        "damage_type": "psychic",
        "desc": "对所有敌人施加 2 层【灰域侵蚀】与 1 层【易伤】，并抽 1 张牌。",
        "feedback": "一只根本不存在的高频声波生物从帷幕后鸣叫着掠过。"
    },
    "thought_cop_of_the_apocalypse": {
        "name": "末日警探",
        "color": "mercenary",
        "type": "spell",
        "cost_a": 2,
        "cost_ba": 0,
        "rarity": "legendary",
        "base_dmg": 14,
        "buff_stacks": 3,
        "self_hp_cost": 4,
        "damage_type": "psychic",
        "desc": "失去 4 点生命，对所有敌人造成 14 点灵能伤害并施加 3 层【灰域侵蚀】。",
        "feedback": "时间所剩无几，末日就在下个拐角等着所有人。"
    },
}

MERCENARY_CARD_UPGRADE_CONFIG = {
    "pale_interference": {
        "base_dmg": 9,
        "buff_stacks": 3,
        "desc": "造成 9 点灵能伤害，并赋予目标 3 层【灰域侵蚀】。"
    },
    "pale_two_mm_hole": {
        "base_dmg": 11,
        "buff_stacks": 2,
        "desc": "造成 11 点灵能伤害；若目标带有【灰域侵蚀】，额外抽 1 张牌并赋予其 2 层【虚弱】。"
    },
    "pale_crossing": {
        "shield_amount": 14,
        "buff_stacks": 4,
        "desc": "失去 3 点生命，获得 14 点护盾，所有敌人获得 4 层【灰域侵蚀】，并抽 2 张牌。"
    },
    "pale_lathe_memory": {
        "heal_amount": 7,
        "desc": "为自身或指定友方恢复 7 点生命，并抽 2 张牌。"
    },
    "pale_white_noise": {
        "shield_amount": 12,
        "buff_stacks": 2,
        "desc": "获得 12 点护盾，对随机一名敌人施加 2 层【灰域侵蚀】。"
    },
    "pale_porch_collapse": {
        "base_dmg": 16,
        "multiplier": 3,
        "desc": "对所有敌人造成 16 点灵能伤害，并引爆其身上的【灰域侵蚀】（每层额外造成 3 点灵能伤害）。"
    },
    "thought_aces_high": {
        "shield_amount": 14,
        "strength_gain": 3,
        "desc": "为自身或指定友方提供 14 点护盾与 3 层【力量】；若目标生命高于一半，抽 1 张牌。"
    },
    "thought_aces_low": {
        "heal_amount": 9,
        "desc": "恢复 9 点生命并抽 1 张牌；若自身生命低于 60%，改为恢复 14 点生命并获得 1A。"
    },
    "thought_actual_art_degree": {
        "shield_amount": 12,
        "buff_stacks": 3,
        "desc": "获得 12 点护盾，抽 2 张牌，并赋予目标 3 层【虚弱】。"
    },
    "thought_advanced_race_theory": {
        "base_dmg": 10,
        "buff_stacks": 3,
        "desc": "失去 2 点生命，对目标造成 10 点灵能伤害并施加 3 层【易伤】。"
    },
    "thought_anti_object_task_force": {
        "base_dmg": 15,
        "absorb_amount": 18,
        "desc": "造成 15 点钝击伤害并摧毁目标最多 18 点护盾；若目标护盾归零，获得 1BA。"
    },
    "thought_apricot_chewing_gum": {
        "self_hp_cost": 2,
        "buff_stacks": 3,
        "desc": "失去 2 点生命，获得 1A 1BA，并赋予所有敌人 3 层【灰域侵蚀】。"
    },
    "thought_arno_van_eyck": {
        "base_dmg": 10,
        "desc": "对所有敌人造成 10 点雷鸣伤害，所有存活友方获得 1BA。"
    },
    "thought_bankruptcy_sequence": {
        "self_hp_cost": 2,
        "draw_count": 3,
        "desc": "失去 5 金币（若不足则失去 2 点生命），获得 1A 1BA 并抽 3 张牌。消耗。"
    },
    "thought_boiadeiro": {
        "base_dmg": 12,
        "bonus_damage": 6,
        "desc": "造成 12 点穿刺伤害；若这是本回合打出的第 1 张牌，伤害提高至 18 点。"
    },
    "thought_bringing_of_the_law": {
        "base_dmg": 20,
        "desc": "造成 20 点钝击伤害，必定使目标晕眩 1 回合并施加 2 层【易伤】。"
    },
    "thought_caustic_echo": {
        "base_dmg": 11,
        "hit_count": 2,
        "desc": "造成 11 点灵能伤害，并额外触发 2 次目标身上的【灰域侵蚀】伤害（不消耗层数）。"
    },
    "thought_cleaning_out_the_rooms": {
        "shield_amount": 10,
        "count": 2,
        "desc": "获得 10 点护盾，抽 2 张牌，并清除自身 2 个负面状态。"
    },
    "thought_coach_physical_instrument": {
        "strength_gain": 3,
        "shield_amount": 9,
        "desc": "获得 3 层【力量】与 9 点护盾。"
    },
    "thought_col_do_ma_ma_daqua": {
        "buff_stacks": 3,
        "desc": "对所有敌人施加 3 层【灰域侵蚀】与 2 层【易伤】，并抽 1 张牌。"
    },
    "thought_cop_of_the_apocalypse": {
        "base_dmg": 18,
        "buff_stacks": 4,
        "self_hp_cost": 3,
        "desc": "失去 3 点生命，对所有敌人造成 18 点灵能伤害并施加 4 层【灰域侵蚀】。"
    },
}
