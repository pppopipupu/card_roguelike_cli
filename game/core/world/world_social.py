from datetime import datetime

from ...data.progression.balance_config import LOG_MAX_ENTRIES
from ...data.text.locale_data import get_locale_text
from ...data.world.world_social_config import (
    WORLD_MAILBOX_LIMIT,
    WORLD_MESSAGE_MAX_LENGTH,
    WORLD_PENDING_LOG_LIMIT,
    WORLD_PLAYER_DIALOG_EXIT_WORDS,
    WORLD_PLAYER_DIALOG_KEY,
)
from ..text.pipeline import render_text_node
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
        dialog = stats.town_flags.get(WORLD_PLAYER_DIALOG_KEY)
        if isinstance(dialog, dict):
            dlg_world = str(dialog.get("world", "") or "")
            dlg_coord = str(dialog.get("coord", "") or "")
            if location is None or location[0] != dlg_world or location[1] != dlg_coord:
                stats.town_flags.pop(WORLD_PLAYER_DIALOG_KEY, None)
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
                if raw.lower() == name.lower():
                    return entry, ""
                if raw.lower().startswith(name.lower() + " "):
                    return entry, raw[len(name):].strip()
        return None, raw

    def _validate_target(self, uid: str, target_uid: str, world: str, coord: str) -> dict | None:
        for entry in self.presence.players(world, coord=coord, exclude_uid=uid):
            if entry.get("user_id") == target_uid:
                return entry
        return None

    def has_dialog(self, uid: str, stats=None) -> bool:
        if not uid:
            return False
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        return isinstance(stats.town_flags.get(WORLD_PLAYER_DIALOG_KEY), dict)

    def clear_dialog(self, uid: str, stats=None) -> bool:
        if not uid:
            return False
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        if WORLD_PLAYER_DIALOG_KEY not in stats.town_flags:
            return False
        stats.town_flags.pop(WORLD_PLAYER_DIALOG_KEY, None)
        self.save_manager.save_stats(uid, stats)
        return True

    def render_dialog(self, uid: str, stats=None) -> str:
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        dialog = stats.town_flags.get(WORLD_PLAYER_DIALOG_KEY)
        if not isinstance(dialog, dict):
            return ""
        target_uid = str(dialog.get("target_uid", ""))
        target_name = str(dialog.get("target_name", "") or get_locale_text("i18n_world_social.default_player_name"))
        class_text = str(dialog.get("class_text", "") or "-")
        is_friend = target_uid in (getattr(stats, "friends", []) or [])
        friend_opt = (
            get_locale_text("i18n_world_social.dialog.opt_friend_done", name=target_name)
            if is_friend
            else get_locale_text("i18n_world_social.dialog.opt_add_friend", name=target_name)
        )
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("i18n_world_social.dialog.title", name=target_name),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("i18n_world_social.dialog.intro", name=target_name, class_text=class_text),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  [1] {get_locale_text('i18n_world_social.dialog.opt_greet')}",
            f"  [2] {friend_opt}",
            f"  [3] {get_locale_text('i18n_world_social.dialog.opt_inspect')}",
            f"  [4] {get_locale_text('i18n_world_social.dialog.opt_trade')}",
            f"  [0] {get_locale_text('i18n_world_social.dialog.opt_leave')}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("i18n_world_social.dialog.help", name=target_name),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        return "\n".join(lines)

    def open_dialog(self, uid: str, target: dict, world: str, coord: str = "", stats=None) -> str:
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        stats.town_flags.pop("current_dialog", None)
        stats.town_flags.pop("market_sub_menu", None)
        stats.town_flags.pop("shop_sub_menu", None)
        target_name = _entry_name(target)
        stats.town_flags[WORLD_PLAYER_DIALOG_KEY] = {
            "target_uid": str(target.get("user_id", "")),
            "target_name": target_name,
            "target_handle": str(target.get("player_id", "") or target_name),
            "class_text": str(target.get("class_text", "") or ""),
            "world": str(world),
            "coord": str(coord or target.get("coord", "")),
        }
        self.save_manager.save_stats(uid, stats)
        return self.render_dialog(uid, stats=stats)

    def handle_dialog_choice(self, uid: str, raw: str, stats=None) -> str | None:
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        dialog = stats.town_flags.get(WORLD_PLAYER_DIALOG_KEY)
        if not isinstance(dialog, dict):
            return None
        token = str(raw or "").strip().lower()
        if token in WORLD_PLAYER_DIALOG_EXIT_WORDS:
            return self.close(uid, stats=stats)
        target_uid = str(dialog.get("target_uid", ""))
        target_name = str(dialog.get("target_name", "") or get_locale_text("i18n_world_social.default_player_name"))
        target_handle = str(dialog.get("target_handle", "") or target_uid)
        world = str(dialog.get("world", ""))
        coord = str(dialog.get("coord", ""))
        if token in ("1", "打招呼", "问候", "greet"):
            live = self._validate_target(uid, target_uid, world, coord)
            if live is None:
                stats.town_flags.pop(WORLD_PLAYER_DIALOG_KEY, None)
                self.save_manager.save_stats(uid, stats)
                return get_locale_text("i18n_world_social.dialog.target_left", name=target_name)
            greet_text = get_locale_text("i18n_world_social.dialog.quick_greet_text")
            msg = self.send(uid, live, greet_text)
            return msg + "\n\n" + self.render_dialog(uid, stats=stats)
        if token in ("2", "加好友", "好友", "friend", "add"):
            if target_uid in (getattr(stats, "friends", []) or []):
                msg = get_locale_text("i18n_world_social.dialog.already_friend_hint", name=target_name)
            else:
                from ..social.service import SocialService
                msg = SocialService(self.save_manager).friend_add(uid, target_handle or target_name)
                stats = self.save_manager.load_stats(uid)
            return msg + "\n\n" + self.render_dialog(uid, stats=stats)
        if token in ("3", "查看", "名片", "info", "inspect"):
            target_stats = self.save_manager.load_stats(target_uid)
            handle = getattr(target_stats, "player_handle", "") or target_handle or target_name
            cls_base = getattr(target_stats, "selected_class", "")
            cls_sub = getattr(target_stats, "selected_subclass", "")
            sep = get_locale_text("i18n_social.common.class_separator")
            cls_text = f"{cls_base}{sep}{cls_sub}" if cls_sub else cls_base
            friend_flag = get_locale_text("i18n_world_social.dialog.friend_yes") if target_uid in (getattr(stats, "friends", []) or []) else get_locale_text("i18n_world_social.dialog.friend_no")
            info = get_locale_text(
                "i18n_world_social.dialog.inspect_card",
                name=getattr(target_stats, "player_name", "") or target_name,
                player_id=handle,
                class_text=cls_text or "-",
                friend_status=friend_flag,
                coord=coord or "-",
            )
            return info + "\n\n" + self.render_dialog(uid, stats=stats)
        if token in ("4", "交易", "赠送", "trade", "gift"):
            from ..social.trade import TradeService
            assets = TradeService(self.save_manager, self).render_assets(uid, target_uid)
            return render_text_node(assets) + "\n\n" + self.render_dialog(uid, stats=stats)
        return get_locale_text("global.invalid_option") + "\n\n" + self.render_dialog(uid, stats=stats)

    def close(self, uid: str, stats=None) -> str:
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        stats.town_flags.pop(WORLD_PLAYER_DIALOG_KEY, None)
        self.save_manager.save_stats(uid, stats)
        return get_locale_text("i18n_world_social.dialog.closed")

    def push_log(self, target_uid: str, line: str, *, command: str = "", player_name: str = "", record_history: bool = True, coop_id: str = "") -> bool:
        clean_line = str(line or "").strip()
        if not target_uid or not clean_line:
            return False
        target_stats = self.save_manager.load_stats(target_uid)
        pending = getattr(target_stats, "pending_logs", None)
        if not isinstance(pending, list):
            pending = []
        pending.append(clean_line)
        target_stats.pending_logs = pending[-WORLD_PENDING_LOG_LIMIT:]
        if record_history:
            history = getattr(target_stats, "log_history", None)
            if not isinstance(history, list):
                history = []
            history.append({
                "kind": "action",
                "command": command or clean_line,
                "text": clean_line,
                "player": player_name,
                "coop_id": coop_id or getattr(target_stats, "active_coop_id", ""),
            })
            target_stats.log_history = history[-LOG_MAX_ENTRIES:]
        return self.save_manager.save_stats(target_uid, target_stats)

    def pop_pending_logs(self, uid: str, stats=None) -> list[str]:
        if not uid:
            return []
        if stats is None:
            stats = self.save_manager.load_stats(uid)
        pending = getattr(stats, "pending_logs", None)
        if not isinstance(pending, list) or not pending:
            return []
        lines = [str(item) for item in pending if str(item or "").strip()]
        stats.pending_logs = []
        self.save_manager.save_stats(uid, stats)
        return lines

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
        line = get_locale_text("i18n_world_social.live.entry", name=source_name, text=clean)
        self.push_log(
            target_uid,
            line,
            command=f"talk {source_name}",
            player_name=source_name,
            record_history=True,
            coop_id=getattr(source_stats, "active_coop_id", ""),
        )
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

    def _talk_target(self, uid: str, world: str, coord: str, target: dict, message: str, stats=None) -> str:
        live = self._validate_target(uid, target.get("user_id", ""), world, coord)
        if live is None:
            return get_locale_text("i18n_world_social.dialog.target_left", name=_entry_name(target))
        from ..battle.party_battle import revive_downed_ally
        revived = revive_downed_ally(self.save_manager, str(target.get("user_id", "") or ""))
        if revived:
            return revived
        if not message:
            return self.open_dialog(uid, live, world, coord=coord, stats=stats)
        return self.send(uid, live, message)

    def try_talk(self, uid: str, query: str, stats=None, run=None) -> str | None:
        raw = str(query or "").strip()
        if not raw or not uid:
            return None
        location = self.presence.resolve_location(uid, stats=stats, run=run)
        if location is None:
            return None
        world, coord = location
        target, message = self.resolve_target(world, coord, raw, uid)
        if target is None:
            return None
        return self._talk_target(uid, world, coord, target, message, stats=stats)

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
        return self._talk_target(uid, world, coord, target, message)

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
