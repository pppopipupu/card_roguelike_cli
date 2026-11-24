import os
import time
import uuid
from typing import Dict, Optional

from ..data.progression.trade_config import TRADE_OFFER_EXPIRE_SECONDS, TRADE_OFFER_FILE
from ..json_codec import load
from .corpse_registry import _atomic_write_json


class TradeRegistry:
    def __init__(self, data_dir: str, store=None):
        self.path = os.path.join(data_dir, TRADE_OFFER_FILE)
        self._store = store

    def _load(self) -> Dict[str, dict]:
        if self._store is not None:
            data = self._store.get_json("kv_store", "trade_registry")
            if data is None and os.path.exists(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as f:
                        loaded = load(f)
                    if isinstance(loaded, dict):
                        if not isinstance(loaded.get("offers"), dict):
                            loaded["offers"] = {}
                        self._store.put_json("kv_store", "trade_registry", loaded, updated_at=os.path.getmtime(self.path))
                        data = loaded
                except Exception:
                    return {"offers": {}}
            if not isinstance(data, dict):
                return {"offers": {}}
            if not isinstance(data.get("offers"), dict):
                data["offers"] = {}
            return data
        if not os.path.exists(self.path):
            return {"offers": {}}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = load(f)
            if not isinstance(data, dict):
                return {"offers": {}}
            if not isinstance(data.get("offers"), dict):
                data["offers"] = {}
            return data
        except Exception:
            return {"offers": {}}

    def _save(self, data: Dict[str, dict]) -> None:
        if self._store is not None:
            self._store.put_json("kv_store", "trade_registry", data)
            return
        _atomic_write_json(self.path, data)

    def _live(self, data: Dict[str, dict], now: Optional[float] = None) -> Dict[str, dict]:
        current = time.time() if now is None else float(now)
        offers = data.get("offers")
        if not isinstance(offers, dict):
            offers = {}
            data["offers"] = offers
        kept = {}
        for offer_id, offer in offers.items():
            if not isinstance(offer, dict):
                continue
            try:
                created_at = float(offer.get("created_at", 0) or 0)
            except (TypeError, ValueError):
                created_at = 0
            if not created_at or current - created_at > TRADE_OFFER_EXPIRE_SECONDS:
                continue
            kept[str(offer_id)] = offer
        return kept

    def create(self, offer: dict) -> dict:
        data = self._load()
        offers = self._live(data)
        offer_id = f"trd_{uuid.uuid4().hex[:8]}"
        entry = dict(offer)
        entry["id"] = offer_id
        entry["created_at"] = time.time()
        offers[offer_id] = entry
        data["offers"] = offers
        self._save(data)
        return dict(entry)

    def incoming(self, uid: str) -> list[dict]:
        data = self._load()
        offers = self._live(data)
        result = [
            dict(offer)
            for offer in offers.values()
            if str(offer.get("to_uid", "")) == str(uid)
        ]
        return sorted(result, key=lambda offer: float(offer.get("created_at", 0) or 0), reverse=True)

    def outgoing(self, uid: str) -> list[dict]:
        data = self._load()
        offers = self._live(data)
        result = [
            dict(offer)
            for offer in offers.values()
            if str(offer.get("from_uid", "")) == str(uid)
        ]
        return sorted(result, key=lambda offer: float(offer.get("created_at", 0) or 0), reverse=True)

    def get(self, offer_id: str) -> Optional[dict]:
        if not offer_id:
            return None
        data = self._load()
        offers = self._live(data)
        offer = offers.get(str(offer_id))
        return dict(offer) if isinstance(offer, dict) else None

    def pop(self, offer_id: str) -> Optional[dict]:
        data = self._load()
        offers = self._live(data)
        removed = offers.pop(str(offer_id), None)
        data["offers"] = offers
        if removed is not None:
            self._save(data)
        return dict(removed) if isinstance(removed, dict) else None

    def remove_pair(self, from_uid: str, to_uid: str) -> list[dict]:
        data = self._load()
        offers = self._live(data)
        removed = []
        for offer_id, offer in list(offers.items()):
            if str(offer.get("from_uid", "")) != str(from_uid):
                continue
            if str(offer.get("to_uid", "")) != str(to_uid):
                continue
            removed.append(dict(offer))
            offers.pop(offer_id, None)
        data["offers"] = offers
        if removed:
            self._save(data)
        return removed
