from typing import Optional, List
from ...models.state import Card
from ...data.card_data import CARD_CONFIG
from ...data.locale_data import get_locale_text
from .registry import register_card

@register_card("time_warp")
class TimeWarpCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        max_hand = getattr(self, "hand_limit", 12)
        if "mask_of_void" in p.relics:
            max_hand = getattr(self, "mask_hand_limit", 9)
        p.draw_pile.extend(p.discard_pile)
        p.draw_pile.extend(p.hand)
        p.discard_pile.clear()
        p.hand.clear()
        import random
        random.shuffle(p.draw_pile)
        before = len(p.hand)
        engine._draw_cards(p, max_hand, run)
        after = len(p.hand)
        draw_count = after - before
        if self.upgraded:
            gain_a = getattr(self, "gain_a", 1)
            gain_ba = getattr(self, "gain_ba", 1)
            buff_stacks = getattr(self, "buff_stacks", 1)
            p.actions += gain_a
            p.bonus_actions += gain_ba
            engine._add_buff_to(p, "time_warp_spell_boost", get_locale_text("i18n_cards_neutral.legendary.time_warp.buff_name"), get_locale_text("i18n_cards_neutral.legendary.time_warp.buff_desc"), buff_stacks)
            return get_locale_text("i18n_cards_neutral.legendary.time_warp.result_upgraded", draw_count=draw_count)
        cfg = CARD_CONFIG.get(self.id, {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(draw_count=draw_count)
        return get_locale_text("i18n_cards_neutral.legendary.time_warp.result", draw_count=draw_count)

@register_card("meteor_swarm")
class MeteorSwarmCard(Card):
    def __init__(self, id, name, color, type, cost_a, cost_ba, base_dmg, desc=""):
        super().__init__(id, name, color, type, cost_a, cost_ba, desc=desc)
        self.base_dmg = base_dmg

    def execute(self, run, target, engine) -> str:
        import random
        num_dice = getattr(self, "hit_count", getattr(self, "dice_count", 12 if self.upgraded else 8))
        die_size = getattr(self, "die_size", 12)
        dice_results = [random.randint(1, die_size) for _ in range(num_dice)]
        dmg = sum(dice_results)
        extra_true_dmg = 0
        if self.upgraded:
            dice_threshold = getattr(self, "dice_threshold", 8)
            extra_per_die = getattr(self, "extra_true_damage", 2)
            extra_true_dmg = sum(extra_per_die for d in dice_results if d > dice_threshold)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        for idx in range(len(run.enemies) - 1, -1, -1):
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type="fire", card=self, damage_ready=True)
            if extra_true_dmg > 0:
                engine._damage_target(run, f"e{idx+1}", extra_true_dmg, damage_type="true", card=self)
        if self.upgraded:
            if extra_true_dmg > 0:
                return get_locale_text("i18n_cards_neutral.legendary.meteor_swarm.result_extra", dmg=dmg, extra_true_dmg=extra_true_dmg)
            return get_locale_text("i18n_cards_neutral.legendary.meteor_swarm.result", dmg=dmg)
        cfg = CARD_CONFIG.get(self.id, {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(dmg=dmg)
        return get_locale_text("i18n_cards_neutral.legendary.meteor_swarm.result", dmg=dmg)

@register_card("archmage_wish")
class ArchmageWishCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        shield_amount = getattr(self, "shield_amount", 15 if self.upgraded else 10)
        draw_count = getattr(self, "draw_count", 3 if self.upgraded else 2)
        if self.upgraded:
            engine._gain_shield(run, "p0", shield_amount)
            engine._add_buff_to(p, "wish_power+", get_locale_text("i18n_cards_neutral.legendary.archmage_wish.buff_name"), get_locale_text("i18n_cards_neutral.legendary.archmage_wish.buff_desc_upgraded"))
            before_hand = list(p.hand)
            engine._draw_cards(p, draw_count, run)
            drawn = p.hand[len(before_hand):]
            run.node_data.setdefault("temp_retain_cards", []).extend(drawn)
            return get_locale_text("i18n_cards_neutral.legendary.archmage_wish.result_upgraded")
        else:
            engine._gain_shield(run, "p0", shield_amount)
            engine._add_buff_to(p, "wish_power", get_locale_text("i18n_cards_neutral.legendary.archmage_wish.buff_name"), get_locale_text("i18n_cards_neutral.legendary.archmage_wish.buff_desc"))
            engine._draw_cards(p, draw_count, run)
            cfg = CARD_CONFIG.get(self.id, {})
            return cfg.get("feedback", get_locale_text("i18n_cards_neutral.legendary.archmage_wish.result"))

@register_card("time_stop")
class TimeStopCard(Card):
    def execute(self, run, target, engine) -> str:
        extra_turns = getattr(self, "extra_turns", 4 if self.upgraded else 3)
        if self.upgraded:
            run.node_data["extra_turns_left"] = extra_turns
            run.node_data["time_stop_upgraded"] = True
            return get_locale_text("i18n_cards_neutral.legendary.time_stop.result_upgraded")
        else:
            run.node_data["extra_turns_left"] = extra_turns
            run.node_data["time_stop_upgraded"] = False
            cfg = CARD_CONFIG.get(self.id, {})
            return cfg.get("feedback", get_locale_text("i18n_cards_neutral.legendary.time_stop.result"))

@register_card("break_limits")
class BreakLimitsCard(Card):
    def execute(self, run, target, engine) -> str:
        from ..buffs import is_debuff
        p = run.player
        doubled_count = 0
        threshold = getattr(self, "threshold", 2000)
        multiplier = getattr(self, "multiplier", 2)
        gain_a = getattr(self, "gain_a", 1)
        gain_ba = getattr(self, "gain_ba", 1)
        for b in p.buffs:
            if not is_debuff(b.id):
                if b.stacks <= threshold:
                    b.stacks *= multiplier
                    if getattr(b, "stacks2", None) is not None:
                        b.stacks2 *= multiplier
                    doubled_count += 1
        p.actions += gain_a
        if self.upgraded:
            p.bonus_actions += gain_ba
            return get_locale_text("i18n_cards_neutral.legendary.break_limits.result_upgraded", doubled_count=doubled_count)
        return get_locale_text("i18n_cards_neutral.legendary.break_limits.result", doubled_count=doubled_count)

@register_card("abyss_collapse")
class AbyssCollapseCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 32 if self.upgraded else 24)
        stun_multiplier = getattr(self, "stun_multiplier", 2)
        if "abyss_gaze" in run.player.relics:
            dmg += 4
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        
        feedback_parts = []
        for idx in range(len(run.enemies) - 1, -1, -1):
            enemy = run.enemies[idx]
            is_stunned = any(b.id == "stun" for b in enemy.buffs)
            final_dmg = dmg * stun_multiplier if is_stunned else dmg
            engine._damage_target(run, f"e{idx+1}", final_dmg, damage_type="necrotic", card=self, damage_ready=True)
            feedback_parts.append(get_locale_text("i18n_cards_neutral.legendary.abyss_collapse.part", enemy_name=enemy.name, final_dmg=final_dmg))
        return get_locale_text("i18n_cards_neutral.legendary.abyss_collapse.result", parts="，".join(feedback_parts))

@register_card("demon_contract")
class DemonContractCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        ba_gain = getattr(self, "gain_ba", 3 if self.upgraded else 2)
        draw_cnt = getattr(self, "draw_count", 4 if self.upgraded else 3)
        p.bonus_actions += ba_gain
        engine._draw_cards(p, draw_cnt, run)
        
        buff_id = "demon_contract_buff"
        buff_stacks = getattr(self, "buff_stacks", 2 if self.upgraded else 1)
        engine._add_buff_to(p, buff_id, get_locale_text("i18n_cards_neutral.legendary.demon_contract.buff_name"), get_locale_text("i18n_cards_neutral.legendary.demon_contract.buff_desc"), buff_stacks)
        return get_locale_text("i18n_cards_neutral.legendary.demon_contract.result", ba_gain=ba_gain, draw_cnt=draw_cnt, buff_stacks=buff_stacks)

@register_card("frost_nova")
class FrostNovaCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 20 if self.upgraded else 14)
        if "frost_blade" in run.player.relics:
            dmg += 4
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        
        vuln_stacks = getattr(self, "buff_stacks", 3 if self.upgraded else 2)
        stun_turns = getattr(self, "buff_turns", 1)
        feedback_parts = []
        for idx in range(len(run.enemies) - 1, -1, -1):
            enemy = run.enemies[idx]
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type="cold", card=self, damage_ready=True)
            engine._add_buff_to(enemy, "minor_vulnerable_cold", get_locale_text("i18n_cards_neutral.neutral.buffs.cold_vulnerable.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.cold_vulnerable.desc"), vuln_stacks)
            engine._add_buff_to(enemy, "stun", get_locale_text("i18n_cards_neutral.neutral.buffs.stun.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.stun.desc"), stun_turns)
            feedback_parts.append(get_locale_text("i18n_cards_neutral.legendary.frost_nova.part", enemy_name=enemy.name, dmg=dmg, vuln_stacks=vuln_stacks))
        return get_locale_text("i18n_cards_neutral.legendary.frost_nova.result", parts="，".join(feedback_parts))

