from ...models.state import Card, AmuletState
from ...data.card_data import CARD_CONFIG
from ...data.locale_data import get_locale_text
from .registry import register_card


def is_upgraded_card(card, base_id: str) -> bool:
    return getattr(card, "id", "") == base_id and bool(getattr(card, "upgraded", False))

@register_card("dagger_throw")
@register_card("fire_bolt")
@register_card("quick_strike")
@register_card("agile_strike")
class SpellDamageCard(Card):
    def __init__(self, id, name, color, type, cost_a, cost_ba, base_dmg, desc=""):
        super().__init__(id, name, color, type, cost_a, cost_ba, desc=desc)
        self.base_dmg = base_dmg

    def execute(self, run, target, engine) -> str:
        dmg = self.base_dmg
        dmg = engine.get_modified_spell_damage(run, self, dmg)
        name = engine._get_target_name(run, target)
        
        is_agile = run.node_data.get("agile_triggering", False)
        dtype = "true" if (is_upgraded_card(self, "agile_strike") and is_agile) else self.damage_type
        
        target_enemy = None
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    target_enemy = run.enemies[idx]
            except ValueError:
                pass
                
        engine._damage_target(run, target, dmg, damage_type=dtype, card=self, damage_ready=True)
        
        is_kill = False
        if target_enemy and (target_enemy not in run.enemies or target_enemy.hp <= 0):
            is_kill = True
            
        bonus_msg = ""
        if is_upgraded_card(self, "dagger_throw") and is_kill:
            gain_a = getattr(self, "gain_a", 1)
            run.player.actions += gain_a
            bonus_msg = get_locale_text("i18n_cards_neutral.neutral.base.spell_damage.kill_bonus")
        elif is_upgraded_card(self, "quick_strike"):
            ally_atk_bonus = getattr(self, "ally_atk_bonus", 1)
            for m in run.player.minions.values():
                m.atk += ally_atk_bonus
            bonus_msg = get_locale_text("i18n_cards_neutral.neutral.base.spell_damage.quick_strike_bonus")
        elif is_upgraded_card(self, "agile_strike") and is_agile:
            draw_count = getattr(self, "draw_count", 1)
            engine._draw_cards(run.player, draw_count, run)
            bonus_msg = get_locale_text("i18n_cards_neutral.neutral.base.spell_damage.agile_strike_bonus")
            
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(target=name, dmg=dmg) + bonus_msg
        
        return get_locale_text("i18n_cards_neutral.neutral.base.spell_damage.result", card_name=self.name, target=name, dmg=dmg) + bonus_msg

@register_card("first_aid")
class SpellHealCard(Card):
    def __init__(self, id, name, color, type, cost_a, cost_ba, heal_amount, desc=""):
        super().__init__(id, name, color, type, cost_a, cost_ba, desc=desc)
        self.heal_amount = heal_amount

    def execute(self, run, target, engine) -> str:
        name = engine._get_target_name(run, target)
        engine._heal_target(run, target, self.heal_amount)
        
        shield_msg = ""
        if is_upgraded_card(self, "first_aid"):
            shield_amount = getattr(self, "shield_amount", 2)
            engine._gain_shield(run, "p0", shield_amount)
            shield_msg = get_locale_text("i18n_cards_neutral.neutral.base.spell_heal.shield_suffix")
            
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        feedback_tmpl = cfg.get("feedback")
        if is_upgraded_card(self, "first_aid"):
            return get_locale_text("i18n_cards_neutral.neutral.base.spell_heal.result_upgraded", target=name, heal_amount=self.heal_amount, shield_msg=shield_msg)
        if feedback_tmpl:
            return feedback_tmpl.format(target=name, heal_amount=self.heal_amount)
        return get_locale_text("i18n_cards_neutral.neutral.base.spell_heal.result", target=name, heal_amount=self.heal_amount)

