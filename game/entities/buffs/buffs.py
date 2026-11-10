from typing import List, Optional
import re
from .base import BuffImpl, is_debuff
from .registry import register_buff
from ...data.buff_data import BUFF_CONFIG
from ...data.locale_data import get_locale_text

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
        if entity == event.run.player and event.card.color == "wizard":
            event.engine._draw_cards(event.run.player, buff_state.stacks, event.run)

    def on_card_played_legacy(self, run, card, target: str, engine) -> str:
        if card.color == "wizard":
            engine._draw_cards(run.player, self.stacks, run)
        return ""

class ArcaneChargeBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "spell" and event.source == "p0":
            event.modified_damage += buff_state.stacks * _stat(self, "arcane_charge", "dmg_per_stack", 3)

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        return damage + self.stacks * _stat(self, "arcane_charge", "dmg_per_stack", 3)

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
                from ...models.events import CardPlayedEvent
                played_evt = CardPlayedEvent(event.run, event.card, event.target, extra_res, is_extra=True)
                event.engine.event_bus.dispatch(played_evt)
                event.run.node_data.setdefault("extra_play_msgs", []).append(get_locale_text("i18n_buffs.echo_trigger_msg", res=played_evt.feedback))
                if hasattr(event.card, "execute_tags"):
                    event.card.execute_tags(event.run, event.target, event.engine)

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
                if hasattr(card, "execute_tags"):
                    card.execute_tags(run, target, engine)
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

class WishPowerBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "spell" and event.source == "p0":
            val = _stat(self, "wish_power", "upgraded_damage_bonus", 6) if self.upgraded else _stat(self, "wish_power", "damage_bonus", 4)
            event.modified_damage += buff_state.stacks * val

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        val = _stat(self, "wish_power", "upgraded_damage_bonus", 6) if self.upgraded else _stat(self, "wish_power", "damage_bonus", 4)
        return damage + self.stacks * val

class StrengthBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        is_owner = False
        if entity == event.run.player:
            if event.source == "p0":
                is_owner = True
        elif entity in event.run.enemies:
            try:
                idx = event.run.enemies.index(entity)
                if event.source == f"e{idx+1}":
                    is_owner = True
            except ValueError:
                pass
        if is_owner:
            dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
            is_astral_strike = False
            if entity == event.run.player and event.card:
                card_id = event.card.id
                if card_id.startswith("duel_"):
                    card_id = card_id[5:]
                if card_id == "neutral_astral_strike":
                    is_astral_strike = True
            if dtype_str in ("slashing", "bludgeoning", "piercing") or is_astral_strike:
                mult = _stat(self, "strength", "default_multiplier", 1)
                if entity == event.run.player and event.card:
                    card_id = event.card.id
                    if card_id.startswith("duel_"):
                        card_id = card_id[5:]
                    if card_id.startswith("heavy_blade"):
                        mult = _stat(self, "strength", "heavy_blade_upgraded_multiplier", 5) if event.card.upgraded else _stat(self, "strength", "heavy_blade_multiplier", 3)
                    elif card_id == "neutral_astral_strike":
                        mult = _stat(self, "strength", "astral_strike_upgraded_multiplier", 5) if event.card.upgraded else _stat(self, "strength", "astral_strike_multiplier", 4)
                event.modified_damage += buff_state.stacks * mult

class FlameBarrierBuff(BuffImpl):
    def on_damage_take_defend(self, event, buff_state, entity, engine):
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
            if dtype in ("slashing", "bludgeoning", "piercing"):
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

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        if getattr(card, "damage_type", "") == "fire":
            return damage + self.stacks * _stat(self, "fire_grow", "damage_per_stack", 1)
        return damage

class ForgeBackfireBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "spell" and event.source == "p0":
            event.modified_damage = max(0, event.modified_damage - buff_state.stacks * _stat(self, "forge_backfire", "damage_per_stack", 1))

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        return max(0, damage - self.stacks * _stat(self, "forge_backfire", "damage_per_stack", 1))

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                event.run.player.buffs.remove(buff_state)

class TimeWarpSpellBoostBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "spell" and event.source == "p0":
            event.modified_damage += buff_state.stacks * _stat(self, "time_warp_spell_boost", "damage_per_stack", 2)

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        return damage + self.stacks * _stat(self, "time_warp_spell_boost", "damage_per_stack", 2)

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
        if dtype_str == self.damage_type and dtype_str != "true":
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
        if dtype_str == self.damage_type and dtype_str != "true":
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
            if not card_id.startswith("demon_contract"):
                stacks = buff_state.stacks
            for _ in range(stacks):
                if event.engine.is_battle_won(event.run):
                    break
                extra_res = event.engine._execute_card_effect(event.run, event.card, event.target)
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
        if entity == event.run.player and event.card.type == "spell":
            val = _stat(self, "wish_power", "upgraded_damage_bonus", 6) if self.upgraded else _stat(self, "wish_power", "damage_bonus", 4)
            event.modified_damage += val

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
    pass

