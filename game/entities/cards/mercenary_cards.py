import random
from ...models.state import Card
from ...data.locale_data import get_locale_text
from ...data.buff_data import BUFF_CONFIG
from ...data.mercenary_card_data import MERCENARY_CARD_CONFIG
from .registry import register_card
from .coop import _resolve_ally


def _pale_buff_meta():
    cfg = BUFF_CONFIG.get("pale_entropy", {})
    return cfg.get("name", "pale_entropy"), cfg.get("desc", "")


def _apply_pale_entropy(engine, entity, stacks: int):
    if stacks <= 0 or entity is None:
        return
    name, desc = _pale_buff_meta()
    engine._add_buff_to(entity, "pale_entropy", name, desc, stacks)


def _apply_weak(engine, entity, stacks: int):
    if stacks <= 0 or entity is None:
        return
    engine._add_buff_to(
        entity,
        "weak",
        get_locale_text("i18n_cards_neutral.neutral.buffs.weak.name"),
        get_locale_text("i18n_cards_neutral.neutral.buffs.weak.desc"),
        stacks,
    )


def _apply_vulnerable(engine, entity, stacks: int):
    if stacks <= 0 or entity is None:
        return
    engine._add_buff_to(
        entity,
        "vulnerable",
        get_locale_text("i18n_cards_neutral.neutral.buffs.vulnerable.name"),
        get_locale_text("i18n_cards_neutral.neutral.buffs.vulnerable.desc"),
        stacks,
    )


def _apply_strength(engine, entity, stacks: int):
    if stacks <= 0 or entity is None:
        return
    engine._add_buff_to(
        entity,
        "strength",
        get_locale_text("i18n_cards_neutral.neutral.buffs.strength.name"),
        get_locale_text("i18n_cards_neutral.neutral.buffs.strength.desc"),
        stacks,
    )


def _enemy_index_from_target(run, target):
    if target and isinstance(target, str) and target.startswith("e"):
        try:
            idx = int(target[1:]) - 1
            if 0 <= idx < len(run.enemies) and run.enemies[idx].hp > 0:
                return idx
        except ValueError:
            pass
    for idx, enemy in enumerate(run.enemies):
        if enemy.hp > 0:
            return idx
    return None


def _feedback(card_id: str, **kwargs) -> str:
    tpl = MERCENARY_CARD_CONFIG.get(card_id, {}).get("feedback", "")
    try:
        return tpl.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return tpl


@register_card("pale_interference")
class PaleInterferenceCard(Card):
    def execute(self, run, target, engine) -> str:
        idx = _enemy_index_from_target(run, target)
        if idx is None:
            return ""
        enemy = run.enemies[idx]
        t_ref = f"e{idx + 1}"
        dmg = getattr(self, "base_dmg", 6)
        stacks = getattr(self, "buff_stacks", 2)
        engine._damage_target(run, t_ref, dmg, source="p0", damage_type="psychic", card=self)
        if enemy.hp > 0:
            _apply_pale_entropy(engine, enemy, stacks)
        return _feedback("pale_interference", target=enemy.name)


@register_card("pale_two_mm_hole")
class PaleTwoMmHoleCard(Card):
    def execute(self, run, target, engine) -> str:
        idx = _enemy_index_from_target(run, target)
        if idx is None:
            return ""
        enemy = run.enemies[idx]
        t_ref = f"e{idx + 1}"
        has_pale = any(b.id == "pale_entropy" and b.stacks > 0 for b in enemy.buffs)
        dmg = getattr(self, "base_dmg", 8)
        engine._damage_target(run, t_ref, dmg, source="p0", damage_type="psychic", card=self)
        if has_pale:
            engine._draw_cards(run.player, getattr(self, "draw_count", 1), run)
            if enemy.hp > 0:
                _apply_weak(engine, enemy, getattr(self, "buff_stacks", 1))
        return _feedback("pale_two_mm_hole")


@register_card("pale_crossing")
class PaleCrossingCard(Card):
    def execute(self, run, target, engine) -> str:
        hp_cost = getattr(self, "self_hp_cost", 3)
        if hp_cost > 0:
            engine._damage_target(run, "p0", hp_cost, source="p0", damage_type="true", card=self)
        if run.player.hp <= 0:
            return _feedback("pale_crossing")
        engine._gain_shield(run, "p0", getattr(self, "shield_amount", 10))
        stacks = getattr(self, "buff_stacks", 3)
        for enemy in list(run.enemies):
            if enemy.hp > 0:
                _apply_pale_entropy(engine, enemy, stacks)
        engine._draw_cards(run.player, getattr(self, "draw_count", 2), run)
        return _feedback("pale_crossing")


