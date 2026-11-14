from ...data.locale_data import get_locale_text
from ...data.outer_plane_config import OUTER_PLANE_TRIGGER_FLAG
from ...models.state import Card
from .registry import register_card


@register_card("dream_shard")
class DreamShardCard(Card):
    def execute(self, run, target, engine) -> str:
        run.player.max_hp = 0
        run.node_data[OUTER_PLANE_TRIGGER_FLAG] = True
        return get_locale_text("i18n_outer_plane.dream_shard.hidden_trigger")
