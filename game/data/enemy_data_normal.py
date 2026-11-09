ENEMY_NORMAL_CONFIG = {
    "训练假人": {
        "name": "训练假人",
        "type": "normal",
        "hp": "99999",
        "actions": "1A 0BA",
        "intents": []
    },
    "测试训练假人": {
        "name": "测试训练假人",
        "type": "normal",
        "hp": "999999",
        "actions": "1A 0BA",
        "intents": [
            {"id": "test_sweep", "val": 10, "desc": "横扫击打 (造成 10 点钝击伤害)"},
            {"id": "test_heal", "val": 10, "desc": "自我修复 (获得 10 点护盾)"}
        ]
    },
    "NoobSlayer99": {
        "name": "NoobSlayer99",
        "type": "normal",
        "hp": "30",
        "actions": "1A 0BA",
        "intents": [
            {"id": "fireball", "val": 8, "desc": "施法火球 (造成 8 点火焰伤害)"},
            {"id": "ice_armor", "val": 8, "desc": "凝聚冰甲 (获得 8 点护盾)"}
        ]
    },
    "xXx_SniperElite_xXx": {
        "name": "xXx_SniperElite_xXx",
        "type": "normal",
        "hp": "50",
        "actions": "1A 0BA",
        "intents": [
            {"id": "aim", "val": 0, "desc": "精准瞄准 (锁定目标，下回合伤害增加)"},
            {"id": "piercing_shot", "val": 18, "desc": "穿甲射击 (造成 18 点穿刺伤害)"}
        ]
    },
    "地精百夫长": {
        "name": "地精百夫长",
        "type": "elite",
        "hp": "30 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "heavy_strike", "val": 8, "desc": "重击 (造成 8 伤害)"},
            {"id": "defend", "val": 6, "desc": "举盾 (获得 6 护盾)"},
            {"id": "command", "val": 0, "desc": "咆哮 (下回合获得 1 个动作)"}
        ]
    },
    "石像鬼祭司": {
        "name": "石像鬼祭司",
        "type": "elite",
        "hp": "38 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "attack", "val": 5, "desc": "惩戒 (造成 5 伤害)"},
            {"id": "defend", "val": 8, "desc": "暗影护盾 (获得 8 护盾)"},
            {"id": "drain", "val": 4, "desc": "生命汲取 (造成 4 伤害，并回复 4 生命)"}
        ]
    },
    "狂暴兽王": {
        "name": "狂暴兽王",
        "type": "elite",
        "hp": "32 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "attack", "val": 6, "desc": "鞭笞 (造成 6 伤害)"},
            {"id": "summon_beast", "val": 0, "desc": "野兽召唤 (召唤一只狂暴猎犬)"},
            {"id": "defend", "val": 5, "desc": "猎手防线 (获得 5 护盾)"}
        ],
        "summon_hound": {
            "name": "狂暴猎犬",
            "hp": 8,
            "max_hp": 8,
            "intent_val": 2,
            "intent_desc": "扑咬 (造成 2 伤害)"
        }
    },
    "黑曜石巨灵": {
        "name": "黑曜石巨灵",
        "type": "elite",
        "hp": "45 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "quake", "val": 5, "desc": "大地崩裂 (造成 5 伤害，并剥夺玩家 1BA)"},
            {"id": "defend", "val": 12, "desc": "黑曜石防护 (获得 12 护盾)"}
        ]
    },
    "幽灵大魔法师": {
        "name": "幽灵大魔法师",
        "type": "elite",
        "hp": "36 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "spell_burst", "val": 8, "desc": "奥术闪电 (造成 8 伤害)"},
            {"id": "mana_drain", "val": 4, "desc": "魔力虹吸 (造成 4 伤害，并丢弃手牌)"}
        ]
    },
    "暗影影魔": {
        "name": "暗影影魔",
        "type": "elite",
        "hp": "34 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "shadow_strike", "val": 6, "desc": "影袭 (造成 6 伤害，且无视玩家护盾)"},
            {"id": "defend", "val": 6, "desc": "虚化 (获得 6 护盾)"}
        ]
    },
    "地精突袭者": {
        "name": "地精突袭者",
        "type": "normal",
        "hp": "12 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "石像鬼守卫": {
        "name": "石像鬼守卫",
        "type": "normal",
        "hp": "18 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "堕落学徒": {
        "name": "堕落学徒",
        "type": "normal",
        "hp": "14 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "狂暴野兽": {
        "name": "狂暴野兽",
        "type": "normal",
        "hp": "15 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "幽灵法师": {
        "name": "幽灵法师",
        "type": "normal",
        "hp": "16 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "冰霜史莱姆": {
        "name": "冰霜史莱姆",
        "type": "normal",
        "hp": "10 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "骷髅弓箭手": {
        "name": "骷髅弓箭手",
        "type": "normal",
        "hp": "12 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "剧毒蜘蛛": {
        "name": "剧毒蜘蛛",
        "type": "normal",
        "hp": "10 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "黑曜石巨人": {
        "name": "黑曜石巨人",
        "type": "normal",
        "hp": "22 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "暗影刺客": {
        "name": "暗影刺客",
        "type": "normal",
        "hp": "14 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成随机伤害，基于关卡数: 3 + 关卡数//2 + 随机值)"},
            {"id": "defend", "desc": "防御 (获得随机护盾，基于关卡数: 3 + 关卡数 + 随机值)"}
        ]
    },
    "魔仆": {
        "name": "魔仆",
        "type": "summon",
        "hp": "5",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "准备攻击 (造成 1 伤害)"}
        ]
    },
    "狂暴猎犬": {
        "name": "狂暴猎犬",
        "type": "summon",
        "hp": "8",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "扑咬 (造成 2 伤害)"}
        ]
    },
    "雷影魔仆": {
        "name": "雷影魔仆",
        "type": "summon",
        "hp": "12",
        "actions": "1A 0BA",
        "intents": [
            {"id": "lightning_strike", "val": 4, "desc": "闪电击 (造成 4 闪电伤害，并施加 1 层电击)"},
            {"id": "charge", "val": 1, "desc": "蓄能 (获得 1 层力量)"}
        ]
    },
    "末日守卫": {
        "name": "末日守卫",
        "type": "elite",
        "hp": "40 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "doom_strike", "val": 7, "desc": "毁灭打击 (造成 7 穿刺伤害，并施加 1 层轻度挥砍易伤)"},
            {"id": "hellfire", "val": 5, "desc": "地狱火 (造成 5 火焰伤害，并施加 1 层轻度火焰易伤)"},
            {"id": "sacrifice", "val": 15, "desc": "牺牲防御 (获得 15 护盾，但扣除自身 2 HP)"}
        ]
    },
    "亡灵巫师": {
        "name": "亡灵巫师",
        "type": "elite",
        "hp": "35 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "shadow_bolt", "val": 6, "desc": "暗影箭 (造成 6 黯蚀伤害，并对玩家施加 1 层轻度黯蚀易伤)"},
            {"id": "raise_dead", "val": 0, "desc": "死者苏生 (召唤一只骷髅兵)"},
            {"id": "soul_drain", "val": 4, "desc": "灵魂吸取 (造成 4 黯蚀伤害，回复自身 4 生命)"}
        ]
    },
    "传送门守卫者": {
        "name": "传送门守卫者",
        "type": "elite",
        "hp": "45 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "dimensional_tear", "val": 6, "desc": "空间撕裂 (造成 6 真实伤害)"},
            {"id": "void_shield", "val": 10, "desc": "虚空屏障 (获得 10 护盾并净化 1 负面 Buff)"},
            {"id": "portal_instability", "val": 8, "desc": "传送门不稳定 (造成 8 心灵伤害，并丢弃玩家 1 张手牌)"}
        ]
    },
    "火元素守卫": {
        "name": "火元素守卫",
        "type": "elite",
        "hp": "30 (+ 2 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "fire_blast", "val": 8, "desc": "烈焰爆轰 (造成 8 火焰伤害，并施加 1 层轻度火焰易伤)"},
            {"id": "fire_armor", "val": 8, "desc": "火焰护甲 (获得 8 护盾，且使玩家受到 2 点火焰伤害)"},
            {"id": "heat_grow", "val": 1, "desc": "热力凝聚 (获得 1 层力量)"}
        ]
    },
    "狂暴魔仆": {
        "name": "狂暴魔仆",
        "type": "normal",
        "hp": "15",
        "actions": "1A 0BA",
        "intents": [
            {"id": "rage_bite", "val": 4, "desc": "狂暴撕咬 (造成 4 点穿刺伤害，半血以下时伤害翻倍)"},
            {"id": "evil_gaze", "val": 5, "desc": "邪恶凝视 (获得 5 护盾)"}
        ]
    },
    "骷髅兵": {
        "name": "骷髅兵",
        "type": "summon",
        "hp": "6",
        "actions": "1A 0BA",
        "intents": [
            {"id": "attack", "desc": "攻击 (造成 2 点钝击伤害)"}
        ]
    },
    "虚空游荡者": {
        "name": "虚空游荡者",
        "type": "normal",
        "hp": "80 (+ 2 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "void_bite", "val": 8, "desc": "虚空噬咬 (造成 8 点黯蚀伤害，并施加 1 层轻度黯蚀易伤)"},
            {"id": "void_erosion", "val": 2, "desc": "虚空侵蚀 (使玩家获得 2 级虚空虚弱 Buff)"}
        ]
    },
    "先古守卫": {
        "name": "先古守卫",
        "type": "elite",
        "hp": "120 (+ 3 * 关卡数)",
        "actions": "2A 0BA",
        "intents": [
            {"id": "portal_smash", "val": 15, "desc": "门扉重击 (造成 15 点钝击伤害)"},
            {"id": "ancient_charge", "val": 3, "desc": "先古充能 (获得 3 层力量)"},
            {"id": "space_lock", "val": 1, "desc": "空间闭锁 (使玩家下回合减少 1A)"}
        ]
    },
    "星界猎犬": {
        "name": "星界猎犬",
        "type": "elite",
        "hp": "110 (+ 3 * 关卡数)",
        "actions": "1A 2BA",
        "intents": [
            {"id": "star_bite", "val": 10, "desc": "星光撕咬 (造成 10 点力场伤害)"},
            {"id": "phase_shift", "val": 12, "desc": "相位转移 (获得 12 护盾并净化自身 1 负面 Buff)"},
            {"id": "star_fury", "val": 1, "desc": "星光狂暴 (使玩家下回合少抽 1 张牌)"}
        ]
    },
    "虚空潜伏者": {
        "name": "虚空潜伏者",
        "type": "elite",
        "hp": "50 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "void_ambush", "val": 12, "desc": "虚空伏击 (造成 12 点黯蚀伤害)"},
            {"id": "shadow_fade", "val": 10, "desc": "影遁 (获得 10 点护盾)"}
        ]
    },
    "虚空潜伏者（召唤）": {
        "name": "虚空潜伏者",
        "type": "summon",
        "hp": "20",
        "actions": "1A 0BA",
        "intents": [
            {"id": "void_strike", "val": 6, "desc": "虚空打击 (造成 6 点黯蚀伤害)"}
        ]
    },
    "夺心魔": {
        "name": "夺心魔",
        "type": "elite",
        "hp": "48 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "tentacles", "val": 6, "desc": "触须缠绕 (造成 6 心灵伤害并使你受擒)"},
            {"id": "mind_blast", "val": 8, "desc": "心灵震爆 (造成 8 心灵伤害并使你眩晕)"},
            {"id": "extract_brain", "val": 25, "desc": "采脑 (对受擒的你造成 25 穿刺伤害)"},
            {"id": "defend", "val": 8, "desc": "心灵屏障 (获得 8 护盾)"}
        ]
    },
    "夺心魔奥术师": {
        "name": "夺心魔奥术师",
        "type": "elite",
        "hp": "52 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "tentacles", "val": 6, "desc": "触须缠绕 (造成 6 心灵伤害并使你受擒)"},
            {"id": "mind_blast", "val": 8, "desc": "心灵震爆 (造成 8 心灵伤害并使你眩晕)"},
            {"id": "extract_brain", "val": 25, "desc": "采脑 (对受擒的你造成 25 穿刺伤害)"},
            {"id": "magic_missile", "val": 3, "desc": "奥术飞弹 (造成 3 点力场伤害，重复 3 次)"},
            {"id": "shield_spell", "val": 12, "desc": "护盾术 (获得 12 护盾并净化 1 负面状态)"}
        ]
    },
    "吉斯洋基海盗": {
        "name": "吉斯洋基海盗",
        "type": "normal",
        "hp": "18 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "silver_sword", "val": 7, "desc": "银剑横扫 (造成 7 挥砍伤害，若你有盾额外造成 4 力场伤害)"},
            {"id": "astral_step", "val": 6, "desc": "星界跃迁 (获得 6 护盾，且下回合多 1 个动作点)"},
            {"id": "parry", "val": 8, "desc": "招架防御 (获得 8 护盾)"}
        ]
    },
    "吉斯洋基至高指挥官": {
        "name": "吉斯洋基至高指挥官",
        "type": "elite",
        "hp": "55 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "silver_greatsword", "val": 12, "desc": "银光大剑 (造成 12 挥砍伤害，施加挥砍易伤)"},
            {"id": "commanding_presence", "val": 2, "desc": "战术指挥 (所有盟友获得 2 层力量)"},
            {"id": "psionic_barrier", "val": 14, "desc": "灵能屏障 (获得 14 护盾并获得 1 层力量)"},
            {"id": "summon_hound", "val": 0, "desc": "星界呼唤 (召唤一只星界幼犬)"}
        ],
        "summon_hound": {
            "name": "星界幼犬",
            "hp": 15,
            "max_hp": 15,
            "intent_val": 3,
            "intent_desc": "星光撕咬 (造成 3 力场伤害)"
        }
    },
    "邪教徒咔咔": {
        "name": "邪教徒咔咔",
        "type": "normal",
        "hp": "15 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "caw", "val": 0, "desc": "咔咔！ (第一回合必定施展仪式，此后每回合获得 1 层力量)"},
            {"id": "peck", "val": 6, "desc": "啄击 (造成 6 点穿刺伤害)"}
        ]
    },
    "星界幼犬": {
        "name": "星界幼犬",
        "type": "summon",
        "hp": "15",
        "actions": "1A 0BA",
        "intents": [
            {"id": "star_bite", "val": 3, "desc": "星光撕咬 (造成 3 力场伤害)"}
        ]
    },
    "虚空行者": {
        "name": "虚空行者",
        "type": "normal",
        "hp": "16 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "void_touch", "val": 6, "desc": "虚空之触 (造成 6 点黯蚀伤害)"},
            {"id": "phase_shift", "val": 8, "desc": "相位转移 (获得 8 点护盾)"}
        ]
    },
    "骨轻卒": {
        "name": "骨轻卒",
        "type": "summon",
        "hp": "10",
        "actions": "1A 0BA",
        "intents": [
            {"id": "bone_slash", "val": 3, "desc": "骨刃挥砍 (造成 3 点挥砍伤害)"}
        ]
    },
    "深潜者": {
        "name": "深潜者",
        "type": "normal",
        "hp": "14 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "tsunami_strike", "val": 5, "desc": "海啸重击 (造成 5 伤害，若有盾额外造成 3 真实伤害)"},
            {"id": "defend", "val": 6, "desc": "潮汐之盾 (获得 6 护盾)"}
        ]
    },
    "食尸鬼": {
        "name": "食尸鬼",
        "type": "normal",
        "hp": "15 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "rot_bite", "val": 5, "desc": "腐烂咬击 (造成 5 伤害并施加 1 层物理易伤)"},
            {"id": "claw_slash", "val": 6, "desc": "撕裂爪击 (造成 6 伤害)"}
        ]
    },
    "夜魇": {
        "name": "夜魇",
        "type": "normal",
        "hp": "20 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "tickle_claw", "val": 7, "desc": "搔痒爪 (造成 7 心灵伤害)"},
            {"id": "void_glide", "val": 8, "desc": "虚空滑翔 (获得 8 护盾，下回合额外获得 1 个动作)"}
        ]
    },
    "夏塔克鸟": {
        "name": "夏塔克鸟",
        "type": "normal",
        "hp": "22 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "wind_buffet", "val": 8, "desc": "狂风拍击 (造成 8 点力场伤害)"},
            {"id": "shriek", "val": 5, "desc": "尖啸 (造成 5 点心灵伤害，且丢弃玩家 1 张手牌)"}
        ]
    },
    "空鬼": {
        "name": "空鬼",
        "type": "normal",
        "hp": "26 (+ 2 * 关卡数)",
        "actions": "1A 0BA",
        "intents": [
            {"id": "phase_strike", "val": 9, "desc": "相位打击 (造成 9 点真实伤害)"},
            {"id": "dimensional_shift", "val": 10, "desc": "维度偏移 (获得 10 护盾)"}
        ]
    },
    "冷蛛": {
        "name": "冷蛛",
        "type": "elite",
        "hp": "36 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "venom_bite", "val": 7, "desc": "剧毒啃咬 (造成 7 穿刺伤害并施加物理易伤)"},
            {"id": "web_trap", "val": 8, "desc": "蛛网束缚 (获得 8 护盾并丢弃玩家 1 张手牌)"},
            {"id": "spider_jump", "val": 8, "desc": "跳跃突袭 (造成 8 点钝击伤害)"}
        ]
    },
    "米·戈": {
        "name": "米·戈",
        "type": "elite",
        "hp": "34 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "electric_probe", "val": 6, "desc": "电击探针 (造成 6 闪电伤害，使玩家下回合少抽 1 张牌)"},
            {"id": "brain_case", "val": 9, "desc": "大脑提取 (造成 9 心灵伤害)"},
            {"id": "bio_shield", "val": 10, "desc": "生物护盾 (获得 10 护盾并净化自身 1 负面 Buff)"}
        ]
    },
    "修格斯": {
        "name": "修格斯",
        "type": "elite",
        "hp": "55 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "acid_splash", "val": 8, "desc": "强酸泼溅 (造成 8 点伤害并剥夺玩家 1 BA)"},
            {"id": "slime_cocoon", "val": 14, "desc": "粘液茧 (获得 14 护盾)"},
            {"id": "ooze_strike", "val": 12, "desc": "软泥撞击 (造成 12 伤害)"}
        ]
    },
    "星之精": {
        "name": "星之精",
        "type": "elite",
        "hp": "48 (+ 3 * 关卡数)",
        "actions": "1A 1BA",
        "intents": [
            {"id": "blood_drain", "val": 8, "desc": "鲜血虹吸 (造成 8 黯蚀伤害，回复自身 8 点生命)"},
            {"id": "invisible_stalker", "val": 10, "desc": "隐形潜行 (获得 10 护盾，下回合伤害增加 4)"},
            {"id": "talon_rend", "val": 11, "desc": "利爪撕裂 (造成 11 伤害)"}
        ]
    },
    "克苏鲁之星之眷族": {
        "name": "克苏鲁之星之眷族",
        "type": "elite",
        "hp": "130 (+ 3 * 关卡数)",
        "actions": "2A 0BA",
        "intents": [
            {"id": "cosmic_blast", "val": 16, "desc": "宇宙冲击 (造成 16 力场伤害)"},
            {"id": "cthulhu_gaze", "val": 10, "desc": "克苏鲁之视 (造成 10 心灵伤害，下回合减少玩家 1A)"},
            {"id": "star_regeneration", "val": 15, "desc": "星光再生 (获得 15 护盾，并回复 10 生命)"}
        ]
    }
}