@register_card("pale_lathe_memory")
class PaleLatheMemoryCard(Card):
    def execute(self, run, target, engine) -> str:
        resolved = _resolve_ally(engine, run, target, allow_self=True)
        heal = getattr(self, "heal_amount", 4)
        if resolved:
            from ...core.battle.party_battle import party_target_ref
            uid, _, grid = resolved
            ref = party_target_ref(run, uid, grid)
            engine._heal_target(run, ref, heal)
        else:
            engine._heal_target(run, "p0", heal)
        engine._draw_cards(run.player, getattr(self, "draw_count", 2), run)
        return _feedback("pale_lathe_memory")


@register_card("pale_white_noise")
class PaleWhiteNoiseCard(Card):
    def execute(self, run, target, engine) -> str:
        engine._gain_shield(run, "p0", getattr(self, "shield_amount", 8))
        alive = [e for e in run.enemies if e.hp > 0]
        if alive:
            _apply_pale_entropy(engine, random.choice(alive), getattr(self, "buff_stacks", 1))
        return _feedback("pale_white_noise")


@register_card("pale_porch_collapse")
class PalePorchCollapseCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 12)
        mult = getattr(self, "multiplier", 2)
        for idx in range(len(run.enemies) - 1, -1, -1):
            enemy = run.enemies[idx]
            if enemy.hp <= 0:
                continue
            t_ref = f"e{idx + 1}"
            pale_buff = next((b for b in enemy.buffs if b.id == "pale_entropy"), None)
            stacks = pale_buff.stacks if pale_buff else 0
            engine._damage_target(run, t_ref, dmg, source="p0", damage_type="psychic", card=self)
            if stacks > 0 and idx < len(run.enemies) and run.enemies[idx].hp > 0:
                det_dmg = stacks * mult
                if pale_buff in run.enemies[idx].buffs:
                    run.enemies[idx].buffs.remove(pale_buff)
                engine._log_event(run, get_locale_text("i18n_mercenary.pale_entropy_detonate", target=enemy.name, stacks=stacks, dmg=det_dmg))
                engine._damage_target(run, t_ref, det_dmg, source="p0", damage_type="psychic", card=self)
        return _feedback("pale_porch_collapse")


@register_card("thought_aces_high")
class ThoughtAcesHighCard(Card):
    def execute(self, run, target, engine) -> str:
        resolved = _resolve_ally(engine, run, target, allow_self=True)
        shield = getattr(self, "shield_amount", 10)
        strength = getattr(self, "strength_gain", 2)
        draw_count = getattr(self, "draw_count", 1)
        if resolved:
            from ...core.battle.party_battle import party_target_ref
            uid, ally_p, grid = resolved
            ref = party_target_ref(run, uid, grid)
            target_entity = ally_p.minions.get(grid) if grid else ally_p
            engine._gain_shield(run, ref, shield)
            _apply_strength(engine, target_entity, strength)
            if target_entity.max_hp > 0 and target_entity.hp * 2 > target_entity.max_hp:
                engine._draw_cards(run.player, draw_count, run)
        else:
            engine._gain_shield(run, "p0", shield)
            _apply_strength(engine, run.player, strength)
            if run.player.max_hp > 0 and run.player.hp * 2 > run.player.max_hp:
                engine._draw_cards(run.player, draw_count, run)
        return _feedback("thought_aces_high")


@register_card("thought_aces_low")
class ThoughtAcesLowCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        base_heal = getattr(self, "heal_amount", 6)
        low_hp = p.max_hp > 0 and p.hp * 100 < p.max_hp * 60
        if low_hp:
            heal = base_heal + (5 if self.upgraded else 4)
            engine._heal_target(run, "p0", heal)
            p.actions += getattr(self, "action_gain", 1)
        else:
            engine._heal_target(run, "p0", base_heal)
            engine._draw_cards(p, getattr(self, "draw_count", 1), run)
        return _feedback("thought_aces_low")


@register_card("thought_actual_art_degree")
class ThoughtActualArtDegreeCard(Card):
    def execute(self, run, target, engine) -> str:
        engine._gain_shield(run, "p0", getattr(self, "shield_amount", 8))
        engine._draw_cards(run.player, getattr(self, "draw_count", 2), run)
        idx = _enemy_index_from_target(run, target)
        if idx is not None and run.enemies[idx].hp > 0:
            _apply_weak(engine, run.enemies[idx], getattr(self, "buff_stacks", 2))
        return _feedback("thought_actual_art_degree")


