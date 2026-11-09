from typing import Optional
from ...data.amulet_data import AMULET_CONFIG
from ...data.locale_data import get_locale_text
from ...core.deck_service import DeckService, UPGRADE_SUFFIX

class AmuletTemplate:
    def on_end_turn(self, run, grid: str, engine) -> str:
        return ""

    def on_take_damage(self, run, grid: str, source: str, amount: int, engine) -> str:
        return ""

    def on_spell_played(self, run, grid: str, card, engine) -> str:
        return ""

    def on_death(self, run, grid, is_upgraded: bool, engine) -> str:
        return ""

class LuckyCoinAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("lucky_coin", {})
        self.gold_on_end = cfg.get("gold_on_end", 3)
        self.upgraded_gold_on_end = cfg.get("upgraded_gold_on_end", 4)
        self.upgraded_draw_on_end = cfg.get("upgraded_draw_on_end", 1)
        self.gold_on_death = cfg.get("gold_on_death", 10)
        self.upgraded_gold_on_death = cfg.get("upgraded_gold_on_death", 15)
        self.upgraded_draw_on_death = cfg.get("upgraded_draw_on_death", 1)

    def on_end_turn(self, run, grid, engine) -> str:
        av = run.player.amulets.get(grid)
        is_upgraded = av.id.endswith(UPGRADE_SUFFIX) if av else False
        if is_upgraded:
            run.player.gold += self.upgraded_gold_on_end
            engine._draw_cards(run.player, self.upgraded_draw_on_end, run)
        else:
            run.player.gold += self.gold_on_end
        return ""

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        if is_upgraded:
            run.player.gold += self.upgraded_gold_on_death
            engine._draw_cards(run.player, self.upgraded_draw_on_death, run)
            return get_locale_text("i18n_relics_amulets.amulets.lucky_coin.upgraded_death")
        else:
            run.player.gold += self.gold_on_death
            return get_locale_text("i18n_relics_amulets.amulets.lucky_coin.death")

class MageWardAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("mage_ward", {})
        self.shield_on_end = cfg.get("shield_on_end", 4)
        self.upgraded_shield_on_end = cfg.get("upgraded_shield_on_end", 6)
        self.upgraded_countdown_refund = cfg.get("upgraded_countdown_refund", 1)
        self.shield_on_death = cfg.get("shield_on_death", 5)
        self.upgraded_shield_on_death = cfg.get("upgraded_shield_on_death", 10)

    def on_end_turn(self, run, grid, engine) -> str:
        av = run.player.amulets.get(grid)
        is_upgraded = av.id.endswith(UPGRADE_SUFFIX) if av else False
        if is_upgraded:
            engine._gain_shield(run, "p0", self.upgraded_shield_on_end)
            if not run.node_data.get("player_damaged_this_turn", False):
                av.countdown += self.upgraded_countdown_refund
        else:
            engine._gain_shield(run, "p0", self.shield_on_end)
        return ""

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        shield = self.upgraded_shield_on_death if is_upgraded else self.shield_on_death
        engine._gain_shield(run, "p0", shield)
        return get_locale_text("i18n_relics_amulets.amulets.mage_ward.death", shield=shield)

class ThornsNecklaceAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("thorns_necklace", {})
        self.damage_on_hit = cfg.get("damage_on_hit", 2)
        self.upgraded_damage_on_hit = cfg.get("upgraded_damage_on_hit", 4)
        self.upgraded_shield_on_hit = cfg.get("upgraded_shield_on_hit", 1)
        self.death_damage = cfg.get("death_damage", 4)
        self.upgraded_death_damage = cfg.get("upgraded_death_damage", 4)

    def on_take_damage(self, run, grid, source, amount, engine) -> str:
        av = run.player.amulets.get(grid)
        if not av:
            return ""
        is_upgraded = av.id.endswith(UPGRADE_SUFFIX)
        if is_upgraded:
            dmg = self.upgraded_damage_on_hit
            engine._gain_shield(run, "p0", self.upgraded_shield_on_hit)
        else:
            dmg = self.damage_on_hit
        engine._damage_target(run, source, dmg, damage_type="true")
        src_name = engine._get_target_name(run, source)
        msg = get_locale_text("i18n_relics_amulets.amulets.thorns_necklace.reflect", dmg=dmg, src_name=src_name)
        if run.player.amulets.get(grid) is not av:
            return msg
        av.countdown -= 1
        if av.countdown <= 0:
            run.player.amulets.pop(grid, None)
            run.player.minion_graveyard.append(av.id)
            lw = self.on_death(run, grid, is_upgraded, engine)
            msg += get_locale_text("i18n_relics_amulets.amulets.thorns_necklace.requiem", name=av.name, effect=lw)
        return msg

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        if is_upgraded:
            for idx in range(len(run.enemies)):
                engine._damage_target(run, f"e{idx+1}", self.upgraded_death_damage, damage_type="true")
            return get_locale_text("i18n_relics_amulets.amulets.thorns_necklace.death_all")
        else:
            t = engine._get_first_alive_enemy(run)
            if t:
                engine._damage_target(run, t, self.death_damage, damage_type="true")
                tname = engine._get_target_name(run, t)
                return get_locale_text("i18n_relics_amulets.amulets.thorns_necklace.death_single", tname=tname)
            return get_locale_text("i18n_relics_amulets.amulets.thorns_necklace.no_enemies")

class ArcaneCrystalAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("arcane_crystal", {})
        self.heal_on_spell = cfg.get("heal_on_spell", 2)
        self.upgraded_heal_on_spell = cfg.get("upgraded_heal_on_spell", 3)
        self.upgraded_shield_on_spell = cfg.get("upgraded_shield_on_spell", 2)
        self.heal_on_death = cfg.get("heal_on_death", 4)
        self.upgraded_heal_on_death = cfg.get("upgraded_heal_on_death", 8)

    def on_spell_played(self, run, grid, card, engine) -> str:
        av = run.player.amulets.get(grid)
        is_upgraded = av.id.endswith(UPGRADE_SUFFIX) if av else False
        if is_upgraded:
            heal = self.upgraded_heal_on_spell
            shield = self.upgraded_shield_on_spell
            engine._heal_target(run, "p0", heal)
            engine._gain_shield(run, "p0", shield)
        else:
            heal = self.heal_on_spell
            engine._heal_target(run, "p0", heal)
        return ""

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        heal = self.upgraded_heal_on_death if is_upgraded else self.heal_on_death
        engine._heal_target(run, "p0", heal)
        return get_locale_text("i18n_relics_amulets.amulets.arcane_crystal.death", heal=heal)

class RingOfElementsAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("ring_of_elements", {})
        self.fire_dmg_bonus = cfg.get("fire_dmg_bonus", 2)
        self.upgraded_fire_dmg_bonus = cfg.get("upgraded_fire_dmg_bonus", 3)
        self.death_damage = cfg.get("death_damage", 4)
        self.upgraded_death_damage = cfg.get("upgraded_death_damage", 8)

    def on_damage_calculate(self, run, grid, event, engine):
        if event.source != "p0" or event.card is None:
            return
        if getattr(event.card, "type", "") != "spell" or event.damage_type != "fire":
            return
        av = run.player.amulets.get(grid)
        event.modified_damage += self.upgraded_fire_dmg_bonus if av and av.id.endswith("+") else self.fire_dmg_bonus

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        if is_upgraded:
            for idx in range(len(run.enemies)):
                engine._damage_target(run, f"e{idx+1}", self.upgraded_death_damage, damage_type="fire")
            return get_locale_text("i18n_relics_amulets.amulets.ring_of_elements.death_all")
        else:
            t = engine._get_first_alive_enemy(run)
            if t:
                engine._damage_target(run, t, self.death_damage, damage_type="fire")
                tname = engine._get_target_name(run, t)
                return get_locale_text("i18n_relics_amulets.amulets.ring_of_elements.death_single", tname=tname)
            return get_locale_text("i18n_relics_amulets.amulets.ring_of_elements.no_enemies")

class VoidBeaconAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("void_beacon", {})
        self.damage = cfg.get("damage", 5)
        self.upgraded_damage = cfg.get("upgraded_damage", 8)
        self.vulnerable_stacks = cfg.get("vulnerable_stacks", 1)

    def on_end_turn(self, run, grid, engine) -> str:
        av = run.player.amulets.get(grid)
        is_upgraded = av.id.endswith(UPGRADE_SUFFIX) if av else False
        damage = self.upgraded_damage if is_upgraded else self.damage
        for enemy in list(run.enemies):
            engine._add_buff_to(enemy, "vulnerable_force", get_locale_text("i18n_relics_amulets.amulets.void_beacon.buff_name"), get_locale_text("i18n_relics_amulets.amulets.void_beacon.buff_desc"), self.vulnerable_stacks)
        import random
        alive_enemies = [e for e in run.enemies if e.hp > 0]
        if alive_enemies:
            target = random.choice(alive_enemies)
            curr_idx = run.enemies.index(target)
            engine._damage_target(run, f"e{curr_idx+1}", damage, damage_type="force")
            engine._log_event(run, get_locale_text("i18n_relics_amulets.amulets.void_beacon.trigger", name=target.name, damage=damage))
        return ""

class AbyssAltarAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        from ...models.state import AmuletState
        next_id = "abyss_altar_awaken+" if is_upgraded else "abyss_altar_awaken"
        next_name = get_locale_text("i18n_relics_amulets.amulets.abyss_altar.next_name_upgraded") if is_upgraded else get_locale_text("i18n_relics_amulets.amulets.abyss_altar.next_name")
        next_desc = get_locale_text("i18n_relics_amulets.amulets.abyss_altar.next_desc")
        run.player.amulets[grid] = AmuletState(next_id, next_name, AMULET_CONFIG.get(next_id, {}).get("countdown", 1), next_desc)
        return get_locale_text("i18n_relics_amulets.amulets.abyss_altar.deployed", name=next_name)

class AbyssAltarAwakenAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        from ...models.state import AmuletState
        next_id = "abyss_altar_converge+" if is_upgraded else "abyss_altar_converge"
        next_name = get_locale_text("i18n_relics_amulets.amulets.abyss_altar_awaken.next_name_upgraded") if is_upgraded else get_locale_text("i18n_relics_amulets.amulets.abyss_altar_awaken.next_name")
        next_desc = get_locale_text("i18n_relics_amulets.amulets.abyss_altar_awaken.next_desc")
        run.player.amulets[grid] = AmuletState(next_id, next_name, AMULET_CONFIG.get(next_id, {}).get("countdown", 1), next_desc)
        return get_locale_text("i18n_relics_amulets.amulets.abyss_altar_awaken.deployed", name=next_name)

class AbyssAltarConvergeAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        from ...models.state import AmuletState
        next_id = "abyss_altar_burst+" if is_upgraded else "abyss_altar_burst"
        next_name = get_locale_text("i18n_relics_amulets.amulets.abyss_altar_converge.next_name_upgraded") if is_upgraded else get_locale_text("i18n_relics_amulets.amulets.abyss_altar_converge.next_name")
        next_desc = get_locale_text("i18n_relics_amulets.amulets.abyss_altar_converge.next_desc")
        run.player.amulets[grid] = AmuletState(next_id, next_name, AMULET_CONFIG.get(next_id, {}).get("countdown", 1), next_desc)
        return get_locale_text("i18n_relics_amulets.amulets.abyss_altar_converge.deployed", name=next_name)

