from typing import Optional, List
from ...data.minion_data import MINION_CONFIG

class BaseMinionSkill:
    def __init__(self, name: str, cost_a: int, cost_ba: int, desc: str):
        self.name = name
        self.cost_a = cost_a
        self.cost_ba = cost_ba
        self.desc = desc

    def execute(self, run, my_grid: str, target: Optional[str], engine) -> str:
        return ""

class MercenaryHeavyStrike(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        damage = cfg["damage"]
        tname = engine._get_target_name(run, target)
        engine._damage_target(run, target, damage)
        return cfg["feedback"].format(target=tname, damage=damage)

class MercenaryBattlecry(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        atk_buff = cfg["atk_buff"]
        m.atk += atk_buff
        return cfg["feedback"].format(atk_buff=atk_buff)

class ShieldGuardDefend(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        shield = cfg["shield"]
        run.player.shield += shield
        return cfg["feedback"].format(shield=shield)

class ShieldGuardBash(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        damage = cfg["damage"]
        shield = cfg["shield"]
        tname = engine._get_target_name(run, target)
        engine._damage_target(run, target, damage)
        run.player.shield += shield
        return cfg["feedback"].format(target=tname, damage=damage, shield=shield)

class FamiliarAssist(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        draw = cfg["draw"]
        engine._draw_cards(run.player, draw, run)
        return cfg["feedback"].format(draw=draw)

class FamiliarCharge(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        ba_gain = cfg["ba_gain"]
        run.player.bonus_actions += ba_gain
        return cfg["feedback"].format(ba_gain=ba_gain)

class WaterTouch(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        t = target or "e1"
        if run.node_type == "duel":
            if t == "e1" or t == "e":
                enemy = run.player2
            elif t.startswith("e") and len(t) > 1:
                try:
                    grid_idx = str(int(t[1:]) - 1)
                    enemy = run.player2.minions.get(grid_idx)
                except ValueError:
                    enemy = None
            else:
                enemy = None
        else:
            enemy = None
            if t.startswith("e"):
                try:
                    grid_idx = int(t[1:]) - 1
                except ValueError:
                    grid_idx = 0
                if 0 <= grid_idx < len(run.enemies):
                    enemy = run.enemies[grid_idx]
        if enemy:
            enemy.bonus_actions = max(0, enemy.bonus_actions - 1)
            tname = engine._get_target_name(run, t)
            return cfg["feedback"].format(target=tname)
        return "未找到敌方目标。"

class WaterLance(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        damage = cfg["damage"]
        t = target or "e1"
        tname = engine._get_target_name(run, t)
        engine._damage_target(run, t, damage)
        if run.node_type == "duel":
            if t == "e1" or t == "e":
                enemy = run.player2
            elif t.startswith("e") and len(t) > 1:
                try:
                    grid_idx = str(int(t[1:]) - 1)
                    enemy = run.player2.minions.get(grid_idx)
                except ValueError:
                    enemy = None
            else:
                enemy = None
        else:
            enemy = None
            if t.startswith("e"):
                try:
                    grid_idx = int(t[1:]) - 1
                except ValueError:
                    grid_idx = 0
                if 0 <= grid_idx < len(run.enemies):
                    enemy = run.enemies[grid_idx]
        if enemy:
            enemy.actions = max(0, enemy.actions - 1)
            if cfg.get("stun"):
                engine._add_buff_to(enemy, "stun", "眩晕", "下一回合无法行动", cfg["stun"])
            feedback_boss = cfg.get("feedback_boss")
            if feedback_boss and (t == "e1" or t == "e" or run.node_type == "duel"):
                return feedback_boss.format(target=tname, damage=damage)
            return cfg["feedback"].format(target=tname, damage=damage)
        return "未找到敌方目标。"

class GolemOverload(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        self_damage = cfg["self_damage"]
        atk_buff = cfg["atk_buff"]
        m.hp -= self_damage
        m.atk += atk_buff
        if m.hp <= 0:
            del run.player.minions[my_grid]
            return cfg["feedback_dead"].format(self_damage=self_damage, atk_buff=atk_buff)
        return cfg["feedback"].format(self_damage=self_damage, atk_buff=atk_buff)

class GolemRepair(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        heal = cfg["heal"]
        m.hp = min(m.max_hp, m.hp + heal)
        return cfg["feedback"].format(heal=heal, hp=m.hp, max_hp=m.max_hp)

class IcerainbowwSpray(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        damage = cfg["damage"]
        layers = cfg.get("vulnerable_layers", 1)
        for idx, enemy in enumerate(list(run.enemies)):
            engine._damage_target(run, f"e{idx+1}", damage, source=f"minion:{m.name}", damage_type="cold")
            engine._add_buff_to(enemy, "minor_vulnerable_cold", "轻度寒冷易伤", "受到的寒冷伤害增加 50%", layers)
        return cfg["feedback"] + f"（对所有敌人造成 {damage} 点寒冷伤害并附加 {layers} 层轻度寒冷易伤）"

class IcerainbowwShield(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        p_shield = cfg.get("player_shield", 12)
        m_heal = cfg.get("minion_heal", 4)
        run.player.shield += p_shield
        for mk, mv in list(run.player.minions.items()):
            mv.hp = min(mv.max_hp, mv.hp + m_heal)
        return cfg["feedback"] + f"（为玩家提供 {p_shield} 点护盾，并为我方所有随从恢复 {m_heal} 点生命）"

class GateGuardStrike(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        damage = cfg["damage"]
        t = target or "e1"
        tname = engine._get_target_name(run, t)
        engine._damage_target(run, t, damage)
        if t.startswith("e"):
            try:
                grid_idx = int(t[1:]) - 1
            except ValueError:
                grid_idx = 0
            if 0 <= grid_idx < len(run.enemies):
                enemy = run.enemies[grid_idx]
                enemy.actions = max(0, enemy.actions - 1)
        return cfg["feedback"].format(target=tname, damage=damage)


class BannerBearerBuff(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        is_upgraded = m.id.endswith("+")
        eligible = [mk for mk, mv in run.player.minions.items() if mk != my_grid]
        if not eligible:
            return "没有其他我方随从可以激励。"
        import random
        chosen_grid = random.choice(eligible)
        chosen_minion = run.player.minions[chosen_grid]
        val = 3 if is_upgraded else 2
        chosen_minion.atk += val
        shield_msg = ""
        if is_upgraded:
            m.hp = min(m.max_hp, m.hp + 3)
            shield_msg = "，并恢复自身 3 点生命值"
        return f"成功激励了【{chosen_minion.name}】使其攻击力本回合提升 {val} 点{shield_msg}。"


class PatrolCaptainOrder(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        is_upgraded = m.id.endswith("+")
        heal_val = 5 if is_upgraded else 3
        shield_val = 5 if is_upgraded else 3
        for mk, mv in run.player.minions.items():
            mv.hp = min(mv.max_hp, mv.hp + heal_val)
        engine._gain_shield(run, "p0", shield_val)
        return f"为我方所有随从恢复了 {heal_val} 点生命，并为玩家提供了 {shield_val} 点护盾。"


class GarrisonLeaderWall(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        is_upgraded = m.id.endswith("+")
        shield_val = 9 if is_upgraded else 6
        heal_val = 5 if is_upgraded else 3
        engine._gain_shield(run, "p0", shield_val)
        for mk, mv in run.player.minions.items():
            if mv.id.startswith("officer_") or mv.id.startswith("commander_"):
                mv.hp = min(mv.max_hp, mv.hp + heal_val)
        return f"为玩家提供了 {shield_val} 点护盾，并使我方全体士兵随从恢复了 {heal_val} 点生命。"


class ValiantHeraldSignal(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        is_upgraded = m.id.endswith("+")
        val = 3 if is_upgraded else 2
        for mk, mv in run.player.minions.items():
            mv.atk += val
        return f"吹响了冲锋信号，我方所有在场随从本回合攻击力提升了 {val} 点！"


class SteelcladTacticianStrike(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        is_upgraded = m.id.endswith("+")
        dmg = 9 if is_upgraded else 6
        t = target or "e1"
        tname = engine._get_target_name(run, t)
        enemy_to_attack = None
        if t.startswith("e"):
            try:
                idx = int(t[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    enemy_to_attack = run.enemies[idx]
            except ValueError:
                pass
        engine._damage_target(run, t, dmg, damage_type="bludgeoning", source=f"p{my_grid}")
        is_kill = False
        if enemy_to_attack and enemy_to_attack.hp <= 0:
            is_kill = True
        tok_msg = ""
        if is_kill:
            tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
            tok_name = "步兵轻卒+" if is_upgraded else "步兵轻卒"
            summon_count = 0
            for _ in range(2):
                tok_grid = engine._summon_minion(run, tok_id, tok_name, 4 if is_upgraded else 3, 2 if is_upgraded else 1, 0)
                if tok_grid:
                    summon_count += 1
                    tm = run.player.minions[tok_grid]
                    engine._add_buff_to(tm, "ward", "守护", "敌方单体攻击只能指向该随从")
            if summon_count > 0:
                tok_msg = f"\n📢 [战术压制] 成功斩杀目标！在战场上召唤了 {summon_count} 个具有守护的【{tok_name}】！"
        return f"执行战术压制，对【{tname}】造成了 {dmg} 点钝击伤害。{tok_msg}"


class BladeDancerSlash(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        is_upgraded = m.id.endswith("+")
        dmg = 6 if is_upgraded else 4
        t = target or "e1"
        tname = engine._get_target_name(run, t)
        for _ in range(2):
            engine._damage_target(run, t, dmg, damage_type="slashing", source=f"p{my_grid}")
        return f"对【{tname}】连续发动两次双重斩击，造成了 {dmg}*2 点伤害。"


class AuroraEmperorJudgment(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        is_upgraded = m.id.endswith("+")
        rally = run.node_data.get("rally_count", 0)
        if rally >= 15:
            dmg = 22 if is_upgraded else 15
            dtype = "true"
        else:
            dmg = 12 if is_upgraded else 8
            dtype = "radiant"
        for idx in range(len(run.enemies) - 1, -1, -1):
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type=dtype, source=f"p{my_grid}")
        type_name = "真实" if dtype == "true" else "光耀"
        return f"降下极光审判，对所有敌人造成了 {dmg} 点{type_name}伤害。"


class MinionTemplate:
    def __init__(self, id: str, name: str, skills: List[BaseMinionSkill]):
        self.id = id
        self.name = name
        self.skills = skills

    def on_minion_death(self, run, grid, event, engine):
        pass

    def on_card_played(self, run, grid, event, engine):
        pass

    def on_shield_gain(self, run, grid, event, engine):
        pass

    def on_damage_take(self, run, grid, event, engine):
        pass

    def on_card_exhaust(self, run, grid, event, engine):
        pass

    def on_turn_end(self, run, grid, event, engine):
        pass

    def on_damage_calculate(self, run, grid, event, engine):
        pass

    def on_attack(self, run, grid, event, engine):
        pass

    def on_minion_summon(self, run, grid, event, engine):
        pass


class CardsPlayedEntryDamageTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if grid != event.grid:
            return
        if event.minion_state.id != self.id:
            return
        cfg = MINION_CONFIG.get(self.id) or MINION_CONFIG.get(self.id.rstrip("+"), {})
        thresholds = cfg.get("enter_hit_thresholds") or []
        damage = int(cfg.get("enter_damage", 0))
        if not thresholds or damage <= 0:
            return
        count = run.node_data.get("cards_played_this_turn", 0)
        if run.node_data.get("current_playing_card_id"):
            count += 1
        if count < min(thresholds):
            return
        hits = sum(1 for threshold in thresholds if count >= threshold)
        damage_type = cfg.get("enter_damage_type", "effect")
        damage_name = cfg.get("enter_damage_name", "伤害")
        import random
        hit_count = 0
        for _ in range(hits):
            alive = [idx for idx, enemy in enumerate(run.enemies) if enemy.hp > 0]
            if not alive:
                break
            idx = random.choice(alive)
            engine._damage_target(run, f"e{idx+1}", damage, source=f"p{grid}", damage_type=damage_type)
            hit_count += 1
        if hit_count:
            engine._log_event(run, f"✨ 【{self.name}】进入战场时，本回合已打出 {count} 张牌，触发了 {hit_count} 次{damage_name}伤害！")


class ShieldGuardTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            engine._add_buff_to(event.minion_state, "ward", "守护", "敌方单体攻击只能指向该随从")


class GateGuardTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            engine._add_buff_to(event.minion_state, "ward", "守护", "敌方单体攻击指向该随从")


class SoldierTokenTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            engine._add_buff_to(event.minion_state, "ward", "守护", "敌方单体攻击只能指向该随从")


class CommanderPatrolCaptainTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            is_upgraded = event.minion_state.id.endswith("+")
            tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
            tok_name = "步兵轻卒+" if is_upgraded else "步兵轻卒"
            tok_grid = engine._summon_minion(run, tok_id, tok_name, 4 if is_upgraded else 3, 2 if is_upgraded else 1, 0)
            if tok_grid:
                tm = run.player.minions[tok_grid]
                engine._add_buff_to(tm, "ward", "守护", "敌方单体攻击只能指向该随从")
                engine._log_event(run, f"📢 【{event.minion_state.name}】进场触发：在格子 [{tok_grid}] 召唤了具有守护的【{tok_name}】。")


class MercenaryTemplate(MinionTemplate):
    def on_attack(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m:
            is_upgraded = m.id.endswith("+")
            val = 2 if is_upgraded else 1
            m.atk += val
            engine._log_event(run, f"⚔️ 【{m.name}】发起攻击，触发攻击时效果：本回合自身攻击力提升了 {val} 点。")


class RecruitVanguardTemplate(MinionTemplate):
    def on_attack(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m:
            rally = run.node_data.get("rally_count", 0)
            if rally >= 6:
                is_upgraded = m.id.endswith("+")
                val = 4 if is_upgraded else 2
                event.modified_damage += val
                shield_msg = ""
                if is_upgraded:
                    engine._gain_shield(run, "p0", 2)
                    shield_msg = "并获得 2 点护盾"
                engine._log_event(run, f"⚔️ 【{m.name}】发起攻击，协作达到了 {rally}！该次攻击伤害额外增加 {val} 点{shield_msg}。")


class BannerBearerTemplate(MinionTemplate):
    def on_card_played(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m and event.card.id.replace("+", "") in ("warrior_strike", "warrior_bash", "iron_wave", "warrior_anger", "body_slam", "pommel_strike", "heavy_blade", "uppercut", "feed", "bludgeon"):
            is_upgraded = m.id.endswith("+")
            turn_uses = run.node_data.get(f"banner_bearer_use_{grid}", 0)
            if turn_uses < 1:
                eligible = [mk for mk, mv in run.player.minions.items() if mk != grid]
                if eligible:
                    import random
                    chosen_grid = random.choice(eligible)
                    chosen_minion = run.player.minions[chosen_grid]
                    chosen_minion.attack_actions = 1
                    val = 3 if is_upgraded else 2
                    chosen_minion.atk += val
                    run.node_data[f"banner_bearer_use_{grid}"] = turn_uses + 1
                    shield_msg = ""
                    if is_upgraded:
                        engine._gain_shield(run, f"p{grid}", 3)
                        shield_msg = f"，且【{m.name}】获得 3 点护盾"
                    engine._log_event(run, f"🎺 【{m.name}】被动触发！由于打出了挥砍、钝击或穿刺卡牌，使我方随从【{chosen_minion.name}】重置了攻击次数，且攻击力本回合 +{val}{shield_msg}。")


class RoyalGuardTemplate(MinionTemplate):
    def on_shield_gain(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m and event.target == "p0" and event.modified_amount > 0:
            is_upgraded = m.id.endswith("+")
            val = 2 if is_upgraded else 1
            m.atk += val
            dmg = 3 if is_upgraded else 2
            dtype = "true" if is_upgraded else "piercing"
            first_enemy = engine._get_first_alive_enemy(run)
            if first_enemy:
                engine._damage_target(run, first_enemy, dmg, damage_type=dtype, source=f"p{grid}")
                tname = engine._get_target_name(run, first_enemy)
                engine._log_event(run, f"🛡️ 【{m.name}】在场触发被动：玩家获得护盾使自身攻击力永久提升 {val}，且对【{tname}】发起反击。")


class GarrisonLeaderTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            engine._add_buff_to(event.minion_state, "ward", "守护", "敌方单体攻击指向该随从")

    def on_damage_take(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m and event.target == "p0" and event.amount > 0:
            p = run.player
            if p.shield == 0 and "last_shield_before_dmg" in run.node_data and run.node_data["last_shield_before_dmg"] > 0:
                is_upgraded = m.id.endswith("+")
                tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
                tok_name = "步兵轻卒+" if is_upgraded else "步兵轻卒"
                tok_grid = engine._summon_minion(run, tok_id, tok_name, 4 if is_upgraded else 3, 2 if is_upgraded else 1, 0)
                shield_val = 5 if is_upgraded else 3
                engine._gain_shield(run, "p0", shield_val)
                ref_msg = ""
                if is_upgraded:
                    engine._damage_target(run, event.source, event.amount, damage_type="true", source=f"p{grid}")
                    ref_msg = f"，且向【{engine._get_target_name(run, event.source)}】反弹了 {event.amount} 点真实伤害"
                tok_msg = f"\n📢 [要塞卫队长] 在格子 [{tok_grid}] 召唤了【{tok_name}】{ref_msg}！" if tok_grid else ""
                engine._log_event(run, f"🛡️ 【{m.name}】在场被动触发：玩家护盾破碎，玩家获得 {shield_val} 点护盾。{tok_msg}")


class SquadSkirmisherTemplate(MinionTemplate):
    def on_minion_death(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m and event.is_enemy and event.source == f"p{grid}":
            is_upgraded = m.id.endswith("+")
            tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
            tok_name = "步兵轻卒+" if is_upgraded else "步兵轻卒"
            tok_grid = engine._summon_minion(run, tok_id, tok_name, 4 if is_upgraded else 3, 2 if is_upgraded else 1, 0)
            if tok_grid:
                tm = run.player.minions[tok_grid]
                engine._add_buff_to(tm, "ward", "守护", "敌方单体攻击指向该随从")
                if is_upgraded:
                    tm.attack_actions = 2
                    engine._log_event(run, f"⚔️ 【{m.name}】斩杀了【{event.name}】！触发被动：在格子 [{tok_grid}] 召唤了【{tok_name}】（本回合可攻击两次）。")
                else:
                    engine._log_event(run, f"⚔️ 【{m.name}】斩杀了【{event.name}】！触发被动：在格子 [{tok_grid}] 召唤了【{tok_name}】。")

    def on_card_exhaust(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m:
            is_upgraded = m.id.endswith("+")
            val = 3 if is_upgraded else 2
            m.atk += val
            if is_upgraded:
                for enemy in list(run.enemies):
                    engine._add_buff_to(enemy, "minor_vulnerable", "轻度易伤", "受到的所有类型伤害增加 50%", 1)
                engine._log_event(run, f"🧩 【{m.name}】被动触发：由于有卡牌被消耗，自身本回合攻击力 +{val}，且使所有敌人获得 1 层【轻度易伤】。")
            else:
                first_enemy = engine._get_first_alive_enemy(run)
                if first_enemy:
                    try:
                        f_idx = int(first_enemy.replace("e", "")) - 1
                        if 0 <= f_idx < len(run.enemies):
                            engine._add_buff_to(run.enemies[f_idx], "minor_vulnerable", "轻度易伤", "受到的所有类型伤害增加 50%", 1)
                    except ValueError:
                        pass
                    tname = engine._get_target_name(run, first_enemy)
                    engine._log_event(run, f"🧩 【{m.name}】被动触发：由于有卡牌被消耗，自身本回合攻击力 +{val}，且使【{tname}】获得 1 层【轻度易伤】。")


class ValiantHeraldTemplate(MinionTemplate):
    def on_minion_death(self, run, grid, event, engine):
        from ..cards.base import ALL_CARDS
        if event.grid == f"p{grid}" and not event.is_enemy:
            is_upgraded = event.minion_id.endswith("+")
            if is_upgraded:
                eligible = [cid for cid in run.player.hand if ALL_CARDS.get(cid) and ALL_CARDS.get(cid).type == "minion"]
                for cid in eligible:
                    run.node_data.setdefault("free_minion_cards", []).append(cid)
                engine._log_event(run, f"🔔 【英勇传令官+】死亡触发谢幕曲：使手牌中所有的随从牌动作点费用全部降为 0！")
            else:
                eligible = [cid for cid in run.player.hand if ALL_CARDS.get(cid) and ALL_CARDS.get(cid).type == "minion"]
                if eligible:
                    import random
                    chosen = random.choice(eligible)
                    run.node_data.setdefault("free_minion_cards", []).append(chosen)
                    cname = ALL_CARDS.get(chosen).name
                    engine._log_event(run, f"🔔 【英勇传令官】死亡触发谢幕曲：使手牌随从牌【{cname}】本回合费用降为 0！")


class SteelcladTacticianTemplate(MinionTemplate):
    def on_turn_end(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m:
            rally = run.node_data.get("rally_count", 0)
            if rally >= 10:
                is_upgraded = m.id.endswith("+")
                tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
                tok_name = "步兵轻卒+" if is_upgraded else "步兵轻卒"
                tok_grid = engine._summon_minion(run, tok_id, tok_name, 4 if is_upgraded else 3, 2 if is_upgraded else 1, 0)
                coef = 2 if is_upgraded else 1
                shield_val = len(run.player.minions) * coef
                engine._gain_shield(run, "p0", shield_val)
                tok_msg = f"并在格子 [{tok_grid}] 召唤了【{tok_name}】" if tok_grid else "但没有多余格子召唤步兵轻卒"
                engine._log_event(run, f"🛡️ 【{m.name}】在场回合结束触发被动：协作达到了 {rally}！获得了 {shield_val} 点护盾，{tok_msg}。")


class BladeDancerTemplate(MinionTemplate):
    def on_damage_calculate(self, run, grid, event, engine):
        if event.source == f"p{grid}":
            target_enemy = None
            if event.target.startswith("e"):
                try:
                    idx = int(event.target[1:]) - 1
                    if 0 <= idx < len(run.enemies):
                        target_enemy = run.enemies[idx]
                except ValueError:
                    pass
            if target_enemy and target_enemy.shield > 0:
                m = run.player.minions.get(grid)
                is_upgraded = m.id.endswith("+") if m else False
                coef = 2.0 if is_upgraded else 1.5
                event.modified_damage = int(event.modified_damage * coef)
                event.damage_type = "true"
                engine._log_event(run, f"⚔️ 【{m.name if m else '双刃轻卫'}】被动触发：由于目标敌人拥有护盾，本次造成的伤害提升为原有的 {int(coef*100)}% 且全部转化为真实伤害（穿透护盾）！")


class MinionTemplate:
    def __init__(self, id: str, name: str, skills: List[BaseMinionSkill]):
        self.id = id
        self.name = name
        self.skills = skills


ALL_MINIONS = {
    "mercenary": MercenaryTemplate(
        "mercenary",
        MINION_CONFIG["mercenary"]["name"],
        [
            MercenaryHeavyStrike(
                MINION_CONFIG["mercenary"]["skills"][0]["name"],
                MINION_CONFIG["mercenary"]["skills"][0]["cost_a"],
                MINION_CONFIG["mercenary"]["skills"][0]["cost_ba"],
                MINION_CONFIG["mercenary"]["skills"][0]["desc"]
            ),
            MercenaryBattlecry(
                MINION_CONFIG["mercenary"]["skills"][1]["name"],
                MINION_CONFIG["mercenary"]["skills"][1]["cost_a"],
                MINION_CONFIG["mercenary"]["skills"][1]["cost_ba"],
                MINION_CONFIG["mercenary"]["skills"][1]["desc"]
            )
        ]
    ),
    "shield_guard": ShieldGuardTemplate(
        "shield_guard",
        MINION_CONFIG["shield_guard"]["name"],
        [
            ShieldGuardDefend(
                MINION_CONFIG["shield_guard"]["skills"][0]["name"],
                MINION_CONFIG["shield_guard"]["skills"][0]["cost_a"],
                MINION_CONFIG["shield_guard"]["skills"][0]["cost_ba"],
                MINION_CONFIG["shield_guard"]["skills"][0]["desc"]
            ),
            ShieldGuardBash(
                MINION_CONFIG["shield_guard"]["skills"][1]["name"],
                MINION_CONFIG["shield_guard"]["skills"][1]["cost_a"],
                MINION_CONFIG["shield_guard"]["skills"][1]["cost_ba"],
                MINION_CONFIG["shield_guard"]["skills"][1]["desc"]
            )
        ]
    ),
    "find_familiar": MinionTemplate(
        "find_familiar",
        MINION_CONFIG["find_familiar"]["name"],
        [
            FamiliarAssist(
                MINION_CONFIG["find_familiar"]["skills"][0]["name"],
                MINION_CONFIG["find_familiar"]["skills"][0]["cost_a"],
                MINION_CONFIG["find_familiar"]["skills"][0]["cost_ba"],
                MINION_CONFIG["find_familiar"]["skills"][0]["desc"]
            ),
            FamiliarCharge(
                MINION_CONFIG["find_familiar"]["skills"][1]["name"],
                MINION_CONFIG["find_familiar"]["skills"][1]["cost_a"],
                MINION_CONFIG["find_familiar"]["skills"][1]["cost_ba"],
                MINION_CONFIG["find_familiar"]["skills"][1]["desc"]
            )
        ]
    ),
    "water_elemental": MinionTemplate(
        "water_elemental",
        MINION_CONFIG["water_elemental"]["name"],
        [
            WaterTouch(
                MINION_CONFIG["water_elemental"]["skills"][0]["name"],
                MINION_CONFIG["water_elemental"]["skills"][0]["cost_a"],
                MINION_CONFIG["water_elemental"]["skills"][0]["cost_ba"],
                MINION_CONFIG["water_elemental"]["skills"][0]["desc"]
            ),
            WaterLance(
                MINION_CONFIG["water_elemental"]["skills"][1]["name"],
                MINION_CONFIG["water_elemental"]["skills"][1]["cost_a"],
                MINION_CONFIG["water_elemental"]["skills"][1]["cost_ba"],
                MINION_CONFIG["water_elemental"]["skills"][1]["desc"]
            )
        ]
    ),
    "arcane_golem": MinionTemplate(
        "arcane_golem",
        MINION_CONFIG["arcane_golem"]["name"],
        [
            GolemOverload(
                MINION_CONFIG["arcane_golem"]["skills"][0]["name"],
                MINION_CONFIG["arcane_golem"]["skills"][0]["cost_a"],
                MINION_CONFIG["arcane_golem"]["skills"][0]["cost_ba"],
                MINION_CONFIG["arcane_golem"]["skills"][0]["desc"]
            ),
            GolemRepair(
                MINION_CONFIG["arcane_golem"]["skills"][1]["name"],
                MINION_CONFIG["arcane_golem"]["skills"][1]["cost_a"],
                MINION_CONFIG["arcane_golem"]["skills"][1]["cost_ba"],
                MINION_CONFIG["arcane_golem"]["skills"][1]["desc"]
            )
        ]
    ),
    "minion_icerainboww": MinionTemplate(
        "minion_icerainboww",
        MINION_CONFIG["minion_icerainboww"]["name"],
        [
            IcerainbowwSpray(
                MINION_CONFIG["minion_icerainboww"]["skills"][0]["name"],
                MINION_CONFIG["minion_icerainboww"]["skills"][0]["cost_a"],
                MINION_CONFIG["minion_icerainboww"]["skills"][0]["cost_ba"],
                MINION_CONFIG["minion_icerainboww"]["skills"][0]["desc"]
            ),
            IcerainbowwShield(
                MINION_CONFIG["minion_icerainboww"]["skills"][1]["name"],
                MINION_CONFIG["minion_icerainboww"]["skills"][1]["cost_a"],
                MINION_CONFIG["minion_icerainboww"]["skills"][1]["cost_ba"],
                MINION_CONFIG["minion_icerainboww"]["skills"][1]["desc"]
            )
        ]
    ),
    "gate_guard": GateGuardTemplate(
        "gate_guard",
        MINION_CONFIG["gate_guard"]["name"],
        [
            GateGuardStrike(
                MINION_CONFIG["gate_guard"]["skills"][0]["name"],
                MINION_CONFIG["gate_guard"]["skills"][0]["cost_a"],
                MINION_CONFIG["gate_guard"]["skills"][0]["cost_ba"],
                MINION_CONFIG["gate_guard"]["skills"][0]["desc"]
            )
        ]
    ),
    "elf_archer_xiaomei": CardsPlayedEntryDamageTemplate(
        "elf_archer_xiaomei",
        MINION_CONFIG["elf_archer_xiaomei"]["name"],
        []
    ),
    "officer_recruit_vanguard": RecruitVanguardTemplate(
        "officer_recruit_vanguard",
        MINION_CONFIG["officer_recruit_vanguard"]["name"],
        []
    ),
    "officer_banner_bearer": BannerBearerTemplate(
        "officer_banner_bearer",
        MINION_CONFIG["officer_banner_bearer"]["name"],
        [
            BannerBearerBuff(
                MINION_CONFIG["officer_banner_bearer"]["skills"][0]["name"],
                MINION_CONFIG["officer_banner_bearer"]["skills"][0]["cost_a"],
                MINION_CONFIG["officer_banner_bearer"]["skills"][0]["cost_ba"],
                MINION_CONFIG["officer_banner_bearer"]["skills"][0]["desc"]
            )
        ]
    ),
    "commander_patrol_captain": CommanderPatrolCaptainTemplate(
        "commander_patrol_captain",
        MINION_CONFIG["commander_patrol_captain"]["name"],
        [
            PatrolCaptainOrder(
                MINION_CONFIG["commander_patrol_captain"]["skills"][0]["name"],
                MINION_CONFIG["commander_patrol_captain"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_patrol_captain"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_patrol_captain"]["skills"][0]["desc"]
            )
        ]
    ),
    "officer_royal_guard": RoyalGuardTemplate(
        "officer_royal_guard",
        MINION_CONFIG["officer_royal_guard"]["name"],
        []
    ),
    "commander_garrison_leader": GarrisonLeaderTemplate(
        "commander_garrison_leader",
        MINION_CONFIG["commander_garrison_leader"]["name"],
        [
            GarrisonLeaderWall(
                MINION_CONFIG["commander_garrison_leader"]["skills"][0]["name"],
                MINION_CONFIG["commander_garrison_leader"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_garrison_leader"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_garrison_leader"]["skills"][0]["desc"]
            )
        ]
    ),
    "officer_squad_skirmisher": SquadSkirmisherTemplate(
        "officer_squad_skirmisher",
        MINION_CONFIG["officer_squad_skirmisher"]["name"],
        []
    ),
    "commander_valiant_herald": ValiantHeraldTemplate(
        "commander_valiant_herald",
        MINION_CONFIG["commander_valiant_herald"]["name"],
        [
            ValiantHeraldSignal(
                MINION_CONFIG["commander_valiant_herald"]["skills"][0]["name"],
                MINION_CONFIG["commander_valiant_herald"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_valiant_herald"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_valiant_herald"]["skills"][0]["desc"]
            )
        ]
    ),
    "commander_steelclad_tactician": SteelcladTacticianTemplate(
        "commander_steelclad_tactician",
        MINION_CONFIG["commander_steelclad_tactician"]["name"],
        [
            SteelcladTacticianStrike(
                MINION_CONFIG["commander_steelclad_tactician"]["skills"][0]["name"],
                MINION_CONFIG["commander_steelclad_tactician"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_steelclad_tactician"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_steelclad_tactician"]["skills"][0]["desc"]
            )
        ]
    ),
    "officer_blade_dancer": BladeDancerTemplate(
        "officer_blade_dancer",
        MINION_CONFIG["officer_blade_dancer"]["name"],
        [
            BladeDancerSlash(
                MINION_CONFIG["officer_blade_dancer"]["skills"][0]["name"],
                MINION_CONFIG["officer_blade_dancer"]["skills"][0]["cost_a"],
                MINION_CONFIG["officer_blade_dancer"]["skills"][0]["cost_ba"],
                MINION_CONFIG["officer_blade_dancer"]["skills"][0]["desc"]
            )
        ]
    ),
    "commander_aurora_emperor": MinionTemplate(
        "commander_aurora_emperor",
        MINION_CONFIG["commander_aurora_emperor"]["name"],
        [
            AuroraEmperorJudgment(
                MINION_CONFIG["commander_aurora_emperor"]["skills"][0]["name"],
                MINION_CONFIG["commander_aurora_emperor"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_aurora_emperor"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_aurora_emperor"]["skills"][0]["desc"]
            )
        ]
    ),
    "officer_soldier_token": SoldierTokenTemplate(
        "officer_soldier_token",
        MINION_CONFIG["officer_soldier_token"]["name"],
        []
    )
}

upgraded_minions = {}
for mid, temp in ALL_MINIONS.items():
    upgraded_id = f"{mid}+"
    if upgraded_id in MINION_CONFIG:
        upgraded_skills = []
        for idx, orig_skill in enumerate(temp.skills):
            SkillClass = orig_skill.__class__
            skill_cfg = MINION_CONFIG[upgraded_id]["skills"][idx]
            upgraded_skill = SkillClass(
                skill_cfg["name"],
                skill_cfg["cost_a"],
                skill_cfg["cost_ba"],
                skill_cfg["desc"]
            )
            upgraded_skills.append(upgraded_skill)
        upgraded_minions[upgraded_id] = MinionTemplate(
            upgraded_id,
            MINION_CONFIG[upgraded_id]["name"],
            upgraded_skills
        )
ALL_MINIONS.update(upgraded_minions)

MINION_SKILLS = {}
for mid, temp in ALL_MINIONS.items():
    MINION_SKILLS[mid] = [
        {"name": s.name, "cost_a": s.cost_a, "cost_ba": s.cost_ba, "desc": s.desc}
        for s in temp.skills
    ]
