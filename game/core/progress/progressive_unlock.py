from typing import Iterable

from ...data.chireiden_data import (
    CHIREIDEN_BUFF_CONFIG,
    CHIREIDEN_CARD_CONFIG,
    CHIREIDEN_RELIC_CONFIG,
)
from ...data.enemy_data_chireiden import ENEMY_CHIREIDEN_CONFIG
from ...data.locale_data import get_locale_text

CARD_VISIBILITY_ACHIEVEMENTS: dict[str, tuple[str, ...]] = {
    "neutral_button_magic": ("boss_yog_sothoth",),
    "d_he3_fusion_ignition": ("chireiden_elevator_descent",),
    "lunar_he3_orbital_drop": ("chireiden_elevator_descent",),
    "pb_bi_coolant_loop": ("chireiden_lbe_quench",),
    "int19_tokamak_calculus": ("chireiden_utsuho_headband", "chireiden_overcharge_master"),
    "penning_trap_lockdown": ("chireiden_utsuho_headband", "chireiden_penning_sealer"),
    "hisoutensoku_thermonuclear_cannon": ("chireiden_penning_sealer", "chireiden_overcharge_master"),
}

CARD_DETAIL_ACHIEVEMENTS: dict[str, tuple[str, ...]] = {
    "neutral_button_magic": ("boss_yog_sothoth",),
}

RELIC_UNLOCK_ACHIEVEMENTS: dict[str, tuple[str, ...]] = {
    "lbe_fast_reactor_core": ("chireiden_lbe_quench",),
    "headband_of_intellect_int19": ("chireiden_utsuho_headband",),
    "lunar_he3_capsule": ("chireiden_utsuho_headband", "chireiden_penning_sealer"),
    "penning_ion_stabilizer": ("chireiden_penning_sealer",),
}

BUFF_UNLOCK_ACHIEVEMENTS: dict[str, tuple[str, ...]] = {
    "fusion_overcharge": ("chireiden_elevator_descent", "chireiden_overcharge_master"),
    "magnetic_confinement": ("chireiden_elevator_descent",),
    "lbe_thermal_inertia": ("chireiden_lbe_quench",),
    "headband_int19_aura": ("chireiden_utsuho_headband",),
    "penning_xen_rift_p1": ("chireiden_utsuho_headband", "chireiden_utsuho_ally", "chireiden_penning_sealer"),
    "xen_swarm_link": ("chireiden_utsuho_ally", "chireiden_penning_sealer"),
    "penning_xen_rift_p2": ("chireiden_utsuho_ally", "chireiden_penning_sealer"),
    "penning_xen_rift_p3": ("chireiden_penning_sealer",),
    "penning_xen_rift_p4": ("chireiden_penning_sealer",),
}

LORE_ITEM_ACHIEVEMENT_RULES: dict[str, tuple[str, ...]] = {
    "boss_yog_sothoth": ("boss_yog_sothoth",),
    "abyss_secret_clue": ("abyss_secret_clue",),
    "chireiden_he3_fuel": ("chireiden_elevator_descent", "chireiden_facility_surveyor"),
    "chireiden_lbe_flask": ("chireiden_lbe_quench", "chireiden_facility_surveyor"),
    "chireiden_xen_ampoule": ("chireiden_facility_surveyor", "chireiden_penning_sealer"),
    "chireiden_blueprint": ("chireiden_facility_surveyor", "chireiden_utsuho_headband"),
    "chireiden_headband_known": ("chireiden_rumor_seeker", "chireiden_elevator_descent", "chireiden_utsuho_headband"),
    "chireiden_headband_full": ("chireiden_utsuho_headband", "chireiden_penning_sealer"),
}

