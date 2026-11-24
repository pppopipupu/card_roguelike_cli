CHIREIDEN_FLOOR_INDEX = 3.5
CHIREIDEN_MAP_WIDTH = 5
CHIREIDEN_MAP_HEIGHT = 20
CHIREIDEN_START_COORD = "C1"
CHIREIDEN_RIN_ELITE_COORD = "C10"
CHIREIDEN_UTSUHO_BOSS_COORD = "C15"
CHIREIDEN_PORTAL_BOSS_COORD = "C19"
CHIREIDEN_EXIT_COORD = "C20"

CHIREIDEN_LOCKED_COORDS = (
    "B16", "C16", "D16",
    "A17", "B17", "C17", "D17", "E17",
    "A18", "B18", "C18", "D18", "E18",
    "C19", "C20",
)

CHIREIDEN_WALL_COORDS = (
    "A1", "E1", "A3", "A6", "E6", "E9", "A10", "A14", "E14",
    "A15", "B15", "D15", "E15",
    "A16", "E16",
    "A19", "B19", "D19", "E19",
    "A20", "B20", "D20", "E20",
)

CHIREIDEN_BIG_ROOM_PLANS = [
    {
        "group_id": "chireiden_br_he3_hub",
        "template_id": "lunar_he3_elevator_hub",
        "cells": ["B3", "C3", "B4", "C4"],
        "icon": "🛰️",
    },
    {
        "group_id": "chireiden_br_pb_bi",
        "template_id": "pb_bi_fast_reactor_chamber",
        "cells": ["B7", "C7", "D7", "B8", "C8", "D8"],
        "icon": "☢️",
    },
    {
        "group_id": "chireiden_br_tokamak",
        "template_id": "d_he3_tokamak_array",
        "cells": ["B11", "C11", "D11", "B12", "C12", "D12"],
        "icon": "⚛️",
    },
    {
        "group_id": "chireiden_br_penning_well",
        "template_id": "penning_ion_well_sanctum",
        "cells": ["B17", "C17", "D17", "B18", "C18", "D18"],
        "icon": "🌌",
    },
]

