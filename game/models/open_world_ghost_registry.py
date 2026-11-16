import os
import time
import uuid
from typing import Dict, List, Optional

from ..json_codec import load
from .corpse_registry import _atomic_write_json


class OpenWorldGhostRegistry:
    def __init__(self, data_dir: str):
        self.path = os.path.join(data_dir, "open_world_ghosts.json")

    def _load(self) -> Dict[str, dict]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self, data: Dict[str, dict]) -> None:
        _atomic_write_json(self.path, data)

    def list_at(self, world: str, coord: str) -> List[dict]:
        data = self._load()
        target_world = str(world or "")
        target_coord = str(coord or "")
        matches = [
            dict(entry)
            for entry in data.values()
            if str(entry.get("world", "")) == target_world and str(entry.get("coord", "")) == target_coord
        ]
        matches.sort(key=lambda item: float(item.get("created_at", 0.0)))
        return matches

    def list_all(self, world: Optional[str] = None) -> List[dict]:
        data = self._load()
        items = []
        for entry in data.values():
            if world is not None and str(entry.get("world", "")) != str(world):
                continue
            items.append(dict(entry))
        items.sort(key=lambda item: float(item.get("created_at", 0.0)))
        return items

    def get(self, ghost_id: Optional[str]) -> Optional[dict]:
        if not ghost_id:
            return None
        data = self._load()
        entry = data.get(str(ghost_id))
        return dict(entry) if isinstance(entry, dict) else None

    def add(
        self,
        owner_uid: str,
        owner_name: str,
        world: str,
        coord: str,
        cause: str,
        max_hp: int,
        deck: List[dict],
        relics: List[str],
        relic_counters: Dict[str, int],
        bag_items: List[str],
    ) -> dict:
        data = self._load()
        ghost_id = f"ow_ghost_{uuid.uuid4().hex[:12]}"
        entry = {
            "id": ghost_id,
            "owner_uid": str(owner_uid),
            "owner_name": str(owner_name or owner_uid),
            "world": str(world),
            "coord": str(coord),
            "cause": str(cause or ""),
            "max_hp": max(1, int(max_hp)),
            "deck": list(deck or []),
            "relics": list(relics or []),
            "relic_counters": dict(relic_counters or {}),
            "bag_items": list(bag_items or []),
            "attacked_by": [],
            "created_at": time.time(),
        }
        data[ghost_id] = entry
        self._save(data)
        return dict(entry)

    def mark_attacked(self, ghost_id: str, attacker_uid: str) -> Optional[dict]:
        data = self._load()
        entry = data.get(str(ghost_id))
        if not isinstance(entry, dict):
            return None
        attacked = list(entry.get("attacked_by") or [])
        uid = str(attacker_uid)
        if uid not in attacked:
            attacked.append(uid)
            entry["attacked_by"] = attacked
            data[str(ghost_id)] = entry
            self._save(data)
        return dict(entry)

    def remove(self, ghost_id: Optional[str]) -> Optional[dict]:
        if not ghost_id:
            return None
        data = self._load()
        removed = data.pop(str(ghost_id), None)
        if removed is not None:
            self._save(data)
            return dict(removed)
        return None
