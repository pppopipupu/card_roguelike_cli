from .base import BuffImpl, is_debuff
from .registry import register_buff
from ...data.buff_data import BUFF_CONFIG
from ...data.locale_data import get_locale_text
from ...data.damage_type_data import PHYSICAL_DAMAGE_TYPES


def _stat(instance, buff_id, name, default):
    cfg = BUFF_CONFIG.get(buff_id, {})
    return getattr(instance, name, cfg.get(name, default))


def _damage_type_str(event):
    return event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)


def _enemy_ref(run, enemy):
    try:
        idx = run.enemies.index(enemy)
    except ValueError:
        return ""
    return f"e{idx + 1}"


def _entity_for_ref(run, ref):
    if not ref or not isinstance(ref, str):
        return None
    if ref == "p0":
        return run.player
    if ref.startswith("p") and ref[1:].isdigit():
        return run.player.minions.get(ref[1:])
    if ref.startswith("e") and ref[1:].isdigit():
        idx = int(ref[1:]) - 1
        if 0 <= idx < len(run.enemies):
            return run.enemies[idx]
    return None


def _matches_enemy(entity, locale_key):
    target = get_locale_text(locale_key)
    if not target:
        return False
    return bool(getattr(entity, "name", "")) and entity.name.startswith(target)


def _add_strength(engine, entity, stacks):
    engine._add_buff_to(
        entity,
        "strength",
        get_locale_text("i18n_battle_core.buff_strength_name"),
        get_locale_text("i18n_battle_core.buff_strength_desc"),
        stacks,
    )


def _add_minor_vulnerable(engine, entity, stacks=1):
    engine._add_buff_to(
        entity,
        "minor_vulnerable",
        get_locale_text("i18n_cards_neutral.neutral.buffs.minor_vulnerable.name"),
        get_locale_text("i18n_cards_neutral.neutral.buffs.minor_vulnerable.desc"),
        stacks,
    )


def _add_cold_vulnerable(engine, entity, stacks=1):
    engine._add_buff_to(
        entity,
        "minor_vulnerable_cold",
        get_locale_text("i18n_battle_core.buff_minor_vulnerable_cold_name"),
        get_locale_text("i18n_battle_core.buff_minor_vulnerable_cold_desc"),
        stacks,
    )


@register_buff("dragon_scales_passive")
class DragonScalesPassiveBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        run = event.run
        if event.is_player or entity not in run.enemies:
            return
        if entity.shield != 0:
            return
        grid = _enemy_ref(run, entity)
        if not grid:
            return
        shield = _stat(self, "dragon_scales_passive", "start_shield", 8)
        event.engine._gain_shield(run, grid, shield)
        event.engine._log_event(
            run,
            get_locale_text("i18n_buffs.dragon_scales_shield_log", entity=entity.name, shield=shield),
        )

    def on_damage_take_defend(self, event, buff_state, entity, engine):
        if entity.shield <= 0:
            return
        if _damage_type_str(event) not in PHYSICAL_DAMAGE_TYPES:
            return
        attacker = _entity_for_ref(event.run, event.source)
        if attacker is None:
            return
        damage = _stat(self, "dragon_scales_passive", "thorns_damage", 2)
        stacks = _stat(self, "dragon_scales_passive", "burn_stacks", 1)
        turns = _stat(self, "dragon_scales_passive", "burn_turns", 2)
        engine._damage_target(
            event.run,
            event.source,
            damage,
            source=f"buff:{get_locale_text('i18n_buffs.dragon_scales_passive_name')}",
            damage_type="fire",
        )
        engine._add_buff_to(
            attacker,
            "burning",
            get_locale_text("i18n_battle_core.buff_burning_name"),
            get_locale_text("i18n_battle_core.buff_burning_desc"),
            stacks,
            turns,
        )
        engine._log_event(
            event.run,
            get_locale_text("i18n_buffs.dragon_scales_reflect_log", entity=entity.name, damage=damage, stacks=stacks),
        )


@register_buff("storm_field_passive")
class StormFieldPassiveBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        run = event.run
        grid = _enemy_ref(run, entity)
        if not grid or event.source != grid:
            return
        if _damage_type_str(event) not in ("lightning", "thunder"):
            return
        orb_count = sum(
            1
            for enemy in run.enemies
            if enemy.hp > 0 and _matches_enemy(enemy, "i18n_enemy_misc.thunder_orb.name")
        )
        if orb_count <= 0:
            return
        event.modified_damage += _stat(self, "storm_field_passive", "bonus_per_orb", 2) * orb_count


