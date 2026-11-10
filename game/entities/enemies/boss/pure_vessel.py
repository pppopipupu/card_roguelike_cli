from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.buff_data import BUFF_CONFIG
from ....data.locale_data import get_locale_text


@register_enemy("纯粹容器")
class BossPureVesselTemplate(EnemyTemplate):
    def _config(self):
        return ENEMY_CONFIG.get(self.name.split(" ")[0], {})

    def _intent_entry(self, intent_id: str):
        for entry in self._config().get("intents", []):
            if entry.get("id") == intent_id:
                return entry
        return {}

    def _build_intent(self, intent_id: str, cost_a: int, cost_ba: int):
        from ....models.state import EnemyIntentState
        val = self._intent_entry(intent_id).get("val", 0)
        desc = get_locale_text(f"i18n_enemy_boss.pure_vessel_intent_{intent_id}", val=val)
        return EnemyIntentState(type=intent_id, val=val, desc=desc, cost_a=cost_a, cost_ba=cost_ba)

    def _enemy_grid(self, run, enemy) -> str:
        for index, candidate in enumerate(run.enemies, 1):
            if candidate is enemy:
                return f"e{index}"
        return ""

    def _strength_bonus(self, enemy) -> int:
        total = 0
        for buff in enemy.buffs:
            if buff.id == "strength":
                total += buff.stacks
        return total

    def _roll_damage(self, run, engine, enemy, target: str, dmg: int, damage_type: str) -> str:
        before_len = len(run.node_data.get("battle_logs", []))
        engine._damage_target(run, target, dmg, source=f"enemy:{enemy.name}", damage_type=damage_type)
        after_logs = run.node_data.get("battle_logs", [])
        if len(after_logs) > before_len:
            return after_logs.pop()
        return ""

    def _damage_player(self, run, engine, enemy, dmg: int, damage_type: str) -> str:
        return self._roll_damage(run, engine, enemy, "p0", dmg, damage_type)

    def on_battle_start(self, run, enemy, engine):
        engine._add_buff_to(
            enemy,
            "pure_vessel_body_passive",
            get_locale_text("i18n_enemy_boss.buff_pure_vessel_body"),
            get_locale_text("i18n_enemy_boss.buff_pure_vessel_body_desc"),
            1,
        )
        engine._add_buff_to(
            enemy,
            "pure_parry_stance",
            get_locale_text("i18n_enemy_boss.buff_pure_parry_stance"),
            get_locale_text("i18n_enemy_boss.buff_pure_parry_stance_desc"),
            1,
        )

    def on_damage_take(self, event, enemy, engine):
        run = event.run
        grid = self._enemy_grid(run, enemy)
        target = getattr(event, "target", "")
        if target and grid and target != grid:
            return
        cfg = self._config()
        if enemy.hp * cfg.get("half_hp_divisor", 2) > enemy.max_hp:
            return
        awake = run.node_data.setdefault("pure_vessel_awake", {})
        if awake.get(enemy.name):
            return
        awake[enemy.name] = True
        engine._gain_shield(run, grid, cfg.get("awaken_shield", 15))
        engine._add_buff_to(
            enemy,
            "strength",
            get_locale_text("i18n_enemy_boss.buff_strength"),
            get_locale_text("i18n_enemy_boss.buff_strength_desc"),
            cfg.get("awaken_strength", 1),
        )
        engine._log_event(run, get_locale_text("i18n_enemy_boss.pure_vessel_log_awaken", enemy_name=enemy.name))
        engine._log_event(run, get_locale_text("i18n_enemy_boss.pure_vessel_log_awaken_quote"))

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        cfg = self._config()
        turn = run.node_data.get("pure_vessel_turn", 1)
        cycle = (turn - 1) % 4 + 1
        run.node_data["pure_vessel_turn"] = cycle % 4 + 1
        if cycle == 1:
            action_intents = ["triple_slash", "shining_lunge"]
            bonus_intent = "nail_parry"
        elif cycle == 2:
            action_intents = ["soul_daggers", "desolate_dive"]
            bonus_intent = "vessel_guard"
        elif cycle == 3:
            action_intents = ["focus_channel", "pale_wave"]
            bonus_intent = "nail_parry"
        else:
            second_action = (
                "shining_lunge"
                if enemy.hp * cfg.get("half_hp_divisor", 2) > enemy.max_hp
                else "void_tendrils"
            )
            action_intents = ["focus_bloom", second_action]
            bonus_intent = "abyss_gaze"
        intents_list = [self._build_intent(intent_id, 1, 0) for intent_id in action_intents]
        intents_list.append(self._build_intent(bonus_intent, 0, 1))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            from ....models.state import EnemyIntentState
            logs = []
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0,
            )
        p = run.player
        cfg = self._config()
        buff_cfg = BUFF_CONFIG.get("pure_focus_charge", {})
        strength = self._strength_bonus(enemy)
        val = intent.val + strength
        grid = self._enemy_grid(run, enemy)

        if intent.type == "triple_slash":
            dmg_msgs = []
            for _ in range(cfg.get("triple_slash_hits", 3)):
                dmg_msgs.append(self._damage_player(run, engine, enemy, val, "slashing"))
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_triple_slash",
                    enemy_name=enemy.name,
                    dmg_msg="\n".join(msg for msg in dmg_msgs if msg),
                )
            )
        elif intent.type == "shining_lunge":
            dmg_msg = self._damage_player(run, engine, enemy, val, "piercing")
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_shining_lunge",
                    enemy_name=enemy.name,
                    dmg_msg=dmg_msg,
                )
            )
        elif intent.type == "nail_parry":
            if grid:
                engine._gain_shield(run, grid, intent.val)
            engine._add_buff_to(
                enemy,
                "pure_parry_stance",
                get_locale_text("i18n_enemy_boss.buff_pure_parry_stance"),
                get_locale_text("i18n_enemy_boss.buff_pure_parry_stance_desc"),
                1,
            )
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_nail_parry",
                    enemy_name=enemy.name,
                    val=intent.val,
                )
            )
        elif intent.type == "soul_daggers":
            dmg_msg = self._damage_player(run, engine, enemy, val, "force")
            engine._add_buff_to(
                p,
                "drain_ba",
                get_locale_text("i18n_enemy_boss.buff_drain_ba"),
                get_locale_text("i18n_enemy_boss.buff_drain_ba_desc"),
                1,
            )
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_soul_daggers_player",
                    enemy_name=enemy.name,
                    dmg_msg=dmg_msg,
                )
            )
            for grid_key in list(p.minions.keys()):
                if grid_key not in p.minions:
                    continue
                minion_name = p.minions[grid_key].name
                minion_msg = self._roll_damage(run, engine, enemy, f"p{grid_key}", val, "force")
                logs.append(
                    get_locale_text(
                        "i18n_enemy_boss.pure_vessel_log_soul_daggers_minion",
                        enemy_name=enemy.name,
                        minion_name=minion_name,
                        dmg_msg=minion_msg,
                    )
                )
        elif intent.type == "desolate_dive":
            strip = min(cfg.get("desolate_dive_shield_strip", 5), p.shield)
            if strip > 0:
                p.shield -= strip
            dmg_msg = self._damage_player(run, engine, enemy, val, "radiant")
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_desolate_dive",
                    enemy_name=enemy.name,
                    dmg_msg=dmg_msg,
                )
            )
        elif intent.type == "vessel_guard":
            if grid:
                engine._gain_shield(run, grid, intent.val)
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_vessel_guard",
                    enemy_name=enemy.name,
                    val=intent.val,
                )
            )
        elif intent.type == "focus_channel":
            if grid:
                engine._gain_shield(run, grid, intent.val)
            engine._add_buff_to(
                enemy,
                "pure_focus_charge",
                get_locale_text("i18n_enemy_boss.buff_pure_focus_charge"),
                get_locale_text("i18n_enemy_boss.buff_pure_focus_charge_desc"),
                1,
            )
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_focus_channel",
                    enemy_name=enemy.name,
                    val=intent.val,
                )
            )
        elif intent.type == "pale_wave":
            dmg_msg = self._damage_player(run, engine, enemy, val, "radiant")
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_pale_wave",
                    enemy_name=enemy.name,
                    dmg_msg=dmg_msg,
                )
            )
        elif intent.type == "focus_bloom":
            dmg_msg = self._damage_player(run, engine, enemy, val, "radiant")
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_focus_bloom",
                    enemy_name=enemy.name,
                    dmg_msg=dmg_msg,
                )
            )
            for grid_key in list(p.minions.keys()):
                if grid_key not in p.minions:
                    continue
                minion_msg = self._roll_damage(run, engine, enemy, f"p{grid_key}", val, "radiant")
                logs.append(
                    get_locale_text(
                        "i18n_enemy_boss.pure_vessel_log_focus_bloom",
                        enemy_name=enemy.name,
                        dmg_msg=minion_msg,
                    )
                )
            charge = next(
                (buff for buff in enemy.buffs if buff.id == "pure_focus_charge" and buff.stacks > 0),
                None,
            )
            if charge:
                enemy.buffs.remove(charge)
                heal_val = buff_cfg.get("heal_val", 12)
                strength_val = buff_cfg.get("strength_val", 2)
                if grid:
                    engine._heal_target(run, grid, heal_val)
                engine._add_buff_to(
                    enemy,
                    "strength",
                    get_locale_text("i18n_enemy_boss.buff_strength"),
                    get_locale_text("i18n_enemy_boss.buff_strength_desc"),
                    strength_val,
                )
                logs.append(
                    get_locale_text(
                        "i18n_enemy_boss.pure_vessel_log_focus_bloom_bonus",
                        enemy_name=enemy.name,
                        heal=heal_val,
                    )
                )
        elif intent.type == "void_tendrils":
            dmg_msg = self._damage_player(run, engine, enemy, val, "necrotic")
            engine._add_buff_to(
                p,
                "drain_a",
                get_locale_text("i18n_enemy_boss.buff_drain_a"),
                get_locale_text("i18n_enemy_boss.buff_drain_a_desc"),
                1,
            )
            engine._add_buff_to(
                p,
                "void_weakness",
                get_locale_text("i18n_enemy_boss.buff_void_weakness"),
                get_locale_text("i18n_enemy_boss.buff_void_weakness_desc"),
                1,
            )
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_void_tendrils",
                    enemy_name=enemy.name,
                    dmg_msg=dmg_msg,
                )
            )
        elif intent.type == "abyss_gaze":
            engine._add_buff_to(
                p,
                "minor_vulnerable",
                get_locale_text("i18n_enemy_elite_a.common.minor_vulnerable_name"),
                get_locale_text("i18n_enemy_elite_a.common.minor_vulnerable_desc"),
                1,
            )
            logs.append(
                get_locale_text(
                    "i18n_enemy_boss.pure_vessel_log_abyss_gaze",
                    enemy_name=enemy.name,
                )
            )
        return "\n".join(logs)
