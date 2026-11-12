CAFE_GUESTS = ["Guide_Elder", "Bartender_Jack", "Blacksmith_Ironclad", "pppopipupu"]

CAFE_NORMALS = ["杰斯", "艾琳", "雷恩", "露娜", "莫里", "凯尔", "咪咪", "萨拉", "辛普森", "斯莱克", "编号7", "绯红"]

CAFE_GUEST_COUNT_MIN = 1
CAFE_GUEST_COUNT_MAX = 2
CAFE_TOTAL_NPCS = 4
CAFE_NPCS_PER_EXTRA_PLAYER = 1
CAFE_CARD_MASTER_STOCK = 3
CAFE_GEMCUTTER_STOCK = 2
CAFE_MIN_HP = 1
CAFE_MIN_MAX_HP = 5

NPC_SHOW_NAMES = {
    "Guide_Elder": "👴 向导长老",
    "Bartender_Jack": "🍺 酒保杰克",
    "Blacksmith_Ironclad": "🔨 铁匠艾恩克拉德",
    "pppopipupu": "🐟 pppopipupu",
    "杰斯": "🃏 卡牌大师 · 杰斯",
    "艾琳": "💎 宝石琢磨师 · 艾琳",
    "雷恩": "🛡️ 退役角斗士 · 雷恩",
    "露娜": "🔮 迷路占星师 · 露娜",
    "莫里": "🍳 流浪厨师 · 莫里",
    "凯尔": "🎒 遗迹猎人 · 凯尔",
    "咪咪": "🐱 会说话的猫 · 咪咪",
    "萨拉": "🧵 虚空缝纫师 · 萨拉",
    "辛普森": "🎵 狂热诗人 · 辛普森",
    "斯莱克": "🪙 黑市宝石商 · 斯莱克",
    "编号7": "🤖 沉睡的古老守卫 · 编号7",
    "绯红": "🌹 神秘红衣女士 · 绯红"
}

NPC_ALIASES = {
    "guide_elder": "Guide_Elder", "向导长老": "Guide_Elder", "向导": "Guide_Elder", "长老": "Guide_Elder",
    "bartender_jack": "Bartender_Jack", "酒保杰克": "Bartender_Jack", "酒保": "Bartender_Jack", "杰克": "Bartender_Jack",
    "blacksmith_ironclad": "Blacksmith_Ironclad", "铁匠艾恩克拉德": "Blacksmith_Ironclad", "铁匠": "Blacksmith_Ironclad", "艾恩": "Blacksmith_Ironclad",
    "pppopipupu": "pppopipupu", "神秘高手": "pppopipupu", "高手": "pppopipupu",
    "杰斯": "杰斯", "卡牌大师": "杰斯",
    "艾琳": "艾琳", "宝石琢磨师": "艾琳", "宝石师": "艾琳",
    "雷恩": "雷恩", "角斗士": "雷恩",
    "露娜": "露娜", "占星师": "露娜",
    "莫里": "莫里", "厨师": "莫里",
    "凯尔": "凯尔", "遗迹猎人": "凯尔", "猎人": "凯尔",
    "咪咪": "咪咪", "猫咪": "咪咪", "猫": "咪咪",
    "萨拉": "萨拉", "缝纫师": "萨拉",
    "辛普森": "辛普森", "诗人": "辛普森",
    "斯莱克": "斯莱克", "宝石商": "斯莱克", "黑市": "斯莱克",
    "编号7": "编号7", "守卫": "编号7", "古老守卫": "编号7",
    "绯红": "绯红", "红衣女士": "绯红", "女士": "绯红"
}

