from typing import List, Optional
import re
from .base import BuffImpl, is_debuff, is_damage_event_from_entity
from .registry import register_buff
from ...core.battle.event_bus import PRIORITY_MODIFIER_ADD
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.text.locale_data import get_locale_text
from ...data.battle.damage_type_data import damage_type_matches, is_physical_damage, is_spell_card_damage

def _stat(instance, buff_id, name, default):
    cfg = BUFF_CONFIG.get(buff_id, {})
    return getattr(instance, name, cfg.get(name, default))

class QuickenBuff(BuffImpl):
    def on_card_play(self, event, buff_state, entity):
        if entity == event.run.player and event.card.type == "spell":
            event.cost_ba = max(0, event.cost_ba - buff_state.stacks)

    def modify_spell_cost_ba(self, run, card, cost_ba: int, engine) -> int:
        if card.type == "spell":
            return max(0, cost_ba - self.stacks)
        return cost_ba

class SpellSurgeBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        from ..cards.base import card_matches_color
        if entity == event.run.player and card_matches_color(event.card, "wizard"):
            event.engine._draw_cards(event.run.player, buff_state.stacks, event.run)

    def on_card_played_legacy(self, run, card, target: str, engine) -> str:
        from ..cards.base import card_matches_color
        if card_matches_color(card, "wizard"):
            engine._draw_cards(run.player, self.stacks, run)
        return ""

class ArcaneChargeBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and is_spell_card_damage(event) and event.source == "p0":
            event.modified_damage += buff_state.stacks * _stat(self, "arcane_charge", "dmg_per_stack", 3)

class EchoFormBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity != event.run.player:
            return
        if getattr(event, "is_extra", False):
            return
        played_count = event.run.node_data.get(event.run.turn_key("cards_played_this_turn", entity), 0)
        stacks = buff_state.stacks
        card_id = event.card.id
        if card_id.startswith("duel_"):
            card_id = card_id[5:]
        if card_id.startswith("echo_form"):
            stacks = max(0, stacks - 1)
        num_echoes = min(_stat(self, "echo_form", "max_echoes", 5), max(0, stacks - _stat(self, "echo_form", "echo_stack_cost", 5) * played_count))
        if num_echoes > 0:
            for _ in range(num_echoes):
                if event.engine.is_battle_won(event.run):
                    break
                extra_res = event.engine._execute_card_effect(event.run, event.card, event.target)
                from ...models.events import CardExtraTriggerEvent, CardPlayedEvent
                played_evt = CardPlayedEvent(event.run, event.card, event.target, extra_res, is_extra=True)
                event.engine.event_bus.dispatch(played_evt)
                event.engine.event_bus.dispatch(CardExtraTriggerEvent(event.run, event.card, "echo"))
                event.run.node_data.setdefault("extra_play_msgs", []).append(get_locale_text("i18n_buffs.echo_trigger_msg", res=played_evt.feedback))

    def on_card_played_legacy(self, run, card, target: str, engine) -> str:
        played_count = run.node_data.get(run.turn_key("cards_played_this_turn", run.player), 0)
        stacks = self.stacks
        card_id = card.id
        if card_id.startswith("duel_"):
            card_id = card_id[5:]
        if card_id.startswith("echo_form"):
            stacks = max(0, stacks - 1)
        num_echoes = min(_stat(self, "echo_form", "max_echoes", 5), max(0, stacks - _stat(self, "echo_form", "echo_stack_cost", 5) * played_count))
        res = ""
        if num_echoes > 0:
            for _ in range(num_echoes):
                if engine.is_battle_won(run):
                    break
                extra_res = engine._execute_card_effect(run, card, target)
                run.node_data.setdefault("extra_play_msgs", []).append(get_locale_text("i18n_buffs.echo_trigger_msg", res=extra_res))
        return ""

