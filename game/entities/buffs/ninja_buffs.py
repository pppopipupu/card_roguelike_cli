import random
from ...data.buff_data import BUFF_CONFIG
from ...data.locale_data import get_locale_text
from ...models.state import CardState
from ..cards.ninja_base import add_lan_blade_to_hand, add_ninja_buff, change_lex_kela, has_ninja_tag, scramble_hand_costs
from .base import BuffImpl
from .registry import register_buff


@register_buff("sand_wall")
class SandWallBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        run = event.run
        gain = int(buff.stacks)
        engine.combat_resolver.gain_shield(run, "p0", gain)
        has_build = any(b.id == "build_sand_wall" and b.stacks > 0 for b in entity.buffs)
        buff.stacks = max(0, buff.stacks - 1) if has_build else (buff.stacks // 2)
        engine._log_event(run, get_locale_text("i18n_cards_ninja.sand_wall_trigger", shield=gain, left=buff.stacks))
        if buff.stacks <= 0 and buff in entity.buffs:
            entity.buffs.remove(buff)


@register_buff("build_sand_wall")
class BuildSandWallBuff(BuffImpl):
    pass


@register_buff("stone_strong")
class StoneStrongBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        add_ninja_buff(engine, entity, "sand_wall", buff.stacks)
        engine._log_event(event.run, get_locale_text("i18n_cards_ninja.stone_strong_tick", amount=buff.stacks))


@register_buff("nuclear_dragon")
class NuclearDragonBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player:
            return
        if int(getattr(entity, "lex_kela", 0) or 0) > 0:
            entity.lex_kela = 0
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.nuclear_dragon_clear"))

    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        gained = change_lex_kela(engine, event.run, entity, buff.stacks, reason="nuclear_dragon")
        if gained > 0:
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.nuclear_dragon_gain", amount=gained))


@register_buff("heaven_cross")
class HeavenCrossBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        if has_ninja_tag(event.card, "ninjutsu"):
            gained = change_lex_kela(engine, event.run, entity, buff.stacks, reason="heaven_cross")
            if gained > 0:
                engine._log_event(event.run, get_locale_text("i18n_cards_ninja.heaven_cross_lex", amount=gained))


@register_buff("mummy_power")
class MummyPowerBuff(BuffImpl):
    pass


@register_buff("i_represent_shinobi")
class IRepresentShinobiBuff(BuffImpl):
    pass


@register_buff("free_ninjutsu")
class FreeNinjutsuBuff(BuffImpl):
    pass


@register_buff("no_lexkela")
class NoLexKelaBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player:
            return
        buff.stacks -= 1
        if buff.stacks <= 0 and buff in entity.buffs:
            entity.buffs.remove(buff)


@register_buff("man_too_weak")
class ManTooWeakBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        lost = -change_lex_kela(engine, event.run, entity, -buff.stacks, reason="man_too_weak")
        if lost > 0:
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.man_too_weak_tick", loss=lost))


@register_buff("turbine")
class TurbineBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        if getattr(event.card, "science", False) or has_ninja_tag(event.card, "science"):
            engine.card_player.draw_cards(entity, buff.stacks, event.run)
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.turbine_draw", count=buff.stacks))


@register_buff("science_double")
class ScienceDoubleBuff(BuffImpl):
    pass


@register_buff("blade_power_up")
class BladePowerUpBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or event.source != "p0" or buff.stacks <= 0:
            return
        if has_ninja_tag(event.card, "blade"):
            event.modified_damage += buff.stacks


@register_buff("lan_blade_cutting")
class LanBladeCuttingBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        if event.card is not None and event.card.id != "ninja_lan_blade" and has_ninja_tag(event.card, "blade"):
            for _ in range(buff.stacks):
                add_lan_blade_to_hand(engine, event.run, entity, upgraded=bool(buff.stacks2))


@register_buff("blade_defence")
class BladeDefenceBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        if event.card is not None and getattr(event.card, "type", "") == "attack":
            engine.combat_resolver.gain_shield(event.run, "p0", buff.stacks)

    def on_damage_take_defend(self, event, buff_state, entity, engine):
        buff = buff_state
        if entity is event.run.player and buff.stacks > 0 and event.target == "p0" and event.amount == 0:
            change_lex_kela(engine, event.run, entity, 1, reason="blade_defence")
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.blade_defence_lex"))

    def on_turn_end(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if event.is_player and entity is event.run.player and buff in entity.buffs:
            entity.buffs.remove(buff)


@register_buff("inferno_dragon")
class InfernoDragonBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or event.source != "p0" or buff.stacks <= 0:
            return
        if event.is_attack or (event.card is not None and getattr(event.card, "type", "") == "attack"):
            lex = max(0, int(getattr(entity, "lex_kela", 0) or 0))
            if lex > 0:
                event.modified_damage = int(round(event.modified_damage * (1.0 + (buff.stacks * lex) / 100.0)))


@register_buff("reaper_flame")
class ReaperFlameBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        for e in event.run.enemies:
            if e.hp > 0:
                e.hp = max(0, e.hp - buff.stacks)
        engine._log_event(event.run, get_locale_text("i18n_cards_ninja.reaper_flame_tick", dmg=buff.stacks))


@register_buff("get_all_hands")
class GetAllHandsBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        if event.card is not None and event.card.id == "ninja_get_all_hands":
            return
        if has_ninja_tag(event.card, "hand"):
            entity.actions += 1
            engine.card_player.draw_cards(entity, 1, event.run)
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.get_all_hands_trigger"))
        else:
            if buff in entity.buffs:
                entity.buffs.remove(buff)
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.get_all_hands_break"))

    def on_turn_end(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if event.is_player and entity is event.run.player and buff in entity.buffs:
            entity.buffs.remove(buff)


@register_buff("plasma_arrow")
class PlasmaArrowBuff(BuffImpl):
    pass


@register_buff("disappointed")
class DisappointedBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or event.source != "p0" or buff.stacks <= 0:
            return
        if event.is_attack or (event.card is not None and getattr(event.card, "type", "") == "attack"):
            event.modified_damage *= 3

    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        if event.card is not None and getattr(event.card, "type", "") == "attack":
            buff.stacks -= 1
            if buff.stacks <= 0 and buff in entity.buffs:
                entity.buffs.remove(buff)
            weak_cfg = BUFF_CONFIG["weak"]
            engine._add_buff_to(entity, "weak", weak_cfg["name"], weak_cfg["desc"], 1)


@register_buff("double_damage")
class DoubleDamageBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or event.source != "p0" or buff.stacks <= 0:
            return
        if event.is_attack or (event.card is not None and getattr(event.card, "type", "") == "attack"):
            event.modified_damage *= 2

    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        if event.card is not None and getattr(event.card, "type", "") == "attack":
            buff.stacks -= 1
            if buff.stacks <= 0 and buff in entity.buffs:
                entity.buffs.remove(buff)


@register_buff("infinite_snake_bites")
class InfiniteSnakeBitesBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        max_hand = 9 if "mask_of_void" in entity.relics else 12
        for _ in range(buff.stacks):
            st = CardState(id="ninja_angry_snake_bite", upgraded=True)
            if len(entity.hand) < max_hand:
                entity.hand.append(st)
            else:
                entity.discard_pile.append(st)
        engine._log_event(event.run, get_locale_text("i18n_cards_ninja.infinite_snake_tick"))


@register_buff("wild_snake_god")
class WildSnakeGodBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        if event.card is not None and event.card.id == "ninja_wild_snake_god":
            return
        scramble_hand_costs(entity, 0, 3)
        engine._log_event(event.run, get_locale_text("i18n_cards_ninja.wild_snake_god_trigger"))


@register_buff("black_snake_heart")
class BlackSnakeHeartBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0 or event.card is None:
            return
        prev_id = event.run.node_data.get("ninja_prev_played_card_id", "")
        if prev_id and prev_id == event.card.id:
            for st in reversed(list(entity.discard_pile)):
                if st.id == event.card.id:
                    entity.discard_pile.remove(st)
                    entity.exhaust_pile.append(st)
                    break
            add_ninja_buff(engine, entity, "intangible", buff.stacks)
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.black_snake_heart_trigger"))


@register_buff("alan_walker")
class AlanWalkerBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0:
            return
        for e in event.run.enemies:
            if e.hp > 0:
                e.hp = max(0, e.hp - 6 * buff.stacks)
        entity.shield += 7 * buff.stacks
        engine._log_event(event.run, get_locale_text("i18n_cards_ninja.alan_walker_tick"))