CAFE_PRICES = {
    "guide_tea_cost": 40,
    "guide_spar_hp_cost": 4,
    "guide_spar_gold_reward": 120,
    "guide_rebuke_hp_cost": 6,
    "guide_apology_cost": 20,
    "bartender_drink_cost": 50,
    "bartender_tea_cost": 15,
    "bartender_tea_heal": 10,
    "bartender_drink_hp_cost": 8,
    "bartender_extra_cost": 30,
    "blacksmith_forge_cost": 70,
    "blacksmith_slot_cost": 30,
    "blacksmith_bonus_slot_chance": 0.5,
    "card_master_card_cost": 120,
    "gemcutter_slot_cost": 50,
    "gemcutter_gem_cost": 64,
    "gladiator_gold_cost": 50,
    "gladiator_max_hp_gain": 8,
    "gladiator_hp_cost": 10,
    "astrologer_hp_cost": 15,
    "cook_coffee_cost": 60,
    "cook_donut_cost": 40,
    "cook_donut_heal": 20,
    "hunter_sell_reward": 50,
    "hunter_buy_cost": 120,
    "cat_fish_cost": 15,
    "cat_claw_hp_cost": 3,
    "cat_gold_reward": 20,
    "cat_claw_chance": 0.3,
    "cat_pet_hp_cost": 4,
    "cat_gem_chance": 0.5,
    "tailor_penalty": 4,
    "tailor_fission_cost": 80,
    "bard_song_cost": 30,
    "black_market_gem_cost": 240,
    "guard_gold_reward": 150,
    "guard_explosion_hp_cost": 15,
    "guard_explode_chance": 0.5,
    "crimson_hp_rate": 0.25,
    "crimson_max_hp_gain": 6,
    "pppopipupu_disturb_cost": 20,
    "pppopipupu_hp_cost": 15,
    "pppopipupu_apology_cost": 30
}

NPC_TALKED_FALLBACK = {
    "text": "此人看起来有些疲惫，不想再多说什么了。",
    "options": ["离开交谈"]
}

REHN_DIALOG = {
    "text": "雷恩正在擦拭生锈的肩甲：“小子，真正的力量不是在羊皮纸上写写画画，去磨砺你的肉体吧！”",
    "options": [
        "肉体淬炼 (消耗 50 金币)：永久提升 8 点最大生命值上限",
        "血誓洗礼 (消耗 10 生命值)：夺取退役战利品珍奇遗物【角斗士皮带】",
        "离开交谈"
    ]
}

LUNA_DIALOG = {
    "text": "露娜摆弄着星盘，神情飘忽：“星空在指引着你，但也伴随着坠落的危险。你准备好面对未知的启示了吗？”",
    "options": [
        "接受命运启示 (消耗 15 生命值)：获得占星禁术卡牌【星界坠击】",
        "向星盘低语：询问关于最终BOSS尤格索托斯的弱点情报 (免费闲聊)",
        "离开交谈"
    ]
}

MORI_DIALOG = {
    "text": "莫里正在炖着一锅香气诡异的浓汤：“咖啡的苦涩能唤醒你沉睡的意志，但虚空的甜点...嘿，吃下去别吐出来就行。”",
    "options": [
        "购买特制浓缩咖啡 (消耗 60 金币)：获得本阶段回合开始额外 +1A 临时遗物",
        "购买虚空甜甜圈 (消耗 40 金币)：恢复 20 生命，但卡组随机被塞入一张【消化不良】诅咒卡",
        "离开交谈"
    ]
}

MIMI_DIALOG = {
    "text": "咪咪骄傲地舔着爪子：“愚蠢的人类，看在你有闪亮金币的份上，本喵允许你摸一下。喵呜——”",
    "options": [
        "免费抚摸它 (可能被抓伤流血，或者获得金币)",
        "喂食美味小鱼干 (消耗 15 金币)：借机抚摸耳朵，或进行卡牌净化",
        "离开交谈"
    ]
}

SARA_DIALOG = {
    "text": "萨拉的指尖缠绕着虚空能量线：“虚空的丝线比黄金更坚韧，我可以用它重塑你的卡牌效果。”",
    "options": [
        "编织保留织物 (免费)：为指定卡牌赋予【保留】词条，但该卡伤害/防御效果永久降低 4 点",
        "编织裂变织物 (消耗 80 金币)：为指定卡牌成功编织【复制 1】被动词条",
        "离开交谈"
    ]
}

SIMPSON_DIALOG = {
    "text": "辛普森怀抱竖琴，激情满怀：“你的伟绩将被传唱！只要给点小钱，我的诗歌能让你在战场上充满斗志！”",
    "options": [
        "倾听赞歌 (免费)：获得在接下来的 3 场战斗开始时获得 2 护盾的临时遗物【赞歌】",
        "资助诗集出版 (消耗 30 金币)：获得狂热吟游诗人赠予的卡牌【英雄赞歌】",
        "离开交谈"
    ]
}

