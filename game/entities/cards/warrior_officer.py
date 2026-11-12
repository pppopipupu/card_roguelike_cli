from ...models.state import Card
from ...data.locale_data import get_locale_text
from ...core.deck_service import DeckService
from .registry import register_card

AURORA_ENTRY_SHIELD = 12

@register_card("officer_recruit_vanguard")
class OfficerRecruitVanguardCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 6 if self.upgraded else 4)
        atk = getattr(self, "minion_atk", 3 if self.upgraded else 2)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            msg = get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
            rally = run.node_data.get("rally_count", 0)
            rally_threshold = getattr(self, "rally_threshold", 4)
            if rally >= rally_threshold:
                dmg = getattr(self, "battlecry_damage", 5 if self.upgraded else 3)
                chosen_target = target if (target and target.startswith("e")) else engine._get_first_alive_enemy(run)
                if chosen_target:
                    engine._damage_target(run, chosen_target, dmg, damage_type="piercing")
                    tname = engine._get_target_name(run, chosen_target)
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.recruit_vanguard.rally_damage", rally=rally, name=tname, dmg=dmg)
                else:
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.recruit_vanguard.no_enemy", rally=rally)
                draw_count = getattr(self, "draw_count", 1)
                engine._draw_cards(run.player, draw_count, run)
            else:
                shield = getattr(self, "shield_amount", 4 if self.upgraded else 3)
                engine._gain_shield(run, "p0", shield)
                msg += get_locale_text("i18n_cards_warrior_wizard.warrior.recruit_vanguard.shield", rally=rally, shield=shield)
            return msg
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")


@register_card("officer_banner_bearer")
class OfficerBannerBearerCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 8 if self.upgraded else 5)
        atk = getattr(self, "minion_atk", 2 if self.upgraded else 1)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            msg = get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
            has_cmd = any(m.id.startswith("commander_") for m in run.player.minions.values() if m.id != self.id)
            if has_cmd:
                draw_count = getattr(self, "draw_count", 1)
                engine._draw_cards(run.player, draw_count, run)
                if self.upgraded:
                    gain_a = getattr(self, "gain_a", getattr(self, "action_gain", 1))
                    gain_ba = getattr(self, "gain_ba", getattr(self, "bonus_action_gain", 1))
                    run.player.actions += gain_a
                    run.player.bonus_actions += gain_ba
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.banner_bearer.bonus_upgraded", draw_count=draw_count, gain_a=gain_a, gain_ba=gain_ba)
                else:
                    gain_ba = getattr(self, "gain_ba", getattr(self, "bonus_action_gain", 1))
                    run.player.bonus_actions += gain_ba
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.banner_bearer.bonus", draw_count=draw_count, gain_ba=gain_ba)
            return msg
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")


