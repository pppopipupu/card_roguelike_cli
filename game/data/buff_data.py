BUFF_CONFIG = {
    "pendulum_resonance": {
        "name": "钟摆共振",
        "desc": "回合结束时若动作点全光则受打出牌数*2点真伤惩罚，保留至少1A 1BA则获得额外抽取2张牌的奖赏",
        "min_damage": 4,
        "damage_per_card": 2,
        "draw_bonus": 2,
        "is_debuff": True
    },
    "bleed": {
        "name": "流血",
        "desc": "每回合开始时，受到层数点真实伤害，层数减少 1",
        "damage_per_stack": 1,
        "is_debuff": True
    },
    "hell_raider": {
        "name": "地狱狂徒",
        "desc": "在此状态下，每当你抽到 1A 且不消耗 BA 的卡牌时，立即免费并自动将其打出",
        "cost_a_limit": 1,
        "upgraded_cost_a_limit": 2,
        "chain_depth": 5,
        "upgraded_draw_count": 1
    },
    "prismatic_barrier": {
        "name": "虹光屏障",
        "desc": "每次受到攻击时层数减少 1，并对攻击来源反射 12 点混合属性伤害",
        "reflect_damage": 12,
        "upgraded_reflect_damage": 20
    },
    "antimagic_immune": {
        "name": "反魔法屏障",
        "desc": "免疫本回合内除物理伤害外的所有魔法伤害"
    },
    "tactical_focus": {
        "name": "无法抽牌",
        "desc": "本回合无法再抽牌",
        "is_debuff": True
    },
    "quicken": {
        "name": "超魔-瞬发",
        "desc": "所有法术牌动作消耗减少 1BA（最低为 0）"
    },
    "spell_surge": {
        "name": "法术涌动",
        "desc": "每使用一张蓝色牌，抽 1 张牌"
    },
    "arcane_charge": {
        "name": "奥术充能",
        "desc": "法术牌造成的伤害 +3",
        "dmg_per_stack": 3
    },
    "echo_form": {
        "name": "回响形态",
        "desc": "每回合打出的卡牌额外打出，每张牌最多回响 5 次，多余层数顺延至后续卡牌",
        "max_echoes": 5,
        "echo_stack_cost": 5
    },
    "iron_will": {
        "name": "钢铁意志",
        "desc": "最大生命上限增加 10 并回复 10 生命",
        "max_hp_per_stack": 10,
        "upgraded_max_hp_per_stack": 15,
        "heal_multiplier": 2
    },
    "beat_of_death": {
        "name": "死亡律动",
        "desc": "每当玩家打出一张牌，玩家受到 1 点力场伤害",
        "damage_per_stack": 1,
        "is_debuff": True
    },
    "split_to_ten": {
        "name": "一分为十",
        "desc": "接下来打出的 X 张卡牌会额外再打出 10 次（可与重放、回响乘算）",
        "replay_amount": 10
    },
    "strength": {
        "name": "力量",
        "desc": "造成的伤害增加",
        "heavy_blade_multiplier": 3,
        "heavy_blade_upgraded_multiplier": 5,
        "astral_strike_multiplier": 4,
        "astral_strike_upgraded_multiplier": 5,
        "default_multiplier": 1
    },
    "fury": {
        "name": "愤怒",
        "desc": "玩家使用珍奇或传奇卡牌时，该怪物获得等同于愤怒层数的力量"
    },
    "minor_vulnerable_acid": {
        "name": "轻度强酸易伤",
        "desc": "受到的强酸伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_acid": {
        "name": "强酸易伤",
        "desc": "受到的强酸伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_bludgeoning": {
        "name": "轻度钝击易伤",
        "desc": "受到的钝击伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_bludgeoning": {
        "name": "钝击易伤",
        "desc": "受到的钝击伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_cold": {
        "name": "轻度寒冷易伤",
        "desc": "受到的寒冷伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_cold": {
        "name": "寒冷易伤",
        "desc": "受到的寒冷伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_fire": {
        "name": "轻度火焰易伤",
        "desc": "受到的火焰伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_fire": {
        "name": "火焰易伤",
        "desc": "受到的火焰伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_force": {
        "name": "轻度力场易伤",
        "desc": "受到的力场伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_force": {
        "name": "力场易伤",
        "desc": "受到的力场伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_lightning": {
        "name": "轻度闪电易伤",
        "desc": "受到的闪电伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_lightning": {
        "name": "闪电易伤",
        "desc": "受到的闪电伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_necrotic": {
        "name": "轻度黯蚀易伤",
        "desc": "受到的黯蚀伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_necrotic": {
        "name": "黯蚀易伤",
        "desc": "受到的黯蚀伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_piercing": {
        "name": "轻度穿刺易伤",
        "desc": "受到的穿刺伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_piercing": {
        "name": "穿刺易伤",
        "desc": "受到的穿刺伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_poison": {
        "name": "轻度毒素易伤",
        "desc": "受到的毒素伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_poison": {
        "name": "毒素易伤",
        "desc": "受到的毒素伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_psychic": {
        "name": "轻度心灵易伤",
        "desc": "受到的心灵伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_psychic": {
        "name": "心灵易伤",
        "desc": "受到的心灵伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_radiant": {
        "name": "轻度光耀易伤",
        "desc": "受到的光耀伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_radiant": {
        "name": "光耀易伤",
        "desc": "受到的光耀伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_slashing": {
        "name": "轻度挥砍易伤",
        "desc": "受到的挥砍伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_slashing": {
        "name": "挥砍易伤",
        "desc": "受到的挥砍伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_thunder": {
        "name": "轻度雷鸣易伤",
        "desc": "受到的雷鸣伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_thunder": {
        "name": "雷鸣易伤",
        "desc": "受到的雷鸣伤害翻倍",
        "damage_multiplier": 2.0
    },
    "minor_vulnerable_true": {
        "name": "轻度真实易伤",
        "desc": "受到的真实伤害增加 50%",
        "damage_multiplier": 1.5
    },
    "vulnerable_true": {
        "name": "真实易伤",
        "desc": "受到的真实伤害翻倍",
        "damage_multiplier": 2.0
    },
    "magic_network": {
        "name": "魔网天成",
        "desc": "本回合内每使用一张法术牌，对所有敌人造成 3 点伤害，获得 3 点护盾",
        "damage_amount": 3,
        "shield_amount": 3
    },
    "wish_power": {
        "name": "祈愿奥术",
        "desc": "本场战斗法术牌造成的伤害 +4",
        "damage_bonus": 4,
        "upgraded_damage_bonus": 6
    },
    "stun": {
        "name": "眩晕",
        "desc": "无法行动，回合开始时扣除一层恢复",
        "is_debuff": True
    },
    "shock": {
        "name": "电击",
        "desc": "受到的闪电和雷鸣伤害每层增加 1 点",
        "damage_per_stack": 1,
        "is_debuff": True
    },
    "lightning_shield": {
        "name": "闪电护体",
        "desc": "受到伤害时反弹 2 点闪电伤害并施加 1 层电击",
        "reflect_damage": 2,
        "shock_stacks": 1
    },
    "resist_acid": {
        "name": "强酸抗性",
        "desc": "受到的强酸伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_acid": {
        "name": "强酸免疫",
        "desc": "受到的强酸伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_bludgeoning": {
        "name": "钝击抗性",
        "desc": "受到的钝击伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_bludgeoning": {
        "name": "钝击免疫",
        "desc": "受is_debuff到的钝击伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_cold": {
        "name": "寒冷抗性",
        "desc": "受到的寒冷伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_cold": {
        "name": "寒冷免疫",
        "desc": "受到的寒冷伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_fire": {
        "name": "火焰抗性",
        "desc": "受到的火焰伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_fire": {
        "name": "火焰免疫",
        "desc": "受到的火焰伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_force": {
        "name": "力场抗性",
        "desc": "受到的力场伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_force": {
        "name": "力场免疫",
        "desc": "受到的力场伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_lightning": {
        "name": "闪电抗性",
        "desc": "受到的闪电伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_lightning": {
        "name": "闪电免疫",
        "desc": "受到的闪电伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_necrotic": {
        "name": "黯蚀抗性",
        "desc": "受到的黯蚀伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_necrotic": {
        "name": "黯蚀免疫",
        "desc": "受到的黯蚀伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_piercing": {
        "name": "穿刺抗性",
        "desc": "受到的穿刺伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_piercing": {
        "name": "穿刺免疫",
        "desc": "受到的穿刺伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_poison": {
        "name": "毒素抗性",
        "desc": "受到的毒素伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_poison": {
        "name": "毒素免疫",
        "desc": "受到的毒素伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_psychic": {
        "name": "心灵抗性",
        "desc": "受到的心灵伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_psychic": {
        "name": "心灵免疫",
        "desc": "受到的心灵伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_radiant": {
        "name": "光耀抗性",
        "desc": "受到的光耀伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_radiant": {
        "name": "光耀免疫",
        "desc": "受到的光耀伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_slashing": {
        "name": "挥砍抗性",
        "desc": "受到的挥砍伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_slashing": {
        "name": "挥砍免疫",
        "desc": "受到的挥砍伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "resist_thunder": {
        "name": "雷鸣抗性",
        "desc": "受到的雷鸣伤害减少 50%",
        "damage_multiplier": 0.5
    },
    "immune_thunder": {
        "name": "雷鸣免疫",
        "desc": "受到的雷鸣伤害减少 100%",
        "damage_multiplier": 0.0
    },
    "burning": {
        "name": "燃烧",
        "desc": "每回合开始时受到火焰伤害",
        "damage_per_stack": 1,
        "is_debuff": True
    },
    "key_scholar_passive": {
        "name": "门扉共鸣",
        "desc": "打出或部署护符卡牌时，玩家回复 3 点生命值并获得 4 点护盾",
        "heal_amount": 3,
        "shield_amount": 4
    },
    "void_weakness": {
        "name": "虚空虚弱",
        "desc": "法术牌造成的伤害减少 3 点,回合结束时层数减少 1",
        "damage_per_stack": 3,
        "is_debuff": True
    },
    "ancient_protection": {
        "name": "先古庇护",
        "desc": "每回合开始时若拥有护盾，则清除自身所有负面效果；拥有护盾时，受到伤害的 20% 反弹为力场伤害",
        "recoil_ratio": 0.2,
        "min_recoil": 1
    },
    "end_gate_passive": {
        "name": "终焉之门",
        "desc": "每回合开始时获得 15 点护盾，且清除自身所有负面效果；拥有护盾时，受到伤害会反弹 1 点真实伤害",
        "shield_amount": 15,
        "reflect_damage": 1
    },
    "doomsday_gate_passive": {
        "name": "终焉庇护",
        "desc": "每回合开始获得 20 护盾，且攻击力永久 +2；拥有护盾时，受到伤害会反弹 1 点真实伤害与 2 点力场伤害",
        "shield_amount": 20,
        "strength_stacks": 2,
        "reflect_damage": 1,
        "force_reflect_damage": 2
    },
    "time_lord_passive": {
        "name": "时空主宰",
        "desc": "每回合开始获得 20 护盾，且清除自身所有负面效果；受到伤害时 50% 几率召唤时空残影；分担 50% 伤害",
        "shield_gain": 20,
        "max_echoes": 1,
        "max_enemies": 3,
        "summon_chance": 0.5,
        "echo_hp": 15,
        "echo_actions": 1,
        "echo_max_actions": 1,
        "damage_share_divisor": 2
    },
    "phase_transition_immune": {
        "name": "转换阶段",
        "desc": "处于转换阶段状态，免疫所有伤害"
    },

    "ancient_wisdom_buff": {
        "name": "古老智慧",
        "desc": "打出中立卡牌时，获得 2 点护盾（每层）",
        "shield_per_stack": 2,
        "upgraded_shield_per_stack": 3
    },
    "buffer": {
        "name": "缓冲",
        "desc": "免疫接下来的伤害，受到一次伤害减少一层"
    },
    "demon_contract_buff": {
        "name": "恶魔契约",
        "desc": "打出的下一张法术牌额外打出多次"
    },
    "glacier_fortress_buff": {
        "name": "冰川壁垒",
        "desc": "回合结束时额外获得护盾",
        "shield_per_stack": 4,
        "upgraded_shield_per_stack": 6
    },
    "void_exhaustion": {
        "name": "虚空耗竭",
        "desc": "本回合内打出的所有非随从和护符卡牌都会在结算后被强制消耗移入消耗堆",
        "is_debuff": True
    },
    "mana_leak": {
        "name": "魔力泄漏",
        "desc": "你打出的法术牌需要额外消耗 1BA,且法术牌造成的伤害减少 2 点",
        "damage_per_stack": 2,
        "is_debuff": True
    },
    "minor_vulnerable": {
        "name": "轻度易伤",
        "desc": "受到的所有类型伤害增加 50%",
        "damage_multiplier": 1.5,
        "is_debuff": True
    },
    "vulnerable": {
        "name": "易伤",
        "desc": "受到的所有类型伤害翻倍",
        "damage_multiplier": 2.0,
        "is_debuff": True
    },
    "weak": {
        "name": "虚弱",
        "desc": "造成的伤害减少 50%",
        "damage_multiplier": 0.5,
        "is_debuff": True
    },
    "flame_barrier_buff": {
        "name": "火焰屏障",
        "desc": "受到伤害时对攻击源反弹真实伤害",
        "reflect_damage": 1
    },
    "metallicize": {
        "name": "金属化",
        "desc": "回合结束时额外获得护盾",
        "shield_per_stack": 1
    },
    "demon_form": {
        "name": "恶魔形态",
        "desc": "回合开始时获得力量",
        "strength_stacks": 1
    },
    "double_tap_buff": {
        "name": "双发",
        "desc": "下一次物理伤害卡将触发额外打出",
        "replay_amount": 1
    },
    "barricade": {
        "name": "壁垒",
        "desc": "护盾回合开始时不衰减一半",
        "shield_retention": 0.5
    },
    "ritual": {
        "name": "仪式",
        "desc": "每回合开始时，获得等同于此状态层数的力量",
        "strength_stacks": 1
    },
    "grappled": {
        "name": "受擒",
        "desc": "你被夺心魔擒抱，每回合结束时层数减少 1",
        "is_debuff": True
    },
    "astral_speed": {
        "name": "星界加速",
        "desc": "下回合开始时，获得 1 个额外动作点",
        "action_gain": 1
    },
    "ward": {
        "name": "守护",
        "desc": "拥有守护状态的随从在战场上时，敌方的单体指向性攻击意图将被强制吸引并只能指向该随从"
    },
    "fire_grow": {
        "name": "烈焰成长",
        "desc": "你造成的火焰伤害增加，每层增加 1 点",
        "damage_per_stack": 1
    },
    "forge_backfire": {
        "name": "炉温反噬",
        "desc": "你在锻造熔炉中汲取温热力量带来的后遗症,你打出的法术牌造成的伤害减少,每层减少 1 点",
        "damage_per_stack": 1,
        "is_debuff": True
    },
    "time_warp_spell_boost": {
        "name": "时空强化",
        "desc": "本回合内你打出的法术牌造成的伤害增加 2 点",
        "damage_per_stack": 2
    },
    "commander_aurora_emperor": {
        "name": "极光圣域",
        "desc": "极光圣域力场展开，我方随从发起普通攻击时，玩家获得 2 点护盾（升级版则额外抽 1 张牌）",
        "shield_amount": 2,
        "upgraded_shield_amount": 3,
        "upgraded_draw_count": 1
    },
    "discard_next_turn": {
        "name": "下回合弃牌",
        "desc": "在下一回合开始时，你将随机丢弃等同于此状态层数的手牌",
        "is_debuff": True
    },
    "unyielding": {
        "name": "坚不可摧",
        "desc": "一回合最多可受到该状态层数点伤害，超出的部分会直接免疫，真实伤害可以穿透坚不可摧"
    },
    "drain_ba": {
        "name": "虚空纠缠",
        "desc": "在下一回合开始时，你将失去等同于此状态层数的附赠动作点 (BA)",
        "is_debuff": True
    },
    "drain_a": {
        "name": "时间纠缠",
        "desc": "在下一回合开始时，你将失去等同于此状态层数的动作点 (A)",
        "is_debuff": True
    },
    "poison": {
        "name": "中毒",
        "desc": "每回合开始时，受到层数点毒素伤害，层数减少 1",
        "damage_per_stack": 1,
        "is_debuff": True
    },
    "doom": {
        "name": "灾厄",
        "desc": "每回合开始时，若生命值小于层数，则直接被消灭并死亡",
        "is_debuff": True
    },
    "all_resonance": {
        "name": "万物共振",
        "desc": "你和全体友方单位造成的最终伤害呈指数级叠加翻倍，每层使最终伤害乘以 10 倍，可与其他伤害加成乘算",
        "damage_multiplier": 10
    },
    "coop_aegis": {
        "name": "援护",
        "desc": "本回合受到的单体攻击伤害降低 25%，回合开始时移除",
        "damage_multiplier": 0.75
    },
    "coop_soul_resonance": {
        "name": "灵魂共鸣",
        "desc": "打出的攻击或法术牌基础伤害提升，每次触发减少 1 层并为链接发起者恢复生命",
        "damage_bonus": 4,
        "heal_amount": 2,
        "high_heal_amount": 3,
        "high_bonus_threshold": 6
    },
    "bonus_speed": {
        "name": "迅捷附赠",
        "type": "buff",
        "desc": "下回合开始时，获得等同于层数的额外附赠动作点 (BA)"
    },
    "baguwen_restriction": {
        "name": "八股文限制",
        "type": "debuff",
        "violation_damage": 10,
        "desc": "每回合必须优先打出系统点名的第一张手牌，否则受到 10 点黯蚀伤害",
        "is_debuff": True
    },
    "shroud_time_warp": {
        "name": "虚境时计",
        "type": "buff",
        "card_limit": 12,
        "heal_val": 12,
        "shield_val": 15,
        "strength_val": 2,
        "desc": "玩家每打出 12 张牌，强制结束当前玩家回合并使虚境之影恢复 12 生命、获得 15 护盾与 2 层力量"
    },
    "pure_vessel_body_passive": {
        "name": "空洞之躯",
        "type": "buff",
        "desc": "免疫流血与中毒，每回合开始移除自身 1 层负面状态"
    },
    "pure_parry_stance": {
        "name": "骨钉招架",
        "type": "buff",
        "counter_damage": 8,
        "desc": "拥有护盾期间受到物理攻击时反击造成 8 点挥砍伤害；护盾被击破时解除招架并暴露 1 层轻度易伤"
    },
    "pure_focus_charge": {
        "name": "聚焦蓄能",
        "type": "buff",
        "heal_val": 12,
        "strength_val": 2,
        "desc": "正在凝聚纯白圣环，若下回合行动前护盾未被击破，释放聚焦圣环时恢复 12 生命并获得 2 层力量"
    },
    "dragon_scales_passive": {
        "name": "龙威鳞甲",
        "type": "buff",
        "start_shield": 8,
        "thorns_damage": 2,
        "burn_stacks": 1,
        "burn_turns": 2,
        "desc": "回合开始无盾时获得 8 护盾；持盾受物理攻击时反弹 2 点火焰伤害并施加 1 层灼烧"
    },
    "molten_charge": {
        "name": "熔火蓄力",
        "type": "buff",
        "bonus_damage": 6,
        "desc": "正在蓄力炼狱吐息，若护盾未被击破则下回合炼狱吐息伤害 +6；若护盾被击破则失去蓄力并暴露 1 层轻度易伤"
    },
    "storm_field_passive": {
        "name": "雷暴力场",
        "type": "buff",
        "bonus_per_orb": 2,
        "desc": "场上每有 1 只存活雷影魔仆，雷电伤害 +2；回合开始若有护盾则对玩家施加 1 层电击"
    },
    "permafrost_aura_passive": {
        "name": "极寒领域",
        "type": "buff",
        "card_threshold": 4,
        "chill_damage": 2,
        "desc": "玩家每回合打出第 4 张及之后卡牌时若带轻度寒冷易伤则受 2 点寒冷伤害；回合结束无护盾则获得 1 层轻度寒冷易伤"
    },
    "cthulhu_mist_immune": {
        "name": "星体迷雾",
        "type": "buff",
        "desc": "化为不可名状的星体迷雾，免疫常规伤害；唯【放逐斩】或拉莱耶第三幕冲撞可将其彻底放逐"
    },
    "stars_misaligned": {
        "name": "群星失位",
        "type": "debuff",
        "damage_multiplier": 1.5,
        "desc": "拉莱耶星轨被逆转，受到的所有伤害提高 50%",
        "is_debuff": True
    },
    "doom_furnace_passive": {
        "name": "末日熔炉",
        "type": "buff",
        "desc": "每次自身失去生命值时，获得 1 层力量"
    },
    "soul_phylactery_passive": {
        "name": "魂匣共鸣",
        "type": "buff",
        "damage_reduction": 0.3,
        "desc": "场上有骷髅兵存活时，自身受到的伤害降低 30%"
    },
    "dream_eater_passive": {
        "name": "食梦帷幕",
        "type": "buff",
        "shield_gain": 4,
        "heal_gain": 3,
        "desc": "每当玩家消耗卡牌时，获得 4 点护盾并恢复 3 点生命"
    },
    "pale_entropy": {
        "name": "灰域侵蚀",
        "type": "debuff",
        "desc": "回合结束时，受到层数点灵能伤害，随后层数减少 1",
        "damage_per_stack": 1,
        "is_debuff": True
    },
    "psychic_resistance": {
        "name": "心灵伤害抗性",
        "type": "buff",
        "damage_multiplier": 0.5,
        "desc": "受到的心灵伤害减半；每回合结束时层数减少 1"
    },
    "intangible": {
        "name": "无实体",
        "type": "buff",
        "damage_cap": 1,
        "desc": "受到的一切伤害封顶为 1 点；每回合开始时层数减少 1"
    },
    "bladesong": {
        "name": "剑歌",
        "type": "buff",
        "ba_gain": 1,
        "proc_dmg": 3,
        "proc_shield": 3,
        "desc": "每回合开始时额外获得 1 点附赠动作 (BA)；每当打出红色或蓝色卡牌时，对随机敌方造成 3*层数 点力场伤害并获得 3*层数 点护盾"
    },
    "exhaustion": {
        "name": "力竭",
        "type": "debuff",
        "is_debuff": True,
        "persistent": True,
        "desc": "持久负面状态（共 5 级）：1 级首回合抽牌 -1；2 级护盾获得量 -25%；3 级每回合少 1 点 BA 且伤害 -20%；4 级战斗中最大生命上限减半且每回合抽牌 -1；5 级力竭阵亡"
    },
    "ancient_ward": {
        "name": "先古庇护",
        "type": "buff",
        "is_debuff": False,
        "persistent": True,
        "shield_gain": 6,
        "desc": "持久增益状态：下场战斗开始时获得 6 点护盾并消耗 1 层"
    },
    "arcane_clarity": {
        "name": "奥术澄明",
        "type": "buff",
        "is_debuff": False,
        "persistent": True,
        "draw_gain": 1,
        "desc": "持久增益状态：下场战斗首回合额外抽 1 张牌并消耗 1 层"
    },
    "abyss_chill": {
        "name": "深渊寒蚀",
        "type": "debuff",
        "is_debuff": True,
        "persistent": True,
        "weak_stacks": 1,
        "desc": "持久负面状态：下场战斗开始时获得 1 层虚弱并消耗 1 层，可在篝火或咖啡馆中治愈"
    }
}