@register_card("get_ready")
class GetReadyCard(Card):
    def execute(self, run, target, engine) -> str:
        if self.upgraded:
            gain_a = getattr(self, "gain_a", 1)
            gain_ba = getattr(self, "gain_ba", 1)
            draw_count = getattr(self, "draw_count", 2)
            run.player.actions += gain_a
            run.player.bonus_actions += gain_ba
            engine._draw_cards(run.player, draw_count, run)
            return get_locale_text("i18n_cards_neutral.neutral.base.get_ready.result_upgraded")
        else:
            gain_ba = getattr(self, "gain_ba", 2)
            draw_count = getattr(self, "draw_count", 1)
            run.player.bonus_actions += gain_ba
            engine._draw_cards(run.player, draw_count, run)
            cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
            return cfg.get("feedback", get_locale_text("i18n_cards_neutral.neutral.base.get_ready.result"))

@register_card("adrenaline")
class AdrenalineCard(Card):
    def execute(self, run, target, engine) -> str:
        if self.upgraded:
            gain_a = getattr(self, "gain_a", 1)
            gain_ba = getattr(self, "gain_ba", 1)
            draw_count = getattr(self, "draw_count", 1)
            self_hp_cost = getattr(self, "self_hp_cost", 3)
            run.player.actions += gain_a
            run.player.bonus_actions += gain_ba
            engine._draw_cards(run.player, draw_count, run)
            engine._damage_target(run, "p0", self_hp_cost, source="self", damage_type="true")
            return get_locale_text("i18n_cards_neutral.neutral.base.adrenaline.result_upgraded")
        else:
            gain_a = getattr(self, "gain_a", 1)
            self_hp_cost = getattr(self, "self_hp_cost", 2)
            run.player.actions += gain_a
            engine._damage_target(run, "p0", self_hp_cost, source="self", damage_type="true")
            cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
            return cfg.get("feedback", get_locale_text("i18n_cards_neutral.neutral.base.adrenaline.result"))

@register_card("lucky_coin")
@register_card("thorns_necklace")
@register_card("ring_of_elements")
@register_card("arcane_crystal")
@register_card("mage_ward")
@register_card("void_beacon")
@register_card("abyss_altar")
@register_card("abyss_altar_awaken")
@register_card("abyss_altar_converge")
@register_card("abyss_altar_burst")
@register_card("abyss_altar_end")
class DeployAmuletCard(Card):
    def __init__(self, id, name, color, type, cost_a, cost_ba, countdown, amulet_desc, desc=""):
        super().__init__(id, name, color, type, cost_a, cost_ba, countdown=countdown, desc=desc)
        self.amulet_desc = amulet_desc

    def execute(self, run, target, engine) -> str:
        grid = engine._get_free_grid(run.player)
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        if grid:
            cd = self.countdown
            if "ancient_keyring" in run.player.relics:
                import random
                if random.random() < 0.5:
                    cd = max(1, cd - 1)
            deploy_id = self.id
            deploy_name = self.name
            deploy_desc = self.amulet_desc
            if self.id == "abyss_altar" and self.upgraded:
                deploy_id = "abyss_altar_awaken"
                aw_cfg = CARD_CONFIG.get("abyss_altar_awaken", {})
                deploy_name = aw_cfg.get("name", get_locale_text("i18n_cards_neutral.neutral.base.deploy_amulet.abyss_altar_awaken_name"))
                deploy_desc = aw_cfg.get("amulet_desc", get_locale_text("i18n_cards_neutral.neutral.base.deploy_amulet.abyss_altar_awaken_desc"))
            run.player.amulets[grid] = AmuletState(deploy_id, deploy_name, cd, deploy_desc)
            feedback_success = cfg.get("feedback_success", get_locale_text("i18n_cards_neutral.neutral.base.deploy_amulet.success"))
            return feedback_success.format(name=self.name, grid=grid)
        return cfg.get("feedback_fail", get_locale_text("i18n_cards_neutral.neutral.base.deploy_amulet.fail"))