ENEMY_INTENT_SCALING = {
    "attack": {"base": 3, "stage_divisor": 2, "random_min": 0, "random_max": 2},
    "defend": {"base": 3, "stage_multiplier": 1, "random_min": 0, "random_max": 2}
}

ENEMY_ENCOUNTER_CONFIG = {
    "normal": {
        "hp_per_stage": 2,
        "count_range": [1, 3],
        "pools": [
            {"max_stage": 12, "names": ["地精突袭者", "石像鬼守卫", "堕落学徒", "狂暴野兽", "邪教徒咔咔", "深潜者", "食尸鬼"]},
            {"max_stage": 25, "names": ["幽灵法师", "冰霜史莱姆", "骷髅弓箭手", "剧毒蜘蛛", "邪教徒咔咔", "夜魇", "夏塔克鸟"]},
            {"names": ["黑曜石巨人", "暗影刺客", "吉斯洋基海盗", "虚空行者", "空鬼"]}
        ]
    },
    "elite": {
        "hp_per_stage": 3,
        "pools": [
            {"max_stage": 12, "names": ["地精百夫长", "石像鬼祭司", "狂暴兽王", "夺心魔", "冷蛛", "米·戈"]},
            {"max_stage": 25, "names": ["黑曜石巨灵", "幽灵大魔法师", "暗影影魔", "夺心魔", "修格斯", "星之精"]},
            {"names": ["末日守卫", "亡灵巫师", "夺心魔奥术师", "吉斯洋基至高指挥官", "虚空潜伏者", "克苏鲁之星之眷族"]}
        ]
    }
}
