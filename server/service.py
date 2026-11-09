import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from game.core.headless_server import HeadlessGameServer
from game.data.locale_data import get_locale_text
from game.models.manager import SaveManager
from game.models.state import public_player_id, set_user_id
from game.renderer import GameRenderer

from .accounts import AccountStore
from .auth import Principal
from .config import Settings
from .shell import ShellService
from .snapshot import build_snapshot

logger = logging.getLogger("rogue.server")


def _strip_prefix(message: str, prefixes: tuple[str, ...]) -> str:
    text = message.strip()
    lower = text.lower()
    for prefix in sorted(prefixes, key=len, reverse=True):
        if prefix and lower.startswith(prefix.lower()):
            return text[len(prefix) :].strip()
    if lower.startswith("rogue "):
        return text[len("rogue") :].strip()
    if lower.startswith("/rogue "):
        return text[len("/rogue") :].strip()
    return text


def _account_json(account: dict) -> dict:
    return {
        "id": public_player_id(account["uuid"]),
        "im_user_id": account["im_user_id"],
        "web_user_id": account["web_user_id"],
        "display_name": account["display_name"],
        "linked": bool(account["im_user_id"] and account["web_user_id"]),
    }


class RogueService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.accounts = AccountStore(settings.db_path, settings.player_dir)
        self.server = HeadlessGameServer(str(settings.player_dir))
        self.save_manager: SaveManager = self.server.save_manager
        self.shell = ShellService(settings.data_dir / "shell")
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, user_id: str) -> asyncio.Lock:
        resolve_key = getattr(self.save_manager, "resolve_lock_key", None)
        key = resolve_key(user_id) if callable(resolve_key) else f"user:{user_id}"
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def _ensure_web_rogue(self, uuid: str) -> None:
        stats = self.save_manager.load_stats(uuid)
        if not stats.rogue_mode:
            stats.rogue_mode = True
            stats.duel_mode = False
            self.save_manager.save_stats(uuid, stats)

    def _text_response(
        self,
        account: dict,
        channel: str,
        text: str,
        status: int = 0,
        clear: bool = False,
    ) -> dict:
        set_user_id(account["uuid"])
        run = self.save_manager.load_save(account["uuid"])
        stats = self.save_manager.load_stats(account["uuid"])
        state = build_snapshot(run, stats, text) if channel == "web" else None
        return {
            "ok": True,
            "handled": True,
            "text": text,
            "state": state,
            "account": _account_json(account),
            "shell": self.shell.prompt_info(
                account["uuid"], account["display_name"] or "rogue", status
            ),
            "clear": clear,
        }

    def _strip_web_prefixes(self, text: str) -> str:
        text = text.replace("/rogue ", "").replace(".rogue ", "")
        return text.replace("help 或 help", "help")

    def _resolve_account(self, principal: Principal, display_name: str) -> dict:
        if principal.kind == "web":
            return self.accounts.get_or_create_web(principal.user_id, display_name)
        return self.accounts.get_or_create_im(principal.user_id, display_name)

    def _account_help(self, account: dict, channel: str) -> str:
        yes = get_locale_text("i18n_server_core.common.yes")
        no = get_locale_text("i18n_server_core.common.no")
        lines = [
            get_locale_text(
                "i18n_server_core.service.account_player_id",
                player_id=public_player_id(account["uuid"]),
            ),
            get_locale_text(
                "i18n_server_core.service.account_im_linked",
                value=yes if account["im_user_id"] else no,
            ),
            get_locale_text(
                "i18n_server_core.service.account_web_linked",
                value=yes if account["web_user_id"] else no,
            ),
        ]
        if channel == "web" and not account["im_user_id"]:
            lines.append(get_locale_text("i18n_server_core.service.account_bind_hint"))
        if channel == "web" and account["im_user_id"]:
            lines.append(get_locale_text("i18n_server_core.service.account_shared_save"))
        return "\n".join(lines)

    def _migration_text(self, account: dict) -> str:
        return "\n".join(
            [
                get_locale_text("i18n_server_core.service.migration_title"),
                account["uuid"],
                "",
                get_locale_text("i18n_server_core.service.migration_instruction"),
                get_locale_text(
                    "i18n_server_core.service.migration_bind_command", uuid=account["uuid"]
                ),
                get_locale_text("i18n_server_core.service.migration_warning"),
            ]
        )

    def _admin_accounts(self) -> str:
        rows = self.accounts.list_all()
        if not rows:
            return get_locale_text("i18n_server_core.service.admin_no_players")
        lines = ["UUID | IM | WEB | NAME | LAST_SEEN"]
        for row in rows:
            lines.append(
                " | ".join(
                    [
                        row["uuid"],
                        row["im_user_id"] or "-",
                        row["web_user_id"] or "-",
                        row["display_name"] or "-",
                        row["last_seen"] or "-",
                    ]
                )
            )
        return "\n".join(lines)

    def _is_online(self, last_seen: str, window_seconds: int = 300) -> bool:
        if not last_seen:
            return False
        try:
            seen = datetime.fromisoformat(last_seen)
        except ValueError:
            return False
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - seen).total_seconds() <= window_seconds

    def _leaderboard_rows(self) -> list[dict]:
        rows = []
        for account in self.accounts.list_all():
            stats = self.save_manager.load_stats(account["uuid"])
            run = self.save_manager.load_save(account["uuid"])
            stage = 0
            if run is not None and run.player is not None:
                stage = int(getattr(run.player, "stage", 0))
            rows.append(
                {
                    "name": account["display_name"]
                    or get_locale_text("i18n_server_core.service.anonymous_player"),
                    "gp": int(getattr(stats, "gp", 0)),
                    "stage": stage,
                    "online": self._is_online(account["last_seen"]),
                    "last_seen": account["last_seen"] or "",
                }
            )
        return rows

    def _leaderboard_text(self, online_only: bool = False) -> str:
        rows = self._leaderboard_rows()
        online_rows = [row for row in rows if row["online"]]
        if online_only:
            online_rows.sort(key=lambda row: row["last_seen"], reverse=True)
            lines = [
                "━━━━━━━━━━━━━━━━━━━━",
                get_locale_text(
                    "i18n_server_core.service.online_title", count=len(online_rows)
                ),
                "",
            ]
            if not online_rows:
                lines.append(get_locale_text("i18n_server_core.service.online_empty"))
            else:
                for index, row in enumerate(online_rows[:20], 1):
                    lines.append(
                        get_locale_text(
                            "i18n_server_core.service.online_row",
                            index=index,
                            name=row["name"],
                            stage=row["stage"],
                            gp=row["gp"],
                        )
                    )
            lines.append("━━━━━━━━━━━━━━━━━━━━")
            return "\n".join(lines)
        rows.sort(key=lambda row: (-row["gp"], row["name"]))
        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("i18n_server_core.service.leaderboard_title"),
            "",
        ]
        if not rows:
            lines.append(get_locale_text("i18n_server_core.service.leaderboard_empty"))
        else:
            for index, row in enumerate(rows[:20], 1):
                marker = "🟢 " if row["online"] else ""
                lines.append(
                    get_locale_text(
                        "i18n_server_core.service.leaderboard_row",
                        index=index,
                        marker=marker,
                        name=row["name"],
                        gp=row["gp"],
                        stage=row["stage"],
                    )
                )
        lines.append("")
        lines.append(
            get_locale_text("i18n_server_core.service.online_count", count=len(online_rows))
        )
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    async def _handle_bind(self, account: dict, command: str, channel: str) -> tuple[dict, str]:
        if channel != "web":
            return account, get_locale_text("i18n_server_core.service.bind_web_only")
        parts = command.split()
        if len(parts) < 2:
            return account, get_locale_text("i18n_server_core.service.bind_usage")
        target_uuid = parts[1].strip()
        force = len(parts) >= 3 and parts[2].lower() in ("force", "强制", "覆盖")
        async with self._lock_for(account["uuid"]):
            status, target, message = self.accounts.bind_web(
                account["web_user_id"], target_uuid, force
            )
        if status == "ok" and target:
            return target, f"✅ {message}\n\n{self._account_help(target, channel)}"
        return account, f"❌ {message}"

    async def handle(
        self,
        principal: Principal,
        command: str,
        channel: str,
        display_name: str = "",
        force: bool = False,
        is_admin: bool = False,
        group: bool = False,
        prefixes: Optional[tuple[str, ...]] = None,
    ) -> dict:
        active_prefixes = prefixes or self.settings.im_prefixes
        if len(command) > self.settings.max_command_length:
            return {
                "ok": False,
                "handled": True,
                "text": get_locale_text("i18n_server_core.service.command_too_long"),
                "error": "command_too_long",
                "state": None,
                "account": None,
            }
        if channel != principal.kind:
            return {
                "ok": False,
                "handled": True,
                "text": get_locale_text("i18n_server_core.service.channel_mismatch"),
                "error": "channel_mismatch",
                "state": None,
                "account": None,
            }

        name = (display_name or principal.display_name or "").strip()[:64]
        account = self._resolve_account(principal, name)
        set_user_id(account["uuid"])
        normalized = _strip_prefix(command, active_prefixes)
        parts = normalized.split(maxsplit=1)
        first = parts[0].lower().lstrip("/") if parts else ""

        if first in ("leaderboard", "排行", "排行榜", "lb"):
            sub = parts[1].strip().lower() if len(parts) > 1 else ""
            if sub and sub not in ("online", "在线", "当前在线"):
                return self._text_response(
                    account,
                    channel,
                    get_locale_text("i18n_server_core.service.leaderboard_usage"),
                )
            return self._text_response(
                account, channel, self._leaderboard_text(sub in ("online", "在线", "当前在线"))
            )

        if channel == "web":
            self._ensure_web_rogue(account["uuid"])

        if channel == "web" and first in ("mode", "模式"):
            return self._text_response(
                account, channel, get_locale_text("i18n_server_core.service.mode_removed")
            )

        shell_handled = self.shell.handles(normalized)
        if shell_handled and first == "exit":
            shell_handled = self.save_manager.load_save(account["uuid"]) is None
        if shell_handled:
            async with self._lock_for(account["uuid"]):
                result = self.shell.execute(
                    account["uuid"],
                    account["display_name"] or name or "rogue",
                    normalized,
                )
            return self._text_response(
                account, channel, result.text, result.status, result.clear
            )

        if channel == "web" and first in ("help", "帮助"):
            return self._text_response(
                account,
                channel,
                self._strip_web_prefixes(GameRenderer.render_help(include_mode=False)),
            )

        if channel == "web" and first in ("stat", "stats", "统计"):
            return self._text_response(
                account,
                channel,
                GameRenderer.render_stats(
                    self.save_manager.load_stats(account["uuid"]),
                    include_mode=False,
                ),
            )

        if first in ("我的id", "uuid", "myid"):
            return {
                "ok": True,
                "handled": True,
                "text": self._account_help(account, channel),
                "state": None,
                "account": _account_json(account),
            }

        if first in ("secrets", "迁移码", "migration"):
            if channel != "im":
                return {
                    "ok": False,
                    "handled": True,
                    "text": get_locale_text("i18n_server_core.service.migration_im_only"),
                    "error": "im_only",
                    "state": None,
                    "account": _account_json(account),
                }
            return {
                "ok": True,
                "handled": True,
                "text": self._migration_text(account),
                "state": None,
                "account": _account_json(account),
            }

        if first in ("绑定", "bind"):
            account, text = await self._handle_bind(account, normalized, channel)
            return {
                "ok": not text.startswith("❌"),
                "handled": True,
                "text": text,
                "state": None,
                "account": _account_json(account),
            }

        if first in ("admin", "rogueadmin"):
            if not is_admin:
                return {
                    "ok": False,
                    "handled": True,
                    "text": get_locale_text("i18n_server_core.service.admin_required"),
                    "error": "admin_required",
                    "state": None,
                    "account": _account_json(account),
                }
            admin_command = parts[1] if len(parts) > 1 else ""
            if admin_command.lower().strip() in ("accounts", "账号", "玩家"):
                return {
                    "ok": True,
                    "handled": True,
                    "text": self._admin_accounts(),
                    "state": None,
                    "account": _account_json(account),
                }
            async with self._lock_for(account["uuid"]):
                text = await self.server.handle_admin_message(
                    account["uuid"], "rogueadmin " + admin_command
                )
            return {
                "ok": True,
                "handled": True,
                "text": text,
                "state": None,
                "account": _account_json(account),
            }

        async with self._lock_for(account["uuid"]):
            if channel == "web":
                text = await self.server.handle_rogue_message(
                    user_id=account["uuid"],
                    sender_name=name
                    or get_locale_text("i18n_server_core.service.default_sender_name"),
                    message=command,
                    shortcut_prefix=list(active_prefixes),
                    enable_shortcut=True,
                    force_execute=True,
                )
                handled = True
            else:
                text = await self.server.handle_rogue_message(
                    user_id=account["uuid"],
                    sender_name=name
                    or get_locale_text("i18n_server_core.service.default_sender_name"),
                    message=command,
                    shortcut_prefix=list(active_prefixes),
                    enable_shortcut=True,
                    force_execute=force,
                )
                handled = text is not None
            if text is None:
                text = ""
            if channel == "web":
                text = self._strip_web_prefixes(text)

            run = self.save_manager.load_save(account["uuid"])
            stats = self.save_manager.load_stats(account["uuid"])
            state = build_snapshot(run, stats, text) if channel == "web" else None
            coop_log = []
            if run is not None and getattr(run, "coop_id", "") and not (channel == "im" and group):
                own_prefix = f"[{run.player.name}] " if run.player and run.player.name else ""
                actions = [
                    entry
                    for entry in run.node_data.get("coop_action_history", [])
                    if not own_prefix or not entry.startswith(own_prefix)
                ][-20:]
                battles = [
                    entry
                    for entry in run.node_data.get("coop_battle_log_history", [])
                    if not own_prefix or not entry.startswith(own_prefix)
                ][-20:]
                coop_log = actions + battles
            if state is not None:
                state["coop_log"] = coop_log

        return {
            "ok": True,
            "handled": handled,
            "text": text,
            "state": state,
            "coop_log": coop_log,
            "account": _account_json(account),
            "shell": self.shell.prompt_info(
                account["uuid"], account["display_name"] or name or "rogue"
            ),
        }
