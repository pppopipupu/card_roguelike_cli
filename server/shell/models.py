from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .fs import Node


@dataclass
class ShellResult:
    text: str = ""
    status: int = 0
    clear: bool = False


@dataclass
class ShellContext:
    uuid: str
    user: str
    home: str
    cwd: str
    previous: str
    history: list[str]
    state_path: Path
    files_dir: Path
    nodes: dict[str, Node]
