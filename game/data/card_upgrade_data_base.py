from .coop_card_data import COOP_UPGRADE_CONFIG
from .mercenary_card_data import MERCENARY_CARD_UPGRADE_CONFIG

CARD_UPGRADE_CONFIG_BASE = {
    "coop_tactical_command": COOP_UPGRADE_CONFIG["coop_tactical_command"],
    "coop_phalanx_bulwark": COOP_UPGRADE_CONFIG["coop_phalanx_bulwark"],
    "coop_resonance_hymn": COOP_UPGRADE_CONFIG["coop_resonance_hymn"],
    "coop_soul_link": COOP_UPGRADE_CONFIG["coop_soul_link"],
    "coop_unison_crusade": COOP_UPGRADE_CONFIG["coop_unison_crusade"],
    **MERCENARY_CARD_UPGRADE_CONFIG,
    "meteor_strike": {
        "base_dmg": 40,
        "hit_count": 4,
        "action_gain": 2,
        "gain_a": 2,
        "desc": "对场上的随机敌人造成 40 点钝击伤害，此操作重复执行 4 次，在自己的战场上召唤一个【能量核心+】护符。"
    },
    "strike_of_all": {
        "coef": 12,
        "desc": "造成 1.5^X * 12 点物理伤害，将弃牌堆、抽牌堆、消耗堆中所有名称含“打击”的卡牌抽入手牌。X为牌组中名称含“打击”的卡牌数量。"
    },
    "dagger_throw": {
        "base_dmg": 8,
        "action_gain": 1,
        "gain_a": 1,
        "desc": "造成 8 点穿刺伤害，且若击杀目标则获得 1A。"
    },
    "first_aid": {
        "cost_a": 0,
        "cost_ba": 0,
        "heal_amount": 10,
        "shield_amount": 4,
        "desc": "恢复 10 点生命值，并获得 4 点护盾。保留。消耗。"
    },
    "get_ready": {
        "cost_a": 0,
        "cost_ba": 1,
        "action_gain": 1,
        "gain_a": 1,
        "bonus_action_gain": 1,
        "gain_ba": 1,
        "draw_count": 2,
        "desc": "获得 1A 1BA，抽 2 张牌。"
    },
    "adrenaline": {
        "bonus_action_gain": 1,
        "gain_ba": 1,
        "gain_a": 1,
        "draw_count": 1,
        "self_damage": 3,
        "self_hp_cost": 3,
        "desc": "获得 1A 1BA，且抽 1 张牌，失去 3 点生命。"
    },
    "lucky_coin": {
        "countdown": 4,
        "draw_count": 1,
        "amulet_desc": "每回合结束时，你获得 4 金币，并抽 1 张牌。",
        "desc": "每回合结束时，你获得 4 金币，并抽 1 张牌。"
    },
    "thorns_necklace": {
        "countdown": 3,
        "base_dmg": 4,
        "shield_amount": 1,
        "amulet_desc": "受到伤害时，向伤害源反弹 4 点真实伤害，且自身获得 1 护盾。反弹伤害会使吟唱减少 1。",
        "desc": "当你受到伤害时，对伤害来源造成 4 点真实伤害，且自身获得 1 护盾。"
    },
    "tactical_focus": {
        "cost_a": 0,
        "cost_ba": 0,
        "draw_count": 5,
        "desc": "免费抽 5 张牌，但本回合无法再抽牌。"
    },
    "iron_will": {
        "heal_amount": 15,
        "shield_amount": 8,
        "buff_turns": 2,
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
        "shield_amount": 8,
        "desc": "生命 20，攻击 2。技能：重整防线（消耗 1BA，为你提供 4 点护盾），且进场时立即为你提供 6 点护盾。"
    },
    "quick_strike": {
        "base_dmg": 7,
        "ally_atk_bonus": 1,
        "desc": "造成 7 点钝击伤害，且本回合我方所有在场随从的攻击力 +1。"
    },
    "mana_potion": {
        "action_gain": 1,
        "gain_a": 1,
        "draw_count": 2,
        "desc": "获得 1A，抽 2 张牌。消耗。"
    },
    "agile_strike": {
        "base_dmg": 6,
        "draw_count": 1,
        "desc": "造成 6 点挥砍伤害。若由灵巧自动打出，则该伤害变为真实伤害并抽 1 牌。灵巧。"
    },
    "fleeting_spark": {
        "base_dmg": 9,
        "draw_count": 3,
        "discard_count": 1,
        "desc": "造成 9 点力场伤害，抽 3 张牌，选择 1 张手牌丢弃。若丢弃的是随从牌，则使其下回合行动点数 +1。即逝。"
    },
    "mass_healing_word": {
        "heal_amount": 12,
        "desc": "恢复自己和所有随从 12 点生命值。"
    },
    "refresh_spirit": {
        "shield_amount": 8,
        "action_gain": 1,
        "gain_a": 1,
        "desc": "消耗所有手牌中的非随从牌，每消耗一个获得 8 点护盾，且若消耗了 3 张或以上，则本回合获得 1A。"
    },
    "minion_icerainboww": {
        "minion_hp": 30,
        "minion_atk": 8,
        "shield_amount": 8,
        "buff_stacks": 1,
        "desc": "生命 30，攻击 8。拥有技能：冰雨散射与极光屏障。进场时使全体敌人受 1层轻度寒冷易伤且你获得 8 护盾。"
    },
    "fire_bolt": {
        "base_dmg": 5,
        "desc": "造成 5 点火焰伤害。若目标身上有任何负面Buff，该伤害翻倍。"
    },
    "magic_missile": {
        "base_dmg": 4,
        "count": 4,
        "hit_count": 4,
        "desc": "造成 4 次 4 点真实伤害，无视护盾。"
    },
    "fireball": {
        "base_dmg": 24,
        "burn_damage": 8,
        "burn_turns": 3,
        "desc": "对所有敌人造成 24 点火焰伤害，并给予所有敌人 3 回合的 8 点伤害燃烧效果。且本场战斗中，你后续的所有火焰伤害永久 +1。"
    },
    "thunderwave": {
        "cost_a": 1,
        "cost_ba": 1,
        "base_dmg": 9,
        "stun_turns": 1,
        "buff_turns": 1,
        "desc": "对所有敌人造成 9 点雷鸣伤害，使敌人下回合减少 1A，并使首个敌人陷入眩晕 1 回合。易碎 3。",
        "fragile": 3
    },
    "shield": {
        "shield_amount": 12,
        "heal_ratio": 0.5,
        "desc": "获得 12 点护盾。若生命低于 50%，则将该护盾的 50% 转化为生命治疗。"
    },
    "misty_step": {
        "draw_count": 3,
        "desc": "抽 3 张牌，且使手牌中所有被消耗或即逝卡牌的附赠动作点（BA）消耗减少 1。"
    },
    "arcane_intellect": {
        "draw_count": 4,
        "desc": "抽 4 张牌，且使你下一次打出的法术卡牌伤害 +3。"
    },
    "ring_of_elements": {
        "countdown": 5,
        "amulet_desc": "火焰伤害 +3。吟唱结束销毁时对所有敌人造成 8 点火焰伤害。",
        "base_dmg": 8,
        "desc": "你造成的火焰伤害 +3。吟唱结束销毁时对所有敌人造成 8 点火焰伤害。"
    },
    "arcane_crystal": {
        "countdown": 4,
        "amulet_desc": "每当你使用法术牌，回复 3 点生命值，并获得 2 点护盾。",
        "heal_amount": 3,
        "shield_amount": 2,
        "desc": "每当你使用法术牌，回复 3 点生命值，并获得 2 点护盾。"
    },
    "mage_ward": {
        "countdown": 3,
        "amulet_desc": "你的回合结束时，获得 6 点护盾。若回合结束时未受伤害，不扣除吟唱时间。",
        "shield_amount": 6,
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
        "draw_count": 1,
        "base_dmg": 2,
        "desc": "本场战斗每使用一张蓝色牌，抽 1 张牌。本回合通过法术涌动抽到法术牌时对敌造成 2 伤。"
    },
    "arcane_charge": {
        "cost_a": 0,
        "cost_ba": 1,
        "desc": "本场战斗法术牌造成的伤害 +4,且手牌中所有法术牌本回合伤害额外 +2。"
    },
    "find_familiar": {
        "minion_hp": 8,
        "minion_atk": 3,
        "draw_count": 2,
        "gain_ba": 2,
        "desc": "生命 8，攻击 3。技能：奥术协助（消耗 1BA，你抽 2 张牌），且法力充能获得 2BA。"
    },
    "arcane_golem": {
        "minion_hp": 26,
        "minion_atk": 8,
        "shield_amount": 10,
        "hit_count": 2,
        "desc": "生命 26，攻击 8。仅有普通攻击，但进场时获得 10 护盾，且本回合傀儡可以攻击 2 次。"
    },
    "water_elemental": {
        "minion_hp": 16,
        "minion_atk": 4,
        "base_dmg": 6,
        "buff_turns": 1,
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
        "draw_count": 1,
        "desc": "造成 4 点力场伤害，抽 1 张牌。若抽到的是法术牌，该法术本回合费用变为 0。"
    },
    "overcharge": {
        "buff_stacks": 2,
        "draw_count": 1,
        "desc": "本场战斗获得 2 层奥术充能 buff，并立即抽 1 张法术牌。消耗。"
    },
    "doomsday_judgment": {
        "cost_a": 2,
        "cost_ba": 1,
        "base_dmg": 24,
        "buff_turns": 1,
        "desc": "对所有敌人造成 24 点黯蚀伤害并眩晕他们 1 回合。若眩晕期间击杀目标你最大生命值 +2。消耗。"
    },
    "time_warp": {
        "action_gain": 1,
        "gain_a": 1,
        "bonus_action_gain": 1,
        "gain_ba": 1,
        "spell_damage_bonus": 2,
        "desc": "洗回卡组重新抽满手牌。本回合你额外获得 1A 1BA,且本回合所有法术牌造成的伤害 +2。消耗。"
    },
    "magic_network": {
        "damage_amount": 5,
        "base_dmg": 5,
        "shield_amount": 5,
        "desc": "本回合内，你每使用一张法术牌，便对所有敌人造成 5 点伤害，获得 5 点护盾。支持回响法术触发。"
    },
    "meteor_swarm": {
        "dice_count": 12,
        "dice_threshold": 8,
        "extra_true_damage": 2,
        "desc": "对所有敌人造成 10d12 随机火焰伤害，且大于 8 的单颗骰子会额外造成 2 真实伤害。消耗。"
    },
    "archmage_wish": {
        "shield_amount": 15,
        "spell_damage_bonus": 6,
        "draw_count": 3,
        "desc": "获得 15 点护盾,本场战斗中法术牌造成的伤害 +6,抽 3 张牌且本回合全部获得保留。消耗。"
    },
    "time_stop": {
        "cost_a": 1,
        "cost_ba": 1,
        "extra_turns": 4,
        "desc": "在回合结束时，额外追加 4 个额外回合。额外回合中若造成伤害，则立即结束。在此期间受到的负面 Buff 暂停生效。消耗。"
    },
    "chain_lightning": {
        "base_dmg": 18,
        "crit_multiplier": 1.5,
        "desc": "选择一个敌人，对所有同名敌人造成 18 点闪电伤害。若战场仅有一个同名敌人，该伤害必定暴击。"
    },
    "sunburst": {
        "base_dmg": 22,
        "ally_atk_bonus": 3,
        "desc": "对战场上除了你以外的所有生物造成 22 点光耀伤害。净化我方随从的所有状态，且使其攻击力增加 3 点。"
    },
    "key_resonance": {
        "base_dmg": 9,
        "hit_count": 10,
        "desc": "进行X次死者召回：10。若拥有门之钥匙，每消耗1A额外对所有敌人造成9点力场伤害。"
    },
    "gate_guard": {
        "minion_hp": 16,
        "minion_atk": 3,
        "base_dmg": 8,
        "buff_turns": 1,
        "desc": "生命 16，攻击 3。入场曲：使一个敌人眩晕 1 回合。技能：守卫痛击（消耗 1A，造成 8 点钝击伤害并使目标下回合动作 A 减少 1）。"
    },
    "master_key": {
        "reduction": 3,
        "draw_count": 1,
        "desc": "使你战场中所有护符的吟唱时间减少 3 并抽 1 张牌。"
    },
    "void_beacon": {
        "countdown": 3,
        "amulet_desc": "每回合开始时，对所有敌人施加 1 层易伤，并对随机敌人造成 8 点力场伤害。",
        "base_dmg": 8,
        "buff_stacks": 1,
        "desc": "吟唱 3。每回合开始时，对所有敌人施加 1 层易伤，并对随机敌人造成 8 点力场伤害。"
    },
    "ancient_wisdom": {
        "coef": 4,
        "shield_amount": 3,
        "desc": "立即获得Y*4点护盾，且在本场战斗中获得X层古老智慧+形态：你每打出一张中立卡牌时，获得3点护盾。"
    },
    "arcane_torrent": {
        "damage_amount": 2,
        "force_damage_amount": 2,
        "base_dmg": 4,
        "desc": "对所有敌人造成多次 2 点真实伤害（穿透护盾）与 2 点力场伤害。若最终X不大于2，则造成X*2次伤害；若最终X大于2，则造成X*4次伤害。"
    },
    "arcane_barrier": {
        "coef": 9,
        "buff_stacks": 1,
        "desc": "获得X*9点护盾。若X>1，则获得1层缓冲。"
    },
    "break_limits": {
        "cost_a": 2,
        "cost_ba": 0,
        "bonus_action_gain": 1,
        "gain_ba": 1,
        "gain_a": 1,
        "desc": "使你的所有层数不高于 2000 的正面 Buff 计数器翻倍，并获得 1A 1BA。消耗。"
    },
    "abyss_collapse": {
        "cost_a": 1,
        "cost_ba": 1,
        "base_dmg": 32,
        "desc": "对所有敌人造成 32 点黯蚀伤害。若目标被眩晕，则造成双倍伤害。消耗。"
    },
    "demon_contract": {
        "bonus_action_gain": 3,
        "gain_ba": 3,
        "draw_count": 4,
        "buff_stacks": 2,
        "desc": "获得 3BA 动作点与抽 4 张卡，且本回合内你打出的下一张非恶魔契约法术牌额外打出 2 次。消耗。"
    },
    "frost_nova": {
        "cost_a": 2,
        "cost_ba": 0,
        "base_dmg": 20,
        "buff_stacks": 3,
        "buff_turns": 1,
        "desc": "对所有敌人造成 20 点冰霜伤害，对所有敌人施加 3 层轻度寒冷易伤并使所有敌人眩晕 1 回合。消耗。"
    },
    "glacier_fortress": {
        "cost_a": 1,
        "cost_ba": 0,
        "shield_amount": 28,
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
        "buff_stacks": 5,
        "desc": "对目标敌人造成 15 点黯蚀伤害，并施加 5 层虚空弱化。消耗。"
    },
    "glacier_tempest": {
        "cost_a": 2,
        "cost_ba": 1,
        "base_dmg": 18,
        "desc": "对所有敌人造成 18 点冰霜伤害。若场上存在任何我方随从，则获得等同于本次造成总伤害值 50% 的护盾。消耗。"
    },
    "neutral_banish_slash": {
        "base_dmg": 22,
        "banish_chance": 0.65,
        "gem_slots": 2,
        "desc": "造成 22 点力场伤害。若目标为非领主敌人，有 65% 几率将其直接放逐（被放逐的敌人不掉落金币）。"
    },
    "manaeria_queen_anne": {
        "desc": "免费。生命 21，攻击 6 点火焰伤害。入场曲：随机使弃牌堆与抽牌堆中的 2 张卡牌消失（消失的卡牌不进入消耗堆，也不会从牌组中永久移除）；若消失前两堆合计少于 7 张，召唤【安的巨大英灵】并将珍奇法术牌【卓越暴击】加入手牌。技能（消耗 1 点动作点）：随机使 1 张卡牌消失，并对所有存活敌人随机分配 20 点火焰伤害。"
    },
    "neutral_fusion": {
        "hp_cost_ratio": 0.10,
        "desc": "扣除当前最大生命上限的 10%（向上取整，最低 1 点，最大生命上限为 1 时不可使用），使你当前剩余的动作点 (A) 与附赠动作点 (BA) 翻倍。"
    },
    "neutral_shou_lai": {
        "absorb_amount": 8,
        "desc": "选中战场上任意一个除自己以外的生物（包括己方随从与队友），从目标身上吸收 8 点最大生命值（队友至少保留 1 点上限）。消耗。"
    },
    "neutral_tau": {
        "cost_a": 1,
        "cost_ba": 0,
        "desc": "生命 1，攻击 0，没有 AA 点与主动技能。入场曲：触发自身所有遗物的“战斗开始时”效果一次，并无视动作点触发己方场上所有随从的 1 技能各一次。"
    },
}
