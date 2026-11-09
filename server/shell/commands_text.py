from __future__ import annotations

from game.data.locale_data import get_locale_text

from .models import ShellContext, ShellResult
from .registry import command as _command


class TextCommands:
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
                    return ShellResult(get_locale_text("i18n_server_shell.err_head_invalid_lines"), 1)
                index += 2
            elif args[index].startswith("-n") and len(args[index]) > 2:
                try:
                    count = int(args[index][2:])
                except ValueError:
                    return ShellResult(get_locale_text("i18n_server_shell.err_head_invalid_lines"), 1)
                index += 1
            else:
                files.append(args[index])
                index += 1
        if files:
            content = self._read_file(context, self._resolve(context, files[0]))
            if content is None:
                return ShellResult(get_locale_text("i18n_server_shell.err_head_no_such_file", path=files[0]), 1)
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
                    return ShellResult(get_locale_text("i18n_server_shell.err_tail_invalid_lines"), 1)
                index += 2
            elif args[index].startswith("-n") and len(args[index]) > 2:
                try:
                    count = int(args[index][2:])
                except ValueError:
                    return ShellResult(get_locale_text("i18n_server_shell.err_tail_invalid_lines"), 1)
                index += 1
            else:
                files.append(args[index])
                index += 1
        if files:
            content = self._read_file(context, self._resolve(context, files[0]))
            if content is None:
                return ShellResult(get_locale_text("i18n_server_shell.err_tail_no_such_file", path=files[0]), 1)
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
                    return ShellResult(get_locale_text("i18n_server_shell.err_wc_no_such_file", path=value), 1)
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
            return ShellResult(get_locale_text("i18n_server_shell.err_grep_missing_pattern"), 1)
        sources = []
        if files:
            for value in files:
                content = self._read_file(context, self._resolve(context, value))
                if content is None:
                    return ShellResult(get_locale_text("i18n_server_shell.err_grep_no_such_file", path=value), 1)
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
