from ...data.text.locale_data import get_locale_text
from .base import RelicImpl
from .registry import register_relic


@register_relic("ghost_body")
class GhostBodyRelic(RelicImpl):
    def on_before_damage_apply(self, event, run, engine):
        if event.target != "p0" or event.final_damage <= 0:
            return
        dtype = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype.lower() != "true":
            return
        event.final_damage = 0
        engine._log_event(run, get_locale_text("i18n_grid_map.ghost_body_immune_log", name=run.player.name))
