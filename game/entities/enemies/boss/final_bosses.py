from typing import List
from ..base import EnemyTemplate, register_enemy
from ....core.deck_service import DeckService
from ....data.locale_data import get_locale_text

@register_enemy("虚空之门·尤格-索托斯")
class BossYogSothothTemplate(EnemyTemplate):
    def on_turn_start(self, event, enemy, engine):
        if not event.is_player:
            return
        run = event.run
        p = run.player
        run.node_data["merchant_collection_free_cards"] = []
        if run.node_data.get("yog_sothoth_phase", 1) == 4:
            run.node_data["yog_sothoth_turn"] = run.node_data.get("yog_sothoth_turn", 0) + 1
            import random
            npc_options = [
                ("Guide_Elder", "elder_guidance", get_locale_text("i18n_enemy_boss.yog_npc_quote_elder")),
                ("Blacksmith_Ironclad", "ironclad_rampart", get_locale_text("i18n_enemy_boss.yog_npc_quote_blacksmith")),
                ("Bartender_Jack", "jack_brew", get_locale_text("i18n_enemy_boss.yog_npc_quote_bartender")),
                ("Market_Merchant", "merchant_collection", get_locale_text("i18n_enemy_boss.yog_npc_quote_merchant")),
                ("Lost_Bard", "bard_epic", get_locale_text("i18n_enemy_boss.yog_npc_quote_bard"))
            ]
            chosen_npc = random.choice(npc_options)
            npc_id, card_id, quote = chosen_npc
            from ....models.state import CardState
            npc_card_state = CardState(id=card_id, upgraded=True)
            p.hand.append(npc_card_state)
            card_name = get_locale_text("i18n_enemy_boss.help_card_default")
            if card_id == "elder_guidance":
                card_name = get_locale_text("i18n_enemy_boss.help_card_elder_guidance")
            elif card_id == "ironclad_rampart":
                card_name = get_locale_text("i18n_enemy_boss.help_card_ironclad_rampart")
            elif card_id == "jack_brew":
                card_name = get_locale_text("i18n_enemy_boss.help_card_jack_brew")
            elif card_id == "merchant_collection":
                card_name = get_locale_text("i18n_enemy_boss.help_card_merchant_collection")
            elif card_id == "bard_epic":
                card_name = get_locale_text("i18n_enemy_boss.help_card_bard_epic")
            engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_help_card", quote=quote, card_name=card_name))

    def on_card_play(self, event, enemy, engine):
        run = event.run
        p = run.player
        card = event.card
        if run.node_data.get("intangible_whisper_active"):
            run.node_data.pop("intangible_whisper_active", None)
            import random
            if card.type == "spell" and getattr(card, "base_dmg", 0) > 0:
                my_targets = ["p0"] + [f"p{k}" for k in p.minions.keys()]
                event.target = random.choice(my_targets)
                engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_whisper_redirect_spell", card_name=card.name, target_name=engine._get_target_name(run, event.target)))
            elif card.type == "spell" and getattr(card, "heal_amount", 0) > 0:
                if run.enemies:
                    event.target = f"e{random.randint(1, len(run.enemies))}"
                    engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_whisper_redirect_heal", target_name=engine._get_target_name(run, event.target)))
            elif card.type == "attack" or card.id.startswith("warrior_"):
                my_targets = ["p0"] + [f"p{k}" for k in p.minions.keys()]
                event.target = random.choice(my_targets)
                engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_whisper_redirect_attack", card_name=card.name, target_name=engine._get_target_name(run, event.target)))

        if card.id in run.node_data.get("merchant_collection_free_cards", []):
            event.cost_a = 0
            event.cost_ba = 0

        if run.node_data.get("yog_sothoth_phase", 1) == 4 and card.type == "spell":
            import random
            if random.random() < 0.30:
                event.cancel()
                p.actions = max(0, p.actions - event.cost_a)
                p.bonus_actions = max(0, p.bonus_actions - event.cost_ba)
                hand_idx = run.node_data.get("current_playing_card_hand_idx", 0)
                if 0 <= hand_idx < len(p.hand):
                    c_state = p.hand.pop(hand_idx)
                else:
                    c_state = None
                if c_state:
                    p.exhaust_pile.append(c_state)
                    from ....models.events import CardExhaustEvent
                    exhaust_evt = CardExhaustEvent(run, c_state, "void_distortion_cancel")
                    engine.event_bus.dispatch(exhaust_evt)
                engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_space_disorder", card_name=card.name))
                run.node_data[run.turn_key("cards_played_this_turn", run.player)] = run.node_data.get(run.turn_key("cards_played_this_turn", run.player), 0) + 1
                engine.save_manager.save_save(run.user_id, run)

    def on_turn_end(self, event, enemy, engine):
        if not event.is_player:
            return
        run = event.run
        p = run.player
        if run.node_data.get("yog_sothoth_phase", 1) == 4 and len(p.hand) == 0:
            engine.combat_resolver.damage_target(run, "p0", 10, source="yog_sothoth_passive", damage_type="true")
            engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_no_hand_damage"))
        for cs in p.hand:
            if cs.id == "curse_intangible_whisper":
                run.node_data["intangible_whisper_active"] = True

    def on_enemy_before_death(self, run, enemy, event, engine):
        if enemy.name == "虚空之门·尤格-索托斯":
            event.cancel()
            enemy.hp = 1
            enemy.shield = 0
            if "pending_transitions" not in run.node_data:
                run.node_data["pending_transitions"] = {}
            run.node_data["pending_transitions"][enemy.name] = 2
            from ....models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_boss.buff_phase_transition"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_phase_transition_desc")))
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc=get_locale_text("i18n_enemy_boss.yog_intent_phase_transition_2"),
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_death_phase1"))
        elif enemy.name == "【觉醒】虚空之门·尤格-索托斯":
            event.cancel()
            enemy.hp = 1
            enemy.shield = 0
            if "pending_transitions" not in run.node_data:
                run.node_data["pending_transitions"] = {}
            run.node_data["pending_transitions"][enemy.name] = 3
            from ....models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_boss.buff_phase_transition"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_phase_transition_desc")))
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc=get_locale_text("i18n_enemy_boss.yog_intent_phase_transition_3"),
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_death_phase2"))
        elif enemy.name == "【终焉】虚空之门·尤格-索托斯":
            event.cancel()
            enemy.hp = 1
            enemy.shield = 0
            if "pending_transitions" not in run.node_data:
                run.node_data["pending_transitions"] = {}
            run.node_data["pending_transitions"][enemy.name] = 4
            from ....models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_boss.buff_phase_transition"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_phase_transition_desc")))
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc=get_locale_text("i18n_enemy_boss.yog_intent_phase_transition_4"),
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_death_phase3"))

    def apply_phase_transition(self, run, enemy, target_phase: int, engine, logs: list):
        from ....models.state import BuffState
        if target_phase == 2:
            enemy.name = "【觉醒】虚空之门·尤格-索托斯"
            enemy.max_hp = 260
            enemy.hp = 260
            enemy.shield = 30
            enemy.actions = 2
            enemy.bonus_actions = 2
            enemy.max_actions = 2
            enemy.max_bonus_actions = 2
            enemy.buffs.clear()
            enemy.buffs.append(BuffState(id="end_gate_passive", name=get_locale_text("i18n_enemy_boss.buff_end_gate"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_end_gate_desc")))
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_boss.buff_phase_transition"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_phase_transition_desc")))
            run.node_data["yog_sothoth_phase"] = 2
            run.node_data["yog_sothoth_turn"] = 0
            run.node_data["is_void_corrupted"] = True
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_awaken"))
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_awaken_quote", player_name=run.player.name))
        elif target_phase == 3:
            enemy.name = "【终焉】虚空之门·尤格-索托斯"
            enemy.max_hp = 300
            enemy.hp = 300
            enemy.shield = 50
            enemy.actions = 3
            enemy.bonus_actions = 2
            enemy.max_actions = 3
            enemy.max_bonus_actions = 2
            enemy.buffs.clear()
            from ....models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="doomsday_gate_passive", name=get_locale_text("i18n_enemy_boss.buff_doomsday_gate"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_doomsday_gate_desc")))
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_boss.buff_phase_transition"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_phase_transition_desc")))
            run.node_data["yog_sothoth_phase"] = 3
            run.node_data["yog_sothoth_turn"] = 0
            run.node_data["is_void_corrupted"] = True
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc=get_locale_text("i18n_enemy_boss.yog_intent_phase_transition_3"),
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_doomsday"))
            engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_doomsday_quote", player_name=run.player.name))
        elif target_phase == 4:
            enemy.name = "【万物归一】虚空之门·尤格-索托斯"
            enemy.max_hp = 2147483647
            enemy.hp = 2147483647
            enemy.shield = 80
            enemy.actions = 3
            enemy.bonus_actions = 3
            enemy.max_actions = 3
            enemy.max_bonus_actions = 3
            enemy.buffs.clear()
            from ....models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="transcendence_passive", name=get_locale_text("i18n_enemy_boss.buff_transcendence"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_transcendence_desc")))
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=get_locale_text("i18n_enemy_boss.buff_phase_transition"), stacks=1, desc=get_locale_text("i18n_enemy_boss.buff_phase_transition_desc")))
            run.node_data["yog_sothoth_phase"] = 4
            run.node_data["yog_sothoth_turn"] = 0
            run.node_data["is_void_corrupted"] = True
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc=get_locale_text("i18n_enemy_boss.yog_intent_phase_transition_4"),
                cost_a=1,
                cost_ba=0
            ))
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_transcendence"))
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_transcendence_quote"))
            engine.enemy_controller.sync_enemy_intents(enemy)
            stats = engine.save_manager.load_stats(run.user_id)
            challenge_count = getattr(stats, "yog_sothoth_challenge_count", 1)
            engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_fatal_warning"))
            if challenge_count == 1:
                engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_challenge_quote_first"))
            else:
                engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_challenge_quote_repeat"))
            engine._log_event(run, get_locale_text("i18n_enemy_boss.yog_log_allies_arrive"))


    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        phase = run.node_data.get("yog_sothoth_phase", 1)
        turn = run.node_data.get("yog_sothoth_turn", 1)
        run.node_data["yog_sothoth_turn"] = turn + 1
        cycle = (turn - 1) % 4 + 1
        intents_list = []
        if phase == 1:
            if cycle == 1:
                intents_list.append(EnemyIntentState(type="gate_gaze", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_gate_gaze_12"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_corruption", val=8, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_corruption"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_exhaust", val=1, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_exhaust"), cost_a=0, cost_ba=1))
            elif cycle == 2:
                intents_list.append(EnemyIntentState(type="void_storm", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_storm_10"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="gravity_press", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_gravity_press_typo"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="decay_whisper", val=2, desc=get_locale_text("i18n_enemy_boss.yog_intent_decay_whisper"), cost_a=0, cost_ba=1))
            elif cycle == 3:
                intents_list.append(EnemyIntentState(type="ancient_resonance", val=20, desc=get_locale_text("i18n_enemy_boss.yog_intent_ancient_resonance"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_storm", val=8, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_storm_8"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="mana_block", val=1, desc=get_locale_text("i18n_enemy_boss.yog_intent_mana_block_1"), cost_a=0, cost_ba=1))
            else:
                intents_list.append(EnemyIntentState(type="gate_gaze", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_gate_gaze_12"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="gravity_press", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_gravity_press"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="dimensional_distortion", val=15, desc=get_locale_text("i18n_enemy_boss.yog_intent_dimensional_distortion"), cost_a=0, cost_ba=1))
        elif phase == 2:
            if cycle == 1:
                intents_list.append(EnemyIntentState(type="time_collapse", val=14, desc=get_locale_text("i18n_enemy_boss.yog_intent_time_collapse_14"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="chaos_beam", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_chaos_beam_10"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=20, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_shield_cleanse"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="abyss_exhaust", val=1, desc=get_locale_text("i18n_enemy_boss.yog_intent_abyss_exhaust"), cost_a=0, cost_ba=1))
            elif cycle == 2:
                intents_list.append(EnemyIntentState(type="all_gates_open", val=20, desc=get_locale_text("i18n_enemy_boss.yog_intent_all_gates_open"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="abyss_gaze", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_abyss_gaze"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=2, desc=get_locale_text("i18n_enemy_boss.yog_intent_strength_infuse_2"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="end_whisper", val=6, desc=get_locale_text("i18n_enemy_boss.yog_intent_end_whisper_6"), cost_a=0, cost_ba=1))
            elif cycle == 3:
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_doomsday_tide_12"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="time_collapse", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_time_collapse_10"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="mana_block", val=1, desc=get_locale_text("i18n_enemy_boss.yog_intent_mana_block_1"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="reality_shatter", val=8, desc=get_locale_text("i18n_enemy_boss.yog_intent_reality_shatter_8"), cost_a=0, cost_ba=1))
            else:
                intents_list.append(EnemyIntentState(type="chaos_beam", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_chaos_beam_12"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_doomsday_tide_10"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=2, desc=get_locale_text("i18n_enemy_boss.yog_intent_strength_infuse_2"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=20, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_shield_cleanse"), cost_a=0, cost_ba=1))
        elif phase == 3:
            if cycle == 1:
                intents_list.append(EnemyIntentState(type="time_collapse", val=14, desc=get_locale_text("i18n_enemy_boss.yog_intent_time_collapse_14"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_doomsday_tide_12"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="chaos_beam", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_chaos_beam_10"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=20, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_shield_cleanse"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="abyss_exhaust", val=1, desc=get_locale_text("i18n_enemy_boss.yog_intent_abyss_exhaust"), cost_a=0, cost_ba=1))
            elif cycle == 2:
                intents_list.append(EnemyIntentState(type="all_gates_open", val=20, desc=get_locale_text("i18n_enemy_boss.yog_intent_all_gates_open"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_doomsday_tide_12_typo"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="abyss_gaze", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_abyss_gaze"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=2, desc=get_locale_text("i18n_enemy_boss.yog_intent_strength_infuse_2"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="end_whisper", val=6, desc=get_locale_text("i18n_enemy_boss.yog_intent_end_whisper_6"), cost_a=0, cost_ba=1))
            elif cycle == 3:
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_doomsday_tide_12"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="time_collapse", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_time_collapse_10"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="chaos_beam", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_chaos_beam_10"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="mana_block", val=1, desc=get_locale_text("i18n_enemy_boss.yog_intent_mana_block_1"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="reality_shatter", val=8, desc=get_locale_text("i18n_enemy_boss.yog_intent_reality_shatter_8"), cost_a=0, cost_ba=1))
            else:
                intents_list.append(EnemyIntentState(type="all_gates_open", val=20, desc=get_locale_text("i18n_enemy_boss.yog_intent_all_gates_open"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="chaos_beam", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_chaos_beam_12"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=10, desc=get_locale_text("i18n_enemy_boss.yog_intent_doomsday_tide_10"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=2, desc=get_locale_text("i18n_enemy_boss.yog_intent_strength_infuse_2"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=20, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_shield_cleanse"), cost_a=0, cost_ba=1))
        else:
            if cycle == 1:
                intents_list.append(EnemyIntentState(type="meta_code_injection", val=15, desc=get_locale_text("i18n_enemy_boss.yog_intent_meta_code_injection_full"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_storm", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_storm_12"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="input_hijack", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_input_hijack"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=30, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_shield_cleanse_30"), cost_a=0, cost_ba=1))
            elif cycle == 2:
                intents_list.append(EnemyIntentState(type="data_overflow", val=15, desc=get_locale_text("i18n_enemy_boss.yog_intent_data_overflow_full"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=15, desc=get_locale_text("i18n_enemy_boss.yog_intent_doomsday_tide_15"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=3, desc=get_locale_text("i18n_enemy_boss.yog_intent_strength_infuse_3"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="end_whisper", val=8, desc=get_locale_text("i18n_enemy_boss.yog_intent_end_whisper_8"), cost_a=0, cost_ba=1))
            elif cycle == 3:
                intents_list.append(EnemyIntentState(type="save_erase", val=0, desc=get_locale_text("i18n_enemy_boss.yog_intent_save_erase"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="time_collapse", val=15, desc=get_locale_text("i18n_enemy_boss.yog_intent_time_collapse_15"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="mana_block", val=2, desc=get_locale_text("i18n_enemy_boss.yog_intent_mana_block_2"), cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="reality_shatter", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_reality_shatter_12"), cost_a=0, cost_ba=1))
            else:
                intents_list.append(EnemyIntentState(type="meta_code_injection", val=15, desc=get_locale_text("i18n_enemy_boss.yog_intent_meta_code_injection"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="data_overflow", val=15, desc=get_locale_text("i18n_enemy_boss.yog_intent_data_overflow"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="input_hijack", val=12, desc=get_locale_text("i18n_enemy_boss.yog_intent_input_hijack"), cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=30, desc=get_locale_text("i18n_enemy_boss.yog_intent_void_shield_30"), cost_a=0, cost_ba=1))
        return intents_list

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
        from ...buffs import is_debuff

        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength

        if intent.type == "gate_gaze":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_gate_gaze", enemy_name=enemy.name, dmg_msg=dmg_msg))
            if p.minions:
                target_key = random.choice(list(p.minions.keys()))
                m_name = p.minions[target_key].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{target_key}", 8, source=f"enemy:{enemy.name}", damage_type="force")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_gate_gaze_minion", minion_name=m_name, dmg_msg=dmg_msg_m))
            engine._add_buff_to(run.player, "tactical_focus", get_locale_text("i18n_enemy_boss.buff_tactical_focus"), get_locale_text("i18n_enemy_boss.buff_tactical_focus_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_gate_gaze_no_draw", enemy_name=enemy.name))

        elif intent.type == "void_storm":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_void_storm", enemy_name=enemy.name, dmg_msg=dmg_msg))
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", val, source=f"enemy:{enemy.name}", damage_type="force")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_void_storm_minion", minion_name=m_name, dmg_msg=dmg_msg_m))

        elif intent.type == "ancient_resonance":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_boss.buff_strength"), get_locale_text("i18n_enemy_boss.buff_strength_desc"), 2)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_ancient_resonance", enemy_name=enemy.name, val=intent.val))

        elif intent.type == "void_corruption":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="acid")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "void_weakness", get_locale_text("i18n_enemy_boss.buff_void_weakness"), get_locale_text("i18n_enemy_boss.buff_void_weakness_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_void_corruption", enemy_name=enemy.name, dmg_msg=dmg_msg))
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_void_weakness"))

        elif intent.type == "gravity_press":
            lost_shield_msg = ""
            if p.shield > 0:
                lost_amount = min(5, p.shield)
                p.shield -= lost_amount
                lost_shield_msg = get_locale_text("i18n_enemy_boss.yog_log_gravity_press_shield", amount=lost_amount)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_gravity_press", enemy_name=enemy.name, dmg_msg=dmg_msg, lost_shield_msg=lost_shield_msg))
            if p.minions:
                target_key = random.choice(list(p.minions.keys()))
                m_name = p.minions[target_key].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{target_key}", 6, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_gravity_press_minion", minion_name=m_name, dmg_msg=dmg_msg_m))

        elif intent.type in ("void_exhaust", "abyss_exhaust"):
            engine._add_buff_to(run.player, "void_exhaustion", get_locale_text("i18n_enemy_boss.buff_void_exhaustion"), get_locale_text("i18n_enemy_boss.buff_void_exhaustion_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_void_exhaust", enemy_name=enemy.name))

        elif intent.type == "decay_whisper":
            engine._add_buff_to(run.player, "void_weakness", get_locale_text("i18n_enemy_boss.buff_void_weakness"), get_locale_text("i18n_enemy_boss.buff_void_weakness_desc"), 2)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_decay_whisper", enemy_name=enemy.name))

        elif intent.type == "mana_block":
            engine._add_buff_to(run.player, "mana_leak", get_locale_text("i18n_enemy_boss.buff_mana_leak"), get_locale_text("i18n_enemy_boss.buff_mana_leak_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_mana_block", enemy_name=enemy.name))

        elif intent.type == "dimensional_distortion":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_dimensional_distortion", enemy_name=enemy.name, val=intent.val))

        elif intent.type == "time_collapse":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "drain_a", get_locale_text("i18n_enemy_boss.buff_drain_a"), get_locale_text("i18n_enemy_boss.buff_drain_a_desc"), 1)
            engine._add_buff_to(run.player, "drain_ba", get_locale_text("i18n_enemy_boss.buff_drain_ba"), get_locale_text("i18n_enemy_boss.buff_drain_ba_desc"), 1)
            DeckService.add_card_to_draw(p, "curse_dimensional_tear")
            DeckService.add_card_to_draw(p, "curse_dimensional_tear")
            random.shuffle(p.draw_pile)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_time_collapse", enemy_name=enemy.name, dmg_msg=dmg_msg))

        elif intent.type == "chaos_beam":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="radiant")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_chaos_beam", enemy_name=enemy.name, dmg_msg=dmg_msg))
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", 6, source=f"enemy:{enemy.name}", damage_type="radiant")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_chaos_beam_minion", minion_name=m_name, dmg_msg=dmg_msg_m))

        elif intent.type == "void_shield_large":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", intent.val)
            neg_buff = next((b for b in enemy.buffs if is_debuff(b.id)), None)
            if neg_buff:
                neg_name = neg_buff.name
                neg_buff.stacks -= 1
                if neg_buff.stacks <= 0:
                    enemy.buffs.remove(neg_buff)
                engine._sync_enemy_intents(enemy)
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_void_shield_cleanse", enemy_name=enemy.name, val=intent.val, neg_name=neg_name))
            else:
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_void_shield", enemy_name=enemy.name, val=intent.val))

        elif intent.type == "all_gates_open":
            empty_slots = 6 - len(run.enemies)
            summon_count = min(2, empty_slots)
            from ....models.state import EnemyState, EnemyIntentState
            for _ in range(summon_count):
                new_minion = EnemyState(
                    name="虚空潜伏者",
                    hp=20,
                    max_hp=20,
                    shield=0,
                    actions=1,
                    bonus_actions=0,
                    is_summon=True,
                    max_actions=1,
                    max_bonus_actions=0,
                    intents=[EnemyIntentState(
                        type="void_strike",
                        val=6,
                        desc=get_locale_text("i18n_enemy_boss.void_lurker_intent_void_strike"),
                        cost_a=1,
                        cost_ba=0
                    )]
                )
                run.enemies.append(new_minion)
            for e in run.enemies:
                engine._add_buff_to(e, "strength", get_locale_text("i18n_enemy_boss.buff_strength"), get_locale_text("i18n_enemy_boss.buff_strength_desc"), 2)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_all_gates_open", enemy_name=enemy.name, summon_count=summon_count))
            if summon_count < 2:
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", 20, source=f"enemy:{enemy.name}", damage_type="psychic")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_all_gates_blocked", dmg_msg=dmg_msg))

        elif intent.type == "abyss_gaze":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            run.node_data["draw_penalty_next_turn"] = 2
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_abyss_gaze", enemy_name=enemy.name, dmg_msg=dmg_msg))

        elif intent.type == "strength_infuse":
            for e in run.enemies:
                engine._add_buff_to(e, "strength", get_locale_text("i18n_enemy_boss.buff_strength"), get_locale_text("i18n_enemy_boss.buff_strength_desc"), 2)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_strength_infuse", enemy_name=enemy.name))

        elif intent.type == "end_whisper":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "discard_next_turn", get_locale_text("i18n_enemy_boss.buff_discard_next_turn"), get_locale_text("i18n_enemy_boss.buff_discard_next_turn_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_end_whisper", enemy_name=enemy.name, dmg_msg=dmg_msg))

        elif intent.type == "doomsday_tide":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="true")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_doomsday_tide", enemy_name=enemy.name, dmg_msg=dmg_msg))
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", val, source=f"enemy:{enemy.name}", damage_type="true")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_doomsday_tide_minion", minion_name=m_name, dmg_msg=dmg_msg_m))
            if enemy in run.enemies:
                engine._heal_target(run, f"e{run.enemies.index(enemy)+1}", 15)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_doomsday_tide_heal", enemy_name=enemy.name))

        elif intent.type == "reality_shatter":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="true")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_reality_shatter", enemy_name=enemy.name, dmg_msg=dmg_msg))

        elif intent.type == "meta_code_injection":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_meta_code_injection", enemy_name=enemy.name, dmg_msg=dmg_msg))
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_traceback"))

        elif intent.type == "data_overflow":
            before_len = len(run.node_data.get("battle_logs", []))
            for _ in range(3):
                engine._damage_target(run, "p0", 5, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msgs = []
            while len(after_logs) > before_len:
                dmg_msgs.append(after_logs.pop())
            dmg_msgs.reverse()
            dmg_summary = " ".join(dmg_msgs)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_data_overflow", enemy_name=enemy.name, dmg_summary=dmg_summary))
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_data_overflow_warning"))

        elif intent.type == "save_erase":
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", 35)
            gold_removed = 0
            hp_limit_removed = 0
            if p.gold >= 5:
                p.gold -= 5
                gold_removed = 5
            else:
                if p.hp > 1:
                    engine._damage_target(run, "p0", min(5, p.hp - 1), source=f"enemy:{enemy.name}", damage_type="true")
                p.max_hp = max(10, p.max_hp - 5)
                hp_limit_removed = 5
            if gold_removed:
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_save_erase_gold", enemy_name=enemy.name))
            else:
                logs.append(get_locale_text("i18n_enemy_boss.yog_log_save_erase_hp", enemy_name=enemy.name, hp_limit_removed=hp_limit_removed))

        elif intent.type == "input_hijack":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            DeckService.add_card_to_draw(p, "curse_intangible_whisper")
            DeckService.add_card_to_draw(p, "curse_intangible_whisper")
            random.shuffle(p.draw_pile)
            logs.append(get_locale_text("i18n_enemy_boss.yog_log_input_hijack", enemy_name=enemy.name, dmg_msg=dmg_msg))

        return "\n".join(logs)

register_enemy("【觉醒】虚空之门·尤格-索托斯")(BossYogSothothTemplate)
register_enemy("【终焉】虚空之门·尤格-索托斯")(BossYogSothothTemplate)
register_enemy("【万物归一】虚空之门·尤格-索托斯")(BossYogSothothTemplate)
