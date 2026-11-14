from typing import List

from ..base import EnemyTemplate, register_enemy
from ....data.locale_data import get_locale_text
from ....data.outer_plane_config import OUTER_PLANE_ENCOUNTERS, OUTER_PLANE_INTENTS


def _intent(itype: str, val: int, desc: str, cost_a: int, cost_ba: int):
    from ....models.state import EnemyIntentState
    return EnemyIntentState(type=itype, val=val, desc=desc, cost_a=cost_a, cost_ba=cost_ba)


def _slot(run, enemy) -> str:
    return f"e{run.enemies.index(enemy) + 1}" if enemy in run.enemies else "e1"


class OuterPlaneWraithTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        turn = int(run.node_data.get("outer_plane_turn", 0) or 0) + 1
        run.node_data["outer_plane_turn"] = turn
        key = ("gnaw", "hush", "veil")[(turn - 1) % 3]
        val = int(OUTER_PLANE_INTENTS["wraith"][key])
        desc = get_locale_text(f"i18n_outer_plane.intent.{key}", val=val)
        return [_intent(f"outer_{key}", val, desc, 1, 0)]

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            return ""
        if intent.type == "outer_gnaw":
            engine._damage_target(run, "p0", intent.val, source=f"enemy:{enemy.name}", damage_type="psychic")
            logs.append(get_locale_text("i18n_outer_plane.log.gnaw", name=enemy.name, dmg=intent.val))
        elif intent.type == "outer_hush":
            engine._damage_target(run, "p0", intent.val, source=f"enemy:{enemy.name}", damage_type="force")
            logs.append(get_locale_text("i18n_outer_plane.log.hush", name=enemy.name, dmg=intent.val))
        elif intent.type == "outer_veil":
            engine._gain_shield(run, _slot(run, enemy), intent.val)
            logs.append(get_locale_text("i18n_outer_plane.log.veil", name=enemy.name, val=intent.val))
        return "\n".join(logs)


class OuterPlaneGuardianTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        turn = int(run.node_data.get("outer_plane_turn", 0) or 0) + 1
        run.node_data["outer_plane_turn"] = turn
        cfg = OUTER_PLANE_INTENTS["guardian"]
        cycle = (turn - 1) % 4
        if cycle == 0:
            a_key, ba_key = "hammer", "seal"
        elif cycle == 1:
            a_key, ba_key = "gaze", "seal"
        elif cycle == 2:
            a_key, ba_key = "collapse", "seal"
        else:
            a_key, ba_key = "hammer", "gaze"
        return [
            _intent(f"outer_{a_key}", int(cfg[a_key]), get_locale_text(f"i18n_outer_plane.intent.{a_key}", val=cfg[a_key]), 1, 0),
            _intent(f"outer_{ba_key}", int(cfg[ba_key]), get_locale_text(f"i18n_outer_plane.intent.{ba_key}", val=cfg[ba_key]), 0, 1),
        ]

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            return ""
        if intent.type == "outer_hammer":
            engine._damage_target(run, "p0", intent.val, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            logs.append(get_locale_text("i18n_outer_plane.log.hammer", name=enemy.name, dmg=intent.val))
        elif intent.type == "outer_gaze":
            engine._damage_target(run, "p0", intent.val, source=f"enemy:{enemy.name}", damage_type="psychic")
            engine._damage_target(run, "p0", intent.val, source=f"enemy:{enemy.name}", damage_type="psychic")
            logs.append(get_locale_text("i18n_outer_plane.log.gaze", name=enemy.name, dmg=intent.val * 2))
        elif intent.type == "outer_collapse":
            engine._damage_target(run, "p0", intent.val, source=f"enemy:{enemy.name}", damage_type="force")
            engine._add_buff_to(
                run.player, "vulnerable",
                get_locale_text("i18n_battle_core.buff_vulnerable_name"),
                get_locale_text("i18n_battle_core.buff_vulnerable_desc"), 1,
            )
            logs.append(get_locale_text("i18n_outer_plane.log.collapse", name=enemy.name, dmg=intent.val))
        elif intent.type == "outer_seal":
            engine._gain_shield(run, _slot(run, enemy), intent.val)
            logs.append(get_locale_text("i18n_outer_plane.log.seal", name=enemy.name, val=intent.val))
        return "\n".join(logs)


for _cfg in OUTER_PLANE_ENCOUNTERS.values():
    _template = OuterPlaneGuardianTemplate if _cfg.get("boss") else OuterPlaneWraithTemplate
    for _entry in _cfg["enemies"]:
        register_enemy(get_locale_text(_entry["name_key"]))(_template)
