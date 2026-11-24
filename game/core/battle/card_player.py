import copy
import random
from typing import Optional
from ...models.state import GameRun, PlayerState
from .card_player_rewards import CardPlayerRewardsMixin
from .card_player_turn import CardPlayerTurnMixin
from .card_player_minion import CardPlayerMinionMixin
from .card_cost import resolve_card_effective_cost_a, resolve_card_effective_cost_ba
from .selection.target_rules import normalize_default_target, validate_target
from .selection import TargetSelectorParser, start_card_selection
from ..inventory.deck_service import DeckService
from ...data.text.locale_data import get_locale_text
from ...data.entities.minions.minion_data import MINION_CONFIG
from ...data.entities.gem_data import GEM_CONFIG

from ...entities import ALL_CARDS, ALL_MINIONS
from ...models.events import (
    CardPlayEvent, CardPlayedEvent, CardExhaustEvent, CardDiscardEvent,
    CardCostCalculateEvent, CardDrawnEvent,
)

def _cancelled_card_message(play_evt, card) -> str:
    return play_evt.cancel_message or get_locale_text("i18n_battle_core.spacetime_distortion", name=card.name)


def _clone_card_state(state):
    clone = copy.copy(state)
    if getattr(clone, "gems", None) is not None:
        clone.gems = list(clone.gems)
    if getattr(clone, "enchantments", None) is not None:
        clone.enchantments = list(clone.enchantments)
    if getattr(clone, "tags", None) is not None:
        clone.tags = [copy.copy(tag) for tag in clone.tags]
    return clone