WORLD_ENTRY_ACHIEVEMENTS: dict[tuple[str, str], tuple[str, ...]] = {
    ("floor", "rumor"): ("chireiden_rumor_seeker",),
    ("floor", "full"): ("chireiden_elevator_descent",),
    ("ally", "merc_utsuho"): ("chireiden_utsuho_ally",),
    ("env", "chireiden_elevator_shaft"): ("chireiden_elevator_descent",),
    ("env", "chireiden_turbine_corridor"): ("chireiden_elevator_descent",),
    ("env", "chireiden_he3_logistics_bay"): ("chireiden_elevator_descent",),
    ("env", "chireiden_pb_bi_fast_reactor"): ("chireiden_facility_surveyor", "chireiden_lbe_quench"),
    ("env", "chireiden_d_he3_tokamak_hall"): ("chireiden_facility_surveyor", "chireiden_utsuho_headband"),
    ("env", "chireiden_control_center"): ("chireiden_facility_surveyor", "chireiden_utsuho_headband"),
    ("env", "chireiden_penning_trap"): ("chireiden_facility_surveyor", "chireiden_penning_sealer"),
    ("big_room", "lunar_he3_elevator_hub"): ("chireiden_facility_surveyor",),
    ("big_room", "pb_bi_fast_reactor_chamber"): ("chireiden_facility_surveyor", "chireiden_lbe_quench"),
    ("big_room", "d_he3_tokamak_array"): ("chireiden_facility_surveyor", "chireiden_utsuho_headband"),
    ("big_room", "penning_ion_well_sanctum"): ("chireiden_facility_surveyor", "chireiden_penning_sealer"),
    ("landmark", "chireiden_fusion_terminal"): ("chireiden_facility_surveyor",),
    ("landmark", "chireiden_penning_stabilizer"): ("chireiden_facility_surveyor", "chireiden_penning_sealer"),
    ("prop", "he3_storage_cylinder"): ("chireiden_facility_surveyor",),
    ("prop", "pb_bi_coolant_valve"): ("chireiden_facility_surveyor",),
    ("prop", "tokamak_magnetic_coil"): ("chireiden_facility_surveyor",),
    ("prop", "penning_harmonic_console"): ("chireiden_facility_surveyor",),
    ("trigger", "reactor_steam_vent"): ("chireiden_facility_surveyor", "chireiden_lbe_quench"),
    ("trigger", "he3_orbital_capsule"): ("chireiden_elevator_descent", "chireiden_facility_surveyor"),
    ("trigger", "penning_harmonic_alarm"): ("chireiden_facility_surveyor", "chireiden_penning_sealer"),
}


def _build_enemy_achievement_rules() -> dict[str, dict[str, tuple[str, ...]]]:
    return {
        get_locale_text("i18n_chireiden.enemies.fusion_turbine_automaton"): {
            "full": ("chireiden_elevator_descent",),
        },
        get_locale_text("i18n_chireiden.enemies.he3_cargo_drone"): {
            "full": ("chireiden_elevator_descent",),
        },
        get_locale_text("i18n_chireiden.enemies.lbe_slag_elemental"): {
            "full": ("chireiden_lbe_quench",),
        },
        get_locale_text("i18n_chireiden.enemies.tokamak_arc_sentinel"): {
            "full": ("chireiden_lbe_quench", "chireiden_utsuho_headband"),
        },
        get_locale_text("i18n_chireiden.enemies.kaenbyou_rin"): {
            "rumor": ("chireiden_rumor_seeker",),
            "full": ("chireiden_lbe_quench",),
        },
        get_locale_text("i18n_chireiden.enemies.utsuho_reiuji"): {
            "rumor": ("chireiden_rumor_seeker",),
            "full": ("chireiden_utsuho_headband",),
        },
        get_locale_text("i18n_chireiden.enemies.penning_super_portal_p1"): {
            "full": ("chireiden_utsuho_headband", "chireiden_utsuho_ally", "chireiden_penning_sealer"),
        },
        get_locale_text("i18n_chireiden.enemies.penning_super_portal_p2"): {
            "full": ("chireiden_utsuho_ally", "chireiden_penning_sealer"),
        },
        get_locale_text("i18n_chireiden.enemies.penning_super_portal_p3"): {
            "full": ("chireiden_penning_sealer",),
        },
        get_locale_text("i18n_chireiden.enemies.penning_super_portal_p4"): {
            "full": ("chireiden_penning_sealer",),
        },
        get_locale_text("i18n_chireiden.enemies.xen_headcrab"): {
            "full": ("chireiden_utsuho_ally", "chireiden_penning_sealer"),
        },
        get_locale_text("i18n_chireiden.enemies.xen_houndeye"): {
            "full": ("chireiden_utsuho_ally", "chireiden_penning_sealer"),
        },
        get_locale_text("i18n_chireiden.enemies.xen_vortigaunt"): {
            "full": ("chireiden_utsuho_ally", "chireiden_penning_sealer"),
        },
        get_locale_text("i18n_chireiden.enemies.xen_bullsquid"): {
            "full": ("chireiden_penning_sealer",),
        },
        get_locale_text("i18n_chireiden.enemies.xen_controller"): {
            "full": ("chireiden_penning_sealer",),
        },
    }


