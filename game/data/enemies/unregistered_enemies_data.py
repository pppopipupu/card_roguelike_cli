CAFE_KEY_TO_ENTITY = {
    "Guide_Elder": "向导长老",
    "Bartender_Jack": "酒保杰克",
    "Blacksmith_Ironclad": "铁匠艾恩克拉德",
}

YOG_BOSS_ENTITY_NAMES = frozenset({
    "虚空之门·尤格-索托斯",
    "【觉醒】虚空之门·尤格-索托斯",
    "【终焉】虚空之门·尤格-索托斯",
    "【万物归一】虚空之门·尤格-索托斯",
})

UNREGISTERED_ENEMY_CONFIG = {
    "雪原狼": {
        "name": "雪原狼",
        "hp": "20",
        "type": "normal",
        "actions": "1A 0BA",
        "intents": [
            {"id": "wolf_pounce", "val": 6, "desc": "冰原扑咬 (造成 6 点穿刺伤害，施加 1 层流血)"},
            {"id": "wolf_pack_howl", "val": 5, "desc": "群狼低嚎 (获得 5 点护盾与 1 层力量)"},
        ],
    },
    "霜牙巨狼": {
        "name": "霜牙巨狼",
        "hp": "46",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "frostfang_rend", "val": 11, "desc": "霜牙撕裂 (造成 11 点寒冷伤害，施加 1 层虚弱)"},
            {"id": "blizzard_howl", "val": 10, "desc": "暴风雪嚎叫 (获得 10 点护盾与 2 层力量)"},
            {"id": "glacial_lunge", "val": 14, "desc": "寒冰扑杀 (造成 14 点穿刺伤害)"},
        ],
    },
    "游荡魔物群": {
        "name": "游荡魔物群",
        "hp": "28+",
        "type": "normal",
        "actions": "1A 0BA",
        "intents": [
            {"id": "pack_ambush", "val": 6, "desc": "群怪伏击 (造成 6 点穿刺伤害，施加 1 层流血)"},
            {"id": "huddle_guard", "val": 6, "desc": "抱团警戒 (获得 6 点护盾与 1 层力量)"},
            {"id": "frenzied_claw", "val": 8, "desc": "乱爪撕扯 (造成 8 点挥砍伤害)"},
        ],
    },
    "深渊精英守卫": {
        "name": "深渊精英守卫",
        "hp": "60+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "halberd_sweep", "val": 10, "desc": "重戟横扫 (造成 10 点挥砍伤害，削减 4 点护盾)"},
            {"id": "abyss_bulwark", "val": 12, "desc": "深渊铁壁 (获得 12 点护盾与 2 层力量)"},
            {"id": "execution_cleave", "val": 15, "desc": "处刑下劈 (造成 15 点重击伤害)"},
        ],
    },
    "裂隙高危魔物": {
        "name": "裂隙高危魔物",
        "hp": "70+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "miasma_breath", "val": 11, "desc": "虚空瘴气吐息 (造成 11 点黯蚀伤害，施加 1 层虚弱)"},
            {"id": "rift_distortion", "val": 12, "desc": "空间扭曲护膜 (获得 12 点护盾并回复 5 点生命)"},
            {"id": "dimensional_rend", "val": 16, "desc": "裂隙撕裂暴走 (造成 16 点真实力场伤害)"},
        ],
    },
    "层关镇守领主": {
        "name": "层关镇守领主",
        "hp": "120+",
        "type": "boss",
        "actions": "1A 1BA",
        "intents": [
            {"id": "lord_pressure", "val": 13, "desc": "王者威压斩 (造成 13 点力场伤害，施加 1 层虚弱)"},
            {"id": "sovereign_plate", "val": 15, "desc": "领主黑甲 (获得 15 点护盾与 2 层力量)"},
            {"id": "floor_verdict", "val": 18, "desc": "镇守裁决 (造成 18 点毁灭伤害)"},
        ],
    },
    "裂隙隐秘首领": {
        "name": "裂隙隐秘首领",
        "hp": "150+",
        "type": "boss",
        "actions": "1A 1BA",
        "intents": [
            {"id": "secret_quake", "val": 14, "desc": "隐秘星渊震荡 (造成 14 点心灵伤害并塞入 1 张晕眩)"},
            {"id": "abyss_mirage", "val": 16, "desc": "深渊虚影屏障 (获得 16 点护盾与 2 层力量)"},
            {"id": "annihilation_wave", "val": 20, "desc": "里界湮灭波 (造成 20 点虚空真实伤害)"},
        ],
    },
    "同僚怨灵": {
        "name": "同僚怨灵",
        "hp": "38+",
        "type": "normal",
        "actions": "1A 0BA",
        "intents": [
            {"id": "wraith_wail", "val": 7, "desc": "旧日执念悲鸣 (造成 7 点心灵伤害，施加 1 层虚弱)"},
            {"id": "spectral_fade", "val": 8, "desc": "灵体虚化 (获得 8 点护盾并回复 4 点生命)"},
            {"id": "soul_backstab", "val": 11, "desc": "幽魂背刺 (造成 11 点黯蚀伤害)"},
        ],
    },
    "军械魔像": {
        "name": "军械魔像",
        "hp": "56+",
        "type": "elite",
        "actions": "1A 0BA",
        "intents": [
            {"id": "iron_cannon", "val": 10, "desc": "锻铁重炮 (造成 10 点钝击伤害，剥夺玩家 1 点 BA)"},
            {"id": "gear_armor", "val": 13, "desc": "齿轮合金装甲 (获得 13 点护盾与 2 层力量)"},
            {"id": "sawblade_spin", "val": 13, "desc": "旋转锯刃横扫 (造成 13 点挥砍伤害，施加 2 层流血)"},
        ],
    },
    "墓穴守卫": {
        "name": "墓穴守卫",
        "hp": "50+",
        "type": "elite",
        "actions": "1A 0BA",
        "intents": [
            {"id": "crypt_spear", "val": 9, "desc": "墓室长矛穿刺 (造成 9 点穿刺伤害，施加 2 层流血)"},
            {"id": "sarcophagus_block", "val": 11, "desc": "古石棺盖格挡 (获得 11 点护盾并回复 4 点生命)"},
            {"id": "undead_vengeance", "val": 12, "desc": "亡灵复仇 (造成 12 点黯蚀伤害)"},
        ],
    },
    "星渊哨兵": {
        "name": "星渊哨兵",
        "hp": "54+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "star_laser", "val": 10, "desc": "星辉激光束 (造成 10 点光耀伤害，施加 1 层电击)"},
            {"id": "stardust_field", "val": 11, "desc": "星尘力场护罩 (获得 11 点护盾与 1 层力量)"},
            {"id": "coordinate_meteor", "val": 14, "desc": "坐标锁定坠星 (造成 14 点力场伤害)"},
        ],
    },
    "向导长老": {
        "name": "向导长老",
        "hp": "70+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "elder_cane", "val": 8, "desc": "长老竹杖敲击 (造成 8 点钝击伤害，施加 1 层虚弱)"},
            {"id": "tea_meditation", "val": 10, "desc": "茶水静心 (获得 10 点护盾并回复 5 点生命)"},
            {"id": "hegemon_star_gaze", "val": 14, "desc": "霸瞳天星占卜 (造成 14 点心灵冲击)"},
        ],
    },
    "酒保杰克": {
        "name": "酒保杰克",
        "hp": "70+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "void_spirit_splash", "val": 9, "desc": "虚空烈酒泼洒 (造成 9 点火焰伤害，施加 2 层灼烧)"},
            {"id": "bar_polish_guard", "val": 10, "desc": "吧台擦杯架势 (获得 10 点护盾与 2 层力量)"},
            {"id": "flaming_barrel", "val": 14, "desc": "烈焰调酒桶 (造成 14 点火焰爆发伤害)"},
        ],
    },
    "铁匠艾恩克拉德": {
        "name": "铁匠艾恩克拉德",
        "hp": "75+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "starburst_hammer", "val": 11, "desc": "星爆锻锤 (造成 11 点钝击伤害，削减 4 点护盾)"},
            {"id": "forge_bulwark", "val": 12, "desc": "铸甲护壁 (获得 12 点护盾与 2 层力量)"},
            {"id": "molten_anvil", "val": 15, "desc": "超载炽铁震击 (造成 15 点火焰伤害)"},
        ],
    },
    "杰斯": {
        "name": "卡牌大师 · 杰斯",
        "hp": "70+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "wild_card_toss", "val": 9, "desc": "跨界疾风飞牌 (造成 9 点穿刺伤害，塞入 1 张晕眩)"},
            {"id": "arcane_card_wall", "val": 10, "desc": "秘术护牌阵 (获得 10 点护盾与 1 层力量)"},
            {"id": "trump_volley", "val": 13, "desc": "王牌齐射 (造成 13 点力场伤害)"},
        ],
    },
    "艾琳": {
        "name": "宝石琢磨师 · 艾琳",
        "hp": "70+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "crystal_splinter", "val": 8, "desc": "碎晶飞溅 (造成 8 点穿刺伤害，施加 2 层流血)"},
            {"id": "prism_refraction", "val": 11, "desc": "折射棱镜盾 (获得 11 点护盾与 1 层力量)"},
            {"id": "legendary_gem_burst", "val": 13, "desc": "传奇宝石爆破 (造成 13 点光耀伤害)"},
        ],
    },
    "雷恩": {
        "name": "退役角斗士 · 雷恩",
        "hp": "75+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "arena_shoulder_bash", "val": 10, "desc": "角斗士冲撞 (造成 10 点钝击伤害并获得 4 点护盾)"},
            {"id": "shield_roar", "val": 12, "desc": "战吼架盾 (获得 12 点护盾与 2 层力量)"},
            {"id": "blood_oath_cleave", "val": 15, "desc": "血誓狂劈 (造成 15 点挥砍伤害)"},
        ],
    },
    "露娜": {
        "name": "迷路占星师 · 露娜",
        "hp": "68+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "astrolabe_omen", "val": 8, "desc": "星盘预言 (造成 8 点心灵伤害，施加 1 层虚弱)"},
            {"id": "lunar_veil", "val": 10, "desc": "月影星幕 (获得 10 点护盾并回复 4 点生命)"},
            {"id": "star_crash", "val": 15, "desc": "星界坠击 (造成 15 点力场伤害)"},
        ],
    },
    "莫里": {
        "name": "流浪厨师 · 莫里",
        "hp": "70+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "ladle_whack", "val": 9, "desc": "滚烫锅勺敲头 (造成 9 点火焰伤害，施加 1 层灼烧)"},
            {"id": "broth_tasting", "val": 10, "desc": "暗黑浓汤试吃 (获得 10 点护盾并回复 5 点生命)"},
            {"id": "void_donut_throw", "val": 11, "desc": "虚空甜甜圈投掷 (造成 11 点毒素伤害并塞入 1 张晕眩)"},
        ],
    },
    "凯尔": {
        "name": "遗迹猎人 · 凯尔",
        "hp": "70+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "relic_hook", "val": 9, "desc": "寻宝猎钩 (造成 9 点穿刺伤害，削减 4 点护盾)"},
            {"id": "antique_ward", "val": 10, "desc": "古物防壁 (获得 10 点护盾与 1 层力量)"},
            {"id": "trap_salvo", "val": 13, "desc": "机关陷阱连发 (造成 13 点穿刺伤害，施加 1 层流血)"},
        ],
    },
    "咪咪": {
        "name": "会说话的猫 · 咪咪",
        "hp": "65+",
        "type": "normal",
        "actions": "1A 1BA",
        "intents": [
            {"id": "cat_scratch", "val": 8, "desc": "猫猫抓痕 (造成 8 点穿刺伤害，施加 2 层流血)"},
            {"id": "purr_evasion", "val": 11, "desc": "竖尾撒娇回避 (获得 11 点护盾并回复 4 点生命)"},
            {"id": "golden_paw_flurry", "val": 12, "desc": "喵呜金爪连抓 (造成 12 点挥砍伤害)"},
        ],
    },
    "萨拉": {
        "name": "虚空缝纫师 · 萨拉",
        "hp": "70+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "void_thread_bind", "val": 8, "desc": "虚空金线缠绕 (造成 8 点黯蚀伤害，剥夺玩家 1 点 BA)"},
            {"id": "retain_weave", "val": 11, "desc": "保留织物护罩 (获得 11 点护盾与 1 层力量)"},
            {"id": "fission_scissors", "val": 14, "desc": "裂变剪裁 (造成 14 点挥砍伤害)"},
        ],
    },
    "辛普森": {
        "name": "狂热诗人 · 辛普森",
        "hp": "68+",
        "type": "normal",
        "actions": "1A 1BA",
        "intents": [
            {"id": "offkey_sonic", "val": 8, "desc": "跑调重音音波 (造成 8 点心灵伤害，施加 1 层虚弱)"},
            {"id": "heroic_ballad", "val": 9, "desc": "英雄赞歌自励 (获得 9 点护盾与 2 层力量)"},
            {"id": "finale_solo", "val": 13, "desc": "终章高音独唱 (造成 13 点力场伤害)"},
        ],
    },
    "斯莱克": {
        "name": "黑市宝石商 · 斯莱克",
        "hp": "70+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "smuggled_fume", "val": 8, "desc": "走私毒烟 (造成 8 点毒素伤害，施加 2 层中毒)"},
            {"id": "stash_buckler", "val": 12, "desc": "暗格防弹盾 (获得 12 点护盾)"},
            {"id": "backstab_deal", "val": 14, "desc": "黑吃黑背刺 (造成 14 点穿刺伤害)"},
        ],
    },
    "编号7": {
        "name": "沉睡的古老守卫 · 编号7",
        "hp": "80+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "pulse_gauntlet", "val": 10, "desc": "脉冲机械臂 (造成 10 点闪电伤害，施加 1 层电击)"},
            {"id": "alloy_shell", "val": 14, "desc": "合金过载护壳 (获得 14 点护盾与 2 层力量)"},
            {"id": "overload_beam", "val": 15, "desc": "自爆警戒激光 (造成 15 点力场伤害)"},
        ],
    },
    "绯红": {
        "name": "神秘红衣女士 · 绯红",
        "hp": "76+",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "blood_rose_whip", "val": 10, "desc": "鲜血蔷薇鞭 (造成 10 点穿刺伤害，施加 2 层流血)"},
            {"id": "crimson_waltz", "val": 11, "desc": "红裙优雅回旋 (获得 11 点护盾并回复 5 点生命)"},
            {"id": "scarlet_curtain", "val": 15, "desc": "猩红魅惑终舞 (造成 15 点心灵伤害)"},
        ],
    },
    "【万物归一】虚空之门·尤格-索托斯": {
        "name": "【万物归一】虚空之门·尤格-索托斯",
        "hp": "极高 (终极觉醒形态)",
        "type": "boss",
        "actions": "多段终局行动",
        "intents": [
            {"id": "all_in_one_strike", "desc": "时空归一破灭：贯通时间线与护盾的毁灭打击，随阶段不断改写战斗规则"},
            {"id": "outer_god_gaze", "desc": "超越一切视界的注视：彻底无视常规隐身与遮蔽"},
        ],
    },
    "【觉醒】pppopipupu": {
        "name": "【觉醒】pppopipupu",
        "hp": "9999",
        "type": "boss",
        "actions": "1A 0BA",
        "intents": [
            {"id": "force_strike", "val": 100, "desc": "虚空拉竿猛击 (对玩家造成 100 点力场伤害)"},
        ],
    },
    "Gate_Guardian": {
        "name": "Gate_Guardian",
        "hp": "300",
        "type": "boss",
        "actions": "1A 0BA",
        "intents": [
            {"id": "slash", "val": 12, "desc": "门卫重斩 (造成 12 点物理伤害)"},
            {"id": "block", "val": 15, "desc": "铁闸护盾 (获得 15 点护盾)"},
            {"id": "bash", "val": 20, "desc": "守门粉碎击 (造成 20 点高额重击)"},
        ],
    },
    "DeepSeek": {
        "name": "DeepSeek",
        "hp": "26 (+ 2 * 关卡数)",
        "type": "normal",
        "actions": "1A 0BA",
        "intents": [
            {"id": "deepseek_infer", "desc": "深度推理打击与算法护壁轮换"},
        ],
    },
    "星辉教团·持烛教徒": {
        "name": "星辉教团·持烛教徒",
        "hp": "30",
        "type": "normal",
        "actions": "1A 0BA",
        "intents": [
            {"id": "candle_chant", "desc": "霜烛灼击与冰霜护祷轮转"},
        ],
    },
    "星辉教团·咏唱者": {
        "name": "星辉教团·咏唱者",
        "hp": "34",
        "type": "normal",
        "actions": "1A 0BA",
        "intents": [
            {"id": "star_hymn", "desc": "星辉哀歌心灵冲击与群体护盾"},
        ],
    },
    "星辉教团·执刃者": {
        "name": "星辉教团·执刃者",
        "hp": "40",
        "type": "normal",
        "actions": "1A 0BA",
        "intents": [
            {"id": "frozen_blade", "desc": "霜刃重斩与架势反击"},
        ],
    },
    "星辉教团·守夜人": {
        "name": "星辉教团·守夜人",
        "hp": "48",
        "type": "elite",
        "actions": "1A 0BA",
        "intents": [
            {"id": "vigil_strike", "desc": "极夜巡哨打击与寒冰铁壁"},
        ],
    },
    "星辉教团·疯癫祭司": {
        "name": "星辉教团·疯癫祭司",
        "hp": "52",
        "type": "elite",
        "actions": "1A 0BA",
        "intents": [
            {"id": "mad_ritual", "desc": "疯狂献祭咒文与冰霜诅咒"},
        ],
    },
    "星辉教团·内殿守卫": {
        "name": "星辉教团·内殿守卫",
        "hp": "58",
        "type": "elite",
        "actions": "1A 0BA",
        "intents": [
            {"id": "inner_guard", "desc": "霜甲重戟与内殿守护阵"},
        ],
    },
    "镜中残影": {
        "name": "镜中残影",
        "hp": "44",
        "type": "elite",
        "actions": "1A 0BA",
        "intents": [
            {"id": "mirror_echo", "desc": "冰镜折射心灵裂击与镜像幻盾"},
        ],
    },
    "叛教哨兵": {
        "name": "叛教哨兵",
        "hp": "36",
        "type": "normal",
        "actions": "1A 0BA",
        "intents": [
            {"id": "renegade_shot", "desc": "雪原狙击与破冰突刺"},
        ],
    },
    "冰封少女·欧吕尔的化身": {
        "name": "冰封少女·欧吕尔的化身",
        "hp": "160",
        "type": "boss",
        "actions": "1A 1BA",
        "intents": [
            {"id": "auril_frost", "desc": "极寒降临、冰霜护甲、终极暴雪多阶段切换"},
        ],
    },
    "噬念心魔": {
        "name": "噬念心魔",
        "hp": "64",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "mind_devour", "desc": "吞噬理智心灵重创与幻影虚化"},
        ],
    },
    "静默守门者": {
        "name": "静默守门者",
        "hp": "76",
        "type": "elite",
        "actions": "1A 1BA",
        "intents": [
            {"id": "silent_seal", "desc": "静默镇压打击与位面铁壁"},
        ],
    },
    "锻炉残响": {
        "name": "锻炉残响",
        "hp": "88",
        "type": "boss",
        "actions": "1A 1BA",
        "intents": [
            {"id": "forge_echo_slam", "desc": "炎炉余烬重砸、过热熔岩护罩与高热爆发"},
        ],
    },
}
