import random
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.entities.enchantment_data import ENCHANTMENT_CONFIG
from ...data.text.locale_data import get_locale_text
from ...entities.buffs import is_debuff
from ..inventory.deck_service import DeckService
from ..inventory.enchantment_service import fold_enchantments


def _is_attack_card(card) -> bool:
    if card is None:
        return False
    if getattr(card, "type", "") == "attack":
        return True
    return int(getattr(card, "base_dmg", 0) or 0) > 0


def check_enchantment_playable(run, card) -> str:
    folded = fold_enchantments(getattr(card, "enchantments", None))
    if not folded:
        return ""
    from ...entities.cards.base import ALL_CARDS
    hand = list(getattr(run.player, "hand", []) or [])
    for eid, _ in folded:
        cfg = ENCHANTMENT_CONFIG[eid]
        if cfg.get("only_attacks_in_hand"):
            for h_state in hand:
                h_card = ALL_CARDS.get(h_state)
                if not _is_attack_card(h_card):
                    return get_locale_text("i18n_enchantment.ui.clashy_blocked")
        if cfg.get("only_skills_in_hand"):
            for h_state in hand:
                h_card = ALL_CARDS.get(h_state)
                if _is_attack_card(h_card):
                    return get_locale_text("i18n_enchantment.ui.demur_blocked")
    return ""


def apply_enchantment_dmg(run, card, target: str, dmg: int) -> tuple[int, bool]:
    folded = fold_enchantments(getattr(card, "enchantments", None))
    if not folded:
        return dmg, False
    dmg_pct = 0
    dmg_add = 0
    pierce = False
    p = run.player
    enemy = None
    if target and target.startswith("e"):
        try:
            idx = int(target[1:]) - 1
            if 0 <= idx < len(run.enemies):
                enemy = run.enemies[idx]
        except ValueError:
            enemy = None

    for eid, cnt in folded:
        cfg = ENCHANTMENT_CONFIG[eid]
        all_pct = int(cfg.get("all_num_pct", 0)) * cnt
        dmg_pct += int(cfg.get("dmg_pct", 0)) * cnt + all_pct
        dmg_add += int(cfg.get("dmg_add", 0)) * cnt
        low_hp_pct = int(cfg.get("low_hp_dmg_pct", 0)) * cnt
        if low_hp_pct > 0 and p.max_hp > 0 and p.hp * 2 < p.max_hp:
            dmg_pct += low_hp_pct
        eb_dmg = int(cfg.get("enemy_debuff_dmg", 0)) * cnt
        if eb_dmg > 0 and enemy is not None:
            debuff_kinds = sum(1 for b in enemy.buffs if is_debuff(b.id) and b.stacks > 0)
            dmg_add += eb_dmg * debuff_kinds
        if cfg.get("pierce_shield"):
            pierce = True

    if dmg > 0 and (dmg_pct != 0 or dmg_add != 0):
        dmg = max(1, int(round((dmg + dmg_add) * max(0.1, 1.0 + dmg_pct / 100.0))))
    elif dmg == 0 and dmg_add > 0:
        dmg = dmg_add
    return dmg, pierce


def apply_enchantment_shield(run, card, amount: int) -> int:
    folded = fold_enchantments(getattr(card, "enchantments", None))
    if not folded:
        return amount
    shield_pct = 0
    shield_add = 0
    p = run.player
    for eid, cnt in folded:
        cfg = ENCHANTMENT_CONFIG[eid]
        all_pct = int(cfg.get("all_num_pct", 0)) * cnt
        shield_pct += int(cfg.get("shield_pct", 0)) * cnt + all_pct
        sb_shield = int(cfg.get("self_debuff_shield", 0)) * cnt
        if sb_shield > 0:
            debuff_kinds = sum(1 for b in p.buffs if is_debuff(b.id) and b.stacks > 0)
            shield_add += sb_shield * debuff_kinds
    if amount > 0 and (shield_pct != 0 or shield_add != 0):
        amount = max(1, int(round(amount * max(0.1, 1.0 + shield_pct / 100.0)))) + shield_add
    elif amount == 0 and shield_add > 0:
        amount = shield_add
    return amount


def apply_enchantment_heal(card, heal: int) -> int:
    folded = fold_enchantments(getattr(card, "enchantments", None))
    if not folded:
        return heal
    heal_pct = 0
    for eid, cnt in folded:
        cfg = ENCHANTMENT_CONFIG[eid]
        heal_pct += int(cfg.get("heal_pct", 0)) * cnt + int(cfg.get("all_num_pct", 0)) * cnt
    if heal > 0 and heal_pct != 0:
        heal = max(1, int(round(heal * max(0.1, 1.0 + heal_pct / 100.0))))
    return heal


