from .base import RelicImpl
from .registry import register_relic


@register_relic("ghost_body")
class GhostBodyRelic(RelicImpl):
    pass
