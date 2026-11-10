from typing import Optional, List
from ...models.state import Card
from ...data.card_data import CARD_CONFIG
from ...data.locale_data import get_locale_text
from .registry import register_card

THUNDERWAVE_ACTION_LOSS = 1

@register_card("magic_missile")
class MagicMissileCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 4 if self.upgraded else 3)
        count = getattr(self, "hit_count", getattr(self, "count", 4 if self.upgraded else 3))
        total = 0
        name = engine._get_target_name(run, target)
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if idx < 0:
                    idx = 0
            except ValueError:
                idx = 0
            if 0 <= idx < len(run.enemies):
                original_enemy = run.enemies[idx]
                dmg = engine.get_modified_spell_damage(run, self, dmg)
                for _ in range(count):
                    if original_enemy in run.enemies:
                        curr_idx = run.enemies.index(original_enemy)
                        engine._damage_target(run, f"e{curr_idx+1}", dmg, damage_type="true", card=self, damage_ready=True)
                        total += dmg
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(target=name, count=count, total=total)
        return get_locale_text("i18n_cards_warrior_wizard.wizard.magic_missile.result", name=name, count=count, total=total)

@register_card("fireball")
class FireballCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 24 if self.upgraded else 18)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        for idx in range(len(run.enemies) - 1, -1, -1):
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type="fire", card=self, damage_ready=True)
            
        burn_dmg = getattr(self, "burn_damage", 8 if self.upgraded else 6)
        burn_turns = getattr(self, "burn_turns", 3 if self.upgraded else 2)
        for enemy in list(run.enemies):
            engine._add_buff_to(enemy, "burning", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.burning.name"), get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.burning.desc"), burn_dmg, burn_turns)

        bonus_msg = ""
        if getattr(self, "id", "") == "fireball" and bool(getattr(self, "upgraded", False)):
            engine._add_buff_to(run.player, "fire_grow", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.fire_grow.name"), get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.fire_grow.desc"), getattr(self, "buff_stacks", 1))
            bonus_msg = get_locale_text("i18n_cards_warrior_wizard.wizard.fireball.bonus")
            
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(dmg=dmg) + bonus_msg
        return get_locale_text("i18n_cards_warrior_wizard.wizard.fireball.result", dmg=dmg) + bonus_msg

@register_card("thunderwave")
class ThunderwaveCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 9 if self.upgraded else 6)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        for idx in range(len(run.enemies) - 1, -1, -1):
            run.enemies[idx].actions = max(0, run.enemies[idx].actions - THUNDERWAVE_ACTION_LOSS)
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type="thunder", card=self, damage_ready=True)
            
        bonus_msg = ""
        if self.upgraded:
            first_enemy = engine._get_first_alive_enemy(run)
            if first_enemy:
                try:
                    f_idx = int(first_enemy.replace("e", "")) - 1
                    if 0 <= f_idx < len(run.enemies):
                        stun_turns = getattr(self, "buff_turns", getattr(self, "stun_turns", 1))
                        engine._add_buff_to(run.enemies[f_idx], "stun", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.stun.name"), get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.stun.desc"), stun_turns)
                        bonus_msg = get_locale_text("i18n_cards_warrior_wizard.wizard.thunderwave.bonus", name=run.enemies[f_idx].name, stun_turns=stun_turns)
                except ValueError:
                    pass
                    
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(dmg=dmg) + bonus_msg
        return get_locale_text("i18n_cards_warrior_wizard.wizard.thunderwave.result", dmg=dmg) + bonus_msg

@register_card("shield")
class ShieldSpellCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        shield_val = getattr(self, "shield_amount", 12 if self.upgraded else 8)
        heal_ratio = getattr(self, "heal_ratio", 0.5)
        hp_threshold = getattr(self, "hp_threshold", 0.5)
        if self.upgraded and p.hp < p.max_hp * hp_threshold:
            heal_val = int(shield_val * heal_ratio)
            shield_val = shield_val - heal_val
            engine._heal_target(run, "p0", heal_val)
            engine._gain_shield(run, "p0", shield_val)
            return get_locale_text("i18n_cards_warrior_wizard.wizard.shield.heal_result", shield=shield_val, heal=heal_val)
        else:
            engine._gain_shield(run, "p0", shield_val)
            cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
            feedback_tmpl = cfg.get("feedback")
            if feedback_tmpl:
                return feedback_tmpl.format(shield_amount=shield_val)
            return get_locale_text("i18n_cards_warrior_wizard.wizard.shield.result", shield=shield_val)

