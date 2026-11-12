import random
from ...models.state import GameRun, ensure_card_state
from ...data.locale_data import get_locale_text
from ...entities import ALL_CARDS, ALL_AMULETS
from ...models.events import TurnEndEvent, TurnStartEvent, CardExhaustEvent


class CardPlayerTurnMixin:
    def _end_player_phase(self, run: GameRun, p) -> str:
        evt_end = TurnEndEvent(run, is_player=True)
        self.engine.event_bus.dispatch(evt_end)
        retain_key = run.turn_key("temp_retain_cards", p)
        retained = []
        temp_retains = list(run.node_data.get(retain_key, []))
        for c_state in p.hand:
            card = ALL_CARDS.get(c_state)
            if card and (getattr(card, "retain", False) or (hasattr(card, "gems") and card.gems and "gem_retain" in card.gems)):
                retained.append(c_state)
            elif c_state in temp_retains:
                retained.append(c_state)
                temp_retains.remove(c_state)
            elif card and card.id == "curse_dimensional_tear":
                p.exhaust_pile.append(c_state)
                self.engine._log_event(run, get_locale_text("i18n_battle_core.dimensional_tear_log", name=card.name, player=run.player.name))
                self.engine.combat_resolver.damage_target(run, "p0", 3, source="curse", damage_type="true")
                exhaust_evt = CardExhaustEvent(run, c_state, "curse_dimensional_tear")
                self.engine.event_bus.dispatch(exhaust_evt)
            elif card and getattr(card, "ethereal", False):
                p.exhaust_pile.append(c_state)
                self.engine._log_event(run, get_locale_text("i18n_battle_core.ethereal_exhaust_log", name=card.name))
                exhaust_evt = CardExhaustEvent(run, c_state, "ethereal")
                self.engine.event_bus.dispatch(exhaust_evt)
            else:
                p.discard_pile.append(c_state)
        p.hand = retained
        run.node_data[retain_key] = []
        for ak, av in list(p.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template:
                template.on_end_turn(run, ak, self.engine)
            if p.amulets.get(ak) is not av:
                continue
            av.countdown -= 1
            if av.countdown <= 0:
                p.amulets.pop(ak, None)
                p.minion_graveyard.append(av.id)
                lw_msg = ""
                if template:
                    is_upgraded = av.id.endswith("+")
                    lw_msg = template.on_death(run, ak, is_upgraded, self.engine)
                if lw_msg:
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.amulet_requiem_death_log", name=av.name, effect=lw_msg))
                else:
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.amulet_requiem_log", name=av.name))
        return get_locale_text("i18n_battle_core.end_player_phase_log", name=p.name)

    def _begin_player_phase(self, run: GameRun, p, advance_global: bool = True) -> str:
        decay_msgs = []
        has_barricade = any(b.id.startswith("barricade") for b in p.buffs)
        if p.shield > 0 and not has_barricade:
            lost = p.shield - (p.shield // 2)
            p.shield = p.shield // 2
            if lost > 0:
                decay_msgs.append(get_locale_text("i18n_battle_core.shield_decay_entry", name=p.name, lost=lost))
                from ...models.events import ShieldDecayEvent
                self.engine.event_bus.dispatch(ShieldDecayEvent(run, "p0", lost))
        elif p.shield > 0 and has_barricade:
            pass
        else:
            p.shield = 0
        decay_info = ""
        if decay_msgs:
            decay_info = get_locale_text("i18n_battle_core.player_shield_decay_line", entries="，".join(decay_msgs))
        p.actions = 2
        p.bonus_actions = 1
        evt_start = TurnStartEvent(run, is_player=True)
        self.engine.event_bus.dispatch(evt_start)
        if getattr(p, "subclass", "") == "时序法师":
            if random.random() < 0.25:
                p.bonus_actions += 1
                self.engine._log_event(run, get_locale_text("i18n_battle_core.time_shift_turn_log"))
        from ...data.minion_data import MINION_CONFIG
        for mk, mv in p.minions.items():
            if MINION_CONFIG.get(mv.id, {}).get("no_attack_actions"):
                mv.actions = 0
                mv.bonus_actions = 0
                mv.attack_actions = 0
                continue
            mv.actions += 1
            mv.attack_actions = 1
            if mv.id == "mercenary":
                mv.atk = 4
            elif mv.id == "mercenary+":
                mv.atk = 5
            elif mv.id == "arcane_golem":
                mv.atk = 6
            elif mv.id == "arcane_golem+":
                mv.atk = 8
        if advance_global:
            if run.enemies and any(e.name.startswith("腐化之心") for e in run.enemies):
                run.node_data["heart_turn"] = run.node_data.get("heart_turn", 1) + 1
        draw_count = 6
        if run.node_data.get("draw_penalty_next_turn"):
            draw_count = max(0, draw_count - run.node_data["draw_penalty_next_turn"])
            run.node_data.pop("draw_penalty_next_turn", None)
        self.draw_cards(p, draw_count, run, ignore_focus=True)
        discard_buff = next((b for b in p.buffs if b.id == "discard_next_turn"), None)
        if discard_buff:
            count = discard_buff.stacks
            discarded_names = []
            for _ in range(count):
                if p.hand:
                    discarded = p.hand.pop(random.randint(0, len(p.hand) - 1))
                    card_name = ALL_CARDS[discarded].name if discarded in ALL_CARDS else get_locale_text("i18n_battle_core.unknown_card")
                    discarded_names.append(f"【{card_name}】")
                    self.engine._discard_card(run, discarded)
            p.buffs.remove(discard_buff)
            if discarded_names:
                self.engine._log_event(run, get_locale_text("i18n_battle_core.discard_start_turn_log", cards=', '.join(discarded_names)))
        if any(b.id == "baguwen_restriction" for b in p.buffs):
            required_key = run.turn_key("baguwen_required_card", p)
            checked_key = run.turn_key("baguwen_checked", p)
            candidates = []
            for hand_state in p.hand:
                state = ensure_card_state(hand_state)
                card = ALL_CARDS.get(state)
                if card is None:
                    continue
                if getattr(card, "unplayable", False):
                    continue
                if getattr(card, "type", "") == "curse":
                    continue
                candidates.append((state, card))
            if candidates:
                state, card = random.choice(candidates)
                run.node_data[required_key] = {"id": state.id, "upgraded": bool(state.upgraded)}
                self.engine._log_event(run, get_locale_text("i18n_buffs.baguwen_required_log", card_name=card.name))
            else:
                run.node_data.pop(required_key, None)
            run.node_data[checked_key] = False
        run.node_data[run.turn_key("cards_played_this_turn", p)] = 0
        run.node_data[run.turn_key("action_surge_turn_used", p)] = False
        self._reindex_minions(p)
        if advance_global:
            run.node_data["turn_count"] = run.node_data.get("turn_count", 1) + 1
        return get_locale_text("i18n_battle_core.begin_player_phase_log", decay_info=decay_info, name=p.name)

    def end_turn(self, run: GameRun) -> str:
        if run.node_type != "battle":
            return get_locale_text("i18n_battle_core.not_in_battle_end_turn")
        from .party_battle import alive_uids, assign_enemy_targets, is_all_downed
        multi = run.player_count() > 1
        if not run.player or run.player.downed:
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(run.user_id, run, is_victory=False)
                if multi:
                    return get_locale_text("i18n_explore_core.coop_wipe_simple", settle_msg=settle_msg)
                return get_locale_text("i18n_battle_core.adventure_defeat", enemy_actions="", settle_msg=settle_msg)
            return get_locale_text("i18n_explore_core.downed_spectate")
        viewer = run.player
        viewer_uid = run.user_id
        uid = run.uid_for(viewer)
        end_msg = self._end_player_phase(run, viewer)
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return get_locale_text("i18n_explore_core.coop_wipe_simple", settle_msg=settle_msg)
                return get_locale_text("i18n_battle_core.adventure_defeat", enemy_actions="", settle_msg=settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            self.engine.save_manager.save_save(viewer_uid, run)
            return self.engine._append_logs_to_res(run, get_locale_text("i18n_battle_core.battle_victory"))
        ready = run.node_data.setdefault("turn_ready", {})
        ready[uid] = True
        alive = alive_uids(run)
        waiting = [u for u in alive if not ready.get(u, False)]
        if waiting:
            ready_uids = [u for u in alive if ready.get(u, False)]
            names = get_locale_text("i18n_explore_core.list_delimiter").join(run.players[u].name for u in ready_uids)
            self.engine.save_manager.save_save(uid, run)
            logs_text = self.engine._append_logs_to_res(run, end_msg or "")
            return get_locale_text(
                "i18n_explore_core.turn_waiting_others",
                logs=logs_text,
                count=len(ready_uids),
                total=len(alive),
                names=names,
            )
        run.node_data["turn_ready"] = {
            member: run.players[member].downed or getattr(run.players[member], "is_mercenary", False)
            for member in run.party_order
            if member in run.players
        }
        from ..mercenary import run_mercenaries_for_timing
        from ...data.mercenary_data import MERCENARY_TIMING_AFTER, MERCENARY_TIMING_BEFORE
        merc_after_logs = run_mercenaries_for_timing(self.engine, run, MERCENARY_TIMING_AFTER)
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return get_locale_text("i18n_explore_core.coop_wipe_enemy_log", enemy_logs=merc_after_logs, settle_msg=settle_msg)
                return get_locale_text("i18n_battle_core.adventure_defeat", enemy_actions=merc_after_logs, settle_msg=settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            self.engine.save_manager.save_save(viewer_uid, run)
            if multi:
                return self.engine._append_logs_to_res(run, get_locale_text("i18n_explore_core.battle_victory_log", enemy_logs=merc_after_logs))
            return self.engine._append_logs_to_res(run, f"{merc_after_logs}\n{get_locale_text('i18n_battle_core.battle_victory_emoji')}")
        extra_turns = run.node_data.get("extra_turns_left", 0)
        if extra_turns > 0:
            run.node_data["extra_turns_left"] = extra_turns - 1
            enemy_actions = get_locale_text("i18n_battle_core.time_stop_extra_turn", count=extra_turns - 1)
        else:
            assign_enemy_targets(run)
            enemy_actions = self.engine._enemy_turn(run)
        if merc_after_logs:
            enemy_actions = f"{merc_after_logs}\n{enemy_actions}".strip()
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return get_locale_text("i18n_explore_core.coop_wipe_enemy_log", enemy_logs=enemy_actions, settle_msg=settle_msg)
                return get_locale_text("i18n_battle_core.adventure_defeat", enemy_actions=enemy_actions, settle_msg=settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            self.engine.save_manager.save_save(viewer_uid, run)
            if multi:
                return self.engine._append_logs_to_res(run, get_locale_text("i18n_explore_core.battle_victory_log", enemy_logs=enemy_actions))
            return self.engine._append_logs_to_res(run, f"{enemy_actions}\n{get_locale_text('i18n_battle_core.battle_victory_emoji')}")
        if is_all_downed(run):
            if multi:
                run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
            settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
            if multi:
                return get_locale_text("i18n_explore_core.coop_wipe_enemy_log", enemy_logs=enemy_actions, settle_msg=settle_msg)
            return get_locale_text("i18n_battle_core.adventure_defeat", enemy_actions=enemy_actions, settle_msg=settle_msg)
        from ..mercenary import end_unended_mercenary_phases
        end_unended_mercenary_phases(self.engine, run)
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return get_locale_text("i18n_explore_core.coop_wipe_enemy_log", enemy_logs=enemy_actions, settle_msg=settle_msg)
                return get_locale_text("i18n_battle_core.adventure_defeat", enemy_actions=enemy_actions, settle_msg=settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            self.engine.save_manager.save_save(viewer_uid, run)
            if multi:
                return self.engine._append_logs_to_res(run, get_locale_text("i18n_explore_core.battle_victory_log", enemy_logs=enemy_actions))
            return self.engine._append_logs_to_res(run, f"{enemy_actions}\n{get_locale_text('i18n_battle_core.battle_victory_emoji')}")
        turn_logs = []
        first_alive = True
        for member in run.party_order:
            player = run.players.get(member)
            if player is None or player.downed or player.hp <= 0:
                continue
            run.player = player
            run.user_id = member
            turn_logs.append(self._begin_player_phase(run, player, advance_global=first_alive))
            first_alive = False
        run.player = viewer
        run.user_id = viewer_uid
        self.engine._roll_enemy_intent(run)
        assign_enemy_targets(run)
        merc_before_logs = run_mercenaries_for_timing(self.engine, run, MERCENARY_TIMING_BEFORE)
        if merc_before_logs:
            turn_logs.append(merc_before_logs)
        joined = "\n".join(log for log in turn_logs if log)
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return get_locale_text("i18n_explore_core.coop_wipe_joined", enemy_logs=enemy_actions, joined=joined, settle_msg=settle_msg)
                return get_locale_text("i18n_battle_core.adventure_defeat", enemy_actions=f"{enemy_actions}\n{joined}", settle_msg=settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            self.engine.save_manager.save_save(viewer_uid, run)
            if multi:
                return self.engine._append_logs_to_res(run, get_locale_text("i18n_explore_core.battle_victory_log", enemy_logs=f"{enemy_actions}\n{joined}"))
            return self.engine._append_logs_to_res(run, f"{enemy_actions}\n{joined}\n{get_locale_text('i18n_battle_core.battle_victory_emoji')}")
        if is_all_downed(run):
            if multi:
                run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
            settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
            if multi:
                return get_locale_text("i18n_explore_core.coop_wipe_joined", enemy_logs=enemy_actions, joined=joined, settle_msg=settle_msg)
            return get_locale_text("i18n_battle_core.adventure_defeat", enemy_actions=f"{enemy_actions}\n{joined}", settle_msg=settle_msg)
        self.engine.save_manager.save_save(viewer_uid, run)
        if multi:
            result = get_locale_text(
                "i18n_explore_core.turn_all_ready",
                enemy_logs=enemy_actions,
                joined=joined,
                turn_count=run.node_data["turn_count"],
            )
            return self.engine._append_logs_to_res(run, result)
        return self.engine._append_logs_to_res(run, f"{enemy_actions}\n{joined}")