@register_card("minion_icerainboww")
@register_card("mercenary")
@register_card("shield_guard")
@register_card("find_familiar")
@register_card("arcane_golem")
@register_card("water_elemental")
@register_card("gate_guard")
@register_card("elf_archer_xiaomei")
class SummonMinionCard(Card):
    def __init__(self, id, name, color, type, cost_a, cost_ba, minion_hp, minion_atk, desc=""):
        super().__init__(id, name, color, type, cost_a, cost_ba, desc=desc)
        self.minion_hp = minion_hp
        self.minion_atk = minion_atk

    def execute(self, run, target, engine) -> str:
        if self.id.startswith("minion_icerainboww"):
            from ...models.manager import SaveManager
            boss_cfg = SaveManager().load_admin_config()
            if not boss_cfg.get("icerainboww_enabled", True):
                return get_locale_text("i18n_cards_neutral.neutral.base.summon_minion.disabled")
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        minion_id = f"{self.id}+" if bool(getattr(self, "upgraded", False)) else self.id
        grid = engine._summon_minion(run, minion_id, self.name, self.minion_hp, self.minion_atk, 0)
        if grid:
            battlecry_msg = ""
            target_name = get_locale_text("i18n_cards_neutral.neutral.base.summon_minion.none")
            if is_upgraded_card(self, "shield_guard"):
                shield_amount = getattr(self, "shield_amount", 8)
                engine._gain_shield(run, "p0", shield_amount)
                battlecry_msg = get_locale_text("i18n_cards_neutral.neutral.base.summon_minion.shield_guard_battlecry")
            elif is_upgraded_card(self, "minion_icerainboww"):
                shield_amount = getattr(self, "shield_amount", 8)
                buff_stacks = getattr(self, "buff_stacks", 1)
                engine._gain_shield(run, "p0", shield_amount)
                for enemy in list(run.enemies):
                    engine._add_buff_to(enemy, "minor_vulnerable_cold", get_locale_text("i18n_cards_neutral.neutral.buffs.cold_vulnerable.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.cold_vulnerable.desc"), buff_stacks)
                battlecry_msg = get_locale_text("i18n_cards_neutral.neutral.base.summon_minion.ice_rainbow_battlecry")
            elif self.id.startswith("gate_guard"):
                chosen_target = target if (target and target.startswith("e")) else engine._get_first_alive_enemy(run)
                if chosen_target:
                    try:
                        f_idx = int(chosen_target.replace("e", "")) - 1
                        if 0 <= f_idx < len(run.enemies):
                            target_name = run.enemies[f_idx].name
                            stun_turns = getattr(self, "buff_turns", 1)
                            engine._add_buff_to(run.enemies[f_idx], "stun", get_locale_text("i18n_cards_neutral.neutral.buffs.stun.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.stun.desc"), stun_turns)
                            battlecry_msg = get_locale_text("i18n_cards_neutral.neutral.base.summon_minion.gate_guard_battlecry", target=target_name)
                    except ValueError:
                        pass
                
            feedback_success = cfg.get("feedback_success", get_locale_text("i18n_cards_neutral.neutral.base.summon_minion.success"))
            return feedback_success.format(grid=grid, name=self.name, target=target_name) + battlecry_msg
        return cfg.get("feedback_fail", get_locale_text("i18n_cards_neutral.neutral.base.summon_minion.fail"))

@register_card("quicken")
@register_card("spell_surge")
@register_card("arcane_charge")
class AbilityCard(Card):
    def execute(self, run, target, engine) -> str:
        from ...data.buff_data import BUFF_CONFIG
        base_id = self.id.split(":replay:")[0].split(":fragile:")[0].rstrip("+")
        if base_id.startswith("duel_"):
            base_id = base_id[5:]
        buff_info = BUFF_CONFIG.get(base_id, {})
        buff_name = buff_info.get("name", self.name)
        buff_desc = buff_info.get("desc", "")
        engine._add_buff_to(run.player, base_id, buff_name, buff_desc)
        
        cfg = CARD_CONFIG.get(self.id, {})
        feedback_tmpl = cfg.get("feedback")
        if feedback_tmpl:
            return feedback_tmpl.format(name=self.name)
        return get_locale_text("i18n_cards_neutral.neutral.base.ability.result", name=self.name)
