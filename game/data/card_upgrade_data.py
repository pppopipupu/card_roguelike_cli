CARD_UPGRADE_CONFIG = {
    "meteor_strike": {
        "desc": "对场上的随机敌人造成 40 点钝击伤害，此操作重复执行 4 次，在自己的战场上召唤一个【能量核心+】护符。"
    },
    "strike_of_all": {
        "desc": "造成 1.5^X * 12 点物理伤害，将弃牌堆、抽牌堆、消耗堆中所有名称含“打击”的卡牌抽入手牌。X为牌组中名称含“打击”的卡牌数量。"
    },
    "dagger_throw": {
        "base_dmg": 8,
        "desc": "造成 8 点穿刺伤害，且若击杀目标则获得 1A。"
    },
    "first_aid": {
        "cost_a": 0,
        "cost_ba": 0,
        "heal_amount": 5,
        "desc": "恢复 5 点生命值，并获得 2 点护盾。保留。"
    },
    "get_ready": {
        "cost_a": 0,
        "cost_ba": 1,
        "desc": "获得 1A 1BA，抽 2 张牌。"
    },
    "adrenaline": {
        "desc": "获得 1A 1BA，且抽 1 张牌，失去 3 点生命。"
    },
    "lucky_coin": {
        "countdown": 4,
        "amulet_desc": "每回合结束时，你获得 4 金币，并抽 1 张牌。",
        "desc": "每回合结束时，你获得 4 金币，并抽 1 张牌。"
    },
    "thorns_necklace": {
        "countdown": 3,
        "amulet_desc": "受到伤害时，向伤害源反弹 4 点真实伤害，且自身获得 1 护盾。反弹伤害会使吟唱减少 1。",
        "desc": "当你受到伤害时，对伤害来源造成 4 点真实伤害，且自身获得 1 护盾。"
    },
    "tactical_focus": {
        "cost_a": 0,
        "cost_ba": 0,
        "desc": "免费抽 5 张牌，但本回合无法再抽牌。"
    },
    "iron_will": {
        "desc": "最大生命上限增加 15 并回复 15 生命，且立即获得 8 护盾，下 2 回合获得治疗翻倍。"
    },
    "mercenary": {
        "minion_hp": 14,
        "minion_atk": 5,
        "desc": "生命 14，攻击 5。拥有普通攻击（消耗 1A），且进场时立即对首个敌人发动一次普攻。"
    },
    "shield_guard": {
        "minion_hp": 20,
        "minion_atk": 2,
        "desc": "生命 20，攻击 2。技能：重整防线（消耗 1BA，为你提供 4 点护盾），且进场时立即为你提供 6 点护盾。"
    },
    "quick_strike": {
        "base_dmg": 5,
        "desc": "造成 5 点钝击伤害，且本回合我方所有在场随从的攻击力 +1。"
    },
    "mana_potion": {
        "desc": "获得 1A，抽 2 张牌。消耗。"
    },
    "agile_strike": {
        "base_dmg": 6,
        "desc": "造成 6 点挥砍伤害。若由灵巧自动打出，则该伤害变为真实伤害并抽 1 牌。灵巧。"
    },
    "fleeting_spark": {
        "base_dmg": 9,
        "desc": "造成 9 点力场伤害，抽 3 张牌，选择 1 张手牌丢弃。若丢弃的是随从牌，则使其下回合行动点数 +1。即逝。"
    },
    "mass_healing_word": {
        "heal_amount": 12,
        "desc": "恢复自己和所有随从 12 点生命值。"
    },
    "refresh_spirit": {
        "desc": "消耗所有手牌中的非随从牌，每消耗一个获得 8 点护盾，且若消耗了 3 张或以上，则本回合获得 1A。"
    },
    "minion_icerainboww": {
        "minion_hp": 30,
        "minion_atk": 8,
        "desc": "生命 30，攻击 8。拥有技能：冰雨散射与极光屏障。进场时使全体敌人受 1层轻度寒冷易伤且你获得 8 护盾。"
    },
    "fire_bolt": {
        "base_dmg": 5,
        "desc": "造成 5 点火焰伤害。若目标身上有任何负面Buff，该伤害翻倍。"
    },
    "magic_missile": {
        "base_dmg": 4,
        "count": 4,
        "desc": "造成 4 次 4 点真实伤害，无视护盾。"
    },
    "fireball": {
        "base_dmg": 24,
        "desc": "对所有敌人造成 24 点火焰伤害，并给予所有敌人 3 回合的 8 点伤害燃烧效果。且本场战斗中，你后续的所有火焰伤害永久 +1。"
    },
    "thunderwave": {
        "cost_a": 1,
        "cost_ba": 1,
        "base_dmg": 9,
        "desc": "对所有敌人造成 9 点雷鸣伤害，使敌人下回合减少 1A，并使首个敌人陷入眩晕 1 回合。易碎 3。",
        "fragile": 3
    },
    "shield": {
        "shield_amount": 12,
        "desc": "获得 12 点护盾。若生命低于 50%，则将该护盾的 50% 转化为生命治疗。"
    },
    "misty_step": {
        "desc": "抽 3 张牌，且使手牌中所有被消耗或即逝卡牌的附赠动作点（BA）消耗减少 1。"
    },
    "arcane_intellect": {
        "desc": "抽 4 张牌，且使你下一次打出的法术卡牌伤害 +3。"
    },
    "ring_of_elements": {
        "countdown": 5,
        "amulet_desc": "火焰伤害 +3。吟唱结束销毁时对所有敌人造成 8 点火焰伤害。",
        "desc": "你造成的火焰伤害 +3。吟唱结束销毁时对所有敌人造成 8 点火焰伤害。"
    },
    "arcane_crystal": {
        "countdown": 4,
        "amulet_desc": "每当你使用法术牌，回复 3 点生命值，并获得 2 点护盾。",
        "desc": "每当你使用法术牌，回复 3 点生命值，并获得 2 点护盾。"
    },
    "mage_ward": {
        "countdown": 3,
        "amulet_desc": "你的回合结束时，获得 6 点护盾。若回合结束时未受伤害，不扣除吟唱时间。",
        "desc": "你的回合结束时，获得 6 点护盾。若回合结束时未受伤害，不扣除吟唱时间。"
    },
    "quicken": {
        "cost_a": 0,
        "cost_ba": 0,
        "desc": "本场战斗所有法术牌动作消耗减少 1BA（最低为 0）。本回合下两张打出的法术卡牌额外获得【保留】。"
    },
    "spell_surge": {
        "cost_a": 0,
        "cost_ba": 1,
        "desc": "本场战斗每使用一张蓝色牌，抽 1 张牌。本回合通过法术涌动抽到法术牌时对敌造成 2 伤。"
    },
    "arcane_charge": {
        "cost_a": 0,
        "cost_ba": 1,
        "desc": "本场战斗法术伤害 +4，且手牌中所有法术牌本回合伤害额外 +2。"
    },
    "find_familiar": {
        "minion_hp": 8,
        "minion_atk": 3,
        "desc": "生命 8，攻击 3。技能：奥术协助（消耗 1BA，你抽 2 张牌），且法力充能获得 2BA。"
    },
    "arcane_golem": {
        "minion_hp": 26,
        "minion_atk": 8,
        "desc": "生命 26，攻击 8。仅有普通攻击，但进场时获得 10 护盾，且本回合傀儡可以攻击 2 次。"
    },
    "water_elemental": {
        "minion_hp": 16,
        "minion_atk": 4,
        "desc": "生命 16，攻击 4。技能：寒冰触碰（消耗 1BA，使一个敌方单位下回合减少 2BA），霜冻冰枪造成 6 伤害并使目标眩晕 1 回合。"
    },
    "echo_form": {
        "cost_a": 1,
        "cost_ba": 1,
        "innate": True,
        "ethereal": True,
        "desc": "本场战斗中，你每回合打出的卡牌额外打出，每张牌最多回响 5 次，多余层数顺延至后续卡牌。虚无。固有。"
    },
    "calculated_gamble": {
        "desc": "丢弃所有手牌，重新抽等量 + 1 张牌，且本次丢弃的灵巧卡牌伤害翻倍。"
    },
    "arcane_spark": {
        "base_dmg": 4,
        "desc": "造成 4 点力场伤害，抽 1 张牌。若抽到的是法术牌，该法术本回合费用变为 0。"
    },
    "overcharge": {
        "desc": "本场战斗获得 2 层奥术充能 buff，并立即抽 1 张法术牌。消耗。"
    },
    "doomsday_judgment": {
        "cost_a": 2,
        "cost_ba": 1,
        "base_dmg": 24,
        "desc": "对所有敌人造成 24 点黯蚀伤害并眩晕他们 1 回合。若眩晕期间击杀目标你最大生命值 +2。消耗。"
    },
    "time_warp": {
        "desc": "洗回卡组重新抽满手牌。本回合你额外获得 1A 1BA，且本回合所有法术伤害 +2。消耗。"
    },
    "magic_network": {
        "desc": "本回合内，你每使用一张法术牌，便对所有敌人造成 5 点伤害，获得 5 点护盾。支持回响法术触发。"
    },
    "meteor_swarm": {
        "desc": "对所有敌人造成 10d12 随机火焰伤害，且大于 8 的单颗骰子会额外造成 2 真实伤害。消耗。"
    },
    "archmage_wish": {
        "desc": "获得 15 点护盾，本场战斗中法术伤害 +6，抽 3 张牌且本回合全部获得保留。消耗。"
    },
    "time_stop": {
        "cost_a": 1,
        "cost_ba": 1,
        "desc": "在回合结束时，额外追加 4 个额外回合。额外回合中若造成伤害，则立即结束。在此期间受到的负面 Buff 暂停生效。消耗。"
    },
    "chain_lightning": {
        "base_dmg": 18,
        "desc": "选择一个敌人，对所有同名敌人造成 18 点闪电伤害。若战场仅有一个同名敌人，该伤害必定暴击。"
    },
    "sunburst": {
        "base_dmg": 22,
        "desc": "对战场上除了你以外的所有生物造成 22 点光耀伤害。净化我方随从的所有状态，且使其攻击力增加 3 点。"
    },
    "key_resonance": {
        "desc": "进行X次死者召回：10。若拥有门之钥匙，每消耗1A额外对所有敌人造成9点力场伤害。"
    },
    "gate_guard": {
        "minion_hp": 16,
        "minion_atk": 3,
        "desc": "生命 16，攻击 3。入场曲：使一个敌人眩晕 1 回合。技能：守卫痛击（消耗 1A，造成 8 点钝击伤害并使目标下回合动作 A 减少 1）。"
    },
    "master_key": {
        "desc": "使你战场中所有护符的吟唱时间减少 3 并抽 1 张牌。"
    },
    "void_beacon": {
        "countdown": 3,
        "amulet_desc": "每回合开始时，对所有敌人施加 1 层易伤，并对随机敌人造成 8 点力场伤害。",
        "desc": "吟唱 3。每回合开始时，对所有敌人施加 1 层易伤，并对随机敌人造成 8 点力场伤害。"
    },
    "ancient_wisdom": {
        "desc": "立即获得Y*4点护盾，且在本场战斗中获得X层古老智慧+形态：你每打出一张中立卡牌时，获得3点护盾。"
    },
    "arcane_torrent": {
        "desc": "对所有敌人造成多次 4 点真实伤害（穿透护盾）。若最终X不大于2，则造成X*2次伤害；若最终X大于2，则造成X*4次伤害。"
    },
    "arcane_barrier": {
        "desc": "获得X*9点护盾。若X>1，则获得1层缓冲。"
    },
    "break_limits": {
        "cost_a": 2,
        "cost_ba": 0,
        "desc": "使你的所有层数不高于 2000 的正面 Buff 计数器翻倍，并获得 1A 1BA。消耗。"
    },
    "abyss_collapse": {
        "cost_a": 1,
        "cost_ba": 1,
        "base_dmg": 32,
        "desc": "对所有敌人造成 32 点黯蚀伤害。若目标被眩晕，则造成双倍伤害。消耗。"
    },
    "demon_contract": {
        "desc": "获得 3BA 动作点与抽 4 张卡，且本回合内你打出的下一张非恶魔契约法术牌额外打出 2 次。消耗。"
    },
    "frost_nova": {
        "cost_a": 2,
        "cost_ba": 0,
        "base_dmg": 20,
        "desc": "对所有敌人造成 20 点冰霜伤害，对所有敌人施加 3 层轻度寒冷易伤并使所有敌人眩晕 1 回合。消耗。"
    },
    "glacier_fortress": {
        "cost_a": 1,
        "cost_ba": 0,
        "desc": "获得 28 点护盾，且在本场战斗中，你在回合结束时获得的护盾量增加 6 点。消耗。"
    },
    "abyss_altar": {
        "cost_a": 2,
        "cost_ba": 0,
        "desc": "(消耗: 2A) 部署【深渊祭坛】。拍下直接跳过第一阶段，在格子上部署【苏醒的深渊祭坛】护符。"
    },
    "abyss_erosion": {
        "cost_a": 0,
        "cost_ba": 0,
        "base_dmg": 15,
        "desc": "对目标敌人造成 15 点黯蚀伤害，并施加 5 层虚空弱化。消耗。"
    },
    "glacier_tempest": {
        "cost_a": 2,
        "cost_ba": 1,
        "base_dmg": 18,
        "desc": "对所有敌人造成 18 点冰霜伤害。若场上存在任何我方随从，则获得等同于本次造成总伤害值 50% 的护盾。消耗。"
    },
    "warrior_strike": {
        "base_dmg": 9,
        "desc": "造成 9 点挥砍伤害。"
    },
    "warrior_defend": {
        "desc": "获得 8 点护盾。"
    },
    "warrior_bash": {
        "base_dmg": 11,
        "desc": "造成 11 点钝击伤害，施加 3 层轻度易伤。"
    },
    "iron_wave": {
        "base_dmg": 7,
        "desc": "造成 7 点挥砍伤害，获得 7 点护盾。"
    },
    "warrior_anger": {
        "base_dmg": 6,
        "desc": "造成 6 点挥砍伤害。将一张此牌的复制品加入弃牌堆。"
    },
    "body_slam": {
        "cost_a": 0,
        "cost_ba": 0,
        "desc": "造成等同于你当前护盾值的钝击伤害。"
    },
    "pommel_strike": {
        "base_dmg": 12,
        "desc": "造成 12 点挥砍伤害，抽 2 张牌。"
    },
    "shrug_it_off": {
        "desc": "获得 11 点护盾，抽 1 张牌。"
    },
    "heavy_blade": {
        "base_dmg": 18,
        "desc": "造成 18 点挥砍伤害。力量对该牌伤害的加成效果乘以 5。"
    },
    "shockwave": {
        "desc": "对所有敌人施加 3 层轻度易伤和 3 层虚弱。消耗。"
    },
    "flame_barrier": {
        "desc": "获得 16 点护盾。本回合每次受到攻击，对攻击源反弹 6 点真实伤害。"
    },
    "uppercut": {
        "base_dmg": 17,
        "desc": "造成 17 点钝击伤害，施加 3 层轻度易伤和 3 层虚弱。"
    },
    "spot_weakness": {
        "desc": "若目标敌人的意图包含攻击，你获得 4 层力量。"
    },
    "ghostly_armor": {
        "desc": "获得 14 点护盾。虚无。"
    },
    "power_through": {
        "desc": "手牌中添加两张诅咒牌“伤口”，获得 22 点护盾。"
    },
    "double_tap": {
        "cost_a": 0,
        "cost_ba": 0,
        "exhaust": True,
        "desc": "本回合你打出的下一张物理伤害牌额外打出 2 次。消耗。"
    },
    "feed": {
        "base_dmg": 14,
        "desc": "造成 14 点挥砍伤害。若击杀目标，则你最大生命值永久 +4 并回复 4 点生命。消耗。"
    },
    "inflame": {
        "desc": "你获得 3 层力量。"
    },
    "barricade": {
        "cost_a": 1,
        "desc": "获得 1 层缓冲。本场战斗中，你在回合开始时护盾不会流失一半。消耗。"
    },
    "metallicize": {
        "desc": "本场战斗中，你在每回合结束时获得 6 点护盾。"
    },
    "bludgeon": {
        "base_dmg": 42,
        "desc": "造成 42 点钝击伤害。"
    },
    "demon_form": {
        "desc": "本场战斗中，你在回合开始时获得 4 层力量。且在使用时额外获得 1A。"
    },
    "impervious": {
        "shield_amount": 50,
        "desc": "获得 50 点护盾。消耗。"
    },
    "entrench": {
        "desc": "你当前的护盾翻三倍。"
    },
    "officer_recruit_vanguard": {
        "minion_hp": 6,
        "minion_atk": 3,
        "desc": "生命 6，攻击 3。入场曲：若协作达到 4 以上，对首个敌人造成 5 点穿刺伤害，且抽 1 张牌。攻击时：若协作达到 6 以上，伤害额外 +4，并为你提供 2 点护盾。"
    },
    "officer_banner_bearer": {
        "minion_hp": 8,
        "minion_atk": 2,
        "desc": "生命 8，攻击 2。在场被动：打出物理卡牌时重置随机我方随从AA并使其本回合攻击 +3，自身获得 3 护盾。入场曲：若场上有指挥官，抽 1 张卡牌，你获得 1A 1BA。"
    },
    "commander_patrol_captain": {
        "minion_hp": 10,
        "minion_atk": 4,
        "desc": "生命 10，攻击 4。技能：巡逻指令+（消耗 2A，全体随从回复 5 生命且获得 5 护盾）。入场曲：召唤一个【步兵轻卒+】。谢幕曲：随机获得一张升级后的战士随从牌并使其本回合 0BA。"
    },
    "officer_royal_guard": {
        "minion_hp": 11,
        "minion_atk": 4,
        "desc": "生命 11，攻击 4。在场被动：获得护盾时攻击永久 +2，对首个敌人造成 3 穿刺真伤。入场曲：若协作达到 6 以上，自身获得【守护】。"
    },
    "commander_garrison_leader": {
        "minion_hp": 13,
        "minion_atk": 5,
        "desc": "生命 13，攻击 5。技能：要塞铁壁+（消耗 2A，获得 9 护盾，若有士兵则使其回复 5 生命）。在场被动：受伤碎盾时召唤一个带守护的【步兵轻卒+】并获得护盾，反弹 100% 伤。入场曲：使其他士兵生命上限及血量 +6。自带【守护】。"
    },
    "officer_squad_skirmisher": {
        "minion_hp": 8,
        "minion_atk": 4,
        "desc": "生命 8，攻击 4。在场被动：击杀敌人时召唤一个【步兵轻卒+】且该轻卒本回合可额外攻击一次。消耗卡牌时攻击 +3 并施加给全体敌人 1 层轻度易伤。入场曲：协作达到 8 以上时，造成 9 挥砍伤害并眩晕；否则造成 5 伤害。"
    },
    "commander_valiant_herald": {
        "minion_hp": 11,
        "minion_atk": 4,
        "desc": "生命 11，攻击 4。技能：冲锋信号+（消耗 2A，全体随从攻击本回合 +3）。入场曲：检索一张士兵牌。若协作达到 6 以上，使其费用减 1A 1BA 并获得保留。谢幕曲：使手牌中所有随从本回合 0费。"
    },
    "commander_steelclad_tactician": {
        "minion_hp": 16,
        "minion_atk": 5,
        "desc": "生命 16，攻击 5。技能：战术压制+（消耗 2A，造成 9 钝击伤害，斩杀时召唤两个【步兵轻卒+】）。在场被动：回合结束且协作达到 10 以上，召唤一个【步兵轻卒+】并获得等同我方随从数两倍的护盾。"
    },
    "officer_blade_dancer": {
        "minion_hp": 12,
        "minion_atk": 6,
        "desc": "生命 12，攻击 6。技能：双重斩击+（消耗 2A，造成两次 6 点伤害）。在场被动：攻击有盾目标时伤害增加 100% 且全部转为真伤。入场曲：若协作达到 12 以上，可攻击两次且获得 1A。有指挥官在场额外召唤自身克隆体+。"
    },
    "commander_aurora_emperor": {
        "minion_hp": 18,
        "minion_atk": 8,
        "desc": "生命 18，攻击 8。技能：极光审判+（消耗 3A，对群造成 12 光耀伤害，协作达到 15 以上转为 22 点真伤）。入场曲：使其他士兵 A +2 并立刻攻击，你获得 12 护盾。挂载极光圣域+状态：随从普通攻击时你获得 3 护盾并抽 1 卡。"
    },
    "tactical_barrack": {
        "countdown": 4,
        "desc": "部署吟唱：4。回合开始若协作达到 5 以上，召唤【步兵轻卒+】。谢幕曲：获得 8 护盾，且随机把一张已升级的士兵牌加入手牌。",
        "amulet_desc": "回合开始若协作达到 5 以上召唤【步兵轻卒+】"
    },
    "iron_phalanx_seal": {
        "countdown": 3,
        "desc": "部署吟唱：3。我方士兵进场时，你获得 4 护盾，且该随从最大生命 +4 并获得 1 层缓冲。谢幕曲：若协作达到 8 以上，获得 1 层缓冲且抽 2 张卡牌。",
        "amulet_desc": "我方士兵进场时你获得 4 护盾且该随从最大生命 +4 并获得 1 层缓冲"
    },
    "grand_coronation": {
        "countdown": 2,
        "desc": "部署吟唱：2。打出指挥官时，我方其他在场随从本回合攻击 +3 并回复 3 生命，且抽 1 卡。谢幕曲：若协作达到 10 以上，全体随从最大生命 +6 且你获得 15 护盾，全体随从回复满血。",
        "amulet_desc": "打出指挥官时我方其他在场随从本回合攻击 +3 并回复 3 生命且抽 1 卡"
    },
    "blade_regiment_banner": {
        "countdown": 4,
        "desc": "部署吟唱：4。我方随从或你造成物理伤害时伤害 +5。谢幕曲：若协作达到 12 以上，对敌方全体造成等同于协作数两倍的真伤，并以其中 100% 治疗你（上限 25）。",
        "amulet_desc": "我方随从或你造成物理伤害时伤害 +5"
    },
    "unmined_gem": {
        "desc": "随机给予手牌中的一张卡牌重放 4。消耗。"
    },
    "discover": {
        "desc": "从消耗堆选择两张卡牌加入手牌。消耗。",
        "exhaust": True
    },
    "warrior_shield_bash": {
        "desc": "获得 24 点护盾，造成当前护盾值一半的钝击伤害。如果此卡牌被消耗，则你获得 2A 2BA。"
    },
    "warrior_source_of_cinder": {
        "cost_a": 1,
        "cost_ba": 1,
        "exhaust": True,
        "desc": "获得薪火之源buff，回合开始时额外获得 1A 1BA。消耗。"
    },
    "neutral_emperor_eye": {
        "desc": "选择手牌中的一张手牌，消耗除选择牌以外的所有牌，获得等同于消耗牌数量的随机除对决模式外的卡牌。额外对一个随机敌人造成 49 点力场伤害。消耗。"
    },
    "neutral_astral_strike": {
        "base_dmg": 48,
        "desc": "造成 48 点力场伤害。力量对该牌伤害的加成效果乘以 5。消耗。"
    },
    "neutral_hero_anthem": {
        "desc": "获得 10 点护盾，抽 1 张牌。消耗。"
    },
    "warrior_blood_fury": {
        "desc": "失去 3 点生命值，获得 3 层【力量】。抽 3 张卡牌。保留。"
    },
    "warrior_hell_raider": {
        "desc": "你获得【地狱狂徒+】状态。抽到 2A及以下 且不消耗 BA 卡牌时免费自动打出，并且每次连携触发后额外抽取 1 张卡牌。消耗。"
    },
    "wizard_prismatic_wall": {
        "desc": "获得 25 点护盾与 3 层【虹光屏障+】。受击时反射 20 点混合属性伤害。"
    },
    "wizard_antimagic_field": {
        "cost_ba": 0,
        "desc": "清除场上所有生物的所有 Buff，并使所有护符消失（不触发谢幕曲且不进入墓地）。消耗。"
    },
    "wizard_time_ravage": {
        "desc": "对目标造成 25 点真实伤害，并使其获得 3 层【虚弱】与 3 层【易伤】，且你获得 1A 行动点。消耗。"
    },
    "neutral_power_word_kill": {
        "desc": "若目标生命低于 100 点则直接消灭；否则造成 40 点真实伤害。消耗。"
    },
    "neutral_power_word_stun": {
        "desc": "若目标生命低于 150 点，使其【单体晕眩】1 回合；否则造成 15 点力场伤害，且使其下回合减少 1A 行动点。"
    },
    "neutral_power_word_pain": {
        "desc": "若目标生命低于 180 点，使其获得 4 层【流血】与 3 层【虚弱】；否则造成 12 点物理挥砍伤害。"
    },
    "neutral_plane_shift": {
        "desc": "传送脱逃离开遭遇战，且获得 40 金币空间遗珍。在 25 层与 32 层 BOSS 战中禁用。即逝。"
    },
    "neutral_omega": {
        "cost_a": 0,
        "cost_ba": 0,
        "desc": "以随机顺序打出目前手牌中的所有卡牌的复制品。免费。消耗。"
    },
    "wizard_split_to_ten": {
        "desc": "获得 2 层【一分为十】Buff。消耗。"
    },
    "warrior_hematopoiesis": {
        "desc": "将现有的所有护盾变为在这场战斗生效的 1.5 倍临时生命值，抽取护盾数除10（向上取整）数量的卡牌。消耗。"
    },
    "neutral_button_magic": {
        "desc": "随机触发 X+2 个按钮效果（上限 10 个）。即逝。"
    }
}