@register_card("arcane_spark")
class ArcaneSparkCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 4 if self.upgraded else 2)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        name = engine._get_target_name(run, target)
        engine._damage_target(run, target, dmg, damage_type=self.damage_type, card=self, damage_ready=True)
        
        p = run.player
        before_hand_len = len(p.hand)
        draw_count = getattr(self, "draw_count", 1)
        engine._draw_cards(p, draw_count, run)
        
        bonus_msg = ""
        if self.upgraded and len(p.hand) > before_hand_len:
            drawn_cid = p.hand[-1]
            from .base import ALL_CARDS
            drawn_card = ALL_CARDS.get(drawn_cid)
            if drawn_card and drawn_card.type == "spell":
                run.node_data.setdefault("free_spells_this_turn", []).append(drawn_cid)
                bonus_msg = get_locale_text("i18n_cards_warrior_wizard.wizard.arcane_spark.bonus", name=drawn_card.name)
                
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(target=name, dmg=dmg) + bonus_msg
        return get_locale_text("i18n_cards_warrior_wizard.wizard.arcane_spark.result", name=name, dmg=dmg, draw_count=draw_count) + bonus_msg

@register_card("echo_form")
class EchoFormCard(Card):
    def execute(self, run, target, engine) -> str:
        from ...data.buff_data import BUFF_CONFIG
        buff_info = BUFF_CONFIG.get("echo_form", {})
        buff_name = buff_info.get("name", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.echo_form.name"))
        buff_desc = buff_info.get("desc", "")
        engine._add_buff_to(run.player, "echo_form", buff_name, buff_desc)
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(name=self.name)
        return get_locale_text("i18n_cards_warrior_wizard.wizard.echo_form.result", name=self.name)

@register_card("doomsday_judgment")
class DoomsdayJudgmentCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 24 if self.upgraded else 18)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        for idx in range(len(run.enemies) - 1, -1, -1):
            stun_turns = getattr(self, "buff_turns", getattr(self, "stun_turns", 1))
            engine._add_buff_to(run.enemies[idx], "stun", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.stun.name"), get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.stun.desc"), stun_turns)
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type="necrotic", card=self, damage_ready=True)
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(dmg=dmg)
        return get_locale_text("i18n_cards_warrior_wizard.wizard.doomsday_judgment.result", dmg=dmg)

@register_card("overcharge")
class OverchargeCard(Card):
    def __init__(self, id, name, color, type, cost_a, cost_ba, exhaust=False, desc=""):
        super().__init__(id, name, color, type, cost_a, cost_ba, exhaust=exhaust, desc=desc)

    def execute(self, run, target, engine) -> str:
        stacks = getattr(self, "buff_stacks", 2 if self.upgraded else 1)
        engine._add_buff_to(run.player, "arcane_charge", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.arcane_charge.name"), get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.arcane_charge.desc"), stacks)
        bonus_msg = ""
        if self.upgraded:
            draw_count = getattr(self, "draw_count", 1)
            engine._draw_cards(run.player, draw_count, run)
            bonus_msg = get_locale_text("i18n_cards_warrior_wizard.wizard.overcharge.bonus", draw_count=draw_count)
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        base_feedback = cfg.get("feedback", get_locale_text("i18n_cards_warrior_wizard.wizard.overcharge.feedback"))
        return base_feedback.replace(get_locale_text("i18n_cards_warrior_wizard.wizard.overcharge.suffix"), "") + get_locale_text("i18n_cards_warrior_wizard.wizard.overcharge.stacks", stacks=stacks) + bonus_msg

@register_card("magic_network")
class MagicNetworkCard(Card):
    def execute(self, run, target, engine) -> str:
        buff_id = "magic_network+" if self.upgraded else "magic_network"
        buff_name = get_locale_text("i18n_cards_warrior_wizard.wizard.magic_network.buff_name_upgraded") if self.upgraded else get_locale_text("i18n_cards_warrior_wizard.wizard.magic_network.buff_name")
        damage_amount = getattr(self, "damage_amount", 5 if self.upgraded else 3)
        shield_amount = getattr(self, "shield_amount", 5 if self.upgraded else 3)
        buff_desc = get_locale_text("i18n_cards_warrior_wizard.wizard.magic_network.buff_desc", damage_amount=damage_amount, shield_amount=shield_amount) + (get_locale_text("i18n_cards_warrior_wizard.wizard.magic_network.buff_desc_echo") if self.upgraded else "")
        engine._add_buff_to(run.player, buff_id, buff_name, buff_desc)
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        return cfg.get("feedback", get_locale_text("i18n_cards_warrior_wizard.wizard.magic_network.feedback"))

