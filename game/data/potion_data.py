import random

POTION_SLOT_LIMIT = 3
POTION_THROW_DAMAGE = 3
POTION_RARITY_THRESHOLDS = (
    ("common", 0.60),
    ("rare", 0.85),
    ("epic", 0.97)
)
POTION_FALLBACK = "healing_potion"

POTION_CONFIG = {
    "healing_potion": {
        "name": "治疗药水",
        "rarity": "common",
        "heal_amount": 10,
        "drink_desc": "回复你 10 点生命值。",
        "throw_desc": "回复目标 10 点生命值。"
    },
    "shield_potion": {
        "name": "护盾药水",
        "rarity": "common",
        "shield_amount": 25,
        "drink_desc": "获得 25 点护盾。",
        "throw_desc": "目标获得 25 点护盾。"
    },
    "fire_potion": {
        "name": "火焰药水",
        "rarity": "common",
        "drink_damage": 12,
        "drink_buff_stacks": 2,
        "throw_damage": 16,
        "throw_buff_stacks": 2,
        "drink_desc": "受到 12 点火焰伤害，并被施加 2 层【燃烧】状态。",
        "throw_desc": "对目标造成 16 点火焰伤害，并施加 2 层【燃烧】状态。"
    },
    "frost_potion": {
        "name": "冰霜药水",
        "rarity": "common",
        "drink_damage": 10,
        "throw_damage": 20,
        "throw_buff_stacks": 1,
        "drink_desc": "受到 10 点寒冷伤害。",
        "throw_desc": "对目标造成 20 点寒冷伤害，并施加 1 层【轻度寒冷易伤】。"
    },
    "strength_potion": {
        "name": "力量药水",
        "rarity": "common",
        "buff_stacks": 2,
        "drink_desc": "获得 2 层【力量】状态。",
        "throw_desc": "目标获得 2 层【力量】状态。"
    },
    "swift_potion": {
        "name": "迅捷药水",
        "rarity": "rare",
        "gain_a": 1,
        "gain_ba": 1,
        "draw_count": 1,
        "minion_gain_a": 1,
        "minion_gain_ba": 1,
        "minion_gain_aa": 1,
        "drink_desc": "获得 1A 1BA，抽 1 张牌。",
        "throw_desc": "我方随从获得 1A 1BA 1AA 持续 1 回合。"
    },
    "poison_potion": {
        "name": "剧毒药水",
        "rarity": "rare",
        "drink_damage": 10,
        "drink_buff_stacks": 4,
        "throw_damage": 10,
        "throw_buff_stacks": 4,
        "drink_desc": "受到 10 点毒素伤害，被施加 4 层【中毒】状态。",
        "throw_desc": "对目标造成 10 点毒素伤害，施加 4 层【中毒】状态。"
    },
    "cleanse_potion": {
        "name": "净化药水",
        "rarity": "rare",
        "drink_desc": "清除自身所有负面状态且本回合免疫负面状态。",
        "throw_desc": "清除目标的所有状态（驱散敌人正面 Buff 或解除随从 Debuff）。"
    },
    "iron_potion": {
        "name": "钢铁药水",
        "rarity": "epic",
        "max_hp_gain": 5,
        "shield_amount": 20,
        "heal_amount": 10,
        "buff_stacks": 1,
        "drink_desc": "最大生命上限永久 +5，获得 20 护盾并回复 10 生命。",
        "throw_desc": "目标最大生命上限永久 +5，获得 20 护盾并回复 10 生命。"
    },
    "energy_potion": {
        "name": "能量药水",
        "rarity": "epic",
        "gain_a": 2,
        "minion_gain_a": 2,
        "minion_gain_aa": 1,
        "drink_desc": "获得 2 个额外动作点 (A)。",
        "throw_desc": "我方随从获得 2A 1AA 持续 1 回合。"
    },
    "fury_potion": {
        "name": "狂怒药水",
        "rarity": "epic",
        "buff_stacks": 3,
        "self_hp_cost": 5,
        "draw_count": 3,
        "drink_desc": "获得 3 层【力量】，扣除 5 生命，抽 3 张牌。",
        "throw_desc": "我方随从获得 3 层【力量】，你抽 3 张牌。"
    },
    "intellect_potion": {
        "name": "智力药水",
        "rarity": "epic",
        "buff_stacks": 2,
        "draw_count": 4,
        "drink_desc": "获得 2 层【奥术充能】（法术牌造成的伤害 +6），抽 4 张牌。",
        "throw_desc": "我方随从或玩家获得 2 层【奥术充能】，你抽 4 张牌。"
    },
    "destruction_potion": {
        "name": "毁灭药水",
        "rarity": "legendary",
        "drink_damage": 30,
        "throw_damage": 60,
        "splash_damage": 20,
        "drink_desc": "受到 30 点力场伤害。",
        "throw_desc": "对目标造成 60 点力场伤害，若击杀则对所有其他存活敌人造成 20 点力场溅射伤害。"
    }
}

def get_potion_name(pid: str) -> str:
    return POTION_CONFIG.get(pid, {}).get("name", pid)

def get_potion_drink_text(pid: str) -> str:
    return POTION_CONFIG.get(pid, {}).get("drink_desc", "")

def get_potion_throw_text(pid: str) -> str:
    return POTION_CONFIG.get(pid, {}).get("throw_desc", "")

def get_potion_desc(pid: str) -> str:
    cfg = POTION_CONFIG.get(pid, {})
    if not cfg:
        return ""
    return f"饮用效果：{get_potion_drink_text(pid)} | 投掷效果：{get_potion_throw_text(pid)}"

def roll_potion(player_class: str) -> str:
    r = random.random()
    rarity = "legendary"
    for rarity_name, threshold in POTION_RARITY_THRESHOLDS:
        if r < threshold:
            rarity = rarity_name
            break
    
    eligible = []
    for pid, cfg in POTION_CONFIG.items():
        if cfg["rarity"] == rarity:
            if pid == "fury_potion" and player_class != "战士":
                continue
            if pid == "intellect_potion" and player_class != "法师":
                continue
            eligible.append(pid)
            
    if not eligible:
        return POTION_FALLBACK
    return random.choice(eligible)