@register_card("commander_patrol_captain")
class CommanderPatrolCaptainCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 10 if self.upgraded else 7)
        atk = getattr(self, "minion_atk", 4 if self.upgraded else 3)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            msg = get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
            tok_id = "officer_soldier_token+" if self.upgraded else "officer_soldier_token"
            tok_name = get_locale_text("i18n_cards_warrior_wizard.warrior.patrol_captain.token_name_upgraded") if self.upgraded else get_locale_text("i18n_cards_warrior_wizard.warrior.patrol_captain.token_name")
            token_hp = getattr(self, "token_hp", 4 if self.upgraded else 3)
            token_atk = getattr(self, "token_atk", 2 if self.upgraded else 1)
            tok_grid = engine._summon_minion(run, tok_id, tok_name, token_hp, token_atk, 0)
            if tok_grid:
                msg += get_locale_text("i18n_cards_warrior_wizard.warrior.patrol_captain.token_summon", grid=tok_grid, name=tok_name)
                m = run.player.minions[tok_grid]
                engine._add_buff_to(m, "ward", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.ward.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.ward.desc"))
            return msg
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")


@register_card("officer_royal_guard")
class OfficerRoyalGuardCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 11 if self.upgraded else 8)
        atk = getattr(self, "minion_atk", 4 if self.upgraded else 3)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            msg = get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
            rally = run.node_data.get("rally_count", 0)
            rally_threshold = getattr(self, "rally_threshold", 6)
            if rally >= rally_threshold:
                m = run.player.minions[grid]
                engine._add_buff_to(m, "ward", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.ward.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.ward.desc"))
                msg += get_locale_text("i18n_cards_warrior_wizard.warrior.royal_guard.rally", rally=rally)
            return msg
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")


@register_card("commander_garrison_leader")
class CommanderGarrisonLeaderCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 13 if self.upgraded else 9)
        atk = getattr(self, "minion_atk", 5 if self.upgraded else 4)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            msg = get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
            m = run.player.minions[grid]
            engine._add_buff_to(m, "ward", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.ward.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.ward.desc"))
            buff_hp = getattr(self, "ally_hp_bonus", 6 if self.upgraded else 4)
            for mk in list(run.player.minions.keys()):
                mv = run.player.minions.get(mk)
                if mv is None:
                    continue
                if mk != grid and (mv.id.startswith("officer_") or mv.id.startswith("commander_")):
                    mv.max_hp += buff_hp
                    engine._heal_target(run, f"p{mk}", buff_hp)
            msg += get_locale_text("i18n_cards_warrior_wizard.warrior.garrison_leader.rally", buff_hp=buff_hp)
            return msg
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")


@register_card("officer_squad_skirmisher")
class OfficerSquadSkirmisherCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 8 if self.upgraded else 5)
        atk = getattr(self, "minion_atk", 4 if self.upgraded else 3)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            msg = get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
            rally = run.node_data.get("rally_count", 0)
            chosen_target = target if (target and target.startswith("e")) else engine._get_first_alive_enemy(run)
            rally_threshold = getattr(self, "rally_threshold", 8)
            if rally >= rally_threshold:
                dmg = getattr(self, "damage_amount", 9 if self.upgraded else 6)
                if chosen_target:
                    engine._damage_target(run, chosen_target, dmg, damage_type="slashing")
                    tname = engine._get_target_name(run, chosen_target)
                    stun_turns = getattr(self, "buff_turns", getattr(self, "stun_turns", 1))
                    try:
                        f_idx = int(chosen_target.replace("e", "")) - 1
                        if 0 <= f_idx < len(run.enemies):
                            engine._add_buff_to(run.enemies[f_idx], "stun", get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.stun.name"), get_locale_text("i18n_cards_warrior_wizard.warrior.buffs.stun.desc"), stun_turns)
                    except ValueError:
                        pass
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.squad_skirmisher.rally", rally=rally, name=tname, dmg=dmg, stun_turns=stun_turns)
                else:
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.squad_skirmisher.no_enemy", rally=rally)
            else:
                dmg = getattr(self, "battlecry_damage", 5 if self.upgraded else 3)
                if chosen_target:
                    engine._damage_target(run, chosen_target, dmg, damage_type="slashing")
                    tname = engine._get_target_name(run, chosen_target)
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.squad_skirmisher.hit", name=tname, dmg=dmg)
                else:
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.squad_skirmisher.no_enemy_short")
            return msg
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")


@register_card("commander_valiant_herald")
class CommanderValiantHeraldCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 11 if self.upgraded else 8)
        atk = getattr(self, "minion_atk", 4 if self.upgraded else 3)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            msg = get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
            eligible = []
            from .base import ALL_CARDS
            for cid in run.player.draw_pile:
                card = ALL_CARDS.get(cid)
                if card and card.type == "minion" and (card.id.startswith("officer_") or card.id.startswith("commander_")):
                    eligible.append(cid)
            if eligible:
                import random
                chosen = random.choice(eligible)
                run.player.draw_pile.remove(chosen)
                DeckService.add_card_to_hand(run.player, chosen)
                cname = ALL_CARDS.get(chosen).name
                rally = run.node_data.get("rally_count", 0)
                rally_threshold = getattr(self, "rally_threshold", 6)
                if rally >= rally_threshold:
                    run.player.hand.remove(chosen)
                    upg_state = DeckService.upgrade_state(chosen)
                    DeckService.add_card_to_hand(run.player, upg_state)
                    run.node_data.setdefault(run.turn_key("temp_retain_cards"), []).append(upg_state)
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.valiant_herald.rally", rally=rally, name=cname)
                else:
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.valiant_herald.draw", name=cname)
            else:
                msg += get_locale_text("i18n_cards_warrior_wizard.warrior.valiant_herald.fail")
            return msg
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")


