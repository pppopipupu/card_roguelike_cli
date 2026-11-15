from datetime import datetime

from ...data.locale_data import get_locale_text
from ...data.world_social_config import (
    WORLD_MAILBOX_LIMIT,
    WORLD_MESSAGE_MAX_LENGTH,
    WORLD_TALK_TARGET_KEY,
    WORLD_TALK_WORLD_KEY,
)
from .presence import WorldPresenceService


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").split())[:WORLD_MESSAGE_MAX_LENGTH]


def _entry_name(entry: dict) -> str:
    return entry.get("name") or get_locale_text("i18n_world_social.default_player_name")


class WorldSocialService:
    def __init__(self, save_manager):
        self.save_manager = save_manager
        self.presence = WorldPresenceService(save_manager)

    def refresh(self, uid: str, stats=None, run=None):
        location = self.presence.sync(uid, stats=stats, run=run)
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        target_world = str(stats.town_flags.get(WORLD_TALK_WORLD_KEY, "") or "")
        if target_world and (location is None or location[0] != target_world):
            stats.town_flags.pop(WORLD_TALK_TARGET_KEY, None)
            stats.town_flags.pop(WORLD_TALK_WORLD_KEY, None)
            self.save_manager.save_stats(uid, stats)
        return location

    def visible(self, world: str, coord: str, exclude_uid: str) -> list[dict]:
        return self.presence.players(world, coord=coord, exclude_uid=exclude_uid)

    def resolve_target(self, world: str, coord: str, text: str, exclude_uid: str) -> tuple[dict | None, str]:
        raw = str(text or "").strip()
        if not raw:
            return None, ""
        entries = self.presence.players(world, coord=coord, exclude_uid=exclude_uid)
        for entry in sorted(entries, key=lambda item: len(_entry_name(item)), reverse=True):
            names = {_entry_name(entry), str(entry.get("player_id", ""))}
            for name in names:
                if not name:
                    continue
                if raw == name:
                    return entry, ""
                if raw.lower().startswith(name.lower() + " "):
                    return entry, raw[len(name):].strip()
        return None, raw

    def _target_from_flags(self, uid: str, stats) -> tuple[dict | None, str, str]:
        target_uid = str(stats.town_flags.get(WORLD_TALK_TARGET_KEY, "") or "")
        world = str(stats.town_flags.get(WORLD_TALK_WORLD_KEY, "") or "")
        if not target_uid or not world:
            return None, "", ""
        location = self.presence.resolve_location(uid, stats=stats)
        if location is None or location[0] != world:
            self.close(uid, stats)
            return None, "", ""
        target = self.presence.get(target_uid)
        if target is None:
            self.close(uid, stats)
            return None, "", ""
        return target, world, location[1]

    def _validate_target(self, uid: str, target_uid: str, world: str, coord: str) -> dict | None:
        for entry in self.presence.players(world, coord=coord, exclude_uid=uid):
            if entry.get("user_id") == target_uid:
                return entry
        return None

    def open_dialog(self, uid: str, target: dict, world: str, stats=None) -> str:
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        stats.town_flags[WORLD_TALK_TARGET_KEY] = target.get("user_id", "")
        stats.town_flags[WORLD_TALK_WORLD_KEY] = world
        self.save_manager.save_stats(uid, stats)
        name = _entry_name(target)
        return get_locale_text(
            "i18n_world_social.dialog.open",
            name=name,
            class_text=target.get("class_text", ""),
        )

    def close(self, uid: str, stats=None) -> str:
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        stats.town_flags.pop(WORLD_TALK_TARGET_KEY, None)
        stats.town_flags.pop(WORLD_TALK_WORLD_KEY, None)
        self.save_manager.save_stats(uid, stats)
        return get_locale_text("i18n_world_social.dialog.closed")

    def _append_mail(self, target_uid: str, from_uid: str, from_name: str, text: str, kind: str = "player") -> bool:
        target_stats = self.save_manager.load_stats(target_uid)
        mailbox = getattr(target_stats, "world_mailbox", None)
        if not isinstance(mailbox, list):
            mailbox = []
        mailbox.append({
            "from_uid": from_uid,
            "from_name": from_name,
            "text": text,
            "time": datetime.now().strftime("%m-%d %H:%M"),
            "read": False,
            "kind": kind,
        })
        target_stats.world_mailbox = mailbox[-WORLD_MAILBOX_LIMIT:]
        return self.save_manager.save_stats(target_uid, target_stats)

    def send_system(self, target_uid: str, text: str) -> bool:
        return self._append_mail(target_uid, "", get_locale_text("i18n_world_social.system_name"), _clean_text(text), "system")

    def send(self, uid: str, target: dict, text: str) -> str:
        clean = _clean_text(text)
        if not clean:
            return get_locale_text("i18n_world_social.dialog.need_text")
        target_uid = str(target.get("user_id", ""))
        if not target_uid:
            return get_locale_text("i18n_world_social.dialog.target_missing")
        source_stats = self.save_manager.load_stats(uid)
        source_name = getattr(source_stats, "player_name", "") or get_locale_text("i18n_world_social.default_player_name")
        if not self.presence.send_live(target_uid, uid, source_name, clean):
            return get_locale_text("i18n_world_social.dialog.target_left", name=_entry_name(target))
        return get_locale_text(
            "i18n_world_social.dialog.sent",
            name=_entry_name(target),
            text=clean,
        )

    def send_remote(self, uid: str, raw: str) -> str:
        text = str(raw or "").strip()
        if not text:
            return get_locale_text("i18n_world_social.remote.usage")
        source_stats = self.save_manager.load_stats(uid)
        friend_uids = list(getattr(source_stats, "friends", []) or [])
        candidates = []
        for friend_uid in friend_uids:
            friend_stats = self.save_manager.load_stats(friend_uid)
            names = {
                getattr(friend_stats, "player_name", ""),
                getattr(friend_stats, "player_handle", ""),
            }
            for name in names:
                if name:
                    candidates.append((str(name), friend_uid, friend_stats))
        candidates.sort(key=lambda item: len(item[0]), reverse=True)
        for name, friend_uid, friend_stats in candidates:
            lowered = text.lower()
            if lowered == name.lower():
                return get_locale_text("i18n_world_social.remote.need_text")
            if lowered.startswith(name.lower() + " "):
                message = _clean_text(text[len(name):])
                if not message:
                    return get_locale_text("i18n_world_social.remote.need_text")
                source_name = getattr(source_stats, "player_name", "") or get_locale_text("i18n_world_social.default_player_name")
                self._append_mail(friend_uid, uid, source_name, message, "remote")
                return get_locale_text(
                    "i18n_world_social.remote.sent",
                    name=getattr(friend_stats, "player_name", name),
                    text=message,
                )
        if not friend_uids:
            return get_locale_text("i18n_world_social.remote.no_friends")
        return get_locale_text("i18n_world_social.remote.not_friend", query=text.split()[0] if text else "")

    def pop_live(self, uid: str) -> list[dict]:
        return self.presence.pop_live(uid)

    def render_live(self, message: dict) -> str:
        return get_locale_text(
            "i18n_world_social.live.entry",
            name=message.get("from_name", ""),
            text=message.get("text", ""),
        )

    def talk(self, uid: str, text: str) -> str:
        stats = self.save_manager.load_stats(uid)
        target, world, coord = self._target_from_flags(uid, stats)
        if target is None:
            return get_locale_text("i18n_world_social.dialog.no_target")
        live = self._validate_target(uid, target.get("user_id", ""), world, coord)
        if live is None:
            self.close(uid, stats)
            return get_locale_text("i18n_world_social.dialog.target_left", name=_entry_name(target))
        return self.send(uid, live, text)

    def say_to_world(self, uid: str, world: str, coord: str, query: str) -> str:
        if not str(query or "").strip():
            separator = get_locale_text("i18n_social.common.list_separator")
            names = separator.join(_entry_name(entry) for entry in self.presence.players(world, coord=coord, exclude_uid=uid))
            if names:
                return get_locale_text("i18n_world_social.dialog.here", names=names)
            return get_locale_text("i18n_world_social.dialog.here_empty")
        target, message = self.resolve_target(world, coord, query, uid)
        if target is None:
            return get_locale_text("i18n_world_social.dialog.not_here", query=query)
        if not message:
            stats = self.save_manager.load_stats(uid)
            return self.open_dialog(uid, target, world, stats=stats)
        live = self._validate_target(uid, target.get("user_id", ""), world, coord)
        if live is None:
            return get_locale_text("i18n_world_social.dialog.target_left", name=_entry_name(target))
        return self.send(uid, live, message)

    def unread_count(self, uid: str) -> int:
        stats = self.save_manager.load_stats(uid)
        mailbox = getattr(stats, "world_mailbox", None)
        if not isinstance(mailbox, list):
            return 0
        return sum(1 for item in mailbox if isinstance(item, dict) and not item.get("read"))

    def notify(self, uid: str) -> str:
        count = self.unread_count(uid)
        if count <= 0:
            return ""
        return get_locale_text("i18n_world_social.inbox.notify", count=count)

    def render_inbox(self, uid: str, mark_read: bool = True) -> str:
        stats = self.save_manager.load_stats(uid)
        mailbox = getattr(stats, "world_mailbox", None)
        if not isinstance(mailbox, list):
            mailbox = []
        if not mailbox:
            return get_locale_text("i18n_world_social.inbox.empty")
        lines = [get_locale_text("i18n_world_social.inbox.header", count=len(mailbox))]
        for item in mailbox[-10:]:
            if not isinstance(item, dict):
                continue
            marker = "" if item.get("read") else get_locale_text("i18n_world_social.inbox.unread_marker")
            lines.append(
                get_locale_text(
                    "i18n_world_social.inbox.entry",
                    marker=marker,
                    name=item.get("from_name", ""),
                    time=item.get("time", ""),
                    text=item.get("text", ""),
                )
            )
        lines.append(get_locale_text("i18n_world_social.inbox.hint"))
        if mark_read:
            for item in mailbox:
                if isinstance(item, dict):
                    item["read"] = True
            self.save_manager.save_stats(uid, stats)
        return "\n".join(lines)
