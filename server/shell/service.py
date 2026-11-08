from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import re
import shlex
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from .commands_extra import ExtraCommands
from .fs import Node, build_nodes
from .models import ShellContext, ShellResult
from .registry import COMMANDS, command as _command

MAX_FILE_BYTES = 512 * 1024
MAX_FILES = 32
MAX_TOTAL_BYTES = 4 * 1024 * 1024
WRITE_LIMIT = 8
WRITE_WINDOW = 60.0
MAX_OUTPUT = 256 * 1024
MAX_HISTORY = 200


DENIED = {
    "mkdir",
    "rmdir",
    "mv",
    "cp",
    "ln",
    "chmod",
    "chown",
    "chgrp",
    "sudo",
    "su",
    "apt",
    "apt-get",
    "dnf",
    "yum",
    "pacman",
    "service",
    "kill",
    "pkill",
    "killall",
    "reboot",
    "shutdown",
    "umount",
    "crontab",
    "ssh",
    "scp",
    "sftp",
    "curl",
    "wget",
    "nc",
    "telnet",
    "ftp",
    "vim",
    "vi",
    "nano",
    "emacs",
    "less",
    "more",
    "pip",
    "pip3",
    "npm",
    "node",
    "python",
    "python3",
    "make",
    "gcc",
    "g++",
    "bash",
    "sh",
    "zsh",
    "fish",
    "dd",
    "fdisk",
    "mkfs",
    "passwd",
    "useradd",
    "usermod",
    "groupadd",
    "insmod",
    "modprobe",
    "iptables",
    "ufw",
    "nft",
    "cargo",
    "go",
    "java",
    "javac",
    "php",
    "ruby",
    "perl",
}

STATEFUL = {"cd", "rm", "touch", "mkdir", "rmdir", "mv", "cp", "chmod", "chown"}


def _safe_uuid(value: str) -> str:
    return "".join(c for c in value if c.isalnum() or c in ("-", "_")) or "anonymous"


def _safe_user(value: str) -> str:
    user = re.sub(r"[^a-z0-9_-]", "", (value or "").lower())
    return user or "rogue"


def _size_text(size: int, human: bool = False) -> str:
    if not human:
        return str(size)
    units = ("B", "K", "M", "G")
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"


def _date_text(value: float) -> str:
    return datetime.fromtimestamp(value).strftime("%b %d %H:%M")


