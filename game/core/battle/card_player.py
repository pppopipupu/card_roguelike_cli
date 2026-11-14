import copy
import random
from typing import Optional
from ...models.state import GameRun, PlayerState
from .card_player_rewards import CardPlayerRewardsMixin
from .card_player_turn import CardPlayerTurnMixin
from .coop_targeting import validate_coop_target, normalize_coop_target
from ..inventory.deck_service import DeckService
from ...data.locale_data import get_locale_text
from ...data.buff_data import BUFF_CONFIG
from ...data.gem_data import GEM_CONFIG
from ...data.minion_data import MINION_CONFIG

from ...entities import ALL_CARDS, ALL_MINIONS
from ...models.events import (
    CardPlayEvent, CardPlayedEvent, CardExhaustEvent, CardDiscardEvent
)

def _clone_card_state(state):
    clone = copy.copy(state)
    if getattr(clone, "gems", None) is not None:
        clone.gems = list(clone.gems)
    if getattr(clone, "tags", None) is not None:
        clone.tags = [copy.copy(tag) for tag in clone.tags]
    return clone


class CardPlayer(CardPlayerTurnMixin, CardPlayerRewardsMixin):
    def __init__(self, engine):
        self.engine = engine

    def _handle_card_post_play(self, run, card, c_state, source="played"):
        p = run.player
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(c_state)
        clean_state = _clone_card_state(c_state)
        clean_state.return_left = 0

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
            if any(b.id == "void_exhaustion" for b in p.buffs):
                p.exhaust_pile.append(clean_state)
                self.engine._log_event(run, get_locale_text("i18n_battle_core.void_exhaust_log", name=card.name))
                exhaust_evt = CardExhaustEvent(run, clean_state, source)
                self.engine.event_bus.dispatch(exhaust_evt)
            elif card.type in ("minion", "amulet"):
                if card.type == "minion":
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.minion_enter_log", name=card.name))
                else:
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.amulet_deploy_log", name=card.name))
                exhaust_evt = CardExhaustEvent(run, clean_state, source)
                self.engine.event_bus.dispatch(exhaust_evt)
            elif getattr(card, "exhaust", False):
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
        if return_left <= 0 and getattr(card, "gems", None):
            if "gem_return_5" in card.gems:
                return_left = 5
            elif "gem_return_3" in card.gems:
                return_left = 3
        if allow_return and return_left > 0 and return_left - 1 > 0:
            return_clone.return_left = return_left - 1
            DeckService.add_card_to_hand(p, return_clone)
            returned = True
            res += get_locale_text("i18n_battle_core.card_return_log", name=card.name, count=return_left - 1)
        else:
            self._handle_card_post_play(run, card, c_state, source=source)

        gems = getattr(card, "gems", None) or []
        if gems:
            if any(g in gems for g in ("gem_shield_add_3", "gem_shield_add_8")) and not run.node_data.get("card_played_triggered_shield", False):
                self.engine.combat_resolver.gain_shield(run, "p0", 0)
            if "gem_heal_add_2" in gems and not run.node_data.get("card_played_triggered_heal", False):
                self.engine.combat_resolver.heal_target(run, "p0", 0)
            if "gem_dmg_add_2" in gems and not run.node_data.get("card_played_triggered_dmg", False):
                dmg_target = target
                if not dmg_target or not dmg_target.startswith("e"):
                    dmg_target = self.engine._get_first_alive_enemy(run)
                if dmg_target and dmg_target != "0" and dmg_target != "e0":
                    self.engine.combat_resolver.damage_target(run, dmg_target, 0, source="p0", damage_type="effect")

            for g in gems:
                if g == "gem_gain_a_1":
                    p.actions += 1
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_gain_a_log"))
                elif g == "gem_gain_a_1_ba_1":
                    p.actions += 1
                    p.bonus_actions += 1
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_gain_a_ba_log"))
                elif g == "gem_burn_gold":
                    gp_gain = GEM_CONFIG.get("gem_burn_gold", {}).get("gp_gain", 5)
                    uid = getattr(p, "mercenary_owner", "") if getattr(p, "is_mercenary", False) else (run.uid_for(p) or run.user_id)
                    if uid and hasattr(self.engine, "save_manager") and self.engine.save_manager:
                        stats = self.engine.save_manager.load_stats(uid)
                        stats.gp = int(getattr(stats, "gp", 0) or 0) + gp_gain
                        self.engine.save_manager.save_stats(uid, stats)
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_burn_gold_log", gp=gp_gain))
                elif g in ("gem_vuln_1", "gem_weak_2"):
                    buff_target = target
                    if not buff_target or not buff_target.startswith("e"):
                        buff_target = self.engine._get_first_alive_enemy(run)
                    if buff_target and buff_target.startswith("e"):
                        try:
                            idx = int(buff_target[1:]) - 1
                            if idx < 0: idx = 0
                        except ValueError:
                            idx = 0
                        if idx < len(run.enemies):
                            if g == "gem_vuln_1":
                                self.engine.combat_resolver.add_buff_to(run.enemies[idx], "vulnerable", get_locale_text("i18n_battle_core.buff_vulnerable_name"), get_locale_text("i18n_battle_core.buff_vulnerable_desc"), 1)
                                self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_vulnerable_log", name=run.enemies[idx].name))
                            else:
                                self.engine.combat_resolver.add_buff_to(run.enemies[idx], "weak", get_locale_text("i18n_battle_core.buff_weak_name"), get_locale_text("i18n_battle_core.buff_weak_desc"), 2)
                                self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_weak_log", name=run.enemies[idx].name))

        copy_count = 0
        if not c_state.no_copy:
            if getattr(card, "copy", 0) > 0:
                copy_count = card.copy
            if "gem_copy_1" in gems:
                copy_count = max(copy_count, 1)
        if copy_count > 0:
            max_hand = 9 if "mask_of_void" in p.relics else 12
            added = 0
            for _ in range(copy_count):
                if len(p.hand) < max_hand:
                    copy_cid = DeckService.clone_state(c_state)
                    copy_cid.gems = [g for g in copy_cid.gems if g != "gem_copy_1"]
                    copy_cid.no_copy = True
                    p.hand.append(copy_cid)
                    added += 1
            if added > 0:
                res += get_locale_text("i18n_battle_core.card_copy_log", name=card.name, count=added)

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
        if has_damaged and run.node_data.get("extra_turns_left", 0) > 0:
            end_turn_res = self.end_turn(run)
            res += get_locale_text("i18n_battle_core.time_stop_extra_end_log", end_turn_res=end_turn_res)
        if run.node_data.pop("force_end_turn", False):
            run.node_data.pop("force_end_turn_uid", None)
            if not self.engine.is_battle_won(run) and p.hp > 0:
                res += "\n" + self.end_turn(run)
        self._reindex_minions(p)
        return res

    def draw_cards(self, p: PlayerState, count: int, run: Optional[GameRun] = None, ignore_focus: bool = False, depth: int = 0):
        if not ignore_focus and any(b.id == "tactical_focus" for b in p.buffs):
            if run is not None:
                self.engine._log_event(run, get_locale_text("i18n_battle_core.cannot_draw_log"))
            return
        max_hand = 9 if "mask_of_void" in p.relics else 12
        hell_raider_cfg = BUFF_CONFIG.get("hell_raider", {})
        chain_limit = hell_raider_cfg.get("chain_depth", 5)
        upgraded_draw_count = hell_raider_cfg.get("upgraded_draw_count", 1)
        drawn_cards = []
        reshuffled = False
        hand_full_logged = False
        for _ in range(count):
            if not p.draw_pile:
                if p.discard_pile:
                    p.draw_pile = p.discard_pile.copy()
                    random.shuffle(p.draw_pile)
                    p.discard_pile.clear()
                    reshuffled = True
            if p.draw_pile:
                cid = p.draw_pile.pop()
                is_hell_raider = any(b.id == "hell_raider" for b in p.buffs)
                is_hell_raider_upg = any(b.id == "hell_raider_upgraded" for b in p.buffs)
                if run is not None and (is_hell_raider or is_hell_raider_upg):
                    chain = getattr(run, "_hell_raider_chain", 0)
                    card_obj = ALL_CARDS.get(cid)
                    cost_a_limit = 2 if is_hell_raider_upg else 1
                    if chain < chain_limit and card_obj and getattr(card_obj, "cost_a", 0) <= cost_a_limit and getattr(card_obj, "cost_ba", 0) == 0:
                        buff_prefix = get_locale_text("i18n_battle_core.hell_raider_upgraded_name") if is_hell_raider_upg else get_locale_text("i18n_battle_core.hell_raider_name")
                        self.engine._log_event(run, get_locale_text("i18n_battle_core.hell_raider_auto_play_log", buff_prefix=buff_prefix, cost_a=getattr(card_obj, 'cost_a', 0), name=card_obj.name))
                        target = "p0"
                        if card_obj.type == "spell" and getattr(card_obj, "target_type", "enemy") != "self":
                            target = self.engine._get_first_alive_enemy(run)
                        elif card_obj.type == "minion" or card_obj.type == "amulet":
                            target = self.engine._get_free_grid(run.player)
                            if not target:
                                target = "p1"
                        run._hell_raider_chain = chain + 1
                        try:
                            res_action = self.engine._execute_card_effect(run, card_obj, target)
                            res_action, _ = self._finalize_card_play(run, p, card_obj, cid, target, res_action, source="hell_raider", register=False)
                            self.engine._log_event(run, get_locale_text("i18n_battle_core.hell_raider_feedback_log", feedback=res_action))
                            if is_hell_raider_upg and depth < chain_limit:
                                self.engine._log_event(run, get_locale_text("i18n_battle_core.hell_raider_extra_draw_log"))
                                self.draw_cards(p, upgraded_draw_count, run, depth=depth+1)
                        finally:
                            run._hell_raider_chain = chain
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
        if "mindflayer_brain" in p.relics:
            alive = [e for e in run.enemies if e.hp > 0]
            if alive:
                import random
                target_enemy = random.choice(alive)
                idx = run.enemies.index(target_enemy) + 1
                self.engine._log_event(run, get_locale_text("i18n_battle_core.mindflayer_brain_log", name=target_enemy.name))
                self.engine.combat_resolver.damage_target(run, f"e{idx}", 3, source="relic:mindflayer_brain", damage_type="psychic")
        if not card:
            p.discard_pile.append(c_state)
            return self.engine._append_logs_to_res(run, "")
        if getattr(card, "agile", False):
            target = None
            if card.type == "spell":
                if getattr(card, "target_type", "enemy") == "self":
                    target = "p0"
                else:
                    target = self.engine._get_first_alive_enemy(run)
                if target == "0" or target == "e0":
                    target = "e1"
            run.node_data["extra_play_msgs"] = []
            res = self.engine._execute_card_effect(run, card, target)
            res, _ = self._finalize_card_play(run, p, card, c_state, target, res, source="agile", register=False)
            self._reindex_minions(p)
            return self.engine._append_logs_to_res(run, get_locale_text("i18n_battle_core.agile_discard_log", name=card.name, effect=res))
        else:
            p.discard_pile.append(c_state)
            self._reindex_minions(p)
            return self.engine._append_logs_to_res(run, "")

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
        is_discover = base_id == "discover"
        is_emperor_eye = base_id.startswith("neutral_emperor_eye")
        is_coop_card = bool(getattr(card, "coop_only", False))
        is_any_other = getattr(card, "target_type", "enemy") == "any_other"
        if is_coop_card:
            target = normalize_coop_target(run, card, base_id, target)
        if is_coop_card:
            error = validate_coop_target(self.engine, run, card, base_id, target)
            if error:
                return error
        if not is_discover:
            if target is None:
                if is_emperor_eye or is_coop_card or base_id.startswith("curse_shou_hui"):
                    pass
                elif card.type == "spell":
                    if getattr(card, "target_type", "enemy") == "self":
                        target = "p0"
                    else:
                        target = self.engine._get_first_alive_enemy(run)

            if target is not None:
                if is_emperor_eye:
                    pass
                else:
                    if isinstance(target, str) and target.isdigit():
                        target = f"e{target}"
                    if target == "0" or target == "e0":
                        target = "e1"
                    elif target == "p":
                        target = "p0"
                    if target.lower().startswith("a"):
                        resolved = self.engine.combat_resolver.resolve_ally(run, target)
                        if is_coop_card or is_any_other:
                            if not resolved:
                                return get_locale_text("i18n_battle_misc.coop_ally_not_found", target=target)
                        elif getattr(card, "target_type", "enemy") == "self" and resolved and resolved[0] == run.uid_for(p):
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
        if card.type in ("minion", "amulet") and self.engine._get_free_grid(p) is None:
            return get_locale_text("i18n_battle_core.battlefield_full")
        play_err = card.can_play_error(run, target, self.engine)
        if play_err:
            return play_err
        
        req_a = card.cost_a
        req_ba = card.cost_ba
        real_x_a = 0
        real_x_ba = 0
        if req_a == -1:
            real_x_a = p.actions
            req_a = p.actions
        if req_ba == -1:
            real_x_ba = p.bonus_actions
            req_ba = p.bonus_actions

        if "chemical_x" in p.relics:
            if card.cost_a == -1:
                real_x_a += 2
            if card.cost_ba == -1:
                real_x_ba += 2

        run.node_data["last_x_cost_a"] = real_x_a
        run.node_data["last_x_cost_ba"] = real_x_ba

        play_evt = CardPlayEvent(run, card, target, req_a, req_ba)
        self.engine.event_bus.dispatch(play_evt)
        if play_evt.cancelled:
            return get_locale_text("i18n_battle_core.spacetime_distortion", name=card.name)
        req_a = play_evt.cost_a
        req_ba = play_evt.cost_ba
        target = play_evt.target
        if p.actions < req_a or p.bonus_actions < req_ba:
            return get_locale_text("i18n_battle_core.insufficient_actions", req_a=req_a, req_ba=req_ba, actions=p.actions, bonus_actions=p.bonus_actions)
        chemical_bonus = 2 if "chemical_x" in p.relics else 0
        if card.cost_a == -1:
            real_x_a = req_a + chemical_bonus
        if card.cost_ba == -1:
            real_x_ba = req_ba + chemical_bonus
        run.node_data["last_x_cost_a"] = real_x_a
        run.node_data["last_x_cost_ba"] = real_x_ba
        p.actions -= req_a
        p.bonus_actions -= req_ba
        p.hand.pop(hand_idx - 1)
        
        split_to_ten_active = False
        split_to_ten_buff = next((b for b in p.buffs if b.id == "split_to_ten"), None)
        if split_to_ten_buff and split_to_ten_buff.stacks > 0:
            split_to_ten_active = True
            split_to_ten_buff.stacks -= 1
            if split_to_ten_buff.stacks <= 0:
                p.buffs.remove(split_to_ten_buff)
        run.node_data["split_to_ten_active"] = split_to_ten_active
        
        initial_stack_len = len(run.node_data.get("state_stack", []))
        run.node_data["current_playing_card_cid"] = cid
        run.node_data["current_playing_card_hand_idx"] = hand_idx - 1
        run.node_data["card_played_triggered_dmg"] = False
        run.node_data["card_played_triggered_shield"] = False
        run.node_data["card_played_triggered_heal"] = False
        run.node_data["current_playing_card_id"] = card.id
        run.node_data["extra_play_msgs"] = []
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
        finally:
            run.node_data["current_playing_card_id"] = ""
            run.node_data["current_playing_card_cid"] = ""
            run.node_data.pop("current_playing_card_hand_idx", None)
            run.node_data.pop("split_to_ten_active", None)

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
            return get_locale_text("i18n_battle_core.invalid_hand_index")
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(p.hand[hand_idx - 1])
        p.hand[hand_idx - 1] = c_state
        card = ALL_CARDS.get(c_state)
        if not card:
            return get_locale_text("i18n_battle_core.card_not_found")
        if getattr(card, "unplayable", False):
            return get_locale_text("i18n_battle_core.card_unplayable")

        req_a = card.cost_a
        req_ba = card.cost_ba
        real_x_a = 0
        real_x_ba = 0
        if req_a == -1:
            real_x_a = p.actions
            req_a = p.actions
        if req_ba == -1:
            real_x_ba = p.bonus_actions
            req_ba = p.bonus_actions

        if "chemical_x" in p.relics:
            if card.cost_a == -1:
                real_x_a += 2
            if card.cost_ba == -1:
                real_x_ba += 2

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
            return get_locale_text("i18n_battle_core.spacetime_distortion", name=card.name)
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

    def minion_attack(self, run: GameRun, my_grid: str, opp_grid: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return get_locale_text("i18n_battle_core.not_in_battle_minion_attack")
        if p.downed:
            return get_locale_text("i18n_battle_core.downed_cannot_command")
            return get_locale_text("i18n_battle_core.own_grid_empty", grid=my_grid)
        m = p.minions[my_grid]
        if m.attack_actions < 1:
            return get_locale_text("i18n_battle_core.minion_no_attack_actions")
        if opp_grid is None:
            opp_grid = self.engine._get_first_alive_enemy(run)
        m.attack_actions -= 1
        try:
            opp_idx = int(opp_grid.replace("e", "")) - 1
            if opp_idx < 0:
                opp_idx = 0
        except ValueError:
            opp_idx = 0
        if opp_idx < 0 or opp_idx >= len(run.enemies):
            return get_locale_text("i18n_battle_core.enemy_grid_invalid", target=opp_grid)
        enemy = run.enemies[opp_idx]
        opp_grid = f"e{opp_idx+1}"
        dtype = MINION_CONFIG.get(m.id, {}).get("attack_damage_type", "bludgeoning")
        self.engine._damage_target(run, opp_grid, m.atk, source=f"p{my_grid}", damage_type=dtype, is_attack=True)
        res = get_locale_text("i18n_battle_core.minion_attack_log", minion=m.name, enemy=enemy.name)
        self.engine.save_manager.save_save(run.user_id, run)
        res = self._post_battle_action_check(run, initial_status, res, p)
        return self.engine._append_logs_to_res(run, res)

    def minion_skill(self, run: GameRun, my_grid: str, skill_idx: int = 1, target: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return get_locale_text("i18n_battle_core.not_in_battle_minion_skill")
        if p.downed:
            return get_locale_text("i18n_battle_core.downed_cannot_skill")
            return get_locale_text("i18n_battle_core.own_grid_empty", grid=my_grid)
        m = p.minions[my_grid]
        if m.id not in ALL_MINIONS:
            return get_locale_text("i18n_battle_core.minion_no_skills", name=m.name)
        template = ALL_MINIONS[m.id]
        skills_list = template.skills
        if skill_idx < 1 or skill_idx > len(skills_list):
            skills_desc = "\n".join([f" [{idx}] {s.name}: {s.desc}" for idx, s in enumerate(skills_list, 1)])
            return get_locale_text("i18n_battle_core.invalid_skill_index", name=m.name, skills=skills_desc)
        skill = skills_list[skill_idx - 1]
        cost_a = skill.cost_a
        cost_ba = skill.cost_ba
        if m.actions < cost_a or m.bonus_actions < cost_ba:
            return get_locale_text("i18n_battle_core.minion_insufficient_resources", cost_a=cost_a, cost_ba=cost_ba, actions=m.actions, bonus_actions=m.bonus_actions)
        needs_target = False
        base_id = m.id.rstrip("+")
        if base_id == "mercenary" and skill_idx == 1:
            needs_target = True
        elif base_id == "shield_guard" and skill_idx == 2:
            needs_target = True
        elif base_id == "water_elemental" and skill_idx == 2:
            needs_target = True
        if needs_target:
            if target is None:
                target = self.engine._get_first_alive_enemy(run)
            if isinstance(target, str) and target.isdigit():
                target = f"e{target}"
            if target == "0" or target == "e0":
                target = "e1"
            if target.startswith("e"):
                try:
                    idx = int(target[1:]) - 1
                except ValueError:
                    idx = 0
                if idx < 0 or idx >= len(run.enemies):
                    return get_locale_text("i18n_battle_core.enemy_target_missing", target=target)
            else:
                return get_locale_text("i18n_battle_core.invalid_target_enemy_only")
        m.actions -= cost_a
        m.bonus_actions -= cost_ba
        msg = get_locale_text("i18n_battle_core.minion_skill_log", minion=m.name, skill=skill.name)
        run.node_data["current_acting_minion_grid"] = my_grid
        try:
            effect_msg = skill.execute(run, my_grid, target, self.engine)
        finally:
            run.node_data.pop("current_acting_minion_grid", None)
        msg += effect_msg
        if "archmage_robe" in p.relics:
            self.engine.combat_resolver.gain_shield(run, "p0", 2)
            self.engine._log_event(run, get_locale_text("i18n_battle_core.archmage_robe_log"))
        self.engine.save_manager.save_save(run.user_id, run)
        msg = self._post_battle_action_check(run, initial_status, msg, p)
        return self.engine._append_logs_to_res(run, msg)
