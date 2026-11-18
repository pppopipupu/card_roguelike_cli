from ...data.buff_data import BUFF_CONFIG
from ...data.locale_data import get_locale_text
from ...data.relic_data import RELIC_CONFIG
from .base import RelicImpl
from .registry import register_relic


def _add_buff(engine, player, buff_id: str, stacks: int):
    if stacks <= 0 or player is None:
        return
    cfg = BUFF_CONFIG.get(buff_id, {})
    engine._add_buff_to(player, buff_id, cfg.get("name", buff_id), cfg.get("desc", ""), stacks)


@register_relic("headband_of_intellect_int19")
class HeadbandOfIntellectInt19Relic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.initial_draw_bonus = int(cfg.get("initial_draw_bonus", 1))
        self.initial_overcharge = int(cfg.get("initial_overcharge", 2))
        self.even_turn_draw = int(cfg.get("even_turn_draw", 1))
        self.even_turn_overcharge = int(cfg.get("even_turn_overcharge", 1))

    def modify_initial_draw(self, run, draw_count: int, engine) -> int:
        return draw_count + self.initial_draw_bonus

    def on_battle_start(self, run, engine):
        _add_buff(engine, run.player, "fusion_overcharge", self.initial_overcharge)
        engine._log_event(run, get_locale_text("i18n_chireiden.card_results.relic_int19_battle", stacks=self.initial_overcharge))

    def on_turn_start(self, event, run, engine):
        if not event.is_player:
            return
        turn_count = int(run.node_data.get("turn_count", 1) or 1)
        if turn_count > 1 and turn_count % 2 == 0:
            engine._draw_cards(run.player, self.even_turn_draw, run)
            _add_buff(engine, run.player, "fusion_overcharge", self.even_turn_overcharge)
            engine._log_event(
                run,
                get_locale_text(
                    "i18n_chireiden.card_results.relic_int19_even",
                    draw=self.even_turn_draw,
                    stacks=self.even_turn_overcharge,
                ),
            )


@register_relic("lbe_fast_reactor_core")
class LbeFastReactorCoreRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.start_shield = int(cfg.get("start_shield", 10))
        self.start_confinement = int(cfg.get("start_confinement", 2))
        self.end_turn_heal = int(cfg.get("end_turn_heal", 4))

    def on_battle_start(self, run, engine):
        engine._gain_shield(run, "p0", self.start_shield)
        _add_buff(engine, run.player, "magnetic_confinement", self.start_confinement)
        engine._log_event(
            run,
            get_locale_text(
                "i18n_chireiden.card_results.relic_lbe_start",
                shield=self.start_shield,
                stacks=self.start_confinement,
            ),
        )

    def on_turn_end(self, event, run, engine):
        if not event.is_player or run.player.hp <= 0 or run.player.shield <= 0:
            return
        engine._heal_target(run, "p0", self.end_turn_heal)
        engine._log_event(run, get_locale_text("i18n_chireiden.card_results.relic_lbe_heal", heal=self.end_turn_heal))


@register_relic("lunar_he3_capsule")
class LunarHe3CapsuleRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.card_overcharge = int(cfg.get("card_overcharge", 2))
        self.action_bonus = int(cfg.get("action_bonus", 1))

    def on_battle_start(self, run, engine):
        run.player.actions += self.action_bonus
        engine._log_event(run, get_locale_text("i18n_chireiden.card_results.relic_he3_action", gain_a=self.action_bonus))

    def on_turn_start(self, event, run, engine):
        if not event.is_player:
            return
        turn_count = int(run.node_data.get("turn_count", 1) or 1)
        if turn_count == 3:
            run.player.actions += self.action_bonus
            engine._log_event(run, get_locale_text("i18n_chireiden.card_results.relic_he3_action", gain_a=self.action_bonus))

    def on_card_play(self, event, run, engine):
        uid = run.uid_for(run.player) or run.user_id
        turn_count = int(run.node_data.get("turn_count", 1) or 1)
        used = run.node_data.setdefault("lunar_he3_used_turn", {})
        key = f"{turn_count}:{uid}"
        if used.get(key):
            return
        used[key] = True
        _add_buff(engine, run.player, "fusion_overcharge", self.card_overcharge)
        engine._log_event(run, get_locale_text("i18n_chireiden.card_results.relic_he3_charge", stacks=self.card_overcharge))


@register_relic("penning_ion_stabilizer")
class PenningIonStabilizerRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.first_hit_reduction_pct = int(cfg.get("first_hit_reduction_pct", 25))
        self.reactive_shield = int(cfg.get("reactive_shield", 5))
        self.start_confinement = int(cfg.get("start_confinement", 1))

    def on_battle_start(self, run, engine):
        from ...core.inventory.relic_service import set_relic_counter
        set_relic_counter(run.player, f"{self.relic_id}_first_hit", 0)
        _add_buff(engine, run.player, "magnetic_confinement", self.start_confinement)
        engine._log_event(run, get_locale_text("i18n_chireiden.card_results.relic_penning_start", stacks=self.start_confinement))

    def on_damage_calculate_defend(self, event, run, engine):
        if event.target != "p0" or event.modified_damage <= 0:
            return
        from ...core.inventory.relic_service import get_relic_counter
        if get_relic_counter(run.player, f"{self.relic_id}_first_hit") == 0:
            event.modified_damage = max(0, (event.modified_damage * (100 - self.first_hit_reduction_pct)) // 100)

    def on_damage_take_defend(self, event, run, engine):
        if event.target != "p0" or not str(getattr(event, "source", "")).startswith("e"):
            return
        from ...core.inventory.relic_service import get_relic_counter, set_relic_counter
        if get_relic_counter(run.player, f"{self.relic_id}_first_hit") == 0:
            set_relic_counter(run.player, f"{self.relic_id}_first_hit", 1)
        if self.reactive_shield > 0:
            engine._gain_shield(run, "p0", self.reactive_shield)
            engine._log_event(run, get_locale_text("i18n_chireiden.card_results.relic_penning_guard", shield=self.reactive_shield))