SLACK_DIALOG = {
    "text": "斯莱克拉低兜帽，神神秘秘：“嘘——低调点。这些可是从先古矿区偷偷带出来的绝品，识货的就快下手。”",
    "options": [
        "走私传奇宝石 (消耗 240 金币)：以 8 折购买一颗随机传奇宝石",
        "接受危险试验 (免费)：白嫖一颗随机珍奇宝石，但卡组被迫塞入一张【法力逆流】诅咒卡",
        "离开交谈"
    ]
}

UNIT7_DIALOG = {
    "text": "编号7的装甲缝隙里漏出电火花，红光闪烁：“滴...能量水平极低...检测到有机生命体...是否注入动力源...”",
    "options": [
        "注入动作点动力源 (消耗 1A)：使后续首场战斗第一回合动作点临时少 1A，完全激活并获取独特遗物【能量护盾电池】",
        "暴力拆解机械核心 (免费)：尝试强行拆卸它，可能获得大量金币，也可能引发剧烈爆炸伤害",
        "离开交谈"
    ]
}

CRIMSON_DIALOG = {
    "text": "绯红端着红酒，优雅迷人：“命运是一场迷人的舞会，我的朋友。你愿意为了一时的欢愉，付出什么代价呢？”",
    "options": [
        "灵魂之舞契约 (消耗 25% 最大生命值上限)：获取强大物比的被动遗物【绯红之心】",
        "命运轻吻：撕裂并彻底移除卡组中的一张卡牌，同时最大生命上限增加 6 点",
        "离开交谈"
    ]
}

IRONCLAD_DIALOG = {
    "text": "🔨 铁匠艾恩克拉德：“呸！这咖啡厅一股甜腻娘们味！不过这里的炉子勉强能用。喂，你身上的武器生锈了，要不要老子给你砸几锤？丑话说在前面，别跟老子磨叽！”",
    "options": [
        "极限熔炼 (消耗 70 金币)：直接对随机卡牌进行合金升级",
        "矿石重塑 (消耗 1 颗宝石 + 30 金币)：用宝石作为催化剂，100% 成功为指定卡牌增加 1 个插槽",
        "离开交谈"
    ]
}

