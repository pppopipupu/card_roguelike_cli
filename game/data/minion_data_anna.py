from .anna_card_config import ANNE_ATTACK_DAMAGE_TYPE, ANNE_SKILL_CONFIG, ANNE_SPIRIT_CONFIG

_SKILL_DESC = (
    "消耗 {a} 点动作点，随机使抽牌堆与弃牌堆中的 {count} 张卡牌消失，"
    "并对所有存活敌人随机分配 {dmg} 点火焰伤害。"
).format(
    a=ANNE_SKILL_CONFIG["cost_a"],
    count=ANNE_SKILL_CONFIG["vanish_count"],
    dmg=ANNE_SKILL_CONFIG["fire_damage_total"],
)


def _skill_entry():
    return {
        "id": ANNE_SKILL_CONFIG["id"],
        "name": "湮没之焰",
        "cost_a": ANNE_SKILL_CONFIG["cost_a"],
        "cost_ba": ANNE_SKILL_CONFIG["cost_ba"],
        "desc": _SKILL_DESC,
    }


ANNA_MINION_CONFIG = {
    "manaeria_queen_anne": {
        "name": "马纳历亚女王‧安",
        "attack_damage_type": ANNE_ATTACK_DAMAGE_TYPE,
        "skills": [_skill_entry()],
    },
    "manaeria_queen_anne+": {
        "name": "马纳历亚女王‧安+",
        "attack_damage_type": ANNE_ATTACK_DAMAGE_TYPE,
        "skills": [_skill_entry()],
    },
    "anna_great_spirit": {
        "name": "安的巨大英灵",
        "attack_damage_type": ANNE_SPIRIT_CONFIG["attack_damage_type"],
        "ward": ANNE_SPIRIT_CONFIG["ward"],
        "skills": [],
    },
}
