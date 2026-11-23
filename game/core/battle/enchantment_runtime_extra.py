import random
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.entities.enchantment_data import ENCHANTMENT_CONFIG
from ...data.text.locale_data import get_locale_text
from ...models.state import CardState
from ..inventory.deck_service import DeckService
from ..inventory.enchantment_service import (
    fold_enchantments,
    get_enchantment_name,
)
from .enchantment_runtime_hooks import card_runtime_key as _card_key, is_attack_card as _is_attack_card


def _resolve_enemy(run, target: str):
    if target and target.startswith("e"):
        try:
            idx = int(target[1:]) - 1
            if 0 <= idx < len(run.enemies) and run.enemies[idx].hp > 0:
                return idx, run.enemies[idx]
        except ValueError:
            pass
    for i, e in enumerate(run.enemies):
        if e.hp > 0:
            return i, e
    return -1, None


def apply_enchantment_post_play_extra(engine, run, p, card, c_state, target: str, prev_alive_enemies: int) -> None:
    uid = run.uid_for(p) or run.user_id
    was_attack = _is_attack_card(card)
    prev_was_attack = bool(run.node_data.get("enchant_prev_card_attack", False))
    prev_was_skill = bool(run.node_data.get("enchant_prev_card_skill", False))
    run.node_data["enchant_prev_card_attack"] = was_attack
    run.node_data["enchant_prev_card_skill"] = not was_attack
    if was_attack:
        swivel_map = run.node_data.get("enchant_swivel_free")
        if isinstance(swivel_map, dict) and int(swivel_map.get(uid, 0) or 0) > 0:
            swivel_map[uid] = max(0, int(swivel_map[uid]) - 1)

    unblocked = int(run.node_data.pop("enchant_last_unblocked_dmg", 0) or 0)
    folded = fold_enchantments(getattr(card, "enchantments", None))
    if not folded:
        return
    cr = engine.combat_resolver
    eidx, target_enemy = _resolve_enemy(run, target)
    ckey = _card_key(c_state, card)

    for eid, cnt in folded:
        cfg = ENCHANTMENT_CONFIG[eid]
        if cfg.get("extra_hits_per_enemy") and target_enemy is not None:
            alive_count = sum(1 for e in run.enemies if e.hp > 0)
            extra_hits = max(0, alive_count - 1) * cnt
            hit_dmg = max(1, int(getattr(card, "base_dmg", 4) or 4))
            if extra_hits > 0:
                for _ in range(extra_hits):
                    if target_enemy.hp <= 0:
                        break
                    cr.damage_target(run, f"e{eidx + 1}", hit_dmg, source="p0", damage_type="force")
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_bowling", hits=extra_hits))

        if cfg.get("mantra_by_cost"):
            gain_m = (max(0, int(getattr(card, "cost_a", 0) or 0)) + 2) * cnt
            m_map = run.node_data.setdefault("enchant_mantra", {})
            total_m = int(m_map.get(uid, 0) or 0) + gain_m
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_mantra", amount=gain_m, total=min(10, total_m)))
            while total_m >= 10:
                total_m -= 10
                p.actions += 2
                dd_cfg = BUFF_CONFIG.get("double_damage", {"name": "double_damage", "desc": ""})
                cr.add_buff_to(p, "double_damage", dd_cfg["name"], dd_cfg["desc"], 1)
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_divinity"))
            m_map[uid] = total_m

        elec_n = int(cfg.get("channel_lightning", 0)) * cnt
        if elec_n > 0:
            orbs = run.node_data.setdefault("enchant_lightning_orbs", {})
            orbs[uid] = int(orbs.get(uid, 0) or 0) + elec_n
            alive = [(i + 1, e) for i, e in enumerate(run.enemies) if e.hp > 0]
            if alive:
                for _ in range(elec_n):
                    ti, te = random.choice(alive)
                    if te.hp > 0:
                        cr.damage_target(run, f"e{ti}", 5, source="p0", damage_type="lightning")
                        engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_electro", name=te.name, dmg=5))

        fu_a = int(cfg.get("gain_a_if_prev_attack", 0)) * cnt
        if fu_a > 0 and prev_was_attack:
            p.actions += fu_a
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_follow_up", amount=fu_a))

        frost_n = int(cfg.get("channel_frost", 0)) * cnt
        if frost_n > 0:
            orbs = run.node_data.setdefault("enchant_frost_orbs", {})
            orbs[uid] = int(orbs.get(uid, 0) or 0) + frost_n
            cr.gain_shield(run, "p0", 3 * frost_n)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_frosty", amount=3 * frost_n))

        grit_n = int(cfg.get("exhaust_random_hand", 0)) * cnt
        if grit_n > 0 and p.hand:
            from ...entities.cards.base import ALL_CARDS
            for _ in range(min(grit_n, len(p.hand))):
                rem = p.hand.pop(random.randrange(len(p.hand)))
                p.exhaust_pile.append(rem)
                rc = ALL_CARDS.get(rem)
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_grit", name=rc.name if rc else rem.id))

        mir_a = int(cfg.get("grant_miracle_a", 0)) * cnt
        mir_ba = int(cfg.get("grant_miracle_ba", 0)) * cnt
        if mir_a > 0 or mir_ba > 0:
            p.actions += mir_a
            p.bonus_actions += mir_ba
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_holy", a=mir_a, ba=mir_ba))

        scry_n = int(cfg.get("scry_before_draw", 0)) * cnt
        if scry_n > 0:
            from ...entities.cards.base import ALL_CARDS
            top = p.draw_pile[-scry_n:] if p.draw_pile else []
            curses_dropped = 0
            for st in list(top):
                sc = ALL_CARDS.get(st)
                if sc is not None and getattr(sc, "color", "") == "curse":
                    p.draw_pile.remove(st)
                    p.discard_pile.append(st)
                    curses_dropped += 1
            engine.card_player.draw_cards(p, 1, run)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_lucky", n=scry_n, curses=curses_dropped))

        nt_shield = int(cfg.get("next_turn_shield", 0)) * cnt
        if nt_shield > 0:
            smap = run.node_data.setdefault("enchant_next_turn_shield", {})
            smap[uid] = int(smap.get(uid, 0) or 0) + nt_shield
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_roll_queued", amount=nt_shield))

        frail_n = int(cfg.get("self_frail", 0)) * cnt
        if frail_n > 0:
            fmap = run.node_data.setdefault("enchant_frail_turns", {})
            fmap[uid] = int(fmap.get(uid, 0) or 0) + frail_n
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_shameful", count=frail_n))

        add_cid = cfg.get("add_card_hand")
        if add_cid:
            for _ in range(cnt):
                if len(p.hand) < 10:
                    p.hand.append(CardState(id=str(add_cid)))
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_shiv"))

        pc_red = int(cfg.get("play_cost_reduce", 0)) * cnt
        if pc_red > 0:
            smap = run.node_data.setdefault("enchant_streamlined_delta", {})
            smap[ckey] = int(smap.get(ckey, 0) or 0) - pc_red
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_streamlined", name=card.name, delta=pc_red))

        up_n = int(cfg.get("upgrade_random_hand", 0)) * cnt
        if up_n > 0:
            from ...entities.cards.base import ALL_CARDS
            cands = [st for st in p.hand if not st.upgraded]
            for st in random.sample(cands, min(up_n, len(cands))):
                st.upgraded = True
                uc = ALL_CARDS.get(st)
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_armed", name=uc.name if uc else st.id))

        r_sh = int(cfg.get("ramp_shield", 0)) * cnt
        if r_sh > 0:
            rmap = run.node_data.setdefault("enchant_ramp_shield", {})
            rmap[ckey] = int(rmap.get(ckey, 0) or 0) + r_sh
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_braced", name=card.name, amount=r_sh))

        claw_n = int(cfg.get("claw_scale", 0)) * cnt
        if claw_n > 0:
            cmap = run.node_data.setdefault("enchant_claw_dmg", {})
            cmap[card.id] = int(cmap.get(card.id, 0) or 0) + claw_n
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_clawful", amount=claw_n))

        rand_hits = int(cfg.get("random_extra_hit", 0)) * cnt
        if rand_hits > 0:
            alive = [(i + 1, e) for i, e in enumerate(run.enemies) if e.hp > 0]
            if alive:
                if eid == "tear":
                    ti, te = random.choice(alive)
                    cr.damage_target(run, f"e{ti}", 4 * cnt, source="p0", damage_type="slashing")
                    engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_tear", name=te.name, dmg=4 * cnt))
                else:
                    for _ in range(rand_hits):
                        alive_now = [(i + 1, e) for i, e in enumerate(run.enemies) if e.hp > 0]
                        if not alive_now:
                            break
                        ti, _ = random.choice(alive_now)
                        cr.damage_target(run, f"e{ti}", 3, source="p0", damage_type="bludgeoning")
                    engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_erang", hits=rand_hits))

        if eid == "blurry":
            bk = run.node_data.setdefault("enchant_blurry_keep", {})
            bk[uid] = True

        if cfg.get("enter_wrath"):
            wmap = run.node_data.setdefault("enchant_wrath_active", {})
            wmap[uid] = True
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_erupting"))

        dark_n = int(cfg.get("channel_dark", 0)) * cnt
        if dark_n > 0:
            dlist = run.node_data.setdefault("enchant_dark_orbs", [])
            for _ in range(dark_n):
                dlist.append({"uid": uid, "turns": 2, "dmg": 4})
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_gloom"))

        gft_dmg = int(cfg.get("bonus_vs_attacking_dmg", 0)) * cnt
        if gft_dmg > 0 and target_enemy is not None:
            intents = getattr(target_enemy, "intents", None) or []
            is_atk = any(str(it.get("type", "")).lower() == "attack" or int(it.get("dmg", 0) or 0) > 0 for it in intents if isinstance(it, dict))
            if is_atk:
                cr.damage_target(run, f"e{eidx + 1}", gft_dmg, source="p0", damage_type="piercing")
                cr.add_buff_to(target_enemy, "weak", get_locale_text("i18n_battle_core.buff_weak_name"), get_locale_text("i18n_battle_core.buff_weak_desc"), 1)
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_go_for_the", dmg=gft_dmg))

        lock_n = int(cfg.get("apply_lock_on", 0)) * cnt
        if lock_n > 0 and target_enemy is not None:
            lmap = run.node_data.setdefault("enchant_lock_on", {})
            lmap[str(eidx)] = int(lmap.get(str(eidx), 0) or 0) + lock_n
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_locking", name=target_enemy.name, count=lock_n))

        r_dmg = int(cfg.get("ramp_dmg", 0)) * cnt
        if r_dmg != 0:
            rmap = run.node_data.setdefault("enchant_ramp_dmg", {})
            rmap[ckey] = int(rmap.get(ckey, 0) or 0) + r_dmg
            if r_dmg > 0:
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_ramped", name=card.name, amount=r_dmg))
            else:
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_glass", name=card.name, amount=-r_dmg))

        if cfg.get("next_attack_free"):
            smap = run.node_data.setdefault("enchant_swivel_free", {})
            smap[uid] = int(smap.get(uid, 0) or 0) + cnt
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_swivel"))

        if cfg.get("block_equal_unblocked_dmg") and unblocked > 0:
            cr.gain_shield(run, "p0", unblocked)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_wallop", amount=unblocked))

        next_ench = cfg.get("shuffle_transformed_enchant")
        if next_ench:
            new_st = DeckService.clone_state(c_state)
            new_st.enchantments = [next_ench]
            p.draw_pile.append(new_st)
            random.shuffle(p.draw_pile)
            engine._log_event(
                run,
                get_locale_text(
                    "i18n_enchantment.ui.log_alpha_beta",
                    enchant_name=get_enchantment_name(eid),
                    next_name=get_enchantment_name(next_ench),
                ),
            )

        if cfg.get("die_next_turn"):
            bmap = run.node_data.setdefault("enchant_blasphemous_die", {})
            bmap[uid] = True
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_blasphemous_warn"))

        bundle_n = int(cfg.get("add_base_copies_hand", 0)) * cnt
        if bundle_n > 0:
            added = 0
            for _ in range(bundle_n):
                if len(p.hand) < 10:
                    p.hand.append(CardState(id=c_state.id, upgraded=c_state.upgraded))
                    added += 1
            if added > 0:
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_bundled", count=added))

        exp_turns = int(cfg.get("delayed_burst_turns", 0))
        if exp_turns > 0:
            exp_dmg = int(cfg.get("delayed_burst_dmg", 18)) * cnt
            elist = run.node_data.setdefault("enchant_explosives", [])
            elist.append({"uid": uid, "turns": exp_turns, "dmg": exp_dmg})
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_explosive_arm", turns=exp_turns))

        fo_n = int(cfg.get("return_zero_cost_from_discard", 0)) * cnt
        if fo_n > 0 and p.discard_pile:
            from ...entities.cards.base import ALL_CARDS
            zeros = [st for st in p.discard_pile if getattr(ALL_CARDS.get(st), "cost_a", 1) == 0]
            for st in random.sample(zeros, min(fo_n, len(zeros))):
                if len(p.hand) < 10:
                    p.discard_pile.remove(st)
                    p.hand.append(st)
                    zc = ALL_CARDS.get(st)
                    engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_for_one", name=zc.name if zc else st.id))

        if cfg.get("infinite_copy_each_turn"):
            ilist = run.node_data.setdefault("enchant_infinite_cards", [])
            ilist.append({"uid": uid, "id": c_state.id, "upgraded": c_state.upgraded})
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_infinite_arm", name=card.name))

        plasma_n = int(cfg.get("channel_plasma", 0)) * cnt
        if plasma_n > 0:
            pmap = run.node_data.setdefault("enchant_plasma_turns", {})
            pmap[uid] = int(pmap.get(uid, 0) or 0) + plasma_n
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_plasma", turns=plasma_n))

        moxie_n = int(cfg.get("kill_perm_dmg", 0)) * cnt
        if moxie_n > 0:
            now_alive = sum(1 for e in run.enemies if e.hp > 0)
            kills = max(0, prev_alive_enemies - now_alive)
            if kills > 0:
                if not isinstance(getattr(p, "relic_counters", None), dict):
                    p.relic_counters = {}
                mkey = f"enchant_moxie_{c_state.id}"
                p.relic_counters[mkey] = int(p.relic_counters.get(mkey, 0) or 0) + moxie_n * kills
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_moxie", name=card.name, amount=moxie_n * kills))

        if cfg.get("poison_equal_unblocked_dmg") and unblocked > 0 and target_enemy is not None:
            poison_cfg = BUFF_CONFIG["poison"]
            cr.add_buff_to(target_enemy, "poison", poison_cfg["name"], poison_cfg["desc"], unblocked)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_pernicious", name=target_enemy.name, count=unblocked))

        runic_t = int(cfg.get("obscure_intents_turns", 0)) * cnt
        if runic_t > 0:
            rmap = run.node_data.setdefault("enchant_runic_turns", {})
            rmap[uid] = int(rmap.get(uid, 0) or 0) + runic_t
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_runic", turns=runic_t))

        sanc_n = int(cfg.get("draw_if_prev_skill", 0)) * cnt
        if sanc_n > 0 and prev_was_skill:
            engine.card_player.draw_cards(p, sanc_n, run)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_sanctified", count=sanc_n))

        intang_n = int(cfg.get("gain_intangible", 0)) * cnt
        if intang_n > 0:
            icfg = BUFF_CONFIG["intangible"]
            cr.add_buff_to(p, "intangible", icfg["name"], icfg["desc"], intang_n)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_aberrant", count=intang_n))


