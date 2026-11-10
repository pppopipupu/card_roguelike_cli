ENEMY_BOSS_CONFIG = {
    "pppopipupu": {
        "name": "pppopipupu",
        "type": "boss",
        "hp": "1",
        "actions": "1A 0BA",
        "passive": "觉醒形态 (受到致命伤害时将进入【觉醒】状态并拥有 9999 生命，行动变为猛击造成 100 点伤害)",
        "intents": [
            {"id": "fish", "val": 0, "desc": "钓鱼 (无所事事地在靶场旁钓鱼)"},
            {"id": "force_strike", "val": 100, "desc": "猛击 (对玩家造成 100 点力场伤害)"}
        ]
    },
    "Icerainboww": {
        "name": "Icerainboww",
        "type": "boss",
        "hp": "190",
        "actions": "2A 1BA",
        "passive": "极寒领域 (玩家每回合打出第 4 张及之后卡牌时若带轻度寒冷易伤则受 2 点寒冷伤害；回合结束无护盾则受 1 层轻度寒冷易伤)",
        "intents": [
            {"id": "icerain_shoot", "val": 6, "desc": "冰雨弓射击 (造成 6 寒冷伤害，使玩家下回合失去 1A)"},
            {"id": "fury", "val": 1, "desc": "愤怒 (获得 1 层愤怒buff，被打出珍奇或传奇卡牌激怒时自身增伤)"},
            {"id": "smash_attack", "val": 10, "desc": "粉碎攻击 (造成 10 寒冷伤害，并使玩家受到轻度寒冷易伤)"},
            {"id": "aurora_shield", "val": 14, "desc": "极光屏障 (获得 14 护盾并净化 1 负面 Buff，无负面时额外获得 4 护盾)"},
            {"id": "winter_gaze", "val": 4, "desc": "寒冬凝视 (造成 4 心灵伤害，并使玩家受到轻度寒冷易伤)"},
            {"id": "frost_blast", "val": 6, "desc": "冰霜爆震 (对玩家与所有我方随从造成 6 寒冷伤害)"},
            {"id": "ice_refraction", "val": 10, "desc": "冰晶折射 (获得 10 护盾)"},
            {"id": "frost_trap", "val": 1, "desc": "霜冻陷阱 (使玩家下回合失去 1BA)"},
            {"id": "arctic_whisper", "val": 1, "desc": "极寒低语 (使玩家下回合少抽 1 张牌)"}
        ]
    },
    "远古红龙": {
        "name": "远古红龙",
        "type": "boss",
        "hp": "145",
        "actions": "1A 2BA",
        "passive": "龙威鳞甲 (回合开始无盾时获得 8 护盾；持盾受物理攻击时反弹 2 点火焰伤害并施加 1 层灼烧)",
        "intents": [
            {"id": "summon", "val": 0, "desc": "呼唤魔仆 (召唤魔仆加入战场)"},
            {"id": "defend", "val": 10, "desc": "龙鳞防护 (获得 10 护盾)"},
            {"id": "dragon_roar", "val": 1, "desc": "龙威咆哮 (敌方全体获得 1 层力量)"},
            {"id": "fire_breath", "val": 12, "desc": "喷吐火焰 (造成 12 点火焰伤害，并施加 2 层灼烧)"},
            {"id": "tail_sweep", "val": 6, "desc": "扫尾 (对玩家及所有我方随从造成 6 点钝击伤害)"},
            {"id": "molten_inhale", "val": 16, "desc": "熔火深吸 (获得 16 护盾与熔火蓄力，破盾可打断蓄力并暴露易伤)"},
            {"id": "fireball", "val": 6, "desc": "火球点射 (造成 6 点火焰伤害)"},
            {"id": "inferno_breath", "val": 12, "desc": "炼狱吐息 (对全体造成 12 点火焰伤害与 3 层灼烧，若保留熔火蓄力则伤害 +6)"},
            {"id": "devour_imp", "val": 12, "desc": "吞噬魔仆 (吞噬 1 只魔仆恢复 12 生命并获得 2 层力量；无魔仆时获得 10 护盾)"}
        ],
        "summon_goblin": {
            "name": "魔仆",
            "hp": 5,
            "max_hp": 5,
            "intent_val": 1,
            "intent_desc": "准备攻击 (造成 1 伤害)"
        }
    },
    "腐化之心": {
        "name": "腐化之心",
        "type": "boss",
        "hp": "200",
        "actions": "1A 2BA",
        "passive": "死亡律动 (每当玩家打出一张牌，玩家受到 1 点力场伤害)、坚不可摧 40 (一回合最多受到 40 点伤害)",
        "intents": [
            {"id": "debuff", "val": 0, "desc": "邪恶之语 (将晕眩与苦恼放入玩家牌组)"},
            {"id": "multi_attack", "val": 2, "desc": "血弹喷射 (造成 2 点伤害，重复 8 次)"},
            {"id": "big_attack", "val": 20, "desc": "毁灭之痛 (造成 20 点伤害)"},
            {"id": "strength_buff", "val": 2, "desc": "充能 (获得 2 层力量，使后续伤害增加 2)"},
            {"id": "defend_large", "val": 15, "desc": "暗影护盾 (获得 15 或 20 护盾)"},
            {"id": "defend_normal", "val": 10, "desc": "护盾 (获得 10 护盾)"},
            {"id": "drain_ba", "val": 1, "desc": "虚空之歌 (使玩家下回合失去 1BA)"},
            {"id": "heart_strike", "val": 4, "desc": "心跳重击 (造成 4 伤害)"},
            {"id": "gaze_discard", "val": 1, "desc": "虚无凝视 (迫使玩家随机丢弃 1 张手牌)"},
            {"id": "heart_heal", "val": 10, "desc": "回潮 (恢复 10 生命)"}
        ],
        "cycle_info": [
            "第一回合: 邪恶之语 (将晕眩与苦恼放入玩家牌组) + 暗影护盾(获得 15 护盾) + 虚空之歌 (使玩家下回合失去 1BA)",
            "第二回合: 血弹喷射 (造成 2 点伤害，重复 8 次) + 护盾(获得 10 护盾) + 心跳重击 (造成 4 伤害)",
            "第三回合: 毁灭之痛 (造成 20 点伤害) + 护盾(获得 10 护盾) + 虚无凝视 (迫使玩家随机丢弃 1 张手牌)",
            "第四回合: 充能 (获得 2 层力量，使后续伤害增加 2) + 暗影护盾(获得 20 护盾) + 回潮 (恢复 10 生命)"
        ]
    },
    "雷霆领主": {
        "name": "雷霆领主",
        "type": "boss",
        "hp": "135",
        "actions": "1A 2BA",
        "passive": "雷暴力场 (每只存活雷影魔仆使雷霆领主造成的雷电伤害 +2；回合开始若有护盾则对玩家施加 1 层电击)",
        "intents": [
            {"id": "thunder_strike", "val": 8, "desc": "雷鸣重击 (造成 8 雷鸣伤害，并对玩家施加 2 层电击)"},
            {"id": "lightning_shield", "val": 12, "desc": "闪电护壳 (获得 12 护盾并获得闪电护体)"},
            {"id": "storm_summon", "val": 0, "desc": "呼唤雷云 (召唤一只雷影魔仆)"},
            {"id": "electric_overload", "val": 6, "desc": "电能超载 (获得 2 层力量，造成 6 闪电伤害，下回合失去 1A)"}
        ]
    },
    "虚空之门·尤格-索托斯": {
        "name": "虚空之门·尤格-索托斯",
        "type": "boss",
        "hp": "200",
        "actions": "2A 1BA",
        "passive": "先古庇护 (拥有护盾时，受到伤害的 20% 反弹为力场伤害；回合开始时若拥有护盾则清除自身负面效果)",
        "intents": [
            {"id": "gate_gaze", "val": 12, "desc": "门之凝视 (造成 12 点心灵伤害，对随机随从造成 8 点力场伤害，玩家下回合无法抽牌)"},
            {"id": "void_storm", "val": 8, "desc": "虚空风暴 (对玩家与所有我方随从造成 8 点力场伤害)"},
            {"id": "ancient_resonance", "val": 20, "desc": "先古共鸣 (获得 20 点护盾，且下回合获得 2 层力量)"},
            {"id": "void_corruption", "val": 8, "desc": "虚空腐蚀 (造成 8 点强酸伤害并施加 1 层虚空虚弱)"},
            {"id": "gravity_press", "val": 10, "desc": "重力压迫 (造成 10 点钝击伤害，如果玩家身上有护盾，额外损失 5 点护盾；对随机随从造成 6 点钝击伤害)"},
            {"id": "void_exhaust", "val": 1, "desc": "虚空耗竭 (使玩家获得 1 层虚空耗竭 Buff)"},
            {"id": "decay_whisper", "val": 2, "desc": "衰退低语 (使玩家获得 2 层虚空虚弱 Buff)"},
            {"id": "mana_block", "val": 1, "desc": "魔力阻断 (使玩家获得 1 层魔力泄漏 Buff)"},
            {"id": "dimensional_distortion", "val": 15, "desc": "维度扭曲 (获得 15 点护盾)"}
        ]
    },
    "【觉醒】虚空之门·尤格-索托斯": {
        "name": "【觉醒】虚空之门·尤格-索托斯",
        "type": "boss",
        "hp": "260",
        "actions": "2A 2BA",
        "passive": "终焉之门 (每回合开始获得 15 点护盾并清除自身负面效果；拥有护盾时，受到伤害会反弹 1 点真实伤害)",
        "intents": [
            {"id": "time_collapse", "val": 14, "desc": "时空坍缩 (造成 14 点力场伤害，玩家下回合动作减少 1A 1BA，且洗入 2 张空间撕裂)"},
            {"id": "all_gates_open", "val": 20, "desc": "万门齐开 (召唤 2 个虚空潜伏者，敌方全体获得 2 层力量；若格子满则造成 20 点心灵伤害)"},
            {"id": "doomsday_tide", "val": 12, "desc": "灭世之潮 (对玩家与所有随从造成 12 点真实伤害，穿透护盾，并恢复自身 15 点生命值)"},
            {"id": "chaos_beam", "val": 10, "desc": "混乱光束 (造成 10 点光耀伤害，对所有随从造成 6 点光耀伤害)"},
            {"id": "abyss_gaze", "val": 12, "desc": "深渊凝视 (造成 12 点心灵伤害，使玩家下回合少抽 2 张牌)"},
            {"id": "abyss_exhaust", "val": 1, "desc": "深渊耗竭 (使玩家获得 1 层虚空耗竭 Buff)"},
            {"id": "void_shield_large", "val": 20, "desc": "虚空大盾 (获得 20 点护盾并净化自身 1 负面 Buff)"},
            {"id": "end_whisper", "val": 6, "desc": "终焉低语 (造成 6 点心灵伤害，且迫使玩家随机丢弃 1 张手牌)"},
            {"id": "strength_infuse", "val": 2, "desc": "力量注入 (敌方全体获得 2 层力量)"},
            {"id": "reality_shatter", "val": 8, "desc": "现实碎裂 (造成 8 点真实伤害)"}
        ]
    },
    "【终焉】虚空之门·尤格-索托斯": {
        "name": "【终焉】虚空之门·尤格-索托斯",
        "type": "boss",
        "hp": "300",
        "actions": "3A 2BA",
        "passive": "终焉庇护 (每回合开始获得 20 护盾与 2 层力量；拥有护盾时，受到伤害会反弹 1 点真实伤害与 2 点力场伤害)",
        "intents": [
            {"id": "time_collapse", "val": 14, "desc": "时空坍缩 (造成 14 点力场伤害，玩家下回合动作减少 1A 1BA，且洗入 2 张空间撕裂)"},
            {"id": "all_gates_open", "val": 20, "desc": "万门齐开 (召唤 2 个虚空潜伏者，敌方全体获得 2 层力量；若格子满则造成 20 点心灵伤害)"},
            {"id": "doomsday_tide", "val": 12, "desc": "灭世之潮 (对玩家与所有随从造成 12 点真实伤害，穿透护盾，并恢复自身 15 点生命值)"},
            {"id": "chaos_beam", "val": 10, "desc": "混乱光束 (造成 10 点光耀伤害，对所有随从造成 6 点光耀伤害)"},
            {"id": "abyss_gaze", "val": 12, "desc": "深渊凝视 (造成 12 点心灵伤害，使玩家下回合少抽 2 张牌)"},
            {"id": "abyss_exhaust", "val": 1, "desc": "深渊耗竭 (使玩家获得 1 层虚空耗竭 Buff)"},
            {"id": "void_shield_large", "val": 20, "desc": "虚空大盾 (获得 20 点护盾并净化自身 1 负面 Buff)"},
            {"id": "end_whisper", "val": 6, "desc": "终焉低语 (造成 6 点心灵伤害，且迫使玩家随机丢弃 1 张手牌)"},
            {"id": "strength_infuse", "val": 2, "desc": "力量注入 (敌方全体获得 2 层力量)"},
            {"id": "reality_shatter", "val": 8, "desc": "现实碎裂 (造成 8 点真实伤害)"}
        ]
    },
    "亚弗戈蒙": {
        "name": "亚弗戈蒙",
        "type": "boss",
        "hp": "180",
        "actions": "2A 1BA",
        "intents": [
            {"id": "chain_of_time", "val": 8, "desc": "时间之链 (造成 8 点力场伤害，使玩家下回合减少 1A)"},
            {"id": "portal_implosion", "val": 15, "desc": "门扉内爆 (造成 15 点钝击伤害，若玩家有护盾额外造成 5 点伤害)"},
            {"id": "time_warp", "val": 0, "desc": "时空扭曲 (获得 15 点护盾，下回合获得 1 层力量)"}
        ]
    },
    "【时空主宰】亚弗戈蒙": {
        "name": "【时空主宰】亚弗戈蒙",
        "type": "boss",
        "hp": "220",
        "actions": "3A 1BA",
        "passive": "时空主宰 (每回合开始获得 20 护盾，且清除自身所有负面效果；受到伤害时 50% 几率召唤时空残影；分担 50% 伤害)",
        "intents": [
            {"id": "time_fracture", "val": 12, "desc": "时序断裂 (造成 12 点力场伤害，并使玩家手牌除首张外全部获得【易碎 1】磨损)"},
            {"id": "silver_bell_clang", "val": 15, "desc": "银钟轰鸣 (造成 15 点雷鸣伤害，若玩家已受【钟摆共振】则额外造成 5 点真实伤害，否则对其施加【钟摆共振】)"},
            {"id": "time_reflux", "val": 0, "desc": "时空回退 (获得 20 点护盾并恢复自身 25 点生命值)"},
            {"id": "temporal_lock", "val": 5, "desc": "时间锁定 (造成 5 点心灵伤害，且迫使玩家随机丢弃 1 张手牌)"}
        ]
    },
    "纯粹容器": {
        "name": "纯粹容器",
        "type": "boss",
        "hp": "155",
        "actions": "2A 1BA",
        "passive": "空洞之躯 (免疫流血与中毒，每回合开始移除 1 层负面状态；骨钉招架期间受物理攻击将反击 8 点挥砍伤害，破盾可解除招架并使其暴露轻度易伤)",
        "intents": [
            {"id": "triple_slash", "val": 4, "desc": "三连挥砍 (造成 4 点挥砍伤害，连续 3 次)"},
            {"id": "shining_lunge", "val": 9, "desc": "闪耀突刺 (造成 9 点穿刺伤害)"},
            {"id": "nail_parry", "val": 12, "desc": "骨钉招架 (获得 12 护盾并进入骨钉招架反击状态)"},
            {"id": "soul_daggers", "val": 7, "desc": "灵魂刃幕 (对全体造成 7 点力场伤害，并使玩家下回合失去 1BA)"},
            {"id": "desolate_dive", "val": 10, "desc": "荒芜俯冲 (造成 10 点光耀伤害，有护盾时额外削减 5 点护盾)"},
            {"id": "vessel_guard", "val": 10, "desc": "外壳硬化 (获得 10 护盾)"},
            {"id": "focus_channel", "val": 18, "desc": "纯白聚焦 (获得 18 护盾并凝聚圣环，破盾可打断后续治疗)"},
            {"id": "pale_wave", "val": 8, "desc": "苍白剑气 (造成 8 点光耀伤害)"},
            {"id": "focus_bloom", "val": 13, "desc": "聚焦圣环 (对全体造成 13 点光耀伤害，若聚焦未被打断则恢复 12 生命并获得 2 层力量)"},
            {"id": "void_tendrils", "val": 12, "desc": "虚空触手 (造成 12 点黯蚀伤害，使玩家下回合失去 1A 并施加 1 层虚空虚弱)"},
            {"id": "abyss_gaze", "val": 1, "desc": "空洞凝视 (对玩家施加 1 层轻度易伤)"}
        ]
    },
    "伟大的克苏鲁": {
        "name": "伟大的克苏鲁",
        "type": "boss",
        "hp": "150",
        "actions": "2A 1BA",
        "passive": "不朽星体 (受到致命伤害时化为不可名状的迷雾并在 2 回合后满血重组；可用【放逐斩】直接驱逐迷雾，或在其二次复活后通过【拉莱耶星盘】解开三幕群星封印将其彻底击败)",
        "intents": [
            {"id": "call_of_rlyeh", "val": 10, "desc": "拉莱耶的呼唤 (造成 10 点心灵伤害，并向抽牌堆洗入 1 张无形低语)"},
            {"id": "star_spawn_claw", "val": 14, "desc": "巨爪碾压 (造成 14 点钝击伤害，并施加 1 层轻度钝击易伤)"},
            {"id": "sunken_tsunami", "val": 9, "desc": "沉没海啸 (对全体造成 9 点寒冷伤害，有护盾时额外造成 4 点真实伤害)"},
            {"id": "cosmic_regen", "val": 12, "desc": "群星再生 (获得 12 护盾并恢复 8 生命)"},
            {"id": "madness_pulse", "val": 1, "desc": "疯狂脉动 (使玩家下回合失去 1BA 并少抽 1 张牌)"}
        ]
    },
    "【迷雾】伟大的克苏鲁": {
        "name": "【迷雾】伟大的克苏鲁",
        "type": "boss",
        "hp": "1",
        "actions": "1A 0BA",
        "passive": "星体迷雾 (免疫常规伤害，2 回合后满血重塑肉身；唯【放逐斩】或警觉号冲撞可将其彻底放逐)",
        "intents": [
            {"id": "mist_condense_1", "val": 5, "desc": "迷雾翻涌 (剩余 2 回合重组，对全体造成 5 点心灵伤害并获得 1 层力量)"},
            {"id": "mist_condense_2", "val": 150, "desc": "肉身重塑 (剩余 1 回合重组，回合末满血复活为伟大的克苏鲁)"}
        ]
    }
}

BOSS_POOLS = {
    "early": ["远古红龙", "雷霆领主", "纯粹容器"],
    "gate": ["腐化之心", "Icerainboww", "伟大的克苏鲁"],
    "aforgomon": ["亚弗戈蒙"],
    "final": ["虚空之门·尤格-索托斯"]
}