NPC_DIALOGS = {
    "Guide_Elder": {
        "talked": {
            "text": "👴 向导长老拍了拍你的肩膀：'路在脚下，多想无益。去面对你该面对的难关吧。'",
            "options": ["离开交谈"]
        },
        "start": {
            "text": "👴 向导长老：“选了一条充满荆棘的道路啊，孩子。看到你疲惫的样子，是想退缩了吗？还是依然觉得虚空不过如此？”",
            "options": [
                "诚实诉苦：是的长老，外面的怪物简直是疯子，尤格索托斯甚至还在乱码嘲讽我！",
                "逞强嘴硬：怎么可能？我一路砍瓜切菜，尤格索托斯我翻手可灭！",
                "离开交谈"
            ]
        },
        "branch_a": {
            "text": "👴 向导长老哈哈大笑，赞赏你的坦率：“哈哈！诚实是美德。给你两句忠告：越混沌的地方，越要守住心神。”",
            "options": [
                "虚心求教：花费 40 金币购买长老的珍藏红茶，静气凝神",
                "索要资助：长老手头宽裕，不如赞助我一些金币盘缠？",
                "离开交谈"
            ]
        },
        "branch_b": {
            "text": "👴 向导长老冷笑一声，面露失望：“狂妄！在虚空面前如此自大，看来你还没有领教过真正的绝望。”",
            "options": [
                "强硬反驳：不信？我们可以现场比划一下！",
                "顺从认错：额，其实我开玩笑的，请长老息怒...",
                "离开交谈"
            ]
        }
    },
    "Bartender_Jack": {
        "talked": {
            "text": "🍺 酒保杰克：'哎呀，老顾客，我的酒劲可是很大的。祝你在关卡里一切顺利！'",
            "options": ["离开交谈"]
        },
        "start": {
            "text": "🍺 酒保杰克：“哟！竟然能在这鬼地方遇到老熟人。怎么，不来杯我亲手调的特制烈酒，暖暖冰冷的身子？价格公道，只要 50 金币！”",
            "options": [
                "豪爽接受：满上！正好需要烈酒来壮壮胆，什么代价都行！ (消耗 50 金币)",
                "拒绝饮酒：在这混沌的咖啡厅，我只买杯普通的温红茶 (消耗 15 金币)",
                "离开交谈"
            ]
        },
        "branch_a": {
            "text": "🍺 酒保杰克大喜，递给你一杯燃烧着幽蓝火焰的虚空伏特加：“好气魄！这杯【虚空烈焰】是你的了！来，喝了它还是用它淬炼你的卡牌？”",
            "options": [
                "一饮而尽：咕嘟咕嘟全部喝下！",
                "浇在武器上：额外支付 30 金币，借助酒劲对卡牌进行回炉重塑",
                "离开交谈"
            ]
        }
    },
    "Blacksmith_Ironclad": {
        "talked": {
            "text": "🔨 铁匠艾恩克拉德：'风箱拉得够热了。别打扰老子休息，赶紧上路吧！'",
            "options": ["离开交谈"]
        },
        "start": IRONCLAD_DIALOG,
        "branch_a": IRONCLAD_DIALOG,
        "branch_b": IRONCLAD_DIALOG
    },
    "pppopipupu": {
        "talked": {
            "text": "🐟 pppopipupu静静地盯着池塘：'缘起缘灭，宁静已归于水底。祝你武运昌隆。'",
            "options": ["离开交谈"]
        },
        "start": {
            "text": "🐟 pppopipupu：“嘘……别出声。水波在动。在这混沌虚空的夹缝里钓鱼，能钓起很多不可思议的灵魂……你也是被钓上来的鱼吗？”",
            "options": [
                "安静陪伴：一言不发，在旁边静静坐下",
                "粗暴打扰：喂！在咖啡厅的观赏水池里怎么可能钓得到鱼？你在装什么深沉？",
                "离开交谈"
            ]
        },
        "branch_a": {
            "text": "他闭着眼，池水泛起金光：“很好，你没有像其他浮躁的冒险者一样急着索要力量。但钓鱼需要真正的静气，你还能继续保持沉默吗？”",
            "options": [
                "继续保持沉默：依然坐在一旁，闭目养神",
                "忍不住开口询问：“大师，这水池里真有鱼吗？”",
                "离开交谈"
            ]
        },
        "branch_b": {
            "text": "他眉头微皱，水面泛起寒霜：“惊扰了鱼群，可是要付出代价的。你是想试试我手里的竹竿，还是留下买鱼钱？”",
            "options": [
                "强硬对峙：“代价？我就站在这里，有本事你咬我啊！”",
                "退缩道歉：“对不起！我不该打扰垂钓！”",
                "离开交谈"
            ]
        }
    },
    "雷恩": {
        "start": REHN_DIALOG,
        "branch_a": REHN_DIALOG,
        "branch_b": REHN_DIALOG
    },
    "露娜": {
        "start": LUNA_DIALOG,
        "branch_a": LUNA_DIALOG,
        "branch_b": LUNA_DIALOG
    },
    "莫里": {
        "start": MORI_DIALOG,
        "branch_a": MORI_DIALOG,
        "branch_b": MORI_DIALOG
    },
    "咪咪": {
        "start": MIMI_DIALOG,
        "branch_a": MIMI_DIALOG,
        "branch_b": MIMI_DIALOG
    },
    "萨拉": {
        "start": SARA_DIALOG,
        "branch_a": SARA_DIALOG,
        "branch_b": SARA_DIALOG
    },
    "辛普森": {
        "start": SIMPSON_DIALOG,
        "branch_a": SIMPSON_DIALOG,
        "branch_b": SIMPSON_DIALOG
    },
    "斯莱克": {
        "start": SLACK_DIALOG,
        "branch_a": SLACK_DIALOG,
        "branch_b": SLACK_DIALOG
    },
    "编号7": {
        "start": UNIT7_DIALOG,
        "branch_a": UNIT7_DIALOG,
        "branch_b": UNIT7_DIALOG
    },
    "绯红": {
        "start": CRIMSON_DIALOG,
        "branch_a": CRIMSON_DIALOG,
        "branch_b": CRIMSON_DIALOG
    }
}