def enchantment_pierces(card) -> bool:
    """判断卡牌上的附魔是否带有穿透护盾效果。"""
    folded = fold_enchantments(getattr(card, "enchantments", None))
    for eid, _ in folded:
        if ENCHANTMENT_CONFIG[eid].get("pierce_shield"):
            return True
    return False


def apply_enchantment_post_play(engine, run, p, card, c_state, target: str, prev_alive_enemies: int) -> None:
    folded = fold_enchantments(getattr(card, "enchantments", None))
    if not folded:
        return
    cr = engine.combat_resolver
    for eid, cnt in folded:
        cfg = ENCHANTMENT_CONFIG[eid]

        hp_loss = int(cfg.get("self_hp_loss", 0)) * cnt
        if hp_loss > 0:
            p.hp = max(1, p.hp - hp_loss)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_hemo", loss=hp_loss))

        bonus_shield = int(cfg.get("bonus_shield", 0)) * cnt
        if bonus_shield > 0:
            cr.gain_shield(run, "p0", bonus_shield)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_bonus_shield", amount=bonus_shield))

        bonus_heal = int(cfg.get("bonus_heal", 0)) * cnt
        if bonus_heal > 0:
            cr.heal_target(run, "p0", bonus_heal)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_bonus_heal", amount=bonus_heal))

        draw_n = int(cfg.get("draw", 0)) * cnt
        if draw_n > 0:
            engine.card_player.draw_cards(p, draw_n, run)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_draw", count=draw_n))

        disc_n = int(cfg.get("discard_random", 0)) * cnt
        if disc_n > 0 and p.hand:
            actual = min(disc_n, len(p.hand))
            for _ in range(actual):
                idx = random.randrange(len(p.hand))
                removed = p.hand.pop(idx)
                p.discard_pile.append(removed)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_discard", count=actual))

        uid = run.uid_for(p) or run.user_id
        next_a = int(cfg.get("next_turn_a", 0)) * cnt
        if next_a > 0:
            store_a = run.node_data.setdefault("enchant_next_turn_a", {})
            store_a[uid] = int(store_a.get(uid, 0)) + next_a
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_next_a", count=next_a))

        next_draw = int(cfg.get("next_turn_draw", 0)) * cnt
        if next_draw > 0:
            store_d = run.node_data.setdefault("enchant_next_turn_draw", {})
            store_d[uid] = int(store_d.get(uid, 0)) + next_draw
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_next_draw", count=next_draw))

        str_cfg = BUFF_CONFIG["strength"]
        gain_str = int(cfg.get("gain_strength", 0)) * cnt
        if gain_str > 0:
            cr.add_buff_to(p, "strength", str_cfg["name"], str_cfg["desc"], gain_str)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_strength", count=gain_str))

        temp_str = int(cfg.get("gain_temp_strength", 0)) * cnt
        if temp_str > 0:
            cr.add_buff_to(p, "strength", str_cfg["name"], str_cfg["desc"], temp_str)
            store_ts = run.node_data.setdefault("enchant_temp_strength", {})
            store_ts[uid] = int(store_ts.get(uid, 0)) + temp_str
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_temp_strength", count=temp_str))

        self_weak = int(cfg.get("self_weak", 0)) * cnt
        if self_weak > 0:
            cr.add_buff_to(p, "weak", get_locale_text("i18n_battle_core.buff_weak_name"), get_locale_text("i18n_battle_core.buff_weak_desc"), self_weak)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_self_weak", count=self_weak))

        self_vuln = int(cfg.get("self_vuln", 0)) * cnt
        if self_vuln > 0:
            cr.add_buff_to(p, "vulnerable", get_locale_text("i18n_battle_core.buff_vulnerable_name"), get_locale_text("i18n_battle_core.buff_vulnerable_desc"), self_vuln)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_self_vuln", count=self_vuln))

        enemy_str = int(cfg.get("enemy_strength", 0)) * cnt
        if enemy_str > 0:
            for e in run.enemies:
                if e.hp > 0:
                    cr.add_buff_to(e, "strength", str_cfg["name"], str_cfg["desc"], enemy_str)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_enemy_str", count=enemy_str))

        curse_n = int(cfg.get("add_curse_draw", 0)) * cnt
        if curse_n > 0:
            from ...models.state import CardState
            for _ in range(curse_n):
                p.draw_pile.append(CardState(id="curse_dazed"))
            random.shuffle(p.draw_pile)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_curse_added", count=curse_n))

        buff_target = target
        if not buff_target or not buff_target.startswith("e"):
            buff_target = engine._get_first_alive_enemy(run)
        target_enemy = None
        if buff_target and buff_target.startswith("e"):
            try:
                eidx = int(buff_target[1:]) - 1
                if 0 <= eidx < len(run.enemies) and run.enemies[eidx].hp > 0:
                    target_enemy = run.enemies[eidx]
            except ValueError:
                target_enemy = None

        app_vuln = int(cfg.get("apply_vuln", 0)) * cnt
        if app_vuln > 0 and target_enemy is not None:
            cr.add_buff_to(target_enemy, "vulnerable", get_locale_text("i18n_battle_core.buff_vulnerable_name"), get_locale_text("i18n_battle_core.buff_vulnerable_desc"), app_vuln)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_apply_vuln", name=target_enemy.name, count=app_vuln))

        app_weak = int(cfg.get("apply_weak", 0)) * cnt
        if app_weak > 0 and target_enemy is not None:
            cr.add_buff_to(target_enemy, "weak", get_locale_text("i18n_battle_core.buff_weak_name"), get_locale_text("i18n_battle_core.buff_weak_desc"), app_weak)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_apply_weak", name=target_enemy.name, count=app_weak))

        poison_cfg = BUFF_CONFIG["poison"]
        app_poison = int(cfg.get("apply_poison", 0)) * cnt
        if app_poison > 0 and target_enemy is not None:
            cr.add_buff_to(target_enemy, "poison", poison_cfg["name"], poison_cfg["desc"], app_poison)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_apply_poison", name=target_enemy.name, count=app_poison))

        app_poison_all = int(cfg.get("apply_poison_all", 0)) * cnt
        if app_poison_all > 0:
            for e in run.enemies:
                if e.hp > 0:
                    cr.add_buff_to(e, "poison", poison_cfg["name"], poison_cfg["desc"], app_poison_all)
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_apply_poison_all", count=app_poison_all))

        aoe_dmg = int(cfg.get("aoe_dmg", 0)) * cnt
        if aoe_dmg > 0:
            for i, e in enumerate(run.enemies, 1):
                if e.hp > 0:
                    cr.damage_target(run, f"e{i}", aoe_dmg, source="p0", damage_type="effect")
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_aoe", dmg=aoe_dmg))

        if cfg.get("purify_hand"):
            from ...entities.cards.base import ALL_CARDS
            purified = 0
            for h_state in list(p.hand):
                h_card = ALL_CARDS.get(h_state)
                if h_card is not None and getattr(h_card, "color", "") == "curse":
                    p.hand.remove(h_state)
                    p.exhaust_pile.append(h_state)
                    purified += 1
            if purified > 0:
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_purify", count=purified))

        copy_disc = int(cfg.get("copy_to_discard", 0)) * cnt
        if copy_disc > 0:
            for _ in range(copy_disc):
                p.discard_pile.append(DeckService.clone_state(c_state))
            engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_angry", name=card.name))

        if cfg.get("reshuffle_to_draw"):
            if p.discard_pile and p.discard_pile[-1] == c_state:
                moved = p.discard_pile.pop()
                p.draw_pile.append(moved)
                random.shuffle(p.draw_pile)
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_reshuffle", name=card.name))

        kill_gold = int(cfg.get("kill_gold", 0)) * cnt
        if kill_gold > 0:
            now_alive = sum(1 for e in run.enemies if e.hp > 0)
            kills = max(0, prev_alive_enemies - now_alive)
            if kills > 0:
                gain = kill_gold * kills
                p.gold += gain
                engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_greed", gold=gain))


