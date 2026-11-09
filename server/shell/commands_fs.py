from __future__ import annotations

import fnmatch
import posixpath
from datetime import datetime

from game.data.locale_data import get_locale_text

from .fs import Node
from .models import ShellContext, ShellResult
from .registry import COMMANDS, command as _command

DENIED = {
    "mkdir", "rmdir", "mv", "cp", "ln", "chmod", "chown", "chgrp",
    "sudo", "su", "apt", "apt-get", "dnf", "yum", "pacman", "service",
    "kill", "pkill", "killall", "reboot", "shutdown", "umount", "crontab", "ssh",
    "scp", "sftp", "curl", "wget", "nc", "telnet", "ftp", "vim",
    "vi", "nano", "emacs", "less", "more", "pip", "pip3", "npm",
    "node", "python", "python3", "make", "gcc", "g++", "bash", "sh",
    "zsh", "fish", "dd", "fdisk", "mkfs", "passwd", "useradd", "usermod",
    "groupadd", "insmod", "modprobe", "iptables", "ufw", "nft", "cargo", "go",
    "java", "javac", "php", "ruby", "perl",
}


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


class FilesystemCommands:
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
            return ShellResult(get_locale_text("i18n_server_shell.err_ls_access", path=targets[0] if targets else target), 1)
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
            return ShellResult(get_locale_text("i18n_server_shell.err_cd_too_many_args"), 1)
        value = args[0] if args else "~"
        if value == "-":
            value = context.previous
        target = self._resolve(context, value)
        if self._is_secret(context, target):
            return ShellResult(get_locale_text("i18n_server_shell.err_cd_denied", path=value), 1)
        if not self._is_dir(context, target):
            return ShellResult(get_locale_text("i18n_server_shell.err_cd_no_such_dir", path=value), 1)
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
                return ShellResult(get_locale_text("i18n_server_shell.err_cat_no_such_file", path=value), 1)
            if node.kind == "dir":
                return ShellResult(get_locale_text("i18n_server_shell.err_cat_is_dir", path=value), 1)
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
            return ShellResult(get_locale_text("i18n_server_shell.err_touch_missing_file"), 1)
        for value in args:
            error = self._touch_file(context, self._resolve(context, value))
            if error:
                return ShellResult(get_locale_text("i18n_server_shell.err_touch", path=value, error=error), 1)
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
            return ShellResult(get_locale_text("i18n_server_shell.err_rm_missing_operand"), 1)
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
                    return ShellResult(get_locale_text("i18n_server_shell.err_rm_no_such_file", path=value), 1)
                resolved.extend(matches)
            else:
                resolved.append(path)
        for path in resolved:
            node = self._node(context, path)
            if node is None:
                if not force:
                    return ShellResult(get_locale_text("i18n_server_shell.err_rm_no_such_file", path=self._display(context, path)), 1)
                continue
            if path in context.nodes or self._is_secret(context, path) or node.kind == "dir":
                return ShellResult(get_locale_text("i18n_server_shell.err_rm_denied", path=self._display(context, path)), 1)
        for path in resolved:
            if self._node(context, path) is None:
                continue
            error = self._delete_file(context, path)
            if error:
                return ShellResult(get_locale_text("i18n_server_shell.err_rm_failed", path=self._display(context, path), error=error), 1)
        return ShellResult()

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
            return ShellResult(get_locale_text("i18n_server_shell.err_find_no_such_file", path=target), 1)
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
            return ShellResult(get_locale_text("i18n_server_shell.err_tree_not_dir", path=target), 1)
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
            return ShellResult(get_locale_text("i18n_server_shell.err_stat_missing_file"), 1)
        path = self._resolve(context, args[0])
        node = self._node(context, path)
        if node is None:
            return ShellResult(get_locale_text("i18n_server_shell.err_stat_no_such_file", path=args[0]), 1)
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
            return ShellResult(get_locale_text("i18n_server_shell.err_file_missing_file"), 1)
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
            return ShellResult(get_locale_text("i18n_server_shell.err_du_no_such_file", path=target), 1)
        total = 0
        for path in self._walk(context, target):
            node = self._node(context, path)
            if node and node.kind == "file":
                total += len(node.content.encode("utf-8"))
        return ShellResult(f"{_size_text(total, human)}\t{self._display(context, target)}\n")

    @_command("which", "type")
    def _cmd_which(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if not args:
            return ShellResult(get_locale_text("i18n_server_shell.err_which_missing_command"), 1)
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
            return ShellResult(get_locale_text("i18n_server_shell.err_man_missing_command"), 1)
        key = MANUAL.get(args[0].lower())
        if not key:
            return ShellResult(get_locale_text("i18n_server_shell.err_man_no_page", command=args[0]), 1)
        return ShellResult(get_locale_text("i18n_server_shell." + key) + "\n")

    @_command("help")
    def _cmd_help(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(get_locale_text("i18n_server_shell.help_text"))

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
    "ls": "manual_ls",
    "cd": "manual_cd",
    "cat": "manual_cat",
    "echo": "manual_echo",
    "rm": "manual_rm",
    "uname": "manual_uname",
    "neofetch": "manual_neofetch",
    "git": "manual_git",
}
