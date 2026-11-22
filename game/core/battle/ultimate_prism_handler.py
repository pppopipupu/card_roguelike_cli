import copy
from typing import Optional
from ...data.content.ultimate_prism_data import (
    GLASS_SHARD_ITEM_ID,
    ULTIMATE_PRISM_CARD_ID,
    ULTIMATE_PRISM_CONFIG,
    ULTIMATE_PRISM_FLAG_DEPARTED,
    ULTIMATE_PRISM_FLAG_IDLE_BATTLES,
    ULTIMATE_PRISM_MERC_ID,
)
from ...entities import ALL_CARDS
from ...models.events import (
    BattleStartEvent,
    BattleWinEvent,
    CardExhaustEvent,
    CardExtraTriggerEvent,
    CardPlayEvent,
    CardPlayedEvent,
)
from ...models.state import CardState, GameRun, PlayerState, ensure_card_state
from ..inventory.bag_service import add_bag_item
from ..party.coordinator import add_notice
from ..text.events import locale_text
from ..text.pipeline import render_text_node
from ..world.tutorial import is_tutorial_run


def _player_has_prism(player: Optional[PlayerState]) -> bool:
    if player is None:
        return False
    for pile in (player.deck, player.hand, player.draw_pile, player.discard_pile, player.exhaust_pile):
        if any(ensure_card_state(c).id == ULTIMATE_PRISM_CARD_ID for c in pile):
            return True
    return False


def _remove_all_prism_from_player(player: PlayerState) -> None:
    player.deck = [c for c in player.deck if ensure_card_state(c).id != ULTIMATE_PRISM_CARD_ID]
    player.hand = [c for c in player.hand if ensure_card_state(c).id != ULTIMATE_PRISM_CARD_ID]
    player.draw_pile = [c for c in player.draw_pile if ensure_card_state(c).id != ULTIMATE_PRISM_CARD_ID]
    player.discard_pile = [c for c in player.discard_pile if ensure_card_state(c).id != ULTIMATE_PRISM_CARD_ID]
    player.exhaust_pile = [c for c in player.exhaust_pile if ensure_card_state(c).id != ULTIMATE_PRISM_CARD_ID]


def _pick_auto_target(engine, run: GameRun, card, preferred_target: Optional[str]) -> Optional[str]:
    ctype = getattr(card, "type", "spell")
    ttype = getattr(card, "target_type", "enemy")
    if ctype in ("minion", "amulet"):
        return engine._get_free_grid(run.player)
    if ctype == "ability" or ttype == "self":
        return "p0"
    if ttype in ("all_enemies", "none", "random_enemy"):
        return preferred_target or engine._get_first_alive_enemy(run)
    if preferred_target and str(preferred_target).startswith("e"):
        try:
            idx = int(str(preferred_target)[1:]) - 1
            if 0 <= idx < len(run.enemies) and run.enemies[idx].hp > 0:
                return f"e{idx + 1}"
        except ValueError:
            pass
    return engine._get_first_alive_enemy(run)


class UltimatePrismHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(CardPlayEvent, self.on_card_play)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(CardExtraTriggerEvent, self.on_card_extra_trigger)
        event_bus.subscribe(BattleWinEvent, self.on_battle_win)

    def _battle_flag_key(self, run: GameRun, player: PlayerState) -> str:
        uid = run.uid_for(player) or run.user_id
        return f"prism_triggered_battle_{uid}"

    def on_battle_start(self, event: BattleStartEvent):
        run = event.run
        p = run.player
        if p is None or getattr(p, "is_mercenary", False):
            return
        run.node_data[self._battle_flag_key(run, p)] = False
        run.node_data.pop("prism_pending_refracts", None)

    def on_card_play(self, event: CardPlayEvent):
        run = event.run
        p = run.player
        if event.cancelled or p is None:
            run.node_data.pop("prism_pending_refracts", None)
            return
        played_idx = run.node_data.get("current_playing_card_hand_idx")
        if not isinstance(played_idx, int) or not (0 <= played_idx < len(p.hand)):
            run.node_data.pop("prism_pending_refracts", None)
            return
        pending = []
        hand_len = len(p.hand)
        if played_idx + 2 < hand_len:
            right_mid = ensure_card_state(p.hand[played_idx + 1])
            if right_mid.id == ULTIMATE_PRISM_CARD_ID:
                opp_state = ensure_card_state(p.hand[played_idx + 2])
                pending.append({"opp_idx": played_idx + 1, "opp_id": opp_state.id, "side": "right"})
        if played_idx - 2 >= 0:
            left_mid = ensure_card_state(p.hand[played_idx - 1])
            if left_mid.id == ULTIMATE_PRISM_CARD_ID:
                opp_state = ensure_card_state(p.hand[played_idx - 2])
                pending.append({"opp_idx": played_idx - 2, "opp_id": opp_state.id, "side": "left"})
        if pending:
            run.node_data["prism_pending_refracts"] = pending
        else:
            run.node_data.pop("prism_pending_refracts", None)

    def _find_opposite_index(self, hand: list[CardState], opp_idx: int, opp_id: str, side: str) -> Optional[int]:
        if 0 <= opp_idx < len(hand) and ensure_card_state(hand[opp_idx]).id == opp_id:
            return opp_idx
        for idx, raw_st in enumerate(hand):
            if ensure_card_state(raw_st).id != ULTIMATE_PRISM_CARD_ID:
                continue
            cand = idx + 1 if side == "right" else idx - 1
            if 0 <= cand < len(hand) and ensure_card_state(hand[cand]).id == opp_id:
                return cand
        return None

    def _mark_prism_triggered(self, run: GameRun, player: PlayerState) -> None:
        if getattr(player, "is_mercenary", False):
            return
        run.node_data[self._battle_flag_key(run, player)] = True
        uid = run.uid_for(player) or run.user_id
        sm = getattr(self.engine, "save_manager", None)
        if uid and sm is not None:
            stats = sm.load_stats(uid)
            if int(stats.town_flags.get(ULTIMATE_PRISM_FLAG_IDLE_BATTLES, 0) or 0) != 0:
                stats.town_flags[ULTIMATE_PRISM_FLAG_IDLE_BATTLES] = 0
                sm.save_stats(uid, stats)

    def on_card_played(self, event: CardPlayedEvent):
        run = event.run
        p = run.player
        if p is None or getattr(event, "is_extra", False):
            return
        if run.node_data.get("prism_refract_running"):
            return
        pending = run.node_data.pop("prism_pending_refracts", None)
        if not pending:
            return
        refract_count = int(ULTIMATE_PRISM_CONFIG["refract_count"])
        run.node_data["prism_refract_running"] = True
        try:
            for item in sorted(pending, key=lambda x: int(x.get("opp_idx", -1)), reverse=True):
                opp_idx = int(item.get("opp_idx", -1))
                opp_id = str(item.get("opp_id", ""))
                side = str(item.get("side", "right"))
                found_idx = self._find_opposite_index(p.hand, opp_idx, opp_id, side)
                if found_idx is None:
                    continue
                opp_state = ensure_card_state(p.hand[found_idx])
                opp_card = ALL_CARDS.get(opp_state)
                if opp_card is None or getattr(opp_card, "unplayable", False):
                    continue
                p.hand.pop(found_idx)
                self.engine._log_event(
                    run,
                    locale_text(
                        "i18n_prism.card.refract_trigger",
                        params={"card_name": opp_card.name, "count": refract_count},
                    ),
                )
                for _ in range(refract_count):
                    if self.engine.is_battle_won(run):
                        break
                    opp_target = _pick_auto_target(self.engine, run, opp_card, event.target)
                    if opp_card.type in ("minion", "amulet") and opp_target is None:
                        break
                    extra_res = self.engine._execute_card_effect(run, opp_card, opp_target)
                    played_evt = CardPlayedEvent(run, opp_card, opp_target, extra_res, is_extra=True)
                    self.engine.event_bus.dispatch(played_evt)
                    if played_evt.feedback:
                        run.node_data.setdefault("extra_play_msgs", []).append(f"\n{played_evt.feedback}")
                clean_state = copy.copy(opp_state)
                clean_state.return_left = 0
                clean_state.temp_cost_a = None
                clean_state.temp_cost_ba = None
                clean_state.temp_ethereal = False
                p.exhaust_pile.append(clean_state)
                self.engine._log_event(
                    run,
                    locale_text(
                        "i18n_prism.card.refract_exhaust_log",
                        params={"card_name": opp_card.name},
                    ),
                )
                self.engine.event_bus.dispatch(CardExhaustEvent(run, clean_state, "ultimate_prism"))
                self._mark_prism_triggered(run, p)
                self.engine.event_bus.dispatch(CardExtraTriggerEvent(run, opp_card, "prism"))
        finally:
            run.node_data.pop("prism_refract_running", None)

    def on_card_extra_trigger(self, event: CardExtraTriggerEvent):
        run = event.run
        p = run.player
        if p is None:
            return
        trigger_map = {
            "echo": (int(ULTIMATE_PRISM_CONFIG["echo_cost_reduction"]), "i18n_prism.card.trigger_echo"),
            "replay": (int(ULTIMATE_PRISM_CONFIG["replay_cost_reduction"]), "i18n_prism.card.trigger_replay"),
            "prism": (int(ULTIMATE_PRISM_CONFIG["prism_cost_reduction"]), "i18n_prism.card.trigger_prism"),
        }
        entry = trigger_map.get(event.trigger_type)
        if entry is None:
            return
        reduction, label_key = entry
        trigger_label = render_text_node(locale_text(label_key))
        for raw_st in p.hand:
            st = ensure_card_state(raw_st)
            if st.id != ULTIMATE_PRISM_CARD_ID:
                continue
            card_obj = ALL_CARDS.get(st)
            base_cost = int(getattr(card_obj, "cost_a", ULTIMATE_PRISM_CONFIG["cost_a"]))
            cur_delta = int(getattr(st, "battle_cost_delta_a", 0) or 0)
            new_delta = max(-base_cost, cur_delta - reduction)
            st.battle_cost_delta_a = new_delta
            new_cost = max(0, base_cost + new_delta)
            self.engine._log_event(
                run,
                locale_text(
                    "i18n_prism.card.cost_reduce_log",
                    params={
                        "trigger_label": trigger_label,
                        "amount": reduction,
                        "cost_a": new_cost,
                    },
                ),
            )

    def on_battle_win(self, event: BattleWinEvent):
        run = event.run
        p = run.player
        if p is None or getattr(p, "is_mercenary", False):
            return
        if run.node_data.get("is_town_combat") or is_tutorial_run(run):
            return
        if not _player_has_prism(p):
            return
        sm = getattr(self.engine, "save_manager", None)
        uid = run.uid_for(p) or run.user_id
        if sm is None or not uid:
            return
        stats = sm.load_stats(uid)
        triggered = bool(run.node_data.get(self._battle_flag_key(run, p), False))
        if triggered:
            stats.town_flags[ULTIMATE_PRISM_FLAG_IDLE_BATTLES] = 0
            sm.save_stats(uid, stats)
            return
        idle = int(stats.town_flags.get(ULTIMATE_PRISM_FLAG_IDLE_BATTLES, 0) or 0) + 1
        leave_limit = int(ULTIMATE_PRISM_CONFIG["idle_leave_battles"])
        if idle >= leave_limit:
            _remove_all_prism_from_player(p)
            if ULTIMATE_PRISM_CARD_ID in stats.locked_cards:
                stats.locked_cards = [c for c in stats.locked_cards if c != ULTIMATE_PRISM_CARD_ID]
            if ULTIMATE_PRISM_MERC_ID in stats.hired_mercenaries:
                stats.hired_mercenaries = [m for m in stats.hired_mercenaries if m != ULTIMATE_PRISM_MERC_ID]
            stats.town_flags[ULTIMATE_PRISM_FLAG_DEPARTED] = True
            stats.town_flags[ULTIMATE_PRISM_FLAG_IDLE_BATTLES] = 0
            ok, _ = add_bag_item(p, GLASS_SHARD_ITEM_ID)
            if not ok:
                if not hasattr(p, "bag_items") or p.bag_items is None:
                    p.bag_items = []
                p.bag_items.append(GLASS_SHARD_ITEM_ID)
            notice_text = render_text_node(locale_text("i18n_prism.departure.left_notice"))
            if notice_text not in stats.pending_logs:
                stats.pending_logs.append(notice_text)
            sm.save_stats(uid, stats)
            add_notice(run, uid, notice_text)
        else:
            stats.town_flags[ULTIMATE_PRISM_FLAG_IDLE_BATTLES] = idle
            sm.save_stats(uid, stats)