CHIREIDEN_SPECIAL_ROOMS = {
    "C1": {"room_type": "spawn", "env": "chireiden_elevator_shaft", "items": ["he3_fuel_canister"]},
    "B1": {"room_type": "empty", "env": "chireiden_elevator_shaft", "props": ["he3_storage_cylinder"]},
    "D1": {"room_type": "empty", "env": "chireiden_turbine_corridor", "items": ["he3_fuel_canister"]},
    "A2": {"room_type": "rest", "env": "chireiden_turbine_corridor"},
    "B2": {"room_type": "battle", "env": "chireiden_turbine_corridor"},
    "C2": {"room_type": "battle", "env": "chireiden_turbine_corridor"},
    "D2": {"room_type": "event", "env": "chireiden_he3_logistics_bay"},
    "E2": {"room_type": "treasure", "env": "chireiden_he3_logistics_bay"},
    "D3": {"room_type": "battle", "env": "chireiden_he3_logistics_bay"},
    "E3": {"room_type": "event", "env": "chireiden_he3_logistics_bay"},
    "A4": {"room_type": "empty", "env": "chireiden_turbine_corridor"},
    "D4": {"room_type": "shop", "env": "chireiden_he3_logistics_bay"},
    "E4": {"room_type": "empty", "env": "chireiden_turbine_corridor", "props": ["he3_storage_cylinder"]},
    "A5": {"room_type": "treasure", "env": "chireiden_he3_logistics_bay"},
    "B5": {"room_type": "empty", "env": "chireiden_turbine_corridor"},
    "C5": {"room_type": "landmark", "env": "chireiden_control_center", "landmark_id": "chireiden_fusion_terminal"},
    "D5": {"room_type": "rest", "env": "chireiden_turbine_corridor"},
    "E5": {"room_type": "shop", "env": "chireiden_he3_logistics_bay"},
    "B6": {"room_type": "battle", "env": "chireiden_pb_bi_fast_reactor"},
    "C6": {"room_type": "event", "env": "chireiden_pb_bi_fast_reactor", "forced_triggers": [{"id": "reactor_steam_vent", "timing": "on_enter", "once": True, "chance": 1.0}]},
    "D6": {"room_type": "empty", "env": "chireiden_pb_bi_fast_reactor", "props": ["pb_bi_coolant_valve"]},
    "A7": {"room_type": "empty", "env": "chireiden_pb_bi_fast_reactor"},
    "E7": {"room_type": "empty", "env": "chireiden_pb_bi_fast_reactor", "items": ["lbe_cooling_flask"]},
    "A8": {"room_type": "treasure", "env": "chireiden_pb_bi_fast_reactor"},
    "E8": {"room_type": "empty", "env": "chireiden_pb_bi_fast_reactor"},
    "A9": {"room_type": "rest", "env": "chireiden_turbine_corridor"},
    "B9": {"room_type": "high_danger", "env": "chireiden_pb_bi_fast_reactor"},
    "C9": {"room_type": "empty", "env": "chireiden_pb_bi_fast_reactor", "props": ["pb_bi_coolant_valve"]},
    "D9": {"room_type": "event", "env": "chireiden_d_he3_tokamak_hall"},
    "B10": {"room_type": "empty", "env": "chireiden_d_he3_tokamak_hall"},
    "C10": {"room_type": "elite", "env": "chireiden_pb_bi_fast_reactor", "encounter": ["火焰猫燐", "铅铋液态金属怪"], "elite_name": "火焰猫燐", "reward_relic": "lbe_fast_reactor_core"},
    "D10": {"room_type": "empty", "env": "chireiden_d_he3_tokamak_hall"},
    "E10": {"room_type": "treasure", "env": "chireiden_d_he3_tokamak_hall", "items": ["headband_blueprint_shard"]},
    "A11": {"room_type": "empty", "env": "chireiden_d_he3_tokamak_hall", "props": ["tokamak_magnetic_coil"]},
    "E11": {"room_type": "empty", "env": "chireiden_d_he3_tokamak_hall"},
    "A12": {"room_type": "event", "env": "chireiden_d_he3_tokamak_hall"},
    "E12": {"room_type": "rest", "env": "chireiden_d_he3_tokamak_hall"},
    "A13": {"room_type": "treasure", "env": "chireiden_control_center"},
    "B13": {"room_type": "high_danger", "env": "chireiden_d_he3_tokamak_hall"},
    "C13": {"room_type": "landmark", "env": "chireiden_penning_trap", "landmark_id": "chireiden_penning_stabilizer"},
    "D13": {"room_type": "empty", "env": "chireiden_control_center", "props": ["tokamak_magnetic_coil"]},
    "E13": {"room_type": "shop", "env": "chireiden_control_center"},
    "B14": {"room_type": "rest", "env": "chireiden_control_center"},
    "C14": {"room_type": "empty", "env": "chireiden_control_center"},
    "D14": {"room_type": "treasure", "env": "chireiden_control_center", "items": ["he3_fuel_canister"]},
    "C15": {"room_type": "boss", "env": "chireiden_control_center", "encounter": ["灵乌路空"], "boss_name": "灵乌路空", "chireiden_stage": "utsuho_gate", "reward_relic": "headband_of_intellect_int19"},
    "B16": {"room_type": "rest", "env": "chireiden_penning_trap"},
    "C16": {"room_type": "event", "env": "chireiden_penning_trap", "forced_triggers": [{"id": "penning_harmonic_alarm", "timing": "on_enter", "once": True, "chance": 1.0}]},
    "D16": {"room_type": "treasure", "env": "chireiden_penning_trap", "items": ["xen_sample_ampoule"]},
    "A17": {"room_type": "high_danger", "env": "chireiden_penning_trap"},
    "E17": {"room_type": "high_danger", "env": "chireiden_penning_trap"},
    "A18": {"room_type": "rest", "env": "chireiden_penning_trap"},
    "E18": {"room_type": "treasure", "env": "chireiden_penning_trap", "props": ["penning_harmonic_console"]},
    "C19": {"room_type": "boss", "env": "chireiden_penning_trap", "encounter": ["彭宁离子井·超级传送门·初阶裂隙"], "boss_name": "彭宁离子井·超级传送门·初阶裂隙", "chireiden_stage": "super_portal", "reward_relic": "penning_ion_stabilizer"},
    "C20": {"room_type": "downstairs", "env": "chireiden_penning_trap"},
}

CHIREIDEN_ENVIRONMENTS = [
    "chireiden_elevator_shaft",
    "chireiden_turbine_corridor",
    "chireiden_he3_logistics_bay",
    "chireiden_pb_bi_fast_reactor",
    "chireiden_d_he3_tokamak_hall",
    "chireiden_control_center",
    "chireiden_penning_trap",
]