def apply_grave_enchantments_at_battle_start(engine, run, p) -> None:
    moved = []
    for st in list(p.draw_pile):
        if "grave" in (getattr(st, "enchantments", None) or ()):
            p.draw_pile.remove(st)
            p.discard_pile.append(st)
            moved.append(st)
    if moved:
        engine._log_event(run, get_locale_text("i18n_enchantment.ui.log_grave", count=len(moved)))


def apply_enchantment_turn_start(engine, run, p) -> None:
    uid = run.uid_for(p) or run.user_id
    store_a = run.node_data.get("enchant_next_turn_a")
    if isinstance(store_a, dict):
        bonus_a = int(store_a.pop(uid, 0) or 0)
        if bonus_a > 0:
            p.actions += bonus_a
    store_d = run.node_data.get("enchant_next_turn_draw")
    if isinstance(store_d, dict):
        bonus_d = int(store_d.pop(uid, 0) or 0)
        if bonus_d > 0:
            engine.card_player.draw_cards(p, bonus_d, run)


def apply_enchantment_turn_end(run, p) -> None:
    uid = run.uid_for(p) or run.user_id
    store_ts = run.node_data.get("enchant_temp_strength")
    if isinstance(store_ts, dict):
        lose_str = int(store_ts.pop(uid, 0) or 0)
        if lose_str > 0:
            for b in list(p.buffs):
                if b.id == "strength":
                    b.stacks -= lose_str
                    if b.stacks == 0:
                        p.buffs.remove(b)
                    break
