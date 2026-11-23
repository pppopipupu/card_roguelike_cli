import random
from ...data.entities.enchantment_data import ENCHANTMENT_CONFIG
from ...data.text.locale_data import get_locale_text
from ..inventory.deck_service import DeckService
from ..inventory.enchantment_service import fold_enchantments


def is_attack_card(card) -> bool:
    if card is None:
        return False
    if getattr(card, "type", "") == "attack":
        return True
    return int(getattr(card, "base_dmg", 0) or 0) > 0


def card_runtime_key(card_state, card) -> str:
    cid = getattr(card_state, "id", None) or getattr(card, "id", "")
    enchs = tuple(getattr(card_state, "enchantments", None) or getattr(card, "enchantments", None) or ())
    return f"{cid}|{'+'.join(enchs)}"


def check_enchantment_playable_extra(run, card) -> str:
    from ...entities.cards.base import ALL_CARDS
    hand = list(getattr(run.player, "hand", []) or [])
    card_enchs = set(getattr(card, "enchantments", None) or ())
    if "absolute" not in card_enchs:
        for h_state in hand:
            if "absolute" in (getattr(h_state, "enchantments", None) or ()):
                return get_locale_text("i18n_enchantment.ui.absolute_blocked")
    if "signature" in card_enchs:
        atk_count = 0
        for h_state in hand:
            h_card = ALL_CARDS.get(h_state)
            if is_attack_card(h_card):
                atk_count += 1
        if atk_count > 1:
            return get_locale_text("i18n_enchantment.ui.signature_blocked")
    return ""


def apply_enchantment_cost_calc(run, player, card, card_state, cost_a: int) -> int:
    folded = fold_enchantments(getattr(card, "enchantments", None))
    uid = run.uid_for(player) or run.user_id
    if cost_a > 0 and is_attack_card(card):
        swivel_map = run.node_data.get("enchant_swivel_free")
        if isinstance(swivel_map, dict) and int(swivel_map.get(uid, 0) or 0) > 0:
            return 0
    if not folded or cost_a < 0:
        return cost_a
    hp_losses = int((run.node_data.get("enchant_hp_loss_count") or {}).get(uid, 0) or 0)
    battle_type = str(run.node_data.get("battle_type", "normal"))
    streamlined_map = run.node_data.get("enchant_streamlined_delta") or {}
    ckey = card_runtime_key(card_state, card)
    delta = int(streamlined_map.get(ckey, 0) or 0)
    for eid, cnt in folded:
        cfg = ENCHANTMENT_CONFIG[eid]
        hp_delta = int(cfg.get("hp_loss_cost_delta", 0)) * cnt
        if hp_delta != 0 and hp_losses > 0:
            delta += hp_delta * hp_losses
        eb_delta = int(cfg.get("elite_boss_cost_delta", 0)) * cnt
        if eb_delta != 0 and battle_type in ("elite", "boss"):
            delta += eb_delta
    if delta != 0:
        return max(0, cost_a + delta)
    return cost_a


def apply_enchantment_dmg_extra(run, card, target: str, enemy, dmg: int, damage_type: str = "") -> int:
    folded = fold_enchantments(getattr(card, "enchantments", None))
    p = run.player
    uid = run.uid_for(p) or run.user_id
    extra_add = 0
    mult = 1.0
    if folded:
        ckey = card_runtime_key(None, card)
        ramp_map = run.node_data.get("enchant_ramp_dmg") or {}
        extra_add += int(ramp_map.get(ckey, 0) or 0)
        claw_map = run.node_data.get("enchant_claw_dmg") or {}
        extra_add += int(claw_map.get(getattr(card, "id", ""), 0) or 0)
        moxie_map = getattr(p, "relic_counters", None) or {}
        moxie_key = f"enchant_moxie_{getattr(card, 'id', '')}"
        extra_add += int(moxie_map.get(moxie_key, 0) or 0)
        str_stacks = 0
        for b in p.buffs:
            if b.id == "strength":
                str_stacks = b.stacks
                break
        for eid, cnt in folded:
            cfg = ENCHANTMENT_CONFIG[eid]
            s_mult = int(cfg.get("strength_mult", 0))
            if s_mult > 1 and str_stacks != 0:
                extra_add += str_stacks * (s_mult - 1) * cnt
            curse_dmg = int(cfg.get("curse_deck_dmg", 0)) * cnt
            if curse_dmg > 0:
                from ...entities.cards.base import ALL_CARDS
                curses = sum(
                    1
                    for st in (p.deck or [])
                    if getattr(ALL_CARDS.get(st), "color", "") == "curse"
                )
                extra_add += curse_dmg * curses
            if cfg.get("double_dmg_lowest_hp") and enemy is not None:
                alive = [e for e in run.enemies if e.hp > 0]
                if alive and enemy.hp == min(e.hp for e in alive):
                    mult *= 2.0
    if target and target.startswith("e"):
        try:
            eidx = str(int(target[1:]) - 1)
            lock_map = run.node_data.get("enchant_lock_on") or {}
            if int(lock_map.get(eidx, 0) or 0) > 0 and damage_type in ("effect", "lightning", "necrotic", "fire", "cold", "force"):
                mult *= 1.5
        except ValueError:
            pass
    wrath_map = run.node_data.get("enchant_wrath_active")
    if isinstance(wrath_map, dict) and wrath_map.get(uid):
        mult *= 2.0
    if extra_add != 0 or mult != 1.0:
        if dmg > 0 or extra_add > 0:
            dmg = max(1, int(round((dmg + extra_add) * mult)))
    return dmg