CHIREIDEN_BIG_ROOM_TEMPLATES = {
    "lunar_he3_elevator_hub": {
        "name_key": "i18n_chireiden.big_rooms.lunar_he3_elevator_hub.name",
        "desc_key": "i18n_chireiden.big_rooms.lunar_he3_elevator_hub.desc",
        "icon": "🛰️",
        "chireiden_only": True,
        "shapes": ["rect_2x2"],
        "env_id": "chireiden_he3_logistics_bay",
        "reveal_mode": "whole",
        "share_npcs": False,
        "share_items": False,
        "share_props": True,
        "keep_icon_on_clear": True,
        "direct_reveal_adjacent": True,
        "shared_props": ["he3_storage_cylinder"],
        "item_pool": ["he3_fuel_canister", "headband_blueprint_shard"],
        "prop_pool": [],
        "item_chance_per_cell": 0.6,
        "prop_chance_per_cell": 0.0,
        "forced_triggers": [
            {"id": "he3_orbital_capsule", "timing": "on_enter", "once": True, "chance": 1.0},
        ],
    },
    "pb_bi_fast_reactor_chamber": {
        "name_key": "i18n_chireiden.big_rooms.pb_bi_fast_reactor_chamber.name",
        "desc_key": "i18n_chireiden.big_rooms.pb_bi_fast_reactor_chamber.desc",
        "icon": "☢️",
        "chireiden_only": True,
        "shapes": ["rect_3x2"],
        "env_id": "chireiden_pb_bi_fast_reactor",
        "reveal_mode": "whole",
        "share_npcs": True,
        "share_items": False,
        "share_props": True,
        "keep_icon_on_clear": True,
        "direct_reveal_adjacent": True,
        "shared_npcs": ["kaenbyou_rin"],
        "shared_props": ["pb_bi_coolant_valve"],
        "item_pool": ["lbe_cooling_flask"],
        "prop_pool": [],
        "item_chance_per_cell": 0.45,
        "prop_chance_per_cell": 0.0,
        "forced_triggers": [
            {"id": "reactor_steam_vent", "timing": "on_enter", "once": True, "chance": 1.0},
        ],
    },
    "d_he3_tokamak_array": {
        "name_key": "i18n_chireiden.big_rooms.d_he3_tokamak_array.name",
        "desc_key": "i18n_chireiden.big_rooms.d_he3_tokamak_array.desc",
        "icon": "⚛️",
        "chireiden_only": True,
        "shapes": ["rect_3x2"],
        "env_id": "chireiden_d_he3_tokamak_hall",
        "reveal_mode": "whole",
        "share_npcs": False,
        "share_items": False,
        "share_props": True,
        "keep_icon_on_clear": True,
        "direct_reveal_adjacent": True,
        "shared_props": ["tokamak_magnetic_coil"],
        "item_pool": ["headband_blueprint_shard", "he3_fuel_canister", "headband_of_intellect"],
        "prop_pool": [],
        "item_chance_per_cell": 0.45,
        "prop_chance_per_cell": 0.0,
        "forced_triggers": [],
    },
    "penning_ion_well_sanctum": {
        "name_key": "i18n_chireiden.big_rooms.penning_ion_well_sanctum.name",
        "desc_key": "i18n_chireiden.big_rooms.penning_ion_well_sanctum.desc",
        "icon": "🌌",
        "chireiden_only": True,
        "shapes": ["rect_3x2"],
        "env_id": "chireiden_penning_trap",
        "reveal_mode": "whole",
        "share_npcs": False,
        "share_items": False,
        "share_props": True,
        "keep_icon_on_clear": True,
        "direct_reveal_adjacent": True,
        "shared_props": ["penning_harmonic_console"],
        "item_pool": ["xen_sample_ampoule", "he3_fuel_canister"],
        "prop_pool": [],
        "item_chance_per_cell": 0.5,
        "prop_chance_per_cell": 0.0,
        "forced_triggers": [
            {"id": "penning_harmonic_alarm", "timing": "on_enter", "once": True, "chance": 1.0},
        ],
    },
}

