import random
from typing import TYPE_CHECKING, Optional
from ...models.state import GameRun, ensure_card_state
from ...data.locale_data import get_locale_text
from ...entities import ALL_CARDS, ALL_AMULETS
from ...models.events import TurnEndEvent, TurnStartEvent, CardExhaustEvent
from ..text.events import JoinedText, LocaleText, RenderedText, TextDocument, locale_text
from ..text.pipeline import render_text

if TYPE_CHECKING:
    from ...models.state import PlayerState
    from .engine import BattleEngine




class CardPlayerEngineMixin:
    if TYPE_CHECKING:
        engine: BattleEngine


class CardPlayerTurnMixin(CardPlayerEngineMixin):
    if TYPE_CHECKING:

        def draw_cards(self, p: PlayerState, count: int, run: Optional[GameRun] = None, ignore_focus: bool = False, depth: int = 0) -> None: ...

        def handle_battle_win(self, run: GameRun) -> None: ...

        def _reindex_minions(self, p: PlayerState) -> None: ...
    def _render_events(self, document: TextDocument) -> str:
        return render_text(document, "battle")

    def _end_player_phase(self, run: GameRun, p) -> str:
        return self._render_events(self._end_player_phase_events(run, p))

    def _end_player_phase_events(self, run: GameRun, p) -> TextDocument:
        from .enchantment_runtime import apply_enchantment_turn_end
        apply_enchantment_turn_end(run, p)
        from .ninja_runtime import handle_ninja_turn_end
        handle_ninja_turn_end(self.engine, run, p)
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
                self.engine._log_event(run, locale_text(
                    "i18n_battle_core.dimensional_tear_log",
                    params={"name": card.name, "player": run.player.name},
                ))
                self.engine.combat_resolver.damage_target(run, "p0", 3, source="curse", damage_type="true")
                exhaust_evt = CardExhaustEvent(run, c_state, "curse_dimensional_tear")
                self.engine.event_bus.dispatch(exhaust_evt)
            elif card and getattr(card, "ethereal", False):
                p.exhaust_pile.append(c_state)
                self.engine._log_event(run, locale_text(
                    "i18n_battle_core.ethereal_exhaust_log",
                    params={"name": card.name},
                ))
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
                    self.engine._log_event(run, locale_text(
                        "i18n_battle_core.amulet_requiem_death_log",
                        params={"name": av.name, "effect": lw_msg},
                    ))
                else:
                    self.engine._log_event(run, locale_text(
                        "i18n_battle_core.amulet_requiem_log",
                        params={"name": av.name},
                    ))
        return [locale_text(key="i18n_battle_core.end_player_phase_log", params={"name": p.name})]

    def _begin_player_phase(self, run: GameRun, p, advance_global: bool = True) -> str:
        return self._render_events(self._begin_player_phase_events(run, p, advance_global))

    def _begin_player_phase_events(self, run: GameRun, p, advance_global: bool = True) -> TextDocument:
        decay_entries: list[LocaleText] = []
        has_barricade = any(b.id.startswith("barricade") for b in p.buffs)
        if p.shield > 0 and not has_barricade:
            lost = p.shield - (p.shield // 2)
            p.shield = p.shield // 2
            if lost > 0:
                decay_entries.append(locale_text(
                    "i18n_battle_core.shield_decay_entry",
                    params={"name": p.name, "lost": lost},
                ))
                from ...models.events import ShieldDecayEvent
                self.engine.event_bus.dispatch(ShieldDecayEvent(run, "p0", lost))
        elif p.shield > 0 and has_barricade:
            pass
        else:
            p.shield = 0
        p.actions = 2
        p.bonus_actions = 1
        from .enchantment_runtime import apply_enchantment_turn_start
        apply_enchantment_turn_start(self.engine, run, p)
        from .ninja_runtime import handle_ninja_turn_start
        handle_ninja_turn_start(run, p)
        evt_start = TurnStartEvent(run, is_player=True)
        self.engine.event_bus.dispatch(evt_start)
        if getattr(p, "subclass", "") == "时序法师":
            if random.random() < 0.25:
                p.bonus_actions += 1
                self.engine._log_event(run, locale_text(key="i18n_battle_core.time_shift_turn_log"))
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
                self.engine._log_event(run, locale_text(
                    "i18n_battle_core.discard_start_turn_log",
                    params={"cards": ', '.join(discarded_names)},
                ))
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
                self.engine._log_event(run, locale_text(
                    "i18n_buffs.baguwen_required_log",
                    params={"card_name": card.name},
                ))
            else:
                run.node_data.pop(required_key, None)
            run.node_data[checked_key] = False
        run.node_data[run.turn_key("cards_played_this_turn", p)] = 0
        run.node_data[run.turn_key("action_surge_turn_used", p)] = False
        self._reindex_minions(p)
        if advance_global:
            run.node_data["turn_count"] = run.node_data.get("turn_count", 1) + 1
        events: TextDocument = []
        if decay_entries:
            events.append(locale_text(
                "i18n_battle_core.player_shield_decay_line",
                params={"entries": JoinedText(parts=decay_entries, separator="，")},
            ))
        events.append(locale_text(key="i18n_battle_core.begin_player_phase_log", params={"name": p.name}))
        return events

    def end_turn(self, run: GameRun) -> str:
        return self._render_events(self._end_turn_events(run))

    def _finish_turn(self, run: GameRun, document: TextDocument, save_uid: str) -> TextDocument:
        result = list(document) + self.engine._take_battle_logs(run)
        self.engine.save_manager.save_save(save_uid, run)
        return result

    def _victory_events(self, enemy_events: TextDocument) -> TextDocument:
        return [locale_text(
            "i18n_explore_core.battle_victory_log",
            params={"enemy_logs": JoinedText(parts=enemy_events)},
        )]

    def _end_turn_events(self, run: GameRun) -> TextDocument:
        if run.node_type != "battle":
            return [locale_text(key="i18n_battle_core.not_in_battle_end_turn")]
        from .party_battle import alive_uids, assign_enemy_targets, is_all_downed
        multi = run.player_count() > 1
        if not run.player or run.player.downed:
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(run.user_id, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_simple", params={"settle_msg": settle_msg})]
                return self._defeat_nodes(run, "", settle_msg)
            return [locale_text(key="i18n_explore_core.downed_spectate")]
        viewer = run.player
        viewer_uid = run.user_id
        uid = run.uid_for(viewer)
        end_events = self._end_player_phase_events(run, viewer)
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_simple", params={"settle_msg": settle_msg})]
                return self._defeat_nodes(run, "", settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            return self._finish_turn(run, [locale_text(key="i18n_battle_core.battle_victory")], viewer_uid)
        ready = run.node_data.setdefault("turn_ready", {})
        ready[uid] = True
        alive = alive_uids(run)
        waiting = [u for u in alive if not ready.get(u, False)]
        if waiting:
            ready_uids = [u for u in alive if ready.get(u, False)]
            names = get_locale_text("i18n_explore_core.list_delimiter").join(run.players[u].name for u in ready_uids)
            log_nodes = self.engine._take_battle_logs(run)
            self.engine.save_manager.save_save(uid, run)
            return [locale_text(
                "i18n_explore_core.turn_waiting_others",
                params={
                    "logs": JoinedText(parts=end_events + log_nodes),
                    "count": len(ready_uids),
                    "total": len(alive),
                    "names": names,
                },
            )]
        run.node_data["turn_ready"] = {
            member: run.players[member].downed or getattr(run.players[member], "is_mercenary", False)
            for member in run.party_order
            if member in run.players
        }
        from ..party.mercenary import run_mercenaries_for_timing
        from ...data.mercenary_data import MERCENARY_TIMING_AFTER, MERCENARY_TIMING_BEFORE
        merc_after_logs = run_mercenaries_for_timing(self.engine, run, MERCENARY_TIMING_AFTER)
        merc_after_events: TextDocument = []
        if merc_after_logs:
            merc_after_events.append(RenderedText(text=merc_after_logs))
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_enemy_log", params={
                        "enemy_logs": JoinedText(parts=merc_after_events),
                        "settle_msg": settle_msg,
                    })]
                return self._defeat_nodes(run, JoinedText(parts=merc_after_events), settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            return self._finish_turn(run, self._victory_events(merc_after_events), viewer_uid)
        extra_turns = run.node_data.get("extra_turns_left", 0)
        if extra_turns > 0:
            run.node_data["extra_turns_left"] = extra_turns - 1
            enemy_events: TextDocument = [locale_text(
                "i18n_battle_core.time_stop_extra_turn",
                params={"count": extra_turns - 1},
            )]
        else:
            assign_enemy_targets(run)
            enemy_events = self.engine._enemy_turn_events(run)
        if merc_after_events:
            enemy_events = merc_after_events + enemy_events
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_enemy_log", params={
                        "enemy_logs": JoinedText(parts=enemy_events),
                        "settle_msg": settle_msg,
                    })]
                return self._defeat_nodes(run, JoinedText(parts=enemy_events), settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            return self._finish_turn(run, self._victory_events(enemy_events), viewer_uid)
        if is_all_downed(run):
            if multi:
                run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
            settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
            if multi:
                return [locale_text(key="i18n_explore_core.coop_wipe_enemy_log", params={
                    "enemy_logs": JoinedText(parts=enemy_events),
                    "settle_msg": settle_msg,
                })]
            return self._defeat_nodes(run, JoinedText(parts=enemy_events), settle_msg)
        from ..party.mercenary import end_unended_mercenary_phases
        end_unended_mercenary_phases(self.engine, run)
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_enemy_log", params={
                        "enemy_logs": JoinedText(parts=enemy_events),
                        "settle_msg": settle_msg,
                    })]
                return self._defeat_nodes(run, JoinedText(parts=enemy_events), settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            return self._finish_turn(run, self._victory_events(enemy_events), viewer_uid)
        turn_logs: TextDocument = []
        first_alive = True
        for member in run.party_order:
            player = run.players.get(member)
            if player is None or player.downed or player.hp <= 0:
                continue
            run.player = player
            run.user_id = member
            turn_logs.extend(self._begin_player_phase_events(run, player, advance_global=first_alive))
            first_alive = False
        run.player = viewer
        run.user_id = viewer_uid
        self.engine._roll_enemy_intent(run)
        assign_enemy_targets(run)
        merc_before_logs = run_mercenaries_for_timing(self.engine, run, MERCENARY_TIMING_BEFORE)
        if merc_before_logs:
            turn_logs.append(RenderedText(text=merc_before_logs))
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_joined", params={
                        "enemy_logs": JoinedText(parts=enemy_events),
                        "joined": JoinedText(parts=turn_logs),
                        "settle_msg": settle_msg,
                    })]
                return self._defeat_nodes(run, JoinedText(parts=enemy_events + turn_logs), settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            return self._finish_turn(run, self._victory_events(enemy_events + turn_logs), viewer_uid)
        if is_all_downed(run):
            if multi:
                run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
            settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
            if multi:
                return [locale_text(key="i18n_explore_core.coop_wipe_joined", params={
                    "enemy_logs": JoinedText(parts=enemy_events),
                    "joined": JoinedText(parts=turn_logs),
                    "settle_msg": settle_msg,
                })]
            return self._defeat_nodes(run, JoinedText(parts=enemy_events + turn_logs), settle_msg)
        if multi:
            result = locale_text(
                "i18n_explore_core.turn_all_ready",
                params={
                    "enemy_logs": JoinedText(parts=enemy_events),
                    "joined": JoinedText(parts=turn_logs),
                    "turn_count": run.node_data["turn_count"],
                },
            )
            return self._finish_turn(run, [result], viewer_uid)
        return self._finish_turn(run, enemy_events + turn_logs, viewer_uid)

    def _defeat_nodes(self, run: GameRun, enemy_actions_node, settle_msg: str) -> TextDocument:
        from ..world.open_world.loadout_service import is_open_world_run
        if is_open_world_run(run):
            nodes: TextDocument = []
            if enemy_actions_node:
                nodes.append(enemy_actions_node)
            if settle_msg:
                nodes.append(RenderedText(text=settle_msg))
            if not nodes:
                return []
            doc: TextDocument = []
            doc.append(JoinedText(parts=nodes, separator="\n\n"))
            return doc
        return [
            locale_text(
                key="i18n_battle_core.adventure_defeat",
                params={"enemy_actions": enemy_actions_node, "settle_msg": settle_msg},
            )
        ]
