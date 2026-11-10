from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.buff_data import BUFF_CONFIG
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text


def _intent_entry(enemy_name: str, intent_id: str) -> dict:
    for entry in ENEMY_CONFIG.get(enemy_name, {}).get("intents", []):
        if entry.get("id") == intent_id:
            return entry
    return {}


def _make_intent(intent_id: str, val: int, desc: str, cost_a: int, cost_ba: int):
    from ....models.state import EnemyIntentState
    return EnemyIntentState(type=intent_id, val=val, desc=desc, cost_a=cost_a, cost_ba=cost_ba)


@register_enemy("远古红龙")
class BossRedDragonTemplate(EnemyTemplate):
    def on_battle_start(self, run, enemy, engine):
        engine._add_buff_to(
            enemy,
            "dragon_scales_passive",
            get_locale_text("i18n_enemy_boss.buff_dragon_scales"),
            get_locale_text("i18n_enemy_boss.buff_dragon_scales_desc"),
            1,
        )

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        turn = int(run.node_data.get("red_dragon_turn", 1))
        run.node_data["red_dragon_turn"] = turn + 1
        script_turn = (turn - 1) % 4 + 1
        defend_val = _intent_entry(self.name, "defend").get("val", 10)
        roar_val = _intent_entry(self.name, "dragon_roar").get("val", 1)
        breath_val = _intent_entry(self.name, "fire_breath").get("val", 12)
        sweep_val = _intent_entry(self.name, "tail_sweep").get("val", 6)
        molten_val = _intent_entry(self.name, "molten_inhale").get("val", 16)
        fireball_val = _intent_entry(self.name, "fireball").get("val", 6)
        inferno_val = _intent_entry(self.name, "inferno_breath").get("val", 12)
        devour_val = _intent_entry(self.name, "devour_imp").get("val", 12)
        guard_val = 8
        if script_turn == 1:
            return [
                _make_intent("summon", 2, get_locale_text("i18n_enemy_boss.red_dragon_intent_summon"), 1, 0),
                _make_intent("defend", defend_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_defend", val=defend_val), 0, 1),
                _make_intent("dragon_roar", roar_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_dragon_roar"), 0, 1),
            ]
        if script_turn == 2:
            return [
                _make_intent("fire_breath", breath_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_fire_breath", val=breath_val), 1, 0),
                _make_intent("tail_sweep", sweep_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_tail_sweep", val=sweep_val), 0, 1),
                _make_intent("defend", guard_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_defend", val=guard_val), 0, 1),
            ]
        if script_turn == 3:
            return [
                _make_intent("molten_inhale", molten_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_molten_inhale", val=molten_val), 1, 0),
                _make_intent("fireball", fireball_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_fireball", val=fireball_val), 0, 1),
                _make_intent("summon", 1, get_locale_text("i18n_enemy_boss.red_dragon_intent_summon"), 0, 1),
            ]
        return [
            _make_intent("inferno_breath", inferno_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_inferno_breath", val=inferno_val), 1, 0),
            _make_intent("devour_imp", devour_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_devour_imp"), 0, 1),
            _make_intent("tail_sweep", sweep_val, get_locale_text("i18n_enemy_boss.red_dragon_intent_tail_sweep", val=sweep_val), 0, 1),
        ]

    def _strike_player(self, run, engine, enemy, dmg, damage_type, logs, log_key):
        before_len = len(run.node_data.get("battle_logs", []))
        engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type=damage_type)
        after_logs = run.node_data.get("battle_logs", [])
        if len(after_logs) > before_len:
            dmg_msg = after_logs.pop()
            logs.append(get_locale_text(log_key, enemy_name=enemy.name, dmg_msg=dmg_msg))

    def _strike_minions(self, run, engine, enemy, dmg, damage_type, logs, log_key):
        p = run.player
        for mk in list(p.minions.keys()):
            if mk not in p.minions:
                continue
            m_name = p.minions[mk].name
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, f"p{mk}", dmg, source=f"enemy:{enemy.name}", damage_type=damage_type)
            after_logs = run.node_data.get("battle_logs", [])
            if len(after_logs) > before_len:
                dmg_msg = after_logs.pop()
                logs.append(get_locale_text(log_key, minion_name=m_name, dmg_msg=dmg_msg))

    def _summon_imps(self, run, logs, enemy, count):
        from ....models.state import EnemyState, EnemyIntentState
        cfg = ENEMY_CONFIG.get("远古红龙", {}).get("summon_goblin", {})
        imp_name = cfg.get("name") or get_locale_text("i18n_enemy_misc.flame_imp.name")
        for _ in range(max(1, count)):
            run.enemies.append(EnemyState(
                name=imp_name,
                hp=int(cfg.get("hp", 5)),
                max_hp=int(cfg.get("max_hp", 5)),
                shield=0,
                actions=1,
                bonus_actions=0,
                is_summon=True,
                max_actions=1,
                max_bonus_actions=0,
                intents=[EnemyIntentState(
                    type="imp_claw",
                    val=cfg.get("intent_val", 1),
                    desc=get_locale_text("i18n_enemy_boss.goblin_intent_prepare"),
                    cost_a=1,
                    cost_ba=0,
                )],
            ))
        logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_summon_many", enemy_name=enemy.name, count=max(1, count)))

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ....models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        strength = sum(b.stacks for b in enemy.buffs if b.id == "strength")
        val = intent.val + strength
        enemy_key = f"e{run.enemies.index(enemy)+1}" if enemy in run.enemies else ""

        if intent.type == "summon":
            self._summon_imps(run, logs, enemy, intent.val)
        elif intent.type == "defend":
            if enemy_key:
                engine._gain_shield(run, enemy_key, intent.val)
            logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_defend", enemy_name=enemy.name, val=intent.val))
        elif intent.type == "dragon_roar":
            roar_stacks = intent.val or 1
            for target in run.enemies:
                if target.hp <= 0:
                    continue
                engine._add_buff_to(
                    target,
                    "strength",
                    get_locale_text("i18n_enemy_boss.buff_strength"),
                    get_locale_text("i18n_enemy_boss.buff_strength_desc"),
                    roar_stacks,
                )
            logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_dragon_roar", enemy_name=enemy.name))
        elif intent.type == "fire_breath":
            self._strike_player(run, engine, enemy, val, "fire", logs, "i18n_enemy_boss.red_dragon_log_fire_breath")
            engine._add_buff_to(
                run.player,
                "burning",
                get_locale_text("i18n_enemy_boss.buff_burning"),
                get_locale_text("i18n_enemy_boss.buff_burning_desc"),
                2,
            )
        elif intent.type == "tail_sweep":
            self._strike_player(run, engine, enemy, val, "bludgeoning", logs, "i18n_enemy_boss.red_dragon_log_tail_player")
            self._strike_minions(run, engine, enemy, val, "bludgeoning", logs, "i18n_enemy_boss.red_dragon_log_tail_minion")
        elif intent.type == "molten_inhale":
            if enemy_key:
                engine._gain_shield(run, enemy_key, intent.val)
            engine._add_buff_to(
                enemy,
                "molten_charge",
                get_locale_text("i18n_enemy_boss.buff_molten_charge"),
                get_locale_text("i18n_enemy_boss.buff_molten_charge_desc"),
                1,
            )
            logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_molten_inhale", enemy_name=enemy.name, val=intent.val))
        elif intent.type == "fireball":
            self._strike_player(run, engine, enemy, val, "fire", logs, "i18n_enemy_boss.red_dragon_log_fireball")
        elif intent.type == "inferno_breath":
            charge = next((b for b in enemy.buffs if b.id == "molten_charge"), None)
            bonus = BUFF_CONFIG.get("molten_charge", {}).get("bonus_damage", 6) if charge else 0
            if charge:
                enemy.buffs.remove(charge)
            final_val = val + bonus
            self._strike_player(run, engine, enemy, final_val, "fire", logs, "i18n_enemy_boss.red_dragon_log_inferno_breath")
            if bonus:
                logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_inferno_bonus", damage=bonus))
            engine._add_buff_to(
                run.player,
                "burning",
                get_locale_text("i18n_enemy_boss.buff_burning"),
                get_locale_text("i18n_enemy_boss.buff_burning_desc"),
                3,
            )
            self._strike_minions(run, engine, enemy, final_val, "fire", logs, "i18n_enemy_boss.red_dragon_log_inferno_minion")
        elif intent.type == "devour_imp":
            cfg = ENEMY_CONFIG.get("远古红龙", {}).get("summon_goblin", {})
            imp_name = cfg.get("name") or get_locale_text("i18n_enemy_misc.flame_imp.name")
            imp = next((e for e in run.enemies if e.name == imp_name and e.hp > 0), None)
            if imp:
                run.enemies.remove(imp)
                heal_key = f"e{run.enemies.index(enemy)+1}" if enemy in run.enemies else ""
                if heal_key:
                    engine._heal_target(run, heal_key, intent.val)
                engine._add_buff_to(
                    enemy,
                    "strength",
                    get_locale_text("i18n_enemy_boss.buff_strength"),
                    get_locale_text("i18n_enemy_boss.buff_strength_desc"),
                    2,
                )
                logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_devour_imp", enemy_name=enemy.name))
            else:
                if enemy_key:
                    engine._gain_shield(run, enemy_key, 10)
                logs.append(get_locale_text("i18n_enemy_boss.red_dragon_log_devour_empty", enemy_name=enemy.name))
        return "\n".join(logs)


@register_enemy("雷霆领主")
class BossThunderLordTemplate(EnemyTemplate):
    def on_battle_start(self, run, enemy, engine):
        engine._add_buff_to(
            enemy,
            "storm_field_passive",
            get_locale_text("i18n_enemy_boss.buff_storm_field"),
            get_locale_text("i18n_enemy_boss.buff_storm_field_desc"),
            1,
        )
        run.node_data["thunder_lord_turn"] = 1

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        cycle = [
            ("thunder_strike", "i18n_enemy_boss.thunder_lord_intent_strike_8"),
            ("lightning_shield", "i18n_enemy_boss.thunder_lord_intent_shield_12"),
            ("storm_summon", "i18n_enemy_boss.thunder_lord_intent_summon"),
            ("electric_overload", "i18n_enemy_boss.thunder_lord_intent_overload"),
        ]
        turn = int(run.node_data.get("thunder_lord_turn", 1))
        run.node_data["thunder_lord_turn"] = turn + 1
        start = (turn - 1) % len(cycle)
        intents_list = []
        for offset in range(3):
            intent_id, desc_key = cycle[(start + offset) % len(cycle)]
            entry = _intent_entry(self.name, intent_id)
            intents_list.append(_make_intent(
                intent_id,
                entry.get("val", 0),
                get_locale_text(desc_key),
                1 if offset == 0 else 0,
                0 if offset == 0 else 1,
            ))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ....models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        strength = sum(b.stacks for b in enemy.buffs if b.id == "strength")
        val = intent.val + strength

        if intent.type == "thunder_strike":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="thunder")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(
                run.player,
                "shock",
                get_locale_text("i18n_enemy_boss.buff_shock"),
                get_locale_text("i18n_enemy_boss.buff_shock_desc"),
                2,
            )
            logs.append(get_locale_text("i18n_enemy_boss.thunder_lord_log_strike", enemy_name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "lightning_shield":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(
                enemy,
                "lightning_shield",
                get_locale_text("i18n_enemy_boss.buff_lightning_shield"),
                get_locale_text("i18n_enemy_boss.buff_lightning_shield_desc"),
                1,
            )
            logs.append(get_locale_text("i18n_enemy_boss.thunder_lord_log_shield", enemy_name=enemy.name, val=intent.val))
        elif intent.type == "storm_summon":
            from ....models.state import EnemyState, EnemyIntentState
            cfg = ENEMY_CONFIG.get("雷影魔仆", {})
            strike = next((it for it in cfg.get("intents", []) if it.get("id") == "lightning_strike"), {})
            run.enemies.append(EnemyState(
                name=cfg.get("name") or get_locale_text("i18n_enemy_misc.thunder_orb.name"),
                hp=int(cfg.get("hp", 12)),
                max_hp=int(cfg.get("hp", 12)),
                shield=0,
                actions=1,
                bonus_actions=0,
                is_summon=True,
                max_actions=1,
                max_bonus_actions=0,
                intents=[EnemyIntentState(
                    type="lightning_strike",
                    val=strike.get("val", 4),
                    desc=get_locale_text("i18n_enemy_boss.thunder_lord_intent_lightning_strike_4"),
                    cost_a=1,
                    cost_ba=0,
                )],
            ))
            logs.append(get_locale_text("i18n_enemy_boss.thunder_lord_log_summon", enemy_name=enemy.name))
        elif intent.type == "electric_overload":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="lightning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(
                run.player,
                "drain_a",
                get_locale_text("i18n_enemy_boss.buff_drain_a"),
                get_locale_text("i18n_enemy_boss.buff_drain_a_desc"),
                1,
            )
            logs.append(get_locale_text("i18n_enemy_boss.thunder_lord_log_overload", enemy_name=enemy.name, dmg_msg=dmg_msg))
        return "\n".join(logs)
