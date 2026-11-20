import random
from ...core.inventory.deck_service import DeckService
from ...data.locale_data import get_locale_text
from ...data.ninja_card_data_basic import NINJA_CARD_CONFIG_BASIC
from ...models.state import CardState
from .ninja_base import (
    NinjaCard,
    add_lan_blade_to_hand,
    add_ninja_buff,
    add_random_food_to_hand,
    change_lex_kela,
    consume_ninjutsu_lex,
    count_ninja_tag_in_deck,
    deal_all_enemies,
    deal_random_enemy_hits,
    resolve_enemy_obj,
)
from .registry import register_card


@register_card("ninja_strike")
class NinjaStrikeCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 6) or 6)
        enemy, ref = resolve_enemy_obj(run, target)
        if not ref:
            return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)
        engine.combat_resolver.damage_target(run, ref, dmg, source="p0", damage_type="physical", card=self, is_attack=True)
        return get_locale_text("i18n_cards_ninja.strike_res", name=enemy.name if enemy else ref, dmg=dmg)


@register_card("ninja_defend")
class NinjaDefendCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        shield = int(getattr(self, "shield_amount", 5) or 5)
        engine.combat_resolver.gain_shield(run, "p0", shield)
        return get_locale_text("i18n_cards_ninja.defend_res", shield=shield)


@register_card("ninja_yi_cut")
class NinjaYiCutCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 10) or 10)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, getattr(self, "ninjutsu_cost", 2), self.id)
        if ok:
            deal_all_enemies(engine, run, self, dmg, "physical")
        for e in run.enemies:
            if e.hp > 0:
                add_ninja_buff(engine, e, "vulnerable", 1)
        if ok:
            return get_locale_text("i18n_cards_ninja.yi_cut_ninjutsu", dmg=dmg)
        return get_locale_text("i18n_cards_ninja.yi_cut_base")


@register_card("ninja_shake_hands")
class NinjaShakeHandsCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "weak", 1)
        for e in run.enemies:
            if e.hp > 0:
                add_ninja_buff(engine, e, "weak", 1)
        lex = 2 if self.upgraded else 1
        change_lex_kela(engine, run, run.player, lex, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.shake_hands_res", lex=lex)


@register_card("ninja_angry_snake_bite")
class NinjaAngrySnakeBiteCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        run.player.discard_pile.append(CardState(id=self.id, upgraded=self.upgraded))
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 2, self.id)
        if ok:
            enemy, _ = resolve_enemy_obj(run, target)
            if enemy is not None:
                add_ninja_buff(engine, enemy, "poison", 7 if self.upgraded else 4)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_burning_blade")
class NinjaBurningBladeCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 7) or 7)
        _, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, dmg, source="p0", damage_type="fire", card=self, is_attack=True)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            p = run.player
            for pile in (p.hand, p.draw_pile, p.discard_pile):
                for st in pile:
                    if st.id == self.id:
                        st.replay = max(st.replay, 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_comet_corrupted_star")
class NinjaCometCorruptedStarCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        if int(getattr(p, "lex_kela", 0) or 0) > 2:
            change_lex_kela(engine, run, p, -1, reason="card", source_card_id=self.id)
            p.actions += 1
        else:
            change_lex_kela(engine, run, p, 3 if self.upgraded else 2, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_darkness_snake_hand")
class NinjaDarknessSnakeHandCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        change_lex_kela(engine, run, run.player, 2 if self.upgraded else 1, reason="card", source_card_id=self.id)
        engine.card_player.draw_cards(run.player, 5, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_flame_thrower")
class NinjaFlameThrowerCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 6) or 6)
        enemy, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, dmg, source="p0", damage_type="fire", card=self, is_attack=True)
        if enemy is not None:
            add_ninja_buff(engine, enemy, "weak", 1)
            ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
            if ok:
                add_ninja_buff(engine, enemy, "poison", 6 if self.upgraded else 4)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_frog_frog_go")
class NinjaFrogFrogGoCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        if p.hand:
            rem = p.hand.pop(random.randrange(len(p.hand)))
            p.exhaust_pile.append(rem)
        ok, _ = consume_ninjutsu_lex(engine, run, p, 1, self.id)
        if ok:
            p.actions += 2 if self.upgraded else 1
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_gamma_blade")
class NinjaGammaBladeCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 13) or 13)
        deal_all_enemies(engine, run, self, dmg, "physical")
        for e in run.enemies:
            if e.hp > 0:
                add_ninja_buff(engine, e, "weak", 2)
                add_ninja_buff(engine, e, "vulnerable", 2)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_god_and_buddha")
class NinjaGodAndBuddhaCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_random_food_to_hand(engine, run, run.player)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_gonna_eat_shit")
class NinjaGonnaEatShitCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        p.hp = max(1, p.hp - 3)
        lex = 3 if self.upgraded else 2
        change_lex_kela(engine, run, p, lex, reason="card", source_card_id=self.id)
        p.actions += 1
        add_ninja_buff(engine, p, "shit_power", lex)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_hands_tickle")
class NinjaHandsTickleCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 4) or 4)
        _, ref = resolve_enemy_obj(run, target)
        hits = min(12, count_ninja_tag_in_deck(run.player, "hand"))
        if ref:
            for _ in range(hits):
                engine.combat_resolver.damage_target(run, ref, dmg, source="p0", damage_type="physical", card=self, is_attack=True)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_holy_little_storm")
class NinjaHolyLittleStormCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 7) or 7)
        ok, x_val = consume_ninjutsu_lex(engine, run, run.player, "X", self.id)
        hits = 1 + (x_val if ok else 0)
        deal_random_enemy_hits(engine, run, self, dmg, hits, "physical")
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_italy_silver_slash")
class NinjaItalySilverSlashCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        cnt = 3 if self.upgraded else 2
        deal_random_enemy_hits(engine, run, self, 4, cnt, "physical")
        engine.card_player.draw_cards(run.player, cnt, run)
        for _ in range(cnt):
            add_lan_blade_to_hand(engine, run, run.player, to_draw=True)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_mamba_missile")
class NinjaMambaMissileCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        hits = 6 if self.upgraded else 5
        deal_random_enemy_hits(engine, run, self, 3, hits, "physical")
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_monk_hand")
class NinjaMonkHandCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            shield = int(getattr(self, "shield_amount", 6) or 6)
            engine.combat_resolver.gain_shield(run, "p0", shield)
        _, ref = resolve_enemy_obj(run, target)
        dmg = max(0, int(run.player.shield))
        if ref and dmg > 0:
            engine.combat_resolver.damage_target(run, ref, dmg, source="p0", damage_type="physical", card=self, is_attack=True)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_oi_sheng_long")
class NinjaOiShengLongCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 9) or 9)
        _, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, dmg, source="p0", damage_type="physical", card=self, is_attack=True)
        change_lex_kela(engine, run, run.player, 2 if self.upgraded else 1, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_plasma_hand")
class NinjaPlasmaHandCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        engine.card_player.draw_cards(run.player, 2 if self.upgraded else 1, run)
        change_lex_kela(engine, run, run.player, 2, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_play_hearthstone")
class NinjaPlayHearthstoneCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        shield = int(getattr(self, "shield_amount", 14) or 14)
        engine.combat_resolver.gain_shield(run, "p0", shield)
        return get_locale_text("i18n_cards_ninja.defend_res", shield=shield)


@register_card("ninja_racing_against_messi")
class NinjaRacingAgainstMessiCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        engine.card_player.draw_cards(run.player, 2, run)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            engine.card_player.draw_cards(run.player, 2 if self.upgraded else 1, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_salt_stealth")
class NinjaSaltStealthCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        shield = int(getattr(self, "shield_amount", 8) or 8)
        engine.combat_resolver.gain_shield(run, "p0", shield)
        p = run.player
        if p.hand:
            idx = random.randrange(len(p.hand))
            pool = [k for k, v in NINJA_CARD_CONFIG_BASIC.items() if not v.get("token") and not v.get("event_only")]
            if pool:
                p.hand[idx] = CardState(id=random.choice(pool))
        return get_locale_text("i18n_cards_ninja.defend_res", shield=shield)


@register_card("ninja_sand_defend_hand")
class NinjaSandDefendHandCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        shield = int(getattr(self, "shield_amount", 8) or 8)
        engine.combat_resolver.gain_shield(run, "p0", shield)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            add_ninja_buff(engine, run.player, "sand_wall", 8 if self.upgraded else 6)
        return get_locale_text("i18n_cards_ninja.defend_res", shield=shield)


@register_card("ninja_lan_blade")
class NinjaLanBladeCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 4) or 4)
        _, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, dmg, source="p0", damage_type="physical", card=self, is_attack=True)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_cold_copper")
class NinjaColdCopperCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        shield = int(getattr(self, "shield_amount", 12) or 12)
        engine.combat_resolver.gain_shield(run, "p0", shield)
        return get_locale_text("i18n_cards_ninja.defend_res", shield=shield)


@register_card("ninja_le_li_su")
class NinjaLeLiSuCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        engine.card_player.draw_cards(run.player, 3 if self.upgraded else 2, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_lizhi")
class NinjaLizhiCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        enemy, _ = resolve_enemy_obj(run, target)
        if enemy is not None:
            st = 3 if self.upgraded else 2
            add_ninja_buff(engine, enemy, "weak", st)
            add_ninja_buff(engine, enemy, "vulnerable", st)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_menggu_banana")
class NinjaMengguBananaCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        run.player.actions += 3 if self.upgraded else 2
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_penglai_can")
class NinjaPenglaiCanCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        cnt = min(5 if self.upgraded else 3, len(p.hand))
        for _ in range(cnt):
            p.exhaust_pile.append(p.hand.pop(random.randrange(len(p.hand))))
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_salty_fish")
class NinjaSaltyFishCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        cnt = min(2 if self.upgraded else 1, len(p.discard_pile))
        for _ in range(cnt):
            st = p.discard_pile.pop(random.randrange(len(p.discard_pile)))
            DeckService.add_card_to_hand(p, st)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_spicy_chicken")
class NinjaSpicyChickenCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        gain = 6 if self.upgraded else 4
        add_ninja_buff(engine, run.player, "strength", gain)
        uid = run.uid_for(run.player) or run.user_id
        store = run.node_data.setdefault("enchant_temp_strength", {})
        store[uid] = int(store.get(uid, 0)) + gain
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_ye_suan_milk")
class NinjaYeSuanMilkCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        change_lex_kela(engine, run, run.player, 5 if self.upgraded else 3, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_alan_walker")
class NinjaAlanWalkerCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "alan_walker", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)
