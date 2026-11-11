from ...data.locale_data import get_locale_text
from ...data.relic_data import RELIC_CONFIG
from ...models.events import CardPlayedEvent
from .base import RelicImpl
from .registry import register_relic


@register_relic("blood_covenant")
class BloodCovenantRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.bonus_actions = cfg.get("bonus_actions", 1)
        self.max_hp_threshold = cfg.get("max_hp_threshold", 35)
        self.shield_gain = cfg.get("shield_gain", 20)
        self.strength_gain = cfg.get("strength_gain", 2)

    def on_battle_start(self, run, engine):
        p = run.player
        if p.max_hp <= self.max_hp_threshold:
            engine._gain_shield(run, "p0", self.shield_gain)
            engine._add_buff_to(
                p,
                "strength",
                get_locale_text("i18n_battle_core.buff_strength_name"),
                get_locale_text("i18n_battle_core.buff_strength_desc"),
                self.strength_gain,
            )
            engine._log_event(
                run,
                get_locale_text(
                    "i18n_relics_amulets.mythic.blood_covenant.battle_start",
                    threshold=self.max_hp_threshold,
                    shield=self.shield_gain,
                    strength=self.strength_gain,
                ),
            )

    def on_turn_start(self, event, run, engine):
        if event.is_player:
            run.player.bonus_actions += self.bonus_actions
            engine._log_event(run, get_locale_text("i18n_relics_amulets.mythic.blood_covenant.turn_start"))


@register_relic("sanguine_crown")
class SanguineCrownRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_ratio = cfg.get("shield_ratio", 0.5)
        self.min_shield = cfg.get("min_shield", 15)

    def on_battle_start(self, run, engine):
        p = run.player
        shield = max(self.min_shield, int(p.hp * self.shield_ratio))
        engine._gain_shield(run, "p0", shield)
        engine._log_event(
            run,
            get_locale_text("i18n_relics_amulets.mythic.sanguine_crown.battle_start", shield=shield),
        )

    def on_turn_start(self, event, run, engine):
        if event.is_player:
            run.node_data[run.turn_key("sanguine_crown_used")] = False

    def on_card_played(self, event, run, engine):
        if getattr(event, "is_extra", False):
            return
        if getattr(event.card, "unplayable", False):
            return
        used_key = run.turn_key("sanguine_crown_used")
        if run.node_data.get(used_key):
            return
        run.node_data[used_key] = True
        if engine.is_battle_won(run):
            return
        extra_res = engine._execute_card_effect(run, event.card, event.target)
        played_evt = CardPlayedEvent(run, event.card, event.target, extra_res, is_extra=True)
        engine.event_bus.dispatch(played_evt)
        run.node_data.setdefault("extra_play_msgs", []).append(
            get_locale_text(
                "i18n_relics_amulets.mythic.sanguine_crown.extra_play",
                name=event.card.name,
                feedback=played_evt.feedback,
            )
        )


@register_relic("immortal_pact")
class ImmortalPactRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.revive_hp = cfg.get("revive_hp", 1)
        self.revive_shield = cfg.get("revive_shield", 30)
        self.exhaust_shield = cfg.get("exhaust_shield", 4)

    def _used_key(self, run) -> str:
        return f"immortal_pact_used:{run.uid_for(run.player)}"

    def on_battle_start(self, run, engine):
        run.node_data[self._used_key(run)] = False

    def on_damage_take(self, event, run, engine):
        if event.target != "p0" or not event.is_fatal:
            return
        key = self._used_key(run)
        if run.node_data.get(key):
            return
        run.node_data[key] = True
        p = run.player
        p.hp = min(p.max_hp, self.revive_hp) if p.max_hp > 0 else self.revive_hp
        p.downed = False
        run.node_data.pop("death_cause", None)
        engine._gain_shield(run, "p0", self.revive_shield)
        engine._log_event(
            run,
            get_locale_text("i18n_relics_amulets.mythic.immortal_pact.revive", shield=self.revive_shield),
        )

    def on_card_played(self, event, run, engine):
        if getattr(event, "is_extra", False):
            return
        card = event.card
        if getattr(card, "exhaust", False) or getattr(card, "fleeting", False):
            engine._gain_shield(run, "p0", self.exhaust_shield)
            engine._log_event(
                run,
                get_locale_text("i18n_relics_amulets.mythic.immortal_pact.exhaust_shield", shield=self.exhaust_shield),
            )
