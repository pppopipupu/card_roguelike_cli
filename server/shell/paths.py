from pathlib import Path
import posixpath

from .fs import Node
from .models import ShellContext


class ShellPathMixin:
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