def apply_enchantment_incoming_dmg_extra(run, target: str, dmg: int) -> int:
    if target != "p0":
        return dmg
    uid = run.uid_for(run.player) or run.user_id
    wrath_map = run.node_data.get("enchant_wrath_active")
    if isinstance(wrath_map, dict) and wrath_map.get(uid) and dmg > 0:
        return max(1, int(round(dmg * 1.5)))
    return dmg


def apply_enchantment_shield_extra(run, card, amount: int) -> int:
    p = run.player
    uid = run.uid_for(p) or run.user_id
    ckey = card_runtime_key(None, card)
    ramp_map = run.node_data.get("enchant_ramp_shield") or {}
    add_s = int(ramp_map.get(ckey, 0) or 0)
    if add_s > 0:
        amount += add_s
    frail_map = run.node_data.get("enchant_frail_turns") or {}
    if int(frail_map.get(uid, 0) or 0) > 0 and amount > 0:
        amount = max(1, int(round(amount * 0.75)))
    return amount


def should_prevent_shield_decay(run, player) -> bool:
    uid = run.uid_for(player) or run.user_id
    bmap = run.node_data.get("enchant_blurry_keep")
    if isinstance(bmap, dict) and bmap.pop(uid, False):
        return True
    return False


def apply_enchantment_on_draw(engine, run, player, card_state, card) -> bool:
    folded = fold_enchantments(getattr(card_state, "enchantments", None))
    if not folded:
        return False
    cname = card.name if card is not None else card_state.id
    for eid, cnt in folded:
        cfg = ENCHANTMENT_CONFIG[eid]
        if cfg.get("discard_first_draw"):
            seen = run.node_data.setdefault("enchant_slippery_seen", [])
            ckey = card_runtime_key(card_state, card)
            if ckey not in seen:
                seen.append(ckey)
                player.discard_pile.append(card_state)
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_slippery", name=cname))
                return True
        if cfg.get("duplicate_on_draw"):
            dup = DeckService.clone_state(card_state)
            if len(player.hand) < 10:
                player.hand.append(dup)
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_endless", name=cname))
        if cfg.get("randomize_cost_on_draw"):
            new_cost = random.randint(0, 3)
            card_state.temp_cost_a = new_cost
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_snecko", name=cname, cost=new_cost))
        gain_a = int(cfg.get("draw_gain_a", 0)) * cnt
        if gain_a > 0:
            player.actions += gain_a
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_shining", count=gain_a))
        lose_a = int(cfg.get("draw_lose_a", 0)) * cnt
        if lose_a > 0:
            player.actions = max(0, player.actions - lose_a)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_voiding", count=lose_a))
        if cfg.get("autoplay_on_draw") and not run.node_data.get("enchant_auto_playing"):
            run.node_data["enchant_auto_playing"] = True
            try:
                card_state.temp_cost_a = 0
                card_state.temp_cost_ba = 0
                player.hand.append(card_state)
                idx = len(player.hand)
                target = engine._get_first_alive_enemy(run) or "e1"
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_auto", name=cname))
                engine.card_player.play_card(run, idx, target)
            finally:
                run.node_data["enchant_auto_playing"] = False
            return True
    return False


def apply_enchantment_on_exhaust(engine, run, player, card_state) -> None:
    folded = fold_enchantments(getattr(card_state, "enchantments", None))
    if not folded:
        return
    for eid, cnt in folded:
        draw_n = int(ENCHANTMENT_CONFIG[eid].get("on_exhaust_draw", 0)) * cnt
        if draw_n > 0:
            engine.card_player.draw_cards(player, draw_n, run)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_memento", count=draw_n))


def apply_enchantment_on_damage_take(engine, run, source: str, target: str, amount: int) -> None:
    if amount <= 0:
        return
    p = run.player
    uid = run.uid_for(p) or run.user_id
    if target == "p0":
        counts = run.node_data.setdefault("enchant_hp_loss_count", {})
        counts[uid] = int(counts.get(uid, 0) or 0) + 1
        from ...entities.cards.base import ALL_CARDS
        for h_state in list(p.hand):
            if "vanishing" in (getattr(h_state, "enchantments", None) or ()):
                p.hand.remove(h_state)
                p.exhaust_pile.append(h_state)
                h_card = ALL_CARDS.get(h_state)
                cname = h_card.name if h_card else h_state.id
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_vanishing", name=cname))
    elif source == "p0" and target.startswith("e"):
        run.node_data["enchant_last_unblocked_dmg"] = int(run.node_data.get("enchant_last_unblocked_dmg", 0) or 0) + amount