@register_buff("permafrost_aura_passive")
class PermafrostAuraPassiveBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        run = event.run
        p = run.player
        if p is None or p.hp <= 0:
            return
        played = run.node_data.get(run.turn_key("cards_played_this_turn", p), 0)
        if played < _stat(self, "permafrost_aura_passive", "card_threshold", 4):
            return
        if not any(b.id == "minor_vulnerable_cold" for b in p.buffs):
            return
        damage = _stat(self, "permafrost_aura_passive", "chill_damage", 2)
        event.engine._damage_target(run, "p0", damage, source=f"enemy:{entity.name}", damage_type="cold")
        event.engine._log_event(
            run,
            get_locale_text("i18n_buffs.permafrost_chill_log", entity=entity.name, damage=damage),
        )

    def on_turn_end(self, event, buff_state, entity):
        if event.is_player:
            return
        run = event.run
        if getattr(run, "coop_id", ""):
            targets = list(run.players.values())
        else:
            targets = [run.player]
        for p in targets:
            if p is None or p.hp <= 0 or getattr(p, "downed", False) or p.shield != 0:
                continue
            _add_cold_vulnerable(event.engine, p, 1)
            event.engine._log_event(run, get_locale_text("i18n_buffs.permafrost_expose_log"))


@register_buff("pure_vessel_body_passive")
class PureVesselBodyPassiveBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        run = event.run
        if event.is_player or entity not in run.enemies:
            return
        removed = False
        for buff in list(entity.buffs):
            if buff.id in ("bleed", "poison"):
                entity.buffs.remove(buff)
                removed = True
        for buff in list(entity.buffs):
            if buff is buff_state:
                continue
            if buff.id in ("bleed", "poison"):
                continue
            if is_debuff(buff.id):
                entity.buffs.remove(buff)
                removed = True
                break
        if removed:
            event.engine._log_event(
                run,
                get_locale_text("i18n_buffs.pure_vessel_body_cleanse_log", entity=entity.name),
            )


@register_buff("pure_parry_stance")
class PureParryStanceBuff(BuffImpl):
    def on_damage_take_defend(self, event, buff_state, entity, engine):
        run = event.run
        if entity.shield <= 0:
            if buff_state in entity.buffs:
                entity.buffs.remove(buff_state)
            _add_minor_vulnerable(engine, entity, 1)
            engine._log_event(
                run,
                get_locale_text("i18n_buffs.pure_parry_break_log", entity=entity.name),
            )
            return
        if _damage_type_str(event) not in PHYSICAL_DAMAGE_TYPES:
            return
        cid = run.node_data.get("current_playing_card_cid")
        if not cid or run.node_data.get("pure_parry_counter_cid") == cid:
            return
        run.node_data["pure_parry_counter_cid"] = cid
        damage = _stat(self, "pure_parry_stance", "counter_damage", 8)
        engine._damage_target(
            run,
            event.source,
            damage,
            source=f"buff:{get_locale_text('i18n_buffs.pure_parry_stance_name')}",
            damage_type="slashing",
        )
        engine._log_event(
            run,
            get_locale_text("i18n_buffs.pure_parry_counter_log", entity=entity.name, damage=damage),
        )


@register_buff("pure_focus_charge")
class PureFocusChargeBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies:
            return
        if entity.shield != 0:
            return
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        _add_minor_vulnerable(event.engine, entity, 1)
        event.engine._log_event(
            event.run,
            get_locale_text("i18n_buffs.pure_focus_charge_interrupt_log", entity=entity.name),
        )


@register_buff("molten_charge")
class MoltenChargeBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies:
            return
        if entity.shield != 0:
            return
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        _add_minor_vulnerable(event.engine, entity, 1)
        event.engine._log_event(
            event.run,
            get_locale_text("i18n_buffs.molten_charge_interrupt_log", entity=entity.name),
        )


@register_buff("cthulhu_mist_immune")
class CthulhuMistImmuneBuff(BuffImpl):
    def _block(self, event):
        run = event.run
        if run.node_data.get("current_playing_card_id") == "neutral_banish_slash":
            return
        if run.node_data.get("cthulhu_final_crash"):
            return
        event.modified_damage = 0

    def on_damage_calculate(self, event, buff_state, entity):
        if event.target != _enemy_ref(event.run, entity):
            return
        self._block(event)

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.target != _enemy_ref(event.run, entity):
            return
        self._block(event)


@register_buff("doom_furnace_passive")
class DoomFurnacePassiveBuff(BuffImpl):
    def on_damage_take_defend(self, event, buff_state, entity, engine):
        if event.amount <= 0:
            return
        _add_strength(engine, entity, 1)
        engine._log_event(
            event.run,
            get_locale_text("i18n_buffs.doom_furnace_strength_log", entity=entity.name),
        )


@register_buff("soul_phylactery_passive")
class SoulPhylacteryPassiveBuff(BuffImpl):
    def _reduce(self, event, buff_state, entity):
        run = event.run
        if event.target != _enemy_ref(run, entity):
            return
        has_skeleton = any(
            enemy.hp > 0 and _matches_enemy(enemy, "i18n_enemy_misc.skeleton_minion.name")
            for enemy in run.enemies
        )
        if not has_skeleton:
            return
        before = event.modified_damage
        reduction = _stat(self, "soul_phylactery_passive", "damage_reduction", 0.3)
        reduced = int(before * (1 - reduction))
        if reduced >= before:
            return
        event.modified_damage = reduced
        event.engine._log_event(
            run,
            get_locale_text("i18n_buffs.soul_phylactery_reduce_log", entity=entity.name, damage=before - reduced),
        )

    def on_damage_calculate(self, event, buff_state, entity):
        self._reduce(event, buff_state, entity)

    def on_damage_calculate_defend(self, event, buff_state, entity):
        self._reduce(event, buff_state, entity)