@register_card("glacier_fortress")
class GlacierFortressCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        shield_val = getattr(self, "shield_amount", 28 if self.upgraded else 20)
        buff_stacks = getattr(self, "buff_stacks", 1)
        engine._gain_shield(run, "p0", shield_val)
        
        buff_id = "glacier_fortress_buff+" if self.upgraded else "glacier_fortress_buff"
        engine._add_buff_to(p, buff_id, get_locale_text("i18n_cards_neutral.legendary.glacier_fortress.buff_name"), get_locale_text("i18n_cards_neutral.legendary.glacier_fortress.buff_desc"), buff_stacks)
        return get_locale_text("i18n_cards_neutral.legendary.glacier_fortress.result", shield_val=shield_val)

@register_card("abyss_erosion")
class AbyssErosionCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 15 if self.upgraded else 10)
        if "abyss_gaze" in run.player.relics:
            dmg += 4
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        weakness_stacks = getattr(self, "buff_stacks", 5 if self.upgraded else 3)
        engine._damage_target(run, target, dmg, damage_type="necrotic", card=self, damage_ready=True)
        enemy_state = None
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    enemy_state = run.enemies[idx]
            except ValueError:
                pass
        if not enemy_state and run.enemies:
            enemy_state = run.enemies[0]
        if enemy_state:
            engine._add_buff_to(enemy_state, "void_weakness", get_locale_text("i18n_cards_neutral.legendary.abyss_erosion.buff_name"), get_locale_text("i18n_cards_neutral.legendary.abyss_erosion.buff_desc"), weakness_stacks)
        tname = engine._get_target_name(run, target)
        return get_locale_text("i18n_cards_neutral.legendary.abyss_erosion.result", target=tname, weakness_stacks=weakness_stacks)