class IronWillBuff(BuffImpl):
    def on_heal(self, event, buff_state, entity):
        if event.target == "p0":
            if buff_state.stacks2 is not None and buff_state.stacks2 > 0:
                event.amount = event.amount * _stat(self, "iron_will", "heal_multiplier", 2)
            p = event.run.player
            val = _stat(self, "iron_will", "upgraded_max_hp_per_stack", 15) if self.upgraded else _stat(self, "iron_will", "max_hp_per_stack", 10)
            limit = p.max_hp + buff_state.stacks * val
            if p.hp + event.amount > limit:
                event.amount = max(0, limit - p.hp)

    def on_heal_calculate(self, event, buff_state, entity):
        if event.target == "p0":
            val = _stat(self, "iron_will", "upgraded_max_hp_per_stack", 15) if self.upgraded else _stat(self, "iron_will", "max_hp_per_stack", 10)
            event.modified_max_hp = event.modified_max_hp + buff_state.stacks * val

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            if buff_state.stacks2 is not None and buff_state.stacks2 > 0:
                buff_state.stacks2 -= 1

class MagicNetworkBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player and event.card.type == "spell":
            damage_amount = _stat(self, "magic_network", "damage_amount", 3)
            shield_amount = _stat(self, "magic_network", "shield_amount", 3)
            for idx, enemy in enumerate(list(event.run.enemies)):
                event.engine._damage_target(event.run, f"e{idx+1}", damage_amount)
            event.engine._gain_shield(event.run, "p0", shield_amount)
            event.feedback += get_locale_text("i18n_buffs.magic_network_feedback", damage=damage_amount, shield=shield_amount)

    def on_card_played_legacy(self, run, card, target: str, engine) -> str:
        res = ""
        if card.type == "spell":
            damage_amount = _stat(self, "magic_network", "damage_amount", 3)
            shield_amount = _stat(self, "magic_network", "shield_amount", 3)
            for enemy in list(run.enemies):
                engine._damage_target(run, f"e{run.enemies.index(enemy)+1}", damage_amount)
            engine._gain_shield(run, "p0", shield_amount)
            res = get_locale_text("i18n_buffs.magic_network_feedback", damage=damage_amount, shield=shield_amount)
        return res

    def on_player_turn_end(self, run, buff_state, engine):
        if buff_state in run.player.buffs:
            run.player.buffs.remove(buff_state)

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player:
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

class StrengthBuff(BuffImpl):
    hook_priorities = {"on_damage_calculate": PRIORITY_MODIFIER_ADD}

    def on_damage_calculate(self, event, buff_state, entity):
        if not is_damage_event_from_entity(event, entity):
            return
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if entity in event.run.enemies:
            if dtype_str.lower() != "true":
                event.modified_damage = max(0, event.modified_damage + buff_state.stacks)
            return
        is_astral_strike = False
        if entity == event.run.player and event.card:
            card_id = event.card.id
            if card_id.startswith("duel_"):
                card_id = card_id[5:]
            if card_id == "neutral_astral_strike":
                is_astral_strike = True
        if is_physical_damage(dtype_str) or is_astral_strike:
            mult = _stat(self, "strength", "default_multiplier", 1)
            if entity == event.run.player and event.card:
                card_id = event.card.id
                if card_id.startswith("duel_"):
                    card_id = card_id[5:]
                if card_id.startswith("heavy_blade"):
                    mult = _stat(self, "strength", "heavy_blade_upgraded_multiplier", 5) if event.card.upgraded else _stat(self, "strength", "heavy_blade_multiplier", 3)
                elif card_id == "neutral_astral_strike":
                    mult = _stat(self, "strength", "astral_strike_upgraded_multiplier", 5) if event.card.upgraded else _stat(self, "strength", "astral_strike_multiplier", 4)
            event.modified_damage = max(0, event.modified_damage + buff_state.stacks * mult)

class FlameBarrierBuff(BuffImpl):
    def on_damage_take_defend(self, event, buff_state, entity, engine=None):
        engine = event.engine
        if entity == event.run.player and event.target == "p0" and event.source.startswith("e"):
            reflect_damage = buff_state.stacks * _stat(self, "flame_barrier_buff", "reflect_damage", 1)
            engine._damage_target(event.run, event.source, reflect_damage, damage_type="fire")
            engine._log_event(event.run, get_locale_text("i18n_buffs.flame_barrier_log", damage=reflect_damage))

    def on_turn_start(self, event, buff_state, entity):
        if event.is_player == (entity == event.run.player):
            if buff_state in entity.buffs:
                entity.buffs.remove(buff_state)

class MetallicizeBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            shield_gain = buff_state.stacks * _stat(self, "metallicize", "shield_per_stack", 1)
            event.engine._gain_shield(event.run, "p0", shield_gain)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.metallicize_log", shield=shield_gain))

class DemonFormBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            amount = buff_state.stacks * _stat(self, "demon_form", "strength_stacks", 1)
            event.engine._add_buff_to(entity, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), amount)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.demon_form_log", amount=amount))

class DoubleTapBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player:
            dtype = getattr(event.card, "damage_type", "spell")
            if is_physical_damage(dtype):
                stacks = buff_state.stacks
                for _ in range(stacks):
                    if event.engine.is_battle_won(event.run):
                        break
                    extra_res = event.engine._execute_card_effect(event.run, event.card, event.target)
                    event.run.node_data.setdefault("extra_play_msgs", []).append(get_locale_text("i18n_buffs.double_tap_trigger_msg", res=extra_res))
                if buff_state in event.run.player.buffs:
                    event.run.player.buffs.remove(buff_state)

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

class FuryBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if event.card.rarity in ("rare", "legendary", "mythic", "artifact"):
            event.engine._add_buff_to(entity, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), buff_state.stacks)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.fury_log", entity=entity.name, card=event.card.name, stacks=buff_state.stacks))

class FireGrowBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "fire" and event.source == "p0":
            event.modified_damage += buff_state.stacks * _stat(self, "fire_grow", "damage_per_stack", 1)

class ForgeBackfireBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and is_spell_card_damage(event) and event.source == "p0":
            event.modified_damage = max(0, event.modified_damage - buff_state.stacks * _stat(self, "forge_backfire", "damage_per_stack", 1))

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                event.run.player.buffs.remove(buff_state)

class TimeWarpSpellBoostBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and is_spell_card_damage(event) and event.source == "p0":
            event.modified_damage += buff_state.stacks * _stat(self, "time_warp_spell_boost", "damage_per_stack", 2)

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player:
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

class LightningShieldBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.source == "p0" and event.modified_damage > 0:
            run = event.run
            engine = event.engine
            engine._damage_target(run, "p0", _stat(self, "lightning_shield", "reflect_damage", 2) * buff_state.stacks, source=f"buff:{entity.name}", damage_type="lightning")
            engine._add_buff_to(run.player, "shock", get_locale_text("i18n_enemy_boss.buff_shock"), get_locale_text("i18n_enemy_boss.buff_shock_desc"), _stat(self, "lightning_shield", "shock_stacks", 1))

    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player and entity in event.run.enemies:
            if buff_state in entity.buffs:
                entity.buffs.remove(buff_state)

class ResistBuff(BuffImpl):
    auto_register = False
    def __init__(self, stacks: int, damage_type: str):
        super().__init__(stacks)
        self.damage_type = damage_type

    def on_damage_calculate_defend(self, event, buff_state, entity):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if damage_type_matches(dtype_str, self.damage_type) and dtype_str != "true":
            event.modified_damage = int(event.modified_damage * _stat(self, f"resist_{self.damage_type}", "damage_multiplier", 0.5))

    def on_turn_start(self, event, buff_state, entity):
        if event.is_player == (entity == event.run.player):
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                if buff_state in entity.buffs:
                    entity.buffs.remove(buff_state)

class ImmuneBuff(BuffImpl):
    auto_register = False
    def __init__(self, stacks: int, damage_type: str):
        super().__init__(stacks)
        self.damage_type = damage_type

    def on_damage_calculate_defend(self, event, buff_state, entity):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if damage_type_matches(dtype_str, self.damage_type) and dtype_str != "true":
            event.modified_damage = int(event.modified_damage * _stat(self, f"immune_{self.damage_type}", "damage_multiplier", 0.0))

    def on_turn_start(self, event, buff_state, entity):
        if event.is_player == (entity == event.run.player):
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                if buff_state in entity.buffs:
                    entity.buffs.remove(buff_state)

class KeyScholarPassiveBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player and event.card.type == "amulet":
            heal_amount = _stat(self, "key_scholar_passive", "heal_amount", 3)
            shield_amount = _stat(self, "key_scholar_passive", "shield_amount", 4)
            event.engine._heal_target(event.run, "p0", heal_amount)
            event.engine._gain_shield(event.run, "p0", shield_amount)
            event.feedback += get_locale_text("i18n_buffs.key_scholar_feedback", heal=heal_amount, shield=shield_amount)

class AncientProtectionBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player and entity.shield > 0:
            to_remove = []
            for b in entity.buffs:
                if is_debuff(b.id):
                    to_remove.append(b)
            for b in to_remove:
                entity.buffs.remove(b)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.ancient_protection_log", entity=entity.name))

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0 and entity.shield > 0:
            recoil_dmg = max(_stat(self, "ancient_protection", "min_recoil", 1), int(event.modified_damage * _stat(self, "ancient_protection", "recoil_ratio", 0.20)))
            event.engine._damage_target(event.run, "p0", recoil_dmg, source=f"buff:{entity.name}", damage_type="force")
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.ancient_protection_recoil_log", entity=entity.name, damage=recoil_dmg))

class EndGatePassiveBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player:
            run = event.run
            if entity == run.player:
                target = "p0"
            elif entity in run.enemies:
                target = f"e{run.enemies.index(entity)+1}"
            else:
                target = None
                for grid, m in run.player.minions.items():
                    if m == entity:
                        target = f"p{grid}"
                        break
            if target:
                event.engine._gain_shield(run, target, _stat(self, "end_gate_passive", "shield_amount", 15))
            to_remove = []
            for b in entity.buffs:
                if is_debuff(b.id):
                    to_remove.append(b)
            for b in to_remove:
                entity.buffs.remove(b)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.end_gate_log", entity=entity.name))

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0 and entity.shield > 0:
            event.engine._damage_target(event.run, "p0", _stat(self, "end_gate_passive", "reflect_damage", 1), source=f"buff:{entity.name}", damage_type="true")
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.end_gate_reflect_log", entity=entity.name))

class DoomsdayGatePassiveBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player:
            run = event.run
            if entity == run.player:
                target = "p0"
            elif entity in run.enemies:
                target = f"e{run.enemies.index(entity)+1}"
            else:
                target = None
                for grid, m in run.player.minions.items():
                    if m == entity:
                        target = f"p{grid}"
                        break
            if target:
                event.engine._gain_shield(run, target, _stat(self, "doomsday_gate_passive", "shield_amount", 20))
            event.engine._add_buff_to(entity, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), _stat(self, "doomsday_gate_passive", "strength_stacks", 2))
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.doomsday_gate_log", entity=entity.name))

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0 and entity.shield > 0:
            event.engine._damage_target(event.run, "p0", _stat(self, "doomsday_gate_passive", "reflect_damage", 1), source=f"buff:{entity.name}", damage_type="true")
            event.engine._damage_target(event.run, "p0", _stat(self, "doomsday_gate_passive", "force_reflect_damage", 2), source=f"buff:{entity.name}", damage_type="force")
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.doomsday_gate_reflect_log", entity=entity.name))


class AncientWisdomBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player and event.card.color == "neutral":
            coef = _stat(self, "ancient_wisdom_buff", "upgraded_shield_per_stack", 3) if self.upgraded else _stat(self, "ancient_wisdom_buff", "shield_per_stack", 2)
            shield_gain = buff_state.stacks * coef
            event.engine._gain_shield(event.run, "p0", shield_gain)
            event.feedback += get_locale_text("i18n_buffs.ancient_wisdom_feedback", shield=shield_gain)

class BufferBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0:
            damage_type = event.damage_type
            is_true = False
            if damage_type == "true" or damage_type == "TRUE":
                is_true = True
            elif hasattr(damage_type, "value") and (damage_type.value == "true" or damage_type.value == "TRUE"):
                is_true = True
            if is_true or event.modified_damage > entity.shield:
                event.modified_damage = 0
                buff_state.stacks -= 1
                name = get_locale_text("i18n_buffs.player_display_name") if entity == event.run.player else getattr(entity, "name", get_locale_text("i18n_buffs.unknown_display_name"))
                event.engine._log_event(event.run, get_locale_text("i18n_buffs.buffer_log", name=name))
                if buff_state.stacks <= 0:
                    if buff_state in entity.buffs:
                        entity.buffs.remove(buff_state)

class DemonContractBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player and event.card.type == "spell":
            card_id = event.card.id
            if card_id.startswith("duel_"):
                card_id = card_id[5:]
            if card_id.startswith("demon_contract"):
                return
            stacks = buff_state.stacks
            for _ in range(stacks):
                if event.engine.is_battle_won(event.run):
                    break
                extra_res = event.engine._execute_card_effect(event.run, event.card, event.target)
                from ...models.events import CardExtraTriggerEvent
                event.engine.event_bus.dispatch(CardExtraTriggerEvent(event.run, event.card, "echo"))
                event.run.node_data.setdefault("extra_play_msgs", []).append(get_locale_text("i18n_buffs.demon_contract_trigger_msg", res=extra_res))
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

class GlacierFortressBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            coef = _stat(self, "glacier_fortress_buff", "upgraded_shield_per_stack", 6) if self.upgraded else _stat(self, "glacier_fortress_buff", "shield_per_stack", 4)
            shield_gain = buff_state.stacks * coef
            event.engine._gain_shield(event.run, "p0", shield_gain)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.glacier_fortress_log", shield=shield_gain))

class WishPowerBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and is_spell_card_damage(event) and event.source == "p0":
            val = _stat(self, "wish_power", "upgraded_damage_bonus", 6) if self.upgraded else _stat(self, "wish_power", "damage_bonus", 4)
            event.modified_damage += buff_state.stacks * val

@register_buff("commander_aurora_emperor")
class AuroraEmperorBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if event.source.startswith("p") and event.source != "p0" and event.damage_type == "attack":
            shield = _stat(self, "commander_aurora_emperor", "upgraded_shield_amount", 3) if self.upgraded else _stat(self, "commander_aurora_emperor", "shield_amount", 2)
            event.engine._gain_shield(event.run, "p0", shield)
            msg = get_locale_text("i18n_buffs.aurora_emperor_log", shield=shield)
            if self.upgraded:
                event.engine._draw_cards(event.run.player, _stat(self, "commander_aurora_emperor", "upgraded_draw_count", 1), event.run)
                msg = get_locale_text("i18n_buffs.aurora_emperor_upgraded_log", shield=shield)
            event.engine._log_event(event.run, msg)

class HellRaiderBuff(BuffImpl):
    def on_card_drawn(self, event, buff_state, entity):
        if event.intercepted or entity != event.run.player:
            return
        run = event.run
        upgraded = buff_state.id == "hell_raider_upgraded"
        cfg = BUFF_CONFIG.get("hell_raider", {})
        chain = getattr(run, "_hell_raider_chain", 0)
        chain_limit = cfg.get("chain_depth", 5)
        cost_a_limit = 2 if upgraded else 1
        card = event.card
        if not card:
            return
        if chain >= chain_limit or getattr(card, "cost_a", 0) > cost_a_limit or getattr(card, "cost_ba", 0) != 0:
            return
        event.intercepted = True
        engine = event.engine
        buff_prefix = get_locale_text("i18n_battle_core.hell_raider_upgraded_name") if upgraded else get_locale_text("i18n_battle_core.hell_raider_name")
        engine._log_event(run, get_locale_text("i18n_battle_core.hell_raider_auto_play_log", buff_prefix=buff_prefix, cost_a=getattr(card, "cost_a", 0), name=card.name))
        target = "p0"
        if card.type == "spell" and getattr(card, "target_type", "enemy") != "self":
            target = engine._get_first_alive_enemy(run)
        elif card.type in ("minion", "amulet"):
            target = engine._get_free_grid(run.player)
            if not target:
                target = "p1"
        run._hell_raider_chain = chain + 1
        try:
            res_action = engine._execute_card_effect(run, card, target)
            res_action, _ = engine.card_player._finalize_card_play(run, run.player, card, event.card_state, target, res_action, source="hell_raider", register=False)
            engine._log_event(run, get_locale_text("i18n_battle_core.hell_raider_feedback_log", feedback=res_action))
            if upgraded and event.depth < chain_limit:
                engine._log_event(run, get_locale_text("i18n_battle_core.hell_raider_extra_draw_log"))
                engine.card_player.draw_cards(run.player, cfg.get("upgraded_draw_count", 1), run, depth=event.depth + 1)
        finally:
            run._hell_raider_chain = chain

