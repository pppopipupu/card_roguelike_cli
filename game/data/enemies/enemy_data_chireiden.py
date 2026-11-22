SUPER_PORTAL_PHASES = [
    {
        "phase": 1,
        "name": "彭宁离子井·超级传送门·初阶裂隙",
        "hp": 220,
        "actions": (2, 1),
        "buff_id": "penning_xen_rift_p1",
        "summon_pool": ["Xen猎头蟹", "Xen猎犬眼"],
        "summon_batch": 1,
    },
    {
        "phase": 2,
        "name": "彭宁离子井·超级传送门·二阶扩口",
        "hp": 280,
        "actions": (2, 1),
        "buff_id": "penning_xen_rift_p2",
        "summon_pool": ["Xen猎头蟹", "Xen猎犬眼", "Xen弗地冈"],
        "summon_batch": 1,
    },
    {
        "phase": 3,
        "name": "彭宁离子井·超级传送门·三阶超临界",
        "hp": 360,
        "actions": (2, 2),
        "buff_id": "penning_xen_rift_p3",
        "summon_pool": ["Xen猎犬眼", "Xen弗地冈", "Xen牛鱿"],
        "summon_batch": 2,
    },
    {
        "phase": 4,
        "name": "彭宁离子井·超级传送门·四阶终焉极井",
        "hp": 460,
        "actions": (3, 2),
        "buff_id": "penning_xen_rift_p4",
        "summon_pool": ["Xen弗地冈", "Xen牛鱿", "Xen控制器"],
        "summon_batch": 2,
    },
]

SUPER_PORTAL_PHASE_BY_NAME = {p["name"]: p for p in SUPER_PORTAL_PHASES}

SUPER_PORTAL_MAX_XEN_ALIVE = 4

UTSUHO_INTENT_CYCLE = (
    "utsuho_d_he3_ray",
    "utsuho_elevator_logistics",
    "utsuho_tokamak_flare",
    "utsuho_subterranean_sun",
)

CHIREIDEN_NORMAL_ENCOUNTERS = [
    ["非想天则涡轮机兵", "月都氦三物流机"],
    ["铅铋液态金属怪", "非想天则涡轮机兵"],
    ["托卡马克电弧守卫", "月都氦三物流机"],
]

CHIREIDEN_HIGH_DANGER_ENCOUNTERS = [
    ["托卡马克电弧守卫", "铅铋液态金属怪", "月都氦三物流机"],
    ["非想天则涡轮机兵", "托卡马克电弧守卫"],
]

CHIREIDEN_ELITE_ENCOUNTER = ["火焰猫燐", "铅铋液态金属怪"]
CHIREIDEN_UTSUHO_ENCOUNTER = ["灵乌路空"]
CHIREIDEN_PORTAL_ENCOUNTER = ["彭宁离子井·超级传送门·初阶裂隙"]

