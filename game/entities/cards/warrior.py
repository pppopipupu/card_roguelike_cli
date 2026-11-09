from typing import Optional
from ...models.state import Card
from ...data.card_data import CARD_CONFIG
from ...data.locale_data import get_locale_text
from ...core.deck_service import DeckService
from .registry import register_card
from .warrior_officer import (
    AURORA_ENTRY_SHIELD,
    OfficerRecruitVanguardCard,
    OfficerBannerBearerCard,
    CommanderPatrolCaptainCard,
    OfficerRoyalGuardCard,
    CommanderGarrisonLeaderCard,
    OfficerSquadSkirmisherCard,
    CommanderValiantHeraldCard,
    CommanderSteelcladTacticianCard,
    OfficerBladeDancerCard,
    CommanderAuroraEmperorCard,
)

SHIELD_BASH_DAMAGE_DIVISOR = 2
KEYRING_COUNTDOWN_REDUCTION_CHANCE = 0.5
MIN_AMULET_COUNTDOWN = 1
STRIKE_OF_ALL_GROWTH = 1.5

@register_card("warrior_strike")
class WarriorStrikeCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 9 if self.upgraded else 6)
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="slashing", card=self, damage_ready=True)
        cfg = CARD_CONFIG.get(self.id, {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(target=name)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.strike.result", name=name, dmg=dmg)

@register_card("warrior_defend")
class WarriorDefendCard(Card):
    def execute(self, run, target, engine) -> str:
        shield = getattr(self, "shield_amount", 8 if self.upgraded else 5)
        engine._gain_shield(run, "p0", shield)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.defend.result", shield=shield)

@register_card("warrior_bash")
class WarriorBashCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 11 if self.upgraded else 8)
        stacks = getattr(self, "buff_stacks", 3 if self.upgraded else 2)
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="bludgeoning", card=self, damage_ready=True)
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    enemy = run.enemies[idx]
                    engine._add_buff_to(enemy, "minor_vulnerable", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.minor_vulnerable.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.minor_vulnerable.desc"), stacks)
            except ValueError:
                pass
        return get_locale_text("i18n_cards_warrior_wizard.warrior.bash.result", name=name, dmg=dmg, stacks=stacks)

@register_card("iron_wave")
class IronWaveCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 7 if self.upgraded else 5)
        shield = getattr(self, "shield_amount", 7 if self.upgraded else 5)
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="slashing", card=self, damage_ready=True)
        engine._gain_shield(run, "p0", shield)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.iron_wave.result", name=name, dmg=dmg, shield=shield)

@register_card("warrior_anger")
class WarriorAngerCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 6 if self.upgraded else 4)
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="slashing", card=self, damage_ready=True)
        anger_state = DeckService.new_state(self.id, upgraded=self.upgraded, gems=list(getattr(self, "gems", [])))
        DeckService.add_card_to_discard(run.player, anger_state)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.anger.result", name=name, dmg=dmg)

@register_card("body_slam")
class BodySlamCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = run.player.shield
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="bludgeoning", card=self, damage_ready=True)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.body_slam.result", name=name, dmg=dmg)

@register_card("pommel_strike")
class PommelStrikeCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 12 if self.upgraded else 9)
        cards_to_draw = getattr(self, "draw_count", 2 if self.upgraded else 1)
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="slashing", card=self, damage_ready=True)
        engine._draw_cards(run.player, cards_to_draw, run)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.pommel_strike.result", name=name, dmg=dmg, cards_to_draw=cards_to_draw)

@register_card("shrug_it_off")
class ShrugItOffCard(Card):
    def execute(self, run, target, engine) -> str:
        shield = getattr(self, "shield_amount", 11 if self.upgraded else 8)
        draw_count = getattr(self, "draw_count", 1)
        engine._gain_shield(run, "p0", shield)
        engine._draw_cards(run.player, draw_count, run)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.shrug_it_off.result", shield=shield, draw_count=draw_count)

@register_card("heavy_blade")
class HeavyBladeCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 18 if self.upgraded else 14)
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="slashing", card=self, damage_ready=True)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.heavy_blade.result", name=name, dmg=dmg)

