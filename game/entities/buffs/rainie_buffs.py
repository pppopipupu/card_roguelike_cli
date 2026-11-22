import copy
import math
import random
from typing import Optional

from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.battle.damage_type_data import is_physical_damage
from ...data.text.locale_data import get_locale_text
from ...models.state import BuffState, EnemyIntentState, EnemyState, PlayerState, ensure_card_state
from .base import BuffImpl, is_positive_buff
from .registry import register_buff


def _stat(instance, buff_id: str, key: str, default):
    return getattr(instance, key, BUFF_CONFIG.get(buff_id, {}).get(key, default))


def _owner(run, buff_state) -> PlayerState:
    uid = str(getattr(buff_state, "source_uid", "") or "")
    if uid and uid in run.players:
        return run.players[uid]
    return run.player


def _owner_ref(run, buff_state) -> str:
    uid = str(getattr(buff_state, "source_uid", "") or "")
    if not uid or uid not in run.players:
        return "p0"
    from ...core.battle.party_battle import party_target_ref
    return party_target_ref(run, uid)


def _enemy_ref(run, entity) -> str:
    if entity in run.enemies:
        return f"e{run.enemies.index(entity) + 1}"
    return ""


def _is_player_source(source: str) -> bool:
    if source in ("player", "effect") or source.startswith("player:"):
        return True
    return len(source) > 1 and source[0] in ("p", "a") and source[1:].isdigit()


def _source_enemy(run, source: str) -> Optional[EnemyState]:
    if source.startswith("e"):
        try:
            idx = int(source[1:]) - 1
        except ValueError:
            return None
        if 0 <= idx < len(run.enemies):
            return run.enemies[idx]
    if source.startswith("enemy:"):
        name = source[6:]
        for enemy in run.enemies:
            if enemy.name == name:
                return enemy
    return None


def _buff_name(buff_id: str) -> str:
    return str(BUFF_CONFIG.get(buff_id, {}).get("name", buff_id))


def _buff_desc(buff_id: str) -> str:
    return str(BUFF_CONFIG.get(buff_id, {}).get("desc", ""))


@register_buff("sleep_rain")
class SleepRainBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies:
            return
        buff_state.stacks -= 1
        if buff_state.stacks <= 0 and buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        entity.actions = 0
        entity.bonus_actions = 0
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.sleep_rain", name=entity.name))

    def on_enemy_sync_intents(self, event, buff_state, entity):
        entity.actions = 0
        entity.bonus_actions = 0
        entity.intents = [
            EnemyIntentState(
                type="stun",
                val=0,
                desc=get_locale_text("i18n_rainie.buff.sleep_rain.intent"),
                cost_a=0,
                cost_ba=0,
            )
        ]

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if entity not in event.run.enemies or event.target != _enemy_ref(event.run, entity):
            return
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype in ("cold", "psychic"):
            mult = _stat(self, "sleep_rain", "nightmare_multiplier", 1.5)
            event.modified_damage = int(event.modified_damage * mult)

    def on_damage_take_defend(self, event, buff_state, entity, engine=None):
        engine = event.engine
        if entity not in event.run.enemies or event.amount <= 0 or entity.hp <= 0:
            return
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if not (is_physical_damage(dtype) or dtype in ("fire", "thunder")):
            return
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        strength = _stat(self, "sleep_rain", "wake_strength", 3)
        engine._add_buff_to(entity, "strength", _buff_name("strength"), _buff_desc("strength"), strength)
        engine._log_event(event.run, get_locale_text("i18n_rainie.log.sleep_wake", name=entity.name, strength=strength))
        engine._sync_enemy_intents(entity)


@register_buff("eight_k_sharp")
class EightKSharpBuff(BuffImpl):
    def on_before_damage_apply(self, event, buff_state, entity, engine=None):
        engine = event.engine
        if entity != event.run.player or not _is_player_source(event.source):
            return
        if event.final_damage <= 0:
            return
        step = max(1, int(_stat(self, "eight_k_sharp", "round_to", 10)))
        event.final_damage = int(math.ceil(event.final_damage / step) * step)