CHIREIDEN_ITEMS = {
    "he3_fuel_canister": {
        "name_key": "i18n_chireiden.items.he3_fuel_canister.name",
        "desc_key": "i18n_chireiden.items.he3_fuel_canister.desc",
        "category": "consumable",
        "aliases": ["氦三", "氦三燃料罐", "燃料罐", "he3", "canister"],
        "heal": 28,
        "fusion_overcharge": 2,
    },
    "lbe_cooling_flask": {
        "name_key": "i18n_chireiden.items.lbe_cooling_flask.name",
        "desc_key": "i18n_chireiden.items.lbe_cooling_flask.desc",
        "category": "consumable",
        "aliases": ["铅铋", "铅铋冷却剂", "冷却剂", "lbe", "coolant"],
        "heal": 36,
        "max_hp_bonus": 4,
    },
    "xen_sample_ampoule": {
        "name_key": "i18n_chireiden.items.xen_sample_ampoule.name",
        "desc_key": "i18n_chireiden.items.xen_sample_ampoule.desc",
        "category": "consumable",
        "aliases": ["xen样本", "晶簇样本", "xen", "ampoule"],
        "heal": 18,
    },
    "headband_blueprint_shard": {
        "name_key": "i18n_chireiden.items.headband_blueprint_shard.name",
        "desc_key": "i18n_chireiden.items.headband_blueprint_shard.desc",
        "category": "consumable",
        "aliases": ["头环手稿", "演算残片", "手稿残片", "blueprint"],
        "heal": 20,
        "max_hp_bonus": 8,
    },
    "headband_of_intellect": {
        "name_key": "i18n_chireiden.items.headband_of_intellect.name",
        "desc_key": "i18n_chireiden.items.headband_of_intellect.desc",
        "category": "consumable",
        "aliases": ["智力头环", "头环", "headband", "headband_of_intellect"],
        "heal": 24,
        "max_hp_bonus": 6,
        "fusion_overcharge": 3,
    },
}

CHIREIDEN_PROPS = {
    "he3_storage_cylinder": {
        "name_key": "i18n_room_interact.props.he3_storage_cylinder.name",
        "desc_key": "i18n_room_interact.props.he3_storage_cylinder.desc",
        "aliases": ["氦三储罐", "物流储罐", "储罐", "cylinder"],
        "gold": 48,
        "reward_item": "he3_fuel_canister",
    },
    "pb_bi_coolant_valve": {
        "name_key": "i18n_room_interact.props.pb_bi_coolant_valve.name",
        "desc_key": "i18n_room_interact.props.pb_bi_coolant_valve.desc",
        "aliases": ["旁通阀", "铅铋阀", "冷却阀", "valve"],
        "heal": 24,
    },
    "tokamak_magnetic_coil": {
        "name_key": "i18n_room_interact.props.tokamak_magnetic_coil.name",
        "desc_key": "i18n_room_interact.props.tokamak_magnetic_coil.desc",
        "aliases": ["超导线圈", "备用线圈", "线圈箱", "coil"],
        "gold": 65,
        "max_hp_bonus": 5,
    },
    "penning_harmonic_console": {
        "name_key": "i18n_room_interact.props.penning_harmonic_console.name",
        "desc_key": "i18n_room_interact.props.penning_harmonic_console.desc",
        "aliases": ["谐振监测台", "监测台", "控制台", "console"],
        "gold": 55,
    },
}

CHIREIDEN_NPCS = {
    "kaenbyou_rin": {
        "name_key": "i18n_room_interact.npcs.kaenbyou_rin.name",
        "desc_key": "i18n_room_interact.npcs.kaenbyou_rin.desc",
        "enemy_name_key": "i18n_room_interact.npcs.kaenbyou_rin.enemy_name",
        "greetings_key": "i18n_chireiden.npcs.kaenbyou_rin.greetings",
        "aliases": ["火焰猫燐", "阿燐", "猫燐", "rin", "orin", "kaenbyou_rin"],
        "base_hp": 180,
        "hp_per_stage": 2,
        "atk": 18,
        "actions": 1,
        "bonus_actions": 1,
        "reward_item": "lbe_cooling_flask",
    },
}

CHIREIDEN_FORCED_TRIGGER_CONFIGS = {
    "reactor_steam_vent": {
        "timing": "on_enter",
        "once": True,
        "chance": 1.0,
        "damage": 8,
        "shield_bonus": 16,
    },
    "he3_orbital_capsule": {
        "timing": "on_enter",
        "once": True,
        "chance": 1.0,
        "gold": 45,
        "item": "he3_fuel_canister",
    },
    "penning_harmonic_alarm": {
        "timing": "on_enter",
        "once": True,
        "chance": 1.0,
        "heal": 14,
        "gold": 40,
    },
}

