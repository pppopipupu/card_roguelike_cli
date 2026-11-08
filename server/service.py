import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from game.core.headless_server import HeadlessGameServer
from game.models.manager import SaveManager
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
        "uuid": account["uuid"],
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

    def _lock_for(self, key: str) -> asyncio.Lock:
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
        lines = [
            f"🆔 你的玩家 UUID：{account['uuid']}",
            f"🔗 已关联即时通讯账号：{'是' if account['im_user_id'] else '否'}",
            f"🌐 已关联网页账号：{'是' if account['web_user_id'] else '否'}",
        ]
        if channel == "web" and not account["im_user_id"]:
            lines.append("💡 如需继承即时通讯进度，请输入：绑定 <UUID>")
        if channel == "web" and account["im_user_id"]:
            lines.append("💡 当前网页账号已与即时通讯进度共享同一份存档。")
        return "\n".join(lines)

    def _migration_text(self, account: dict) -> str:
        return "\n".join(
            [
                "🔐 你的迁移码（UUID）：",
                account["uuid"],
                "",
                "在网页版使用 GitHub 登录后，输入：",
                f"绑定 {account['uuid']}",
                "迁移码只用于关联存档，请勿公开。",
            ]
        )

    def _admin_accounts(self) -> str:
        rows = self.accounts.list_all()
        if not rows:
            return "当前没有已注册玩家。"
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
                    "name": account["display_name"] or "匿名玩家",
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
                f"🟢 当前在线玩家（最近 5 分钟，共 {len(online_rows)} 人）",
                "",
            ]
            if not online_rows:
                lines.append("当前没有在线玩家。")
            else:
                for index, row in enumerate(online_rows[:20], 1):
                    lines.append(
                        f"{index}. {row['name']} — 第 {row['stage']} 层 — {row['gp']} GP"
                    )
            lines.append("━━━━━━━━━━━━━━━━━━━━")
            return "\n".join(lines)
        rows.sort(key=lambda row: (-row["gp"], row["name"]))
        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            "🏆 GP 排行榜（前 20）",
            "",
        ]
        if not rows:
            lines.append("当前还没有玩家记录。")
        else:
            for index, row in enumerate(rows[:20], 1):
                marker = "🟢 " if row["online"] else ""
                lines.append(
                    f"{index}. {marker}{row['name']} — {row['gp']} GP — 第 {row['stage']} 层"
                )
        lines.append("")
        lines.append(f"🟢 当前在线：{len(online_rows)} 人")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    async def _handle_bind(self, account: dict, command: str, channel: str) -> tuple[dict, str]:
        if channel != "web":
            return account, "❌ 绑定操作请在网页端进行。"
        parts = command.split()
        if len(parts) < 2:
            return account, "❌ 用法：绑定 <UUID> [force]"
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
        prefixes: Optional[tuple[str, ...]] = None,
    ) -> dict:
        active_prefixes = prefixes or self.settings.im_prefixes
        if len(command) > self.settings.max_command_length:
            return {
                "ok": False,
                "handled": True,
                "text": "❌ 指令过长。",
                "error": "command_too_long",
                "state": None,
                "account": None,
            }
        if channel != principal.kind:
            return {
                "ok": False,
                "handled": True,
                "text": "❌ 认证方式与请求通道不一致。",
                "error": "channel_mismatch",
                "state": None,
                "account": None,
            }

        name = (display_name or principal.display_name or "").strip()[:64]
        account = self._resolve_account(principal, name)
        normalized = _strip_prefix(command, active_prefixes)
        parts = normalized.split(maxsplit=1)
        first = parts[0].lower().lstrip("/") if parts else ""

        if first in ("leaderboard", "排行", "排行榜", "lb"):
            sub = parts[1].strip().lower() if len(parts) > 1 else ""
            if sub and sub not in ("online", "在线", "当前在线"):
                return self._text_response(
                    account, channel, "❌ 用法：leaderboard 或 leaderboard online"
                )
            return self._text_response(
                account, channel, self._leaderboard_text(sub in ("online", "在线", "当前在线"))
            )

        if channel == "web":
            self._ensure_web_rogue(account["uuid"])

        if channel == "web" and first in ("mode", "模式"):
            return self._text_response(
                account, channel, "模式切换指令已移除，肉鸽模式固定开启。\n"
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
                    "text": "❌ 迁移码只能在即时通讯端通过 secrets 获取。",
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
                    "text": "❌ 需要管理员令牌。",
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
                    sender_name=name or "玩家",
                    message=command,
                    shortcut_prefix=list(active_prefixes),
                    enable_shortcut=True,
                    force_execute=True,
                )
                handled = True
            else:
                text = await self.server.handle_rogue_message(
                    user_id=account["uuid"],
                    sender_name=name or "玩家",
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

        return {
            "ok": True,
            "handled": handled,
            "text": text,
            "state": state,
            "account": _account_json(account),
            "shell": self.shell.prompt_info(
                account["uuid"], account["display_name"] or name or "rogue"
            ),
        }