class PrismaticBarrierBuff(BuffImpl):
    pass

class AntimagicImmuneBuff(BuffImpl):
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
        if event.is_player and entity == event.run.player:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                if buff_state in entity.buffs:
                    entity.buffs.remove(buff_state)


class AstralSpeedBuff(BuffImpl):
    pass

class SourceOfCinderBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            event.run.player.actions += buff_state.stacks
            event.run.player.bonus_actions += buff_state.stacks
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.source_of_cinder_log", stacks=buff_state.stacks))


class UnyieldingBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype_str == "true" or dtype_str == "TRUE":
            return
        already_taken = getattr(buff_state, "already_taken", 0)
        limit = buff_state.stacks
        allowed_remaining = max(0, limit - already_taken)
        if event.modified_damage > allowed_remaining:
            event.modified_damage = allowed_remaining

    def on_damage_take_defend(self, event, buff_state, entity, engine):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype_str == "true" or dtype_str == "TRUE":
            return
        already_taken = getattr(buff_state, "already_taken", 0)
        buff_state.already_taken = already_taken + event.amount

    def on_turn_end(self, event, buff_state, entity):
        buff_state.already_taken = 0


class TimeLordPassiveBuff(BuffImpl):
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
                event.engine._gain_shield(run, target, _stat(self, "time_lord_passive", "shield_gain", 20))
            to_remove = []
            for b in entity.buffs:
                if is_debuff(b.id):
                    to_remove.append(b)
            for b in to_remove:
                entity.buffs.remove(b)
            event.engine._log_event(event.run, get_locale_text("i18n_buffs.time_lord_log", entity=entity.name))
            
            echo_name = get_locale_text("i18n_buffs.echo_enemy_name")
            active_echoes = [e for e in event.run.enemies if e.name == echo_name and e.hp > 0]
            if len(active_echoes) < _stat(self, "time_lord_passive", "max_echoes", 1) and len(event.run.enemies) < _stat(self, "time_lord_passive", "max_enemies", 3):
                import random
                if random.random() < _stat(self, "time_lord_passive", "summon_chance", 0.5):
                    from ...models.state import EnemyState
                    echo_hp = _stat(self, "time_lord_passive", "echo_hp", 15)
                    echo_enemy = EnemyState(
                        name=echo_name,
                        hp=echo_hp,
                        max_hp=echo_hp,
                        shield=0,
                        actions=_stat(self, "time_lord_passive", "echo_actions", 1),
                        bonus_actions=0,
                        max_actions=_stat(self, "time_lord_passive", "echo_max_actions", 1),
                        max_bonus_actions=0
                    )
                    event.run.enemies.append(echo_enemy)
                    event.engine._log_event(event.run, get_locale_text("i18n_buffs.time_lord_summon_log"))

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0:
            active_echoes = [e for e in event.run.enemies if e.name == get_locale_text("i18n_buffs.echo_enemy_name") and e.hp > 0]
            if active_echoes:
                active_echo = active_echoes[0]
                shared_dmg = event.modified_damage // _stat(self, "time_lord_passive", "damage_share_divisor", 2)
                if shared_dmg > 0:
                    event.modified_damage = event.modified_damage - shared_dmg
                    idx = event.run.enemies.index(active_echo) + 1
                    event.engine.combat_resolver.damage_target(event.run, f"e{idx}", shared_dmg, source="effect", damage_type="true")
                    event.engine._log_event(event.run, get_locale_text("i18n_buffs.echo_share_damage_log", damage=shared_dmg))
            
            pass


class PendulumResonanceBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if event.is_player:
            run = event.run
            p = run.player
            if p.actions == 0 or p.bonus_actions == 0:
                played_count = run.node_data.get(run.turn_key("cards_played_this_turn", p), 0)
                dmg = max(_stat(self, "pendulum_resonance", "min_damage", 4), played_count * _stat(self, "pendulum_resonance", "damage_per_card", 2))
                event.engine._damage_target(run, "p0", dmg, source=f"buff:{get_locale_text('i18n_buffs.pendulum_resonance_name')}", damage_type="true")
                event.engine._log_event(run, get_locale_text("i18n_buffs.pendulum_resonance_shake_log", actions=p.actions, bonus_actions=p.bonus_actions, damage=dmg))
            else:
                event.engine._log_event(run, get_locale_text("i18n_buffs.pendulum_resonance_stable_log"))
                run.node_data["draw_penalty_next_turn"] = run.node_data.get("draw_penalty_next_turn", 0) - _stat(self, "pendulum_resonance", "draw_bonus", 2)


class SplitToTenBuff(BuffImpl):
    pass


class PhaseTransitionImmuneBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        event.modified_damage = 0

    def on_turn_end(self, event, buff_state, entity):
        if not event.is_player and entity in event.run.enemies:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                if buff_state in entity.buffs:
                    entity.buffs.remove(buff_state)


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