@register_card("fleeting_spark")
class FleetingSparkCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 9 if self.upgraded else 6)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        name = engine._get_target_name(run, target)
        engine._damage_target(run, target, dmg, damage_type=self.damage_type, card=self, damage_ready=True)
        
        draw_count = getattr(self, "draw_count", 3 if self.upgraded else 2)
        engine._draw_cards(run.player, draw_count, run)
        p = run.player
        if p.hand:
            run.node_data["pending_discard"] = True
            run.node_data["pending_discard_source"] = self.id
            return get_locale_text("i18n_cards_warrior_wizard.wizard.fleeting_spark.discard", name=self.name, target=name, dmg=dmg, draw_count=draw_count)
        else:
            return get_locale_text("i18n_cards_warrior_wizard.wizard.fleeting_spark.empty", name=self.name, target=name, dmg=dmg, draw_count=draw_count)

@register_card("chain_lightning")
class ChainLightningCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 18 if self.upgraded else 12)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        name = engine._get_target_name(run, target)
        def get_base_name(n: str) -> str:
            parts = n.split()
            if len(parts) > 1 and len(parts[-1]) == 1 and parts[-1].isupper():
                return " ".join(parts[:-1])
            return n
        base_target_name = ""
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if idx < 0:
                    idx = 0
            except ValueError:
                idx = 0
            if 0 <= idx < len(run.enemies):
                base_target_name = get_base_name(run.enemies[idx].name)
                
        bonus_msg = ""
        if self.upgraded and base_target_name:
            same_name_count = sum(1 for e in run.enemies if get_base_name(e.name) == base_target_name)
            if same_name_count == 1:
                crit_multiplier = getattr(self, "crit_multiplier", 1.5)
                dmg = int(dmg * crit_multiplier)
                bonus_msg = get_locale_text("i18n_cards_warrior_wizard.wizard.chain_lightning.bonus")
                
        affected_count = 0
        if base_target_name:
            for idx in range(len(run.enemies) - 1, -1, -1):
                enemy = run.enemies[idx]
                if get_base_name(enemy.name) == base_target_name:
                    engine._damage_target(run, f"e{idx+1}", dmg, damage_type="lightning", card=self, damage_ready=True)
                    affected_count += 1
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(dmg=dmg) + bonus_msg
        return get_locale_text("i18n_cards_warrior_wizard.wizard.chain_lightning.result", dmg=dmg) + bonus_msg

@register_card("sunburst")
class SunburstCard(Card):
    def execute(self, run, target, engine) -> str:
        dmg = getattr(self, "base_dmg", 22 if self.upgraded else 16)
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        for idx in range(len(run.enemies) - 1, -1, -1):
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type="radiant", card=self, damage_ready=True)
            
        players = list(run.players.values()) if getattr(run, "coop_id", "") else [run.player]
        previous_player = run.player
        previous_user = run.user_id
        for player in players:
            if player.hp <= 0 or player.downed:
                continue
            run.player = player
            uid = run.uid_for(player)
            if uid:
                run.user_id = uid
            for grid in list(player.minions.keys()):
                if grid not in player.minions:
                    continue
                engine._damage_target(run, f"p{grid}", dmg, damage_type="radiant", card=self, damage_ready=True)
        run.player = previous_player
        run.user_id = previous_user

        bonus_msg = ""
        if self.upgraded:
            ally_atk_bonus = getattr(self, "ally_atk_bonus", 3)
            for player in players:
                if player.hp <= 0 or player.downed:
                    continue
                for grid, m_state in list(player.minions.items()):
                    m_state.buffs.clear()
                    m_state.atk += ally_atk_bonus
                    engine._log_event(run, get_locale_text("i18n_cards_warrior_wizard.wizard.sunburst.log", name=m_state.name, ally_atk_bonus=ally_atk_bonus))
            bonus_msg = get_locale_text("i18n_cards_warrior_wizard.wizard.sunburst.bonus", ally_atk_bonus=ally_atk_bonus)
            
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(dmg=dmg) + bonus_msg
        return get_locale_text("i18n_cards_warrior_wizard.wizard.sunburst.result", dmg=dmg) + bonus_msg

