import random
from ...data.locale_data import get_locale_text
from ...entities.cards.ninja_base import add_ninja_buff, change_lex_kela, has_ninja_tag


def handle_lex_kela_changed(engine, event) -> None:
    if event.delta >= 0 or event.player is None:
        return
    spent = -int(event.delta)
    p = event.player
    run = event.run
    for b in list(p.buffs):
        if b.id == "mummy_power" and b.stacks > 0:
            gain = b.stacks * spent
            engine.combat_resolver.gain_shield(run, "p0", gain)
            engine._log_event(run, get_locale_text("i18n_cards_ninja.mummy_shield", shield=gain))
        elif b.id == "i_represent_shinobi" and b.stacks > 0:
            p.actions += b.stacks
            engine._log_event(run, get_locale_text("i18n_cards_ninja.shinobi_action"))


def handle_ninja_card_exhaust(engine, event) -> None:
    run = getattr(event, "run", None)
    if run is None or run.player is None:
        return
    p = run.player
    for pile in (p.hand, p.draw_pile, p.discard_pile):
        for st in pile:
            if getattr(st, "id", "") == "ninja_reaper_flame_blade":
                st.battle_cost_delta_a = int(getattr(st, "battle_cost_delta_a", 0) or 0) - 1


def handle_ninja_post_play(engine, run, p, card, target) -> None:
    if card is None:
        return
    if getattr(card, "science", False):
        if int(getattr(p, "lex_kela", 0) or 0) > 0:
            change_lex_kela(engine, run, p, -1, reason="science", source_card_id=card.id)
            engine._log_event(run, get_locale_text("i18n_cards_ninja.science_spend", current=p.lex_kela))
        for b in list(p.buffs):
            if b.id == "science_double" and b.stacks > 0:
                b.stacks -= 1
                if b.stacks <= 0:
                    p.buffs.remove(b)
                engine._execute_card_effect(run, card, target)
                break
    if has_ninja_tag(card, "blade"):
        run.node_data["ninja_blades_played"] = int(run.node_data.get("ninja_blades_played", 0) or 0) + 1
    run.node_data["ninja_last_was_ninjutsu"] = has_ninja_tag(card, "ninjutsu")
    run.node_data["ninja_prev_played_card_id"] = run.node_data.get("ninja_last_played_card_id", "")
    if card.id != "ninja_mobius_loop_snake":
        run.node_data["ninja_last_played_card_id"] = card.id
    if any(
        st.id == "ninja_mosquito_hand"
        for pile in (p.hand, p.draw_pile, p.discard_pile)
        for st in pile
    ):
        engine._log_event(run, get_locale_text("i18n_cards_ninja.mosquito_buzz"))


def handle_ninja_turn_end(engine, run, p) -> None:
    for st in list(p.hand):
        if st.id == "ninja_i_see_you":
            add_ninja_buff(engine, p, "vulnerable", 1)
            engine._log_event(run, get_locale_text("i18n_cards_ninja.i_see_you_tick"))
        elif st.id == "ninja_hamood_kill_all":
            humans = list(run.all_human_uids())
            n_players = max(1, len(humans))
            dmg = int("9" * (n_players + 1))
            if humans:
                for uid in humans:
                    pl = run.players.get(uid)
                    if pl is not None and not pl.downed and pl.hp > 0:
                        pl.hp = max(0, pl.hp - dmg)
                        if pl.hp <= 0 and len(humans) > 1:
                            pl.downed = True
            else:
                p.hp = max(0, p.hp - dmg)
            for e in run.enemies:
                if e.hp > 0:
                    e.hp = max(0, e.hp - dmg)
            engine._log_event(run, get_locale_text("i18n_cards_ninja.hamood_doom", dmg=dmg))

    if getattr(p, "selected_class", "") == "蕾忍":
        spent_key = run.turn_key("lex_kela_spent_this_turn", p)
        if not run.node_data.get(spent_key, False):
            gained = change_lex_kela(engine, run, p, 1, reason="turn_end")
            if gained > 0:
                engine._log_event(run, get_locale_text("i18n_cards_ninja.lex_turn_end", current=p.lex_kela))


def handle_ninja_turn_start(engine, run, p) -> None:
    run.node_data[run.turn_key("lex_kela_spent_this_turn", p)] = False
    for st in p.hand:
        if st.id == "ninja_wild_snake_god":
            st.temp_cost_a = random.randint(0, 3)
    if any(st.id == "ninja_mobius_loop_snake" for st in p.exhaust_pile):
        prev_id = str(run.node_data.get("ninja_last_played_card_id", "") or "")
        if prev_id and prev_id != "ninja_mobius_loop_snake":
            from ...entities.cards.base import ALL_CARDS
            prev_card = ALL_CARDS.get(prev_id)
            if prev_card is not None:
                target = engine._get_first_alive_enemy(run)
                engine._execute_card_effect(run, prev_card, target)
                engine._log_event(run, get_locale_text("i18n_cards_ninja.mobius_exhaust_replay", name=prev_card.name))


def try_sarira_revive(engine, run, p) -> bool:
    if p is None or p.hp > 0:
        return False
    if "sarira" not in (getattr(p, "relics", []) or []):
        return False
    if p.relic_counters.get("sarira_used", 0) > 0:
        return False
    p.relic_counters["sarira_used"] = 1
    p.hp = p.max_hp
    p.gold = max(0, p.gold - 22000000)
    engine._log_event(run, get_locale_text("i18n_cards_ninja.sarira_revive"))
    return True


def handle_toilet_water_on_draw(engine, run, p, drawn_state) -> bool:
    if drawn_state is not None and getattr(drawn_state, "id", "") == "ninja_hamood_kick":
        drawn_state.battle_cost_delta_a = int(getattr(drawn_state, "battle_cost_delta_a", 0) or 0) + 1
    if "toilet_water" not in (getattr(p, "relics", []) or []):
        return False
    key = run.turn_key("toilet_water_count", p)
    remaining = int(run.node_data.get(key, 0) or 0)
    if remaining <= 0:
        return False
    from ...entities.cards.base import ALL_CARDS
    card = ALL_CARDS.get(drawn_state)
    if card is None or getattr(card, "color", "") != "curse":
        return False
    run.node_data[key] = remaining - 1
    if drawn_state in p.hand:
        p.hand.remove(drawn_state)
    p.exhaust_pile.append(drawn_state)
    engine._log_event(run, get_locale_text("i18n_cards_ninja.toilet_water_trigger", name=card.name))
    engine.card_player.draw_cards(p, 1, run)
    return True
