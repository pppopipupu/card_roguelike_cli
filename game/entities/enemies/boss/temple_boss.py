from typing import List

from ..base import EnemyTemplate, register_enemy
from ....data.temple_config import BOSS_NAME, CULTIST_NAMES, TEMPLE_INTENTS
from ....data.locale_data import get_locale_text


def _intent(itype: str, val: int, desc: str, cost_a: int, cost_ba: int):
    from ....models.state import EnemyIntentState
    return EnemyIntentState(type=itype, val=val, desc=desc, cost_a=cost_a, cost_ba=cost_ba)


def _bonus(run) -> int:
    return int(run.node_data.get("temple_attack_bonus", 0) or 0)


def _enemy_slot(run, enemy) -> str:
    return f"e{run.enemies.index(enemy) + 1}" if enemy in run.enemies else "e1"


class TempleCultistTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        turn = int(run.node_data.get("temple_cultist_turn", 0) or 0) + 1
        run.node_data["temple_cultist_turn"] = turn
        key = ("ember", "chant", "ward")[(turn - 1) % 3]
        val = int(TEMPLE_INTENTS["cultist"][key])
        desc = get_locale_text(f"i18n_temple.cultist_intent.{key}", val=val)
        return [_intent(f"temple_{key}", val, desc, 1, 0)]

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            return ""
        if intent.type == "temple_ember":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="fire")
            logs.append(get_locale_text("i18n_temple.cultist_log.ember", name=enemy.name, dmg=dmg))
        elif intent.type == "temple_chant":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="force")
            logs.append(get_locale_text("i18n_temple.cultist_log.chant", name=enemy.name, dmg=dmg))
        elif intent.type == "temple_ward":
            engine._gain_shield(run, _enemy_slot(run, enemy), intent.val)
            logs.append(get_locale_text("i18n_temple.cultist_log.ward", name=enemy.name, val=intent.val))
        return "\n".join(logs)


class TempleAurilTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        turn = int(run.node_data.get("temple_boss_turn", 0) or 0) + 1
        run.node_data["temple_boss_turn"] = turn
        cfg = TEMPLE_INTENTS["auril"]
        cycle = (turn - 1) % 4
        if cycle == 0:
            a_key, ba_key = "frost_lance", "winter_veil"
        elif cycle == 1:
            a_key, ba_key = "aurora_gaze", "winter_veil"
        elif cycle == 2:
            a_key, ba_key = "absolute_zero", "winter_veil"
        else:
            a_key, ba_key = "frost_lance", "aurora_gaze"
        return [
            _intent(f"temple_{a_key}", int(cfg[a_key]), get_locale_text(f"i18n_temple.boss_intent.{a_key}", val=cfg[a_key]), 1, 0),
            _intent(f"temple_{ba_key}", int(cfg[ba_key]), get_locale_text(f"i18n_temple.boss_intent.{ba_key}", val=cfg[ba_key]), 0, 1),
        ]

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            return ""
        if intent.type == "temple_frost_lance":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            logs.append(get_locale_text("i18n_temple.boss_log.frost_lance", dmg=dmg))
        elif intent.type == "temple_aurora_gaze":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            logs.append(get_locale_text("i18n_temple.boss_log.aurora_gaze", dmg=dmg * 2))
        elif intent.type == "temple_absolute_zero":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            engine._add_buff_to(run.player, "vulnerable", get_locale_text("i18n_battle_core.buff_vulnerable_name"), get_locale_text("i18n_battle_core.buff_vulnerable_desc"), 1)
            logs.append(get_locale_text("i18n_temple.boss_log.absolute_zero", dmg=dmg))
        elif intent.type == "temple_winter_veil":
            engine._gain_shield(run, _enemy_slot(run, enemy), intent.val)
            logs.append(get_locale_text("i18n_temple.boss_log.winter_veil", val=intent.val))
        return "\n".join(logs)


for _name in CULTIST_NAMES:
    register_enemy(_name)(TempleCultistTemplate)

register_enemy(BOSS_NAME)(TempleAurilTemplate)