@register_card("thought_advanced_race_theory")
class ThoughtAdvancedRaceTheoryCard(Card):
    def execute(self, run, target, engine) -> str:
        hp_cost = getattr(self, "self_hp_cost", 2)
        if hp_cost > 0:
            engine._damage_target(run, "p0", hp_cost, source="p0", damage_type="true", card=self)
        idx = _enemy_index_from_target(run, target)
        if idx is not None:
            enemy = run.enemies[idx]
            engine._damage_target(run, f"e{idx + 1}", getattr(self, "base_dmg", 7), source="p0", damage_type="psychic", card=self)
            if enemy.hp > 0:
                _apply_vulnerable(engine, enemy, getattr(self, "buff_stacks", 2))
        return _feedback("thought_advanced_race_theory")


@register_card("thought_anti_object_task_force")
class ThoughtAntiObjectTaskForceCard(Card):
    def execute(self, run, target, engine) -> str:
        idx = _enemy_index_from_target(run, target)
        if idx is None:
            return ""
        enemy = run.enemies[idx]
        had_shield = enemy.shield > 0
        strip = getattr(self, "absorb_amount", 12)
        if enemy.shield > 0:
            enemy.shield = max(0, enemy.shield - strip)
        engine._damage_target(run, f"e{idx + 1}", getattr(self, "base_dmg", 11), source="p0", damage_type="bludgeoning", card=self)
        if (had_shield and enemy.shield <= 0) or enemy.hp <= 0:
            run.player.bonus_actions += getattr(self, "bonus_action_gain", 1)
        return _feedback("thought_anti_object_task_force")


@register_card("thought_apricot_chewing_gum")
class ThoughtApricotChewingGumCard(Card):
    def execute(self, run, target, engine) -> str:
        hp_cost = getattr(self, "self_hp_cost", 3)
        if hp_cost > 0:
            engine._damage_target(run, "p0", hp_cost, source="p0", damage_type="true", card=self)
        if run.player.hp <= 0:
            return _feedback("thought_apricot_chewing_gum")
        run.player.actions += getattr(self, "action_gain", 1)
        run.player.bonus_actions += getattr(self, "bonus_action_gain", 1)
        stacks = getattr(self, "buff_stacks", 2)
        for enemy in list(run.enemies):
            if enemy.hp > 0:
                _apply_pale_entropy(engine, enemy, stacks)
        return _feedback("thought_apricot_chewing_gum")


@register_card("thought_arno_van_eyck")
class ThoughtArnoVanEyckCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 7)
        for idx in range(len(run.enemies) - 1, -1, -1):
            if run.enemies[idx].hp > 0:
                engine._damage_target(run, f"e{idx + 1}", dmg, source="p0", damage_type="thunder", card=self)
        ba_gain = getattr(self, "bonus_action_gain", 1)
        alive = [run.players[uid] for uid in run.party_order if uid in run.players and run.players[uid].hp > 0 and not run.players[uid].downed]
        if self.upgraded:
            for member in alive:
                member.bonus_actions += ba_gain
        elif alive:
            random.choice(alive).bonus_actions += ba_gain
        return _feedback("thought_arno_van_eyck")


@register_card("thought_bankruptcy_sequence")
class ThoughtBankruptcySequenceCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        gold_cost = getattr(self, "gold_cost", 5)
        hp_cost = getattr(self, "self_hp_cost", 3)
        if p.gold >= gold_cost:
            p.gold -= gold_cost
            extra = get_locale_text("i18n_mercenary.bankruptcy_paid_gold", gold=gold_cost)
        else:
            engine._damage_target(run, "p0", hp_cost, source="p0", damage_type="true", card=self)
            extra = get_locale_text("i18n_mercenary.bankruptcy_paid_hp", hp=hp_cost)
        if p.hp > 0:
            p.actions += getattr(self, "action_gain", 1)
            p.bonus_actions += getattr(self, "bonus_action_gain", 1)
            engine._draw_cards(p, getattr(self, "draw_count", 2), run)
        return _feedback("thought_bankruptcy_sequence") + " " + extra


@register_card("thought_boiadeiro")
class ThoughtBoiadeiroCard(Card):
    def execute(self, run, target, engine) -> str:
        idx = _enemy_index_from_target(run, target)
        if idx is None:
            return ""
        played_count = run.node_data.get(run.turn_key("cards_played_this_turn", run.player), 0)
        dmg = getattr(self, "base_dmg", 9)
        if played_count == 0:
            dmg += getattr(self, "bonus_damage", 5)
        engine._damage_target(run, f"e{idx + 1}", dmg, source="p0", damage_type="piercing", card=self)
        return _feedback("thought_boiadeiro")


