import random
from ....data.world.grid_map_config import FLOOR_CONFIGS, HIGH_DANGER_CONFIG
from ....data.text.locale_data import get_locale_text
from ....data.world.grid_map_config import FLOOR_CONFIGS, get_run_floor_index
from ....data.world.room_interact_data import ROOM_NPCS, STEALTH_PEACE_BUFF_IDS, TRUE_SIGHT_ENEMIES, TRUE_SIGHT_NPCS
from ..persistent_buffs import add_persistent_buff
from .big_room import get_effective_alive_npcs, mark_effective_npc_defeated, sync_big_room_clear_state

LEGACY_HOSTILE_NPC_MAP = {
    "battle": "dungeon_raiders",
    "elite": "elite_guardian",
    "high_danger": "abyssal_hazard_fiend",
    "boss": "floor_boss",
    "secret_boss": "secret_boss_avatar",
    "corpse": "corpse_wraith",
}


def is_hostile_npc(npc_id: str) -> bool:
    return bool(ROOM_NPCS.get(npc_id, {}).get("hostile", False))


def ensure_room_hostile_npcs(fm, room) -> None:
    if room is None:
        return
    if getattr(room, "room_type", "") == "downstairs":
        if "floor_boss" in room.npcs:
            room.npcs.remove("floor_boss")
        return
    if getattr(room, "big_room_id", ""):
        return
    npc_id = LEGACY_HOSTILE_NPC_MAP.get(getattr(room, "room_type", ""))
    if not npc_id or getattr(room, "cleared", False):
        return
    if npc_id not in room.npcs and npc_id not in room.defeated_npcs:
        room.npcs.append(npc_id)


def ensure_treasure_chest_prop(room) -> None:
    if room is None:
        return
    if getattr(room, "room_type", "") == "treasure" and not getattr(room, "cleared", False):
        if "treasure_chest" not in room.props and "treasure_chest" not in room.interacted_props:
            room.props.append("treasure_chest")


def get_alive_hostile_npcs(fm, room) -> list[str]:
    if room is None:
        return []
    ensure_room_hostile_npcs(fm, room)
    return [nid for nid in get_effective_alive_npcs(fm, room) if is_hostile_npc(nid)]


def has_stealth_buff(player) -> bool:
    if player is None:
        return False
    for b in getattr(player, "persistent_buffs", None) or []:
        if b.id in STEALTH_PEACE_BUFF_IDS and int(getattr(b, "stacks", 0) or 0) > 0:
            return True
    for b in getattr(player, "buffs", None) or []:
        if b.id in STEALTH_PEACE_BUFF_IDS and int(getattr(b, "stacks", 0) or 0) > 0:
            return True
    return False


def resolve_hostile_npc_difficulty(npc_id: str, room) -> str:
    cfg = ROOM_NPCS.get(npc_id, {})
    diff = str(cfg.get("encounter_difficulty") or "")
    if diff:
        return diff
    rtype = getattr(room, "room_type", "") if room is not None else ""
    return {
        "battle": "normal",
        "elite": "elite",
        "high_danger": "elite",
        "boss": "boss",
        "secret_boss": "secret_boss",
        "corpse": "ghost",
    }.get(rtype, "normal")


def has_true_sight_enemy_name(name: str) -> bool:
    if not name:
        return False
    if name in TRUE_SIGHT_ENEMIES:
        return True
    base = name.rsplit(" ", 1)[0] if (" " in name and len(name.rsplit(" ", 1)[1]) == 1) else name
    return base in TRUE_SIGHT_ENEMIES


def resolve_room_true_sight_enemy(fm, room, npc_id: str, player=None) -> str:
    if room is None:
        return ""
    preset_enemy = str(room.shared_payload.get("preset_enemy_name") or "")
    if has_true_sight_enemy_name(preset_enemy):
        return preset_enemy
    yog_enc = str(room.shared_payload.get("yog_encounter") or "")
    if yog_enc:
        from ....data.world.yog_quest_config import YOG_ENCOUNTERS
        for ename, _ in (YOG_ENCOUNTERS.get(yog_enc, {}).get("enemies") or []):
            if has_true_sight_enemy_name(ename):
                return ename
    if npc_id in TRUE_SIGHT_NPCS:
        cfg = FLOOR_CONFIGS.get(getattr(fm, "floor_index", 1), FLOOR_CONFIGS[1]) if fm is not None else FLOOR_CONFIGS[1]
        sb_name = str(cfg.get("secret_boss_name") or "")
        if sb_name:
            return sb_name
        ncfg = ROOM_NPCS.get(npc_id, {})
        return get_locale_text(ncfg["name_key"]) if ncfg.get("name_key") else npc_id
    if npc_id == "floor_boss" or getattr(room, "room_type", "") == "boss":
        if fm is not None and fm.floor_flags.get("bleak_falls_zone"):
            return ""
        boss_name = str(room.shared_payload.get("preset_boss_name") or "")
        if not boss_name:
            from ....data.enemies.enemy_data_boss import BOSS_POOLS
            floor_index = fm.floor_index if fm is not None else 1
            cfg = FLOOR_CONFIGS.get(floor_index, FLOOR_CONFIGS[1])
            pool_key = str(cfg.get("boss_pool") or "early")
            pool = BOSS_POOLS.get(pool_key, BOSS_POOLS["early"])
            boss_name = pool[0] if len(pool) == 1 else random.choice(pool)
            room.shared_payload["preset_boss_name"] = boss_name
        if has_true_sight_enemy_name(boss_name):
            return boss_name
    return ""


def trigger_hostile_npc_battle(
    grid_map_service,
    run,
    uid: str,
    coord: str,
    room,
    npc_id: str,
) -> str:
    from ....renderer import GameRenderer
    from ..open_world.loadout_service import is_open_world_run

    fm = run.floor_map
    p = run.player

    if (npc_id == "corpse_wraith" or room.room_type == "corpse") and not is_open_world_run(run):
        corpse_id = room.shared_payload.get("corpse_id", "")
        corpse = grid_map_service.save_manager.corpses.get(corpse_id) if corpse_id else None
        if not corpse or corpse.get("claimed_by"):
            mark_effective_npc_defeated(fm, room, npc_id)
            if room.room_type == "corpse":
                room.room_type = "empty"
            room.cleared = True
            sync_big_room_clear_state(fm, room)
            grid_map_service.save_manager.save_save(uid, run)
            return grid_map_service._format_map_output(run, get_locale_text("i18n_grid_map.corpse_gone", coord=coord))
        return grid_map_service._start_battle(
            run, uid, coord, room, "ghost", corpse=corpse, hostile_npc_id=npc_id
        )

    diff = resolve_hostile_npc_difficulty(npc_id, room)
    if (diff == "high_danger" or room.room_type == "high_danger") and not room.shared_payload.get("hazard_applied"):
        loss = max(HIGH_DANGER_CONFIG["hazard_hp_min"], int(p.max_hp * HIGH_DANGER_CONFIG["hazard_hp_ratio"]))
        p.hp = max(1, p.hp - loss)
        add_persistent_buff(p, "abyss_chill", 1)
        room.shared_payload["hazard_applied"] = True
        room.shared_payload["hazard_loss"] = loss
    if diff == "high_danger":
        diff = "elite"

    return grid_map_service._start_battle(
        run, uid, coord, room, diff, hostile_npc_id=npc_id
    )
