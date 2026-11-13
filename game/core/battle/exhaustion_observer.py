from ...data.grid_map_config import EXHAUSTION_CONFIG
from ...data.locale_data import get_locale_text
from ...models.events import (
    BattleStartEvent,
    BeforeDamageApplyEvent,
    DamageCalculateEvent,
    HealCalculateEvent,
    ShieldGainEvent,
    TurnStartEvent,
)
from ...data.damage_type_data import is_spell_card_damage


class ExhaustionObserver:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(ShieldGainEvent, self.on_shield_gain)
        event_bus.subscribe(HealCalculateEvent, self.on_heal_calculate)
        event_bus.subscribe(BeforeDamageApplyEvent, self.on_before_damage_apply)

    def modify_initial_draw(self, player, draw_count: int) -> int:
        ex = int(getattr(player, "exhaustion", 0) or 0)
        if ex >= 1:
            draw_count -= EXHAUSTION_CONFIG.get("level1_draw_penalty", 1)
        if ex >= 4:
            draw_count -= EXHAUSTION_CONFIG.get("level4_draw_penalty", 1)
        return max(1, draw_count)

    def on_battle_start(self, event):
        p = event.run.player
        ex = int(getattr(p, "exhaustion", 0) or 0)
        if ex >= 4:
            divisor = EXHAUSTION_CONFIG.get("level4_max_hp_divisor", 2)
            cap = max(1, p.max_hp // divisor)
            if p.hp > cap:
                p.hp = cap
            self.engine._log_event(event.run, get_locale_text("i18n_grid_map.exhaustion_battle_max_hp_log", max_hp=cap))

    def on_turn_start(self, event):
        if not event.is_player:
            return
        p = event.run.player
        ex = int(getattr(p, "exhaustion", 0) or 0)
        if ex >= 3:
            ba_loss = EXHAUSTION_CONFIG.get("level3_ba_loss", 1)
            p.bonus_actions = max(0, p.bonus_actions - ba_loss)
            self.engine._log_event(event.run, get_locale_text("i18n_grid_map.exhaustion_turn_ba_log", loss=ba_loss))
        if ex >= 4 and event.run.node_data.get("turn_count", 1) >= 2:
            pen = EXHAUSTION_CONFIG.get("level4_draw_penalty", 1)
            event.run.node_data["draw_penalty_next_turn"] = event.run.node_data.get("draw_penalty_next_turn", 0) + pen

    def on_damage_calculate(self, event):
        if event.source not in ("p0", "player", "effect"):
            return
        p = event.run.player
        ex = int(getattr(p, "exhaustion", 0) or 0)
        if ex >= 3 and (getattr(event, "is_attack", False) or is_spell_card_damage(event) or event.card is not None):
            mult = EXHAUSTION_CONFIG.get("level3_damage_multiplier", 0.80)
            event.modified_damage = int(event.modified_damage * mult)

    def on_shield_gain(self, event):
        if event.target != "p0":
            return
        p = event.run.player
        ex = int(getattr(p, "exhaustion", 0) or 0)
        if ex >= 2 and event.modified_amount > 0:
            mult = EXHAUSTION_CONFIG.get("level2_shield_multiplier", 0.75)
            event.modified_amount = int(event.modified_amount * mult)

    def on_heal_calculate(self, event):
        if event.target != "p0":
            return
        p = event.run.player
        ex = int(getattr(p, "exhaustion", 0) or 0)
        if ex >= 4:
            divisor = EXHAUSTION_CONFIG.get("level4_max_hp_divisor", 2)
            event.modified_max_hp = min(event.modified_max_hp, max(1, p.max_hp // divisor))

    def on_before_damage_apply(self, event):
        if event.target != "p0" or event.final_damage <= 0:
            return
        p = event.run.player
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype.lower() == "true" and "ghost_body" in getattr(p, "relics", []):
            event.final_damage = 0
            self.engine._log_event(event.run, get_locale_text("i18n_grid_map.ghost_body_immune_log", name=p.name))
            return
        if any(b.id == "intangible" for b in getattr(p, "buffs", [])):
            if event.final_damage > 1:
                event.final_damage = 1
                self.engine._log_event(event.run, get_locale_text("i18n_grid_map.intangible_cap_log"))