class CardPlayer(CardPlayerMinionMixin, CardPlayerTurnMixin, CardPlayerRewardsMixin):
    def __init__(self, engine):
        self.engine = engine

    def _handle_card_post_play(self, run, card, c_state, source="played"):
        p = run.player
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(c_state)
        clean_state = _clone_card_state(c_state)
        clean_state.return_left = 0
        clean_state.temp_cost_a = None
        clean_state.temp_cost_ba = None
        clean_state.temp_ethereal = False

        if hasattr(card, "handle_post_play") and card.handle_post_play(run, c_state, source, self.engine):
            return
        removed_by_fleeting = False
        if getattr(card, "fleeting", False):
            fleeting_total = int(getattr(card, "fleeting_total", 1) or 1)
            next_fleeting_used = int(getattr(clean_state, "fleeting_used", 0) or 0) + 1
            match_state = _clone_card_state(clean_state)
            match_state.replay = 0
            match_state.fragile = 0
            found = None
            for dc in p.deck:
                if (dc.id == match_state.id and
                    dc.upgraded == match_state.upgraded and
                    dc.gems == match_state.gems and
                    dc.fleeting_used == match_state.fleeting_used):
                    found = dc
                    break
            if not found:
                for dc in p.deck:
                    if (dc.id == match_state.id and
                        dc.upgraded == match_state.upgraded and
                        dc.gems == match_state.gems):
                        found = dc
                        break
            if next_fleeting_used >= fleeting_total:
                if found:
                    p.deck.remove(found)
                self.engine._log_event(run, get_locale_text("i18n_battle_core.fleeting_remove_log", name=card.name))
                removed_by_fleeting = True
            else:
                clean_state.fleeting_used = next_fleeting_used
                if found:
                    found.fleeting_used = next_fleeting_used
                remaining = fleeting_total - next_fleeting_used
                self.engine._log_event(run, get_locale_text("i18n_battle_core.fleeting_wear_log", name=card.name, remaining=remaining))
        if not removed_by_fleeting:
            from ...models.events import CardPostPlayRouteEvent
            route_evt = CardPostPlayRouteEvent(run, p, card, clean_state, source)
            self.engine.event_bus.dispatch(route_evt)
            if route_evt.handled:
                destination = route_evt.destination
                if destination == "exhaust":
                    p.exhaust_pile.append(clean_state)
                    log_key = route_evt.log_key or "i18n_battle_core.exhaust_card_log"
                    self.engine._log_event(run, get_locale_text(log_key, name=card.name))
                    exhaust_evt = CardExhaustEvent(run, clean_state, source)
                    self.engine.event_bus.dispatch(exhaust_evt)
                elif destination == "hand":
                    p.hand.append(clean_state)
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.card_route_hand_log", name=card.name))
                elif destination == "draw":
                    p.draw_pile.insert(0, clean_state)
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.card_route_draw_log", name=card.name))
                elif destination == "remove":
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.card_route_remove_log", name=card.name))
                else:
                    p.discard_pile.append(clean_state)
            elif card.type in ("minion", "amulet"):
                if card.type == "minion":
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.minion_enter_log", name=card.name))
                else:
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.amulet_deploy_log", name=card.name))
                exhaust_evt = CardExhaustEvent(run, clean_state, source)
                self.engine.event_bus.dispatch(exhaust_evt)
            elif getattr(card, "exhaust", False) or getattr(clean_state, "temp_exhaust", False):
                exhaust_total = int(getattr(card, "exhaust_total", 1) or 1)
                next_exhaust_used = int(getattr(clean_state, "exhaust_used", 0) or 0) + 1
                clean_state.exhaust_used = next_exhaust_used
                if next_exhaust_used >= exhaust_total:
                    p.exhaust_pile.append(clean_state)
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.exhaust_card_log", name=card.name))
                    exhaust_evt = CardExhaustEvent(run, clean_state, source)
                    self.engine.event_bus.dispatch(exhaust_evt)
                else:
                    p.discard_pile.append(clean_state)
                    remaining = exhaust_total - next_exhaust_used
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.exhaust_wear_log", name=card.name, remaining=remaining))
            else:
                p.discard_pile.append(clean_state)

    def _finalize_card_play(self, run, p, card, c_state, target, res, source="played", register=True, allow_return=True) -> tuple[str, bool]:
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(c_state)
        return_clone = DeckService.clone_state(c_state)
        card.execute_tags(run, target, self.engine)

        returned = False
        return_left = c_state.return_left
        if return_left <= 0:
            return_left = max(
                (int(GEM_CONFIG.get(gem_id, {}).get("return_count", 0) or 0) for gem_id in (getattr(card, "gems", None) or [])),
                default=0,
            )
        if allow_return and return_left > 0 and return_left - 1 > 0:
            return_clone.return_left = return_left - 1
            DeckService.add_card_to_hand(p, return_clone)
            returned = True
            res += get_locale_text("i18n_battle_core.card_return_log", name=card.name, count=return_left - 1)
        else:
            self._handle_card_post_play(run, card, c_state, source=source)

        copy_count = 0
        if not c_state.no_copy:
            if getattr(card, "copy", 0) > 0:
                copy_count = card.copy
            for gem_id in (getattr(card, "gems", None) or []):
                copy_count = max(copy_count, int(GEM_CONFIG.get(gem_id, {}).get("copy_count", 0) or 0))
        if copy_count > 0:
            max_hand = self.engine.get_max_hand_size(run, p)
            added = 0
            for _ in range(copy_count):
                if len(p.hand) < max_hand:
                    copy_cid = DeckService.clone_state(c_state)
                    copy_cid.no_copy = True
                    p.hand.append(copy_cid)
                    added += 1
            if added > 0:
                res += get_locale_text("i18n_battle_core.card_copy_log", name=card.name, count=added)

        from ...models.events import CardPostPlayEvent
        prev_alive = int(run.node_data.get("pre_play_alive_enemies", sum(1 for e in run.enemies if e.hp > 0)))
        self.engine.event_bus.dispatch(CardPostPlayEvent(run, card, c_state, target, prev_alive))
        from ..audio import get_audio_pipeline
        actor_uid = run.uid_for(p) or run.user_id
        if actor_uid:
            get_audio_pipeline().emit_card_play(actor_uid, card.id)

        res = self._collapse_extra_play_msgs(run, res)

        played_evt = CardPlayedEvent(run, card, target, res)
        self.engine.event_bus.dispatch(played_evt)
        res = played_evt.feedback
        res = self._collapse_extra_play_msgs(run, res)
        if register:
            self.engine._register_card_played(run)
        return res, returned

    def _collapse_extra_play_msgs(self, run, res):
        extra_msgs = run.node_data.pop("extra_play_msgs", [])
        if len(extra_msgs) > 10:
            return res + get_locale_text("i18n_battle_core.extra_play_count", count=len(extra_msgs))
        return res + "".join(extra_msgs)

    def _post_battle_action_check(self, run, initial_status, res, p) -> str:
        has_damaged = False
        for idx, e in enumerate(run.enemies):
            if idx < len(initial_status):
                old_hp, old_shield = initial_status[idx]
                if e.hp < old_hp or e.shield < old_shield:
                    has_damaged = True
                    break
        from .extra_turn_service import clear_active, consume_force_end_request, is_arhat_active, request_force_end, should_break_on_damage
        actor_uid = run.uid_for(p) or run.user_id
        force_end = consume_force_end_request(run, p)
        if has_damaged and not force_end and should_break_on_damage(run, actor_uid):
            from .pvp_service import PvpService, is_pvp_run
            if is_pvp_run(run):
                opponent_dead = not run.enemies or run.enemies[0].hp <= 0
                if p.hp > 0 and not opponent_dead:
                    extra_res = PvpService.consume_extra_turn(
                        self.engine.save_manager,
                        self.engine,
                        run,
                        actor_uid,
                    )
                    res += get_locale_text("i18n_battle_core.time_stop_extra_end_log", end_turn_res=extra_res)
            else:
                clear_active(run, actor_uid)
                end_turn_res = self.end_turn(run)
                res += get_locale_text("i18n_battle_core.time_stop_extra_end_log", end_turn_res=end_turn_res)
        if force_end and not self.engine.is_battle_won(run) and p.hp > 0:
            if is_arhat_active(run, actor_uid):
                request_force_end(run, p, "arhat")
            else:
                res += "\n" + self.end_turn(run)
        self._reindex_minions(p)
        return res

    def play_card(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return get_locale_text("i18n_battle_core.not_in_battle_card")
        if p.downed:
            return get_locale_text("i18n_battle_core.downed_cannot_play")
        if hand_idx < 1 or hand_idx > len(p.hand):
            return get_locale_text("i18n_battle_core.invalid_hand_index")
        from ...models.state import ensure_card_state
        cid = ensure_card_state(p.hand[hand_idx - 1])
        p.hand[hand_idx - 1] = cid
        card = ALL_CARDS.get(cid)
        if not card:
            return get_locale_text("i18n_battle_core.card_not_found")
        if getattr(card, "unplayable", False):
            return get_locale_text("i18n_battle_core.card_unplayable")
        base_id = card.id
        is_coop_card = bool(getattr(card, "coop_only", False))
        is_any_other = getattr(card, "target_type", "enemy") == "any_other"
        is_self_spell = getattr(card, "target_type", "enemy") == "self"

        if card.type in ("minion", "amulet") and self.engine._get_free_grid(p) is None:
            return get_locale_text("i18n_battle_core.battlefield_full")

        from ...models.events import CardPlayCheckEvent
        check_evt = CardPlayCheckEvent(run, p, card, cid, target)
        self.engine.event_bus.dispatch(check_evt)
        if check_evt.cancelled:
            return check_evt.error_message
        req_a = resolve_card_effective_cost_a(card, cid, p)
        req_ba = resolve_card_effective_cost_ba(card, cid, p)
        real_x_a = 0
        real_x_ba = 0
        if req_a == -1:
            real_x_a = p.actions
            req_a = p.actions
        if req_ba == -1:
            real_x_ba = p.bonus_actions
            req_ba = p.bonus_actions
        cost_evt = CardCostCalculateEvent(run, p, card, cid, req_a, req_ba)
        self.engine.event_bus.dispatch(cost_evt)
        req_a = cost_evt.cost_a
        req_ba = cost_evt.cost_ba
        real_x_a += cost_evt.x_bonus_a
        real_x_ba += cost_evt.x_bonus_ba
        run.node_data["last_x_cost_a"] = real_x_a
        run.node_data["last_x_cost_ba"] = real_x_ba

        selection_spec = card.get_selection_spec(run, self.engine)
        if selection_spec is not None:
            return start_card_selection(self, run, card, cid, hand_idx, target, req_a, req_ba, selection_spec)

        if is_coop_card:
            target = normalize_default_target(run, card, base_id, target)
        if target is not None:
            resolved_target, resolve_err = TargetSelectorParser.resolve_simple_target(
                run,
                target,
                is_self_spell=is_self_spell,
                is_coop_card=is_coop_card,
                is_any_other=is_any_other,
                engine=self.engine,
            )
            if resolve_err:
                return resolve_err
            target = resolved_target
        if is_coop_card:
            error = validate_target(self.engine, run, card, base_id, target)
            if error:
                return error

        if target is None and not is_coop_card and not is_any_other:
            if card.type == "spell":
                if is_self_spell:
                    target = "p0"
                else:
                    target = self.engine._get_first_alive_enemy(run)

        if target is not None:
            if target.lower().startswith("a"):
                resolved = self.engine.combat_resolver.resolve_ally(run, target)
                if is_coop_card or is_any_other:
                    if not resolved:
                        return get_locale_text("i18n_battle_misc.coop_ally_not_found", target=target)
                elif is_self_spell and resolved and resolved[0] == run.uid_for(p):
                    if resolved[2] is not None and resolved[2] not in p.minions:
                        return get_locale_text("i18n_battle_core.own_grid_empty", grid=resolved[2])
                    target = "p0" if resolved[2] is None else f"p{resolved[2]}"
                else:
                    return get_locale_text("i18n_battle_core.invalid_target")
            elif target.startswith("e"):
                try:
                    grid = int(target[1:]) - 1
                except ValueError:
                    grid = 0
                if grid < 0 or grid >= len(run.enemies):
                    return get_locale_text("i18n_battle_core.enemy_grid_empty", target=target)
            elif target == "p0":
                pass
            elif target.startswith("p"):
                grid = target[1:]
                if grid not in p.minions:
                    return get_locale_text("i18n_battle_core.own_grid_empty", grid=grid)
            else:
                return get_locale_text("i18n_battle_core.invalid_target")

        play_err = card.can_play_error(run, target, self.engine)
        if play_err:
            return play_err

        run.node_data["current_playing_card_hand_idx"] = hand_idx - 1
        play_evt = CardPlayEvent(run, card, target, req_a, req_ba)
        self.engine.event_bus.dispatch(play_evt)
        if play_evt.cancelled:
            run.node_data.pop("current_playing_card_hand_idx", None)
            run.node_data.pop("prism_pending_refracts", None)
            return _cancelled_card_message(play_evt, card)
        req_a = play_evt.cost_a
        req_ba = play_evt.cost_ba
        target = play_evt.target
        if p.actions < req_a or p.bonus_actions < req_ba:
            run.node_data.pop("current_playing_card_hand_idx", None)
            run.node_data.pop("prism_pending_refracts", None)
            return get_locale_text("i18n_battle_core.insufficient_actions", req_a=req_a, req_ba=req_ba, actions=p.actions, bonus_actions=p.bonus_actions)
        if card.cost_a == -1:
            real_x_a = req_a + cost_evt.x_bonus_a
        if card.cost_ba == -1:
            real_x_ba = req_ba + cost_evt.x_bonus_ba
        run.node_data["last_x_cost_a"] = real_x_a
        run.node_data["last_x_cost_ba"] = real_x_ba
        p.actions -= req_a
        p.bonus_actions -= req_ba
        p.hand.pop(hand_idx - 1)
        

        initial_stack_len = len(run.node_data.get("state_stack", []))
        run.node_data["current_playing_card_cid"] = cid
        run.node_data["current_playing_card_hand_idx"] = hand_idx - 1
        run.node_data["current_playing_card_id"] = card.id
        run.node_data["extra_play_msgs"] = []
        run.node_data["pre_play_alive_enemies"] = sum(1 for e in run.enemies if e.hp > 0)
        try:
            res = self.engine._execute_card_effect(run, card, target)

            suspend_post_play = False
            if len(run.node_data.get("state_stack", [])) > initial_stack_len:
                suspend_post_play = True
                run.node_data["suspended_card_cid"] = cid
                run.node_data["suspended_card_cost_a"] = req_a
                run.node_data["suspended_card_cost_ba"] = req_ba
                run.node_data["suspended_card_hand_idx"] = hand_idx - 1

            if not suspend_post_play:
                res, _ = self._finalize_card_play(run, p, card, cid, target, res, source="played", register=True)
                if run.node_data.get("pending_extra_plays"):
                    from .selection.extra_play_flow import drain_pending_extra_plays
                    res, suspended_extra = drain_pending_extra_plays(self, run, res)
                    if suspended_extra:
                        suspend_post_play = True
        finally:
            run.node_data["current_playing_card_id"] = ""
            run.node_data["current_playing_card_cid"] = ""
            run.node_data.pop("current_playing_card_hand_idx", None)

        if suspend_post_play:
            self.engine.save_manager.save_save(run.user_id, run)
            return self.engine._append_logs_to_res(run, res)
        self.engine.save_manager.save_save(run.user_id, run)
        res = self._post_battle_action_check(run, initial_status, res, p)
        return self.engine._append_logs_to_res(run, res)

    def play_special_action(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return get_locale_text("i18n_battle_core.not_in_battle_special")
        if p.downed:
            return get_locale_text("i18n_battle_core.downed_cannot_act")
        if hand_idx < 1 or hand_idx > len(p.hand):
            return get_locale_text("i18n_battle_core.invalid_hand_index")
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(p.hand[hand_idx - 1])
        p.hand[hand_idx - 1] = c_state
        card = ALL_CARDS.get(c_state)
        if not card:
            return get_locale_text("i18n_battle_core.card_not_found")
        if getattr(card, "unplayable", False):
            return get_locale_text("i18n_battle_core.card_unplayable")

        req_a = resolve_card_effective_cost_a(card, c_state, p)
        req_ba = resolve_card_effective_cost_ba(card, c_state, p)
        real_x_a = 0
        real_x_ba = 0
        if req_a == -1:
            real_x_a = p.actions
            req_a = p.actions
        if req_ba == -1:
            real_x_ba = p.bonus_actions
            req_ba = p.bonus_actions

        cost_evt = CardCostCalculateEvent(run, p, card, c_state, req_a, req_ba)
        self.engine.event_bus.dispatch(cost_evt)
        req_a = cost_evt.cost_a
        req_ba = cost_evt.cost_ba
        real_x_a += cost_evt.x_bonus_a
        real_x_ba += cost_evt.x_bonus_ba

        run.node_data["last_x_cost_a"] = real_x_a
        run.node_data["last_x_cost_ba"] = real_x_ba

        if target is None:
            if getattr(card, "target_type", "enemy") == "self":
                target = "p0"
            else:
                target = self.engine._get_first_alive_enemy(run)
        if target == "0" or target == "e0":
            target = "e1"
        elif target == "p":
            target = "p0"

        play_evt = CardPlayEvent(run, card, target, req_a, req_ba)
        self.engine.event_bus.dispatch(play_evt)
        if play_evt.cancelled:
            return _cancelled_card_message(play_evt, card)
        req_a = play_evt.cost_a
        req_ba = play_evt.cost_ba
        target = play_evt.target

        if p.actions < req_a or p.bonus_actions < req_ba:
            return get_locale_text("i18n_battle_core.insufficient_actions", req_a=req_a, req_ba=req_ba, actions=p.actions, bonus_actions=p.bonus_actions)
        p.actions -= req_a
        p.bonus_actions -= req_ba
        p.hand.pop(hand_idx - 1)
        run.node_data["current_playing_card_cid"] = c_state
        run.node_data["current_playing_card_id"] = card.id
        try:
            res = card.special_action(run, target)
            res, _ = self._finalize_card_play(run, p, card, c_state, target, res, source="special", register=True)
        finally:
            run.node_data["current_playing_card_id"] = ""
            run.node_data["current_playing_card_cid"] = ""
        self.engine.save_manager.save_save(run.user_id, run)
        res = self._post_battle_action_check(run, initial_status, res, p)
        return self.engine._append_logs_to_res(run, res)
