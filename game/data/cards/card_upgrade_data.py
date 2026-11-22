from .card_upgrade_data_base import CARD_UPGRADE_CONFIG_BASE
from .card_upgrade_data_character import CARD_UPGRADE_CONFIG_CHARACTER
from .sets.map_card_data import MAP_CARD_UPGRADE_CONFIG
from ..content.chireiden_data import CHIREIDEN_CARD_UPGRADE_CONFIG
from .classes.ninja_card_data import NINJA_UPGRADE_CONFIG
from .classes.rainie_card_data import RAINIE_CARD_UPGRADE_CONFIG

CARD_UPGRADE_CONFIG = {**CARD_UPGRADE_CONFIG_BASE, **CARD_UPGRADE_CONFIG_CHARACTER, **MAP_CARD_UPGRADE_CONFIG, **CHIREIDEN_CARD_UPGRADE_CONFIG, **NINJA_UPGRADE_CONFIG, **RAINIE_CARD_UPGRADE_CONFIG}
