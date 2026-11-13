from typing import List
from ..base import EnemyTemplate, register_enemy
from ....core.inventory.deck_service import DeckService
from ....data.buff_data import BUFF_CONFIG
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text
from ...buffs import is_debuff

@register_enemy("腐化之心")
class BossCorruptedHeartTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        turn = run.node_data.get("heart_turn", 1)
        cycle = (turn - 1) % 4 + 1
        intents_list = []
        
        if cycle == 1:
            itype, val, desc = "debuff", 0, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_evil_words")
        elif cycle == 2:
            itype, val, desc = "multi_attack", 2, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_blood_bullets")
        elif cycle == 3:
            itype, val, desc = "big_attack", 20, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_pain")
        else:
            itype, val, desc = "strength_buff", 2, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_charge")
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=1, cost_ba=0))
        
        if cycle == 1:
            itype, val, desc = "defend_large", 15, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_shadow_shield_15")
        elif cycle == 2:
            itype, val, desc = "defend_normal", 10, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_shield_10")
        elif cycle == 3:
            itype, val, desc = "defend_normal", 10, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_shield_10")
        else:
            itype, val, desc = "defend_large", 20, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_shadow_shield_20")
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=0, cost_ba=1))
        
        if cycle == 1:
            itype, val, desc = "drain_ba", 1, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_void_song")
        elif cycle == 2:
            itype, val, desc = "heart_strike", 4, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_heart_strike")
        elif cycle == 3:
            itype, val, desc = "gaze_discard", 1, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_gaze")
        else:
            itype, val, desc = "heart_heal", 10, get_locale_text("i18n_enemy_boss.corrupted_heart_intent_heal")
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=0, cost_ba=1))
        
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
            from ....models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        p = run.player
        import random
        
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks

        if intent.type == "debuff":
            DeckService.add_card_to_draw(p, "curse_dazed")
            DeckService.add_card_to_draw(p, "curse_agony")
            random.shuffle(p.draw_pile)
            logs.append(get_locale_text("i18n_enemy_boss.corrupted_heart_log_evil_words", enemy_name=enemy.name))
            
        elif intent.type == "multi_attack":
            dmg = intent.val + strength
            logs.append(get_locale_text("i18n_enemy_boss.corrupted_heart_log_blood_bullets", enemy_name=enemy.name, dmg=dmg))
            for _ in range(8):
                if enemy.hp <= 0:
                    break
                self._perform_attack(run, engine, enemy, dmg, logs)
                
        elif intent.type == "big_attack":
            dmg = intent.val + strength
            self._perform_attack(run, engine, enemy, dmg, logs)
            
        elif intent.type == "strength_buff":
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_boss.buff_strength"), get_locale_text("i18n_enemy_boss.buff_strength_desc_val", val=intent.val), intent.val)
            logs.append(get_locale_text("i18n_enemy_boss.corrupted_heart_log_charge", enemy_name=enemy.name, val=intent.val))
            
        elif intent.type in ("defend_large", "defend_normal"):
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_boss.corrupted_heart_log_shield", enemy_name=enemy.name, val=intent.val))
            
        elif intent.type == "drain_ba":
            engine._add_buff_to(run.player, "drain_ba", get_locale_text("i18n_enemy_boss.buff_drain_ba"), get_locale_text("i18n_enemy_boss.buff_drain_ba_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.corrupted_heart_log_void_song", enemy_name=enemy.name))
            
        elif intent.type == "heart_strike":
            dmg = intent.val + strength
            self._perform_attack(run, engine, enemy, dmg, logs)
            
        elif intent.type == "gaze_discard":
            engine._add_buff_to(run.player, "discard_next_turn", get_locale_text("i18n_enemy_boss.buff_discard_next_turn"), get_locale_text("i18n_enemy_boss.buff_discard_next_turn_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.corrupted_heart_log_gaze", enemy_name=enemy.name))
                
        elif intent.type == "heart_heal":
            if enemy in run.enemies:
                engine._heal_target(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_boss.corrupted_heart_log_heal", enemy_name=enemy.name, val=intent.val))
        return "\n".join(logs)

@register_enemy("Icerainboww")
class BossIcerainbowwTemplate(EnemyTemplate):
    def _config(self):
        return ENEMY_CONFIG.get(self.name, {})

    def _intent_entry(self, intent_id: str):
        for entry in self._config().get("intents", []):
            if entry.get("id") == intent_id:
                return entry
        return {}

    def _intent_val(self, intent_id: str, default: int = 0) -> int:
        return int(self._intent_entry(intent_id).get("val", default))

    def _intent_desc(self, intent_id: str, val: int, cost_ba: int = 0) -> str:
        keys = {
            "icerain_shoot": "i18n_enemy_boss.icerainboww_intent_ice_rain",
            "winter_gaze": "i18n_enemy_boss.icerainboww_intent_winter_gaze",
            "smash_attack": "i18n_enemy_boss.icerainboww_intent_smash",
            "frost_blast": "i18n_enemy_boss.icerainboww_intent_frost_blast",
            "fury": "i18n_enemy_boss.icerainboww_intent_fury",
            "aurora_shield": "i18n_enemy_boss.icerainboww_intent_aurora_shield",
            "ice_refraction": "i18n_enemy_boss.icerainboww_intent_ice_refraction",
            "frost_trap": "i18n_enemy_boss.icerainboww_intent_frost_trap",
            "arctic_whisper": "i18n_enemy_boss.icerainboww_intent_arctic_whisper",
        }
        if intent_id == "aurora_shield" and cost_ba > 0:
            return get_locale_text("i18n_enemy_boss.icerainboww_intent_aurora_shield_ba", val=val)
        key = keys.get(intent_id, "")
        if intent_id == "ice_refraction":
            return get_locale_text(key, val=val)
        return get_locale_text(key)

    def _make_intent(self, intent_id: str, cost_a: int, cost_ba: int):
        from ....models.state import EnemyIntentState
        val = self._intent_val(intent_id)
        return EnemyIntentState(type=intent_id, val=val, desc=self._intent_desc(intent_id, val, cost_ba), cost_a=cost_a, cost_ba=cost_ba)

    def on_battle_start(self, run, enemy, engine):
        engine._add_buff_to(
            enemy,
            "permafrost_aura_passive",
            get_locale_text("i18n_enemy_boss.buff_permafrost_aura"),
            get_locale_text("i18n_enemy_boss.buff_permafrost_aura_desc"),
            BUFF_CONFIG.get("permafrost_aura_passive", {}).get("stacks", 1),
        )

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        turn = int(run.node_data.get("icerainboww_turn", 1))
        run.node_data["icerainboww_turn"] = turn + 1
        cycle = (turn - 1) % 4 + 1
        action_cycle = {
            1: ("icerain_shoot", "fury"),
            2: ("winter_gaze", "aurora_shield"),
            3: ("smash_attack", "icerain_shoot"),
            4: ("frost_blast", "fury"),
        }
        bonus_cycle = {
            1: "ice_refraction",
            2: "frost_trap",
            3: "arctic_whisper",
            4: "aurora_shield",
        }
        intents_list = [self._make_intent(intent_id, 1, 0) for intent_id in action_cycle[cycle]]
        intents_list.append(self._make_intent(bonus_cycle[cycle], 0, 1))
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
        p = run.player
        import random
        
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
 
        val = intent.val + strength
 
        if intent.type == "icerain_shoot":
            if p.minions and random.random() < 0.5:
                target_key = random.choice(list(p.minions.keys()))
                target = p.minions[target_key]
                m_name = target.name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{target_key}", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_ice_rain_minion", enemy_name=enemy.name, minion_name=m_name, dmg_msg=dmg_msg))
            else:
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_ice_rain_player", enemy_name=enemy.name, dmg_msg=dmg_msg))
            engine._add_buff_to(run.player, "drain_a", get_locale_text("i18n_enemy_boss.buff_drain_a"), get_locale_text("i18n_enemy_boss.buff_drain_a_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_ice_rain_drain", enemy_name=enemy.name))
 
        elif intent.type == "fury":
            engine._add_buff_to(enemy, "fury", get_locale_text("i18n_enemy_boss.buff_fury"), get_locale_text("i18n_enemy_boss.buff_fury_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_fury", enemy_name=enemy.name))
 
        elif intent.type == "smash_attack":
            if p.minions and random.random() < 0.5:
                target_key = random.choice(list(p.minions.keys()))
                target = p.minions[target_key]
                m_name = target.name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{target_key}", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_smash_minion", enemy_name=enemy.name, minion_name=m_name, dmg_msg=dmg_msg))
            else:
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_smash_player", enemy_name=enemy.name, dmg_msg=dmg_msg))
            engine._add_buff_to(p, "minor_vulnerable_cold", get_locale_text("i18n_enemy_boss.buff_minor_vulnerable_cold"), get_locale_text("i18n_enemy_boss.buff_minor_vulnerable_cold_desc"), 2)
            logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_smash_vulnerable", enemy_name=enemy.name))
 
        elif intent.type == "aurora_shield":
            neg_buff = next((b for b in enemy.buffs if is_debuff(b.id)), None)
            shield_gain = intent.val
            if neg_buff:
                neg_name = neg_buff.name
                neg_buff.stacks -= 1
                if neg_buff.stacks <= 0:
                    enemy.buffs.remove(neg_buff)
                engine._sync_enemy_intents(enemy)
                logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_aurora_cleanse", enemy_name=enemy.name, shield_gain=shield_gain, neg_name=neg_name))
            elif intent.cost_ba > 0:
                logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_aurora_shield", enemy_name=enemy.name, val=shield_gain))
            else:
                shield_gain += 4
                logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_aurora_bonus", enemy_name=enemy.name, shield_gain=shield_gain))
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", shield_gain)
 
        elif intent.type == "winter_gaze":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            if len(after_logs) > before_len:
                dmg_msg = after_logs.pop()
                logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_winter_gaze", enemy_name=enemy.name, dmg_msg=dmg_msg))
            engine._add_buff_to(p, "minor_vulnerable_cold", get_locale_text("i18n_enemy_boss.buff_minor_vulnerable_cold"), get_locale_text("i18n_enemy_boss.buff_minor_vulnerable_cold_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_winter_gaze_vulnerable", enemy_name=enemy.name))
 
        elif intent.type == "frost_blast":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="cold")
            after_logs = run.node_data.get("battle_logs", [])
            if len(after_logs) > before_len:
                dmg_msg = after_logs.pop()
                logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_frost_blast_player", enemy_name=enemy.name, dmg_msg=dmg_msg))
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_frost_blast_minion", minion_name=m_name, dmg_msg=dmg_msg))

        elif intent.type == "ice_refraction":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_ice_refraction", enemy_name=enemy.name, val=intent.val))

        elif intent.type == "frost_trap":
            engine._add_buff_to(p, "drain_ba", get_locale_text("i18n_enemy_boss.buff_drain_ba"), get_locale_text("i18n_enemy_boss.buff_drain_ba_desc"), intent.val)
            logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_frost_trap", enemy_name=enemy.name))

        elif intent.type == "arctic_whisper":
            run.node_data["draw_penalty_next_turn"] = run.node_data.get("draw_penalty_next_turn", 0) + intent.val
            logs.append(get_locale_text("i18n_enemy_boss.icerainboww_log_arctic_whisper", enemy_name=enemy.name))
        return "\n".join(logs)