class AbyssAltarBurstAmulet(AmuletTemplate):
    def on_death(self, run, grid, is_upgraded, engine) -> str:
        from ...models.state import AmuletState
        next_id = "abyss_altar_end+" if is_upgraded else "abyss_altar_end"
        next_name = get_locale_text("i18n_relics_amulets.amulets.abyss_altar_burst.next_name_upgraded") if is_upgraded else get_locale_text("i18n_relics_amulets.amulets.abyss_altar_burst.next_name")
        next_desc = get_locale_text("i18n_relics_amulets.amulets.abyss_altar_burst.next_desc")
        run.player.amulets[grid] = AmuletState(next_id, next_name, AMULET_CONFIG.get(next_id, {}).get("countdown", 1), next_desc)
        return get_locale_text("i18n_relics_amulets.amulets.abyss_altar_burst.deployed", name=next_name)

class AbyssAltarEndAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("abyss_altar_end", {})
        self.enemy_damage = cfg.get("enemy_damage", 500)
        self.upgraded_enemy_damage = cfg.get("upgraded_enemy_damage", 600)
        self.player_damage = cfg.get("player_damage", 10)
        self.upgraded_player_damage = cfg.get("upgraded_player_damage", 5)

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        dmg_enemies = self.upgraded_enemy_damage if is_upgraded else self.enemy_damage
        dmg_player = self.upgraded_player_damage if is_upgraded else self.player_damage
        feedback_parts = []
        for idx in range(len(run.enemies) - 1, -1, -1):
            enemy = run.enemies[idx]
            engine._damage_target(run, f"e{idx+1}", dmg_enemies, damage_type="true", source="abyss_altar_end")
            feedback_parts.append(get_locale_text("i18n_relics_amulets.amulets.abyss_altar_end.feedback", name=enemy.name, dmg=dmg_enemies))
        engine._damage_target(run, "p0", dmg_player, damage_type="true", source="abyss_altar_end")
        return get_locale_text("i18n_relics_amulets.amulets.abyss_altar_end.result", feedback="，".join(feedback_parts), dmg_player=dmg_player)

class TacticalBarrackAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("tactical_barrack", {})
        self.shield_on_death = cfg.get("shield_on_death", 4)
        self.upgraded_shield_on_death = cfg.get("upgraded_shield_on_death", 8)
        self.max_hand = cfg.get("max_hand", 12)

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        shield = self.upgraded_shield_on_death if is_upgraded else self.shield_on_death
        engine._gain_shield(run, "p0", shield)
        from ..cards.base import ALL_CARDS
        minion_pool = [cid for cid, card in ALL_CARDS.items() if card.color == "warrior" and card.type == "minion"]
        import random
        if minion_pool:
            minion_state = DeckService.new_state(random.choice(minion_pool), upgraded=is_upgraded)
            if len(run.player.hand) < self.max_hand:
                DeckService.add_card_to_hand(run.player, minion_state)
                card_name = ALL_CARDS[minion_state].name
                return get_locale_text("i18n_relics_amulets.amulets.tactical_barrack.shield_and_card", shield=shield, card_name=card_name)
        return get_locale_text("i18n_relics_amulets.amulets.tactical_barrack.shield_only", shield=shield)

class IronPhalanxSealAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("iron_phalanx_seal", {})
        self.max_hp_bonus = cfg.get("max_hp_bonus", 3)
        self.upgraded_max_hp_bonus = cfg.get("upgraded_max_hp_bonus", 4)
        self.shield_bonus = cfg.get("shield_bonus", 3)
        self.upgraded_shield_bonus = cfg.get("upgraded_shield_bonus", 4)

    def on_minion_summon(self, run, grid, event, engine):
        if not event.grid.startswith("e"):
            av = run.player.amulets.get(grid)
            is_upgraded = av.id.endswith(UPGRADE_SUFFIX) if av else False
            max_hp_bonus = self.upgraded_max_hp_bonus if is_upgraded else self.max_hp_bonus
            shield_bonus = self.upgraded_shield_bonus if is_upgraded else self.shield_bonus
            m = event.minion_state
            m.max_hp += max_hp_bonus
            m.hp += max_hp_bonus
            engine._gain_shield(run, "p0", shield_bonus)
            engine._log_event(run, get_locale_text("i18n_relics_amulets.amulets.iron_phalanx_seal.trigger", name=m.name, max_hp_bonus=max_hp_bonus, shield_bonus=shield_bonus))

class GrandCoronationAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("grand_coronation", {})
        self.atk_bonus = cfg.get("atk_bonus", 2)
        self.upgraded_atk_bonus = cfg.get("upgraded_atk_bonus", 4)
        self.hp_gain = cfg.get("hp_gain", 4)
        self.upgraded_hp_gain = cfg.get("upgraded_hp_gain", 8)

    def on_card_played(self, run, grid, event, engine):
        card_id = event.card.id
        if card_id.startswith("commander_"):
            av = run.player.amulets.get(grid)
            is_upgraded = av.id.endswith(UPGRADE_SUFFIX) if av else False
            val = self.upgraded_atk_bonus if is_upgraded else self.atk_bonus
            for mk, mv in run.player.minions.items():
                if mv.id == card_id and not any(b.id == "ward" for b in mv.buffs):
                    engine._add_buff_to(mv, "ward", get_locale_text("i18n_relics_amulets.amulets.grand_coronation.buff_name"), get_locale_text("i18n_relics_amulets.amulets.grand_coronation.buff_desc"))
                    mv.atk += val
                    engine._log_event(run, get_locale_text("i18n_relics_amulets.amulets.grand_coronation.trigger", name=mv.name, val=val))
                    break

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        hp_gain = self.upgraded_hp_gain if is_upgraded else self.hp_gain
        run.player.max_hp += hp_gain
        engine._heal_target(run, "p0", run.player.max_hp - run.player.hp)
        return get_locale_text("i18n_relics_amulets.amulets.grand_coronation.death", hp_gain=hp_gain)

class BladeRegimentBannerAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("blade_regiment_banner", {})
        self.physical_damage_bonus = cfg.get("physical_damage_bonus", 3)
        self.upgraded_physical_damage_bonus = cfg.get("upgraded_physical_damage_bonus", 5)
        self.death_damage = cfg.get("death_damage", 6)
        self.upgraded_death_damage = cfg.get("upgraded_death_damage", 10)
        self.death_heal = cfg.get("death_heal", 6)
        self.upgraded_death_heal = cfg.get("upgraded_death_heal", 10)

    def on_damage_calculate(self, run, grid, event, engine):
        if event.source.startswith("p"):
            if event.damage_type in ("slashing", "bludgeoning", "piercing"):
                av = run.player.amulets.get(grid)
                is_upgraded = av.id.endswith(UPGRADE_SUFFIX) if av else False
                val = self.upgraded_physical_damage_bonus if is_upgraded else self.physical_damage_bonus
                event.modified_damage += val
                engine._log_event(run, get_locale_text("i18n_relics_amulets.amulets.blade_regiment_banner.trigger", val=val))

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        dmg = self.upgraded_death_damage if is_upgraded else self.death_damage
        heal = self.upgraded_death_heal if is_upgraded else self.death_heal
        for idx in range(len(run.enemies)):
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type="true")
        engine._heal_target(run, "p0", heal)
        return get_locale_text("i18n_relics_amulets.amulets.blade_regiment_banner.death", dmg=dmg, heal=heal)

class EnergyCoreAmulet(AmuletTemplate):
    def __init__(self):
        cfg = AMULET_CONFIG.get("energy_core", {})
        self.actions = cfg.get("actions", 1)
        self.upgraded_actions = cfg.get("upgraded_actions", 2)
        self.bonus_actions = cfg.get("bonus_actions", 1)

    def on_death(self, run, grid, is_upgraded, engine) -> str:
        if is_upgraded:
            run.player.actions += self.upgraded_actions
            run.player.bonus_actions += self.bonus_actions
            return get_locale_text("i18n_relics_amulets.amulets.energy_core.death_upgraded")
        else:
            run.player.actions += self.actions
            run.player.bonus_actions += self.bonus_actions
            return get_locale_text("i18n_relics_amulets.amulets.energy_core.death")

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
