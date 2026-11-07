import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(user_id: str) -> str:
    return "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))


class AccountStore:
    def __init__(self, db_path: Path, player_dir: Path):
        self.db_path = Path(db_path)
        self.player_dir = Path(player_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.player_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                im_user_id TEXT UNIQUE,
                web_user_id TEXT UNIQUE,
                display_name TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _row(self, row: sqlite3.Row) -> dict:
        return {
            "uuid": row["id"],
            "im_user_id": row["im_user_id"],
            "web_user_id": row["web_user_id"],
            "display_name": row["display_name"],
            "created_at": row["created_at"],
            "last_seen": row["last_seen"],
        }

    def _get_by(self, column: str, value: str) -> Optional[dict]:
        row = self._conn.execute(
            f"SELECT * FROM players WHERE {column} = ?", (value,)
        ).fetchone()
        return self._row(row) if row else None

    def get(self, player_id: str) -> Optional[dict]:
        with self._lock:
            return self._get_by("id", player_id)

    def get_by_web(self, web_user_id: str) -> Optional[dict]:
        with self._lock:
            return self._get_by("web_user_id", web_user_id)

    def get_by_im(self, im_user_id: str) -> Optional[dict]:
        with self._lock:
            return self._get_by("im_user_id", im_user_id)

    def get_or_create_web(self, web_user_id: str, display_name: str = "") -> dict:
        with self._lock:
            existing = self._get_by("web_user_id", web_user_id)
            if existing:
                self._touch(existing["uuid"], display_name)
                return self._get_by("id", existing["uuid"])
            player_id = str(uuid.uuid4())
            now = _now()
            try:
                self._conn.execute(
                    "INSERT INTO players (id, im_user_id, web_user_id, display_name, created_at, last_seen) VALUES (?, NULL, ?, ?, ?, ?)",
                    (player_id, web_user_id, display_name or None, now, now),
                )
                self._conn.commit()
            except sqlite3.IntegrityError:
                self._conn.rollback()
                existing = self._get_by("web_user_id", web_user_id)
                if not existing:
                    raise
                return existing
            return self._get_by("id", player_id)

    def get_or_create_im(self, im_user_id: str, display_name: str = "") -> dict:
        with self._lock:
            existing = self._get_by("im_user_id", im_user_id)
            if existing:
                self._touch(existing["uuid"], display_name)
                return self._get_by("id", existing["uuid"])
            player_id = str(uuid.uuid4())
            now = _now()
            try:
                self._conn.execute(
                    "INSERT INTO players (id, im_user_id, web_user_id, display_name, created_at, last_seen) VALUES (?, ?, NULL, ?, ?, ?)",
                    (player_id, im_user_id, display_name or None, now, now),
                )
                self._conn.commit()
            except sqlite3.IntegrityError:
                self._conn.rollback()
                existing = self._get_by("im_user_id", im_user_id)
                if not existing:
                    raise
                return existing
            return self._get_by("id", player_id)

    def _touch(self, player_id: str, display_name: str = "") -> None:
        now = _now()
        if display_name:
            self._conn.execute(
                "UPDATE players SET last_seen = ?, display_name = ? WHERE id = ?",
                (now, display_name, player_id),
            )
        else:
            self._conn.execute(
                "UPDATE players SET last_seen = ? WHERE id = ?", (now, player_id)
            )
        self._conn.commit()

    def touch(self, player_id: str, display_name: str = "") -> None:
        with self._lock:
            self._touch(player_id, display_name)

    def has_progress(self, player_id: str) -> bool:
        safe = _safe_id(player_id)
        if (self.player_dir / f"user_{safe}.json").exists():
            return True
        stats_path = self.player_dir / f"stats_{safe}.json"
        if not stats_path.exists():
            return False
        try:
            data = json.loads(stats_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return True
        counters = (
            "total_damage",
            "total_kills",
            "total_stages",
            "gp",
            "yog_sothoth_kill_count",
            "yog_sothoth_challenge_count",
            "town_health_bonus",
        )
        if any(data.get(key) for key in counters):
            return True
        flags = (
            "rogue_mode",
            "in_town",
            "killed_icerainboww",
            "unlocked_gatekey",
        )
        if any(data.get(key) for key in flags):
            return True
        lists = (
            "unlocked_subclasses",
            "locked_cards",
            "purchased_pool",
            "defeated_town_npcs",
            "town_inventory",
            "unlocked_new_cards",
        )
        if any(data.get(key) for key in lists):
            return True
        if data.get("town_flags"):
            return True
        if data.get("selected_class") not in (None, "法师"):
            return True
        if data.get("selected_subclass"):
            return True
        return False

    def _delete_files(self, player_id: str) -> None:
        safe = _safe_id(player_id)
        for name in (f"user_{safe}.json", f"stats_{safe}.json"):
            path = self.player_dir / name
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def bind_web(
        self, web_user_id: str, target_uuid: str, force: bool = False
    ) -> tuple[str, Optional[dict], str]:
        with self._lock:
            target = self._get_by("id", target_uuid)
            if not target:
                return "not_found", None, "该 UUID 不存在，请确认绑定码。"
            if target["web_user_id"] == web_user_id:
                return "ok", target, "该 UUID 已经绑定到当前网页账号。"
            if target["web_user_id"] and target["web_user_id"] != web_user_id:
                return "taken", None, "该 UUID 已经绑定了其他网页账号。"
            current = self._get_by("web_user_id", web_user_id)
            if not current:
                current = self.get_or_create_web(web_user_id)
            if current["uuid"] == target_uuid:
                return "ok", target, "该 UUID 已经绑定到当前网页账号。"
            if current["im_user_id"]:
                return (
                    "conflict",
                    None,
                    "当前网页账号已关联一个即时通讯玩家，无法直接切换绑定。",
                )
            if not force and self.has_progress(current["uuid"]):
                return (
                    "need_force",
                    None,
                    "当前网页账号已有独立进度。若确认放弃该进度并绑定目标 UUID，请输入：绑定 "
                    + target_uuid
                    + " force",
                )
            if force:
                self._delete_files(current["uuid"])
            now = _now()
            try:
                self._conn.execute("DELETE FROM players WHERE id = ?", (current["uuid"],))
                self._conn.execute(
                    "UPDATE players SET web_user_id = ?, last_seen = ? WHERE id = ?",
                    (web_user_id, now, target_uuid),
                )
                self._conn.commit()
            except sqlite3.IntegrityError:
                self._conn.rollback()
                return "taken", None, "该 UUID 已经绑定了其他网页账号。"
            return "ok", self._get_by("id", target_uuid), "绑定成功。"

    def list_all(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM players ORDER BY created_at ASC"
            ).fetchall()
            return [self._row(row) for row in rows]

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM players").fetchone()
            return int(row["n"])
