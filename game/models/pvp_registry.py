import os
import time
import uuid
from typing import Dict, Optional

from ..json_codec import load
from .corpse_registry import _atomic_write_json
from ..data.world.pvp_config import PVP_INVITE_EXPIRE_SECONDS


class PvpRegistry:
    def __init__(self, data_dir: str, store=None):
        self.path = os.path.join(data_dir, "pvp_sessions.json")
        self._store = store

    def _load(self) -> Dict[str, dict]:
        if self._store is not None:
            data = self._store.get_json("kv_store", "pvp_registry")
            if data is None and os.path.exists(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as f:
                        loaded = load(f)
                    if isinstance(loaded, dict):
                        if not isinstance(loaded.get("invites"), dict):
                            loaded["invites"] = {}
                        if not isinstance(loaded.get("matches"), dict):
                            loaded["matches"] = {}
                        self._store.put_json("kv_store", "pvp_registry", loaded, updated_at=os.path.getmtime(self.path))
                        data = loaded
                except Exception:
                    return {"invites": {}, "matches": {}}
            if not isinstance(data, dict):
                return {"invites": {}, "matches": {}}
            if not isinstance(data.get("invites"), dict):
                data["invites"] = {}
            if not isinstance(data.get("matches"), dict):
                data["matches"] = {}
            return data
        if not os.path.exists(self.path):
            return {"invites": {}, "matches": {}}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = load(f)
            if not isinstance(data, dict):
                return {"invites": {}, "matches": {}}
            if not isinstance(data.get("invites"), dict):
                data["invites"] = {}
            if not isinstance(data.get("matches"), dict):
                data["matches"] = {}
            return data
        except Exception:
            return {"invites": {}, "matches": {}}

    def _save(self, data: Dict[str, dict]) -> None:
        if self._store is not None:
            self._store.put_json("kv_store", "pvp_registry", data)
            return
        _atomic_write_json(self.path, data)

    def get_invite(self, target_uid: str, now: Optional[float] = None) -> Optional[dict]:
        data = self._load()
        entry = data["invites"].get(str(target_uid))
        if not isinstance(entry, dict):
            return None
        ts = time.time() if now is None else float(now)
        if ts - float(entry.get("created_at", 0.0)) > PVP_INVITE_EXPIRE_SECONDS:
            data["invites"].pop(str(target_uid), None)
            self._save(data)
            return None
        return dict(entry)

    def set_invite(
        self,
        *,
        challenger_uid: str,
        challenger_name: str,
        target_uid: str,
        target_name: str,
        world: str,
        coord: str,
        challenger_origin: str,
        target_origin: str,
    ) -> dict:
        data = self._load()
        entry = {
            "challenger_uid": str(challenger_uid),
            "challenger_name": str(challenger_name),
            "target_uid": str(target_uid),
            "target_name": str(target_name),
            "world": str(world),
            "coord": str(coord),
            "challenger_origin": str(challenger_origin),
            "target_origin": str(target_origin),
            "created_at": time.time(),
        }
        data["invites"][str(target_uid)] = entry
        self._save(data)
        return dict(entry)

    def pop_invite(self, target_uid: str) -> Optional[dict]:
        data = self._load()
        entry = data["invites"].pop(str(target_uid), None)
        if entry is not None:
            self._save(data)
        return dict(entry) if isinstance(entry, dict) else None

    def create_match(self, match: dict) -> dict:
        data = self._load()
        match_id = str(match.get("id") or f"pvp_{uuid.uuid4().hex[:10]}")
        match["id"] = match_id
        data["matches"][match_id] = match
        self._save(data)
        return dict(match)

    def get_match(self, match_id: Optional[str]) -> Optional[dict]:
        if not match_id:
            return None
        data = self._load()
        entry = data["matches"].get(str(match_id))
        return dict(entry) if isinstance(entry, dict) else None

    def find_match_for_user(self, uid: str) -> Optional[dict]:
        data = self._load()
        s_uid = str(uid)
        for entry in data["matches"].values():
            if not isinstance(entry, dict):
                continue
            if str(entry.get("p1_uid", "")) == s_uid or str(entry.get("p2_uid", "")) == s_uid:
                return dict(entry)
        return None

    def save_match(self, match: dict) -> None:
        match_id = str(match.get("id", ""))
        if not match_id:
            return
        data = self._load()
        data["matches"][match_id] = match
        self._save(data)

    def remove_match(self, match_id: Optional[str]) -> Optional[dict]:
        if not match_id:
            return None
        data = self._load()
        removed = data["matches"].pop(str(match_id), None)
        if removed is not None:
            self._save(data)
        return dict(removed) if isinstance(removed, dict) else None