def has_achievement(stats, achievement_id: str) -> bool:
    if stats is None or not achievement_id:
        return False
    unlocked = getattr(stats, "unlocked_achievements", None) or ()
    return achievement_id in unlocked


def has_any_achievement(stats, achievement_ids: Iterable[str]) -> bool:
    if stats is None:
        return False
    unlocked = set(getattr(stats, "unlocked_achievements", None) or ())
    if not unlocked:
        return False
    return any(aid in unlocked for aid in achievement_ids)


def is_lore_rule_unlocked(rule_name: str, stats) -> bool:
    if not rule_name:
        return False
    if rule_name == "always":
        return True
    reqs = LORE_ITEM_ACHIEVEMENT_RULES.get(rule_name)
    if reqs is not None:
        return has_any_achievement(stats, reqs)
    return has_achievement(stats, rule_name)


def is_card_visible_in_library(cid: str, stats) -> bool:
    reqs = CARD_VISIBILITY_ACHIEVEMENTS.get(cid)
    if reqs is not None:
        return has_any_achievement(stats, reqs)
    if cid in CHIREIDEN_CARD_CONFIG:
        return False
    return True


def is_card_visible_in_query(cid: str, stats) -> bool:
    if cid == "neutral_button_magic":
        return True
    return is_card_visible_in_library(cid, stats)


def is_card_detail_revealed(cid: str, stats) -> bool:
    reqs = CARD_DETAIL_ACHIEVEMENTS.get(cid)
    if reqs is None:
        return True
    return has_any_achievement(stats, reqs)


def is_relic_visible_in_query(rid: str, stats) -> bool:
    reqs = RELIC_UNLOCK_ACHIEVEMENTS.get(rid)
    if reqs is not None:
        return has_any_achievement(stats, reqs)
    if rid in CHIREIDEN_RELIC_CONFIG:
        return False
    return True


def is_buff_visible_in_query(bid: str, stats) -> bool:
    reqs = BUFF_UNLOCK_ACHIEVEMENTS.get(bid)
    if reqs is not None:
        return has_any_achievement(stats, reqs)
    if bid in CHIREIDEN_BUFF_CONFIG:
        return False
    return True


def is_world_entry_unlocked(category: str, entry_id: str, stats) -> bool:
    reqs = WORLD_ENTRY_ACHIEVEMENTS.get((category, entry_id))
    if reqs is None:
        return False
    return has_any_achievement(stats, reqs)


def get_enemy_query_access(eid: str, ename: str, stats) -> str:
    if eid not in ENEMY_CHIREIDEN_CONFIG and ename not in ENEMY_CHIREIDEN_CONFIG:
        return "full"
    rules = _build_enemy_achievement_rules()
    entry = rules.get(ename) or rules.get(eid)
    if entry is None:
        return "hidden"
    full_reqs = entry.get("full", ())
    if full_reqs and has_any_achievement(stats, full_reqs):
        return "full"
    rumor_reqs = entry.get("rumor", ())
    if rumor_reqs and has_any_achievement(stats, rumor_reqs):
        return "rumor"
    return "hidden"
