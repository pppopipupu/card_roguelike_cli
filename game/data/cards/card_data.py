from .neutral.neutral_card_data import NEUTRAL_CARD_CONFIG
from .classes.wizard_card_data import WIZARD_CARD_CONFIG
from .classes.warrior_card_data import WARRIOR_CARD_CONFIG
from .sets.coop_card_data import COOP_CARD_CONFIG
from .sets.mercenary_card_data import MERCENARY_CARD_CONFIG
from .sets.map_card_data import MAP_CARD_CONFIG
from ..content.chireiden_data import CHIREIDEN_CARD_CONFIG
from .classes.ninja_card_data import NINJA_CARD_CONFIG
from .classes.rainie_card_data import RAINIE_CARD_CONFIG
from ..content.ultimate_prism_data import ULTIMATE_PRISM_CARD_CONFIG

CARD_CONFIG = {}
CARD_CONFIG.update(NEUTRAL_CARD_CONFIG)
CARD_CONFIG.update(WIZARD_CARD_CONFIG)
CARD_CONFIG.update(WARRIOR_CARD_CONFIG)
CARD_CONFIG.update(COOP_CARD_CONFIG)
CARD_CONFIG.update(MERCENARY_CARD_CONFIG)
CARD_CONFIG.update(MAP_CARD_CONFIG)
CARD_CONFIG.update(CHIREIDEN_CARD_CONFIG)
CARD_CONFIG.update(NINJA_CARD_CONFIG)
CARD_CONFIG.update(RAINIE_CARD_CONFIG)
CARD_CONFIG.update(ULTIMATE_PRISM_CARD_CONFIG)