@register_buff("dream_eater_passive")
class DreamEaterPassiveBuff(BuffImpl):
    def on_card_exhaust(self, event, buff_state, entity):
        run = event.run
        grid = _enemy_ref(run, entity)
        engine = getattr(event, "engine", None)
        if not grid or engine is None:
            return
        shield = _stat(self, "dream_eater_passive", "shield_gain", 4)
        heal = _stat(self, "dream_eater_passive", "heal_gain", 3)
        engine._gain_shield(run, grid, shield)
        engine._heal_target(run, grid, heal)
        engine._log_event(
            run,
            get_locale_text("i18n_buffs.dream_eater_shield_log", entity=entity.name, shield=shield, heal=heal),
        )


@register_buff("stars_misaligned")
class StarsMisalignedBuff(BuffImpl):
    def _multiply(self, event):
        multiplier = _stat(self, "stars_misaligned", "damage_multiplier", 1.5)
        event.modified_damage = int(event.modified_damage * multiplier)

    def on_damage_calculate(self, event, buff_state, entity):
        if event.target != _enemy_ref(event.run, entity):
            return
        self._multiply(event)

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.target != _enemy_ref(event.run, entity):
            return
        self._multiply(event)


@register_buff("baguwen_restriction")
class BaguwenRestrictionBuff(BuffImpl):
    def _hand_has_card(self, hand, required):
        from ...models.state import ensure_card_state
        required_id = required.get("id", "")
        required_upgraded = bool(required.get("upgraded", False))
        for state in hand:
            parsed = ensure_card_state(state)
            if parsed.id == required_id and bool(parsed.upgraded) == required_upgraded:
                return True
        return False

    def on_card_play(self, event, buff_state, entity):
        run = event.run
        if event.cancelled or entity is not run.player:
            return
        checked_key = run.turn_key("baguwen_checked", entity)
        if run.node_data.get(checked_key):
            return
        run.node_data[checked_key] = True
        required = run.node_data.get(run.turn_key("baguwen_required_card", entity))
        if not required:
            return
        card = event.card
        if card is None:
            return
        if card.id == required.get("id") and bool(card.upgraded) == bool(required.get("upgraded", False)):
            success_key = "i18n_buffs.baguwen_success_log"
            success_text = get_locale_text(success_key)
            if success_text == success_key:
                fallback_key = "i18n_buffs.baguwen_passed_log"
                success_text = get_locale_text(fallback_key)
                if success_text == fallback_key:
                    success_text = ""
            if success_text:
                event.engine._log_event(run, success_text)
            return
        if not self._hand_has_card(entity.hand, required):
            return
        damage = _stat(self, "baguwen_restriction", "violation_damage", 10)
        event.engine._damage_target(
            run,
            "p0",
            damage,
            source=f"buff:{get_locale_text('i18n_buffs.baguwen_restriction_name')}",
            damage_type="necrotic",
        )
        event.engine._log_event(
            run,
            get_locale_text("i18n_buffs.baguwen_violation_log", damage=damage),
        )


@register_buff("shroud_time_warp")
class ShroudTimeWarpBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if getattr(event, "is_extra", False):
            return
        run = event.run
        buff_state.stacks += 1
        card_limit = _stat(self, "shroud_time_warp", "card_limit", 12)
        if buff_state.stacks < card_limit:
            return
        buff_state.stacks = 0
        heal = _stat(self, "shroud_time_warp", "heal_val", 12)
        shield = _stat(self, "shroud_time_warp", "shield_val", 15)
        strength = _stat(self, "shroud_time_warp", "strength_val", 2)
        engine = event.engine
        engine._log_event(
            run,
            get_locale_text("i18n_buffs.shroud_time_warp_log", entity=entity.name, count=card_limit),
        )
        for target in list(run.enemies):
            if target.hp <= 0 or not _matches_enemy(target, "i18n_enemy_elite_c.shroud_shadow_name"):
                continue
            grid = _enemy_ref(run, target)
            if not grid:
                continue
            engine._heal_target(run, grid, heal)
            engine._gain_shield(run, grid, shield)
            _add_strength(engine, target, strength)
            engine._log_event(
                run,
                get_locale_text(
                    "i18n_buffs.shroud_time_warp_empower_log",
                    entity=target.name,
                    heal=heal,
                    shield=shield,
                    stacks=strength,
                ),
            )
        run.node_data["force_end_turn"] = True
        run.node_data["force_end_turn_uid"] = run.user_id
