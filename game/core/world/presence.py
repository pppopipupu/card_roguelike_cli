import os
import sqlite3
import threading
import time
from datetime import datetime, timezone

from ...data.text.locale_data import get_locale_text
from ...data.world.outer_plane_config import (
    OUTER_PLANE_ACTIVE_FLAG,
    OUTER_PLANE_ROOM_KEY,
    OUTER_PLANE_START_ROOM,
)
from ...data.world.town_map_config import TOWN_ROOM_COORDS
from ...data.world.world_social_config import (
    WORLD_COOP_PREFIX,
    WORLD_LIVE_MESSAGE_LIMIT,
    WORLD_OUTER_PLANE,
    WORLD_PRESENCE_FILE,
    WORLD_PRESENCE_TIMEOUT_SECONDS,
    WORLD_SNOWFIELD,
    WORLD_TOWN,
)
from ...data.world.yog_quest_config import YOG_FLOOR_WILDS
from ...json_codec import load
from ...models.manager import _atomic_write_json

_REGISTRY_LOCK = threading.RLock()
_ACTIVE_SERVICE = None


def _now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _is_valid_world(world: object) -> bool:
    if world in (WORLD_TOWN, WORLD_SNOWFIELD, WORLD_OUTER_PLANE):
        return True
    return isinstance(world, str) and world.startswith(WORLD_COOP_PREFIX) and len(world) > len(WORLD_COOP_PREFIX)


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
        store = getattr(self.save_manager, "store", None)
        data = None
        if store is not None:
            try:
                data = store.get_json("kv_store", "world_presence")
                if data is None:
                    path = self._path()
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as f:
                            loaded = load(f)
                        if isinstance(loaded, dict):
                            store.put_json("kv_store", "world_presence", loaded, updated_at=os.path.getmtime(path))
                            data = loaded
            except (OSError, ValueError, TypeError, sqlite3.Error):
                return {}, False
        else:
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
            if not _is_valid_world(world):
                changed = True
                continue
            kept[uid] = entry
        return kept, changed

    def _write(self, entries: dict[str, dict]) -> None:
        store = getattr(self.save_manager, "store", None)
        if store is not None:
            store.put_json("kv_store", "world_presence", entries)
            return
        _atomic_write_json(self._path(), entries, indent=0)

    def _active_entries(self, world: str | None = None) -> dict[str, dict]:
        with _REGISTRY_LOCK:
            entries, changed = self._load()
            if changed:
                self._write(entries)
            if world is None:
                return dict(entries)
            return {uid: entry for uid, entry in entries.items() if entry.get("world") == world}

    def _build_entry(self, uid: str, world: str, coord: str, stats, previous: dict, now: float) -> tuple[dict, bool]:
        pending = previous.get("pending_messages")
        if not isinstance(pending, list):
            pending = []
        name = getattr(stats, "player_name", "") or get_locale_text("i18n_world_social.default_player_name")
        player_id = getattr(stats, "player_handle", "") or getattr(stats, "player_name", "")
        class_text = _class_text(stats)
        coord_str = str(coord or "")
        prev_ts = float(previous.get("last_active_ts", 0) or 0)
        unchanged = (
            previous.get("world") == world
            and previous.get("coord") == coord_str
            and previous.get("name") == name
            and previous.get("player_id") == player_id
            and previous.get("class_text") == class_text
            and prev_ts > 0
            and (now - prev_ts) < 15.0
        )
        entry = {
            "user_id": uid,
            "name": name,
            "player_id": player_id,
            "class_text": class_text,
            "world": world,
            "coord": coord_str,
            "last_active": _now_text(),
            "last_active_ts": now,
            "pending_messages": pending[-WORLD_LIVE_MESSAGE_LIMIT:],
        }
        return entry, not unchanged

    def touch(self, uid: str, world: str, coord: str, stats=None) -> None:
        if not uid or not _is_valid_world(world):
            return
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        now = time.time()
        with _REGISTRY_LOCK:
            entries, changed = self._load()
            previous = entries.get(uid) or {}
            entry, dirty = self._build_entry(uid, world, coord, stats, previous, now)
            if dirty or changed:
                entries[uid] = entry
                self._write(entries)

    def sync_many(self, uids, *, stats_by_uid: dict | None = None, run=None) -> None:
        if not uids:
            return
        stats_map = stats_by_uid if isinstance(stats_by_uid, dict) else {}
        now = time.time()
        updates = []
        leaves = []
        for uid in uids:
            if not uid:
                continue
            st = stats_map.get(uid)
            if st is None:
                st = self.save_manager.load_stats(uid)
            loc = self.resolve_location(uid, stats=st, run=run)
            if loc is None:
                leaves.append(uid)
            elif _is_valid_world(loc[0]):
                updates.append((uid, loc[0], loc[1], st))
        with _REGISTRY_LOCK:
            entries, changed = self._load()
            for uid in leaves:
                if uid in entries:
                    del entries[uid]
                    changed = True
            for uid, world, coord, st in updates:
                previous = entries.get(uid) or {}
                entry, dirty = self._build_entry(uid, world, coord, st, previous, now)
                if dirty:
                    entries[uid] = entry
                    changed = True
            if changed:
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
            coop_id = str(getattr(run, "coop_id", "") or "")
            if floor_map is not None:
                if floor_map.floor_flags.get("yog_quest"):
                    coord = floor_map.player_coords.get(uid, "")
                    if floor_map.floor_index == YOG_FLOOR_WILDS:
                        if not coord:
                            return None
                        return WORLD_SNOWFIELD, coord
                    if coop_id and coord:
                        return f"{WORLD_COOP_PREFIX}{coop_id}", f"{floor_map.floor_index}:{coord}"
                    return None
                if coop_id:
                    coord = floor_map.player_coords.get(uid, "")
                    if not coord:
                        return None
                    return f"{WORLD_COOP_PREFIX}{coop_id}", f"{floor_map.floor_index}:{coord}"
                if outer_active:
                    room = stats.town_flags.get(OUTER_PLANE_ROOM_KEY) or OUTER_PLANE_START_ROOM
                    return WORLD_OUTER_PLANE, str(room)
                if stats.in_town and run.node_data.get("is_town_combat"):
                    return WORLD_TOWN, TOWN_ROOM_COORDS.get(stats.town_pos, "C2")
                return None
            if coop_id:
                return f"{WORLD_COOP_PREFIX}{coop_id}", "0:START"
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
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        location = self.resolve_location(uid, stats=stats, run=run)
        if location is None:
            self.leave(uid)
            return None
        self.touch(uid, location[0], location[1], stats=stats)
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


def sync_active_many(uids, *, stats_by_uid: dict | None = None, run=None) -> None:
    service = _ACTIVE_SERVICE
    if service is None:
        return
    service.sync_many(uids, stats_by_uid=stats_by_uid, run=run)


def render_players(world: str, coord: str | None = None, exclude_uid: str = "") -> list[dict]:
    service = _ACTIVE_SERVICE
    if service is None:
        return []
    return service.players(world, coord=coord, exclude_uid=exclude_uid)


def render_players_for(uid: str, stats=None, run=None) -> list[dict]:
    service = _ACTIVE_SERVICE
    if service is None or not uid:
        return []
    location = service.resolve_location(uid, stats=stats, run=run)
    if location is None:
        return []
    return service.players(location[0], coord=location[1], exclude_uid=uid)
