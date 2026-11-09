from __future__ import annotations

from datetime import datetime

from game.data.locale_data import get_locale_text

from .models import ShellContext, ShellResult
from .registry import command as _command


class ExtraCommands:
    @_command("uname")
    def _cmd_uname(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        flags = "".join(args)
        all_info = "a" in flags
        pieces = []
        if all_info or "s" in flags or not flags:
            pieces.append("Linux")
        if all_info or "n" in flags:
            pieces.append("rogue-core")
        if all_info or "r" in flags:
            pieces.append("6.8.12-rogue")
        if all_info or "v" in flags:
            pieces.append("#1 SMP PREEMPT_DYNAMIC Sun Nov 08 00:00:00 UTC 2026")
        if all_info or "m" in flags:
            pieces.append("x86_64")
        if all_info or "o" in flags:
            pieces.append("GNU/Linux")
        return ShellResult(" ".join(pieces) + "\n")

    @_command("whoami")
    def _cmd_whoami(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(context.user + "\n")

    @_command("id")
    def _cmd_id(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if args and args[0] == "-u":
            return ShellResult("1000\n")
        if args and args[0] == "-g":
            return ShellResult("1000\n")
        return ShellResult(
            f"uid=1000({context.user}) gid=1000({context.user}) "
            f"groups=1000({context.user}),27(sudo)\n"
        )

    @_command("hostname")
    def _cmd_hostname(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if args and args[0] == "-f":
            return ShellResult("rogue-core.dungeon-07.local\n")
        return ShellResult("rogue-core\n")

    @_command("date")
    def _cmd_date(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        now = datetime.now().astimezone()
        if args and args[0].startswith("+"):
            return ShellResult(now.strftime(args[0][1:]) + "\n")
        return ShellResult(now.strftime("%a %b %d %H:%M:%S %Z %Y") + "\n")

    @_command("uptime")
    def _cmd_uptime(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if args and args[0] == "-p":
            return ShellResult("up 4 days, 10 hours, 54 minutes\n")
        return ShellResult(
            " 04:20:07 up 4 days, 10:54,  1 user,  load average: 0.18, 0.12, 0.09\n"
        )

    @_command("df")
    def _cmd_df(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/vda1       512G  118G  369G  25% /\n"
            "tmpfs            16G   12M   16G   1% /dev/shm\n"
            "rogue-vault     256G   74G  182G  29% /var/lib/rogue\n"
        )

    @_command("free")
    def _cmd_free(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "               total        used        free      shared  buff/cache   available\n"
            "Mem:            31Gi       7.8Gi        17Gi       212Mi       6.2Gi        23Gi\n"
            "Swap:          8.0Gi          0B       8.0Gi\n"
        )

    @_command("ps")
    def _cmd_ps(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
            "root         1  0.0  0.1  22512  9216 ?        Ss   Nov03   0:04 /sbin/init\n"
            "root       412  0.1  0.4 184320 148992 ?       Ssl  Nov03   1:22 /usr/bin/cardd --vault\n"
            "root       518  0.0  0.1  14208  7168 ?        Ss   Nov03   0:02 /usr/sbin/sshd\n"
            f"{context.user:<8} 1042  0.0  0.0  10112  5120 pts/0    Ss   04:19   0:00 -bash\n"
            f"{context.user:<8} 1098  0.0  0.0  12108  4352 pts/0    R+   04:20   0:00 ps aux\n"
        )

    @_command("top")
    def _cmd_top(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "top - 04:20:11 up 4 days, 10:54,  1 user,  load average: 0.18, 0.12, 0.09\n"
            "Tasks: 142 total,   1 running, 141 sleeping,   0 stopped,   0 zombie\n"
            "%Cpu(s):  1.2 us,  0.4 sy,  0.0 ni, 98.3 id,  0.1 wa\n"
            "MiB Mem :  31992.0 total,  17412.0 free,   7982.0 used,   6598.0 buff/cache\n"
            "\n"
            "  PID USER      PR  NI    VIRT    RES  %CPU  %MEM COMMAND\n"
            "  412 root      20   0  184320 148992   0.4   0.5 cardd\n"
            " 1042 player    20   0   10112   5120   0.0   0.0 bash\n"
        )

    @_command("env", "printenv")
    def _cmd_env(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            f"USER={context.user}\n"
            "HOME=/home/" + context.user + "\n"
            "SHELL=/bin/bash\n"
            "TERM=xterm-256color\n"
            "HOSTNAME=rogue-core\n"
            "LANG=zh_CN.UTF-8\n"
            "ROGUE_NODE=dungeon-07\n"
            "ROGUE_VAULT=sealed\n"
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
        )

    @_command("history")
    def _cmd_history(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if args and args[0] == "-c":
            context.history = []
            return ShellResult()
        lines = [f"{index:>4}  {value}" for index, value in enumerate(context.history, 1)]
        return ShellResult("\n".join(lines) + ("\n" if lines else ""))

    @_command("clear", "cls")
    def _cmd_clear(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(get_locale_text("i18n_server_shell.clear_done"), 0, True)

    @_command("git")
    def _cmd_git(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        command = args[0] if args else "status"
        if command == "status":
            return ShellResult(
                "On branch master\n"
                "Your branch is up to date with 'origin/master'.\n"
                "\n"
                "Changes not staged for commit:\n"
                "  modified:   dungeon/deck.json\n"
                "  modified:   dungeon/runs/2026-11-08.log\n"
                "\n"
                "no changes added to commit\n"
            )
        if command == "branch":
            return ShellResult("* master\n  mercury-vault\n  sealed-ending\n")
        if command == "log":
            return ShellResult(
                "7f3a91c (HEAD -> master) chore: seal ascension vault\n"
                "91c20d6 feat: add mercury coolant loop\n"
                "0d6b7a1 fix: do not delete vault files\n"
            )
        if command == "remote":
            return ShellResult(
                "origin\tgit@rogue-core:dungeon/node-07.git (fetch)\n"
                "origin\tgit@rogue-core:dungeon/node-07.git (push)\n"
            )
        if command == "diff":
            return ShellResult(
                "diff --git a/dungeon/deck.json b/dungeon/deck.json\n"
                "index 7f3a91c..91c20d6 100644\n"
                "--- a/dungeon/deck.json\n"
                "+++ b/dungeon/deck.json\n"
                "@@ -1,4 +1,4 @@\n"
                '-  "ascension": 6\n'
                '+  "ascension": 7\n'
            )
        return ShellResult(get_locale_text("i18n_server_shell.err_git_unavailable", command=command), 1)

    @_command("docker")
    def _cmd_docker(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        command = args[0] if args else "ps"
        if command == "ps":
            return ShellResult(
                "CONTAINER ID   IMAGE                    STATUS          NAMES\n"
                "7f3a91c20d6b   rogue/cardd:7.9.3        Up 4 days       cardd\n"
                "91c20d6b7a1f   rogue/vault:sealed       Up 4 days       vault\n"
            )
        if command == "images":
            return ShellResult(
                "REPOSITORY       TAG       IMAGE ID       SIZE\n"
                "rogue/cardd      7.9.3     7f3a91c20d6b   184MB\n"
                "rogue/vault      sealed    91c20d6b7a1f   96MB\n"
            )
        return ShellResult(get_locale_text("i18n_server_shell.err_docker_unavailable", command=command), 1)

    @_command("systemctl")
    def _cmd_systemctl(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        if args and args[0] == "status":
            unit = args[1] if len(args) > 1 else "rogue-core"
            return ShellResult(
                f"● {unit}.service - Rogue Core Dungeon Node\n"
                "     Loaded: loaded (/etc/systemd/system/rogue-core.service; enabled)\n"
                "     Active: active (running) since Tue 2026-11-03 17:26:04 UTC\n"
                "   Main PID: 412 (cardd)\n"
                "      Tasks: 14 (limit: 3840)\n"
                "     Memory: 148.9M\n"
                "        CPU: 1.220s\n"
            )
        return ShellResult(get_locale_text("i18n_server_shell.err_systemctl_denied"), 1)

    @_command("journalctl")
    def _cmd_journalctl(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "-- Logs begin at Tue 2026-11-03 17:26:04 UTC --\n"
            "Nov 08 04:19:02 rogue-core cardd[412]: player session attached\n"
            "Nov 08 04:19:02 rogue-core cardd[412]: deck checksum ok\n"
            "Nov 08 04:19:03 rogue-core cardd[412]: vault seal intact\n"
        )

    @_command("ip")
    def _cmd_ip(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536\n"
            "    inet 127.0.0.1/8 scope host lo\n"
            "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500\n"
            "    inet 10.7.3.12/24 brd 10.7.3.255 scope global eth0\n"
            "    inet6 fe80::7f3a:91ff:fe20:d6b/64 scope link\n"
        )

    @_command("ss", "netstat")
    def _cmd_ss(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "Netid State  Local Address:Port    Peer Address:Port\n"
            "tcp   LISTEN 127.0.0.1:8787        0.0.0.0:*\n"
            "tcp   LISTEN 0.0.0.0:22            0.0.0.0:*\n"
            "tcp   ESTAB  10.7.3.12:22         10.7.3.1:51422\n"
        )

    @_command("lscpu")
    def _cmd_lscpu(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "Architecture:            x86_64\n"
            "CPU op-mode(s):          32-bit, 64-bit\n"
            "Model name:              AMD Ryzen 9 7950X3D 16-Core Processor\n"
            "CPU(s):                  32\n"
            "Thread(s) per core:      2\n"
            "Core(s) per socket:      16\n"
            "Socket(s):               1\n"
            "CPU max MHz:             5700.0000\n"
            "L3 cache:                96 MiB\n"
        )

    @_command("lsblk")
    def _cmd_lsblk(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS\n"
            "vda    252:0    0   512G  0 disk\n"
            "└─vda1 252:1    0   512G  0 part /\n"
            "vdb    252:16   0   256G  0 disk /var/lib/rogue\n"
        )

    @_command("mount")
    def _cmd_mount(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(
            "/dev/vda1 on / type ext4 (rw,relatime,errors=remount-ro)\n"
            "tmpfs on /dev/shm type tmpfs (rw,nosuid,nodev)\n"
            "rogue-vault on /var/lib/rogue type fuse.rogue (ro,nosuid,nodev)\n"
        )

    @_command("exit")
    def _cmd_exit(self, context: ShellContext, args: list[str], stdin: str | None) -> ShellResult:
        return ShellResult(get_locale_text("i18n_server_shell.err_logout"), 1)



