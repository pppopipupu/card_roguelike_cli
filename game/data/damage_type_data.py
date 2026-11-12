PHYSICAL_DAMAGE_TYPES = ("slashing", "piercing", "bludgeoning")

PHYSICAL_DAMAGE_ALIASES = ("attack",)

MAGIC_DAMAGE_VARIANTS = {
    "slashing_magic": "slashing",
    "piercing_magic": "piercing",
    "bludgeoning_magic": "bludgeoning"
}

MAGIC_DAMAGE_TYPES = (
    "acid",
    "cold",
    "fire",
    "force",
    "lightning",
    "necrotic",
    "poison",
    "psychic",
    "radiant",
    "thunder",
    "true",
    "slashing_magic",
    "piercing_magic",
    "bludgeoning_magic"
)

DAMAGE_TYPE_QUERY_ENTRIES = {
    "physical_damage": {
        "name_key": "i18n_battle_misc.damage_type_physical_name",
        "desc_key": "i18n_battle_misc.damage_type_physical_desc",
        "members": PHYSICAL_DAMAGE_TYPES,
        "aliases": ("物理", "物理伤害", "physical", "physical_damage")
    },
    "magic_damage": {
        "name_key": "i18n_battle_misc.damage_type_magic_name",
        "desc_key": "i18n_battle_misc.damage_type_magic_desc",
        "members": MAGIC_DAMAGE_TYPES,
        "aliases": ("魔法", "魔法伤害", "magic", "magical", "magic_damage")
    },
    "slashing": {
        "name_key": "i18n_battle_misc.damage_type_slashing",
        "category": "physical_damage",
        "aliases": ("挥砍", "挥砍伤害", "slashing")
    },
    "piercing": {
        "name_key": "i18n_battle_misc.damage_type_piercing",
        "category": "physical_damage",
        "aliases": ("穿刺", "穿刺伤害", "piercing")
    },
    "bludgeoning": {
        "name_key": "i18n_battle_misc.damage_type_bludgeoning",
        "category": "physical_damage",
        "aliases": ("钝击", "钝击伤害", "bludgeoning")
    },
    "acid": {
        "name_key": "i18n_battle_misc.damage_type_acid",
        "category": "magic_damage",
        "aliases": ("强酸", "强酸伤害", "acid")
    },
    "cold": {
        "name_key": "i18n_battle_misc.damage_type_cold",
        "category": "magic_damage",
        "aliases": ("寒冷", "寒冷伤害", "cold")
    },
    "fire": {
        "name_key": "i18n_battle_misc.damage_type_fire",
        "category": "magic_damage",
        "aliases": ("火焰", "火焰伤害", "fire")
    },
    "force": {
        "name_key": "i18n_battle_misc.damage_type_force",
        "category": "magic_damage",
        "aliases": ("力场", "力场伤害", "force")
    },
    "lightning": {
        "name_key": "i18n_battle_misc.damage_type_lightning",
        "category": "magic_damage",
        "aliases": ("闪电", "闪电伤害", "lightning")
    },
    "necrotic": {
        "name_key": "i18n_battle_misc.damage_type_necrotic",
        "category": "magic_damage",
        "aliases": ("黯蚀", "黯蚀伤害", "necrotic")
    },
    "poison": {
        "name_key": "i18n_battle_misc.damage_type_poison",
        "category": "magic_damage",
        "aliases": ("毒素", "毒素伤害", "poison")
    },
    "psychic": {
        "name_key": "i18n_battle_misc.damage_type_psychic",
        "category": "magic_damage",
        "aliases": ("心灵", "心灵伤害", "psychic")
    },
    "radiant": {
        "name_key": "i18n_battle_misc.damage_type_radiant",
        "category": "magic_damage",
        "aliases": ("光耀", "光耀伤害", "radiant")
    },
    "thunder": {
        "name_key": "i18n_battle_misc.damage_type_thunder",
        "category": "magic_damage",
        "aliases": ("雷鸣", "雷鸣伤害", "thunder")
    },
    "true": {
        "name_key": "i18n_battle_misc.damage_type_true",
        "category": "magic_damage",
        "desc_key": "i18n_battle_misc.damage_type_true_desc",
        "aliases": ("真实", "真实伤害", "true")
    },
    "slashing_magic": {
        "name_key": "i18n_battle_misc.damage_type_slashing_magic",
        "category": "magic_damage",
        "desc_key": "i18n_battle_misc.damage_type_slashing_magic_desc",
        "aliases": ("挥砍魔法", "挥砍(魔法)", "slashing_magic", "magic_slashing")
    },
    "piercing_magic": {
        "name_key": "i18n_battle_misc.damage_type_piercing_magic",
        "category": "magic_damage",
        "desc_key": "i18n_battle_misc.damage_type_piercing_magic_desc",
        "aliases": ("穿刺魔法", "穿刺(魔法)", "piercing_magic", "magic_piercing")
    },
    "bludgeoning_magic": {
        "name_key": "i18n_battle_misc.damage_type_bludgeoning_magic",
        "category": "magic_damage",
        "desc_key": "i18n_battle_misc.damage_type_bludgeoning_magic_desc",
        "aliases": ("钝击魔法", "钝击(魔法)", "bludgeoning_magic", "magic_bludgeoning")
    }
}


def damage_type_value(damage_type):
    return damage_type.value if hasattr(damage_type, "value") else str(damage_type)


def base_damage_type(damage_type):
    dtype = damage_type_value(damage_type)
    return MAGIC_DAMAGE_VARIANTS.get(dtype, dtype)


def is_physical_damage(damage_type):
    return damage_type_value(damage_type) in PHYSICAL_DAMAGE_TYPES + PHYSICAL_DAMAGE_ALIASES


def is_magic_damage(damage_type):
    return not is_physical_damage(damage_type)


def damage_type_matches(damage_type, expected):
    dtype = damage_type_value(damage_type)
    return dtype == expected or base_damage_type(dtype) == expected


def is_spell_card_damage(event):
    card = getattr(event, "card", None)
    if card is not None:
        return getattr(card, "type", "") == "spell"
    return damage_type_value(getattr(event, "damage_type", "")) == "spell"
