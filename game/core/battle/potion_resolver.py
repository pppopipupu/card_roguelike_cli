from typing import Optional
from ...data.potion_data import POTION_CONFIG, POTION_THROW_DAMAGE, get_potion_name
from ...models.state import GameRun
from ...data.locale_data import get_locale_text

class PotionResolver:
    def __init__(self, engine):
        self.engine = engine

    def use_potion(self, run: GameRun, potion_id: str, target: str, is_throw: bool) -> str:
        p = run.player
        name = get_potion_name(potion_id)
        resolver = self.engine.battle_engine.combat_resolver
        ally_info = resolver.resolve_ally(run, target)
        target_name = resolver.get_target_name(run, target)
        potion_cfg = POTION_CONFIG.get(potion_id, {})
        
        if is_throw:
            self.engine.battle_engine._log_event(run, get_locale_text("i18n_battle_core.throw_hit_log", target_name=target_name, name=name))
            self.engine.battle_engine.combat_resolver.damage_target(run, target, POTION_THROW_DAMAGE, source="p0", damage_type="bludgeoning")
            
        if potion_id == "healing_potion":
            heal = potion_cfg["heal_amount"]
            self.engine.battle_engine.combat_resolver.heal_target(run, target, heal)
            return get_locale_text("i18n_battle_core.healing_potion_log", name=name, target_name=target_name, heal=heal)
            
        elif potion_id == "shield_potion":
            shield = potion_cfg["shield_amount"]
            self.engine.battle_engine.combat_resolver.gain_shield(run, target, shield)
            return get_locale_text("i18n_battle_core.shield_potion_log", name=name, target_name=target_name, shield=shield)
            
        elif potion_id == "fire_potion":
            if not is_throw:
                damage = potion_cfg["drink_damage"]
                stacks = potion_cfg["drink_buff_stacks"]
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", damage, source="potion:fire_potion", damage_type="fire")
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "burning", get_locale_text("i18n_battle_core.buff_burning_name"), get_locale_text("i18n_battle_core.buff_burning_desc"), stacks)
                return get_locale_text("i18n_battle_core.fire_potion_drink_log", name=name, damage=damage, stacks=stacks)
            else:
                damage = potion_cfg["throw_damage"]
                stacks = potion_cfg["throw_buff_stacks"]
                self.engine.battle_engine.combat_resolver.damage_target(run, target, damage, source="potion:fire_potion", damage_type="fire")
                if target.startswith("p") and target != "p0":
                    grid = target[1:]
                    if grid in p.minions:
                        self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "burning", get_locale_text("i18n_battle_core.buff_burning_name"), get_locale_text("i18n_battle_core.buff_burning_desc"), stacks)
                elif target.startswith("e"):
                    try:
                        idx = int(target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "burning", get_locale_text("i18n_battle_core.buff_burning_name"), get_locale_text("i18n_battle_core.buff_burning_desc"), stacks)
                    except ValueError:
                        pass
                return get_locale_text("i18n_battle_core.fire_potion_throw_log", name=name, target_name=target_name, damage=damage, stacks=stacks)
                
        elif potion_id == "frost_potion":
            if not is_throw:
                damage = potion_cfg["drink_damage"]
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", damage, source="potion:frost_potion", damage_type="cold")
                return get_locale_text("i18n_battle_core.frost_potion_drink_log", name=name, damage=damage)
            else:
                damage = potion_cfg["throw_damage"]
                stacks = potion_cfg["throw_buff_stacks"]
                self.engine.battle_engine.combat_resolver.damage_target(run, target, damage, source="potion:frost_potion", damage_type="cold")
                if target.startswith("p") and target != "p0":
                    grid = target[1:]
                    if grid in p.minions:
                        self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "minor_vulnerable_cold", get_locale_text("i18n_battle_core.buff_minor_vulnerable_cold_name"), get_locale_text("i18n_battle_core.buff_minor_vulnerable_cold_desc"), stacks)
                elif target.startswith("e"):
                    try:
                        idx = int(target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "minor_vulnerable_cold", get_locale_text("i18n_battle_core.buff_minor_vulnerable_cold_name"), get_locale_text("i18n_battle_core.buff_minor_vulnerable_cold_desc"), stacks)
                    except ValueError:
                        pass
                return get_locale_text("i18n_battle_core.frost_potion_throw_log", name=name, target_name=target_name, damage=damage, stacks=stacks)
                
        elif potion_id == "strength_potion":
            stacks = potion_cfg["buff_stacks"]
            if target == "p0":
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), stacks)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                resolver.add_buff_to(ally_minion or ally, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), stacks)
            elif target.startswith("p"):
                grid = target[1:]
                if grid in p.minions:
                    self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), stacks)
            elif target.startswith("e"):
                try:
                    idx = int(target[1:]) - 1
                    if 0 <= idx < len(run.enemies):
                        self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), stacks)
                except ValueError:
                    pass
            return get_locale_text("i18n_battle_core.strength_potion_log", name=name, target_name=target_name, stacks=stacks)
            
        elif potion_id == "swift_potion":
            gain_a = potion_cfg["gain_a"]
            gain_ba = potion_cfg["gain_ba"]
            draw_count = potion_cfg["draw_count"]
            if target == "p0":
                p.actions += gain_a
                p.bonus_actions += gain_ba
                self.engine.battle_engine.card_player.draw_cards(p, draw_count, run)
                return get_locale_text("i18n_battle_core.swift_potion_self_log", name=name, gain_a=gain_a, gain_ba=gain_ba, draw_count=draw_count)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                if ally_minion:
                    ally_minion.actions += potion_cfg["minion_gain_a"]
                    ally_minion.bonus_actions += potion_cfg["minion_gain_ba"]
                    ally_minion.attack_actions += potion_cfg["minion_gain_aa"]
                    return get_locale_text("i18n_battle_core.swift_potion_ally_minion_log", ally=ally.name, minion=ally_minion.name, name=name, gain_a=potion_cfg['minion_gain_a'], gain_ba=potion_cfg['minion_gain_ba'], gain_aa=potion_cfg['minion_gain_aa'])
                ally.actions += gain_a
                ally.bonus_actions += gain_ba
                self.engine.battle_engine.card_player.draw_cards(ally, draw_count, run)
                return get_locale_text("i18n_battle_core.swift_potion_ally_log", ally=ally.name, name=name, gain_a=gain_a, gain_ba=gain_ba, draw_count=draw_count)
            else:
                if target.startswith("p"):
                    grid = target[1:]
                    if grid in p.minions:
                        m = p.minions[grid]
                        m.actions += potion_cfg["minion_gain_a"]
                        m.bonus_actions += potion_cfg["minion_gain_ba"]
                        m.attack_actions += potion_cfg["minion_gain_aa"]
                        return get_locale_text("i18n_battle_core.swift_potion_minion_log", name=name, minion=m.name, gain_a=potion_cfg['minion_gain_a'], gain_ba=potion_cfg['minion_gain_ba'], gain_aa=potion_cfg['minion_gain_aa'])
                return get_locale_text("i18n_battle_core.potion_no_effect", name=name, target_name=target_name)
                
        elif potion_id == "poison_potion":
            if not is_throw:
                damage = potion_cfg["drink_damage"]
                stacks = potion_cfg["drink_buff_stacks"]
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", damage, source="potion:poison_potion", damage_type="poison")
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "poison", get_locale_text("i18n_battle_core.buff_poison_name"), get_locale_text("i18n_battle_core.buff_poison_desc"), stacks)
                return get_locale_text("i18n_battle_core.poison_potion_drink_log", name=name, damage=damage, stacks=stacks)
            else:
                damage = potion_cfg["throw_damage"]
                stacks = potion_cfg["throw_buff_stacks"]
                self.engine.battle_engine.combat_resolver.damage_target(run, target, damage, source="potion:poison_potion", damage_type="poison")
                if target.startswith("p") and target != "p0":
                    grid = target[1:]
                    if grid in p.minions:
                        self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "poison", get_locale_text("i18n_battle_core.buff_poison_name"), get_locale_text("i18n_battle_core.buff_poison_desc"), stacks)
                elif target.startswith("e"):
                    try:
                        idx = int(target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "poison", get_locale_text("i18n_battle_core.buff_poison_name"), get_locale_text("i18n_battle_core.buff_poison_desc"), stacks)
                    except ValueError:
                        pass
                return get_locale_text("i18n_battle_core.poison_potion_throw_log", name=name, target_name=target_name, damage=damage, stacks=stacks)
                
        elif potion_id == "cleanse_potion":
            from ...data.buff_data import BUFF_CONFIG
            if target == "p0":
                to_remove = []
                for b in p.buffs:
                    cfg = BUFF_CONFIG.get(b.id, {})
                    if cfg.get("is_debuff") or b.id in ("bleed", "tactical_focus", "beat_of_death", "void_exhaustion", "mana_leak", "minor_vulnerable", "vulnerable", "weak", "grappled", "discard_next_turn", "drain_ba", "drain_a", "forge_backfire", "void_weakness"):
                        to_remove.append(b)
                for b in to_remove:
                    p.buffs.remove(b)
                return get_locale_text("i18n_battle_core.cleanse_potion_self_log", name=name)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                target_entity = ally_minion or ally
                to_remove = []
                for b in target_entity.buffs:
                    cfg = BUFF_CONFIG.get(b.id, {})
                    if cfg.get("is_debuff") or b.id in ("bleed", "tactical_focus", "beat_of_death", "void_exhaustion", "mana_leak", "minor_vulnerable", "vulnerable", "weak", "grappled", "discard_next_turn", "drain_ba", "drain_a", "forge_backfire", "void_weakness"):
                        to_remove.append(b)
                for b in to_remove:
                    target_entity.buffs.remove(b)
                return get_locale_text("i18n_battle_core.cleanse_potion_ally_log", ally=ally.name, name=name)
            else:
                if target.startswith("p"):
                    grid = target[1:]
                    if grid in p.minions:
                        m = p.minions[grid]
                        to_remove = []
                        for b in m.buffs:
                            cfg = BUFF_CONFIG.get(b.id, {})
                            if cfg.get("is_debuff") or b.id in ("bleed", "tactical_focus", "beat_of_death", "void_exhaustion", "mana_leak", "minor_vulnerable", "vulnerable", "weak", "grappled", "discard_next_turn", "drain_ba", "drain_a", "forge_backfire", "void_weakness"):
                                to_remove.append(b)
                        for b in to_remove:
                            m.buffs.remove(b)
                        return get_locale_text("i18n_battle_core.cleanse_potion_minion_log", name=name, minion=m.name)
                elif target.startswith("e"):
                    try:
                        idx = int(target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            e = run.enemies[idx]
                            to_remove = []
                            for b in e.buffs:
                                cfg = BUFF_CONFIG.get(b.id, {})
                                is_deb = cfg.get("is_debuff", False)
                                if not is_deb and b.id not in ("stun", "weak", "electrified", "poison", "agony", "bleed", "void_weakness") and "vulnerable" not in b.id:
                                    to_remove.append(b)
                            for b in to_remove:
                                e.buffs.remove(b)
                            return get_locale_text("i18n_battle_core.cleanse_potion_enemy_log", name=name, enemy=e.name)
                    except ValueError:
                        pass
                return get_locale_text("i18n_battle_core.potion_no_effect", name=name, target_name=target_name)
                
        elif potion_id == "iron_potion":
            max_hp_gain = potion_cfg["max_hp_gain"]
            shield = potion_cfg["shield_amount"]
            heal = potion_cfg["heal_amount"]
            stacks = potion_cfg["buff_stacks"]
            if target == "p0":
                p.max_hp += max_hp_gain
                p.hp += max_hp_gain
                self.engine.battle_engine.combat_resolver.gain_shield(run, "p0", shield)
                self.engine.battle_engine.combat_resolver.heal_target(run, "p0", heal)
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "iron_will", get_locale_text("i18n_battle_core.buff_iron_will_name"), get_locale_text("i18n_battle_core.buff_iron_will_desc"), stacks)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                if ally_minion:
                    ally_minion.max_hp += max_hp_gain
                    ally_minion.hp += max_hp_gain
                else:
                    ally.max_hp += max_hp_gain
                    ally.hp += max_hp_gain
                resolver.gain_shield(run, target, shield)
                resolver.heal_target(run, target, heal)
                resolver.add_buff_to(ally_minion or ally, "iron_will", get_locale_text("i18n_battle_core.buff_iron_will_name"), get_locale_text("i18n_battle_core.buff_iron_will_desc"), stacks)
            elif target.startswith("p"):
                grid = target[1:]
                if grid in p.minions:
                    m = p.minions[grid]
                    m.max_hp += max_hp_gain
                    m.hp += max_hp_gain
                    self.engine.battle_engine.combat_resolver.gain_shield(run, target, shield)
                    self.engine.battle_engine.combat_resolver.heal_target(run, target, heal)
                    self.engine.battle_engine.combat_resolver.add_buff_to(m, "iron_will", get_locale_text("i18n_battle_core.buff_iron_will_name"), get_locale_text("i18n_battle_core.buff_iron_will_desc"), stacks)
            elif target.startswith("e"):
                try:
                    idx = int(target[1:]) - 1
                    if 0 <= idx < len(run.enemies):
                        e = run.enemies[idx]
                        e.max_hp += max_hp_gain
                        e.hp += max_hp_gain
                        self.engine.battle_engine.combat_resolver.gain_shield(run, target, shield)
                        self.engine.battle_engine.combat_resolver.heal_target(run, target, heal)
                        self.engine.battle_engine.combat_resolver.add_buff_to(e, "iron_will", get_locale_text("i18n_battle_core.buff_iron_will_name"), get_locale_text("i18n_battle_core.buff_iron_will_desc"), stacks)
                except ValueError:
                    pass
            return get_locale_text("i18n_battle_core.iron_potion_log", name=name, target_name=target_name, max_hp_gain=max_hp_gain, shield=shield, heal=heal, stacks=stacks)
            
        elif potion_id == "energy_potion":
            gain_a = potion_cfg["gain_a"]
            if target == "p0":
                p.actions += gain_a
                return get_locale_text("i18n_battle_core.energy_potion_self_log", name=name, gain_a=gain_a)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                if ally_minion:
                    ally_minion.actions += potion_cfg["minion_gain_a"]
                    ally_minion.attack_actions += potion_cfg["minion_gain_aa"]
                    return get_locale_text("i18n_battle_core.energy_potion_ally_minion_log", ally=ally.name, minion=ally_minion.name, name=name, gain_a=potion_cfg['minion_gain_a'], gain_aa=potion_cfg['minion_gain_aa'])
                ally.actions += gain_a
                return get_locale_text("i18n_battle_core.energy_potion_ally_log", ally=ally.name, name=name, gain_a=gain_a)
            else:
                if target.startswith("p"):
                    grid = target[1:]
                    if grid in p.minions:
                        m = p.minions[grid]
                        m.actions += potion_cfg["minion_gain_a"]
                        m.attack_actions += potion_cfg["minion_gain_aa"]
                        return get_locale_text("i18n_battle_core.energy_potion_minion_log", name=name, minion=m.name, gain_a=potion_cfg['minion_gain_a'], gain_aa=potion_cfg['minion_gain_aa'])
                return get_locale_text("i18n_battle_core.potion_no_effect", name=name, target_name=target_name)
                
        elif potion_id == "fury_potion":
            stacks = potion_cfg["buff_stacks"]
            self_hp_cost = potion_cfg["self_hp_cost"]
            draw_count = potion_cfg["draw_count"]
            if target == "p0":
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), stacks)
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", self_hp_cost, source="potion:fury_potion", damage_type="true")
                self.engine.battle_engine.card_player.draw_cards(p, draw_count, run)
                return get_locale_text("i18n_battle_core.fury_potion_self_log", name=name, cost=self_hp_cost, stacks=stacks, draw_count=draw_count)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                resolver.add_buff_to(ally_minion or ally, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), stacks)
                self.engine.battle_engine.card_player.draw_cards(p, draw_count, run)
                return get_locale_text("i18n_battle_core.fury_potion_ally_log", ally=ally.name, name=name, stacks=stacks, draw_count=draw_count)
            else:
                if target.startswith("p"):
                    grid = target[1:]
                    if grid in p.minions:
                        self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), stacks)
                elif target.startswith("e"):
                    try:
                        idx = int(target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), stacks)
                    except ValueError:
                        pass
                self.engine.battle_engine.card_player.draw_cards(p, draw_count, run)
                return get_locale_text("i18n_battle_core.fury_potion_throw_log", name=name, target_name=target_name, stacks=stacks, draw_count=draw_count)
                
        elif potion_id == "intellect_potion":
            stacks = potion_cfg["buff_stacks"]
            draw_count = potion_cfg["draw_count"]
            if target == "p0":
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "arcane_charge", get_locale_text("i18n_battle_core.buff_arcane_charge_name"), get_locale_text("i18n_battle_core.buff_arcane_charge_desc"), stacks)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                resolver.add_buff_to(ally_minion or ally, "arcane_charge", get_locale_text("i18n_battle_core.buff_arcane_charge_name"), get_locale_text("i18n_battle_core.buff_arcane_charge_desc"), stacks)
            elif target.startswith("p"):
                grid = target[1:]
                if grid in p.minions:
                    self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "arcane_charge", get_locale_text("i18n_battle_core.buff_arcane_charge_name"), get_locale_text("i18n_battle_core.buff_arcane_charge_desc"), stacks)
            elif target.startswith("e"):
                try:
                    idx = int(target[1:]) - 1
                    if 0 <= idx < len(run.enemies):
                        self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "arcane_charge", get_locale_text("i18n_battle_core.buff_arcane_charge_name"), get_locale_text("i18n_battle_core.buff_arcane_charge_desc"), stacks)
                except ValueError:
                    pass
            self.engine.battle_engine.card_player.draw_cards(p, draw_count, run)
            return get_locale_text("i18n_battle_core.intellect_potion_log", name=name, target_name=target_name, stacks=stacks, draw_count=draw_count)
            
        elif potion_id == "destruction_potion":
            if not is_throw:
                damage = potion_cfg["drink_damage"]
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", damage, source="potion:destruction_potion", damage_type="force")
                return get_locale_text("i18n_battle_core.destruction_potion_drink_log", name=name, damage=damage)
            else:
                target_enemy = None
                enemy_idx = -1
                if target.startswith("e"):
                    try:
                        enemy_idx = int(target[1:]) - 1
                        if 0 <= enemy_idx < len(run.enemies):
                            target_enemy = run.enemies[enemy_idx]
                    except ValueError:
                        pass
                
                other_enemies = [e for e in run.enemies if e != target_enemy and e.hp > 0]
                
                damage = potion_cfg["throw_damage"]
                self.engine.battle_engine.combat_resolver.damage_target(run, target, damage, source="potion:destruction_potion", damage_type="force")
                
                is_dead = False
                if target_enemy:
                    if target_enemy not in run.enemies or target_enemy.hp <= 0:
                        is_dead = True
                else:
                    if target.startswith("p") and target != "p0":
                        grid = target[1:]
                        if grid not in p.minions or p.minions[grid].hp <= 0:
                            is_dead = True
                            
                if is_dead and target.startswith("e"):
                    for e in other_enemies:
                        if e in run.enemies:
                            curr_idx = run.enemies.index(e) + 1
                            self.engine.battle_engine.combat_resolver.damage_target(run, f"e{curr_idx}", potion_cfg["splash_damage"], source="potion:destruction_potion", damage_type="force")
                    return get_locale_text("i18n_battle_core.destruction_potion_splash_log", name=name, target_name=target_name, damage=damage, splash_damage=potion_cfg['splash_damage'])
                else:
                    return get_locale_text("i18n_battle_core.destruction_potion_throw_log", name=name, target_name=target_name, damage=damage)
                    
        return get_locale_text("i18n_battle_core.unknown_potion_log", potion_id=potion_id)
