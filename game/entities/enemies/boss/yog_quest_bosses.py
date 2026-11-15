from typing import List

from ..base import EnemyTemplate, register_enemy
from ....data.yog_quest_config import YOG_BOSS_INTENTS, YOG_BOSS_NAME, YOG_CULTISTS
from ....data.locale_data import get_locale_text


def _intent(itype: str, val: int, desc: str, cost_a: int, cost_ba: int):
    from ....models.state import EnemyIntentState
    return EnemyIntentState(type=itype, val=val, desc=desc, cost_a=cost_a, cost_ba=cost_ba)


def _bonus(run) -> int:
    fm = getattr(run, "floor_map", None)
    if fm is None:
        return 0
    flags = fm.floor_flags.get("yog_flags") or {}
    return 3 if flags.get("altar_defiled") else 0


def _enemy_slot(run, enemy) -> str:
    return f"e{run.enemies.index(enemy) + 1}" if enemy in run.enemies else "e1"


class YogCultistTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        turn = int(run.node_data.get("yog_cultist_turn", 0) or 0) + 1
        run.node_data["yog_cultist_turn"] = turn
        key = ("ember", "chant", "ward")[(turn - 1) % 3]
        val = int(YOG_BOSS_INTENTS["cultist"][key])
        desc = get_locale_text(f"i18n_yog_quest.cultist_intent.{key}", val=val)
        return [_intent(f"yog_{key}", val, desc, 1, 0)]

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            return ""
        if intent.type == "yog_ember":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="fire")
            logs.append(get_locale_text("i18n_yog_quest.cultist_log.ember", name=enemy.name, dmg=dmg))
        elif intent.type == "yog_chant":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="force")
            logs.append(get_locale_text("i18n_yog_quest.cultist_log.chant", name=enemy.name, dmg=dmg))
        elif intent.type == "yog_ward":
            engine._gain_shield(run, _enemy_slot(run, enemy), intent.val)
            logs.append(get_locale_text("i18n_yog_quest.cultist_log.ward", name=enemy.name, val=intent.val))
        return "\n".join(logs)


class YogAurilTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        turn = int(run.node_data.get("yog_boss_turn", 0) or 0) + 1
        run.node_data["yog_boss_turn"] = turn
        cfg = YOG_BOSS_INTENTS["auril"]
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
            _intent(f"yog_{a_key}", int(cfg[a_key]), get_locale_text(f"i18n_yog_quest.boss_intent.{a_key}", val=cfg[a_key]), 1, 0),
            _intent(f"yog_{ba_key}", int(cfg[ba_key]), get_locale_text(f"i18n_yog_quest.boss_intent.{ba_key}", val=cfg[ba_key]), 0, 1),
        ]

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            return ""
        if intent.type == "yog_frost_lance":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            logs.append(get_locale_text("i18n_yog_quest.boss_log.frost_lance", dmg=dmg))
        elif intent.type == "yog_aurora_gaze":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            logs.append(get_locale_text("i18n_yog_quest.boss_log.aurora_gaze", dmg=dmg * 2))
        elif intent.type == "yog_absolute_zero":
            dmg = intent.val + _bonus(run)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            engine._add_buff_to(run.player, "vulnerable", get_locale_text("i18n_battle_core.buff_vulnerable_name"), get_locale_text("i18n_battle_core.buff_vulnerable_desc"), 1)
            logs.append(get_locale_text("i18n_yog_quest.boss_log.absolute_zero", dmg=dmg))
        elif intent.type == "yog_winter_veil":
            engine._gain_shield(run, _enemy_slot(run, enemy), intent.val)
            logs.append(get_locale_text("i18n_yog_quest.boss_log.winter_veil", val=intent.val))
        return "\n".join(logs)


for _name in YOG_CULTISTS:
    register_enemy(_name)(YogCultistTemplate)

register_enemy(YOG_BOSS_NAME)(YogAurilTemplate)
