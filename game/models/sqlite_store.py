from contextlib import contextmanager
import os
import sqlite3
import threading
import time
from typing import Any, Iterator, Optional
import weakref

from ..json_codec import dumps, loads

_TABLE_PK_COLS: dict[str, str] = {
    "user_stats": "user_id",
    "run_saves": "run_id",
    "kv_store": "key",
}

_MISSING = object()
_LIVE_STORES: "weakref.WeakSet[SqliteStore]" = weakref.WeakSet()
_SHARED_STORES: dict[str, "SqliteStore"] = {}
_LIVE_STORES_LOCK = threading.RLock()
_PATH_EPOCHS: dict[str, int] = {}


def close_stores_under(directory: str) -> None:
    if not directory:
        return
    norm_dir = os.path.normcase(os.path.abspath(directory))
    with _LIVE_STORES_LOCK:
        stores = list(_LIVE_STORES)
    for store in stores:
        norm_db = os.path.normcase(os.path.abspath(store.db_path))
        if norm_db == norm_dir or norm_db.startswith(norm_dir + os.sep):
            store.close()


class SqliteStore:
    @classmethod
    def for_path(cls, db_path: str) -> "SqliteStore":
        norm_path = os.path.normcase(os.path.abspath(db_path))
        with _LIVE_STORES_LOCK:
            existing = _SHARED_STORES.get(norm_path)
            if existing is not None:
                return existing
            store = cls(db_path)
            _SHARED_STORES[norm_path] = store
            return store

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._norm_path = os.path.normcase(os.path.abspath(db_path))
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._cache: dict[tuple[str, str], tuple[bytes, float]] = {}
        with _LIVE_STORES_LOCK:
            self._epoch = _PATH_EPOCHS.get(self._norm_path, 0)
        self._tx_depth = 0
        self._tx_dirty = False
        self._tx_undo: dict[tuple[str, str], Any] = {}
        self._finalizer = weakref.finalize(self, self._close_conn_ref, None)
        self._ensure_conn()
        with _LIVE_STORES_LOCK:
            _LIVE_STORES.add(self)

    @staticmethod
    def _close_conn_ref(conn: Optional[sqlite3.Connection]) -> None:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA temp_store=MEMORY")
        for table, pk_col in _TABLE_PK_COLS.items():
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ("
                f"{pk_col} TEXT PRIMARY KEY, "
                f"payload BLOB NOT NULL, "
                f"updated_at REAL NOT NULL)"
            )
        self._conn = conn
        self._finalizer.detach()
        self._finalizer = weakref.finalize(self, self._close_conn_ref, conn)
        return conn

    def close(self) -> None:
        with _LIVE_STORES_LOCK:
            if _SHARED_STORES.get(self._norm_path) is self:
                _SHARED_STORES.pop(self._norm_path, None)
        with self._lock:
            conn = self._conn
            self._conn = None
            self._tx_depth = 0
            self._tx_dirty = False
            self._tx_undo.clear()
            self._cache.clear()
            self._finalizer.detach()
            if conn is not None:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass

    def _sync_epoch(self) -> None:
        with _LIVE_STORES_LOCK:
            global_epoch = _PATH_EPOCHS.get(self._norm_path, 0)
        if self._epoch != global_epoch:
            self._cache.clear()
            self._epoch = global_epoch

    def _bump_epoch(self) -> None:
        with _LIVE_STORES_LOCK:
            new_epoch = _PATH_EPOCHS.get(self._norm_path, 0) + 1
            _PATH_EPOCHS[self._norm_path] = new_epoch
        self._epoch = new_epoch

    def _rollback_tx(self, conn: sqlite3.Connection) -> None:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        for ck, prev in self._tx_undo.items():
            if prev is _MISSING:
                self._cache.pop(ck, None)
            else:
                self._cache[ck] = prev
        self._tx_undo = {}
        self._tx_dirty = False

    @contextmanager
    def batch(self) -> Iterator[None]:
        with self._lock:
            conn = self._ensure_conn()
            is_outer = self._tx_depth == 0
            if is_outer:
                self._sync_epoch()
                self._tx_undo = {}
                self._tx_dirty = False
                conn.execute("BEGIN IMMEDIATE")
            self._tx_depth += 1
            try:
                yield
            except BaseException:
                self._tx_depth -= 1
                if is_outer:
                    self._rollback_tx(conn)
                raise
            else:
                self._tx_depth -= 1
                if is_outer:
                    try:
                        conn.execute("COMMIT")
                    except BaseException:
                        self._rollback_tx(conn)
                        raise
                    if self._tx_dirty:
                        self._bump_epoch()
                    self._tx_undo = {}
                    self._tx_dirty = False

    def _record_undo(self, cache_key: tuple[str, str]) -> None:
        if self._tx_depth > 0 and cache_key not in self._tx_undo:
            self._tx_undo[cache_key] = self._cache.get(cache_key, _MISSING)

    def get_row(self, table: str, key: str) -> Optional[tuple[bytes, float]]:
        pk_col = _TABLE_PK_COLS[table]
        cache_key = (table, key)
        with self._lock:
            if self._tx_depth == 0:
                self._sync_epoch()
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
            conn = self._ensure_conn()
            row = conn.execute(
                f"SELECT payload, updated_at FROM {table} WHERE {pk_col} = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            blob = bytes(row[0])
            ts = float(row[1])
            entry = (blob, ts)
            self._cache[cache_key] = entry
            return entry

    def get_json(self, table: str, key: str) -> Any:
        row = self.get_row(table, key)
        if row is None:
            return None
        return loads(row[0])

    def put_bytes(self, table: str, key: str, blob: bytes, updated_at: Optional[float] = None) -> None:
        pk_col = _TABLE_PK_COLS[table]
        ts = time.time() if updated_at is None else float(updated_at)
        cache_key = (table, key)
        with self._lock:
            if self._tx_depth == 0:
                self._sync_epoch()
            conn = self._ensure_conn()
            self._record_undo(cache_key)
            conn.execute(
                f"INSERT OR REPLACE INTO {table} ({pk_col}, payload, updated_at) VALUES (?, ?, ?)",
                (key, sqlite3.Binary(blob), ts),
            )
            self._cache[cache_key] = (blob, ts)
            if self._tx_depth > 0:
                self._tx_dirty = True
            else:
                self._bump_epoch()

    def put_json(self, table: str, key: str, data: Any, updated_at: Optional[float] = None) -> None:
        blob = dumps(data, indent=False)
        self.put_bytes(table, key, blob, updated_at=updated_at)

    def delete(self, table: str, key: str) -> bool:
        pk_col = _TABLE_PK_COLS[table]
        cache_key = (table, key)
        with self._lock:
            if self._tx_depth == 0:
                self._sync_epoch()
            conn = self._ensure_conn()
            self._record_undo(cache_key)
            cur = conn.execute(f"DELETE FROM {table} WHERE {pk_col} = ?", (key,))
            self._cache.pop(cache_key, None)
            if self._tx_depth > 0:
                self._tx_dirty = True
            else:
                self._bump_epoch()
            return cur.rowcount > 0

    def exists(self, table: str, key: str) -> bool:
        return self.get_row(table, key) is not None

    def list_rows(self, table: str) -> list[tuple[str, bytes, float]]:
        pk_col = _TABLE_PK_COLS[table]
        with self._lock:
            if self._tx_depth == 0:
                self._sync_epoch()
            conn = self._ensure_conn()
            rows = conn.execute(
                f"SELECT {pk_col}, payload, updated_at FROM {table}"
            ).fetchall()
            result: list[tuple[str, bytes, float]] = []
            for key, payload, updated_at in rows:
                blob = bytes(payload)
                ts = float(updated_at)
                self._cache[(table, str(key))] = (blob, ts)
                result.append((str(key), blob, ts))
            return result
