import random
from ...core.inventory.deck_service import DeckService
from ...core.inventory.relic_service import grant_relic
from ...data.text.locale_data import get_locale_text
from ...entities.buffs import is_debuff
from .ninja_base import (
    NinjaCard,
    add_ninja_buff,
    change_lex_kela,
    consume_ninjutsu_lex,
    deal_all_enemies,
    deal_random_enemy_hits,
    resolve_enemy_obj,
)
from .registry import register_card


@register_card("ninja_become_nong")
class NinjaBecomeNongCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        if p.hand:
            picked = random.choice(p.hand)
            run.node_data["ninja_nong_card_id"] = picked.id
            add_ninja_buff(engine, p, "become_nong", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_black_snake_heart")
class NinjaBlackSnakeHeartCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "black_snake_heart", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_countless_vampire_dog")
class NinjaCountlessVampireDogCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        if p.hand:
            src = random.choice(p.hand)
            max_hand = 9 if "mask_of_void" in p.relics else 12
            while len(p.hand) < max_hand:
                p.hand.append(DeckService.clone_state(src))
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_dark_soul_cut")
class NinjaDarkSoulCutCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 0) or 0)
        enemy, ref = resolve_enemy_obj(run, target)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 3, self.id)
        hits = 3 if ok else 0
        was_alive = enemy is not None and enemy.hp > 0
        pre_hp = int(enemy.hp) if enemy is not None else 0
        if ref:
            for _ in range(hits):
                engine.combat_resolver.damage_target(run, ref, dmg, source="p0", damage_type="slashing", card=self, is_attack=True)
        if ok and was_alive and enemy is not None and enemy.hp <= 0 and pre_hp > 0:
            run.player.max_hp += pre_hp
            run.player.hp += pre_hp
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_dragon_smog")
class NinjaDragonSmogCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "intangible", 1)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, getattr(self, "ninjutsu_cost", 2), self.id)
        if ok:
            for e in run.enemies:
                if e.hp > 0:
                    e.shield = 0
                    add_ninja_buff(engine, e, "vulnerable", 2)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_four_nights_lightning")
class NinjaFourNightsLightningCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 4, self.id)
        reps = (4 if self.upgraded else 3) if ok else 1
        for _ in range(reps):
            deal_random_enemy_hits(engine, run, self, 4, 4, "lightning")
            engine.card_player.draw_cards(run.player, 1, run)
            run.player.actions += 1
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_get_all_hands")
class NinjaGetAllHandsCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "get_all_hands", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_get_people_tax")
class NinjaGetPeopleTaxCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        alive_before = sum(1 for e in run.enemies if e.hp > 0)
        deal_all_enemies(engine, run, self, int(getattr(self, "base_dmg", 15) or 15), "slashing")
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 2, self.id)
        if ok and alive_before > 0:
            run.player.gold += alive_before * (15 if self.upgraded else 12)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_hand_ion_destruction")
class NinjaHandIonDestructionCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        deal_all_enemies(engine, run, self, int(getattr(self, "base_dmg", 33) or 33), "lightning")
        add_ninja_buff(engine, run.player, "no_lexkela", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_henghe_shui")
class NinjaHengheShuiCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        heal = random.randint(8 if self.upgraded else 5, 20 if self.upgraded else 15)
        engine.combat_resolver.heal_target(run, "p0", heal)
        poi = random.randint(0, 3)
        if poi > 0:
            add_ninja_buff(engine, run.player, "poison", poi)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_i_represent_shinobi")
class NinjaIRepresentShinobiCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "i_represent_shinobi", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_ignis_healing")
class NinjaIgnisHealingCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        ratio = 0.4 if self.upgraded else 0.3
        heal = max(1, int(run.player.max_hp * ratio))
        engine.combat_resolver.heal_target(run, "p0", heal)
        add_ninja_buff(engine, run.player, "ignis_healing", 2)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_inferno_dragon")
class NinjaInfernoDragonCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "inferno_dragon", 14 if self.upgraded else 10)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_nuclear_dragon")
class NinjaNuclearDragonCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "nuclear_dragon", 5 if self.upgraded else 4)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_oh_fuck_flash")
class NinjaOhFuckFlashCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "intangible", 1)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, getattr(self, "ninjutsu_cost", 3), self.id)
        if ok:
            from ...core.battle.extra_turn_service import MODE_EXTRA, grant_extra_turn
            add_ninja_buff(engine, run.player, "oh_fuck_flash", 1)
            uid = run.uid_for(run.player) or run.user_id
            grant_extra_turn(run, uid, MODE_EXTRA, 1, source=self.id)
            from ...core.battle.extra_turn_service import request_force_end
            request_force_end(run, run.player, self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_past_has_gone_hand")
class NinjaPastHasGoneHandCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        cnt = len(p.discard_pile)
        if cnt > 0:
            p.exhaust_pile.extend(p.discard_pile)
            p.discard_pile.clear()
            engine.combat_resolver.gain_shield(run, "p0", cnt * (6 if self.upgraded else 4))
            change_lex_kela(engine, run, p, cnt, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_power_jesus")
class NinjaPowerJesusCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        for b in p.buffs:
            if b.stacks > 0:
                b.stacks *= 2
        cur = int(getattr(p, "lex_kela", 0) or 0)
        if cur > 0:
            change_lex_kela(engine, run, p, cur, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_radiation_annihilation")
class NinjaRadiationAnnihilationCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        for e in run.enemies:
            if e.hp > 0:
                add_ninja_buff(engine, e, "radiation", 2)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_reaper_flame_blade")
class NinjaReaperFlameBladeCard(NinjaCard):
    def on_exhaust(self, event, card_state):
        p = event.run.player
        for pile in (p.hand, p.draw_pile, p.discard_pile):
            for st in pile:
                if getattr(st, "id", "") == "ninja_reaper_flame_blade":
                    st.battle_cost_delta_a = int(getattr(st, "battle_cost_delta_a", 0) or 0) - 1

    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "intangible", 1)
        add_ninja_buff(engine, run.player, "reaper_flame", 7 if self.upgraded else 5)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_sarira_revive")
class NinjaSariraReviveCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        change_lex_kela(engine, run, p, 3 if self.upgraded else 2, reason="card", source_card_id=self.id)
        engine.card_player.draw_cards(p, 1, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_scare_form")
class NinjaScareFormCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        cost = 1 if self.upgraded else 2
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, cost, self.id)
        if ok:
            add_ninja_buff(engine, run.player, "scare_form", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_south_cross_seal")
class NinjaSouthCrossSealCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        enemy, _ = resolve_enemy_obj(run, target)
        if enemy is not None:
            enemy.shield += 50
            add_ninja_buff(engine, enemy, "stun", 1)
            ok, _ = consume_ninjutsu_lex(engine, run, run.player, 3, self.id)
            if ok:
                add_ninja_buff(engine, enemy, "south_cross_seal", 4 if self.upgraded else 3)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_stone_strong")
class NinjaStoneStrongCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        amt = 9 if self.upgraded else 6
        add_ninja_buff(engine, run.player, "stone_strong", amt)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            add_ninja_buff(engine, run.player, "sand_wall", amt)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_take_your_heart")
class NinjaTakeYourHeartCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        enemy, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, int(getattr(self, "base_dmg", 10) or 10), source="p0", damage_type="piercing", card=self, is_attack=True)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 10, self.id)
        if ok and enemy is not None and enemy.hp > 0:
            debuff_total = sum(b.stacks for b in enemy.buffs if is_debuff(b.id) and b.stacks > 0)
            if debuff_total >= (4 if self.upgraded else 5):
                enemy.hp = 0
                engine._log_event(run, get_locale_text("i18n_cards_ninja.take_your_heart_kill", name=enemy.name))
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_two_monks")
class NinjaTwoMonksCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        from ...core.battle.extra_turn_service import MODE_ARHAT, grant_extra_turn
        uid = run.uid_for(run.player) or run.user_id
        grant_extra_turn(run, uid, MODE_ARHAT, 1, source=self.id)
        return get_locale_text("i18n_cards_ninja.two_monks_result")


@register_card("ninja_ubw")
class NinjaUbwCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            dmg = int(getattr(self, "base_dmg", 8) or 8)
            played_blades = max(1, int(run.node_data.get("ninja_blades_played", 1) or 1))
            deal_random_enemy_hits(engine, run, self, dmg, played_blades, "slashing")
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_shade_cross_slash")
class NinjaShadeCrossSlashCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 10) or 10)
        deal_all_enemies(engine, run, self, dmg, "slashing")
        for e in run.enemies:
            if e.hp > 0:
                add_ninja_buff(engine, e, "vulnerable", 2)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, getattr(self, "ninjutsu_cost", 2), self.id)
        if ok:
            deal_all_enemies(engine, run, self, dmg, "slashing")
            deal_all_enemies(engine, run, self, dmg, "slashing")
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_shen_wei")
class NinjaShenWeiCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "shen_wei", 1)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 3, self.id)
        if ok:
            add_ninja_buff(engine, run.player, "intangible", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_evil_twin")
class NinjaEvilTwinCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        from ...core.party.mercenary import summon_evil_twin_mercenary
        owner_uid = run.uid_for(run.player) or run.user_id
        _, slot, merc = summon_evil_twin_mercenary(engine, run, owner_uid)
        return get_locale_text(
            "i18n_mercenary.evil_twin_summoned",
            slot=slot,
            name=merc.name,
            hp=merc.hp,
            max_hp=merc.max_hp,
        )
