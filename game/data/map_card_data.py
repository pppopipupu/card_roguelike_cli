MAP_CARD_CONFIG = {
    "haste_sp": {
        "name": "加速术",
        "color": "neutral",
        "type": "spell",
        "cost_a": 0,
        "cost_ba": 0,
        "sp_cost": 3,
        "draw_count": 1,
        "exhaust": True,
        "target_type": "self",
        "rarity": "rare",
        "desc": "消耗 3 点 SP（SP 为 0 时可强行打出并叠加力竭）；立即将当前剩余的主动作 A 与附赠动作 BA 翻倍，抽 1 张牌。消耗。",
        "feedback": "发动【加速术】！消耗 {sp_cost} 点 SP，剩余动作翻倍为 {actions}A {bonus_actions}BA，并抽了 {draw_count} 张牌。"
    },
    "calm_mind": {
        "name": "平心定气",
        "color": "neutral",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "sp_gain": 4,
        "buff_stacks": 3,
        "exhaust": True,
        "target_type": "self",
        "rarity": "rare",
        "desc": "不获得护盾；立即回复 4 点 SP，并获得 3 层【心灵伤害抗性】（持续期间受到的心灵伤害减半）。消耗。",
        "feedback": "发动【平心定气】，回复了 {sp_gain} 点 SP，获得了 {buff_stacks} 层【心灵伤害抗性】。"
    },
    "desperate_strike": {
        "name": "孤注一掷",
        "color": "neutral",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "base_dmg": 6,
        "sp_loss_bonus": 2,
        "exhaustion_pct": 25,
        "damage_type": "slashing",
        "rarity": "rare",
        "desc": "造成 6 点挥砍伤害；自身每损失 1 点 SP 额外提高 2 点基础伤害；若处于力竭状态，每级力竭再使最终伤害提高 25%。",
        "feedback": "对【{target}】施展【孤注一掷】，造成 {dmg} 点挥砍伤害！"
    },
    "intangible": {
        "name": "无实体",
        "color": "neutral",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "buff_stacks": 1,
        "exhaust": True,
        "ethereal": True,
        "event_only": True,
        "target_type": "self",
        "rarity": "epic",
        "desc": "获得 1 层【无实体】（受到的一切伤害封顶为 1 点）。虚无。消耗。",
        "feedback": "身躯融入虚影，获得了 1 层【无实体】！"
    },
    "bladesong": {
        "name": "剑歌",
        "color": "wizard_warrior",
        "type": "ability",
        "cost_a": 0,
        "cost_ba": 1,
        "shield_amount": 8,
        "buff_stacks": 1,
        "exhaust": True,
        "event_only": True,
        "target_type": "self",
        "rarity": "epic",
        "desc": "获得 8 点护盾与 1 层【剑歌】（每回合开始额外得 1BA；打出红牌或蓝牌时额外造成 3 点伤害并获得 3 点护盾）。消耗。",
        "feedback": "吟唱起古老的【剑歌】！获得了 {shield} 点护盾与 {stacks} 层【剑歌】。"
    },
}

MAP_CARD_UPGRADE_CONFIG = {
    "haste_sp": {
        "sp_cost": 2,
        "draw_count": 2,
        "desc": "消耗 2 点 SP（SP 为 0 时可强行打出并叠加力竭）；立即将当前剩余的主动作 A 与附赠动作 BA 翻倍，抽 2 张牌。消耗。"
    },
    "calm_mind": {
        "sp_gain": 6,
        "buff_stacks": 4,
        "desc": "不获得护盾；立即回复 6 点 SP，并获得 4 层【心灵伤害抗性】（持续期间受到的心灵伤害减半）。消耗。"
    },
    "desperate_strike": {
        "base_dmg": 8,
        "sp_loss_bonus": 3,
        "exhaustion_pct": 35,
        "desc": "造成 8 点挥砍伤害；自身每损失 1 点 SP 额外提高 3 点基础伤害；若处于力竭状态，每级力竭再使最终伤害提高 35%。"
    },
    "intangible": {
        "ethereal": False,
        "desc": "获得 1 层【无实体】（受到的一切伤害封顶为 1 点）。消耗。"
    },
    "bladesong": {
        "cost_a": 0,
        "cost_ba": 0,
        "shield_amount": 12,
        "buff_stacks": 2,
        "desc": "获得 12 点护盾与 2 层【剑歌】（每回合开始额外得 1BA；打出红牌或蓝牌时额外造成 6 点伤害并获得 6 点护盾）。消耗。"
    },
}