@register_card("arcane_torrent")
class ArcaneTorrentCard(Card):
    def execute(self, run, target, engine) -> str:
        X = run.node_data.get("last_x_cost_a", 0)
        single_dmg = getattr(self, "damage_amount", 4 if self.upgraded else 3)
        threshold = getattr(self, "threshold", 2)
        coef = getattr(self, "coef", 2)
        factor = getattr(self, "factor", 4)
        if X <= threshold:
            count = X * coef
        else:
            count = X * factor
        single_dmg = engine.get_modified_spell_damage(run, self, single_dmg)
        for enemy in list(run.enemies):
            for _ in range(count):
                if enemy in run.enemies:
                    curr_idx = run.enemies.index(enemy)
                    engine._damage_target(run, f"e{curr_idx+1}", single_dmg, damage_type="true", card=self, damage_ready=True)
        from ...data.card_data import CARD_CONFIG
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(count=count, dmg=single_dmg)
        return get_locale_text("i18n_cards_warrior_wizard.wizard.arcane_torrent.result", count=count, dmg=single_dmg)

@register_card("arcane_barrier")
class ArcaneBarrierCard(Card):
    def execute(self, run, target, engine) -> str:
        X = run.node_data.get("last_x_cost_ba", 0)
        coef = getattr(self, "coef", 9 if self.upgraded else 6)
        shield_val = X * coef
        engine._gain_shield(run, "p0", shield_val)
        bonus_msg = ""
        if X > getattr(self, "threshold", 1):
            from ...data.buff_data import BUFF_CONFIG
            buff_info = BUFF_CONFIG.get("buffer", {})
            buff_name = buff_info.get("name", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.buffer.name"))
            buff_desc = buff_info.get("desc", "")
            buff_stacks = getattr(self, "buff_stacks", 1)
            engine._add_buff_to(run.player, "buffer", buff_name, buff_desc, buff_stacks)
            bonus_msg = get_locale_text("i18n_cards_warrior_wizard.wizard.arcane_barrier.bonus", buff_stacks=buff_stacks, buff_name=buff_name)
        from ...data.card_data import CARD_CONFIG
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(shield=shield_val) + bonus_msg
        return get_locale_text("i18n_cards_warrior_wizard.wizard.arcane_barrier.result", shield=shield_val) + bonus_msg

@register_card("wizard_prismatic_wall")
class WizardPrismaticWallCard(Card):
    def execute(self, run, target, engine) -> str:
        shield_val = getattr(self, "shield_amount", 25 if self.upgraded else 15)
        barrier_layers = getattr(self, "buff_stacks", 3 if self.upgraded else 2)
        reflect_damage = getattr(self, "reflect_damage", 20 if self.upgraded else 12)
        engine._gain_shield(run, "p0", shield_val)
        if self.upgraded:
            engine._add_buff_to(run.player, "prismatic_barrier_upgraded", get_locale_text("i18n_cards_warrior_wizard.wizard.prismatic_wall.buff_name_upgraded"), get_locale_text("i18n_cards_warrior_wizard.wizard.prismatic_wall.buff_desc", reflect_damage=reflect_damage), barrier_layers)
            return get_locale_text("i18n_cards_warrior_wizard.wizard.prismatic_wall.result_upgraded", shield=shield_val, barrier_layers=barrier_layers)
        else:
            engine._add_buff_to(run.player, "prismatic_barrier", get_locale_text("i18n_cards_warrior_wizard.wizard.prismatic_wall.buff_name"), get_locale_text("i18n_cards_warrior_wizard.wizard.prismatic_wall.buff_desc", reflect_damage=reflect_damage), barrier_layers)
            return get_locale_text("i18n_cards_warrior_wizard.wizard.prismatic_wall.result", shield=shield_val, barrier_layers=barrier_layers)

@register_card("wizard_antimagic_field")
class WizardAntimagicFieldCard(Card):
    def execute(self, run, target, engine) -> str:
        players = list(run.players.values()) if getattr(run, "coop_id", "") else [run.player]
        for player in players:
            player.buffs.clear()
            player.amulets.clear()
            for m in player.minions.values():
                m.buffs.clear()
        for enemy in run.enemies:
            enemy.buffs.clear()
        if self.upgraded:
            return get_locale_text("i18n_cards_warrior_wizard.wizard.antimagic_field.result_upgraded")
        else:
            return get_locale_text("i18n_cards_warrior_wizard.wizard.antimagic_field.result")

@register_card("wizard_time_ravage")
class WizardTimeRavageCard(Card):
    def execute(self, run, target, engine) -> str:
        name = engine._get_target_name(run, target)
        dmg = getattr(self, "base_dmg", 25 if self.upgraded else 15)
        debuff_layers = getattr(self, "buff_stacks", 3 if self.upgraded else 2)
        engine._damage_target(run, target, dmg, damage_type="true", card=self)
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    enemy = run.enemies[idx]
                    engine._add_buff_to(enemy, "weak", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.time_weak.name"), get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.time_weak.desc"), debuff_layers)
                    engine._add_buff_to(enemy, "vulnerable", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.vulnerable.name"), get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.vulnerable.desc"), debuff_layers)
            except ValueError:
                pass
        msg = get_locale_text("i18n_cards_warrior_wizard.wizard.time_ravage.result", name=name, dmg=dmg, debuff_layers=debuff_layers)
        if self.upgraded:
            action_gain = getattr(self, "gain_a", getattr(self, "action_gain", 1))
            run.player.actions += action_gain
            msg += get_locale_text("i18n_cards_warrior_wizard.wizard.time_ravage.bonus", action_gain=action_gain)
        return msg