def apply_enchantment_turn_start_extra(engine, run, p) -> None:
    uid = run.uid_for(p) or run.user_id
    cr = engine.combat_resolver

    wmap = run.node_data.get("enchant_wrath_active")
    if isinstance(wmap, dict):
        wmap.pop(uid, None)

    smap = run.node_data.get("enchant_next_turn_shield")
    if isinstance(smap, dict):
        sh = int(smap.pop(uid, 0) or 0)
        if sh > 0:
            cr.gain_shield(run, "p0", sh)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_roll_gain", amount=sh))

    pmap = run.node_data.get("enchant_plasma_turns")
    if isinstance(pmap, dict) and int(pmap.get(uid, 0) or 0) > 0:
        pmap[uid] = int(pmap[uid]) - 1
        p.actions += 2
        engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_plasma_gain"))

    rmap = run.node_data.get("enchant_runic_turns")
    if isinstance(rmap, dict) and int(rmap.get(uid, 0) or 0) > 0:
        rmap[uid] = int(rmap[uid]) - 1

    fmap = run.node_data.get("enchant_frail_turns")
    if isinstance(fmap, dict) and int(fmap.get(uid, 0) or 0) > 0:
        fmap[uid] = int(fmap[uid]) - 1

    lmap = run.node_data.get("enchant_lock_on")
    if isinstance(lmap, dict):
        for lk in list(lmap.keys()):
            lmap[lk] = max(0, int(lmap[lk] or 0) - 1)
            if lmap[lk] <= 0:
                lmap.pop(lk, None)

    elist = run.node_data.get("enchant_explosives")
    if isinstance(elist, list) and elist:
        rem = []
        for item in elist:
            if item.get("uid") != uid:
                rem.append(item)
                continue
            item["turns"] = int(item.get("turns", 1)) - 1
            if item["turns"] <= 0:
                dmg = int(item.get("dmg", 18))
                for i, e in enumerate(run.enemies, 1):
                    if e.hp > 0:
                        cr.damage_target(run, f"e{i}", dmg, source="p0", damage_type="fire")
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_explosive_boom", dmg=dmg))
            else:
                rem.append(item)
        run.node_data["enchant_explosives"] = rem

    ilist = run.node_data.get("enchant_infinite_cards")
    if isinstance(ilist, list) and ilist:
        from ...entities.cards.base import ALL_CARDS
        for item in ilist:
            if item.get("uid") == uid and len(p.hand) < 10:
                st = CardState(id=item["id"], upgraded=bool(item.get("upgraded", False)))
                p.hand.append(st)
                ic = ALL_CARDS.get(st)
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_infinite_gain", name=ic.name if ic else st.id))

    bmap = run.node_data.get("enchant_blasphemous_die")
    if isinstance(bmap, dict) and bmap.pop(uid, False):
        engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_blasphemous_die"))
        cr.damage_target(run, "p0", max(99999, p.hp + p.shield + 999), source="effect", damage_type="true")


