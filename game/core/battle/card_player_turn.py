import random
from typing import TYPE_CHECKING, Optional
from ...models.state import GameRun
from ...data.text.locale_data import get_locale_text
from ...entities import ALL_CARDS
from ...models.events import (
    TurnEndEvent,
    TurnEndAfterHandEvent,
    TurnStartEvent,
    TurnResourceInitEvent,
    TurnDrawCalculateEvent,
    TurnStartAfterDrawEvent,
    ShieldDecayCalculateEvent,
    CardExhaustEvent,
    CardTurnEndResolveEvent,
    CardDrawnEvent,
    CardDiscardEvent,
)
from ..text.events import JoinedText, LocaleText, RenderedText, TextDocument, locale_text
from ..text.pipeline import render_text
from .extra_turn_service import end_and_begin

if TYPE_CHECKING:
    from ...models.state import PlayerState
    from .engine import BattleEngine




class CardPlayerEngineMixin:
    if TYPE_CHECKING:
        engine: BattleEngine


class CardPlayerTurnMixin(CardPlayerEngineMixin):
    if TYPE_CHECKING:

        def handle_battle_win(self, run: GameRun) -> None: ...

        def _finalize_card_play(self, run, p, card, c_state, target, res, source="played", register=True, allow_return=True) -> tuple[str, bool]: ...

        def _reindex_minions(self, p: PlayerState) -> None: ...
    def _render_events(self, document: TextDocument) -> str:
        return render_text(document, "battle")

    def _end_player_phase(self, run: GameRun, p) -> str:
        return self._render_events(self._end_player_phase_events(run, p))

    def _end_player_phase_events(self, run: GameRun, p) -> TextDocument:
        evt_end = TurnEndEvent(run, is_player=True)
        self.engine.event_bus.dispatch(evt_end)
        retain_key = run.turn_key("temp_retain_cards", p)
        retained = []
        temp_retains = list(run.node_data.get(retain_key, []))
        for c_state in list(p.hand):
            card = ALL_CARDS.get(c_state)
            action = "discard"
            if card and (getattr(card, "retain", False) or getattr(c_state, "temp_retain", False) or c_state in temp_retains):
                action = "retain"
            elif card and (getattr(card, "ethereal", False) or getattr(c_state, "temp_ethereal", False)):
                action = "exhaust"
            evt = CardTurnEndResolveEvent(run, p, c_state, card, action=action)
            self.engine.event_bus.dispatch(evt)
            action = evt.action
            if action == "retain":
                c_state.temp_cost_a = None
                c_state.temp_cost_ba = None
                c_state.temp_retain = False
                retained.append(c_state)
                if c_state in temp_retains:
                    temp_retains.remove(c_state)
            elif action == "exhaust":
                p.exhaust_pile.append(c_state)
                if not evt.handled:
                    self.engine._log_event(run, locale_text(
                        "i18n_battle_core.ethereal_exhaust_log",
                        params={"name": card.name if card else c_state.id},
                    ))
                exhaust_evt = CardExhaustEvent(run, c_state, "turn_end")
                self.engine.event_bus.dispatch(exhaust_evt)
            elif action == "draw":
                p.draw_pile.append(c_state)
            elif action != "remove":
                c_state.temp_cost_a = None
                c_state.temp_cost_ba = None
                c_state.temp_ethereal = False
                c_state.temp_exhaust = False
                c_state.temp_retain = False
                p.discard_pile.append(c_state)
        p.hand = retained
        run.node_data[retain_key] = []
        self.engine.event_bus.dispatch(TurnEndAfterHandEvent(run, p))
        return [locale_text(key="i18n_battle_core.end_player_phase_log", params={"name": p.name})]

    def _begin_player_phase(self, run: GameRun, p, advance_global: bool = True) -> str:
        return self._render_events(self._begin_player_phase_events(run, p, advance_global))

    def _begin_player_phase_events(self, run: GameRun, p, advance_global: bool = True) -> TextDocument:
        decay_entries: list[LocaleText] = []
        if p.shield > 0:
            decay_evt = ShieldDecayCalculateEvent(run, p, "p0", p.shield, p.shield - (p.shield // 2))
            self.engine.event_bus.dispatch(decay_evt)
            lost = 0 if decay_evt.cancelled else max(0, min(p.shield, decay_evt.decay_amount))
            p.shield -= lost
            if lost > 0:
                decay_entries.append(locale_text(
                    "i18n_battle_core.shield_decay_entry",
                    params={"name": p.name, "lost": lost},
                ))
                from ...models.events import ShieldDecayEvent
                self.engine.event_bus.dispatch(ShieldDecayEvent(run, "p0", lost))
        else:
            p.shield = 0
        resource_evt = TurnResourceInitEvent(run, p, 2, 1)
        self.engine.event_bus.dispatch(resource_evt)
        p.actions = resource_evt.actions
        p.bonus_actions = resource_evt.bonus_actions
        evt_start = TurnStartEvent(run, is_player=True)
        self.engine.event_bus.dispatch(evt_start)
        from ...data.entities.minions.minion_data import MINION_CONFIG
        for mk, mv in p.minions.items():
            if MINION_CONFIG.get(mv.id, {}).get("no_attack_actions"):
                mv.actions = 0
                mv.bonus_actions = 0
                mv.attack_actions = 0
                continue
            mv.actions += 1
            mv.attack_actions = 1
        draw_count = 6
        if run.node_data.get("draw_penalty_next_turn"):
            draw_count = max(0, draw_count - run.node_data["draw_penalty_next_turn"])
            run.node_data.pop("draw_penalty_next_turn", None)
        draw_evt = TurnDrawCalculateEvent(run, p, draw_count)
        self.engine.event_bus.dispatch(draw_evt)
        draw_count = draw_evt.draw_count
        self.draw_cards(p, draw_count, run, ignore_focus=True, is_turn_start=True)
        self.engine.event_bus.dispatch(TurnStartAfterDrawEvent(run, p))
        run.node_data[run.turn_key("cards_played_this_turn", p)] = 0
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

    def _exit_downed_battle(self, run: GameRun, uid: str, logs: TextDocument | None = None) -> TextDocument:
        settle_msg = self.engine.save_manager.settle_game_and_delete(uid, run, is_victory=False)
        return [locale_text(
            "i18n_explore_core.coop_downed_exit",
            params={"logs": JoinedText(parts=list(logs or [])), "settle_msg": settle_msg},
        )]

    def _end_turn_events(self, run: GameRun) -> TextDocument:
        if run.node_type != "battle":
            return [locale_text(key="i18n_battle_core.not_in_battle_end_turn")]
        from .party_battle import alive_uids, assign_enemy_targets, is_all_downed
        multi = len(run.all_human_uids()) > 1
        if not run.player or run.player.downed:
            if is_all_downed(run):
                if multi:
                    run.end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(run.user_id, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_simple", params={"settle_msg": settle_msg})]
                return self._defeat_nodes(run, "", settle_msg)
            if alive_uids(run):
                return [locale_text(key="i18n_explore_core.downed_spectate")]
            return self._exit_downed_battle(run, run.user_id)
        viewer = run.player
        viewer_uid = run.user_id
        uid = run.uid_for(viewer)
        end_events = self._end_player_phase_events(run, viewer)
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_simple", params={"settle_msg": settle_msg})]
                return self._defeat_nodes(run, "", settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            if run.node_type == "room_dialog":
                return self._finish_turn(run, [], viewer_uid)
            return self._finish_turn(run, [locale_text(key="i18n_battle_core.battle_victory")], viewer_uid)
        extra_events, in_extra = end_and_begin(self.engine, run, uid)
        if in_extra:
            return self._finish_turn(run, extra_events, viewer_uid)
        if extra_events and self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_simple", params={"settle_msg": settle_msg})]
                return self._defeat_nodes(run, JoinedText(parts=extra_events), settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            if run.node_type == "room_dialog":
                return self._finish_turn(run, extra_events, viewer_uid)
            return self._finish_turn(run, extra_events + [locale_text(key="i18n_battle_core.battle_victory")], viewer_uid)
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
                    "logs": JoinedText(parts=end_events + extra_events + log_nodes),
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
        from ...data.entities.mercenary_data import MERCENARY_TIMING_AFTER, MERCENARY_TIMING_BEFORE
        merc_after_logs = run_mercenaries_for_timing(self.engine, run, MERCENARY_TIMING_AFTER)
        merc_after_events: TextDocument = []
        if merc_after_logs:
            merc_after_events.append(RenderedText(text=merc_after_logs))
        if extra_events:
            merc_after_events = extra_events + merc_after_events
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_enemy_log", params={
                        "enemy_logs": JoinedText(parts=merc_after_events),
                        "settle_msg": settle_msg,
                    })]
                return self._defeat_nodes(run, JoinedText(parts=merc_after_events), settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            if run.node_type == "room_dialog":
                return self._finish_turn(run, merc_after_events, viewer_uid)
            return self._finish_turn(run, self._victory_events(merc_after_events), viewer_uid)
        assign_enemy_targets(run, self.engine)
        enemy_events: TextDocument = self.engine._enemy_turn_events(run)
        if merc_after_events:
            enemy_events = merc_after_events + enemy_events
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_enemy_log", params={
                        "enemy_logs": JoinedText(parts=enemy_events),
                        "settle_msg": settle_msg,
                    })]
                return self._defeat_nodes(run, JoinedText(parts=enemy_events), settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            if run.node_type == "room_dialog":
                return self._finish_turn(run, enemy_events, viewer_uid)
            return self._finish_turn(run, self._victory_events(enemy_events), viewer_uid)
        if is_all_downed(run):
            if multi:
                run.end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
            settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
            if multi:
                return [locale_text(key="i18n_explore_core.coop_wipe_enemy_log", params={
                    "enemy_logs": JoinedText(parts=enemy_events),
                    "settle_msg": settle_msg,
                })]
            return self._defeat_nodes(run, JoinedText(parts=enemy_events), settle_msg)
        from ..party.mercenary import end_unended_mercenary_phases
        end_unended_mercenary_phases(self.engine, run)
        if run.player is not None and run.player.downed and not alive_uids(run):
            return self._exit_downed_battle(run, viewer_uid, enemy_events)
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.engine.save_manager.settle_game_and_delete(viewer_uid, run, is_victory=False)
                if multi:
                    return [locale_text(key="i18n_explore_core.coop_wipe_enemy_log", params={
                        "enemy_logs": JoinedText(parts=enemy_events),
                        "settle_msg": settle_msg,
                    })]
                return self._defeat_nodes(run, JoinedText(parts=enemy_events), settle_msg)
            self.handle_battle_win(run)
            self._reindex_minions(viewer)
            if run.node_type == "room_dialog":
                return self._finish_turn(run, enemy_events, viewer_uid)
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
        assign_enemy_targets(run, self.engine)
        merc_before_logs = run_mercenaries_for_timing(self.engine, run, MERCENARY_TIMING_BEFORE)
        if merc_before_logs:
            turn_logs.append(RenderedText(text=merc_before_logs))
        if self.engine.is_battle_won(run):
            if is_all_downed(run):
                if multi:
                    run.end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
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
            if run.node_type == "room_dialog":
                return self._finish_turn(run, enemy_events + turn_logs, viewer_uid)
            return self._finish_turn(run, self._victory_events(enemy_events + turn_logs), viewer_uid)
        if is_all_downed(run):
            if multi:
                run.end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
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

    def draw_cards(self, p: PlayerState, count: int, run: Optional[GameRun] = None, ignore_focus: bool = False, is_turn_start: bool = False, depth: int = 0):
        if run is not None:
            from ...models.events import BeforeCardDrawEvent
            pre_evt = BeforeCardDrawEvent(run, p, count, ignore_focus, is_turn_start)
            self.engine.event_bus.dispatch(pre_evt)
            if pre_evt.cancelled:
                return
        max_hand = self.engine.get_max_hand_size(run, p)
        drawn_cards = []
        reshuffled = False
        for _ in range(count):
            if not p.draw_pile:
                if p.discard_pile:
                    p.draw_pile = p.discard_pile.copy()
                    random.shuffle(p.draw_pile)
                    p.discard_pile.clear()
                    reshuffled = True
            if p.draw_pile:
                cid = p.draw_pile.pop()
                card_obj = ALL_CARDS.get(cid)
                if run is not None:
                    drawn_evt = CardDrawnEvent(run, p, cid, card_obj, False, depth)
                    self.engine.event_bus.dispatch(drawn_evt)
                    if drawn_evt.intercepted:
                        continue
                if len(p.hand) < max_hand:
                    p.hand.append(cid)
                    drawn_cards.append(cid)
                else:
                    p.discard_pile.append(cid)
                    if run is not None:
                        card_obj = ALL_CARDS.get(cid)
                        card_name = card_obj.name if card_obj else get_locale_text("i18n_battle_core.unknown_card")
                        self.engine._log_event(run, get_locale_text("i18n_battle_core.hand_full_discard_log", name=card_name))
        if run is not None:
            if reshuffled:
                self.engine._log_event(run, get_locale_text("i18n_battle_core.reshuffle_log"))

    def discard_card(self, run: GameRun, cid) -> str:
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(cid)
        p = run.player
        card = ALL_CARDS.get(c_state)
        discard_evt = CardDiscardEvent(run, c_state, "manual")
        self.engine.event_bus.dispatch(discard_evt)
        if not card:
            p.discard_pile.append(c_state)
            return self.engine._append_logs_to_res(run, "")
        is_agile = getattr(card, "agile", False)
        is_cryptic = getattr(card, "cryptic", False)
        if is_agile or is_cryptic:
            target = None
            if card.type == "spell":
                if getattr(card, "target_type", "enemy") == "self":
                    target = "p0"
                else:
                    target = self.engine._get_first_alive_enemy(run)
                if target == "0" or target == "e0":
                    target = "e1"
            elif card.type == "ability":
                target = "p0"
            elif card.type in ("minion", "amulet"):
                if getattr(card, "target_type", "enemy") == "enemy":
                    target = self.engine._get_first_alive_enemy(run)
                else:
                    target = self.engine._get_free_grid(run.player) or "p1"
            run.node_data["extra_play_msgs"] = []
            play_source = "agile" if is_agile else "cryptic"
            res = self.engine._execute_card_effect(run, card, target)
            res, _ = self._finalize_card_play(run, p, card, c_state, target, res, source=play_source, register=False)
            self._reindex_minions(p)
            log_key = "i18n_battle_core.agile_discard_log" if is_agile else "i18n_battle_core.cryptic_discard_log"
            return self.engine._append_logs_to_res(run, get_locale_text(log_key, name=card.name, effect=res))
        else:
            p.discard_pile.append(c_state)
            self._reindex_minions(p)
            return self.engine._append_logs_to_res(run, "")