@register_card("thought_bringing_of_the_law")
class ThoughtBringingOfTheLawCard(Card):
    def execute(self, run, target, engine) -> str:
        idx = _enemy_index_from_target(run, target)
        if idx is None:
            return ""
        enemy = run.enemies[idx]
        has_status = any(b.id in ("vulnerable", "pale_entropy") and b.stacks > 0 for b in enemy.buffs)
        engine._damage_target(run, f"e{idx + 1}", getattr(self, "base_dmg", 16), source="p0", damage_type="bludgeoning", card=self)
        msg = _feedback("thought_bringing_of_the_law")
        if enemy.hp > 0:
            if self.upgraded:
                _apply_vulnerable(engine, enemy, getattr(self, "buff_stacks", 2))
            if self.upgraded or has_status or random.random() < 0.60:
                engine._add_buff_to(
                    enemy,
                    "stun",
                    get_locale_text("i18n_cards_neutral.neutral.buffs.stun.name"),
                    get_locale_text("i18n_cards_neutral.neutral.buffs.stun.desc"),
                    getattr(self, "buff_turns", 1),
                )
                msg += " " + get_locale_text("i18n_mercenary.law_stun_success", target=enemy.name)
        return msg


@register_card("thought_caustic_echo")
class ThoughtCausticEchoCard(Card):
    def execute(self, run, target, engine) -> str:
        idx = _enemy_index_from_target(run, target)
        if idx is None:
            return ""
        enemy = run.enemies[idx]
        t_ref = f"e{idx + 1}"
        engine._damage_target(run, t_ref, getattr(self, "base_dmg", 8), source="p0", damage_type="psychic", card=self)
        msg = _feedback("thought_caustic_echo")
        if enemy.hp > 0:
            pale = next((b for b in enemy.buffs if b.id == "pale_entropy" and b.stacks > 0), None)
            if pale:
                hits = getattr(self, "hit_count", 1)
                for _ in range(hits):
                    if idx >= len(run.enemies) or run.enemies[idx].hp <= 0:
                        break
                    extra_dmg = pale.stacks
                    engine._damage_target(run, t_ref, extra_dmg, source="p0", damage_type="psychic", card=self)
                    msg += " " + get_locale_text("i18n_mercenary.caustic_echo_trigger", target=enemy.name, dmg=extra_dmg)
        return msg


@register_card("thought_cleaning_out_the_rooms")
class ThoughtCleaningOutTheRoomsCard(Card):
    def execute(self, run, target, engine) -> str:
        from ..buffs.base import is_debuff
        p = run.player
        engine._gain_shield(run, "p0", getattr(self, "shield_amount", 7))
        engine._draw_cards(p, getattr(self, "draw_count", 2), run)
        to_purge = getattr(self, "count", 1)
        removed = 0
        for buff in list(p.buffs):
            if removed >= to_purge:
                break
            if is_debuff(buff.id):
                p.buffs.remove(buff)
                removed += 1
        msg = _feedback("thought_cleaning_out_the_rooms")
        if removed > 0:
            msg += " " + get_locale_text("i18n_mercenary.cleaning_purged", count=removed)
        return msg


@register_card("thought_coach_physical_instrument")
class ThoughtCoachPhysicalInstrumentCard(Card):
    def execute(self, run, target, engine) -> str:
        _apply_strength(engine, run.player, getattr(self, "strength_gain", 2))
        engine._gain_shield(run, "p0", getattr(self, "shield_amount", 6))
        return _feedback("thought_coach_physical_instrument")


@register_card("thought_col_do_ma_ma_daqua")
class ThoughtColDoMaMaDaquaCard(Card):
    def execute(self, run, target, engine) -> str:
        pale_stacks = getattr(self, "buff_stacks", 2)
        vuln_stacks = 2 if self.upgraded else 1
        for enemy in list(run.enemies):
            if enemy.hp > 0:
                _apply_pale_entropy(engine, enemy, pale_stacks)
                _apply_vulnerable(engine, enemy, vuln_stacks)
        engine._draw_cards(run.player, getattr(self, "draw_count", 1), run)
        return _feedback("thought_col_do_ma_ma_daqua")


@register_card("thought_cop_of_the_apocalypse")
class ThoughtCopOfTheApocalypseCard(Card):
    def execute(self, run, target, engine) -> str:
        hp_cost = getattr(self, "self_hp_cost", 4)
        if hp_cost > 0:
            engine._damage_target(run, "p0", hp_cost, source="p0", damage_type="true", card=self)
        if run.player.hp <= 0:
            return _feedback("thought_cop_of_the_apocalypse")
        dmg = getattr(self, "base_dmg", 14)
        stacks = getattr(self, "buff_stacks", 3)
        for idx in range(len(run.enemies) - 1, -1, -1):
            enemy = run.enemies[idx]
            if enemy.hp <= 0:
                continue
            engine._damage_target(run, f"e{idx + 1}", dmg, source="p0", damage_type="psychic", card=self)
            if idx < len(run.enemies) and run.enemies[idx].hp > 0:
                _apply_pale_entropy(engine, run.enemies[idx], stacks)
        return _feedback("thought_cop_of_the_apocalypse")
