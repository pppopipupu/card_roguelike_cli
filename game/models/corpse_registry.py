import os
import random
import sqlite3
import tempfile
import threading
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from .state import GameRun, ensure_card_state
from ..json_codec import dumps, load
from ..data.entities.corpse_config import CorpseConfig
from ..data.text.locale_data import get_locale_text

_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: str, data, indent: int = 2) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".rogue-corpse-", suffix=".tmp", dir=directory or None)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(dumps(data, indent=indent > 0))
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


class CorpseRegistry:
    def __init__(self, data_dir: str, store=None):
        self.path = os.path.join(data_dir, "corpses.json")
        self._store = store

    def _load(self) -> dict:
        if self._store is not None:
            try:
                data = self._store.get_json("kv_store", "corpses")
                if data is None and os.path.exists(self.path):
                    with open(self.path, "r", encoding="utf-8") as handle:
                        loaded = load(handle)
                    if isinstance(loaded, dict):
                        if not isinstance(loaded.get("corpses"), list):
                            loaded["corpses"] = []
                        self._store.put_json("kv_store", "corpses", loaded, updated_at=os.path.getmtime(self.path))
                        data = loaded
            except (OSError, ValueError, TypeError, sqlite3.Error):
                return {"corpses": []}
            if not isinstance(data, dict):
                return {"corpses": []}
            if not isinstance(data.get("corpses"), list):
                data["corpses"] = []
            return data
        if not os.path.exists(self.path):
            return {"corpses": []}
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = load(handle)
            if not isinstance(data, dict):
                return {"corpses": []}
            if not isinstance(data.get("corpses"), list):
                data["corpses"] = []
            return data
        except (OSError, ValueError):
            return {"corpses": []}

    def _save(self, data: dict) -> None:
        if self._store is not None:
            self._store.put_json("kv_store", "corpses", data)
            return
        _atomic_write_json(self.path, data)

    def create_from_run(self, run: GameRun, cause: str) -> Optional[dict]:
        player = getattr(run, "player", None)
        if player is None or not getattr(player, "deck", None):
            return None
        from ..data.world.grid_map_config import format_display_floor, get_run_floor_index
        floor_index = get_run_floor_index(run)
        floor_label = format_display_floor(floor_index)
        fm = getattr(run, "floor_map", None)
        cleared_rooms = sum(1 for r in fm.rooms.values() if r.cleared) if fm is not None else 0
        gold = int(getattr(player, "gold", 0))
        qualifies_gp = float(floor_index) >= CorpseConfig.MIN_FLOOR_FOR_GP or cleared_rooms >= CorpseConfig.MIN_CLEARED_ROOMS_FOR_GP
        gp_pool = gold * CorpseConfig.GP_MULTIPLIER if qualifies_gp else 0
        corpse = {
            "id": uuid.uuid4().hex,
            "floor": floor_index,
            "user_id": str(getattr(run, "user_id", "")),
            "player_name": str(getattr(player, "name", "玩家")),
            "cause": str(cause or "").strip() or get_locale_text("i18n_models.corpse_registry.fall_at_stage", stage=floor_label),
            "gold": gold,
            "gp_pool": max(0, gp_pool),
            "max_hp": int(getattr(player, "max_hp", 1)),
            "selected_class": str(getattr(player, "selected_class", "法师")),
            "deck": [asdict(ensure_card_state(card)) for card in player.deck],
            "created_at": _now(),
            "claimed_by": "",
            "claimed_at": "",
            "gp_reward": 0,
        }
        with _LOCK:
            data = self._load()
            data["corpses"].append(corpse)
            self._save(data)
        return corpse

    def list_at_floor(self, floor_index: int | float, exclude_user: str = "") -> list[dict]:
        with _LOCK:
            data = self._load()
            result = []
            for corpse in data["corpses"]:
                corpse_floor = corpse.get("floor")
                if corpse_floor is None or float(corpse_floor) != float(floor_index):
                    continue
                if corpse.get("claimed_by"):
                    continue
                if exclude_user and corpse.get("user_id") == exclude_user:
                    continue
                result.append(corpse)
            result.sort(key=lambda item: item.get("created_at", ""), reverse=True)
            return result

    def get(self, corpse_id: str) -> Optional[dict]:
        with _LOCK:
            data = self._load()
            for corpse in data["corpses"]:
                if corpse.get("id") == corpse_id:
                    return corpse
        return None

    def claim(self, corpse_id: str, user_id: str) -> Optional[dict]:
        with _LOCK:
            data = self._load()
            for corpse in data["corpses"]:
                if corpse.get("id") != corpse_id:
                    continue
                if corpse.get("claimed_by"):
                    return None
                gp_pool = max(0, int(corpse.get("gp_pool", 0)))
                percent = random.randint(
                    CorpseConfig.LOOT_GP_MIN_PERCENT,
                    CorpseConfig.LOOT_GP_MAX_PERCENT,
                )
                corpse["gp_reward"] = int(gp_pool * percent / 100)
                corpse["claimed_by"] = str(user_id)
                corpse["claimed_at"] = _now()
                self._save(data)
                return corpse
        return None

    def remove(self, corpse_id: str) -> None:
        with _LOCK:
            data = self._load()
            data["corpses"] = [
                corpse for corpse in data["corpses"] if corpse.get("id") != corpse_id
            ]
            self._save(data)
