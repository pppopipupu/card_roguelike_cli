MINION_BASIC_CONFIG = {
    "mercenary": {
        "name": "雇佣兵",
        "atk_buff": 1,
        "skills": [
            {
                "id": "heavy_strike",
                "name": "重击",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，造成 6 点伤害。",
                "damage": 6,
                "feedback": "对【{target}】造成了 {damage} 点伤害。"
            },
            {
                "id": "battlecry",
                "name": "战吼",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，本回合随从攻击力增加 4。",
                "atk_buff": 4,
                "feedback": "本回合攻击力提升了 {atk_buff} 点。"
            }
        ]
    },
    "shield_guard": {
        "name": "盾卫",
        "skills": [
            {
                "id": "defend",
                "name": "重整防线",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，为玩家提供 2 点护盾。",
                "shield": 2,
                "feedback": "为玩家提供了 {shield} 点护盾。"
            },
            {
                "id": "bash",
                "name": "持盾撞击",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，造成 3 点伤害，玩家获得 1 点护盾。",
                "damage": 3,
                "shield": 1,
                "feedback": "对【{target}】造成了 {damage} 点伤害，并为玩家提供了 {shield} 点护盾。"
            }
        ]
    },
    "find_familiar": {
        "name": "召唤魔宠",
        "skills": [
            {
                "id": "assist",
                "name": "奥术协助",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，玩家抽 1 张牌。",
                "draw": 1,
                "feedback": "玩家抽取了 {draw} 张牌。"
            },
            {
                "id": "charge",
                "name": "法力充能",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，为玩家提供 1BA。",
                "ba_gain": 1,
                "feedback": "玩家获得了 {ba_gain} 个附赠动作点 (BA)。"
            }
        ]
    },
    "water_elemental": {
        "name": "寒冰元素",
        "skills": [
            {
                "id": "touch",
                "name": "寒冰触碰",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，扣除敌方领主下回合 1BA。",
                "ba_reduction": 1,
                "feedback": "扣除了敌人【{target}】下回合 1 个附赠动作点。"
            },
            {
                "id": "lance",
                "name": "霜冻冰枪",
                "cost_a": 3,
                "cost_ba": 0,
                "desc": "消耗 3A，造成 4 点伤害，若目标是随从则使其本回合无法攻击，若为领主则扣除其下回合 1A。",
                "damage": 4,
                "action_reduction": 1,
                "feedback": "对【{target}】造成了 {damage} 点伤害。",
                "feedback_boss": "对【{target}】造成了 {damage} 点伤害，并扣掉了其下回合 1 个动作点。"
            }
        ]
    },
    "arcane_golem": {
        "name": "奥术傀儡",
        "skills": [
            {
                "id": "overload",
                "name": "能量过载",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，自身失去 4 生命，本回合攻击力 +3。",
                "self_damage": 4,
                "atk_buff": 3,
                "feedback": "自身失去 {self_damage} 点生命值，本回合攻击力增加 {atk_buff} 点。",
                "feedback_dead": "自身失去 {self_damage} 点生命值并过载死亡，本回合攻击力增加 {atk_buff} 点。"
            },
            {
                "id": "repair",
                "name": "自我修复",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，恢复自身 6 点生命值。",
                "heal": 6,
                "feedback": "恢复了自身 {heal} 点生命值，当前生命 {hp}/{max_hp}。"
            }
        ]
    },
    "minion_icerainboww": {
        "name": "Icerainboww",
        "skills": [
            {
                "id": "icerain_spray",
                "name": "冰雨散射",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，对所有敌人造成 4 点寒冷伤害，并使所有敌人受到 1 层轻度寒冷易伤。",
                "damage": 4,
                "vulnerable_layers": 1,
                "feedback": "降下漫天冰雨散射攻击敌人。"
            },
            {
                "id": "aurora_shield",
                "name": "极光屏障",
                "cost_a": 1,
                "cost_ba": 0,
                "desc": "消耗 1A，为玩家提供 8 点护盾，且我方所有随从和玩家均获得 4 点护盾（随从获得 4 点生命恢复，玩家共获得 12 点护盾）。",
                "shield": 8,
                "player_shield": 12,
                "minion_heal": 4,
                "feedback": "凝聚极光屏障，为所有人附加防护效果。"
            }
        ]
    },
    "mercenary+": {
        "name": "雇佣兵+",
        "atk_buff": 2,
        "skills": [
            {
                "id": "heavy_strike",
                "name": "重击+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，造成 10 点伤害。",
                "damage": 10,
                "feedback": "对【{target}】造成了 {damage} 点伤害。"
            },
            {
                "id": "battlecry",
                "name": "战吼+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，本回合随从攻击力增加 6。",
                "atk_buff": 6,
                "feedback": "本回合攻击力提升了 {atk_buff} 点。"
            }
        ]
    },
    "shield_guard+": {
        "name": "盾卫+",
        "skills": [
            {
                "id": "defend",
                "name": "重整防线+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，为玩家提供 5 点护盾。",
                "shield": 5,
                "feedback": "为玩家提供了 {shield} 点护盾。"
            },
            {
                "id": "bash",
                "name": "持盾撞击+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，造成 5 点伤害，玩家获得 3 点护盾。",
                "damage": 5,
                "shield": 3,
                "feedback": "对【{target}】造成了 {damage} 点伤害，并为玩家提供了 {shield} 点护盾。"
            }
        ]
    },
    "find_familiar+": {
        "name": "召唤魔宠+",
        "skills": [
            {
                "id": "assist",
                "name": "奥术协助+",
                "cost_a": 1,
                "cost_ba": 0,
                "desc": "消耗 1A，玩家抽 1 张牌。",
                "draw": 1,
                "feedback": "玩家抽取了 {draw} 张牌。"
            },
            {
                "id": "charge",
                "name": "法力充能+",
                "cost_a": 1,
                "cost_ba": 0,
                "desc": "消耗 1A，为玩家提供 1BA。",
                "ba_gain": 1,
                "feedback": "玩家获得了 {ba_gain} 个附赠动作点 (BA)。"
            }
        ]
    },
    "water_elemental+": {
        "name": "寒冰元素+",
        "skills": [
            {
                "id": "touch",
                "name": "寒冰触碰+",
                "cost_a": 1,
                "cost_ba": 0,
                "desc": "消耗 1A，扣除敌方领主下回合 1BA。",
                "ba_reduction": 1,
                "feedback": "扣除了敌人【{target}】下回合 1 个附赠动作点。"
            },
            {
                "id": "lance",
                "name": "霜冻冰枪+",
                "cost_a": 3,
                "cost_ba": 0,
                "desc": "消耗 3A，造成 7 点伤害，若目标是随从则使其本回合无法攻击，若为领主则扣除其下回合 1A 并使其眩晕 1 回合。",
                "damage": 7,
                "action_reduction": 1,
                "stun": 1,
                "feedback": "对【{target}】造成了 {damage} 点伤害并使其陷入眩晕！",
                "feedback_boss": "对【{target}】造成了 {damage} 点伤害，并扣掉了其下回合 1 个动作点，且使其陷入眩晕！"
            }
        ]
    },
    "arcane_golem+": {
        "name": "奥术傀儡+",
        "skills": [
            {
                "id": "overload",
                "name": "能量过载+",
                "cost_a": 1,
                "cost_ba": 0,
                "desc": "消耗 1A，自身失去 3 生命，本回合攻击力 +4。",
                "self_damage": 3,
                "atk_buff": 4,
                "feedback": "自身失去 {self_damage} 点生命值，本回合攻击力增加 {atk_buff} 点。",
                "feedback_dead": "自身失去 {self_damage} 点生命值并过载死亡，本回合攻击力增加 {atk_buff} 点。"
            },
            {
                "id": "repair",
                "name": "自我修复+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，恢复自身 10 点生命值。",
                "heal": 10,
                "feedback": "恢复了自身 {heal} 点生命值，当前生命 {hp}/{max_hp}。"
            }
        ]
    },
    "minion_icerainboww+": {
        "name": "Icerainboww+",
        "skills": [
            {
                "id": "icerain_spray",
                "name": "冰雨散射+",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，对所有敌人造成 7 点寒冷伤害，并使所有敌人受到 2 层轻度寒冷易伤。",
                "damage": 7,
                "vulnerable_layers": 2,
                "feedback": "降下漫天冰雨散射攻击敌人。"
            },
            {
                "id": "aurora_shield",
                "name": "极光屏障+",
                "cost_a": 1,
                "cost_ba": 0,
                "desc": "消耗 1A，为玩家提供 12 点护盾，且我方所有随从和玩家均获得 6 点护盾（随从获得 6 点生命恢复，玩家共获得 18 点护盾）。",
                "player_shield": 12,
                "minion_heal": 6,
                "feedback": "凝聚极光屏障，为所有人附加防护效果。"
            }
        ]
    },
    "gate_guard": {
        "name": "门扉守卫",
        "skills": [
            {
                "id": "guard_strike",
                "name": "守卫痛击",
                "cost_a": 2,
                "cost_ba": 0,
                "desc": "消耗 2A，造成 6 点钝击伤害并使目标下回合动作 A 减少 1。",
                "damage": 6,
                "action_reduction": 1,
                "feedback": "对【{target}】造成了 {damage} 点钝击伤害。"
            }
        ]
    },
    "elf_archer_xiaomei": {
        "name": "精灵射手小梅",
        "enter_damage": 16,
        "enter_hit_thresholds": [4, 6, 8],
        "enter_current_card_bonus": 1,
        "enter_damage_type": "piercing",
        "enter_damage_name": "穿刺",
        "skills": []
    },
    "gate_guard+": {
        "name": "门扉守卫+",
        "skills": [
            {
                "id": "gate_strike",
                "name": "守卫痛击+",
                "cost_a": 1,
                "cost_ba": 0,
                "desc": "消耗 1A，造成 8 点钝击伤害并使目标下回合动作 A 减少 1。",
                "damage": 8,
                "action_reduction": 1,
                "feedback": "对【{target}】造成了 {damage} 点钝击伤害并使其下回合动作点 A 减少 1。"
            }
        ]
    }
}
