from typing import Tuple, List
from .base import EnemyTemplate, register_enemy
from ...models.state import EnemyIntentState, BuffState
from ...data.locale_data import get_locale_text

@register_enemy("训练假人")
class DummyTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List[EnemyIntentState]:
        return []

@register_enemy("测试训练假人")
class TestDummyTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List[EnemyIntentState]:
        turn = run.node_data.get("test_dummy_turn", 1)
        run.node_data["test_dummy_turn"] = turn + 1
        intents_list = []
        if turn % 2 == 1:
            intents_list.append(EnemyIntentState(
                type="attack",
                val=10,
                desc=get_locale_text("i18n_enemy_misc.test_dummy.sweep"),
                cost_a=1,
                cost_ba=0
            ))
        else:
            intents_list.append(EnemyIntentState(
                type="defend",
                val=10,
                desc=get_locale_text("i18n_enemy_misc.test_dummy.repair"),
                cost_a=1,
                cost_ba=0
            ))
        return intents_list

@register_enemy("NoobSlayer99")
class NoobSlayer99Template(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List[EnemyIntentState]:
        turn = run.node_data.get("noob_turn", 1)
        run.node_data["noob_turn"] = turn + 1
        intents_list = []
        if turn % 2 == 1:
            intents_list.append(EnemyIntentState(
                type="attack",
                val=8,
                desc=get_locale_text("i18n_enemy_misc.noob_slayer.fireball"),
                cost_a=1,
                cost_ba=0
            ))
        else:
            intents_list.append(EnemyIntentState(
                type="defend",
                val=8,
                desc=get_locale_text("i18n_enemy_misc.noob_slayer.ice_armor"),
                cost_a=1,
                cost_ba=0
            ))
        return intents_list

@register_enemy("xXx_SniperElite_xXx")
class SniperEliteTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List[EnemyIntentState]:
        turn = run.node_data.get("sniper_turn", 1)
        run.node_data["sniper_turn"] = turn + 1
        intents_list = []
        if turn % 2 == 1:
            intents_list.append(EnemyIntentState(
                type="aim",
                val=0,
                desc=get_locale_text("i18n_enemy_misc.sniper_elite.aim"),
                cost_a=1,
                cost_ba=0
            ))
        else:
            intents_list.append(EnemyIntentState(
                type="attack",
                val=18,
                desc=get_locale_text("i18n_enemy_misc.sniper_elite.shot"),
                cost_a=1,
                cost_ba=0
            ))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        from .trash_talk_actions import try_trash_talk
        try_trash_talk(run, enemy, logs)
        if intent.type == "aim":
            enemy.buffs.append(BuffState(id="strength", name=get_locale_text("i18n_enemy_misc.common.strength_name"), stacks=3, desc=get_locale_text("i18n_enemy_misc.sniper_elite.strength_desc")))
            logs.append(get_locale_text("i18n_enemy_misc.sniper_elite.aim_log", name=enemy.name))
        else:
            for b in list(enemy.buffs):
                if b.id == "strength":
                    enemy.buffs.remove(b)
            super().execute_intent(run, engine, enemy, intent, logs)

@register_enemy("pppopipupu")
class PppopipupuTemplate(EnemyTemplate):
    def on_enemy_before_death(self, run, enemy, event, engine):
        if enemy.name == "pppopipupu":
            event.cancel()
            enemy.hp = 1
            enemy.shield = 0
            if "pending_transitions" not in run.node_data:
                run.node_data["pending_transitions"] = {}
            run.node_data["pending_transitions"][enemy.name] = 2
            from ...models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_misc.common.phase_transition_name"), stacks=1, desc=get_locale_text("i18n_enemy_misc.common.phase_transition_desc")))
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc=get_locale_text("i18n_enemy_misc.pppopipupu.phase_intent"),
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, get_locale_text("i18n_enemy_misc.pppopipupu.phase_log"))

    def apply_phase_transition(self, run, enemy, target_phase: int, engine, logs: list):
        if target_phase == 2:
            enemy.name = "【觉醒】pppopipupu"
            enemy.max_hp = 9999
            enemy.hp = 9999
            enemy.shield = 0
            enemy.actions = 1
            enemy.bonus_actions = 0
            enemy.max_actions = 1
            enemy.max_bonus_actions = 0
            enemy.buffs.clear()
            from ...models.state import BuffState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_misc.common.phase_transition_name"), stacks=1, desc=get_locale_text("i18n_enemy_misc.common.phase_transition_desc")))
            run.node_data["pppopipupu_phase"] = 2
            logs.append(get_locale_text("i18n_enemy_misc.pppopipupu.awaken_log"))

    def roll_intents(self, run, engine, enemy) -> List[EnemyIntentState]:
        phase = run.node_data.get("pppopipupu_phase", 1)
        intents_list = []
        if phase == 2:
            intents_list.append(EnemyIntentState(
                type="force_strike",
                val=100,
                desc=get_locale_text("i18n_enemy_misc.pppopipupu.force_strike_intent"),
                cost_a=1,
                cost_ba=0
            ))
        else:
            intents_list.append(EnemyIntentState(
                type="fish",
                val=0,
                desc=get_locale_text("i18n_enemy_misc.pppopipupu.fish_intent"),
                cost_a=1,
                cost_ba=0
            ))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        from .trash_talk_actions import try_trash_talk
        try_trash_talk(run, enemy, logs)
        if intent.type == "force_strike":
            engine._damage_target(run, "p0", 100, source=f"enemy:{enemy.name}", damage_type="force")
            logs.append(get_locale_text("i18n_enemy_misc.pppopipupu.force_strike_log", name=enemy.name))
        else:
            logs.append(get_locale_text("i18n_enemy_misc.pppopipupu.fish_log", name=enemy.name))

register_enemy("【觉醒】pppopipupu")(PppopipupuTemplate)

@register_enemy("Gate_Guardian")
class GateGuardianTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List[EnemyIntentState]:
        turn = run.node_data.get("guardian_turn", 1)
        run.node_data["guardian_turn"] = turn + 1
        intents_list = []
        cycle = (turn - 1) % 3 + 1
        if cycle == 1:
            intents_list.append(EnemyIntentState(
                type="attack",
                val=12,
                desc=get_locale_text("i18n_enemy_misc.gate_guardian.slash"),
                cost_a=1,
                cost_ba=0
            ))
        elif cycle == 2:
            intents_list.append(EnemyIntentState(
                type="defend",
                val=15,
                desc=get_locale_text("i18n_enemy_misc.gate_guardian.block"),
                cost_a=1,
                cost_ba=0
            ))
        else:
            intents_list.append(EnemyIntentState(
                type="attack",
                val=20,
                desc=get_locale_text("i18n_enemy_misc.gate_guardian.bash"),
                cost_a=1,
                cost_ba=0
            ))
        return intents_list
