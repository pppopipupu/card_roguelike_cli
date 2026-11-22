from ...data.text.locale_data import get_locale_text
from ...models.state import CardState
from ..cards.ninja_base import add_ninja_buff, change_lex_kela
from .base import BuffImpl
from .registry import register_buff


@register_buff("shen_wei")
class ShenWeiBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        if int(getattr(entity, "lex_kela", 0) or 0) >= 1:
            change_lex_kela(engine, event.run, entity, -1, reason="shen_wei")
            add_ninja_buff(engine, entity, "intangible", 1)
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.shen_wei_trigger"))

    def on_card_played(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if entity is not event.run.player or buff.stacks <= 0 or event.card is None:
            return
        if getattr(event.card, "type", "") == "attack":
            for b in list(entity.buffs):
                if b.id == "intangible" and b.stacks > 0:
                    b.stacks -= 1
                    if b.stacks <= 0:
                        entity.buffs.remove(b)
                    engine._log_event(event.run, get_locale_text("i18n_cards_ninja.shen_wei_break"))
                    break


@register_buff("radiation")
class RadiationBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0 or buff.stacks <= 0:
            return
        loss = max(1, int(entity.max_hp * 0.25))
        entity.hp = max(0, entity.hp - loss)
        engine._log_event(event.run, get_locale_text("i18n_cards_ninja.radiation_tick", name=entity.name, loss=loss))
        buff.stacks -= 1
        if buff.stacks <= 0 and buff in entity.buffs:
            entity.buffs.remove(buff)


@register_buff("south_cross_seal")
class SouthCrossSealBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0 or buff.stacks <= 0:
            return
        entity.shield += 50
        add_ninja_buff(engine, entity, "stun", 1)
        buff.stacks -= 1
        if buff.stacks <= 0 and buff in entity.buffs:
            entity.buffs.remove(buff)

    def on_damage_take_defend(self, event, buff_state, entity, engine=None):
        engine = event.engine
        buff = buff_state
        if entity not in event.run.enemies or event.amount <= 0:
            return
        try:
            idx = event.run.enemies.index(entity)
        except ValueError:
            return
        if event.target == f"e{idx + 1}" and buff in entity.buffs:
            entity.buffs.remove(buff)
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.south_cross_break", name=entity.name))


@register_buff("we_peace")
class WePeaceBuff(BuffImpl):
    def on_card_play_check(self, event, buff_state, entity):
        if getattr(event.card, "type", "") != "attack":
            return
        event.cancel()
        event.error_message = get_locale_text("i18n_cards_ninja.we_peace_blocked")

    def on_turn_end(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if event.is_player and entity is event.run.player and buff in entity.buffs:
            entity.buffs.remove(buff)


@register_buff("ignis_healing")
class IgnisHealingBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        entity.hp = max(1, entity.hp - buff.stacks)
        engine._log_event(event.run, get_locale_text("i18n_cards_ninja.ignis_healing_tick", loss=buff.stacks))


@register_buff("good_night")
class GoodNightBuff(BuffImpl):
    def on_card_play_check(self, event, buff_state, entity):
        if buff_state.stacks <= 0:
            return
        event.cancel()
        event.error_message = get_locale_text("i18n_cards_ninja.good_night_blocked")

    def on_turn_end(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if event.is_player and entity is event.run.player:
            buff.stacks -= 1
            if buff.stacks <= 0 and buff in entity.buffs:
                entity.buffs.remove(buff)


@register_buff("scare_form")
class ScareFormBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        import random
        from ...data.cards.classes.ninja_card_data_basic import NINJA_CARD_CONFIG_BASIC
        from ...data.cards.classes.ninja_card_data_uncommon import NINJA_CARD_CONFIG_UNCOMMON
        from ..cards.base import ALL_CARDS
        pool = [
            k for k, v in {**NINJA_CARD_CONFIG_BASIC, **NINJA_CARD_CONFIG_UNCOMMON}.items()
            if "ninjutsu" in v.get("ninja_tags", ()) and k not in ("ninja_good_night", "ninja_he_bully_me", "ninja_we_peace")
        ]
        if not pool:
            return
        for _ in range(buff.stacks):
            cid = random.choice(pool)
            card = ALL_CARDS.get(cid)
            if card is None:
                continue
            add_ninja_buff(engine, entity, "free_ninjutsu", 1)
            target = engine._get_first_alive_enemy(event.run)
            engine._execute_card_effect(event.run, card, target)
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.scare_form_cast", name=card.name))


@register_buff("oh_fuck_flash")
class OhFuckFlashBuff(BuffImpl):
    pass


@register_buff("become_nong")
class BecomeNongBuff(BuffImpl):
    def on_battle_before_win_cleanup(self, event, buff_state, entity):
        engine = event.engine
        if entity is not event.run.player:
            return
        cid = event.run.node_data.pop("ninja_nong_card_id", "")
        if cid:
            from ..cards.base import ALL_CARDS
            st = CardState(id=cid)
            entity.deck.append(st)
            name = ALL_CARDS[st].name if cid in ALL_CARDS else cid
            engine._log_event(event.run, get_locale_text("i18n_cards_ninja.become_nong_win", name=name))


@register_buff("shit_power")
class ShitPowerBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        lex = int(buff.stacks)
        change_lex_kela(engine, event.run, entity, lex, reason="shit_power")
        entity.actions += 1
        engine._log_event(event.run, get_locale_text("i18n_cards_ninja.shit_power_tick", lex=lex))
        if buff in entity.buffs:
            entity.buffs.remove(buff)


@register_buff("damage_next_turn")
class DamageNextTurnBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        for i, e in enumerate(event.run.enemies, 1):
            if e.hp > 0:
                engine.combat_resolver.damage_target(event.run, f"e{i}", buff.stacks, source="p0", damage_type="effect")
        if buff in entity.buffs:
            entity.buffs.remove(buff)


@register_buff("pain")
class PainBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        buff = buff_state
        engine = event.engine
        if not event.is_player or entity is not event.run.player or buff.stacks <= 0:
            return
        entity.hp = max(1, entity.hp - buff.stacks)