@register_card("wizard_split_to_ten")
class WizardSplitToTenCard(Card):
    def execute(self, run, target, engine) -> str:
        stacks = getattr(self, "buff_stacks", 2 if self.upgraded else 1)
        from ...data.buff_data import BUFF_CONFIG
        buff_info = BUFF_CONFIG.get("split_to_ten", {})
        engine._add_buff_to(run.player, "split_to_ten", buff_info.get("name", get_locale_text("i18n_cards_warrior_wizard.wizard.buffs.split_to_ten.name")), buff_info.get("desc", ""), stacks)
        return get_locale_text("i18n_cards_warrior_wizard.wizard.split_to_ten.result", name=self.name, stacks=stacks)

@register_card("meteor_strike")
class MeteorStrikeCard(Card):
    def execute(self, run, target, engine) -> str:
        import random
        from ...models.state import AmuletState
        base_dmg = getattr(self, "base_dmg", 40 if self.upgraded else 30)
        dmg = engine.get_modified_spell_damage(run, self, base_dmg)
        hits = []
        hits_count = getattr(self, "hit_count", getattr(self, "hits", 4))
        for _ in range(hits_count):
            if not run.enemies:
                break
            enemy = random.choice(run.enemies)
            curr_idx = run.enemies.index(enemy)
            engine._damage_target(run, f"e{curr_idx+1}", dmg, damage_type="bludgeoning", card=self, damage_ready=True)
            hits.append(enemy.name)
        grid = engine._get_free_grid(run.player)
        amulet_msg = ""
        if grid:
            deploy_id = "energy_core+" if self.upgraded else "energy_core"
            deploy_name = get_locale_text("i18n_cards_warrior_wizard.wizard.meteor_strike.deploy_name_upgraded") if self.upgraded else get_locale_text("i18n_cards_warrior_wizard.wizard.meteor_strike.deploy_name")
            countdown = getattr(self, "countdown", 1)
            action_gain = getattr(self, "gain_a", getattr(self, "action_gain", 2 if self.upgraded else 1))
            bonus_action_gain = getattr(self, "gain_ba", getattr(self, "bonus_action_gain", 1))
            desc_val = f"{action_gain}A {bonus_action_gain}BA"
            deploy_desc = get_locale_text("i18n_cards_warrior_wizard.wizard.meteor_strike.deploy_desc", desc_val=desc_val)
            run.player.amulets[grid] = AmuletState(deploy_id, deploy_name, countdown, deploy_desc)
            amulet_msg = get_locale_text("i18n_cards_warrior_wizard.wizard.meteor_strike.amulet_deployed", grid=grid, deploy_name=deploy_name)
        else:
            amulet_msg = get_locale_text("i18n_cards_warrior_wizard.wizard.meteor_strike.amulet_fail")
        if not hits:
            return get_locale_text("i18n_cards_warrior_wizard.wizard.meteor_strike.silent", amulet_msg=amulet_msg)
        hits_summary = ", ".join(hits)
        return get_locale_text("i18n_cards_warrior_wizard.wizard.meteor_strike.result", hits_summary=hits_summary, hits_len=len(hits), amulet_msg=amulet_msg)
