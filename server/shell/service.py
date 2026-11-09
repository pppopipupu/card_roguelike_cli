from __future__ import annotations

import json
import os
import posixpath
import re
import shlex
import time
from collections import deque
from pathlib import Path

from game.data.locale_data import get_locale_text

from .commands_extra import ExtraCommands
from .commands_fs import DENIED, FilesystemCommands
from .commands_text import TextCommands
from .fs import build_nodes
from .models import ShellContext, ShellResult
from .paths import ShellPathMixin
from .registry import COMMANDS

MAX_FILE_BYTES = 512 * 1024
MAX_FILES = 32
MAX_TOTAL_BYTES = 4 * 1024 * 1024
WRITE_LIMIT = 8
WRITE_WINDOW = 60.0
MAX_OUTPUT = 256 * 1024
MAX_HISTORY = 200


STATEFUL = {"cd", "rm", "touch", "mkdir", "rmdir", "mv", "cp", "chmod", "chown"}


def _safe_uuid(value: str) -> str:
    return "".join(c for c in value if c.isalnum() or c in ("-", "_")) or "anonymous"


def _safe_user(value: str) -> str:
    user = re.sub(r"[^a-z0-9_-]", "", (value or "").lower())
    return user or "rogue"


class ShellService(FilesystemCommands, TextCommands, ExtraCommands, ShellPathMixin):
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._writes: dict[str, deque[float]] = {}

    def handles(self, command: str) -> bool:
        tokens = self._tokens(command)
        if not tokens:
            return False
        first = tokens[0].lower()
        if first == "help":
            return len(tokens) > 1 and tokens[1].lower() in ("system", "shell")
        return first in COMMANDS or first in DENIED

    def prompt_info(self, uuid: str, user: str, status: int = 0) -> dict:
        context = self._context(uuid, user)
        return {
            "user": context.user,
            "host": "rogue-core",
            "cwd": self._display(context, context.cwd),
            "branch": "master",
            "status": status,
        }

    def execute(self, uuid: str, user: str, command: str) -> ShellResult:
        context = self._context(uuid, user)
        raw = command.strip()
        if raw:
            context.history.append(raw)
            context.history = context.history[-MAX_HISTORY:]
        try:
            result = self._execute(context, raw)
        except Exception:
            result = ShellResult(get_locale_text("i18n_server_shell.err_internal"), 1)
        if len(result.text) > MAX_OUTPUT:
            result.text = result.text[:MAX_OUTPUT] + get_locale_text("i18n_server_shell.output_truncated")
        self._save(context)
        return result

    def _tokens(self, command: str) -> list[str]:
        try:
            lexer = shlex.shlex(command, posix=True, punctuation_chars="|<>")
            lexer.whitespace_split = True
            return list(lexer)
        except ValueError:
            return []

    def _context(self, uuid: str, user: str) -> ShellContext:
        safe = _safe_uuid(uuid)
        base = self.root / safe
        files_dir = base / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        state_path = base / "state.json"
        data = {}
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        safe_user = _safe_user(user)
        home = f"/home/{safe_user}"
        nodes = build_nodes(safe_user)
        cwd = data.get("cwd")
        if not isinstance(cwd, str) or cwd not in nodes or nodes[cwd].kind != "dir":
            cwd = home
        previous = data.get("previous")
        if not isinstance(previous, str) or previous not in nodes:
            previous = home
        history = data.get("history")
        if not isinstance(history, list):
            history = []
        return ShellContext(
            uuid=safe,
            user=safe_user,
            home=home,
            cwd=cwd,
            previous=previous,
            history=[str(item) for item in history][-MAX_HISTORY:],
            state_path=state_path,
            files_dir=files_dir,
            nodes=nodes,
        )

    def _save(self, context: ShellContext) -> None:
        data = {
            "cwd": context.cwd,
            "previous": context.previous,
            "history": context.history[-MAX_HISTORY:],
        }
        try:
            temporary = context.state_path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            os.replace(temporary, context.state_path)
        except OSError:
            pass

    def _rate_allowed(self, context: ShellContext) -> bool:
        now = time.monotonic()
        bucket = self._writes.setdefault(context.uuid, deque())
        while bucket and now - bucket[0] >= WRITE_WINDOW:
            bucket.popleft()
        if len(bucket) >= WRITE_LIMIT:
            return False
        bucket.append(now)
        return True

    def _write_file(
        self, context: ShellContext, path: str, content: str, append: bool = False
    ) -> str:
        if path == context.home or not self._under_home(context, path):
            return get_locale_text("i18n_server_shell.err_permission_denied")
        if self._is_secret(context, path):
            return get_locale_text("i18n_server_shell.err_permission_denied")
        if path in context.nodes:
            return get_locale_text("i18n_server_shell.err_permission_denied")
        parent = posixpath.dirname(path)
        if not self._is_dir(context, parent) or self._is_secret(context, parent):
            return get_locale_text("i18n_server_shell.err_no_such_dir")
        payload = content.encode("utf-8")
        if len(payload) > MAX_FILE_BYTES:
            return get_locale_text("i18n_server_shell.err_write_failed")
        target = self._player_path(context, path)
        if target is None:
            return get_locale_text("i18n_server_shell.err_permission_denied")
        existing_size = target.stat().st_size if target.is_file() else 0
        files = self._player_files(context)
        if target not in files.values() and len(files) >= MAX_FILES:
            return get_locale_text("i18n_server_shell.err_write_failed")
        total = sum(item.stat().st_size for item in files.values())
        if total - existing_size + len(payload) > MAX_TOTAL_BYTES:
            return get_locale_text("i18n_server_shell.err_no_space")
        if not self._rate_allowed(context):
            return get_locale_text("i18n_server_shell.err_write_failed")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if append and target.exists():
                with target.open("ab") as handle:
                    handle.write(payload)
            else:
                target.write_bytes(payload)
        except OSError:
            return get_locale_text("i18n_server_shell.err_write_failed")
        return ""

    def _delete_file(self, context: ShellContext, path: str) -> str:
        if path == context.home or not self._under_home(context, path):
            return get_locale_text("i18n_server_shell.err_permission_denied")
        if path in context.nodes or self._is_secret(context, path):
            return get_locale_text("i18n_server_shell.err_permission_denied")
        target = self._player_path(context, path)
        if target is None:
            return get_locale_text("i18n_server_shell.err_permission_denied")
        if not target.is_file():
            return get_locale_text("i18n_server_shell.err_no_such_file")
        if not self._rate_allowed(context):
            return get_locale_text("i18n_server_shell.err_write_failed")
        try:
            target.unlink()
        except OSError:
            return get_locale_text("i18n_server_shell.err_delete_failed")
        return ""

    def _touch_file(self, context: ShellContext, path: str) -> str:
        if path in context.nodes:
            return get_locale_text("i18n_server_shell.err_permission_denied")
        target = self._player_path(context, path)
        if target and target.is_file():
            try:
                os.utime(target, None)
                return ""
            except OSError:
                return get_locale_text("i18n_server_shell.err_operation_failed")
        return self._write_file(context, path, "")

    def _execute(self, context: ShellContext, raw: str) -> ShellResult:
        if not raw:
            return ShellResult()
        tokens = self._tokens(raw)
        if not tokens:
            return ShellResult(get_locale_text("i18n_server_shell.err_syntax"), 1)
        if tokens[0].lower() == "help" and len(tokens) > 1 and tokens[1].lower() in ("system", "shell"):
            return self._cmd_help(context, [], None)
        segments: list[list[str]] = []
        current: list[str] = []
        for token in tokens:
            if token == "|":
                if not current:
                    return ShellResult(get_locale_text("i18n_server_shell.err_syntax"), 1)
                segments.append(current)
                current = []
            else:
                current.append(token)
        if not current:
            return ShellResult(get_locale_text("i18n_server_shell.err_syntax"), 1)
        segments.append(current)

        stdin = ""
        clear = False
        for index, segment in enumerate(segments):
            args, redirect, append, input_file = self._parse_segment(segment)
            if input_file:
                input_path = self._resolve(context, input_file)
                content = self._read_file(context, input_path)
                if content is None:
                    return ShellResult(get_locale_text("i18n_server_shell.err_input_no_file", path=input_file), 1)
                stdin = content
            if not args:
                return ShellResult(get_locale_text("i18n_server_shell.err_syntax"), 1)
            first = args[0].lower()
            if first in DENIED:
                if first == "sudo":
                    return ShellResult(get_locale_text("i18n_server_shell.err_sudo_denied"), 1)
                return ShellResult(
                    get_locale_text("i18n_server_shell.err_command_denied", command=first), 1
                )
            handler_name = COMMANDS.get(first)
            if handler_name is None:
                return ShellResult(get_locale_text("i18n_server_shell.err_command_missing", command=first), 1)
            if len(segments) > 1 and first in STATEFUL:
                return ShellResult(get_locale_text("i18n_server_shell.err_stateful_in_pipe", command=first), 1)
            if redirect and index != len(segments) - 1:
                return ShellResult(get_locale_text("i18n_server_shell.err_redirect_only_tail"), 1)
            handler = getattr(self, handler_name)
            result = handler(context, args[1:], stdin)
            clear = result.clear
            if result.status != 0:
                return result
            stdin = result.text
            if redirect:
                error = self._write_file(context, self._resolve(context, redirect), stdin, append)
                if error:
                    return ShellResult(get_locale_text("i18n_server_shell.err_redirect", path=redirect, error=error), 1)
                return ShellResult("", 0, clear)
        return ShellResult(stdin, 0, clear)

    def _parse_segment(
        self, tokens: list[str]
    ) -> tuple[list[str], str | None, bool, str | None]:
        args: list[str] = []
        redirect: str | None = None
        input_file: str | None = None
        append = False
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token in (">", ">>"):
                if index + 1 >= len(tokens) or redirect:
                    raise ValueError
                redirect = tokens[index + 1]
                append = token == ">>"
                index += 2
                continue
            if token == "<":
                if index + 1 >= len(tokens) or input_file:
                    raise ValueError
                input_file = tokens[index + 1]
                index += 2
                continue
            args.append(token)
            index += 1
        return args, redirect, append, input_file
