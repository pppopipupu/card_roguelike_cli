from typing import Optional
from ...data.potion_data import POTION_CONFIG, get_potion_name
from ...models.state import GameRun

class PotionResolver:
    def __init__(self, engine):
        self.engine = engine

    def use_potion(self, run: GameRun, potion_id: str, target: str, is_throw: bool) -> str:
        p = run.player
        name = get_potion_name(potion_id)
        resolver = self.engine.battle_engine.combat_resolver
        ally_info = resolver.resolve_ally(run, target)
        target_name = resolver.get_target_name(run, target)
        
        if is_throw:
            self.engine.battle_engine._log_event(run, f"💥 {target_name}被你投掷的【{name}】击中了！")
            self.engine.battle_engine.combat_resolver.damage_target(run, target, 3, source="p0", damage_type="bludgeoning")
            
        if potion_id == "healing_potion":
            self.engine.battle_engine.combat_resolver.heal_target(run, target, 10)
            return f"🧪 使用了【{name}】，对【{target_name}】回复了 10 点生命值。"
            
        elif potion_id == "shield_potion":
            self.engine.battle_engine.combat_resolver.gain_shield(run, target, 25)
            return f"🧪 使用了【{name}】，对【{target_name}】施加了 25 点护盾。"
            
        elif potion_id == "fire_potion":
            if not is_throw:
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", 12, source="potion:fire_potion", damage_type="fire")
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "burning", "燃烧", "每回合开始时受到火焰伤害", 2)
                return f"🧪 你喝下了【{name}】，内脏灼伤，受到了 12 点火焰伤害并被施加 2 层【燃烧】。"
            else:
                self.engine.battle_engine.combat_resolver.damage_target(run, target, 16, source="potion:fire_potion", damage_type="fire")
                if target.startswith("p") and target != "p0":
                    grid = target[1:]
                    if grid in p.minions:
                        self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "burning", "燃烧", "每回合开始时受到火焰伤害", 2)
                elif target.startswith("e"):
                    try:
                        idx = int(target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "burning", "燃烧", "每回合开始时受到火焰伤害", 2)
                    except ValueError:
                        pass
                return f"🧪 投掷了【{name}】，对【{target_name}】造成 16 点火焰伤害并施加 2 层【燃烧】。"
                
        elif potion_id == "frost_potion":
            if not is_throw:
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", 10, source="potion:frost_potion", damage_type="cold")
                return f"🧪 你喝下了【{name}】，身体冻僵，受到了 10 点寒冷伤害。"
            else:
                self.engine.battle_engine.combat_resolver.damage_target(run, target, 20, source="potion:frost_potion", damage_type="cold")
                if target.startswith("p") and target != "p0":
                    grid = target[1:]
                    if grid in p.minions:
                        self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "minor_vulnerable_cold", "轻度寒冷易伤", "受到的寒冷伤害增加 50%", 1)
                elif target.startswith("e"):
                    try:
                        idx = int(target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "minor_vulnerable_cold", "轻度寒冷易伤", "受到的寒冷伤害增加 50%", 1)
                    except ValueError:
                        pass
                return f"🧪 投掷了【{name}】，对【{target_name}】造成 20 点寒冷伤害并施加 1 层【轻度寒冷易伤】。"
                
        elif potion_id == "strength_potion":
            if target == "p0":
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "strength", "力量", "造成的伤害增加", 2)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                resolver.add_buff_to(ally_minion or ally, "strength", "力量", "造成的伤害增加", 2)
            elif target.startswith("p"):
                grid = target[1:]
                if grid in p.minions:
                    self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "strength", "力量", "造成的伤害增加", 2)
            elif target.startswith("e"):
                try:
                    idx = int(target[1:]) - 1
                    if 0 <= idx < len(run.enemies):
                        self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "strength", "力量", "造成的伤害增加", 2)
                except ValueError:
                    pass
            return f"🧪 使用了【{name}】，使【{target_name}】获得了 2 层【力量】。"
            
        elif potion_id == "swift_potion":
            if target == "p0":
                p.actions += 1
                p.bonus_actions += 1
                self.engine.battle_engine.card_player.draw_cards(p, 1, run)
                return f"🧪 喝下了【{name}】，本回合获得 1A 1BA 并抽取 1 张牌。"
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                if ally_minion:
                    ally_minion.actions += 1
                    ally_minion.bonus_actions += 1
                    ally_minion.attack_actions += 1
                    return f"🧪 对【{ally.name}】的随从【{ally_minion.name}】使用了【{name}】，其获得 1A 1BA 1AA。"
                ally.actions += 1
                ally.bonus_actions += 1
                self.engine.battle_engine.card_player.draw_cards(ally, 1, run)
                return f"🧪 对【{ally.name}】使用了【{name}】，其获得 1A 1BA 并抽取 1 张牌。"
            else:
                if target.startswith("p"):
                    grid = target[1:]
                    if grid in p.minions:
                        m = p.minions[grid]
                        m.actions += 1
                        m.bonus_actions += 1
                        m.attack_actions += 1
                        return f"🧪 投掷了【{name}】，使我方随从【{m.name}】获得了 1A 1BA 1AA。"
                return f"🧪 投掷了【{name}】，但对【{target_name}】没有产生明显效果。"
                
        elif potion_id == "poison_potion":
            if not is_throw:
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", 10, source="potion:poison_potion", damage_type="poison")
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "poison", "中毒", "每回合开始时，受到层数点毒素伤害，层数减少 1", 4)
                return f"🧪 你喝下了【{name}】，毒素入骨，受到了 10 点毒素伤害并被施加 4 层【中毒】。"
            else:
                self.engine.battle_engine.combat_resolver.damage_target(run, target, 10, source="potion:poison_potion", damage_type="poison")
                if target.startswith("p") and target != "p0":
                    grid = target[1:]
                    if grid in p.minions:
                        self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "poison", "中毒", "每回合开始时，受到层数点毒素伤害，层数减少 1", 4)
                elif target.startswith("e"):
                    try:
                        idx = int(target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "poison", "中毒", "每回合开始时，受到层数点毒素伤害，层数减少 1", 4)
                    except ValueError:
                        pass
                return f"🧪 投掷了【{name}】，对【{target_name}】造成 10 点毒素伤害并施加 4 层【中毒】。"
                
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
                return f"🧪 喝下了【{name}】，清除了自身所有的负面状态。"
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
                return f"🧪 对【{ally.name}】使用了【{name}】，清除了其所有的负面状态。"
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
                        return f"🧪 对我方随从【{m.name}】投掷了【{name}】，清除了其负面状态。"
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
                            return f"🧪 投掷了【{name}】，驱散了敌人【{e.name}】身上的正面增益状态。"
                    except ValueError:
                        pass
                return f"🧪 投掷了【{name}】，但对【{target_name}】没有产生明显效果。"
                
        elif potion_id == "iron_potion":
            if target == "p0":
                p.max_hp += 5
                p.hp += 5
                self.engine.battle_engine.combat_resolver.gain_shield(run, "p0", 20)
                self.engine.battle_engine.combat_resolver.heal_target(run, "p0", 10)
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "iron_will", "钢铁意志", "最大生命上限增加 10 并回复 10 生命", 1)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                if ally_minion:
                    ally_minion.max_hp += 5
                    ally_minion.hp += 5
                else:
                    ally.max_hp += 5
                    ally.hp += 5
                resolver.gain_shield(run, target, 20)
                resolver.heal_target(run, target, 10)
                resolver.add_buff_to(ally_minion or ally, "iron_will", "钢铁意志", "最大生命上限增加 10 并回复 10 生命", 1)
            elif target.startswith("p"):
                grid = target[1:]
                if grid in p.minions:
                    m = p.minions[grid]
                    m.max_hp += 5
                    m.hp += 5
                    self.engine.battle_engine.combat_resolver.gain_shield(run, target, 20)
                    self.engine.battle_engine.combat_resolver.heal_target(run, target, 10)
                    self.engine.battle_engine.combat_resolver.add_buff_to(m, "iron_will", "钢铁意志", "最大生命上限增加 10 并回复 10 生命", 1)
            elif target.startswith("e"):
                try:
                    idx = int(target[1:]) - 1
                    if 0 <= idx < len(run.enemies):
                        e = run.enemies[idx]
                        e.max_hp += 5
                        e.hp += 5
                        self.engine.battle_engine.combat_resolver.gain_shield(run, target, 20)
                        self.engine.battle_engine.combat_resolver.heal_target(run, target, 10)
                        self.engine.battle_engine.combat_resolver.add_buff_to(e, "iron_will", "钢铁意志", "最大生命上限增加 10 并回复 10 生命", 1)
                except ValueError:
                    pass
            return f"🧪 使用了【{name}】，使【{target_name}】最大生命上限永久 +5，并获得 20 护盾、回复 10 生命与 1 层【钢铁意志】。"
            
        elif potion_id == "energy_potion":
            if target == "p0":
                p.actions += 2
                return f"🧪 喝下了【{name}】，本回合额外获得 2 个动作点 (A)。"
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                if ally_minion:
                    ally_minion.actions += 2
                    ally_minion.attack_actions += 1
                    return f"🧪 对【{ally.name}】的随从【{ally_minion.name}】使用了【{name}】，其获得 2A 1AA。"
                ally.actions += 2
                return f"🧪 对【{ally.name}】使用了【{name}】，其获得 2 个动作点 (A)。"
            else:
                if target.startswith("p"):
                    grid = target[1:]
                    if grid in p.minions:
                        m = p.minions[grid]
                        m.actions += 2
                        m.attack_actions += 1
                        return f"🧪 投掷了【{name}】，使我方随从【{m.name}】获得了 2A 1AA。"
                return f"🧪 投掷了【{name}】，但对【{target_name}】没有产生明显效果。"
                
        elif potion_id == "fury_potion":
            if target == "p0":
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "strength", "力量", "造成的伤害增加", 3)
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", 5, source="potion:fury_potion", damage_type="true")
                self.engine.battle_engine.card_player.draw_cards(p, 3, run)
                return f"🧪 喝下了【{name}】，损失 5 生命，获得了 3 层【力量】并抽 3 张牌。"
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                resolver.add_buff_to(ally_minion or ally, "strength", "力量", "造成的伤害增加", 3)
                self.engine.battle_engine.card_player.draw_cards(p, 3, run)
                return f"🧪 对【{ally.name}】使用了【{name}】，其获得 3 层【力量】，你额外抽取了 3 张牌。"
            else:
                if target.startswith("p"):
                    grid = target[1:]
                    if grid in p.minions:
                        self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "strength", "力量", "造成的伤害增加", 3)
                elif target.startswith("e"):
                    try:
                        idx = int(target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "strength", "力量", "造成的伤害增加", 3)
                    except ValueError:
                        pass
                self.engine.battle_engine.card_player.draw_cards(p, 3, run)
                return f"🧪 投掷了【{name}】，使【{target_name}】获得 3 层【力量】，你额外抽取了 3 张牌。"
                
        elif potion_id == "intellect_potion":
            if target == "p0":
                self.engine.battle_engine.combat_resolver.add_buff_to(p, "arcane_charge", "奥术充能", "法术伤害 +3", 2)
            elif ally_info:
                ally = ally_info[1]
                ally_minion = ally.minions.get(ally_info[2]) if ally_info[2] else None
                resolver.add_buff_to(ally_minion or ally, "arcane_charge", "奥术充能", "法术伤害 +3", 2)
            elif target.startswith("p"):
                grid = target[1:]
                if grid in p.minions:
                    self.engine.battle_engine.combat_resolver.add_buff_to(p.minions[grid], "arcane_charge", "奥术充能", "法术伤害 +3", 2)
            elif target.startswith("e"):
                try:
                    idx = int(target[1:]) - 1
                    if 0 <= idx < len(run.enemies):
                        self.engine.battle_engine.combat_resolver.add_buff_to(run.enemies[idx], "arcane_charge", "奥术充能", "法术伤害 +3", 2)
                except ValueError:
                    pass
            self.engine.battle_engine.card_player.draw_cards(p, 4, run)
            return f"🧪 使用了【{name}】，使【{target_name}】获得 2 层【奥术充能】，你额外抽取了 4 张牌。"
            
        elif potion_id == "destruction_potion":
            if not is_throw:
                self.engine.battle_engine.combat_resolver.damage_target(run, "p0", 30, source="potion:destruction_potion", damage_type="force")
                return f"🧪 你喝下了【{name}】，体内狂暴能量爆发，受到了 30 点力场伤害！"
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
                
                self.engine.battle_engine.combat_resolver.damage_target(run, target, 60, source="potion:destruction_potion", damage_type="force")
                
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
                            self.engine.battle_engine.combat_resolver.damage_target(run, f"e{curr_idx}", 20, source="potion:destruction_potion", damage_type="force")
                    return f"🧪 投掷了【{name}】，对【{target_name}】造成了 60 点力场伤害并成功将其消灭，毁灭能量发生爆裂溅射，对其他所有敌人造成了 20 点力场伤害！"
                else:
                    return f"🧪 投掷了【{name}】，对【{target_name}】造成了 60 点力场伤害。"
                    
        return f"🧪 使用了未知药水：{potion_id}。"