@register_card("glacier_tempest")
class GlacierTempestCard(Card):
    def execute(self, run, target, engine) -> str:
        base_dmg = getattr(self, "base_dmg", 18 if self.upgraded else 12)
        shield_ratio = getattr(self, "shield_ratio", 0.5)
        if "frost_blade" in run.player.relics:
            base_dmg += 4
        total_dmg = 0
        feedback_parts = []
        dmg = engine.get_modified_spell_damage(run, self, base_dmg)
        for idx in range(len(run.enemies) - 1, -1, -1):
            enemy = run.enemies[idx]
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type="cold", card=self, damage_ready=True)
            total_dmg += dmg
            feedback_parts.append(get_locale_text("i18n_cards_neutral.legendary.glacier_tempest.part", enemy_name=enemy.name, dmg=dmg))
        shield_msg = ""
        if run.player.minions and total_dmg > 0:
            shield_gain = int(total_dmg * shield_ratio)
            engine._gain_shield(run, "p0", shield_gain)
            shield_msg = get_locale_text("i18n_cards_neutral.legendary.glacier_tempest.shield_suffix", shield_gain=shield_gain)
        return get_locale_text("i18n_cards_neutral.legendary.glacier_tempest.result", parts="，".join(feedback_parts), shield_msg=shield_msg)