@register_card("shockwave")
class ShockwaveCard(Card):
    def execute(self, run, target, engine) -> str:
        stacks = getattr(self, "buff_stacks", 3 if self.upgraded else 2)
        for enemy in list(run.enemies):
            engine._add_buff_to(enemy, "minor_vulnerable", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.minor_vulnerable.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.minor_vulnerable.desc"), stacks)
            engine._add_buff_to(enemy, "weak", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.weak.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.weak.desc"), stacks)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.shockwave.result", stacks=stacks)

@register_card("flame_barrier")
class FlameBarrierCard(Card):
    def execute(self, run, target, engine) -> str:
        shield = getattr(self, "shield_amount", 16 if self.upgraded else 12)
        barrier_dmg = getattr(self, "reflect_damage", 6 if self.upgraded else 4)
        engine._gain_shield(run, "p0", shield)
        engine._add_buff_to(run.player, "flame_barrier_buff", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.flame_barrier.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.flame_barrier.desc"), barrier_dmg)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.flame_barrier.result", shield=shield, barrier_dmg=barrier_dmg)

@register_card("uppercut")
class UppercutCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 17 if self.upgraded else 13)
        stacks = getattr(self, "buff_stacks", 3 if self.upgraded else 2)
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="bludgeoning", card=self, damage_ready=True)
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    enemy = run.enemies[idx]
                    engine._add_buff_to(enemy, "minor_vulnerable", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.minor_vulnerable.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.minor_vulnerable.desc"), stacks)
                    engine._add_buff_to(enemy, "weak", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.weak.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.weak.desc"), stacks)
            except ValueError:
                pass
        return get_locale_text("i18n_cards_warrior_wizard.warrior.uppercut.result", name=name, dmg=dmg, stacks=stacks)

@register_card("spot_weakness")
class SpotWeaknessCard(Card):
    def execute(self, run, target, engine) -> str:
        strength_gain = getattr(self, "strength_gain", 4 if self.upgraded else 3)
        name = engine._get_target_name(run, target)
        is_attack = False
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    enemy = run.enemies[idx]
                    for it in enemy.intents:
                        if it.type in ("attack", "damage", "strike") or "伤害" in it.desc or "攻击" in it.desc:
                            is_attack = True
            except ValueError:
                pass
        if is_attack:
            engine._add_buff_to(run.player, "strength", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.strength.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.strength.desc"), strength_gain)
            return get_locale_text("i18n_cards_warrior_wizard.warrior.spot_weakness.success", name=name, strength_gain=strength_gain)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.spot_weakness.fail", name=name)

@register_card("ghostly_armor")
class GhostlyArmorCard(Card):
    def execute(self, run, target, engine) -> str:
        shield = getattr(self, "shield_amount", 14 if self.upgraded else 10)
        engine._gain_shield(run, "p0", shield)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.ghostly_armor.result", shield=shield)

@register_card("power_through")
class PowerThroughCard(Card):
    def execute(self, run, target, engine) -> str:
        shield = getattr(self, "shield_amount", 22 if self.upgraded else 15)
        curse_count = getattr(self, "curse_count", 2)
        hand_limit = getattr(self, "hand_limit", 12)
        engine._gain_shield(run, "p0", shield)
        added_wounds = 0
        for _ in range(curse_count):
            if len(run.player.hand) < hand_limit:
                DeckService.add_card_to_hand(run.player, "curse_wound")
                added_wounds += 1
        return get_locale_text("i18n_cards_warrior_wizard.warrior.power_through.result", shield=shield, added_wounds=added_wounds)

@register_card("double_tap")
class DoubleTapCard(Card):
    def execute(self, run, target, engine) -> str:
        stacks = getattr(self, "buff_stacks", 2 if self.upgraded else 1)
        engine._add_buff_to(run.player, "double_tap_buff", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.double_tap.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.double_tap.desc"), stacks)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.double_tap.result", stacks=stacks)

@register_card("feed")
class FeedCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 14 if self.upgraded else 10)
        hp_gain = getattr(self, "heal_amount", getattr(self, "hp_gain", 4 if self.upgraded else 3))
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        enemy_to_attack = None
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    enemy_to_attack = run.enemies[idx]
            except ValueError:
                pass
        engine._damage_target(run, target, dmg, damage_type="slashing", card=self, damage_ready=True)
        if enemy_to_attack and enemy_to_attack.hp <= 0:
            run.player.max_hp += hp_gain
            engine._heal_target(run, "p0", hp_gain)
            return get_locale_text("i18n_cards_warrior_wizard.warrior.feed.kill", name=name, dmg=dmg, hp_gain=hp_gain)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.feed.miss", name=name, dmg=dmg)

@register_card("inflame")
class InflameCard(Card):
    def execute(self, run, target, engine) -> str:
        strength_gain = getattr(self, "strength_gain", 3 if self.upgraded else 2)
        engine._add_buff_to(run.player, "strength", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.strength.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.strength.desc"), strength_gain)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.inflame.result", strength_gain=strength_gain)

@register_card("barricade")
class BarricadeCard(Card):
    def execute(self, run, target, engine) -> str:
        stacks = getattr(self, "buff_stacks", 1)
        engine._add_buff_to(run.player, "buffer", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.buffer.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.buffer.desc"), stacks)
        engine._add_buff_to(run.player, "barricade", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.barricade.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.barricade.desc"), stacks)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.barricade.result", stacks=stacks)

@register_card("metallicize")
class MetallicizeCard(Card):
    def execute(self, run, target, engine) -> str:
        stacks = getattr(self, "buff_stacks", 6 if self.upgraded else 4)
        engine._add_buff_to(run.player, "metallicize", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.metallicize.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.metallicize.desc"), stacks)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.metallicize.result", stacks=stacks)

@register_card("bludgeon")
class BludgeonCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 42 if self.upgraded else 32)
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="bludgeoning", card=self, damage_ready=True)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.bludgeon.result", name=name, dmg=dmg)

@register_card("demon_form")
class DemonFormCard(Card):
    def execute(self, run, target, engine) -> str:
        stacks = getattr(self, "strength_gain", 4 if self.upgraded else 3)
        engine._add_buff_to(run.player, "demon_form", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.demon_form.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.demon_form.desc"), stacks)
        bonus = ""
        if self.upgraded:
            gain_a = getattr(self, "gain_a", getattr(self, "action_gain", 1))
            run.player.actions += gain_a
            bonus = get_locale_text("i18n_cards_warrior_wizard.warrior.demon_form.bonus", gain_a=gain_a)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.demon_form.result", bonus=bonus, stacks=stacks)

@register_card("impervious")
class ImperviousCard(Card):
    def execute(self, run, target, engine) -> str:
        shield = getattr(self, "shield_amount", 50 if self.upgraded else 30)
        engine._gain_shield(run, "p0", shield)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.impervious.result", shield=shield)


@register_card("entrench")
class EntrenchCard(Card):
    def execute(self, run, target, engine) -> str:
        multiplier = getattr(self, "multiplier", 3 if self.upgraded else 2)
        old_shield = run.player.shield
        new_shield = old_shield * multiplier
        gain = new_shield - old_shield
        if gain > 0:
            engine._gain_shield(run, "p0", gain)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.entrench.result", gain=gain, old_shield=old_shield, new_shield=new_shield)


@register_card("tactical_barrack")
@register_card("iron_phalanx_seal")
@register_card("grand_coronation")
@register_card("blade_regiment_banner")
class DeployWarriorAmuletCard(Card):
    def __init__(self, id, name, color, type, cost_a, cost_ba, countdown, amulet_desc, desc=""):
        super().__init__(id, name, color, type, cost_a, cost_ba, countdown=countdown, desc=desc)
        self.amulet_desc = amulet_desc

    def execute(self, run, target, engine) -> str:
        grid = engine._get_free_grid(run.player)
        from ...data.card_data import CARD_CONFIG
        cfg = CARD_CONFIG.get(self.id, {})
        if grid:
            cd = self.countdown
            if "ancient_keyring" in run.player.relics:
                import random
                if random.random() < KEYRING_COUNTDOWN_REDUCTION_CHANCE:
                    cd = max(MIN_AMULET_COUNTDOWN, cd - 1)
            from ...models.state import AmuletState
            run.player.amulets[grid] = AmuletState(self.id, self.name, cd, self.amulet_desc)
            if getattr(run.player, "subclass", "") == "秘钥学者":
                engine._heal_target(run, "p0", cfg.get("heal_amount", 3))
                engine._gain_shield(run, "p0", cfg.get("shield_amount", 4))
            feedback_success = cfg.get("feedback_success", get_locale_text("i18n_cards_warrior_wizard.warrior.deploy.success"))
            return feedback_success.format(name=self.name, grid=grid)
        return cfg.get("feedback_fail", get_locale_text("i18n_cards_warrior_wizard.warrior.deploy.fail"))

@register_card("warrior_hell_raider")
class WarriorHellRaiderCard(Card):
    def execute(self, run, target, engine) -> str:
        stacks = getattr(self, "buff_stacks", 1)
        if self.upgraded:
            engine._add_buff_to(run.player, "hell_raider_upgraded", get_locale_text("i18n_cards_warrior_wizard.warrior.hell_raider.buff_name_upgraded"), get_locale_text("i18n_cards_warrior_wizard.warrior.hell_raider.buff_desc_upgraded"), stacks)
            return get_locale_text("i18n_cards_warrior_wizard.warrior.hell_raider.result_upgraded")
        else:
            engine._add_buff_to(run.player, "hell_raider", get_locale_text("i18n_cards_warrior_wizard.warrior.hell_raider.buff_name"), get_locale_text("i18n_cards_warrior_wizard.warrior.hell_raider.buff_desc"), stacks)
            return get_locale_text("i18n_cards_warrior_wizard.warrior.hell_raider.result")

@register_card("warrior_shield_bash")
class WarriorShieldBashCard(Card):
    def execute(self, run, target, engine) -> str:
        shield_val = getattr(self, "shield_amount", 24 if self.upgraded else 16)
        engine._gain_shield(run, "p0", shield_val)
        dmg = run.player.shield // SHIELD_BASH_DAMAGE_DIVISOR
        name = engine._get_target_name(run, target)
        engine._damage_target(run, target, dmg, damage_type="bludgeoning", card=self)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.shield_bash.result", name=name, shield=shield_val, dmg=dmg)

@register_card("warrior_blood_fury")
class WarriorBloodFuryCard(Card):
    def execute(self, run, target, engine) -> str:
        loss_val = getattr(self, "self_hp_cost", getattr(self, "hp_loss", 3 if self.upgraded else 5))
        str_val = getattr(self, "strength_gain", 3 if self.upgraded else 2)
        draw_val = getattr(self, "draw_count", 3 if self.upgraded else 2)
        loss = min(loss_val, run.player.hp - 1)
        if loss > 0:
            engine._damage_target(run, "p0", loss, source="self", damage_type="true")
        engine._add_buff_to(run.player, "strength", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.strength.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.strength_blood_fury.desc"), str_val)
        engine._draw_cards(run.player, draw_val, run)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.blood_fury.result", loss=loss, strength=str_val, draw=draw_val)

@register_card("warrior_source_of_cinder")
class WarriorSourceOfCinderCard(Card):
    def execute(self, run, target, engine) -> str:
        engine._add_buff_to(run.player, "source_of_cinder", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.source_of_cinder.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.source_of_cinder.desc"), getattr(self, "buff_stacks", 1))
        return get_locale_text("i18n_cards_warrior_wizard.warrior.source_of_cinder.result")

@register_card("warrior_hematopoiesis")
class WarriorHematopoiesisCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        shield_val = p.shield
        p.shield = 0
        
        factor = getattr(self, "factor", 1.5 if self.upgraded else 1.0)
        temp_hp = int(shield_val * factor)
        engine._heal_target(run, "p0", temp_hp)
        
        import math
        draw_divisor = getattr(self, "draw_divisor", 10)
        draw_count = math.ceil(shield_val / draw_divisor)
        drawn_msg = ""
        if draw_count > 0:
            engine.card_player.draw_cards(p, draw_count, run)
            drawn_msg = get_locale_text("i18n_cards_warrior_wizard.warrior.hematopoiesis.drawn", draw_count=draw_count)
            
        return get_locale_text("i18n_cards_warrior_wizard.warrior.hematopoiesis.result", name=self.name, shield=shield_val, temp_hp=temp_hp, drawn_msg=drawn_msg)

@register_card("discover")
class DiscoverCard(Card):
    def execute(self, run, target, engine) -> str:
        from .base import ALL_CARDS
        p = run.player
        max_count = getattr(self, "max_count", 2 if self.upgraded else 1)
        valid_exhaust = [c for c in p.exhaust_pile if c.id != "discover"]
        if not valid_exhaust:
            return get_locale_text("i18n_cards_warrior_wizard.warrior.discover.no_cards", name=self.name)

        if target is not None:
            parts_str = str(target)
            if "," in parts_str:
                parts = parts_str.split(",")
            else:
                parts = parts_str.split()
            
            indices = []
            for p_str in parts:
                p_str = p_str.strip()
                if p_str.isdigit():
                    indices.append(int(p_str) - 1)
            
            valid_indices = [idx for idx in indices if 0 <= idx < len(valid_exhaust)]
            valid_indices = valid_indices[:max_count]
            
            if valid_indices:
                valid_indices.sort(reverse=True)
                selected_names = []
                for idx in valid_indices:
                    target_card = valid_exhaust[idx]
                    real_idx = p.exhaust_pile.index(target_card)
                    cid = p.exhaust_pile.pop(real_idx)
                    DeckService.add_card_to_hand(p, cid)
                    selected_names.append(ALL_CARDS[cid].name if cid in ALL_CARDS else get_locale_text("i18n_cards_warrior_wizard.warrior.discover.unknown_card"))
                selected_names.reverse()
                return get_locale_text("i18n_cards_warrior_wizard.warrior.discover.success", name=self.name, names=", ".join(selected_names))
            else:
                return get_locale_text("i18n_cards_warrior_wizard.warrior.discover.invalid")

        run.node_data.setdefault("state_stack", []).append({
            "type": "discover_selection",
            "count": max_count,
            "selected": []
        })
        exhaust_list = "\n".join(f"{i+1}. {ALL_CARDS[c].name}" for i, c in enumerate(valid_exhaust))
        return get_locale_text("i18n_cards_warrior_wizard.warrior.discover.prompt", exhaust_list=exhaust_list)

@register_card("strike_of_all")
class StrikeOfAllCard(Card):
    def execute(self, run, target, engine) -> str:
        from .base import ALL_CARDS
        p = run.player
        X = 0
        for cid in p.deck:
            card = ALL_CARDS.get(cid)
            if card and "打击" in card.name:
                X += 1
        base_coef = getattr(self, "coef", 12 if self.upgraded else 8)
        dmg = int((STRIKE_OF_ALL_GROWTH ** X) * base_coef)
        name = engine._get_target_name(run, target)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        engine._damage_target(run, target, dmg, damage_type="slashing", card=self, damage_ready=True)
        moved_cards = []
        for cid in list(p.draw_pile):
            card = ALL_CARDS.get(cid)
            if card and "打击" in card.name:
                p.draw_pile.remove(cid)
                DeckService.add_card_to_hand(p, cid)
                moved_cards.append(card.name)
        for cid in list(p.discard_pile):
            card = ALL_CARDS.get(cid)
            if card and "打击" in card.name:
                p.discard_pile.remove(cid)
                DeckService.add_card_to_hand(p, cid)
                moved_cards.append(card.name)
        for cid in list(p.exhaust_pile):
            card = ALL_CARDS.get(cid)
            if card and "打击" in card.name:
                p.exhaust_pile.remove(cid)
                DeckService.add_card_to_hand(p, cid)
                moved_cards.append(card.name)
        msg = get_locale_text("i18n_cards_warrior_wizard.warrior.strike_of_all.result", name=name, dmg=dmg, x=X)
        if moved_cards:
            msg += get_locale_text("i18n_cards_warrior_wizard.warrior.strike_of_all.moved", names=", ".join(moved_cards))
        else:
            msg += get_locale_text("i18n_cards_warrior_wizard.warrior.strike_of_all.none")
        return msg

