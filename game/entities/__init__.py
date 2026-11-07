from .cards import ALL_CARDS, MARKET_CARDS, is_card_available
from .minions import ALL_MINIONS, MINION_SKILLS
from .enemies import ALL_ENEMIES, get_enemy_template
from .amulets import ALL_AMULETS
from .buffs import (
    get_buff_impl,
)
from .relics import get_relic_name, get_relic_desc, get_relic_rarity, ALL_RELIC_IDS, get_relic_impl
from ..data.gem_data import GEM_CONFIG

def get_gem_name(gem_id: str) -> str:
    return GEM_CONFIG.get(gem_id, {}).get("name", gem_id)

def get_gem_desc(gem_id: str) -> str:
    return GEM_CONFIG.get(gem_id, {}).get("desc", "")
