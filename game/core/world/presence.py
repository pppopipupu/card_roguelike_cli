import os
import threading
import time
from datetime import datetime, timezone

from ...data.locale_data import get_locale_text
from ...data.outer_plane_config import (
    OUTER_PLANE_ACTIVE_FLAG,
    OUTER_PLANE_ROOM_KEY,
    OUTER_PLANE_START_ROOM,
)
from ...data.town_map_config import TOWN_ROOM_COORDS
from ...data.world_social_config import (
    WORLD_OUTER_PLANE,
    WORLD_PRESENCE_FILE,
    WORLD_PRESENCE_TIMEOUT_SECONDS,
    WORLD_LIVE_MESSAGE_LIMIT,
    WORLD_SNOWFIELD,
    WORLD_TOWN,
)
from ...data.yog_quest_config import YOG_FLOOR_WILDS
from ...json_codec import load
from ...models.manager import _atomic_write_json

_REGISTRY_LOCK = threading.RLock()
_ACTIVE_SERVICE = None


def _now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _class_text(stats) -> str:
    base = getattr(stats, "selected_class", "")
    sub = getattr(stats, "selected_subclass", "")
    if not sub:
        return base
    return f"{base}{get_locale_text('i18n_social.common.class_separator')}{sub}"


class WorldPresenceService:
    def __init__(self, save_manager):
        self.save_manager = save_manager

    def _path(self) -> str:
        return os.path.join(self.save_manager.data_dir, WORLD_PRESENCE_FILE)

    def _load(self) -> tuple[dict[str, dict], bool]:
        path = self._path()
        if not os.path.exists(path):
            return {}, False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = load(f)
        except (OSError, ValueError, TypeError):
            return {}, False
        if not isinstance(data, dict):
            return {}, False
        entries = {}
        for uid, entry in data.items():
            if isinstance(uid, str) and isinstance(entry, dict):
                entries[uid] = entry
        return self._prune(entries)

    def _prune(self, entries: dict[str, dict], now: float | None = None) -> tuple[dict[str, dict], bool]:
        current = time.time() if now is None else now
        kept = {}
        changed = False
        for uid, entry in entries.items():
            try:
                last_active = float(entry.get("last_active_ts", 0) or 0)
            except (TypeError, ValueError):
                last_active = 0
            if not last_active or current - last_active > WORLD_PRESENCE_TIMEOUT_SECONDS:
                changed = True
                continue
            world = entry.get("world")
            if world not in (WORLD_TOWN, WORLD_SNOWFIELD, WORLD_OUTER_PLANE):
                changed = True
                continue
            kept[uid] = entry
        return kept, changed

    def _write(self, entries: dict[str, dict]) -> None:
        _atomic_write_json(self._path(), entries, indent=0)

    def _active_entries(self, world: str | None = None) -> dict[str, dict]:
        with _REGISTRY_LOCK:
            entries, changed = self._load()
            if changed:
                self._write(entries)
            if world is None:
                return dict(entries)
            return {uid: entry for uid, entry in entries.items() if entry.get("world") == world}

    def touch(self, uid: str, world: str, coord: str) -> None:
        if not uid or world not in (WORLD_TOWN, WORLD_SNOWFIELD, WORLD_OUTER_PLANE):
            return
        stats = self.save_manager.load_stats(uid)
        with _REGISTRY_LOCK:
            entries, _ = self._load()
            previous = entries.get(uid) or {}
            pending = previous.get("pending_messages")
            if not isinstance(pending, list):
                pending = []
            entry = {
                "user_id": uid,
                "name": getattr(stats, "player_name", "") or get_locale_text("i18n_world_social.default_player_name"),
                "player_id": getattr(stats, "player_handle", "") or getattr(stats, "player_name", ""),
                "class_text": _class_text(stats),
                "world": world,
                "coord": str(coord or ""),
                "last_active": _now_text(),
                "last_active_ts": time.time(),
                "pending_messages": pending[-WORLD_LIVE_MESSAGE_LIMIT:],
            }
            entries[uid] = entry
            self._write(entries)

    def send_live(self, target_uid: str, from_uid: str, from_name: str, text: str) -> bool:
        if not target_uid or not text:
            return False
        with _REGISTRY_LOCK:
            entries, _ = self._load()
            entry = entries.get(target_uid)
            if not entry:
                return False
            pending = entry.get("pending_messages")
            if not isinstance(pending, list):
                pending = []
            pending.append({
                "from_uid": from_uid,
                "from_name": from_name,
                "text": text,
                "time": _now_text(),
            })
            entry["pending_messages"] = pending[-WORLD_LIVE_MESSAGE_LIMIT:]
            entries[target_uid] = entry
            self._write(entries)
            return True

    def pop_live(self, uid: str) -> list[dict]:
        if not uid:
            return []
        with _REGISTRY_LOCK:
            entries, _ = self._load()
            entry = entries.get(uid)
            if not entry:
                return []
            pending = entry.get("pending_messages")
            if not isinstance(pending, list) or not pending:
                return []
            entry["pending_messages"] = []
            entries[uid] = entry
            self._write(entries)
            return [item for item in pending if isinstance(item, dict)]

    def leave(self, uid: str) -> None:
        if not uid:
            return
        with _REGISTRY_LOCK:
            entries, changed = self._load()
            if uid in entries:
                del entries[uid]
                changed = True
            if changed:
                self._write(entries)

    def get(self, uid: str) -> dict | None:
        return self._active_entries().get(uid)

    def players(self, world: str, coord: str | None = None, exclude_uid: str = "") -> list[dict]:
        entries = self._active_entries(world)
        result = []
        for uid, entry in entries.items():
            if uid == exclude_uid:
                continue
            if coord is not None and str(entry.get("coord", "")) != str(coord):
                continue
            result.append(dict(entry))
        return sorted(result, key=lambda item: (item.get("name", ""), item.get("user_id", "")))

    def resolve_location(self, uid: str, stats=None, run=None) -> tuple[str, str] | None:
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        if run is None:
            run = self.save_manager.load_save(uid)
        outer_active = bool(stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG))
        if run is not None:
            floor_map = getattr(run, "floor_map", None)
            if floor_map is not None and floor_map.floor_flags.get("yog_quest"):
                if floor_map.floor_index != YOG_FLOOR_WILDS:
                    return None
                coord = floor_map.player_coords.get(uid, "")
                if not coord:
                    return None
                return WORLD_SNOWFIELD, coord
            if outer_active:
                room = stats.town_flags.get(OUTER_PLANE_ROOM_KEY) or OUTER_PLANE_START_ROOM
                return WORLD_OUTER_PLANE, str(room)
            if stats.in_town and run.node_data.get("is_town_combat"):
                return WORLD_TOWN, TOWN_ROOM_COORDS.get(stats.town_pos, "C2")
            return None
        if not stats.in_town:
            return None
        if outer_active:
            room = stats.town_flags.get(OUTER_PLANE_ROOM_KEY) or OUTER_PLANE_START_ROOM
            return WORLD_OUTER_PLANE, str(room)
        return WORLD_TOWN, TOWN_ROOM_COORDS.get(stats.town_pos, "C2")

    def sync(self, uid: str, stats=None, run=None) -> tuple[str, str] | None:
        location = self.resolve_location(uid, stats=stats, run=run)
        if location is None:
            self.leave(uid)
            return None
        self.touch(uid, location[0], location[1])
        return location


def set_active_service(service: WorldPresenceService) -> None:
    global _ACTIVE_SERVICE
    _ACTIVE_SERVICE = service


def active_service() -> WorldPresenceService | None:
    return _ACTIVE_SERVICE


def sync_active(uid: str, stats=None, run=None) -> tuple[str, str] | None:
    service = _ACTIVE_SERVICE
    if service is None:
        return None
    return service.sync(uid, stats=stats, run=run)


def render_players(world: str, coord: str | None = None, exclude_uid: str = "") -> list[dict]:
    service = _ACTIVE_SERVICE
    if service is None:
        return []
    return service.players(world, coord=coord, exclude_uid=exclude_uid)
