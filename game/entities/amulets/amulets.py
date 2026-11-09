from typing import Optional
from ...data.amulet_data import AMULET_CONFIG

class AmuletTemplate:
    def on_end_turn(self, run, grid: str, engine) -> str:
        return ""

    def on_take_damage(self, run, grid: str, source: str, amount: int, engine) -> str:
        return ""

    def on_spell_played(self, run, grid: str, card, engine) -> str:
        return ""

    def on_death(self, run, grid: str, is_upgraded: bool, engine) -> str:
        return ""

class LuckyCoinAmulet(AmuletTemplate):
    def on_end_turn(self, run, grid, engine) -> str:
        av = run.player.amulets.get(grid)
        is_upgraded = av.id.endswith("+") if av else False
        if is_upgraded:
            run.player.gold += 4
            engine._draw_cards(run.player, 1, run)
        else:
            cfg = AMULET_CONFIG.get("lucky_coin", {})
            gold = cfg.get("gold_on_end", 3)
            run.player.gold += gold
        return ""

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        if is_upgraded:
            run.player.gold += 15
            engine._draw_cards(run.player, 1, run)
            return "获得 15 金币并抽 1 张牌。"
        else:
            run.player.gold += 10
            return "获得 10 金币。"

class MageWardAmulet(AmuletTemplate):
    def on_end_turn(self, run, grid, engine) -> str:
        av = run.player.amulets.get(grid)
        is_upgraded = av.id.endswith("+") if av else False
        if is_upgraded:
            run.player.shield += 6
            if not run.node_data.get("player_damaged_this_turn", False):
                av.countdown += 1
        else:
            cfg = AMULET_CONFIG.get("mage_ward", {})
            shield = cfg.get("shield_on_end", 4)
            run.player.shield += shield
        return ""

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        shield = 10 if is_upgraded else 5
        run.player.shield += shield
        return f"玩家获得 {shield} 点护盾。"

class ThornsNecklaceAmulet(AmuletTemplate):
    def on_take_damage(self, run, grid, source, amount, engine) -> str:
        av = run.player.amulets.get(grid)
        if not av:
            return ""
        is_upgraded = av.id.endswith("+")
        if is_upgraded:
            dmg = 4
            run.player.shield += 1
        else:
            cfg = AMULET_CONFIG.get("thorns_necklace", {})
            dmg = cfg.get("damage_on_hit", 2)
        engine._damage_target(run, source, dmg, damage_type="true")
        src_name = engine._get_target_name(run, source)
        msg = f"【荆棘项链】反弹了 {dmg} 点伤害给【{src_name}】。"
        if run.player.amulets.get(grid) is not av:
            return msg
        av.countdown -= 1
        if av.countdown <= 0:
            run.player.amulets.pop(grid, None)
            run.player.minion_graveyard.append(av.id)
            lw = self.on_death(run, grid, is_upgraded, engine)
            msg += f"\n🔔 [谢幕曲] 我方【{av.name}】吟唱结束进入墓地：{lw}"
        return msg

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        if is_upgraded:
            for idx in range(len(run.enemies)):
                engine._damage_target(run, f"e{idx+1}", 4, damage_type="true")
            return "对全体敌人造成 4 点真实伤害。"
        else:
            t = engine._get_first_alive_enemy(run)
            if t:
                engine._damage_target(run, t, 4, damage_type="true")
                tname = engine._get_target_name(run, t)
                return f"对【{tname}】造成 4 点真实伤害。"
            return "没有存活的敌人。"

class ArcaneCrystalAmulet(AmuletTemplate):
    def on_spell_played(self, run, grid, card, engine) -> str:
        av = run.player.amulets.get(grid)
        is_upgraded = av.id.endswith("+") if av else False
        if is_upgraded:
            heal = 3
            shield = 2
            run.player.hp = min(run.player.max_hp, run.player.hp + heal)
            run.player.shield += shield
        else:
            cfg = AMULET_CONFIG.get("arcane_crystal", {})
            heal = cfg.get("heal_on_spell", 2)
            run.player.hp = min(run.player.max_hp, run.player.hp + heal)
        return ""

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        heal = 8 if is_upgraded else 4
        run.player.hp = min(run.player.max_hp, run.player.hp + heal)
        return f"玩家回复 {heal} 点生命值。"

class RingOfElementsAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        if is_upgraded:
            for idx in range(len(run.enemies)):
                engine._damage_target(run, f"e{idx+1}", 8, damage_type="fire")
            return "对全体敌人造成 8 点火焰伤害。"
        else:
            t = engine._get_first_alive_enemy(run)
            if t:
                engine._damage_target(run, t, 4, damage_type="fire")
                tname = engine._get_target_name(run, t)
                return f"对【{tname}】造成 4 点火焰伤害。"
            return "没有存活的敌人。"

class VoidBeaconAmulet(AmuletTemplate):
    def on_end_turn(self, run, grid, engine) -> str:
        av = run.player.amulets.get(grid)
        is_upgraded = av.id.endswith("+") if av else False
        damage = 8 if is_upgraded else 5
        for enemy in list(run.enemies):
            engine._add_buff_to(enemy, "vulnerable_force", "力场易伤", "受到的力场伤害增加 100%", 1)
        import random
        alive_enemies = [e for e in run.enemies if e.hp > 0]
        if alive_enemies:
            target = random.choice(alive_enemies)
            curr_idx = run.enemies.index(target)
            engine._damage_target(run, f"e{curr_idx+1}", damage, damage_type="force")
            engine._log_event(run, f"🌌 【虚空信标】使所有敌人获得 1 层力场易伤，并对【{target.name}】造成了 {damage} 点力场伤害！")
        return ""

class AbyssAltarAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        from ...models.state import AmuletState
        next_id = "abyss_altar_awaken+" if is_upgraded else "abyss_altar_awaken"
        next_name = "【觉醒】苏醒的深渊祭坛" if is_upgraded else "苏醒的深渊祭坛"
        next_desc = "谢幕曲：在此格子部署【汇集的深渊祭坛】。"
        run.player.amulets[grid] = AmuletState(next_id, next_name, 1, next_desc)
        return f"部署了【{next_name}】。"

class AbyssAltarAwakenAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        from ...models.state import AmuletState
        next_id = "abyss_altar_converge+" if is_upgraded else "abyss_altar_converge"
        next_name = "【觉醒】汇集的深渊祭坛" if is_upgraded else "汇集的深渊祭坛"
        next_desc = "谢幕曲：在此格子部署【爆发的深渊祭坛】。"
        run.player.amulets[grid] = AmuletState(next_id, next_name, 1, next_desc)
        return f"部署了【{next_name}】。"

class AbyssAltarConvergeAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        from ...models.state import AmuletState
        next_id = "abyss_altar_burst+" if is_upgraded else "abyss_altar_burst"
        next_name = "【觉醒】爆发的深渊祭坛" if is_upgraded else "爆发的深渊祭坛"
        next_desc = "谢幕曲：在此格子部署【终结的深渊祭坛】。"
        run.player.amulets[grid] = AmuletState(next_id, next_name, 1, next_desc)
        return f"部署了【{next_name}】。"

class AbyssAltarBurstAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        from ...models.state import AmuletState
        next_id = "abyss_altar_end+" if is_upgraded else "abyss_altar_end"
        next_name = "【觉醒】终结的深渊祭坛" if is_upgraded else "终结的深渊祭坛"
        next_desc = "谢幕曲对场上所有敌人造成 500 点真实伤害，玩家受到 10 点真实伤害。"
        run.player.amulets[grid] = AmuletState(next_id, next_name, 1, next_desc)
        return f"部署了【{next_name}】。"

class AbyssAltarEndAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        dmg_enemies = 600 if is_upgraded else 500
        dmg_player = 5 if is_upgraded else 10
        feedback_parts = []
        for idx in range(len(run.enemies) - 1, -1, -1):
            enemy = run.enemies[idx]
            engine._damage_target(run, f"e{idx+1}", dmg_enemies, damage_type="true", source="abyss_altar_end")
            feedback_parts.append(f"【{enemy.name}】受到 {dmg_enemies} 点真实伤害")
        engine._damage_target(run, "p0", dmg_player, damage_type="true", source="abyss_altar_end")
        return "深渊仪式终结！" + "，".join(feedback_parts) + f"，玩家受到 {dmg_player} 点真实伤害。"

class TacticalBarrackAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        shield = 8 if is_upgraded else 4
        engine._gain_shield(run, "p0", shield)
        from ..cards.base import ALL_CARDS
        minion_pool = [cid for cid, card in ALL_CARDS.items() if card.color == "warrior" and card.type == "minion" and not cid.endswith("+")]
        import random
        if minion_pool:
            cid = random.choice(minion_pool)
            if is_upgraded:
                cid = cid + "+" if not cid.endswith("+") else cid
            if len(run.player.hand) < 12:
                run.player.hand.append(cid)
                card_name = ALL_CARDS[cid].name
                return f"获得 {shield} 点护盾，且将【{card_name}】加入手牌。"
        return f"获得 {shield} 点护盾。"

class IronPhalanxSealAmulet(AmuletTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if not event.grid.startswith("e"):
            av = run.player.amulets.get(grid)
            is_upgraded = av.id.endswith("+") if av else False
            val = 4 if is_upgraded else 3
            m = event.minion_state
            m.max_hp += val
            m.hp += val
            engine._gain_shield(run, "p0", val)
            engine._log_event(run, f"🛡️ 【铁壁法阵】效果触发：使新进场随从【{m.name}】最大生命值与当前生命值提升了 {val} 点，且为玩家提供了 {val} 点护盾。")

class GrandCoronationAmulet(AmuletTemplate):
    def on_card_played(self, run, grid, event, engine):
        card_id = event.card.id
        if card_id.startswith("commander_"):
            av = run.player.amulets.get(grid)
            is_upgraded = av.id.endswith("+") if av else False
            val = 4 if is_upgraded else 2
            for mk, mv in run.player.minions.items():
                if mv.id == card_id and not any(b.id == "ward" for b in mv.buffs):
                    engine._add_buff_to(mv, "ward", "守护", "敌方单体攻击只能指向该随从")
                    mv.atk += val
                    engine._log_event(run, f"👑 【加冕典礼】使新进场的指挥官【{mv.name}】获得了【守护】，且本回合攻击力提升了 {val} 点。")
                    break

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        hp_gain = 8 if is_upgraded else 4
        run.player.max_hp += hp_gain
        run.player.hp = run.player.max_hp
        return f"使玩家最大生命值永久提升了 {hp_gain} 点，且将生命值回复满。"

class BladeRegimentBannerAmulet(AmuletTemplate):
    def on_damage_calculate(self, run, grid, event, engine):
        if event.source.startswith("p"):
            if event.damage_type in ("slashing", "bludgeoning", "piercing"):
                av = run.player.amulets.get(grid)
                is_upgraded = av.id.endswith("+") if av else False
                val = 5 if is_upgraded else 3
                event.modified_damage += val
                engine._log_event(run, f"⚔️ 【锋刃军旗】使本次造成的物理伤害额外增加了 {val} 点。")

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        dmg = 10 if is_upgraded else 6
        heal = 10 if is_upgraded else 6
        for idx in range(len(run.enemies)):
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type="true")
        engine._heal_target(run, "p0", heal)
        return f"对所有敌人造成了 {dmg} 点真实伤害，且为玩家回复了 {heal} 点生命。"

class EnergyCoreAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        if is_upgraded:
            run.player.actions += 2
            run.player.bonus_actions += 1
            return "你获得 2A 1BA。"
        else:
            run.player.actions += 1
            run.player.bonus_actions += 1
            return "你获得 1A 1BA。"

ALL_AMULETS = {
    "energy_core": EnergyCoreAmulet(),
    "lucky_coin": LuckyCoinAmulet(),
    "mage_ward": MageWardAmulet(),
    "thorns_necklace": ThornsNecklaceAmulet(),
    "arcane_crystal": ArcaneCrystalAmulet(),
    "ring_of_elements": RingOfElementsAmulet(),
    "void_beacon": VoidBeaconAmulet(),
    "abyss_altar": AbyssAltarAmulet(),
    "abyss_altar_awaken": AbyssAltarAwakenAmulet(),
    "abyss_altar_converge": AbyssAltarConvergeAmulet(),
    "abyss_altar_burst": AbyssAltarBurstAmulet(),
    "abyss_altar_end": AbyssAltarEndAmulet(),
    "tactical_barrack": TacticalBarrackAmulet(),
    "iron_phalanx_seal": IronPhalanxSealAmulet(),
    "grand_coronation": GrandCoronationAmulet(),
    "blade_regiment_banner": BladeRegimentBannerAmulet(),
}
