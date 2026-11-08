from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Node:
    kind: str
    content: str = ""
    mode: str = "-r--r--r--"
    owner: str = "root"
    group: str = "root"
    mtime: float = 0.0


def _file(content: str, mtime: float, owner: str = "root") -> Node:
    return Node("file", content, "-r--r--r--", owner, owner, mtime)


def _dir(mtime: float, mode: str = "drwxr-xr-x", owner: str = "root") -> Node:
    return Node("dir", "", mode, owner, owner, mtime)


def build_nodes(user: str) -> dict[str, Node]:
    home = f"/home/{user}"
    now = time.time()
    old = now - 86400 * 18
    nodes: dict[str, Node] = {}
    for path in ("/", "/bin", "/etc", "/home", "/proc", "/tmp", "/usr", "/usr/bin", "/var", "/var/log"):
        nodes[path] = _dir(old, "drwxr-xr-x", "root")
    nodes["/root"] = _dir(old, "drwx------", "root")
    nodes[home] = _dir(now - 86400 * 4, "drwxr-xr-x", user)
    nodes[f"{home}/.secrets"] = _dir(old, "drwx------", "root")
    for path in (
        f"{home}/dungeon",
        f"{home}/dungeon/cards",
        f"{home}/dungeon/runs",
        f"{home}/notes",
    ):
        nodes[path] = _dir(old, "drwxr-xr-x", "root")

    nodes["/etc/hostname"] = _file("rogue-core\n", old)
    nodes["/etc/rogue-release"] = _file(
        "ROGUE CORE 7.9.3 LTS\n"
        "codename: MERCURY VAULT\n"
        "kernel: 6.8.12-rogue\n"
        "build: cards-2026.11.08\n"
        "node: dungeon-07\n",
        old,
    )
    nodes["/etc/passwd"] = _file(
        "root:x:0:0:root:/root:/bin/bash\n"
        f"{user}:x:1000:1000:Rogue Runner:{home}:/bin/bash\n"
        "cardd:x:991:991:Card Daemon:/var/lib/cardd:/usr/sbin/nologin\n",
        old,
    )
    nodes["/etc/os-release"] = _file(
        'NAME="Rogue Core"\n'
        'VERSION="7.9.3 LTS (Mercury Vault)"\n'
        'ID=rogue-core\n'
        'PRETTY_NAME="Rogue Core 7.9.3 LTS"\n',
        old,
    )
    nodes["/proc/version"] = _file(
        "Linux version 6.8.12-rogue (forge@rogue-core) "
        "(gcc version 13.2.0) #1 SMP PREEMPT_DYNAMIC "
        "Sun Nov 08 00:00:00 UTC 2026\n",
        old,
    )
    nodes["/proc/cpuinfo"] = _file(
        "processor\t: 0\n"
        "vendor_id\t: AuthenticAMD\n"
        "model name\t: AMD Ryzen 9 7950X3D 16-Core Processor\n"
        "cpu MHz\t\t: 4200.000\n"
        "cache size\t: 98304 KB\n"
        "flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic sep\n"
        "\n"
        "processor\t: 1\n"
        "vendor_id\t: AuthenticAMD\n"
        "model name\t: AMD Ryzen 9 7950X3D 16-Core Processor\n"
        "cpu MHz\t\t: 4200.000\n",
        old,
    )
    nodes["/proc/meminfo"] = _file(
        "MemTotal:       32768000 kB\n"
        "MemFree:        18432000 kB\n"
        "MemAvailable:   24117248 kB\n"
        "SwapTotal:       8388608 kB\n"
        "SwapFree:        8388608 kB\n",
        old,
    )
    nodes["/proc/uptime"] = _file("384921.44 1843900.12\n", old)
    nodes["/var/log/rogue.log"] = _file(
        "[00:00:01] cardd: dungeon node 07 online\n"
        "[00:00:02] cardd: loaded 1482 cards, 96 relics, 41 curses\n"
        "[00:00:03] cardd: mercury coolant loop stable\n"
        "[03:12:44] rune-watch: sealed vault integrity 100%\n"
        "[04:19:02] cardd: player session attached\n"
        "[04:19:02] cardd: deck checksum ok\n",
        now - 3600,
    )
    nodes[f"{home}/README.md"] = _file(
        "# ROGUE CORE // DUNGEON NODE 07\n"
        "\n"
        "本机是卡牌肉鸽终端。玩家可以在当前目录写入文本笔记。\n"
        "\n"
        "试试：ls -la、cat dungeon/deck.json、uname -a、neofetch。\n",
        now - 86400 * 3,
    )
    nodes[f"{home}/.bashrc"] = _file(
        "export PS1='\\u@rogue-core \\w \\$ '\n"
        "export EDITOR=none\n"
        "export PAGER=none\n"
        "alias ll='ls -la'\n"
        "alias cls='clear'\n",
        old,
    )
    nodes[f"{home}/.profile"] = _file(
        "if [ -f ~/.bashrc ]; then\n"
        "  . ~/.bashrc\n"
        "fi\n",
        old,
    )
    nodes[f"{home}/dungeon/README.md"] = _file(
        "# DUNGEON PROJECT\n"
        "\n"
        "这个仓库保存当前冒险者的卡组、遗物和路线记录。\n"
        "不要直接编辑 cards/ascension.json。\n"
        "它不属于当前周目。\n",
        now - 86400 * 9,
    )
    nodes[f"{home}/dungeon/deck.json"] = _file(
        "{\n"
        '  "class": "wizard",\n'
        '  "subclass": "mercury",\n'
        '  "cards": [\n'
        '    {"id": "arcane_spark", "count": 4},\n'
        '    {"id": "mirror_guard", "count": 2},\n'
        '    {"id": "quicksilver_bolt", "count": 2},\n'
        '    {"id": "forbidden_page", "count": 1}\n'
        "  ],\n"
        '  "relics": ["iron_heart", "silent_bell", "mercury_drop"],\n'
        '  "ascension": 7\n'
        "}\n",
        now - 86400 * 2,
    )
    nodes[f"{home}/dungeon/cards/ascension.json"] = _file(
        "{\n"
        '  "name": "汞心",\n'
        '  "rarity": "mythic",\n'
        '  "cost": "3A",\n'
        '  "text": "将所有护盾转化为等量真实伤害。若生命低于 1，改为保留 1 点生命。",\n'
        '  "owner": "mercury-vault",\n'
        '  "sealed": true\n'
        "}\n",
        old,
    )
    nodes[f"{home}/dungeon/runs/2026-11-08.log"] = _file(
        "run 07\n"
        "stage 1  ancient gate       cleared\n"
        "stage 2  hollow library     cleared\n"
        "stage 3  mercury fountain   cleared\n"
        "stage 4  iron choir         cleared\n"
        "stage 5  vault approach     active\n"
        "deck 9 cards / 3 relics / 1 curse\n",
        now - 7200,
    )
    nodes[f"{home}/notes/README.md"] = _file(
        "# NOTES\n"
        "\n"
        "这里可以放你的终端笔记。\n"
        "示例：echo 第一行 > note.txt\n"
        "追加：echo 第二行 >> note.txt\n",
        now - 86400 * 5,
    )
    nodes[f"{home}/.secrets/ascension.key"] = _file(
        "ROGUE-CORE-SEALED-KEY::MERCURY::7F3A-91C2-0D6B\n"
        "不要把这段内容写进牌组。\n",
        old,
    )
    nodes[f"{home}/.secrets/devnote.txt"] = _file(
        "开发记录 07\n"
        "如果有人在终端里找到这里，说明他没有被 UI 宠坏。\n"
        "彩蛋文件不能被 rm 删除。\n"
        "秘密目录也不能被 rm 删除。\n"
        "这不是 bug，是 vault policy。\n",
        old,
    )
    nodes[f"{home}/.secrets/true_ending.txt"] = _file(
        "真正的结局不是通关。\n"
        "是你在主界面输入了 uname -a。\n"
        "然后继续往下走。\n",
        old,
    )
    nodes[f"{home}/dungeon/.vault"] = _file(
        "vault seal: intact\n"
        "next run: mercury\n",
        old,
    )
    return nodes
