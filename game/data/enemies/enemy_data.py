from .enemy_data_boss import ENEMY_BOSS_CONFIG
from .enemy_data_normal import ENEMY_NORMAL_CONFIG
from .enemy_data_bleak_falls import ENEMY_BLEAK_FALLS_CONFIG
from .enemy_data_chireiden import ENEMY_CHIREIDEN_CONFIG
from ..content.chaos_expansion_data import CHAOS_AND_NPC_ENEMY_CONFIG
from .unregistered_enemies_data import UNREGISTERED_ENEMY_CONFIG

AOE_INTENT_TYPES = {
    "attack_all",
    "aoe_attack",
    "all_attack",
    "aoe_damage",
    "hellfire",
    "electrodynamics",
    "soul_daggers",
    "focus_bloom",
    "sunken_tsunami",
    "mist_condense_1",
    "tail_sweep",
    "inferno_breath",
    "drone_he3_drop",
    "rin_corpse_ash_nova",
    "utsuho_tokamak_flare",
    "portal_xen_bombard",
    "xen_houndeye_sonic",
}

ENEMY_CONFIG = {}
ENEMY_CONFIG.update(ENEMY_BOSS_CONFIG)
ENEMY_CONFIG.update(ENEMY_NORMAL_CONFIG)
ENEMY_CONFIG.update(ENEMY_BLEAK_FALLS_CONFIG)
ENEMY_CONFIG.update(ENEMY_CHIREIDEN_CONFIG)
ENEMY_CONFIG.update(CHAOS_AND_NPC_ENEMY_CONFIG)
ENEMY_CONFIG.update(UNREGISTERED_ENEMY_CONFIG)