class BarricadeBuff(BuffImpl):
    def on_shield_decay_calculate(self, event, buff_state, entity):
        event.decay_amount = 0

class PrismaticBarrierBuff(BuffImpl):
    def on_damage_take_defend(self, event, buff_state, entity, engine=None):
        engine = event.engine
        if event.target != "p0" or event.amount <= 0 or not event.source.startswith("e"):
            return
        upgraded = buff_state.id == "prismatic_barrier_upgraded"
        cfg = BUFF_CONFIG.get("prismatic_barrier", {})
        total = int(cfg.get("upgraded_reflect_damage" if upgraded else "reflect_damage", 12))
        per_type = max(1, total // 4)
        buff_state.stacks -= 1
        if buff_state.stacks <= 0 and buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        buff_prefix = get_locale_text(
            "i18n_battle_misc.prismatic_barrier_upgraded_name" if upgraded else "i18n_battle_misc.prismatic_barrier_name"
        )
        engine._log_event(event.run, get_locale_text("i18n_battle_misc.prismatic_barrier_reflect", buff_prefix=buff_prefix))
        for damage_type in ("fire", "cold", "lightning", "poison"):
            engine._damage_target(event.run, event.source, per_type, source="p0", damage_type=damage_type)



class AntimagicImmuneBuff(BuffImpl):
    hook_priorities = {"on_before_damage_apply": -200}

    def on_before_damage_apply(self, event, buff_state, entity, engine=None):
        engine = event.engine
        if event.target != "p0":
            return
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if not is_physical_damage(dtype):
            event.final_damage = 0

    def on_turn_end(self, event, buff_state, entity):
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)


class RitualBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player:
            amount = buff_state.stacks * _stat(self, "ritual", "strength_stacks", 1)
            event.engine._add_buff_to(entity, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), amount)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.ritual_log", entity=entity.name, stacks=buff_state.stacks))


class GrappledBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if event.is_player:
            return
        if entity != event.run.player:
            return
        stacks = buff_state.stacks
        if stacks:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0 and buff_state in entity.buffs:
                entity.buffs.remove(buff_state)


class AstralSpeedBuff(BuffImpl):
    def on_enemy_roll_intent(self, event, buff_state, entity):
        event.enemy.actions += buff_state.stacks
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)


class BonusSpeedBuff(BuffImpl):
    def on_enemy_roll_intent(self, event, buff_state, entity):
        event.enemy.bonus_actions += buff_state.stacks
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)


class SourceOfCinderBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player:
            return
        if not event.run.player:
            return
        if entity != event.run.player:
            return
        actions = buff_state.stacks
        event.run.player.actions += actions
        event.run.player.bonus_actions += actions
        event.engine._log_event(event.run, get_locale_text("i18n_buffs.source_of_cinder_log", actions=actions))


class UnyieldingBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype_str in ("true", "TRUE"):
            return
        already_taken = getattr(buff_state, "already_taken", 0)
        allowed_remaining = max(0, buff_state.stacks - already_taken)
        if event.modified_damage > allowed_remaining:
            event.modified_damage = allowed_remaining

    def on_damage_take_defend(self, event, buff_state, entity, engine=None):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype_str in ("true", "TRUE"):
            return
        buff_state.already_taken = getattr(buff_state, "already_taken", 0) + event.amount

    def on_turn_end(self, event, buff_state, entity):
        buff_state.already_taken = 0


class TimeLordPassiveBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player:
            return
        run = event.run
        if entity == run.player:
            target = "p0"
        elif entity in run.enemies:
            target = f"e{run.enemies.index(entity) + 1}"
        else:
            target = None
        if target is None:
            return
        shield_gain = _stat(self, "time_lord_passive", "shield_gain", 20)
        event.engine._gain_shield(run, target, shield_gain)
        for removed in list(entity.buffs):
            if is_debuff(removed.id) and removed in entity.buffs:
                entity.buffs.remove(removed)
        echo_hp = _stat(self, "time_lord_passive", "echo_hp", 15)
        echo_actions = _stat(self, "time_lord_passive", "echo_actions", 1)
        echo_max_actions = _stat(self, "time_lord_passive", "echo_max_actions", 1)
        echo_name = get_locale_text("i18n_buffs.echo_enemy_name")
        active_echoes = [e for e in run.enemies if e.name == echo_name]
        max_echoes = _stat(self, "time_lord_passive", "max_echoes", 1)
        max_enemies = _stat(self, "time_lord_passive", "max_enemies", 3)
        import random
        if len(active_echoes) < max_echoes and len(run.enemies) < max_enemies:
            if random.random() < _stat(self, "time_lord_passive", "summon_chance", 0.5):
                from ...models.state import EnemyState, BuffState
                echo = EnemyState(
                    name=echo_name,
                    hp=echo_hp,
                    max_hp=echo_hp,
                    shield=0,
                    actions=echo_actions,
                    bonus_actions=0,
                    max_actions=echo_max_actions,
                    max_bonus_actions=0,
                    buffs=[BuffState(id="echo", name=echo_name, stacks=1, desc=echo_name)],
                )
                run.enemies.append(echo)
                event.engine._log_event(run, get_locale_text("i18n_buffs.time_lord_summon_log", enemy=echo_name))

    def on_damage_calculate(self, event, buff_state, entity):
        if event.modified_damage <= 0:
            return
        run = event.run
        echo_name = get_locale_text("i18n_buffs.echo_enemy_name")
        active_echoes = [e for e in run.enemies if e.name == echo_name and e.hp > 0]
        if not active_echoes:
            return
        shared_damage = event.modified_damage // _stat(self, "time_lord_passive", "damage_share_divisor", 2)
        if shared_damage <= 0:
            return
        echo_enemy = active_echoes[0]
        event.modified_damage -= shared_damage
        echo_index = run.enemies.index(echo_enemy) + 1
        event.engine.combat_resolver.damage_target(run, f"e{echo_index}", shared_damage, source="effect", damage_type="true")
        event.engine._log_event(run, get_locale_text("i18n_buffs.echo_share_damage_log", damage=shared_damage))


class PendulumResonanceBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        run = event.run
        if event.is_player:
            return
        p = run.player
        if p is None or not p.buffs:
            return
        played_key = run.turn_key("cards_played_this_turn", p)
        played = int(run.node_data.get(played_key, 0) or 0)
        if p.actions <= 0 and p.bonus_actions <= 0:
            damage = max(_stat(self, "pendulum_resonance", "min_damage", 4), played * _stat(self, "pendulum_resonance", "damage_per_card", 2))
            event.engine._damage_target(run, "p0", damage, source="effect", damage_type="true")
            event.engine._log_event(run, get_locale_text(
                "i18n_buffs.pendulum_resonance_shake_log",
                actions=p.actions,
                bonus_actions=p.bonus_actions,
                damage=damage,
            ))
        else:
            bonus = _stat(self, "pendulum_resonance", "draw_bonus", 2)
            key = "draw_penalty_next_turn"
            run.node_data[key] = int(run.node_data.get(key, 0) or 0) - bonus
            event.engine._log_event(run, get_locale_text("i18n_buffs.pendulum_resonance_stable_log"))


class SplitToTenBuff(BuffImpl):
    def on_card_effect_resolved(self, event, buff_state, entity):
        run = event.run
        if entity != run.player or buff_state.stacks <= 0 or run.node_data.get("split_to_ten_running"):
            return
        buff_state.stacks -= 1
        if buff_state.stacks <= 0 and buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        engine = event.engine
        from ...core.battle.card_executor import execute_extra_card_effect
        replay_amount = int(_stat(self, "split_to_ten", "replay_amount", 10))
        run.node_data["split_to_ten_running"] = True
        try:
            for _ in range(replay_amount):
                if engine.is_battle_won(run):
                    break
                extra_res = execute_extra_card_effect(
                    engine,
                    run,
                    event.card,
                    event.target,
                    trigger_type="split_to_ten",
                )
                run.node_data.setdefault("extra_play_msgs", []).append(
                    get_locale_text("i18n_battle_core.split_to_ten_extra", feedback=extra_res)
                )
        finally:
            run.node_data.pop("split_to_ten_running", None)


class PhaseTransitionImmuneBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        event.modified_damage = 0

    def on_turn_end(self, event, buff_state, entity):
        if not event.is_player and entity in event.run.enemies:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                if buff_state in entity.buffs:
                    entity.buffs.remove(buff_state)


class PsychicResistanceBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype.lower() == "psychic":
            event.modified_damage = int(event.modified_damage * _stat(self, "psychic_resistance", "damage_multiplier", 0.5))

    def on_turn_end(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0 and buff_state in entity.buffs:
                entity.buffs.remove(buff_state)


class IntangibleBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        cap = _stat(self, "intangible", "damage_cap", 1)
        if event.modified_damage > cap:
            event.modified_damage = cap

    def on_turn_start(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0 and buff_state in entity.buffs:
                entity.buffs.remove(buff_state)


class BladesongBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player:
            ba_gain = _stat(self, "bladesong", "ba_gain", 1)
            event.run.player.bonus_actions += ba_gain
            event.engine._log_event(event.run, get_locale_text("i18n_grid_map.bladesong_turn_log", ba=ba_gain))

    def on_card_played(self, event, buff_state, entity):
        if entity != event.run.player:
            return
        from ..cards.base import card_matches_color
        if not (card_matches_color(event.card, "warrior") or card_matches_color(event.card, "wizard")):
            return
        stacks = max(1, int(getattr(buff_state, "stacks", 1) or 1))
        proc_dmg = _stat(self, "bladesong", "proc_dmg", 3) * stacks
        proc_shield = _stat(self, "bladesong", "proc_shield", 3) * stacks
        event.engine._gain_shield(event.run, "p0", proc_shield)
        living = [f"e{i + 1}" for i, e in enumerate(event.run.enemies) if e.hp > 0]
        if living:
            import random
            target = random.choice(living)
            event.engine._damage_target(event.run, target, proc_dmg, source="p0", damage_type="force")
            event.engine._log_event(event.run, get_locale_text("i18n_grid_map.bladesong_proc_log", dmg=proc_dmg, shield=proc_shield))
        else:
            event.engine._log_event(event.run, get_locale_text("i18n_grid_map.bladesong_shield_log", shield=proc_shield))


class InvisibilityBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0 and buff_state in entity.buffs:
                entity.buffs.remove(buff_state)

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.target != "p0" or not event.source.startswith("e"):
            return
        enemy_name = ""
        source = event.source
        if source[1:].isdigit():
            idx = int(source[1:]) - 1
            if 0 <= idx < len(event.run.enemies):
                enemy_name = event.run.enemies[idx].name
        if enemy_name:
            from ...data.world.room_interact_data import TRUE_SIGHT_ENEMIES
            if enemy_name in TRUE_SIGHT_ENEMIES:
                event.engine._log_event(event.run, get_locale_text("i18n_buffs.invisibility_true_sight_pierce_log", name=enemy_name))
                return
        import random
        if random.random() < _stat(self, "invisibility", "dodge_chance", 0.75):
            event.modified_damage = 0
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.invisibility_dodge_log", name=enemy_name))


class AllResonanceBuff(BuffImpl):
    hook_priorities = {"on_damage_calculate": 200}

    def on_damage_calculate(self, event, buff_state, entity):
        ghost_name = str(event.run.node_data.get("ghost_name", "") or "")
        if ghost_name and getattr(entity, "name", "") == ghost_name:
            return
        source = event.source
        player_source = (
            source in ("p0", "player", "effect")
            or source.startswith("player:")
            or (len(source) > 1 and source[0] in ("p", "a") and source[1:].isdigit())
        )
        if not player_source:
            return
        multiplier = _stat(self, "all_resonance", "damage_multiplier", 10)
        event.modified_damage = event.modified_damage * (multiplier ** max(0, int(buff_state.stacks)))


for name, obj in list(globals().items()):
    if isinstance(obj, type) and issubclass(obj, BuffImpl) and obj is not BuffImpl:
        if not getattr(obj, "auto_register", True):
            continue
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        if snake.endswith('_buff'):
            buff_id = snake[:-5]
        else:
            buff_id = snake
        register_buff(buff_id)(obj)
