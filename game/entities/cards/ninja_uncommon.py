import random
from ...core.inventory.deck_service import DeckService
from ...data.locale_data import get_locale_text
from ...data.ninja_card_data_basic import NINJA_CARD_CONFIG_BASIC
from ...data.ninja_card_data_uncommon import NINJA_CARD_CONFIG_UNCOMMON
from ...models.state import CardState
from .ninja_base import (
    NinjaCard,
    add_lan_blade_to_hand,
    add_ninja_buff,
    change_lex_kela,
    consume_ninjutsu_lex,
    deal_all_enemies,
    has_ninja_tag,
    resolve_enemy_obj,
)
from .registry import register_card


@register_card("ninja_abrasive_strike")
class NinjaAbrasiveStrikeCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        dmg = int(getattr(self, "base_dmg", 8) or 8)
        _, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, dmg, source="p0", damage_type="physical", card=self, is_attack=True)
        add_ninja_buff(engine, run.player, "thorns", 5 if self.upgraded else 3)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_annai_master")
class NinjaAnnaiMasterCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        pool = [k for k, v in {**NINJA_CARD_CONFIG_BASIC, **NINJA_CARD_CONFIG_UNCOMMON}.items() if "ninjutsu" in v.get("ninja_tags", ())]
        if pool:
            DeckService.add_card_to_hand(run.player, CardState(id=random.choice(pool)))
        add_ninja_buff(engine, run.player, "free_ninjutsu", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_back_fourth_hand")
class NinjaBackFourthHandCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        engine.combat_resolver.gain_shield(run, "p0", int(getattr(self, "shield_amount", 8) or 8))
        p = run.player
        for _ in range(min(2, len(p.discard_pile))):
            DeckService.add_card_to_hand(p, p.discard_pile.pop(random.randrange(len(p.discard_pile))))
        for _ in range(min(2, len(p.hand))):
            p.discard_pile.append(p.hand.pop(random.randrange(len(p.hand))))
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_beast_shout")
class NinjaBeastShoutCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        deal_all_enemies(engine, run, self, int(getattr(self, "base_dmg", 11) or 11), "physical")
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            loss = 3 if self.upgraded else 2
            for e in run.enemies:
                if e.hp > 0:
                    for b in list(e.buffs):
                        if b.id == "strength":
                            b.stacks = max(0, b.stacks - loss)
                            if b.stacks <= 0:
                                e.buffs.remove(b)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_black_dragon_hand")
class NinjaBlackDragonHandCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        enemy, _ = resolve_enemy_obj(run, target)
        if enemy is not None:
            add_ninja_buff(engine, enemy, "weak", 3 if self.upgraded else 2)
            enemy.buffs = [b for b in enemy.buffs if b.id != "intangible"]
            ok, _ = consume_ninjutsu_lex(engine, run, run.player, 2, self.id)
            if ok:
                steal = 3 if self.upgraded else 2
                enemy.max_hp = max(1, enemy.max_hp - steal)
                enemy.hp = min(enemy.hp, enemy.max_hp)
                run.player.max_hp += steal
                run.player.hp += steal
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_black_zi_cannon")
class NinjaBlackZiCannonCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        _, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, int(getattr(self, "base_dmg", 26) or 26), source="p0", damage_type="physical", card=self, is_attack=True)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_blade_defence")
class NinjaBladeDefenceCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "blade_defence", 6 if self.upgraded else 4)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_buddha_hand")
class NinjaBuddhaHandCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        enemy, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, int(getattr(self, "base_dmg", 10) or 10), source="p0", damage_type="physical", card=self, is_attack=True)
        if enemy is not None:
            add_ninja_buff(engine, enemy, "vulnerable", 2)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            run.player.actions += 2
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_build_sand_wall")
class NinjaBuildSandWallCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "build_sand_wall", 1)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            sw = next((b.stacks for b in run.player.buffs if b.id == "sand_wall"), 0)
            if sw > 0:
                engine.combat_resolver.gain_shield(run, "p0", sw)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_darkness_crawl")
class NinjaDarknessCrawlCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        x_val = int(run.node_data.get("last_x_cost_a", 0) or 0) + (1 if self.upgraded else 0)
        if x_val > 0:
            engine.combat_resolver.gain_shield(run, "p0", 5 * x_val)
            change_lex_kela(engine, run, run.player, x_val, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_darkness_shoryuken")
class NinjaDarknessShoryukenCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        enemy, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, int(getattr(self, "base_dmg", 8) or 8), source="p0", damage_type="physical", card=self, is_attack=True)
        if enemy is not None:
            add_ninja_buff(engine, enemy, "weak", 1)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok and run.player.hand:
            run.player.exhaust_pile.append(run.player.hand.pop(random.randrange(len(run.player.hand))))
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_disappointed_bocchi")
class NinjaDisappointedBocchiCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "disappointed", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_dragon_punch")
class NinjaDragonPunchCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        _, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, int(getattr(self, "base_dmg", 18) or 18), source="p0", damage_type="fire", card=self, is_attack=True)
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            engine.card_player.draw_cards(run.player, 3 if self.upgraded else 2, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_eclipse_mist_blade")
class NinjaEclipseMistBladeCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        from .base import ALL_CARDS
        engine.combat_resolver.gain_shield(run, "p0", int(getattr(self, "shield_amount", 8) or 8))
        p = run.player
        gained = 0
        for st in list(p.hand):
            c = ALL_CARDS.get(st)
            if not has_ninja_tag(c, "blade"):
                p.hand.remove(st)
                p.exhaust_pile.append(st)
                gained += 1
        if gained > 0:
            change_lex_kela(engine, run, p, gained, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_genshin_storm")
class NinjaGenshinStormCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        ok, x_val = consume_ninjutsu_lex(engine, run, run.player, "X", self.id)
        targets = [run.players[u] for u in run.party_order if u in run.players and not run.players[u].downed]
        if not targets:
            targets = [run.player]
        for pl in targets:
            DeckService.add_card_to_hand(pl, CardState(id="ninja_holy_little_storm", upgraded=True))
            if ok and x_val > 0:
                change_lex_kela(engine, run, pl, x_val, reason="card", source_card_id=self.id)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_go_back_hands")
class NinjaGoBackHandsCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        from .base import ALL_CARDS
        p = run.player
        for st in list(p.discard_pile):
            if has_ninja_tag(ALL_CARDS.get(st), "hand"):
                p.discard_pile.remove(st)
                DeckService.add_card_to_hand(p, st)
        ok, _ = consume_ninjutsu_lex(engine, run, p, 2, self.id)
        if ok:
            p.actions += 1
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_good_night")
class NinjaGoodNightCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        change_lex_kela(engine, run, run.player, 5 if self.upgraded else 3, reason="card", source_card_id=self.id)
        engine.combat_resolver.heal_target(run, "p0", 12 if self.upgraded else 8)
        add_ninja_buff(engine, run.player, "good_night", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_hamood_kick")
class NinjaHamoodKickCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        deal_all_enemies(engine, run, self, int(getattr(self, "base_dmg", 13) or 13), "physical")
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            engine.card_player.draw_cards(run.player, 1, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_he_bully_me")
class NinjaHeBullyMeCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        targets = [run.players[u] for u in run.party_order if u in run.players and not run.players[u].downed]
        if not targets:
            targets = [run.player]
        act_gain = 3 if self.upgraded else 2
        str_gain = 4 if self.upgraded else 3
        for pl in targets:
            pl.actions += act_gain
            add_ninja_buff(engine, pl, "strength", str_gain)
            uid = run.uid_for(pl) or run.user_id
            store = run.node_data.setdefault("enchant_temp_strength", {})
            store[uid] = int(store.get(uid, 0)) + str_gain
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_heaven_cross")
class NinjaHeavenCrossCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "heaven_cross", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_infinite_snake_bites")
class NinjaInfiniteSnakeBitesCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "infinite_snake_bites", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_lan_blade_cutting")
class NinjaLanBladeCuttingCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "lan_blade_cutting", 1)
        if self.upgraded:
            for b in run.player.buffs:
                if b.id == "lan_blade_cutting":
                    b.stacks2 = 1
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok:
            add_lan_blade_to_hand(engine, run, run.player, upgraded=self.upgraded)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_leech_friend")
class NinjaLeechFriendCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        enemy, _ = resolve_enemy_obj(run, target)
        if enemy is not None and any(b.id == "weak" and b.stacks > 0 for b in enemy.buffs):
            amt = 3 if self.upgraded else 2
            add_ninja_buff(engine, run.player, "strength", amt)
            engine.combat_resolver.gain_shield(run, "p0", 6 if self.upgraded else 4)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_man_too_weak")
class NinjaManTooWeakCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        amt = 4 if self.upgraded else 3
        add_ninja_buff(engine, run.player, "strength", amt)
        add_ninja_buff(engine, run.player, "dexterity", amt)
        add_ninja_buff(engine, run.player, "man_too_weak", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_mobius_loop_snake")
class NinjaMobiusLoopSnakeCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        prev_id = run.node_data.get("ninja_last_played_card_id", "")
        if prev_id and prev_id != self.id:
            DeckService.add_card_to_hand(run.player, CardState(id=prev_id))
        engine.card_player.draw_cards(run.player, 1, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_mummy_mummy")
class NinjaMummyMummyCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "mummy_power", 6 if self.upgraded else 4)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_nami_lightning")
class NinjaNamiLightningCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        engine.card_player.draw_cards(run.player, 3 if self.upgraded else 2, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_nami_yoyo")
class NinjaNamiYoyoCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        enemy, _ = resolve_enemy_obj(run, target)
        if enemy is not None:
            add_ninja_buff(engine, enemy, "poison", 7 if self.upgraded else 5)
            p_stacks = next((b.stacks for b in enemy.buffs if b.id == "poison"), 0)
            others = [e for e in run.enemies if e is not enemy and e.hp > 0]
            if others and p_stacks > 0:
                add_ninja_buff(engine, random.choice(others), "poison", p_stacks)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_plasma_arrow")
class NinjaPlasmaArrowCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        _, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, int(getattr(self, "base_dmg", 14) or 14), source="p0", damage_type="lightning", card=self, is_attack=True)
        add_ninja_buff(engine, run.player, "plasma_arrow", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_shadow_blade")
class NinjaShadowBladeCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        enemy, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, int(getattr(self, "base_dmg", 12) or 12), source="p0", damage_type="physical", card=self, is_attack=True)
        if enemy is not None:
            add_ninja_buff(engine, enemy, "vulnerable", 2)
        if run.player.hand:
            run.player.exhaust_pile.append(run.player.hand.pop(random.randrange(len(run.player.hand))))
            if ref:
                engine.combat_resolver.damage_target(run, ref, 9 if self.upgraded else 6, source="p0", damage_type="physical", card=self, is_attack=True)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_sharpen_to_kill")
class NinjaSharpenToKillCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        _, ref = resolve_enemy_obj(run, target)
        if ref:
            engine.combat_resolver.damage_target(run, ref, int(getattr(self, "base_dmg", 9) or 9), source="p0", damage_type="physical", card=self, is_attack=True)
        add_ninja_buff(engine, run.player, "blade_power_up", 5 if self.upgraded else 3)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_snake_switch")
class NinjaSnakeSwitchCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        p = run.player
        for idx in random.sample(range(len(p.hand)), min(2, len(p.hand))):
            p.hand[idx] = CardState(id="ninja_angry_snake_bite", upgraded=self.upgraded)
        engine.card_player.draw_cards(p, 2, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_swallow_steps")
class NinjaSwallowStepsCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        engine.card_player.draw_cards(run.player, 1, run)
        if run.node_data.get("ninja_last_was_ninjutsu"):
            engine.card_player.draw_cards(run.player, 2 if self.upgraded else 1, run)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_true_leech_friend")
class NinjaTrueLeechFriendCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        me = run.player
        my_cnt = int(run.node_data.get(run.turn_key("cards_played_this_turn", me), 0) or 0)
        gain = 5 if self.upgraded else 3
        for uid in run.party_order:
            ally = run.players.get(uid)
            if ally is None or ally is me or ally.downed:
                continue
            ally_cnt = int(run.node_data.get(run.turn_key("cards_played_this_turn", ally), 0) or 0)
            if ally_cnt < my_cnt:
                add_ninja_buff(engine, me, "strength", gain)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_turbine")
class NinjaTurbineCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "turbine", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_water_sand_storm")
class NinjaWaterSandStormCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 2, self.id)
        if ok:
            add_ninja_buff(engine, run.player, "sand_wall", 12 if self.upgraded else 8)
        sw = next((b.stacks for b in run.player.buffs if b.id == "sand_wall"), 0)
        if sw > 0:
            deal_all_enemies(engine, run, self, sw, "physical")
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_we_peace")
class NinjaWePeaceCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        ok, _ = consume_ninjutsu_lex(engine, run, run.player, 1, self.id)
        if ok and not any(b.id == "intangible" and b.stacks > 0 for b in run.player.buffs):
            add_ninja_buff(engine, run.player, "intangible", 1)
            add_ninja_buff(engine, run.player, "we_peace", 1)
            self.exhaust = True
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)


@register_card("ninja_wild_snake_god")
class NinjaWildSnakeGodCard(NinjaCard):
    def execute(self, run, target, engine) -> str:
        add_ninja_buff(engine, run.player, "wild_snake_god", 1)
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)
