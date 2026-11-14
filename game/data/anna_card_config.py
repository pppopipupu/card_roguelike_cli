ANNE_CARD_ID = "manaeria_queen_anne"
ANNE_SPIRIT_ID = "anna_great_spirit"
EXCELLENT_CRIT_ID = "excellent_crit"

CARD_PILES = ("draw_pile", "discard_pile")

ANNE_ATTACK_DAMAGE_TYPE = "fire"

ANNE_FANFARE_CONFIG = {
    "vanish_count": 2,
    "piles_less_than": 5,
    "piles_less_than_upgraded": 7,
    "count_piles": CARD_PILES,
    "spirit_minion_id": ANNE_SPIRIT_ID,
    "bonus_card_id": EXCELLENT_CRIT_ID,
}

ANNE_SPIRIT_CONFIG = {
    "minion_hp": 50,
    "minion_atk": 20,
    "attack_damage_type": "bludgeoning",
    "ward": True,
    "attack_actions_bonus": 2,
    "dies_on_turn_start": True,
}

ANNE_SKILL_CONFIG = {
    "id": "anne_vanish",
    "cost_a": 1,
    "cost_ba": 0,
    "vanish_count": 1,
    "fire_damage_total": 20,
    "attack_damage_type": "fire",
}

EXCELLENT_CRIT_CONFIG = {
    "base": {"force": 10, "true": 10},
    "tiers": (
        {"op": "eq", "value": 0, "force": 200, "true": 200},
        {"op": "lt", "value": 3, "force": 80, "true": 80},
        {"op": "lt", "value": 5, "force": 40, "true": 40},
        {"op": "lt", "value": 8, "force": 20, "true": 20},
    ),
    "count_piles": CARD_PILES,
    "damage_types": ("force", "true"),
}
