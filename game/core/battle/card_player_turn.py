import random
from ...models.state import GameRun
from ...data.locale_data import get_locale_text
from ...entities import ALL_CARDS, ALL_AMULETS
from ...models.events import TurnEndEvent, TurnStartEvent, CardExhaustEvent


class CardPlayerTurnMixin:
    def _end_player_phase(self, run: GameRun, p) -> str:
        evt_end = TurnEndEvent(run, is_player=True)
        self.engine.event_bus.dispatch(evt_end)
        retain_key = "temp_retain_cards" if not run.coop_id else f"temp_retain_cards:{run.uid_for(p)}"
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
        for mk, mv in p.minions.items():
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
            if run.enemies and any(e.name.startswith("Icerainboww") for e in run.enemies):
                run.node_data["icerainboww_turn"] = run.node_data.get("icerainboww_turn", 1) + 1
            if run.enemies and any(e.name.startswith("雷霆领主") for e in run.enemies):
                run.node_data["thunder_lord_turn"] = run.node_data.get("thunder_lord_turn", 1) + 1
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
        run.node_data[run.turn_key("cards_played_this_turn", p)] = 0
        if getattr(run, "coop_id", ""):
            run.node_data[f"action_surge_turn_used:{run.uid_for(p)}"] = False
        else:
            run.node_data["action_surge_turn_used"] = False
        self._reindex_minions(p)
        if advance_global:
            run.node_data["turn_count"] = run.node_data.get("turn_count", 1) + 1
        return get_locale_text("i18n_battle_core.begin_player_phase_log", decay_info=decay_info, name=p.name)

    def end_turn(self, run: GameRun) -> str:
        if run.node_type != "battle":
            return get_locale_text("i18n_battle_core.not_in_battle_end_turn")
        if getattr(run, "coop_id", ""):
            from ..coop_engine import CoopEngine
            return CoopEngine(self.engine.save_manager, self.engine).handle_battle_turn_end(run)
        p = run.player
        self._end_player_phase(run, p)
        if self.engine.is_battle_won(run):
            self.handle_battle_win(run)
            self._reindex_minions(p)
            return self.engine._append_logs_to_res(run, get_locale_text("i18n_battle_core.battle_victory"))
        extra_turns = run.node_data.get("extra_turns_left", 0)
        if extra_turns > 0:
            run.node_data["extra_turns_left"] = extra_turns - 1
            enemy_actions = get_locale_text("i18n_battle_core.time_stop_extra_turn", count=extra_turns - 1)
        else:
            enemy_actions = self.engine._enemy_turn(run)
        if self.engine.is_battle_won(run):
            self.handle_battle_win(run)
            self._reindex_minions(p)
            return self.engine._append_logs_to_res(run, f"{enemy_actions}\n{get_locale_text('i18n_battle_core.battle_victory_emoji')}")
        if p.hp <= 0:
            settle_msg = self.engine.save_manager.settle_game_and_delete(run.user_id, run, is_victory=False)
            return get_locale_text("i18n_battle_core.adventure_defeat", enemy_actions=enemy_actions, settle_msg=settle_msg)
        begin_info = self._begin_player_phase(run, p, advance_global=True)
        self.engine._roll_enemy_intent(run)
        self.engine.save_manager.save_save(run.user_id, run)
        return self.engine._append_logs_to_res(run, f"{enemy_actions}\n{begin_info}")
