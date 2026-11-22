from typing import Any, Dict, List, Optional
from ..big_room import get_big_room

ATTITUDE_MODIFIERS = {
    "hostile": -3,
    "wary": -1,
    "neutral": 0,
    "friendly": 2,
    "trusted": 3,
}


class NpcMemoryStore:
    @staticmethod
    def clamp_affinity(val: int) -> int:
        return max(-10, min(10, int(val)))

    @staticmethod
    def attitude_tier(affinity: int) -> str:
        val = int(affinity)
        if val <= -4:
            return "hostile"
        if val <= -1:
            return "wary"
        if val <= 2:
            return "neutral"
        if val <= 5:
            return "friendly"
        return "trusted"

    @staticmethod
    def attitude_modifier(affinity: int) -> int:
        tier = NpcMemoryStore.attitude_tier(affinity)
        return ATTITUDE_MODIFIERS.get(tier, 0)

    @staticmethod
    def load_stats(save_manager, uid: str):
        if save_manager is None or not uid:
            return None
        return save_manager.load_stats(uid)

    @staticmethod
    def save_stats(save_manager, uid: str, stats) -> None:
        if save_manager is None or stats is None or not uid:
            return
        save_manager.save_stats(uid, stats)

    @staticmethod
    def ensure_run_bucket(run, uid: str) -> Dict[str, Any]:
        if not isinstance(getattr(run, "map_data", None), dict):
            run.map_data = {}
        root = run.map_data.setdefault("npc_memory", {})
        bucket = root.setdefault(uid, {})
        bucket.setdefault("npcs", {})
        bucket.setdefault("world_flags", [])
        return bucket

    @staticmethod
    def ensure_run_npc(run, uid: str, npc_id: str, initial_affinity: int = 0) -> Dict[str, Any]:
        bucket = NpcMemoryStore.ensure_run_bucket(run, uid)
        npcs = bucket["npcs"]
        if npc_id not in npcs:
            npcs[npc_id] = {
                "affinity": NpcMemoryStore.clamp_affinity(initial_affinity),
                "met_count": 0,
                "known_flags": [],
                "completed_quests": [],
                "last_floor": 0,
                "last_coord": "",
            }
        entry = npcs[npc_id]
        entry.setdefault("affinity", NpcMemoryStore.clamp_affinity(initial_affinity))
        entry.setdefault("met_count", 0)
        entry.setdefault("known_flags", [])
        entry.setdefault("completed_quests", [])
        entry.setdefault("last_floor", 0)
        entry.setdefault("last_coord", "")
        return entry

    @staticmethod
    def ensure_cycle_memory(stats) -> Dict[str, Any]:
        if stats is None:
            return {
                "killed_npcs": {},
                "spared_npcs": {},
                "cycle_flags": [],
                "cross_run_affinity": {},
            }
        if not isinstance(getattr(stats, "town_flags", None), dict):
            stats.town_flags = {}
        mem = stats.town_flags.setdefault("npc_cycle_memory", {})
        mem.setdefault("killed_npcs", {})
        mem.setdefault("spared_npcs", {})
        mem.setdefault("cycle_flags", [])
        mem.setdefault("cross_run_affinity", {})
        return mem

    @staticmethod
    def get_cycle_memory_readonly(stats) -> Dict[str, Any]:
        if stats is None:
            return {
                "killed_npcs": {},
                "spared_npcs": {},
                "cycle_flags": [],
                "cross_run_affinity": {},
            }
        flags = getattr(stats, "town_flags", None) or {}
        mem = flags.get("npc_cycle_memory")
        if not isinstance(mem, dict):
            return {
                "killed_npcs": {},
                "spared_npcs": {},
                "cycle_flags": [],
                "cross_run_affinity": {},
            }
        return mem

    @staticmethod
    def _encounter_holder(run, room=None, coord: str = ""):
        fm = getattr(run, "floor_map", None)
        if room is None and fm is not None:
            target_coord = coord or fm.player_coords.get(getattr(run, "user_id", ""), "")
            room = fm.rooms.get(target_coord)
        if room is None:
            return None
        br = get_big_room(fm, room) if fm is not None else None
        if br is not None and br.share_npcs:
            return br
        return room

    @staticmethod
    def ensure_encounter(run, npc_id: str, room=None, coord: str = "") -> Dict[str, Any]:
        holder = NpcMemoryStore._encounter_holder(run, room=room, coord=coord)
        if holder is None:
            if not isinstance(getattr(run, "map_data", None), dict):
                run.map_data = {}
            root = run.map_data.setdefault("_fallback_npc_encounter", {})
        else:
            if not isinstance(getattr(holder, "shared_payload", None), dict):
                holder.shared_payload = {}
            root = holder.shared_payload.setdefault("npc_encounter", {})
        enc = root.setdefault(npc_id, {})
        world = enc.setdefault("world", {})
        world.setdefault("departed", False)
        world.setdefault("spared", False)
        world.setdefault("shared_claimed", [])
        enc.setdefault("players", {})
        return enc

    @staticmethod
    def ensure_player_encounter(run, npc_id: str, uid: str, room=None, coord: str = "") -> Dict[str, Any]:
        enc = NpcMemoryStore.ensure_encounter(run, npc_id, room=room, coord=coord)
        players = enc["players"]
        if uid not in players:
            players[uid] = {
                "talk_turns": 0,
                "visited_nodes": [],
                "consumed_options": [],
                "locked_groups": [],
                "service_uses": {},
                "checked_nodes": {},
                "local_flags": [],
                "recap_entries": [],
                "exhausted": False,
                "greeting_idx": 0,
            }
        p_enc = players[uid]
        p_enc.setdefault("talk_turns", 0)
        p_enc.setdefault("visited_nodes", [])
        p_enc.setdefault("consumed_options", [])
        p_enc.setdefault("locked_groups", [])
        p_enc.setdefault("service_uses", {})
        p_enc.setdefault("checked_nodes", {})
        p_enc.setdefault("local_flags", [])
        p_enc.setdefault("recap_entries", [])
        p_enc.setdefault("exhausted", False)
        p_enc.setdefault("greeting_idx", 0)
        return p_enc

    @staticmethod
    def effective_affinity(run, stats, uid: str, npc_id: str, graph: dict) -> int:
        base_aff = int(graph.get("initial_affinity", 0))
        bucket = ((getattr(run, "map_data", None) or {}).get("npc_memory") or {}).get(uid) or {}
        npc_entry = (bucket.get("npcs") or {}).get(npc_id)
        if isinstance(npc_entry, dict) and "affinity" in npc_entry:
            val = int(npc_entry["affinity"])
        else:
            val = base_aff
            if graph.get("cross_run_memory") and stats is not None:
                cmem = NpcMemoryStore.get_cycle_memory_readonly(stats)
                cross_map = cmem.get("cross_run_affinity") or {}
                if npc_id in cross_map:
                    val = max(-5, min(5, int(cross_map[npc_id])))
                if int((cmem.get("killed_npcs") or {}).get(npc_id, 0) or 0) > 0:
                    val -= 1
        return NpcMemoryStore.clamp_affinity(val)

    @staticmethod
    def ensure_initialized_run_npc(run, stats, uid: str, npc_id: str, graph: dict) -> Dict[str, Any]:
        bucket = NpcMemoryStore.ensure_run_bucket(run, uid)
        npcs = bucket["npcs"]
        if npc_id not in npcs:
            init_aff = NpcMemoryStore.effective_affinity(run, stats, uid, npc_id, graph)
            return NpcMemoryStore.ensure_run_npc(run, uid, npc_id, initial_affinity=init_aff)
        return NpcMemoryStore.ensure_run_npc(run, uid, npc_id, initial_affinity=int(graph.get("initial_affinity", 0)))

    @staticmethod
    def add_affinity(run, stats, save_manager, uid: str, npc_id: str, delta: int, graph: dict) -> int:
        entry = NpcMemoryStore.ensure_initialized_run_npc(run, stats, uid, npc_id, graph)
        new_val = NpcMemoryStore.clamp_affinity(int(entry["affinity"]) + int(delta))
        entry["affinity"] = new_val
        if graph.get("cross_run_memory") and stats is not None:
            cmem = NpcMemoryStore.ensure_cycle_memory(stats)
            cross_map = cmem["cross_run_affinity"]
            cur_cross = int(cross_map.get(npc_id, 0) or 0)
            cross_map[npc_id] = max(-5, min(5, cur_cross + int(delta)))
            NpcMemoryStore.save_stats(save_manager, uid, stats)
        return new_val

    @staticmethod
    def record_npc_killed(stats, save_manager, uid: str, npc_id: str) -> None:
        if stats is None:
            return
        cmem = NpcMemoryStore.ensure_cycle_memory(stats)
        killed = cmem["killed_npcs"]
        killed[npc_id] = int(killed.get(npc_id, 0) or 0) + 1
        NpcMemoryStore.save_stats(save_manager, uid, stats)

    @staticmethod
    def record_npc_spared(stats, save_manager, uid: str, npc_id: str) -> None:
        if stats is None:
            return
        cmem = NpcMemoryStore.ensure_cycle_memory(stats)
        spared = cmem["spared_npcs"]
        spared[npc_id] = int(spared.get(npc_id, 0) or 0) + 1
        NpcMemoryStore.save_stats(save_manager, uid, stats)

    @staticmethod
    def add_recap(p_enc: Dict[str, Any], recap_id: str, locale_key: str, params: Optional[dict] = None) -> None:
        entries: List[dict] = p_enc.setdefault("recap_entries", [])
        for existing in entries:
            if existing.get("id") == recap_id:
                existing["locale_key"] = locale_key
                existing["params"] = dict(params or {})
                return
        entries.append(
            {
                "id": recap_id,
                "locale_key": locale_key,
                "params": dict(params or {}),
            }
        )