def apply_enchantment_turn_end_extra(engine, run, p) -> None:
    uid = run.uid_for(p) or run.user_id
    cr = engine.combat_resolver

    eorbs = run.node_data.get("enchant_lightning_orbs")
    if isinstance(eorbs, dict):
        cnt = int(eorbs.pop(uid, 0) or 0)
        if cnt > 0:
            alive = [(i + 1, e) for i, e in enumerate(run.enemies) if e.hp > 0]
            if alive:
                for _ in range(cnt):
                    ti, te = random.choice(alive)
                    if te.hp > 0:
                        cr.damage_target(run, f"e{ti}", 3, source="p0", damage_type="lightning")
                        engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_electro", name=te.name, dmg=3))

    forbs = run.node_data.get("enchant_frost_orbs")
    if isinstance(forbs, dict):
        cnt = int(forbs.pop(uid, 0) or 0)
        if cnt > 0:
            cr.gain_shield(run, "p0", 3 * cnt)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_frosty", amount=3 * cnt))

    dlist = run.node_data.get("enchant_dark_orbs")
    if isinstance(dlist, list) and dlist:
        rem = []
        for item in dlist:
            if item.get("uid") != uid:
                rem.append(item)
                continue
            item["dmg"] = int(item.get("dmg", 4)) + 4
            item["turns"] = int(item.get("turns", 1)) - 1
            if item["turns"] <= 0:
                alive = [(i + 1, e) for i, e in enumerate(run.enemies) if e.hp > 0]
                if alive:
                    ti, te = min(alive, key=lambda x: x[1].hp)
                    cr.damage_target(run, f"e{ti}", item["dmg"], source="p0", damage_type="necrotic")
                    engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_gloom_detonate", name=te.name, dmg=item["dmg"]))
            else:
                rem.append(item)
        run.node_data["enchant_dark_orbs"] = rem