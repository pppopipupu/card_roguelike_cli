import re
from ...data.locale_data import get_locale_text
from .base import RelicImpl
from .registry import register_relic

class RustShackleRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        self.hp_loss = 4

    def on_battle_start(self, run, engine):
        p = run.player
        loss = min(self.hp_loss, p.hp - 1) if p.hp > 1 else 0
        if loss > 0:
            engine._damage_target(run, "p0", loss, source="self", damage_type="true")
        engine._log_event(run, get_locale_text("i18n_relics_amulets.curse.rust_shackle.trigger", hp_loss=self.hp_loss))

class BlindSpotRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        self.draw_penalty = 2

    def on_battle_start(self, run, engine):
        engine._log_event(run, get_locale_text("i18n_relics_amulets.curse.blind_spot.trigger", draw_penalty=self.draw_penalty))

    def modify_initial_draw(self, run, draw_count: int, engine) -> int:
        return max(0, draw_count - self.draw_penalty)

class FoolOathRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        self.hp_reduction = 3

    def on_minion_summon(self, event, run, engine):
        m = event.minion_state
        m.hp = max(1, m.hp - self.hp_reduction)
        m.max_hp = max(1, m.max_hp - self.hp_reduction)

class WitherSeedRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)

    def on_heal(self, event, run, engine):
        if event.target == "p0":
            event.cancel()

class ShadowCurseRelic(RelicImpl):
    def on_card_played(self, event, run, engine):
        if event.card.type == "spell" and not event.card.id.startswith("demon_contract"):
            engine._damage_target(run, "p0", 1, source="shadow_curse", damage_type="force")
            engine._log_event(run, get_locale_text("i18n_relics_amulets.curse.shadow_curse.trigger"))

class GlacierChillRelic(RelicImpl):
    def on_turn_start(self, event, run, engine):
        if event.is_player:
            run.player.actions = max(0, run.player.actions - 1)
            engine._log_event(run, get_locale_text("i18n_relics_amulets.curse.glacier_chill.trigger"))


for name, obj in list(globals().items()):
    if isinstance(obj, type) and issubclass(obj, RelicImpl) and obj is not RelicImpl:
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        if snake.endswith('_relic'):
            relic_id = snake[:-6]
            register_relic(relic_id)(obj)
