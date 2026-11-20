from dataclasses import dataclass
import mimetypes
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from ...data.audio_config import (
    AUDIO_API_PREFIX,
    AUDIO_ASSET_ROOT,
    AUDIO_MAX_QUEUE_PER_RESPONSE,
    CARD_PLAY_AUDIO_MAP,
)


@dataclass
class AudioPacket:
    id: str
    pack: str
    file: str
    url: str
    volume: float = 1.0
    card_id: str = ""
    trigger: str = "card_play"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "pack": self.pack,
            "file": self.file,
            "url": self.url,
            "volume": self.volume,
            "card_id": self.card_id,
            "trigger": self.trigger,
        }


class AudioPipeline:
    def __init__(self, asset_root: Optional[Path] = None, api_prefix: str = AUDIO_API_PREFIX):
        self.asset_root = asset_root or AUDIO_ASSET_ROOT
        self.api_prefix = api_prefix.rstrip("/")
        self._queues: dict[str, list[AudioPacket]] = {}
        self._seq = 0

    def _next_id(self) -> str:
        self._seq += 1
        return f"aud_{self._seq}"

    def build_url(self, pack: str, filename: str) -> str:
        return f"{self.api_prefix}/{quote(pack, safe='')}/{quote(filename, safe='')}"

    def resolve_asset_path(self, pack: str, filename: str) -> Optional[Path]:
        if not pack or not filename:
            return None
        if "/" in pack or "\\" in pack or ".." in pack:
            return None
        if "/" in filename or "\\" in filename or ".." in filename:
            return None
        root = self.asset_root.resolve()
        candidate = (root / pack / filename).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        return candidate

    def media_type_for(self, path: Path) -> str:
        guessed, _ = mimetypes.guess_type(str(path))
        if guessed:
            return guessed
        ext = path.suffix.lower()
        if ext == ".ogg":
            return "audio/ogg"
        if ext == ".wav":
            return "audio/wav"
        return "audio/mpeg"

    def emit_sound(
        self,
        user_id: str,
        pack: str,
        filename: str,
        volume: float = 1.0,
        card_id: str = "",
        trigger: str = "sfx",
    ) -> Optional[AudioPacket]:
        if not user_id or not pack or not filename:
            return None
        if self.resolve_asset_path(pack, filename) is None:
            return None
        queue = self._queues.setdefault(str(user_id), [])
        if len(queue) >= AUDIO_MAX_QUEUE_PER_RESPONSE:
            return None
        pkt = AudioPacket(
            id=self._next_id(),
            pack=pack,
            file=filename,
            url=self.build_url(pack, filename),
            volume=round(min(1.5, max(0.0, float(volume))), 2),
            card_id=card_id,
            trigger=trigger,
        )
        queue.append(pkt)
        return pkt

    def emit_card_play(self, user_id: str, card_id: str) -> Optional[AudioPacket]:
        base_id = str(card_id or "").rstrip("+")
        cfg = CARD_PLAY_AUDIO_MAP.get(base_id)
        if not cfg:
            return None
        pack = str(cfg.get("pack", ""))
        filename = str(cfg.get("file", ""))
        raw_vol = cfg.get("volume", 1.0)
        volume = float(raw_vol) if isinstance(raw_vol, (int, float)) else 1.0
        return self.emit_sound(
            user_id=user_id,
            pack=pack,
            filename=filename,
            volume=volume,
            card_id=base_id,
            trigger="card_play",
        )

    def drain(self, user_id: str, channel: str) -> list[dict[str, object]]:
        packets = self._queues.pop(str(user_id), [])
        if channel.lower() != "web":
            return []
        return [pkt.to_dict() for pkt in packets]

    def clear(self, user_id: str) -> None:
        self._queues.pop(str(user_id), None)

    def clear_all(self) -> None:
        self._queues.clear()


_DEFAULT_PIPELINE = AudioPipeline()


def get_audio_pipeline() -> AudioPipeline:
    return _DEFAULT_PIPELINE


def reset_audio_pipeline() -> None:
    _DEFAULT_PIPELINE.clear_all()