CHIREIDEN_CARD_POOL = [
    "d_he3_fusion_ignition",
    "pb_bi_coolant_loop",
    "lunar_he3_orbital_drop",
    "int19_tokamak_calculus",
    "penning_trap_lockdown",
    "hisoutensoku_thermonuclear_cannon",
]

CHIREIDEN_CARD_CONFIG = {
    "d_he3_fusion_ignition": {
        "name": "D-He3聚变点火",
        "color": "neutral",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "event_only": True,
        "base_dmg": 20,
        "shield_amount": 8,
        "buff_stacks": 2,
        "draw_count": 1,
        "damage_type": "fire",
        "desc": "造成 20 点火焰伤害，获得 8 点护盾与 2 层聚变超载；若自身已有聚变超载则转为对全体敌人造成等量伤害并抽 1 张牌。",
        "feedback": "纯净氦三聚变火球贯通磁场！",
    },
    "pb_bi_coolant_loop": {
        "name": "铅铋热工循环",
        "color": "neutral",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 0,
        "rarity": "rare",
        "event_only": True,
        "shield_amount": 16,
        "heal_amount": 10,
        "buff_stacks": 2,
        "target_type": "self",
        "desc": "获得 16 点护盾与 2 层磁约束场，清除自身各 1 层流血与灼烧效果，并恢复 10 点生命。",
        "feedback": "银白液态铅铋金属带走多余余热并稳固甲胄。",
    },
    "lunar_he3_orbital_drop": {
        "name": "月都氦三空投",
        "color": "neutral",
        "type": "spell",
        "cost_a": 1,
        "cost_ba": 1,
        "rarity": "epic",
        "event_only": True,
        "base_dmg": 18,
        "action_gain": 1,
        "gain_a": 1,
        "draw_count": 2,
        "damage_type": "force",
        "target_type": "self",
        "desc": "召唤太空电梯氦三补给舱砸落战阵，对全体敌人造成 18 点力场伤害，获得 1A 并抽 2 张牌。",
        "feedback": "静止轨道物流闸门洞开，氦三燃料舱精确落入战场！",
    },
    "int19_tokamak_calculus": {
        "name": "头环托卡马克演算",
        "color": "neutral",
        "type": "spell",
        "cost_a": 0,
        "cost_ba": 1,
        "rarity": "epic",
        "event_only": True,
        "draw_count": 2,
        "action_gain": 1,
        "gain_a": 1,
        "buff_stacks": 3,
        "heal_amount": 6,
        "target_type": "self",
        "exhaust": True,
        "desc": "奥术头环加持下的磁流体方程重构：抽 2 张牌，获得 1A、3 层聚变超载与 6 点生命回复。消耗。",
        "feedback": "奥术符文自头环浮现，托卡马克截面分布一瞬明晰。",
    },
    "penning_trap_lockdown": {
        "name": "彭宁井四极封锁",
        "color": "neutral",
        "type": "spell",
        "cost_a": 2,
        "cost_ba": 0,
        "rarity": "epic",
        "event_only": True,
        "base_dmg": 22,
        "shield_amount": 14,
        "buff_stacks": 2,
        "weak_stacks": 2,
        "damage_type": "lightning",
        "target_type": "self",
        "desc": "张开高能四极电极井，对全体敌人造成 22 点闪电伤害并赋予 2 层虚弱，同时获得 14 点护盾与 2 层磁约束场。",
        "feedback": "高压偶极磁场瞬间收紧，异界波动被死死钉在地面。",
    },
    "hisoutensoku_thermonuclear_cannon": {
        "name": "非想天则热核炮",
        "color": "neutral",
        "type": "attack",
        "cost_a": 2,
        "cost_ba": 0,
        "rarity": "legendary",
        "event_only": True,
        "base_dmg": 34,
        "splash_dmg": 14,
        "overcharge_scale": 4,
        "damage_type": "fire",
        "desc": "轰出非想天则规格热核主炮，对目标造成 34 点火焰伤害并溅射全体敌人 14 点火焰伤害，每层聚变超载额外追加 4 点主伤害。",
        "feedback": "巨型蒸汽风箱怒吼震颤，太阳般的耀斑轰然吞没敌阵！",
    },
}