ENEMY_CHIREIDEN_CONFIG = {
    "非想天则涡轮机兵": {
        "name": "非想天则涡轮机兵",
        "size": "large",
        "type": "normal",
        "hp": "68",
        "actions": "1A 1BA",
        "passive": "非想天则时代重装蒸汽装甲，擅长高压涡轮重砸与蒸汽护盾再生",
        "intents": [
            {"id": "turbine_steam_slam", "val": 14, "desc": "高压涡轮重压 (造成 14 点钝击伤害)"},
            {"id": "turbine_shield_vent", "val": 12, "desc": "蒸汽泄压装甲 (获得 12 点护盾并附加 2 层力量)"},
        ],
    },
    "月都氦三物流机": {
        "name": "月都氦三物流机",
        "size": "medium",
        "type": "normal",
        "hp": "54",
        "actions": "1A 1BA",
        "passive": "太空电梯高速分拣无人单元，能投射校准激光并空投氦三爆燃罐",
        "intents": [
            {"id": "drone_orbital_laser", "val": 12, "desc": "物流轨道校正激光 (造成 12 点力场伤害)"},
            {"id": "drone_he3_drop", "val": 10, "desc": "氦三高爆罐空投 (造成 10 点火焰群体冲击并增益敌方护盾)"},
        ],
    },
    "铅铋液态金属怪": {
        "name": "铅铋液态金属怪",
        "size": "large",
        "type": "normal",
        "hp": "76",
        "actions": "1A 1BA",
        "passive": "从快堆溢流槽聚形的高比重液态金属聚合体，防御稳固且攻击灼热",
        "intents": [
            {"id": "lbe_molten_splash", "val": 13, "desc": "沸腾铅铋泼溅 (造成 13 点火焰伤害并附加 2 层虚弱)"},
            {"id": "lbe_dense_wall", "val": 16, "desc": "液态重金属凝壁 (获得 16 点护盾并回复 8 点生命)"},
        ],
    },
    "托卡马克电弧守卫": {
        "name": "托卡马克电弧守卫",
        "size": "large",
        "type": "normal",
        "hp": "82",
        "actions": "2A 0BA",
        "passive": "环形超导磁笼护卫，电弧攻击可自我充能并强化同伴",
        "intents": [
            {"id": "tokamak_arc_sweep", "val": 15, "desc": "环形强电弧清扫 (造成 15 点闪电伤害)"},
            {"id": "tokamak_field_lock", "val": 12, "desc": "磁流体脉冲增压 (敌方全体获得 12 点护盾与 2 层力量)"},
        ],
    },
    "火焰猫燐": {
        "name": "火焰猫燐",
        "size": "medium",
        "type": "elite",
        "hp": "145",
        "actions": "1A 1BA",
        "passive": "铅铋热惯性：掌控地灵殿铅铋快堆循环系统，每回合凝聚金属护膜并以怨灵车轮冲击阵线",
        "intents": [
            {"id": "rin_cat_wheel_charge", "val": 18, "desc": "火猫怨灵战车冲锋 (造成 18 点火焰冲击并附加 2 层易伤)"},
            {"id": "rin_lbe_quench_guard", "val": 20, "desc": "铅铋快堆淬火护膜 (获得 20 点护盾并回复 12 点生命，获得 2 层磁约束场)"},
            {"id": "rin_corpse_ash_nova", "val": 14, "desc": "灼热地狱鬼火阵 (全体敌人获得 2 层力量，对所有我方造成 14 点火焰伤害)"},
        ],
    },
    "灵乌路空": {
        "name": "灵乌路空",
        "size": "large",
        "type": "boss",
        "hp": "210",
        "actions": "2A 1BA",
        "passive": "穿戴智力头环：通过月之都太空电梯统筹氦三物流补给，每回合高能叠加 D-He3 聚变超载并释放超高温聚变射线",
        "intents": [
            {"id": "utsuho_d_he3_ray", "val": 16, "desc": "D-He3 精准点火射线 (造成 16 点火焰伤害并获得 2 层聚变超载)"},
            {"id": "utsuho_elevator_logistics", "val": 18, "desc": "月都太空电梯氦三补给校准 (获得 18 点护盾、2 层力量与 3 层聚变超载)"},
            {"id": "utsuho_tokamak_flare", "val": 14, "desc": "头环·托卡马克太阳黑子爆 (全体伤害 14 点火焰并造成 2 层灼烧)"},
            {"id": "utsuho_subterranean_sun", "val": 24, "desc": "伪狱热核终焉日轮 (超高能聚变重击，造成 24 点火焰辐射伤害)"},
        ],
    },
    "彭宁离子井·超级传送门·初阶裂隙": {
        "name": "彭宁离子井·超级传送门·初阶裂隙",
        "size": "gargantuan",
        "type": "boss",
        "hp": "220",
        "actions": "2A 1BA",
        "passive": "彭宁裂缝四阶传送门（一阶）：无反弹亦无控牌技能；纯靠庞大生命壁垒与源源不断召唤 Xen 猎群推进",
        "intents": [
            {"id": "portal_summon_swarm", "val": 1, "desc": "开启彭宁传送门·投放 Xen 群落 (召唤 Xen 异界单元并全敌强化)"},
            {"id": "portal_ion_beam", "val": 16, "desc": "四极直流离子贯穿束 (造成 16 点闪电伤害)"},
            {"id": "portal_magnetic_pulse", "val": 16, "desc": "强磁约束过载震荡 (获得 16 点护盾与 2 层力量)"},
            {"id": "portal_xen_bombard", "val": 12, "desc": "超级传送门·异界维度齐射 (对我方全体造成 12 点力场伤害)"},
        ],
    },
    "彭宁离子井·超级传送门·二阶扩口": {
        "name": "彭宁离子井·超级传送门·二阶扩口",
        "size": "gargantuan",
        "type": "boss",
        "hp": "280",
        "actions": "2A 1BA",
        "passive": "彭宁裂缝（二阶）：扩口后灵乌路空从侧面回路介入我方阵线协助封门；传送门加速投送高阶 Xen 单位",
        "intents": [
            {"id": "portal_summon_swarm", "val": 1, "desc": "开启彭宁传送门·投放 Xen 群落 (召唤 Xen 异界单元并全敌强化)"},
            {"id": "portal_ion_beam", "val": 18, "desc": "四极直流离子贯穿束 (造成 18 点闪电伤害)"},
            {"id": "portal_magnetic_pulse", "val": 18, "desc": "强磁约束过载震荡 (获得 18 点护盾与 3 层力量)"},
            {"id": "portal_xen_bombard", "val": 14, "desc": "超级传送门·异界维度齐射 (对我方全体造成 14 点力场伤害)"},
        ],
    },
    "彭宁离子井·超级传送门·三阶超临界": {
        "name": "彭宁离子井·超级传送门·三阶超临界",
        "size": "gargantuan",
        "type": "boss",
        "hp": "360",
        "actions": "2A 2BA",
        "passive": "彭宁裂缝（三阶）：超临界投放 Xen 弗地冈与牛鱿，能量射线伤害陡增",
        "intents": [
            {"id": "portal_summon_swarm", "val": 2, "desc": "开启彭宁传送门·投放 Xen 群落 (批量召唤 Xen 异界单元并全敌强化)"},
            {"id": "portal_ion_beam", "val": 22, "desc": "四极直流离子贯穿束 (造成 22 点闪电伤害)"},
            {"id": "portal_magnetic_pulse", "val": 20, "desc": "强磁约束过载震荡 (获得 20 点护盾与 3 层力量)"},
            {"id": "portal_xen_bombard", "val": 16, "desc": "超级传送门·异界维度齐射 (对我方全体造成 16 点力场伤害)"},
        ],
    },
    "彭宁离子井·超级传送门·四阶终焉极井": {
        "name": "彭宁离子井·超级传送门·四阶终焉极井",
        "size": "gargantuan",
        "type": "boss",
        "hp": "460",
        "actions": "3A 2BA",
        "passive": "彭宁裂缝（四阶终焉）：无反伤亦无控牌技能，召唤含 Xen 控制器在内的完整 Xen 军团，全功率冲击阵线",
        "intents": [
            {"id": "portal_summon_swarm", "val": 2, "desc": "开启彭宁传送门·投放 Xen 群落 (批量召唤高阶 Xen 单位并强化全军)"},
            {"id": "portal_ion_beam", "val": 26, "desc": "四极直流离子贯穿束 (造成 26 点闪电伤害)"},
            {"id": "portal_magnetic_pulse", "val": 24, "desc": "强磁约束过载震荡 (获得 24 点护盾与 4 层力量)"},
            {"id": "portal_xen_bombard", "val": 18, "desc": "超级传送门·异界维度齐射 (对我方全体造成 18 点力场伤害)"},
        ],
    },
    "Xen猎头蟹": {
        "name": "Xen猎头蟹",
        "size": "tiny",
        "type": "summon",
        "hp": "18",
        "actions": "1A 0BA",
        "intents": [
            {"id": "xen_headcrab_leap", "val": 6, "desc": "突袭扑咬 (造成 6 点穿刺伤害)"},
            {"id": "xen_headcrab_burrow", "val": 6, "desc": "异界甲壳蜷缩 (获得 6 点护盾)"},
        ],
    },
    "Xen猎犬眼": {
        "name": "Xen猎犬眼",
        "size": "small",
        "type": "summon",
        "hp": "28",
        "actions": "1A 1BA",
        "intents": [
            {"id": "xen_houndeye_sonic", "val": 8, "desc": "猎犬眼高频冲击波 (对全体我方造成 8 点雷鸣伤害)"},
            {"id": "xen_headcrab_leap", "val": 10, "desc": "猎犬眼撕咬 (造成 10 点穿刺伤害)"},
        ],
    },
    "Xen弗地冈": {
        "name": "Xen弗地冈",
        "size": "medium",
        "type": "summon",
        "hp": "42",
        "actions": "1A 1BA",
        "intents": [
            {"id": "xen_vortigaunt_bolt", "val": 12, "desc": "弗地冈青绿电浆束 (造成 12 点闪电伤害)"},
            {"id": "xen_headcrab_burrow", "val": 12, "desc": "弗地冈护体电幕 (获得 12 点护盾并增强友军力量)"},
        ],
    },
    "Xen牛鱿": {
        "name": "Xen牛鱿",
        "size": "large",
        "type": "summon",
        "hp": "56",
        "actions": "1A 1BA",
        "intents": [
            {"id": "xen_bullsquid_acid", "val": 13, "desc": "牛鱿强酸喷吐 (造成 13 点强酸伤害并附加 1 层易伤)"},
            {"id": "xen_headcrab_leap", "val": 14, "desc": "牛鱿重尾横扫 (造成 14 点钝击伤害)"},
        ],
    },
    "Xen控制器": {
        "name": "Xen控制器",
        "size": "large",
        "type": "summon",
        "hp": "68",
        "actions": "2A 0BA",
        "intents": [
            {"id": "xen_controller_psi_lance", "val": 15, "desc": "控制器虚空能量投矛 (造成 15 点心灵伤害)"},
            {"id": "xen_controller_overdrive", "val": 2, "desc": "共鸣增幅传送门群 (敌方全体获得 2 层力量并恢复 14 点生命)"},
        ],
    },
}
