from typing import Iterable, Set
from ...data.cafe_data import NPC_SHOW_NAMES
from ...data.locale_data import get_locale_text
from ...data.room_interact_data import ROOM_NPCS
from ...data.unregistered_enemies_data import CAFE_KEY_TO_ENTITY, YOG_BOSS_ENTITY_NAMES


def normalize_entity_keys(*candidates: str) -> Set[str]:
    keys: Set[str] = set()
    for raw in candidates:
        s = str(raw or "").strip()
        if not s:
            continue
        keys.add(s)
        if s in CAFE_KEY_TO_ENTITY:
            keys.add(CAFE_KEY_TO_ENTITY[s])
        if s in NPC_SHOW_NAMES:
            keys.add(NPC_SHOW_NAMES[s])
        if " · " in s:
            keys.add(s.rsplit(" · ", 1)[-1].strip())
        if " " in s:
            head = s.split(" ", 1)[0]
            tail = s.split(" ", 1)[-1].strip()
            if len(s.rsplit(" ", 1)[-1]) == 1 and " " in s:
                keys.add(s.rsplit(" ", 1)[0].strip())
            if head and len(head) <= 2 and not head.isascii():
                keys.add(tail)
            if tail:
                keys.add(tail)
        if s.startswith("DeepSeek"):
            keys.add("DeepSeek")
            keys.add("DeepSeek V4.1 Flash")
        if s in ROOM_NPCS:
            rcfg = ROOM_NPCS[s]
            if rcfg.get("name_key"):
                keys.add(get_locale_text(rcfg["name_key"]))
            if rcfg.get("enemy_name_key"):
                keys.add(get_locale_text(rcfg["enemy_name_key"]))
    return {k for k in keys if k}


def _collect_room_npc_names(room) -> Set[str]:
    out: Set[str] = set()
    for nid in getattr(room, "npcs", None) or []:
        out.update(normalize_entity_keys(nid))
    return out


def has_encountered(stats, run, *candidates: str) -> bool:
    cand_keys = normalize_entity_keys(*candidates)
    if not cand_keys:
        return False
    if stats is not None:
        recorded = normalize_entity_keys(*(getattr(stats, "encountered_entities", None) or ()))
        if cand_keys & recorded:
            return True
        defeated_town = normalize_entity_keys(*(getattr(stats, "defeated_town_npcs", None) or ()))
        if cand_keys & defeated_town:
            return True
        if getattr(stats, "yog_sothoth_kill_count", 0) > 0 and (cand_keys & YOG_BOSS_ENTITY_NAMES):
            return True
        if getattr(stats, "killed_icerainboww", False) and any("icerainboww" in k.lower() for k in cand_keys):
            return True
    if run is not None:
        active_enemies = normalize_entity_keys(*(getattr(e, "name", "") for e in (getattr(run, "enemies", None) or ())))
        if cand_keys & active_enemies:
            return True
        cafe_data = getattr(run, "node_data", None) or {}
        cafe_npcs = (cafe_data.get("cafe_data") or {}).get("npcs") or []
        if cafe_npcs and (cand_keys & normalize_entity_keys(*cafe_npcs)):
            return True
        fm = getattr(run, "floor_map", None)
        if fm is not None:
            coord = fm.player_coords.get(getattr(run, "user_id", ""), "")
            room = fm.rooms.get(coord)
            if room is not None and (cand_keys & _collect_room_npc_names(room)):
                return True
    return False


def record_encounter(save_manager, user_id: str, *names_or_ids: str) -> None:
    if save_manager is None or not user_id:
        return
    keys = normalize_entity_keys(*names_or_ids)
    if not keys:
        return
    stats = save_manager.load_stats(user_id)
    existing = set(getattr(stats, "encountered_entities", None) or [])
    added = [k for k in sorted(keys) if k not in existing]
    if not added:
        return
    stats.encountered_entities.extend(added)
    save_manager.save_stats(user_id, stats)


def record_encounter_for_run(save_manager, run, *names_or_ids: str) -> None:
    if save_manager is None or run is None:
        return
    uids: Iterable[str]
    if hasattr(run, "all_human_uids"):
        uids = run.all_human_uids() or [getattr(run, "user_id", "")]
    else:
        uids = [getattr(run, "user_id", "")]
    for uid in uids:
        if uid:
            record_encounter(save_manager, uid, *names_or_ids)


def resolve_entity_intro(
    entity_id: str,
    entity_name: str,
    stats=None,
    run=None,
    extra_candidates: tuple[str, ...] = (),
) -> str:
    if not has_encountered(stats, run, entity_id, entity_name, *extra_candidates):
        return get_locale_text("i18n_entity_lore.unknown_intro")
    from ...data.locale_data import get_locale_raw

    intros = get_locale_raw("i18n_entity_lore.intros", {})
    if isinstance(intros, dict):
        for key in (entity_id, entity_name, *extra_candidates, *sorted(normalize_entity_keys(entity_id, entity_name))):
            if key in intros and intros[key]:
                return str(intros[key])
    if entity_id in ROOM_NPCS and ROOM_NPCS[entity_id].get("desc_key"):
        return get_locale_text(ROOM_NPCS[entity_id]["desc_key"])
    return get_locale_text("renderer_menu.npc_default_desc")
