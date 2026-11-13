RELIC_CONFIG = {
    "infinite_hourglass": {
        "name": "无限沙漏",
        "rarity": "mythic",
        "desc": "每场战斗开始时，直接获得 1 层时间停止状态（额外获得 1 个额外回合）。",
        "extra_turns": 1,
        "bonus_actions": 1,
        "price": 300
    },
    "ancient_eye": {
        "name": "先古之眼",
        "rarity": "epic",
        "desc": "每场战斗第一回合开始额外多抽 2 张牌。",
        "draw_bonus": 2,
        "price": 120
    },
    "gold_compass": {
        "name": "黄金罗盘",
        "rarity": "epic",
        "desc": "奇妙商店中所有商品价格享受 6 折优惠。",
        "shop_discount": 0.6,
        "price": 120
    },
    "dragon_blood": {
        "name": "红龙之血",
        "rarity": "epic",
        "desc": "每次战斗胜利后恢复 5 点生命值。",
        "heal_amount": 5,
        "price": 120
    },
    "energy_core": {
        "name": "能量核心",
        "rarity": "epic",
        "desc": "每回合开始时额外获得 1 个动作点 (A)。",
        "action_bonus": 1,
        "price": 120
    },
    "heavy_armor": {
        "name": "重装甲片",
        "rarity": "epic",
        "desc": "每场战斗开始时自动获得 8 点护盾。",
        "shield_gain": 8,
        "price": 120
    },
    "mark_of_fury": {
        "name": "狂暴之印",
        "rarity": "epic",
        "desc": "玩家打出的法术牌造成的伤害增加 2 点,但玩家的最大生命值上限永久减少 5 点。",
        "spell_bonus": 2,
        "max_hp_cost": 5,
        "price": 100
    },
    "greedy_contract": {
        "name": "贪婪契约",
        "rarity": "epic",
        "desc": "奇妙商店中所有商品价格额外享受 6 折优惠，但每场战斗开始时扣除 3 点生命值。",
        "shop_discount": 0.6,
        "hp_loss": 3,
        "price": 100
    },
    "mask_of_void": {
        "name": "虚空面具",
        "rarity": "epic",
        "desc": "每回合开始多抽 1 张牌，但玩家的手牌上限降为 9 张。",
        "draw_bonus": 1,
        "hand_limit": 9,
        "price": 100
    },
    "rust_shackle": {
        "name": "铁锈之锁",
        "rarity": "curse",
        "desc": "每场战斗开始时扣除玩家 4 点生命值。",
        "hp_loss": 4,
        "price": 80
    },
    "fool_oath": {
        "name": "愚者之誓",
        "rarity": "curse",
        "desc": "我方所有随从在入场时最大 HP 减少 3 点（最低为 1）。",
        "hp_reduction": 3,
        "price": 80
    },
    "wither_seed": {
        "name": "枯萎之种",
        "rarity": "curse",
        "desc": "在战斗中玩家无法受到任何治疗效果。",
        "price": 80
    },
    "lucky_coin": {
        "name": "幸运硬币",
        "rarity": "common",
        "desc": "每次进入下一个关卡时获得 5 金币。",
        "gold_gain": 5,
        "price": 40
    },
    "red_bottle": {
        "name": "红药水瓶",
        "rarity": "common",
        "desc": "玩家最大生命上限永久增加 5 点，且立即回复 5 点生命值。",
        "max_hp_gain": 5,
        "heal_amount": 5,
        "price": 40
    },
    "leather_armor": {
        "name": "坚固皮革",
        "rarity": "common",
        "desc": "每场战斗开始时自动获得 4 点护盾。",
        "shield_gain": 4,
        "price": 40
    },
    "whetstone": {
        "name": "磨刀石",
        "rarity": "rare",
        "desc": "我方随从进行普通攻击时的伤害增加 1 点。",
        "attack_bonus": 1,
        "price": 70
    },
    "ready_pack": {
        "name": "准备背包",
        "rarity": "rare",
        "desc": "战斗第一回合开始额外多抽 1 张牌且获得 1BA 动作资源。",
        "draw_bonus": 1,
        "ba_bonus": 1,
        "price": 70
    },
    "arcane_rune": {
        "name": "奥术符文",
        "rarity": "rare",
        "desc": "玩家打出的法术牌造成的伤害增加 1 点。",
        "spell_bonus": 1,
        "price": 70
    },
    "unstable_crystal": {
        "name": "不稳定水晶",
        "rarity": "epic",
        "desc": "玩家打出的法术牌造成的伤害增加 1 点,且每回合开始时额外获得 1BA;但每当玩家打出法术牌时,玩家受到 1 点伤害。",
        "spell_dmg_bonus": 1,
        "turn_ba_bonus": 1,
        "recoil_damage": 1,
        "price": 100
    },
    "vampiric_touch": {
        "name": "吸血之触",
        "rarity": "epic",
        "desc": "玩家打出伤害法术时回复 1 点生命值，但最大生命值上限永久减少 4 点。",
        "heal_amount": 1,
        "max_hp_cost": 4,
        "price": 100
    },
    "ancient_page": {
        "name": "先古残页",
        "rarity": "epic",
        "desc": "战斗开始时，额外将 2 张【奥术星火】加入手牌，但战斗开始时玩家失去 4 点生命值。",
        "spark_count": 2,
        "hp_loss": 4,
        "max_hand": 12,
        "void_mask_max_hand": 9,
        "price": 100
    },
    "blind_spot": {
        "name": "盲目之障",
        "rarity": "curse",
        "desc": "每场战斗第一回合开始时，玩家少抽 2 张牌。",
        "draw_penalty": 2,
        "price": 80
    },
    "tax_contract": {
        "name": "税收契约",
        "rarity": "curse",
        "desc": "每当进入下一个关卡时，玩家失去 6 金币。",
        "gold_loss": 6,
        "price": 80
    },
    "chemical_x": {
        "name": "X化学物",
        "rarity": "rare",
        "desc": "所有X费卡牌的X或Y消耗计数在结算时额外+2。",
        "x_bonus": 2,
        "price": 150
    },
    "ancient_compass": {
        "name": "古老罗盘",
        "rarity": "rare",
        "desc": "战斗第一回合开始时，所有敌人下回合的动作点A减少1。",
        "action_reduction": 1,
        "price": 120
    },
    "portal_fragment": {
        "name": "门扉碎片",
        "rarity": "epic",
        "desc": "进入战斗时，随机将一张中立的“秘钥共鸣”、“门扉守卫”、“万能钥匙”、“虚空信标”或“古老智慧”加入手牌。",
        "max_hand": 12,
        "void_mask_max_hand": 9,
        "price": 160
    },
    "ancient_sigil": {
        "name": "先古印记",
        "rarity": "legendary",
        "desc": "每当打出一张具有“消耗”属性的卡牌时，随机恢复3点生命值或获得5点护盾。",
        "proc_chance": 0.5,
        "heal_amount": 3,
        "shield_gain": 5,
        "price": 200
    },
    "trash_mountain": {
        "name": "垃圾山",
        "rarity": "legendary",
        "desc": "所有卡牌奖励都会被升级，但你无法在选择卡牌时点击跳过。",
        "price": 200
    },
    "void_lens": {
        "name": "虚空透镜",
        "rarity": "rare",
        "desc": "打出中立卡牌时，如果造成了伤害，伤害增加2点；如果提供了护盾，护盾增加2点。",
        "damage_bonus": 2,
        "shield_bonus": 2,
        "price": 120
    },
    "ancient_keyring": {
        "name": "古老钥匙扣",
        "rarity": "epic",
        "desc": "部署护符时，该护符有50%几率吟唱时间额外减少1（最低为1）。",
        "proc_chance": 0.5,
        "countdown_reduction": 1,
        "price": 150
    },
    "abyss_gaze": {
        "name": "深渊凝视",
        "rarity": "epic",
        "desc": "玩家打出的法术牌造成的伤害增加 4 点,但每当玩家受到伤害时,额外受到 2 点真实伤害。",
        "spell_bonus": 4,
        "recoil_damage": 2,
        "price": 100
    },
    "glacier_armor": {
        "name": "冰川装甲",
        "rarity": "epic",
        "desc": "每场战斗开始时自动获得 12 点护盾，但玩家的最大生命上限永久减少 6 点。",
        "shield_gain": 12,
        "max_hp_cost": 6,
        "price": 100
    },
    "abyss_whisper": {
        "name": "深渊低语",
        "rarity": "epic",
        "desc": "战斗开始时，随机使一个敌人眩晕 1 回合。",
        "stun_stacks": 1,
        "price": 120
    },
    "frost_blade": {
        "name": "凝霜之刃",
        "rarity": "epic",
        "desc": "每当玩家对敌人造成冰霜伤害时，伤害值增加 4 点。",
        "cold_damage_bonus": 4,
        "price": 120
    },
    "shadow_curse": {
        "name": "影之诅咒",
        "rarity": "curse",
        "desc": "每当你打出一张法术牌，受到 1 点力场伤害。",
        "damage": 1,
        "price": 80
    },
    "glacier_chill": {
        "name": "严寒侵袭",
        "rarity": "curse",
        "desc": "玩家每回合开始时，动作点 A 减少 1。",
        "action_penalty": 1,
        "price": 80
    },
    "abyss_contract": {
        "name": "深渊契约书",
        "rarity": "epic",
        "desc": "每当玩家受到真实伤害时，抽取 1 张卡牌。",
        "draw_count": 1,
        "price": 120
    },
    "glacier_core": {
        "name": "极寒之核",
        "rarity": "epic",
        "desc": "每当玩家的护盾在回合开始自动流失时，对所有敌人造成等同于流失量 50% 的冰霜伤害。",
        "damage_ratio": 0.5,
        "price": 120
    },
    "centurion_mail": {
        "name": "百夫长重甲",
        "rarity": "rare",
        "desc": "你受到的所有物理伤害降低 2 点。",
        "damage_reduction": 2,
        "price": 70
    },
    "priest_charm": {
        "name": "祭司骨饰",
        "rarity": "rare",
        "desc": "每当你受到生命值治疗时，额外获得 3 点护盾。",
        "shield_gain": 3,
        "price": 70
    },
    "beastmaster_claw": {
        "name": "兽王之爪",
        "rarity": "rare",
        "desc": "我方所有在场随从的攻击力永久 +1。",
        "atk_bonus": 1,
        "price": 70
    },
    "djinn_shard": {
        "name": "巨灵碎晶",
        "rarity": "rare",
        "desc": "你每回合打出的第一张法术卡牌，会对随机敌方角色造成 5 点力场伤害。",
        "damage": 5,
        "price": 70
    },
    "archmage_robe": {
        "name": "魔法师法袍",
        "rarity": "rare",
        "desc": "每当有我方随从打出法术时，玩家获得 2 点护盾。",
        "shield_gain": 2,
        "price": 70
    },
    "shadow_tentacle": {
        "name": "影魔触角",
        "rarity": "rare",
        "desc": "当敌方目标被施加任何负面 Buff 时，你获得 2 点护盾。",
        "shield_gain": 2,
        "price": 70
    },
    "mindflayer_brain": {
        "name": "夺心魔脑核",
        "rarity": "rare",
        "desc": "每当你因为卡牌效果弃牌时，对随机敌人造成 3 点心灵伤害。",
        "damage": 3,
        "price": 70
    },
    "leng_spider_venom": {
        "name": "冷蛛毒腺",
        "rarity": "rare",
        "desc": "你造成的物理伤害有 50% 概率对目标施加 1 层【轻度物理易伤】。",
        "proc_chance": 0.5,
        "vulnerable_stacks": 1,
        "price": 70
    },
    "migo_lightning_gun": {
        "name": "米·戈电击枪",
        "rarity": "rare",
        "desc": "战斗开始时，对所有敌方角色造成 5 点闪电伤害。",
        "damage": 5,
        "price": 70
    },
    "shoggoth_slime": {
        "name": "修格斯粘液",
        "rarity": "rare",
        "desc": "每当你受到伤害时，获得 4 点护盾。",
        "shield_gain": 4,
        "price": 70
    },
    "star_vampire_proboscis": {
        "name": "星之吸管",
        "rarity": "rare",
        "desc": "每当你打出具有【消耗】词条的卡牌时，回复 2 点生命值。",
        "heal_amount": 2,
        "price": 70
    },
    "starspawn_core": {
        "name": "眷族之核",
        "rarity": "epic",
        "desc": "回合结束时，若你本回合结束保留了至少 1 个附赠动作点 (BA)，对随机敌方角色造成 10 点力场伤害。",
        "damage": 10,
        "ba_threshold": 1,
        "price": 120
    },
    "doomsday_core": {
        "name": "末日核心",
        "rarity": "epic",
        "desc": "回合结束时，若你本回合打出了 3 张或以上的卡牌，抽 1 张牌。",
        "play_threshold": 3,
        "draw_count": 1,
        "price": 120
    },
    "necromancer_skull": {
        "name": "巫师颅骨",
        "rarity": "epic",
        "desc": "每当场上有任何我方随从或敌方角色死亡，你回复 2 点生命值。",
        "heal_amount": 2,
        "price": 120
    },
    "arcanist_hand": {
        "name": "奥术师之手",
        "rarity": "epic",
        "desc": "每当你打出一张 0 费的卡牌，对首个敌人造成 3 点力场伤害。",
        "damage": 3,
        "cost_threshold": 0,
        "price": 120
    },
    "commander_medal": {
        "name": "至高勋章",
        "rarity": "epic",
        "desc": "战斗开始时，我方所有在场随从本回合获得的行动点数 +1。",
        "action_bonus": 1,
        "bonus_action_bonus": 1,
        "price": 120
    },
    "stalker_eye": {
        "name": "潜伏者眼球",
        "rarity": "epic",
        "desc": "你打出的具有【消耗】词条的卡牌，其造成的伤害或获得的护盾值增加 4 点。",
        "damage_bonus": 4,
        "shield_bonus": 4,
        "price": 120
    },
    "time_sand_blessing": {
        "name": "时间沙之赐福",
        "rarity": "epic",
        "desc": "每个回合开始时额外获得 2 个附赠动作（BA）。",
        "bonus_actions": 2,
        "price": 0
    },
    "gladiator_belt": {
        "name": "角斗士皮带",
        "rarity": "epic",
        "desc": "若我方有随从在场，你在回合开始时获得 2 点护盾。",
        "shield_gain": 2,
        "price": 120
    },
    "shield_battery": {
        "name": "能量护盾电池",
        "rarity": "epic",
        "desc": "你每当获得护盾时，有 50% 几率额外获得 2 点护盾。",
        "proc_chance": 0.5,
        "shield_gain": 2,
        "price": 120
    },
    "crimson_heart": {
        "name": "绯红之心",
        "rarity": "epic",
        "desc": "当生命值低于 30% 时，你造成的伤害翻倍，且每次打出卡牌时回复 2 点生命值。",
        "hp_threshold": 0.3,
        "damage_multiplier": 2,
        "heal_amount": 2,
        "price": 120
    },
    "espresso_relic": {
        "name": "特制浓缩咖啡",
        "rarity": "epic",
        "desc": "本阶段内每场战斗回合开始时额外获得 1A。进入下一阶段时自动清除。",
        "action_bonus": 1,
        "price": 0
    },
    "anthem_relic_3": {
        "name": "赞歌",
        "rarity": "epic",
        "desc": "接下来的 3 场战斗开始时获得 2 点护盾。",
        "shield_gain": 2,
        "price": 0
    },
    "anthem_relic_2": {
        "name": "赞歌",
        "rarity": "epic",
        "desc": "接下来的 2 场战斗开始时获得 2 点护盾。",
        "shield_gain": 2,
        "price": 0
    },
    "anthem_relic_1": {
        "name": "赞歌",
        "rarity": "epic",
        "desc": "接下来的 1 场战斗开始时获得 2 点护盾。",
        "shield_gain": 2,
        "price": 0
    },
    "blood_covenant": {
        "name": "残躯圣契",
        "rarity": "legendary",
        "desc": "每回合开始时额外获得 1 个附赠动作 (BA)；每场战斗开始时，若最大生命上限不高于 35 点，获得 20 点护盾与 2 层【力量】。",
        "bonus_actions": 1,
        "max_hp_threshold": 35,
        "shield_gain": 20,
        "strength_gain": 2,
        "price": 220
    },
    "sanguine_crown": {
        "name": "血冕王冠",
        "rarity": "mythic",
        "desc": "每回合打出的第一张非衍生卡牌额外触发 1 次（不消耗动作点）；每场战斗开始时，获得等同于当前生命值 50% 的护盾（最低 15 点）。",
        "shield_ratio": 0.5,
        "min_shield": 15,
        "price": 320
    },
    "immortal_pact": {
        "name": "永生契约",
        "rarity": "mythic",
        "desc": "每场战斗一次，当你受到致命伤害时免疫本次死亡，将生命值锁定为 1 并获得 30 点护盾；每当你打出一张【消耗】或【即逝】卡牌时，获得 4 点护盾。",
        "revive_hp": 1,
        "revive_shield": 30,
        "exhaust_shield": 4,
        "price": 350
    },
    "ghost_body": {
        "name": "虚体之躯",
        "rarity": "artifact",
        "event_only": True,
        "desc": "完全免疫所有【真实伤害】（伤害强制归零）。",
        "price": 0
    },
    "pen_nib": {
        "name": "铅笔尖",
        "rarity": "common",
        "desc": "你每打出 5 张攻击牌，你的下一张攻击牌伤害翻倍。",
        "attack_threshold": 5,
        "damage_multiplier": 2,
        "counter_init": 0,
        "counter_max": 5,
        "price": 40
    },
    "prayer_wheel": {
        "name": "转经轮",
        "rarity": "rare",
        "desc": "每 3 个回合，你的下一回合开始时额外获得 1 点动作点 (A)。",
        "turn_threshold": 3,
        "action_bonus": 1,
        "counter_init": 0,
        "counter_max": 3,
        "price": 70
    },
    "nail_of_heaven": {
        "name": "天之钉",
        "rarity": "epic",
        "desc": "初始计数值为 5。每受到一次来自敌人的攻击伤害且伤害不少于 10 点时计数减 1（每回合最多减 1）；归 0 时，你下一次受到来自敌人的伤害将被免除，并对其施加 1 层【混乱】与 1 层【震颤】，随后重置计数。",
        "min_damage": 10,
        "confusion_stacks": 1,
        "tremor_stacks": 1,
        "counter_init": 5,
        "counter_max": 5,
        "price": 120
    }
}

