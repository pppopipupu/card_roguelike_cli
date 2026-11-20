from typing import Tuple, List, Optional
from ...data.enemy_data_normal import ENEMY_INTENT_SCALING
from ...data.locale_data import get_locale_text

class EnemyTemplate:
    def __init__(self, name: str):
        self.name = name

    def roll_intents(self, run, engine, enemy) -> List:
        from ...models.state import EnemyIntentState
        stage = run.player.stage
        intents_list = []
        for _ in range(enemy.max_actions):
            itype, val, desc = self._roll_single_intent(run, enemy, stage)
            intents_list.append(EnemyIntentState(
                type=itype,
                val=val,
                desc=desc,
                cost_a=1,
                cost_ba=0
            ))
        for _ in range(enemy.max_bonus_actions):
            itype, val, desc = self._roll_single_intent(run, enemy, stage)
            intents_list.append(EnemyIntentState(
                type=itype,
                val=val,
                desc=desc,
                cost_a=0,
                cost_ba=1
            ))
        return intents_list

    def _roll_single_intent(self, run, enemy, stage) -> Tuple[str, int, str]:
        import random
        attack_scaling = ENEMY_INTENT_SCALING["attack"]
        defend_scaling = ENEMY_INTENT_SCALING["defend"]
        intents = [
            ("attack", attack_scaling["base"] + stage // attack_scaling["stage_divisor"] + random.randint(attack_scaling["random_min"], attack_scaling["random_max"])),
            ("defend", defend_scaling["base"] + stage * defend_scaling["stage_multiplier"] + random.randint(defend_scaling["random_min"], defend_scaling["random_max"]))
        ]
        itype, val = random.choice(intents)
        if itype == "attack":
            desc = get_locale_text("i18n_entity_wiring.enemy_base.intent_attack", val=val)
        else:
            desc = get_locale_text("i18n_entity_wiring.enemy_base.intent_defend", val=val)
        return itype, val, desc

    def _perform_attack(self, run, engine, enemy, dmg: int, logs: List[str], damage_type: str = "bludgeoning"):
        p = run.player
        import random
        final_dmg = dmg
        target_key = engine.combat_resolver.pick_ward_minion(p)
        if target_key is not None:
            target = p.minions[target_key]
            m_name = target.name
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, f"p{target_key}", final_dmg, source=f"enemy:{enemy.name}", damage_type=damage_type)
            after_logs = run.node_data.get("battle_logs", [])
            if len(after_logs) > before_len:
                dmg_msg = after_logs.pop()
                logs.append(get_locale_text("i18n_entity_wiring.enemy_base.ward_attack", name=enemy.name, m_name=m_name, dmg_msg=dmg_msg))
        else:
            if p.minions and random.random() < 0.5:
                target_key = random.choice(list(p.minions.keys()))
                target = p.minions[target_key]
                m_name = target.name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{target_key}", final_dmg, source=f"enemy:{enemy.name}", damage_type=damage_type)
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(get_locale_text("i18n_entity_wiring.enemy_base.minion_attack", name=enemy.name, m_name=m_name, dmg_msg=dmg_msg))
            else:
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", final_dmg, source=f"enemy:{enemy.name}", damage_type=damage_type)
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(get_locale_text("i18n_entity_wiring.enemy_base.player_attack", name=enemy.name, dmg_msg=dmg_msg))

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None) -> str | None:
        if logs is None:
            logs = []
        from .trash_talk_actions import try_trash_talk
        try_trash_talk(run, enemy, logs)
        if intent.type == "attack":
            self._perform_attack(run, engine, enemy, intent.val, logs)
        elif intent.type == "defend":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_entity_wiring.enemy_base.defend_log", name=enemy.name, val=intent.val))

    def on_enemy_before_death(self, run, enemy, event, engine):
        pass

    def on_card_play(self, event, enemy, engine):
        pass

    def on_turn_start(self, event, enemy, engine):
        pass

    def on_turn_end(self, event, enemy, engine):
        pass

    def on_battle_start(self, run, enemy, engine):
        pass

    def on_card_played(self, event, enemy, engine):
        pass

    def on_damage_take(self, event, enemy, engine):
        pass

    def on_damage_calculate(self, event, enemy, engine):
        pass

    def on_card_exhaust(self, event, enemy, engine):
        pass

    def on_minion_death(self, event, enemy, engine):
        pass

    def apply_phase_transition(self, run, enemy, target_phase: int, engine, logs: list):
        pass

ALL_ENEMIES = {}

def register_enemy(name: str):
    def decorator(cls):
        ALL_ENEMIES[name] = cls(name)
        return cls
    return decorator

def get_enemy_template(name: str) -> EnemyTemplate:
    ghost_prefix = get_locale_text("i18n_battle_core.ghost_default_name")
    ghost_suffix = get_locale_text("i18n_battle_core.ghost_name_suffix")
    if name.startswith(ghost_prefix) or (ghost_suffix and name.endswith(ghost_suffix)):
        from .ghost import GhostEnemyTemplate
        return GhostEnemyTemplate(name)
    if name in ALL_ENEMIES:
        return ALL_ENEMIES[name]
    if " · " in name:
        short_tail = name.rsplit(" · ", 1)[-1].strip()
        if short_tail in ALL_ENEMIES:
            return ALL_ENEMIES[short_tail]
    if " " in name:
        no_prefix = name.split(" ", 1)[-1].strip()
        if no_prefix in ALL_ENEMIES:
            return ALL_ENEMIES[no_prefix]
    base_name = name.split(" ")[0] if name else ""
    return ALL_ENEMIES.get(base_name, EnemyTemplate(base_name))