class ShellService(ExtraCommands):
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._writes: dict[str, deque[float]] = {}

    def handles(self, command: str) -> bool:
        tokens = self._tokens(command)
        if not tokens:
            return False
        first = tokens[0].lower()
        if first == "help" and len(tokens) > 1 and tokens[1].lower() == "shell":
            return True
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
            result = ShellResult("bash: 终端内部错误。\n", 1)
        if len(result.text) > MAX_OUTPUT:
            result.text = result.text[:MAX_OUTPUT] + "\n[输出已截断]\n"
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

    def _display(self, context: ShellContext, path: str) -> str:
        if path == context.home:
            return "~"
        if path.startswith(context.home + "/"):
            return "~" + path[len(context.home) :]
        return path

    def _resolve(self, context: ShellContext, value: str) -> str:
        if not value or value == "~":
            path = context.home
        elif value.startswith("~/"):
            path = context.home + value[1:]
        elif value.startswith("/"):
            path = value
        else:
            path = posixpath.join(context.cwd, value)
        path = posixpath.normpath(path)
        return path if path.startswith("/") else "/" + path

    def _under_home(self, context: ShellContext, path: str) -> bool:
        return path == context.home or path.startswith(context.home + "/")

    def _is_secret(self, context: ShellContext, path: str) -> bool:
        secret = context.home + "/.secrets"
        return path == secret or path.startswith(secret + "/")

    def _player_path(self, context: ShellContext, path: str) -> Path | None:
        if not self._under_home(context, path) or path == context.home:
            return None
        if self._is_secret(context, path):
            return None
        relative = path[len(context.home) + 1 :]
        if not relative or ".." in Path(relative).parts:
            return None
        target = (context.files_dir / relative).resolve()
        base = context.files_dir.resolve()
        if target != base and base not in target.parents:
            return None
        return target

    def _player_files(self, context: ShellContext) -> dict[str, Path]:
        result: dict[str, Path] = {}
        if not context.files_dir.exists():
            return result
        for path in context.files_dir.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(context.files_dir).as_posix()
            if relative == "state.json" or relative.startswith(".secrets"):
                continue
            result[f"{context.home}/{relative}"] = path
        return result

    def _node(self, context: ShellContext, path: str) -> Node | None:
        if self._is_secret(context, path):
            return None
        node = context.nodes.get(path)
        if node is not None:
            return node
        player = self._player_path(context, path)
        if player and player.is_file():
            try:
                stat = player.stat()
                return Node(
                    "file",
                    player.read_text(encoding="utf-8"),
                    "-rw-r--r--",
                    context.user,
                    context.user,
                    stat.st_mtime,
                )
            except OSError:
                return None
        return None

    def _is_dir(self, context: ShellContext, path: str) -> bool:
        node = self._node(context, path)
        return node is not None and node.kind == "dir"

    def _children(self, context: ShellContext, path: str) -> list[str]:
        children: set[str] = set()
        for candidate in context.nodes:
            if posixpath.dirname(candidate) == path:
                children.add(candidate)
        for candidate in self._player_files(context):
            if posixpath.dirname(candidate) == path:
                children.add(candidate)
        return sorted(children, key=lambda item: posixpath.basename(item))

    def _read_file(self, context: ShellContext, path: str) -> str | None:
        node = self._node(context, path)
        if node is None or node.kind != "file":
            return None
        return node.content

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
            return "权限被拒"
        if self._is_secret(context, path):
            return "权限被拒"
        if path in context.nodes:
            return "权限被拒"
        parent = posixpath.dirname(path)
        if not self._is_dir(context, parent) or self._is_secret(context, parent):
            return "没有那个目录"
        payload = content.encode("utf-8")
        if len(payload) > MAX_FILE_BYTES:
            return "文件超过 512 KB 限制"
        target = self._player_path(context, path)
        if target is None:
            return "权限被拒"
        existing_size = target.stat().st_size if target.is_file() else 0
        files = self._player_files(context)
        if target not in files.values() and len(files) >= MAX_FILES:
            return "文件数量超过限制"
        total = sum(item.stat().st_size for item in files.values())
        if total - existing_size + len(payload) > MAX_TOTAL_BYTES:
            return "终端存储空间不足"
        if not self._rate_allowed(context):
            return "写入过于频繁，请稍后再试"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if append and target.exists():
                with target.open("ab") as handle:
                    handle.write(payload)
            else:
                target.write_bytes(payload)
        except OSError:
            return "写入失败"
        return ""

    def _delete_file(self, context: ShellContext, path: str) -> str:
        if path == context.home or not self._under_home(context, path):
            return "权限被拒"
        if path in context.nodes or self._is_secret(context, path):
            return "权限被拒"
        target = self._player_path(context, path)
        if target is None:
            return "权限被拒"
        if not target.is_file():
            return "没有那个文件"
        if not self._rate_allowed(context):
            return "写入过于频繁，请稍后再试"
        try:
            target.unlink()
        except OSError:
            return "删除失败"
        return ""

    def _touch_file(self, context: ShellContext, path: str) -> str:
        if path in context.nodes:
            return "权限被拒"
        target = self._player_path(context, path)
        if target and target.is_file():
            try:
                os.utime(target, None)
                return ""
            except OSError:
                return "操作失败"
        return self._write_file(context, path, "")

    def _execute(self, context: ShellContext, raw: str) -> ShellResult:
        if not raw:
            return ShellResult()
        tokens = self._tokens(raw)
        if not tokens:
            return ShellResult("bash: 语法错误。\n", 1)
        if tokens[0].lower() == "help" and len(tokens) > 1 and tokens[1].lower() == "shell":
            return self._cmd_help(context, [], None)
        segments: list[list[str]] = []
        current: list[str] = []
        for token in tokens:
            if token == "|":
                if not current:
                    return ShellResult("bash: 语法错误。\n", 1)
                segments.append(current)
                current = []
            else:
                current.append(token)
        if not current:
            return ShellResult("bash: 语法错误。\n", 1)
        segments.append(current)

        stdin = ""
        clear = False
        for index, segment in enumerate(segments):
            args, redirect, append, input_file = self._parse_segment(segment)
            if input_file:
                input_path = self._resolve(context, input_file)
                content = self._read_file(context, input_path)
                if content is None:
                    return ShellResult(f"bash: {input_file}: 没有那个文件。\n", 1)
                stdin = content
            if not args:
                return ShellResult("bash: 语法错误。\n", 1)
            first = args[0].lower()
            if first in DENIED:
                if first == "sudo":
                    return ShellResult("sudo: 权限被拒。此终端受沙箱限制。\n", 1)
                return ShellResult(
                    f"bash: {first}: 权限被拒（沙箱限制）。\n", 1
                )
            handler_name = COMMANDS.get(first)
            if handler_name is None:
                return ShellResult(f"bash: {first}: 未找到命令。\n", 1)
            if len(segments) > 1 and first in STATEFUL:
                return ShellResult(f"bash: {first}: 不能在管道中执行。\n", 1)
            if redirect and index != len(segments) - 1:
                return ShellResult("bash: 只支持在管道末尾重定向。\n", 1)
            handler = getattr(self, handler_name)
            result = handler(context, args[1:], stdin)
            clear = result.clear
            if result.status != 0:
                return result
            stdin = result.text
            if redirect:
                error = self._write_file(context, self._resolve(context, redirect), stdin, append)
                if error:
                    return ShellResult(f"bash: {redirect}: {error}。\n", 1)
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

    @_command("ls", "dir")
    def _cmd_ls(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        show_all = False
        long_format = False
        human = False
        targets: list[str] = []
        for arg in args:
            if arg.startswith("-") and len(arg) > 1:
                show_all = show_all or "a" in arg
                long_format = long_format or "l" in arg
                human = human or "h" in arg
            else:
                targets.append(arg)
        target = self._resolve(context, targets[0]) if targets else context.cwd
        node = self._node(context, target)
        if node is None:
            return ShellResult(f"ls: 无法访问 '{targets[0] if targets else target}': 没有那个文件或目录\n", 1)
        if node.kind == "file":
            return ShellResult(self._ls_line(context, target, node, long_format, human) + "\n")
        names: list[str] = []
        if show_all:
            names.extend([".", ".."])
        for child in self._children(context, target):
            name = posixpath.basename(child)
            if not show_all and name.startswith("."):
                continue
            names.append(name)
        if not long_format:
            return ShellResult("  ".join(names) + ("\n" if names else ""))
        lines = []
        total = 0
        for name in names:
            if name == ".":
                child_path = target
            elif name == "..":
                child_path = posixpath.dirname(target)
            else:
                child_path = posixpath.join(target, name)
            child = self._node(context, child_path)
            if child is None:
                continue
            size = 4096 if child.kind == "dir" else len(child.content.encode("utf-8"))
            total += (size + 511) // 512
            lines.append(self._ls_line(context, child_path, child, True, human, name))
        output = [f"total {total}"] + lines
        return ShellResult("\n".join(output) + "\n")

    def _ls_line(
        self,
        context: ShellContext,
        path: str,
        node: Node,
        long_format: bool,
        human: bool,
        name: str | None = None,
    ) -> str:
        label = name or posixpath.basename(path) or path
        if not long_format:
            return label
        size = 4096 if node.kind == "dir" else len(node.content.encode("utf-8"))
        owner = node.owner
        group = node.group
        return (
            f"{node.mode} 1 {owner} {group} "
            f"{_size_text(size, human):>7} {_date_text(node.mtime)} {label}"
        )

    @_command("cd")
    def _cmd_cd(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if len(args) > 1:
            return ShellResult("cd: 参数过多。\n", 1)
        value = args[0] if args else "~"
        if value == "-":
            value = context.previous
        target = self._resolve(context, value)
        if self._is_secret(context, target):
            return ShellResult(f"cd: {value}: 权限被拒。\n", 1)
        if not self._is_dir(context, target):
            return ShellResult(f"cd: {value}: 没有那个目录。\n", 1)
        context.previous = context.cwd
        context.cwd = target
        return ShellResult()

    @_command("pwd")
    def _cmd_pwd(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(context.cwd + "\n")

    @_command("cat")
    def _cmd_cat(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if not args:
            return ShellResult(stdin or "")
        output = []
        for value in args:
            path = self._resolve(context, value)
            node = self._node(context, path)
            if node is None:
                return ShellResult(f"cat: {value}: 没有那个文件或目录。\n", 1)
            if node.kind == "dir":
                return ShellResult(f"cat: {value}: 是一个目录。\n", 1)
            output.append(node.content)
        return ShellResult("".join(output))

    @_command("echo")
    def _cmd_echo(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        newline = True
        escape = False
        while args and args[0] in ("-n", "-e", "-ne", "-en"):
            newline = newline and "n" not in args[0]
            escape = escape or "e" in args[0]
            args = args[1:]
        text = " ".join(args)
        if escape:
            text = (
                text.replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace("\\\\", "\\")
            )
        if newline:
            text += "\n"
        return ShellResult(text)

    @_command("printf")
    def _cmd_printf(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if not args:
            return ShellResult("")
        text = args[0]
        if len(args) > 1:
            text = text.replace("%s", args[1], 1)
        text = text.replace("\\n", "\n").replace("\\t", "\t")
        return ShellResult(text)

    @_command("touch")
    def _cmd_touch(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if not args:
            return ShellResult("touch: 缺少文件。\n", 1)
        for value in args:
            error = self._touch_file(context, self._resolve(context, value))
            if error:
                return ShellResult(f"touch: {value}: {error}。\n", 1)
        return ShellResult()

    @_command("rm")
    def _cmd_rm(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        recursive = False
        force = False
        targets = []
        for arg in args:
            if arg.startswith("-") and len(arg) > 1:
                recursive = recursive or "r" in arg or "R" in arg
                force = force or "f" in arg
            else:
                targets.append(arg)
        if not targets:
            return ShellResult("rm: 缺少操作数。\n", 1)
        resolved: list[str] = []
        for value in targets:
            path = self._resolve(context, value)
            if any(char in value for char in "*?["):
                parent = posixpath.dirname(path)
                pattern = posixpath.basename(path)
                matches = [
                    child
                    for child in self._children(context, parent)
                    if fnmatch.fnmatch(posixpath.basename(child), pattern)
                ]
                if not matches and not force:
                    return ShellResult(f"rm: 无法删除 '{value}': 没有那个文件或目录\n", 1)
                resolved.extend(matches)
            else:
                resolved.append(path)
        for path in resolved:
            node = self._node(context, path)
            if node is None:
                if not force:
                    return ShellResult(f"rm: 无法删除 '{self._display(context, path)}': 没有那个文件或目录\n", 1)
                continue
            if path in context.nodes or self._is_secret(context, path) or node.kind == "dir":
                return ShellResult(f"rm: 无法删除 '{self._display(context, path)}': 权限被拒\n", 1)
        for path in resolved:
            if self._node(context, path) is None:
                continue
            error = self._delete_file(context, path)
            if error:
                return ShellResult(f"rm: 无法删除 '{self._display(context, path)}': {error}\n", 1)
        return ShellResult()

    @_command("head")
    def _cmd_head(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        count = 10
        files = []
        index = 0
        while index < len(args):
            if args[index] == "-n" and index + 1 < len(args):
                try:
                    count = int(args[index + 1])
                except ValueError:
                    return ShellResult("head: 无效的行数。\n", 1)
                index += 2
            elif args[index].startswith("-n") and len(args[index]) > 2:
                try:
                    count = int(args[index][2:])
                except ValueError:
                    return ShellResult("head: 无效的行数。\n", 1)
                index += 1
            else:
                files.append(args[index])
                index += 1
        if files:
            content = self._read_file(context, self._resolve(context, files[0]))
            if content is None:
                return ShellResult(f"head: {files[0]}: 没有那个文件。\n", 1)
        else:
            content = stdin or ""
        return ShellResult("".join(content.splitlines(keepends=True)[:count]))

    @_command("tail")
    def _cmd_tail(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        count = 10
        files = []
        index = 0
        while index < len(args):
            if args[index] == "-n" and index + 1 < len(args):
                try:
                    count = int(args[index + 1])
                except ValueError:
                    return ShellResult("tail: 无效的行数。\n", 1)
                index += 2
            elif args[index].startswith("-n") and len(args[index]) > 2:
                try:
                    count = int(args[index][2:])
                except ValueError:
                    return ShellResult("tail: 无效的行数。\n", 1)
                index += 1
            else:
                files.append(args[index])
                index += 1
        if files:
            content = self._read_file(context, self._resolve(context, files[0]))
            if content is None:
                return ShellResult(f"tail: {files[0]}: 没有那个文件。\n", 1)
        else:
            content = stdin or ""
        return ShellResult("".join(content.splitlines(keepends=True)[-count:]))

    @_command("wc")
    def _cmd_wc(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        flags = "".join(arg for arg in args if arg.startswith("-"))
        files = [arg for arg in args if not arg.startswith("-")]
        sources = []
        if files:
            for value in files:
                content = self._read_file(context, self._resolve(context, value))
                if content is None:
                    return ShellResult(f"wc: {value}: 没有那个文件。\n", 1)
                sources.append((value, content))
        else:
            sources.append(("", stdin or ""))
        lines = []
        for name, content in sources:
            line_count = content.count("\n")
            word_count = len(content.split())
            byte_count = len(content.encode("utf-8"))
            if "l" in flags:
                value = line_count
            elif "w" in flags:
                value = word_count
            elif "c" in flags:
                value = byte_count
            else:
                value = f"{line_count:>7} {word_count:>7} {byte_count:>7}"
            lines.append(f"{value} {name}".rstrip())
        return ShellResult("\n".join(lines) + "\n")

    @_command("grep", "egrep")
    def _cmd_grep(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        ignore_case = False
        line_numbers = False
        invert = False
        pattern = ""
        files = []
        for arg in args:
            if arg.startswith("-") and len(arg) > 1:
                ignore_case = ignore_case or "i" in arg
                line_numbers = line_numbers or "n" in arg
                invert = invert or "v" in arg
            elif not pattern:
                pattern = arg
            else:
                files.append(arg)
        if not pattern:
            return ShellResult("grep: 缺少模式。\n", 1)
        sources = []
        if files:
            for value in files:
                content = self._read_file(context, self._resolve(context, value))
                if content is None:
                    return ShellResult(f"grep: {value}: 没有那个文件。\n", 1)
                sources.append((value, content))
        else:
            sources.append(("", stdin or ""))
        needle = pattern.lower() if ignore_case else pattern
        output = []
        for name, content in sources:
            for number, line in enumerate(content.splitlines(), 1):
                haystack = line.lower() if ignore_case else line
                matched = needle in haystack
                if matched == invert:
                    continue
                prefix = ""
                if len(sources) > 1 and name:
                    prefix += name + ":"
                if line_numbers:
                    prefix += f"{number}:"
                output.append(prefix + line)
        return ShellResult("\n".join(output) + ("\n" if output else ""), 0 if output else 1)

    @_command("find")
    def _cmd_find(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        target = context.cwd
        pattern = "*"
        index = 0
        while index < len(args):
            if args[index] == "-name" and index + 1 < len(args):
                pattern = args[index + 1]
                index += 2
            elif not args[index].startswith("-"):
                target = self._resolve(context, args[index])
                index += 1
            else:
                index += 1
        if self._node(context, target) is None:
            return ShellResult(f"find: '{target}': 没有那个文件或目录\n", 1)
        output = []
        for path in self._walk(context, target):
            if fnmatch.fnmatch(posixpath.basename(path), pattern):
                output.append(path)
        return ShellResult("\n".join(output) + ("\n" if output else ""))

    def _walk(self, context: ShellContext, path: str) -> list[str]:
        result = [path]
        node = self._node(context, path)
        if node and node.kind == "dir":
            for child in self._children(context, path):
                result.extend(self._walk(context, child))
        return result

    @_command("tree")
    def _cmd_tree(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        target = self._resolve(context, args[0]) if args else context.cwd
        if not self._is_dir(context, target):
            return ShellResult(f"tree: {target}: 不是目录\n", 1)
        lines = [self._display(context, target)]

        def walk(path: str, prefix: str) -> None:
            children = self._children(context, path)
            for index, child in enumerate(children):
                last = index == len(children) - 1
                lines.append(prefix + ("└── " if last else "├── ") + posixpath.basename(child))
                if len(lines) > 200:
                    return
                if self._is_dir(context, child):
                    walk(child, prefix + ("    " if last else "│   "))

        walk(target, "")
        if len(lines) > 200:
            lines.append("...")
        return ShellResult("\n".join(lines) + "\n")

    @_command("stat")
    def _cmd_stat(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if not args:
            return ShellResult("stat: 缺少文件。\n", 1)
        path = self._resolve(context, args[0])
        node = self._node(context, path)
        if node is None:
            return ShellResult(f"stat: 无法获取 '{args[0]}' 的状态: 没有那个文件或目录\n", 1)
        size = 4096 if node.kind == "dir" else len(node.content.encode("utf-8"))
        return ShellResult(
            f"  File: {args[0]}\n"
            f"  Size: {size:<12} Blocks: {(size + 511) // 512:<8} IO Block: 4096\n"
            f"Access: ({node.mode[1:4]})  Uid: (1000/{node.owner})   Gid: (1000/{node.group})\n"
            f"Modify: {datetime.fromtimestamp(node.mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    @_command("file")
    def _cmd_file(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if not args:
            return ShellResult("file: 缺少文件。\n", 1)
        output = []
        for value in args:
            path = self._resolve(context, value)
            node = self._node(context, path)
            if node is None:
                output.append(f"{value}: cannot open")
            elif node.kind == "dir":
                output.append(f"{value}: directory")
            elif not node.content:
                output.append(f"{value}: empty")
            elif node.content.lstrip().startswith(("{", "[")):
                output.append(f"{value}: JSON text data")
            else:
                output.append(f"{value}: Unicode text, UTF-8 text")
        return ShellResult("\n".join(output) + "\n")

    @_command("du")
    def _cmd_du(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        human = any("h" in arg for arg in args if arg.startswith("-"))
        target = self._resolve(context, next((arg for arg in args if not arg.startswith("-")), "."))
        if self._node(context, target) is None:
            return ShellResult(f"du: 无法访问 '{target}': 没有那个文件或目录\n", 1)
        total = 0
        for path in self._walk(context, target):
            node = self._node(context, path)
            if node and node.kind == "file":
                total += len(node.content.encode("utf-8"))
        return ShellResult(f"{_size_text(total, human)}\t{self._display(context, target)}\n")

    @_command("which", "type")
    def _cmd_which(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if not args:
            return ShellResult("which: 缺少命令。\n", 1)
        output = []
        missing = False
        for name in args:
            if name in COMMANDS or name in DENIED:
                output.append(f"/usr/bin/{name}")
            else:
                missing = True
        return ShellResult("\n".join(output) + ("\n" if output else ""), 1 if missing and not output else 0)

    @_command("man")
    def _cmd_man(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if not args:
            return ShellResult("man: 缺少命令。\n", 1)
        text = MANUAL.get(args[0].lower())
        if not text:
            return ShellResult(f"man: 没有 {args[0]} 的手册页。\n", 1)
        return ShellResult(text + "\n")

    @_command("help")
    def _cmd_help(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(HELP_TEXT)

    @_command("neofetch")
    def _cmd_neofetch(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            f"       .------.        {context.user}@rogue-core\n"
            "      /  .--.  \\       ------------------\n"
            "     |  /    \\  |      OS: Rogue Core 7.9.3 LTS x86_64\n"
            "     | |  ()  | |      Host: Dungeon Node 07\n"
            "     |  \\    /  |      Kernel: 6.8.12-rogue\n"
            "      \\  '--'  /       Uptime: 4 days, 10 hours, 54 mins\n"
            "       '------'        Shell: bash 5.2.21\n"
            "        /|    |\\       Terminal: xterm-256color\n"
            "       / |    | \\      CPU: AMD Ryzen 9 7950X3D (32) @ 4.20GHz\n"
            "      /  |    |  \\     Memory: 7982MiB / 31992MiB\n"
            "         `----'         Deck: 9 cards / 3 relics / 1 curse\n"
        )

MANUAL = {
    "ls": "ls [-a] [-l] [path]\n列出目录内容。玩家文件与只读彩蛋文件会同时显示。",
    "cd": "cd [path]\n切换目录。.secrets 目录禁止进入。",
    "cat": "cat <file>\n读取文本文件。彩蛋文件可读，但不可删除。",
    "echo": "echo [-n] <text> [> file] [>> file]\n输出文本，或写入/追加到可写目录中的文本文件。",
    "rm": "rm [-f] <file>\n删除玩家创建的文本文件。彩蛋文件、.secrets 与目录受保护。",
    "uname": "uname [-a]\n显示伪造的 Rogue Core 内核信息。",
    "neofetch": "neofetch\n显示终端与卡牌周目摘要。",
    "git": "git status|log|branch|remote|diff\n只读仓库信息。",
}

HELP_TEXT = (
    "可用终端命令：\n"
    "  ls / ls -la / cd / pwd / cat / echo / touch / rm\n"
    "  uname / whoami / id / hostname / date / uptime\n"
    "  df / free / ps / top / env / history / clear\n"
    "  head / tail / wc / grep / find / tree / stat / file / du\n"
    "  which / man / neofetch / git / docker / systemctl / journalctl\n"
    "  ip / ss / lscpu / lsblk / mount / printf\n"
    "\n"
    "可写：/home 与 /home/dungeon 下的现有目录。\n"
    "限制：单文件 512 KB，8 次写入/分钟，最多 32 个文件。\n"
    "受保护：彩蛋文件与 .secrets 目录不可删除。\n"
    "其他变更命令一律权限被拒。\n"
)