@register_buff("breath_osmosis")
class BreathOsmosisBuff(BuffImpl):
    def on_shield_gain(self, event, buff_state, entity):
        if entity not in event.run.enemies or event.target != _enemy_ref(event.run, entity):
            return
        amount = int(event.modified_amount)
        if amount <= 0:
            return
        event.modified_amount = 0
        event.engine._gain_shield(event.run, _owner_ref(event.run, buff_state), amount)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.breath_shield", name=entity.name, amount=amount))

    def on_heal(self, event, buff_state, entity):
        if entity not in event.run.enemies or event.target != _enemy_ref(event.run, entity):
            return
        amount = int(event.amount)
        if amount <= 0:
            return
        event.cancelled = True
        event.engine._heal_target(event.run, _owner_ref(event.run, buff_state), amount)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.breath_heal", name=entity.name, amount=amount))

    def on_buff_gain(self, event, buff_state, entity):
        if event.entity is not entity or entity not in event.run.enemies:
            return
        if not is_positive_buff(event.buff_id):
            return
        event.cancelled = True
        owner = _owner(event.run, buff_state)
        event.engine._add_buff_to(owner, event.buff_id, event.buff_name, event.desc, event.count, event.count2)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.breath_buff", name=entity.name, buff=event.buff_name))

    def on_turn_end(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0:
            return
        ratio = float(_stat(self, "breath_osmosis", "drain_ratio", 0.1))
        cap = int(_stat(self, "breath_osmosis", "drain_cap", 25))
        amount = min(cap, int(entity.hp * ratio))
        if amount <= 0:
            return
        ref = _enemy_ref(event.run, entity)
        before = int(entity.hp)
        if ref:
            event.engine._damage_target(event.run, ref, amount, source=_owner_ref(event.run, buff_state), damage_type="true")
        actual = max(0, before - int(entity.hp))
        if actual > 0:
            event.engine._heal_target(event.run, _owner_ref(event.run, buff_state), actual)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.breath_drain", name=entity.name, amount=actual))


@register_buff("emo_love_brain")
class EmoLoveBrainBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity != event.run.player or getattr(event.card, "lyrics", False):
            return
        state = getattr(event.card, "card_state", None)
        if state is None:
            return
        event.run.node_data[event.run.turn_key("rainie_last_non_lyric", entity)] = copy.copy(state)

    def on_turn_end(self, event, buff_state, entity):
        if not event.is_player or entity != event.run.player:
            return
        current_key = event.run.turn_key("rainie_last_non_lyric", entity)
        prev_key = event.run.turn_key("rainie_prev_non_lyric", entity)
        state = event.run.node_data.pop(current_key, None)
        if state is not None:
            event.run.node_data[prev_key] = state

    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player or entity != event.run.player:
            return
        state = event.run.node_data.pop(event.run.turn_key("rainie_prev_non_lyric", entity), None)
        if state is None:
            return
        illusion = copy.copy(ensure_card_state(state))
        illusion.temp_cost_a = 0
        illusion.temp_cost_ba = 0
        illusion.temp_ethereal = True
        illusion.temp_exhaust = True
        entity.hand.append(illusion)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.emo_return", name=get_locale_text("i18n_rainie.effects.ghost_name")))


@register_buff("missing_ex")
class MissingExBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0:
            return
        ref = _enemy_ref(event.run, entity)
        damage = max(0, int(buff_state.stacks)) * int(_stat(self, "missing_ex", "psychic_per_stack", 4))
        if damage > 0:
            event.engine._damage_target(event.run, ref, damage, source="buff:missing_ex", damage_type="psychic")
            event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.missing_damage", name=entity.name, damage=damage))
        if entity not in event.run.enemies or entity.hp <= 0:
            return
        chance = float(_stat(self, "missing_ex", "confuse_chance", 0.35))
        if random.random() < chance:
            turns = int(_stat(self, "missing_ex", "confuse_turns", 1))
            event.engine._add_buff_to(entity, "confusion", _buff_name("confusion"), _buff_desc("confusion"), turns)
            event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.missing_confuse", name=entity.name))

    def on_unit_death(self, event, buff_state, entity):
        if entity not in event.run.enemies or entity.hp <= 0:
            return
        buff_state.stacks = max(1, int(buff_state.stacks) * 2)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.missing_double", name=entity.name, stacks=buff_state.stacks))


@register_buff("transparent_wrap")
class TransparentWrapBuff(BuffImpl):
    def on_shield_gain(self, event, buff_state, entity):
        if entity not in event.run.enemies or event.target != _enemy_ref(event.run, entity):
            return
        amount = int(event.modified_amount)
        if amount <= 0:
            return
        leaked = int(amount * float(_stat(self, "transparent_wrap", "leak_ratio", 0.5)))
        event.modified_amount = max(0, amount - leaked)
        if leaked > 0:
            event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.transparent_leak", name=entity.name, amount=leaked))

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if entity not in event.run.enemies or event.target != _enemy_ref(event.run, entity):
            return
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        eligible = (
            _is_player_source(event.source)
            and int(entity.shield) <= 0
            and is_physical_damage(dtype)
            and event.modified_damage > 0
        )
        buff_state.stacks2 = 1 if eligible else 0

    def on_damage_take_defend(self, event, buff_state, entity, engine=None):
        engine = event.engine
        if not buff_state.stacks2 or event.amount <= 0 or event.source == "buff:transparent_wrap":
            return
        buff_state.stacks2 = 0
        extra = max(1, int(event.amount * float(_stat(self, "transparent_wrap", "true_bonus", 0.25))))
        ref = _enemy_ref(event.run, entity)
        if not ref:
            return
        engine._damage_target(event.run, ref, extra, source="buff:transparent_wrap", damage_type="true")
        engine._log_event(event.run, get_locale_text("i18n_rainie.log.transparent_true", name=entity.name, damage=extra))


@register_buff("rainie_transparent")
class RainieTransparentBuff(BuffImpl):
    def on_enemy_target_select(self, event, buff_state, entity):
        uid = event.run.uid_for(entity)
        if not uid or uid not in event.candidates:
            return
        teammate_alive = len(event.candidates) > 1
        has_minion = any(minion.hp > 0 for minion in entity.minions.values())
        if (teammate_alive or has_minion) and uid not in event.excluded_uids:
            event.excluded_uids.append(uid)

    def on_turn_start(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player and buff_state in entity.buffs:
            entity.buffs.remove(buff_state)


@register_buff("rainie_courage")
class RainieCourageBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player or entity != event.run.player:
            return
        if entity.shield <= 0:
            entity.bonus_actions += int(_stat(self, "rainie_courage", "ba_gain", 1))
            removed = [
                b for b in entity.buffs
                if b.id in ("confusion", "tremor") or "vulnerable" in b.id
            ]
            if removed:
                entity.buffs[:] = [b for b in entity.buffs if b not in removed]
                event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.courage_immune"))

    def on_damage_calculate(self, event, buff_state, entity):
        if entity != event.run.player or not _is_player_source(event.source) or entity.shield > 0:
            return
        mult = float(_stat(self, "rainie_courage", "damage_bonus", 0.5))
        event.modified_damage = int(event.modified_damage * (1.0 + mult))

    def on_shield_gain(self, event, buff_state, entity):
        if entity != event.run.player or event.target != _owner_ref(event.run, buff_state):
            return
        amount = int(event.modified_amount)
        if amount <= 0:
            return
        entity.hp = max(1, entity.hp - 1)
        taunt = random.randint(1, 3)
        event.engine._log_event(event.run, get_locale_text(f"i18n_rainie.taunt.{taunt}"))

    def on_buff_gain(self, event, buff_state, entity):
        if event.entity is not entity or entity != event.run.player or entity.shield > 0:
            return
        if event.buff_id in ("confusion", "tremor") or "vulnerable" in event.buff_id:
            event.cancelled = True
            event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.courage_block", name=event.buff_name))


@register_buff("wet")
class WetBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        if entity not in event.run.enemies or event.target != _enemy_ref(event.run, entity):
            return
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype in ("cold", "lightning"):
            event.modified_damage = int(event.modified_damage * 2)


@register_buff("dripping")
class DrippingBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity not in event.run.enemies or entity.hp <= 0:
            return
        owner_uid = str(getattr(buff_state, "source_uid", "") or "")
        if owner_uid and event.run.uid_for(event.run.player) != owner_uid:
            return
        if buff_state.stacks2:
            buff_state.stacks2 = 0
            return
        stacks = max(1, int(buff_state.stacks))
        ref = _enemy_ref(event.run, entity)
        event.engine._damage_target(event.run, ref, stacks, source="p0", damage_type="cold")
        if entity in event.run.enemies and entity.hp > 0 and buff_state in entity.buffs:
            buff_state.stacks += 1
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.drip_hit", name=entity.name, damage=stacks))

    def on_turn_end(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0:
            return
        owner_uid = str(getattr(buff_state, "source_uid", "") or "")
        owner = event.run.players.get(owner_uid) if owner_uid else event.run.player
        if owner is None:
            return
        played = int(event.run.node_data.get(event.run.turn_key("cards_played_this_turn", owner), 0) or 0)
        if played >= int(_stat(self, "dripping", "threshold", 5)):
            buff_state.stacks = max(1, int(buff_state.stacks) * 2)
            event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.drip_double", name=entity.name, stacks=buff_state.stacks))


@register_buff("rainy_season")
class RainySeasonBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player or entity != event.run.player:
            return
        buff_state.stacks -= 1
        if buff_state.stacks <= 0 and buff_state in entity.buffs:
            entity.buffs.remove(buff_state)

    def on_damage_calculate(self, event, buff_state, entity):
        if entity != event.run.player or not event.target.startswith("e"):
            return
        if not _is_player_source(event.source):
            return
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype == "lightning":
            event.modified_damage = int(event.modified_damage * float(_stat(self, "rainy_season", "lightning_multiplier", 2.0)))

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if entity != event.run.player or event.target != "p0":
            return
        enemy = _source_enemy(event.run, event.source)
        if enemy is None:
            return
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype == "fire":
            event.modified_damage = int(event.modified_damage * float(_stat(self, "rainy_season", "fire_multiplier", 0.5)))
        chance = float(_stat(self, "rainy_season", "slip_chance", 0.4))
        if random.random() >= chance:
            return
        event.modified_damage = 0
        ref = _enemy_ref(event.run, enemy)
        if ref:
            damage = int(_stat(self, "rainy_season", "slip_damage", 15))
            event.engine._damage_target(event.run, ref, damage, source="buff:rainy_season", damage_type="bludgeoning")
            event.engine._add_buff_to(enemy, "tremor", _buff_name("tremor"), _buff_desc("tremor"), 1)
            event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.rainy_slip", name=enemy.name, damage=damage))


@register_buff("social_death")
class SocialDeathBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity not in event.run.enemies or _source_enemy(event.run, event.source) is None:
            return
        mult = 1.0 - float(_stat(self, "social_death", "damage_reduction", 0.25))
        event.modified_damage = int(event.modified_damage * mult)

    def on_damage_take_defend(self, event, buff_state, entity, engine=None):
        engine = event.engine
        if entity not in event.run.enemies or event.amount <= 0:
            return
        if not _is_player_source(event.source) or event.source == "buff:social_death":
            return
        extra = int(_stat(self, "social_death", "extra_psychic", 6))
        ref = _enemy_ref(event.run, entity)
        if extra > 0 and ref:
            engine._damage_target(event.run, ref, extra, source="buff:social_death", damage_type="psychic")
            engine._log_event(event.run, get_locale_text("i18n_rainie.log.social_extra", name=entity.name, damage=extra))
        from ...core.battle.rainie_runtime import check_social_death
        check = check_social_death(engine, event.run, entity, _owner(event.run, buff_state))
        if check:
            engine._log_event(event.run, check)

    def on_turn_start(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0:
            return
        from ...core.battle.rainie_runtime import check_social_death
        check = check_social_death(event.engine, event.run, entity, _owner(event.run, buff_state))
        if check:
            event.engine._log_event(event.run, check)


@register_buff("infinite_refill")
class InfiniteRefillBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if not event.is_player or entity != event.run.player:
            return
        event.run.node_data[event.run.turn_key("rainie_carried_a", entity)] = int(entity.actions)
        event.run.node_data[event.run.turn_key("rainie_carried_ba", entity)] = int(entity.bonus_actions)

    def on_shield_decay_calculate(self, event, buff_state, entity):
        event.decay_amount = 0

    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player or entity != event.run.player:
            return
        carried_a = int(event.run.node_data.pop(event.run.turn_key("rainie_carried_a", entity), 0) or 0)
        carried_ba = int(event.run.node_data.pop(event.run.turn_key("rainie_carried_ba", entity), 0) or 0)
        if carried_a or carried_ba:
            entity.actions += max(0, carried_a)
            entity.bonus_actions += max(0, carried_ba)
            event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.refill_carry", a=carried_a, ba=carried_ba))


@register_buff("rain_wish_replay_pending")
class RainWishReplayPendingBuff(BuffImpl):
    def on_card_play(self, event, buff_state, entity):
        if entity != event.run.player or getattr(event.card, "lyrics", False) or buff_state.stacks <= 0:
            return
        event.card.replay = int(getattr(event.card, "replay", 0) or 0) + int(buff_state.stacks)
        buff_state.stacks2 = 1
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.replay_pending", name=event.card.name, replay=buff_state.stacks))

    def on_card_played(self, event, buff_state, entity):
        if entity != event.run.player or not buff_state.stacks2:
            return
        buff_state.stacks2 = 0
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)

    def on_turn_end(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player and buff_state in entity.buffs:
            entity.buffs.remove(buff_state)


@register_buff("rain_wish_rain_pending")
class RainWishRainPendingBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity != event.run.player or not getattr(event.card, "lyrics", False):
            return
        if buff_state.stacks2:
            buff_state.stacks2 = 0
            return
        damage = int(_stat(self, "rain_wish_rain_pending", "rain_damage", 6))
        for idx in range(len(event.run.enemies) - 1, -1, -1):
            if idx < len(event.run.enemies) and event.run.enemies[idx].hp > 0:
                event.engine._damage_target(event.run, f"e{idx + 1}", damage, source="p0", damage_type="cold")
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.rain_wish_rain", damage=damage))

    def on_turn_end(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player and buff_state in entity.buffs:
            entity.buffs.remove(buff_state)


@register_buff("rain_wish_retain_hand")
class RainWishRetainHandBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if not event.is_player or entity != event.run.player:
            return
        for state in list(entity.hand):
            state.temp_retain = True
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.retain_hand"))


@register_buff("i_believe_you_will_die")
class IBelieveYouWillDieBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0:
            return
        buff_state.stacks -= 1
        if buff_state.stacks > 0:
            return
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        ref = _enemy_ref(event.run, entity)
        damage = int(_stat(self, "i_believe_you_will_die", "damage", 55))
        event.engine._damage_target(event.run, ref, damage, source="buff:i_believe_you_will_die", damage_type="true")
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.prophecy_damage", name=entity.name, damage=damage))
        if entity not in event.run.enemies or entity.hp <= 0:
            return
        owner = _owner(event.run, buff_state)
        failed = event.run.node_data.setdefault("rainie_prophecy_failed", [])
        uid = event.run.uid_for(owner)
        if uid in failed:
            return
        failed.append(uid)
        event.engine._add_buff_to(owner, "confusion", _buff_name("confusion"), _buff_desc("confusion"), int(_stat(self, "i_believe_you_will_die", "confuse_turns", 1)))
        owner.actions += int(_stat(self, "i_believe_you_will_die", "actions", 2))
        event.engine._draw_cards(owner, int(_stat(self, "i_believe_you_will_die", "draw", 3)), event.run)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.prophecy_failed"))


@register_buff("idealist_death_ward")
class IdealistDeathWardBuff(BuffImpl):
    def on_player_before_death(self, event, buff_state, entity):
        if buff_state.stacks <= 0:
            return
        buff_state.stacks -= 1
        if buff_state.stacks <= 0 and buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        entity.hp = 1
        shield_gain = int(BUFF_CONFIG.get("idealist_death_ward", {}).get("shield_on_save", 40))
        event.engine._gain_shield(event.run, "p0", shield_gain)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.idealist_ward_saved", name=entity.name))
        event.cancel()


@register_buff("rain_wish_free_pending")
class RainWishFreePendingBuff(BuffImpl):
    def on_card_play(self, event, buff_state, entity):
        if entity != event.run.player or buff_state.stacks <= 0:
            return
        event.cost_a = 0
        event.cost_ba = 0
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.free_next", name=event.card.name))


@register_buff("rainie_cross_battle")
class RainieCrossBattleBuff(BuffImpl):
    def on_battle_before_win_cleanup(self, event, buff_state, entity):
        player = event.player
        strength = sum(max(0, int(b.stacks)) for b in player.buffs if b.id == "strength")
        player.rainie_legacy_strength = min(15, strength)
        player.rainie_legacy_shield = min(40, max(0, player.shield) // 2)


@register_buff("rain_wish_amplify")
class RainWishAmplifyBuff(BuffImpl):
    hook_priorities = {"on_turn_end": 1000}

    def on_turn_end(self, event, buff_state, entity):
        if not event.is_player or entity is not event.run.player:
            return
        from ...core.battle.rainie_runtime import snapshot_all_buffs
        event.run.node_data["rain_wish_amplify_snapshot"] = snapshot_all_buffs(event.run)


@register_buff("rain_wish_amplify_post")
class RainWishAmplifyPostBuff(BuffImpl):
    hook_priorities = {"on_turn_end": -1000}

    def on_turn_end(self, event, buff_state, entity):
        if not event.is_player or entity is not event.run.player:
            return
        snapshot = event.run.node_data.pop("rain_wish_amplify_snapshot", None)
        if snapshot:
            from ...core.battle.rainie_runtime import amplify_all_buffs
            changed = amplify_all_buffs(event.run, snapshot)
            if changed:
                event.engine._log_event(event.run, get_locale_text("i18n_rainie.log.rain_wish_amplify", count=changed))
        for buff_id in ("rain_wish_amplify", "rain_wish_amplify_post"):
            for buff in list(entity.buffs):
                if buff.id == buff_id:
                    entity.buffs.remove(buff)


@register_buff("rain_wish_no_shield_decay")
class RainWishNoShieldDecayBuff(BuffImpl):
    def on_shield_decay_calculate(self, event, buff_state, entity):
        if entity is not event.run.player:
            return
        event.decay_amount = 0
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
