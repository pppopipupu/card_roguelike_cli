RAINIE_BUFF_CONFIG = {
    "sleep_rain": {
        "name": "助眠雨声",
        "desc": "无法行动 1 回合；受到寒冷或心灵伤害时额外受到 50% 噩梦伤害；受到任意物理、火焰或雷鸣伤害时立刻解除并获得 3 层力量。",
        "is_debuff": True,
        "nightmare_multiplier": 1.5,
        "wake_strength": 3
    },
    "eight_k_sharp": {
        "name": "8K 锐化",
        "desc": "本场战斗中，你造成的任意大于 0 的伤害都会被强行向上取整为 10 的倍数。",
        "round_to": 10
    },
    "breath_osmosis": {
        "name": "呼吸渗透",
        "desc": "该敌人获得的护盾、治疗与正面状态全部转移给施加者；其回合结束时将当前生命 10%（至多 25 点）转移给施加者。",
        "is_debuff": True,
        "drain_ratio": 0.1,
        "drain_cap": 25
    },
    "emo_love_brain": {
        "name": "深夜 emo 恋爱脑",
        "desc": "每回合开始时，将上一回合打出的最后一张非【歌词】牌的 0A 0BA、带【虚无】【消耗】的幻影置入手牌。"
    },
    "missing_ex": {
        "name": "想念前任",
        "desc": "敌方回合开始时每层受到 4 点心灵伤害，并有 35% 概率陷入 1 回合【混乱】；场上任意单位死亡时，所有敌人的【想念前任】层数翻倍。",
        "is_debuff": True,
        "psychic_per_stack": 4,
        "confuse_chance": 0.35,
        "confuse_turns": 1
    },
    "transparent_wrap": {
        "name": "透明包装",
        "desc": "敌人获得的护盾减半；处于无盾状态时，受到的物理攻击额外承受 25% 真实伤害。",
        "is_debuff": True,
        "leak_ratio": 0.5,
        "true_bonus": 0.25
    },
    "rainie_transparent": {
        "name": "小透明",
        "desc": "本回合若场上存在我方随从或联机队友，敌人将完全无视你。"
    },
    "rainie_courage": {
        "name": "Rainie 给的勇气",
        "desc": "护盾为 0 时免疫【混乱】【震颤】【易伤】，造成伤害 +50%，每回合初额外获得 1BA；主动获得护盾时扣 1 血（最低留 1）并在日志中遭到嘲讽。",
        "damage_bonus": 0.5,
        "ba_gain": 1
    },
    "wet": {
        "name": "湿透",
        "desc": "受到的寒冷伤害与闪电伤害翻倍。",
        "is_debuff": True
    },
    "dripping": {
        "name": "滴水穿石",
        "desc": "永不衰减。玩家每打出 1 张牌，受到等于层数的寒冷伤害并使层数 +1；玩家单回合出满 5 张牌时，回合结束层数翻倍。",
        "is_debuff": True,
        "threshold": 5
    },
    "rainy_season": {
        "name": "重度回南天",
        "desc": "持续 3 回合。敌人攻击有 40% 概率打滑落空并反受 15 点钝击伤害与 1 层【震颤】；敌方火焰伤害减半；敌人受闪电伤害翻倍。",
        "slip_chance": 0.4,
        "slip_damage": 15,
        "fire_multiplier": 0.5,
        "lightning_multiplier": 2.0
    },
    "social_death": {
        "name": "社会性死亡",
        "desc": "伤害降低 25%，每次受玩家卡牌伤害额外受 6 点心灵伤害；非首领血量低于 30% 或负面 ≥ 6 层时直接逃跑离场；首领改为清盾并眩晕 1 回合（限 1 次）。",
        "is_debuff": True,
        "damage_reduction": 0.25,
        "extra_psychic": 6,
        "hp_threshold": 0.3,
        "neg_threshold": 6
    },
    "infinite_refill": {
        "name": "无限续杯",
        "desc": "本场战斗中，你的正面状态不再衰减，护盾回合开始不减半，未消耗的 A 与 BA 保留到下回合。"
    },
    "rainie_cross_battle": {
        "name": "跨战延续",
        "desc": "本场胜利时，将当前力量（至多 15 层）与剩余护盾的一半（至多 40 点）带入下一场战斗开局。"
    },
    "rain_wish_replay_pending": {
        "name": "暴雨预警",
        "desc": "本回合打出的下一张非【歌词】牌附加重放。"
    },
    "rain_wish_rain_pending": {
        "name": "倾盆冷雨",
        "desc": "本回合每再打出 1 张【歌词】牌，对所有敌人造成 6 点寒冷伤害。",
        "rain_damage": 6
    },
    "rain_wish_retain_hand": {
        "name": "暴雨保留",
        "desc": "本回合结束时手牌全部临时获得【保留】。"
    },
    "i_believe_you_will_die": {
        "name": "我信你会死",
        "desc": "2 回合倒计时，归零时造成 55 点真实伤害；若目标未死，施法者陷入 1 回合【混乱】，并立即获得 2A 与抽 3 张牌。",
        "is_debuff": True,
        "damage": 55,
        "confuse_turns": 1,
        "actions": 2,
        "draw": 3
    },
    "idealist_death_ward": {
        "name": "唯心免死",
        "desc": "抵挡 1 次致命伤害，将生命锁定为 1 点并立即获得 40 点护盾。",
        "shield_on_save": 40
    },
    "rain_wish_free_pending": {
        "name": "言出法随",
        "desc": "你打出的下一张牌费用变为 0A 0BA。"
    },

    "rain_wish_amplify": {
        "name": "祈愿增幅",
        "desc": "回合结束时记录并放大本回合 Buff 变化。",
        "is_buff": True
    },
    "rain_wish_amplify_post": {
        "name": "祈愿增幅结算",
        "desc": "回合末后置放大 Buff 变化。",
        "is_buff": True
    },
    "rain_wish_no_shield_decay": {
        "name": "祈愿护盾",
        "desc": "下回合护盾不衰减。",
        "is_buff": True
    }
}