CHIREIDEN_CARD_UPGRADE_CONFIG = {
    "d_he3_fusion_ignition": {
        "base_dmg": 28,
        "shield_amount": 12,
        "buff_stacks": 3,
        "desc": "造成 28 点火焰伤害，获得 12 点护盾与 3 层聚变超载；若自身已有聚变超载则转为对全体敌人造成等量伤害并抽 1 张牌。",
    },
    "pb_bi_coolant_loop": {
        "shield_amount": 22,
        "heal_amount": 15,
        "buff_stacks": 3,
        "desc": "获得 22 点护盾与 3 层磁约束场，清除自身各 1 层流血与灼烧效果，并恢复 15 点生命。",
    },
    "lunar_he3_orbital_drop": {
        "base_dmg": 25,
        "action_gain": 1,
        "gain_a": 1,
        "draw_count": 3,
        "desc": "召唤太空电梯氦三补给舱砸落战阵，对全体敌人造成 25 点力场伤害，获得 1A 并抽 3 张牌。",
    },
    "int19_tokamak_calculus": {
        "draw_count": 3,
        "action_gain": 2,
        "gain_a": 2,
        "buff_stacks": 4,
        "heal_amount": 10,
        "desc": "奥术头环加持下的磁流体方程重构：抽 3 张牌，获得 2A、4 层聚变超载与 10 点生命回复。消耗。",
    },
    "penning_trap_lockdown": {
        "base_dmg": 30,
        "shield_amount": 20,
        "buff_stacks": 3,
        "weak_stacks": 3,
        "desc": "张开高能四极电极井，对全体敌人造成 30 点闪电伤害并赋予 3 层虚弱，同时获得 20 点护盾与 3 层磁约束场。",
    },
    "hisoutensoku_thermonuclear_cannon": {
        "base_dmg": 46,
        "splash_dmg": 20,
        "overcharge_scale": 6,
        "desc": "轰出非想天则规格热核主炮，对目标造成 46 点火焰伤害并溅射全体敌人 20 点火焰伤害，每层聚变超载额外追加 6 点主伤害。",
    },
}

CHIREIDEN_RELIC_CONFIG = {
    "headband_of_intellect_int19": {
        "name": "智力头环",
        "rarity": "legendary",
        "desc": "原本只应存在于奇幻秘典中的思维增幅头环，不知为何扣在了地狱鸦头顶。每场战斗首次出牌阶段多抽 1 张牌并获得 2 层聚变超载，偶数回合额外抽 1 张牌并获得 1 层聚变超载。",
        "initial_draw_bonus": 1,
        "initial_overcharge": 2,
        "even_turn_draw": 1,
        "even_turn_overcharge": 1,
        "price": 240,
    },
    "lbe_fast_reactor_core": {
        "name": "铅铋快堆微型堆芯",
        "rarity": "epic",
        "desc": "火焰猫燐精心封存的液态铅铋共晶反应堆模块。每场战斗开始获得 10 点护盾与 2 层磁约束场；己方回合结束时若仍有剩余护盾则恢复 4 点生命。",
        "start_shield": 10,
        "start_confinement": 2,
        "end_turn_heal": 4,
        "price": 190,
    },
    "lunar_he3_capsule": {
        "name": "月之都氦三物流舱",
        "rarity": "epic",
        "desc": "连接静止轨道太空电梯末端的微缩燃料舱。每回合首次打出卡牌获得 2 层聚变超载；第 1 与第 3 回合开始额外获得 1A。",
        "card_overcharge": 2,
        "action_bonus": 1,
        "price": 210,
    },
    "penning_ion_stabilizer": {
        "name": "彭宁离子井稳压器",
        "rarity": "legendary",
        "desc": "用以锚定超高维离子陷阱的精密四极电极组。每场战斗首次承伤减免 25%，每次受到敌人伤害后生成 5 点护盾，且初始额外获得 1 层磁约束场。",
        "first_hit_reduction_pct": 25,
        "reactive_shield": 5,
        "start_confinement": 1,
        "price": 250,
    },
}

