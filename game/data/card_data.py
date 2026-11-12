from .neutral_card_data import NEUTRAL_CARD_CONFIG
from .wizard_card_data import WIZARD_CARD_CONFIG
from .warrior_card_data import WARRIOR_CARD_CONFIG
from .coop_card_data import COOP_CARD_CONFIG
from .mercenary_card_data import MERCENARY_CARD_CONFIG

CARD_CONFIG = {}
CARD_CONFIG.update(NEUTRAL_CARD_CONFIG)
CARD_CONFIG.update(WIZARD_CARD_CONFIG)
CARD_CONFIG.update(WARRIOR_CARD_CONFIG)
CARD_CONFIG.update(COOP_CARD_CONFIG)
CARD_CONFIG.update(MERCENARY_CARD_CONFIG)