@register_card("commander_steelclad_tactician")
class CommanderSteelcladTacticianCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 16 if self.upgraded else 12)
        atk = getattr(self, "minion_atk", 5 if self.upgraded else 4)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")


@register_card("officer_blade_dancer")
class OfficerBladeDancerCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 12 if self.upgraded else 9)
        atk = getattr(self, "minion_atk", 6 if self.upgraded else 5)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            msg = get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
            m = run.player.minions[grid]
            rally = run.node_data.get("rally_count", 0)
            rally_threshold = getattr(self, "rally_threshold", 12)
            if rally >= rally_threshold:
                m.attack_actions = getattr(self, "attack_actions", 2)
                bonus = ""
                if self.upgraded:
                    gain_a = getattr(self, "gain_a", getattr(self, "action_gain", 1))
                    run.player.actions += gain_a
                    bonus = get_locale_text("i18n_cards_warrior_wizard.warrior.blade_dancer.rally_bonus", gain_a=gain_a)
                msg += get_locale_text("i18n_cards_warrior_wizard.warrior.blade_dancer.rally", rally=rally, bonus=bonus)
            has_cmd = any(mv.id.startswith("commander_") for mv in run.player.minions.values() if mv.id != self.id)
            if has_cmd:
                tok_id = "officer_blade_dancer+" if self.upgraded else "officer_blade_dancer"
                tok_name = get_locale_text("i18n_cards_warrior_wizard.warrior.blade_dancer.clone_name_upgraded") if self.upgraded else get_locale_text("i18n_cards_warrior_wizard.warrior.blade_dancer.clone_name")
                tok_grid = engine._summon_minion(run, tok_id, tok_name, hp, atk, 0)
                if tok_grid:
                    msg += get_locale_text("i18n_cards_warrior_wizard.warrior.blade_dancer.clone", grid=tok_grid)
            return msg
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")


@register_card("commander_aurora_emperor")
class CommanderAuroraEmperorCard(Card):
    def execute(self, run, target, engine) -> str:
        hp = getattr(self, "minion_hp", 18 if self.upgraded else 14)
        atk = getattr(self, "minion_atk", 8 if self.upgraded else 6)
        grid = engine._summon_minion(run, self.id, self.name, hp, atk, 0)
        if grid:
            msg = get_locale_text("i18n_cards_warrior_wizard.warrior.minion.summon", grid=grid, name=self.name)
            gain_a = getattr(self, "gain_a", getattr(self, "action_gain", 2))
            attack_actions = getattr(self, "attack_actions", 1)
            for mk, mv in run.player.minions.items():
                if mk != grid and (mv.id.startswith("officer_") or mv.id.startswith("commander_")):
                    mv.actions += gain_a
                    mv.attack_actions = attack_actions
            buff_id = "commander_aurora_emperor+" if self.upgraded else "commander_aurora_emperor"
            buff_name = get_locale_text("i18n_cards_warrior_wizard.warrior.aurora_emperor.buff_name_upgraded") if self.upgraded else get_locale_text("i18n_cards_warrior_wizard.warrior.aurora_emperor.buff_name")
            passive_shield = getattr(self, "shield_amount", 3 if self.upgraded else 2)
            draw_count = getattr(self, "draw_count", 1)
            buff_desc = get_locale_text("i18n_cards_warrior_wizard.warrior.aurora_emperor.buff_desc_upgraded", passive_shield=passive_shield, draw_count=draw_count) if self.upgraded else get_locale_text("i18n_cards_warrior_wizard.warrior.aurora_emperor.buff_desc", passive_shield=passive_shield)
            buff_stacks = getattr(self, "buff_stacks", 1)
            engine._add_buff_to(run.player, buff_id, buff_name, buff_desc, buff_stacks)
            if self.upgraded:
                engine._gain_shield(run, "p0", AURORA_ENTRY_SHIELD)
                msg += get_locale_text("i18n_cards_warrior_wizard.warrior.aurora_emperor.entry_upgraded", gain_a=gain_a, shield=AURORA_ENTRY_SHIELD)
            else:
                msg += get_locale_text("i18n_cards_warrior_wizard.warrior.aurora_emperor.entry", gain_a=gain_a)
            return msg
        return get_locale_text("i18n_cards_warrior_wizard.warrior.minion.full")