CHIREIDEN_BUFF_CONFIG = {
    "fusion_overcharge": {
        "name": "聚变超载",
        "desc": "D-He3 聚变能量在体表跃动。玩家每次攻击或法术伤害按层数提高 2 点伤害，并可激发聚变系列卡牌额外效应（每回合末减半）。",
        "dmg_per_stack": 2,
    },
    "magnetic_confinement": {
        "name": "磁约束场",
        "desc": "直流磁约束屏蔽。受到直接攻击时消耗 1 层，将所受伤害降低 25% 并立即生成 4 点反冲护盾。",
        "reduction_pct": 25,
        "rebound_shield": 4,
    },
    "headband_int19_aura": {
        "name": "头环超导算力",
        "desc": "智力头环驱动的超精细D-He3演算矩阵。每回合自动增强灵乌路空聚变输出，调度月都太空电梯补给而不依赖反伤或控牌。",
        "overcharge_gain": 2,
    },
    "lbe_thermal_inertia": {
        "name": "铅铋热惯性",
        "desc": "液态铅铋冷却介质护体，每次火焰猫燐行动后凝结高密度金属护盾，大幅缓冲外力冲击。",
        "end_turn_shield": 12,
    },
    "penning_xen_rift_p1": {
        "name": "彭宁裂缝·一阶谐振",
        "desc": "超级传送门一阶模态：周期性召唤 Xen 猎头蟹与猎犬眼，不含反弹与控牌机制。",
        "bonus_str_per_turn": 1,
    },
    "penning_xen_rift_p2": {
        "name": "彭宁裂缝·二阶扩容",
        "desc": "超级传送门二阶模态：扩张口径投入更多 Xen 猎犬眼与弗地冈，灵乌路空已并入玩家方协作封门。",
        "bonus_str_per_turn": 1,
    },
    "penning_xen_rift_p3": {
        "name": "彭宁裂缝·三阶超临界",
        "desc": "超级传送门三阶模态：密集放出 Xen 弗地冈与牛鱿协同突击，考验防线耐受能力。",
        "bonus_str_per_turn": 2,
    },
    "penning_xen_rift_p4": {
        "name": "彭宁裂缝·四阶终焉封堵",
        "desc": "超级传送门终焉模态：持续召唤全谱系 Xen 异界部队与 Xen 控制器，唯以纯粹火力与防守耐久可破。",
        "bonus_str_per_turn": 2,
    },
    "xen_swarm_link": {
        "name": "Xen 群巢共振",
        "desc": "场上每名 Xen 异界单元共享共振回路，回合结束恢复 4 点生命并加强进攻节奏。",
        "end_turn_heal": 4,
    },
}

CHIREIDEN_LORE = {
    "he3_fuel_canister": {
        "require_seen": "chireiden_he3_fuel",
        "intro_key": "i18n_chireiden.lore.he3_fuel_canister",
    },
    "lbe_cooling_flask": {
        "require_seen": "chireiden_lbe_flask",
        "intro_key": "i18n_chireiden.lore.lbe_cooling_flask",
    },
    "xen_sample_ampoule": {
        "require_seen": "chireiden_xen_ampoule",
        "intro_key": "i18n_chireiden.lore.xen_sample_ampoule",
    },
    "headband_blueprint_shard": {
        "require_seen": "chireiden_blueprint",
        "intro_key": "i18n_chireiden.lore.headband_blueprint_shard",
    },
    "headband_of_intellect": {
        "require_seen": "chireiden_headband_known",
        "intro_key": "i18n_chireiden.lore.headband_of_intellect_rumor",
        "secret": {
            "reveal": "chireiden_headband_full",
            "hint_key": "i18n_chireiden.lore.headband_of_intellect_hint",
            "reveal_key": "i18n_chireiden.lore.headband_of_intellect",
        },
    },
}

CHIREIDEN_LANDMARK_IDS = (
    "chireiden_fusion_terminal",
    "chireiden_penning_stabilizer",
)

CHIREIDEN_FLOOR_QUERY_ALIASES = (
    "地灵殿核聚变控制中心",
    "地灵殿",
    "核聚变控制中心",
    "chireiden_fusion_center",
    "chireiden",
    "3.5层",
    "3.5",
)

CHIREIDEN_TRIGGER_QUERY_IDS = (
    "reactor_steam_vent",
    "he3_orbital_capsule",
    "penning_harmonic_alarm",
)

CHIREIDEN_RUMOR_ENEMY_IDS = frozenset({"灵乌路空", "火焰猫燐"})

CHIREIDEN_RUMOR_GREETING_NPCS = {
    "hakurei_reimu": 3,
    "kirisame_marisa": 3,
    "patchouli_knowledge": 3,
}
