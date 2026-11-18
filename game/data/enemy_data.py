from ..data.enemy_data_boss import ENEMY_BOSS_CONFIG
from ..data.enemy_data_normal import ENEMY_NORMAL_CONFIG
from ..data.enemy_data_bleak_falls import ENEMY_BLEAK_FALLS_CONFIG
from ..data.enemy_data_chireiden import ENEMY_CHIREIDEN_CONFIG
from ..data.chaos_expansion_data import CHAOS_AND_NPC_ENEMY_CONFIG
from ..data.unregistered_enemies_data import UNREGISTERED_ENEMY_CONFIG

ENEMY_CONFIG = {}
ENEMY_CONFIG.update(ENEMY_BOSS_CONFIG)
ENEMY_CONFIG.update(ENEMY_NORMAL_CONFIG)
ENEMY_CONFIG.update(ENEMY_BLEAK_FALLS_CONFIG)
ENEMY_CONFIG.update(ENEMY_CHIREIDEN_CONFIG)
ENEMY_CONFIG.update(CHAOS_AND_NPC_ENEMY_CONFIG)
ENEMY_CONFIG.update(UNREGISTERED_ENEMY_CONFIG)
