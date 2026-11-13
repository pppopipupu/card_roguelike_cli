from ...data.balance_config import LOG_DEFAULT_ENTRIES, LOG_MAX_ENTRIES
from ...data.locale_data import get_locale_text

LOG_COMMANDS = {"logs", "日志", "logc", "团队日志", "队伍日志"}
LOG_SKIP_COMMANDS = LOG_COMMANDS | {
    "status",
    "r",
    "状态",
    "help",
    "帮助",
    "query",
    "查询",
    "info",
    "i",
    "projection",
    "投影",
    "pj",
    "secrets",
}
COMMAND_PREFIXES = {".rogue", "/rogue", "rogue"}


def _command_parts(command: str) -> list[str]:
    parts = str(command or "").strip().split()
    while parts and parts[0].lower() in COMMAND_PREFIXES:
        parts = parts[1:]
    return parts


def is_log_command(command: str) -> bool:
    parts = _command_parts(command)
    return bool(parts) and parts[0].lower() in LOG_COMMANDS


def parse_log_limit(parts: list[str]) -> tuple[int, str]:
    if len(parts) < 2:
        return LOG_DEFAULT_ENTRIES, ""
    try:
        value = int(parts[1])
    except (TypeError, ValueError):
        return 0, get_locale_text("i18n_logs.invalid_count", min=1, max=LOG_MAX_ENTRIES)
    if value < 1:
        return 0, get_locale_text("i18n_logs.invalid_count", min=1, max=LOG_MAX_ENTRIES)
    return min(value, LOG_MAX_ENTRIES), ""


class LogService:
    def __init__(self, save_manager):
        self.save_manager = save_manager

    def _should_record_parts(self, parts: list[str], run, stats) -> bool:
        if not parts:
            return False
        first = parts[0].lower()
        return first not in LOG_SKIP_COMMANDS

    def should_record(self, command: str, run=None, stats=None, user_id: str = "") -> bool:
        parts = _command_parts(command)
        return self._should_record_parts(parts, run, stats)

    def _load_stats(self, user_id: str):
        loader = getattr(self.save_manager, "load_stats", None)
        if not callable(loader):
            return None
        return loader(user_id)

    def _save_stats(self, user_id: str, stats) -> None:
        saver = getattr(self.save_manager, "save_stats", None)
        if callable(saver):
            saver(user_id, stats)

    def _append(self, stats, field: str, entry: dict) -> None:
        history = getattr(stats, field, [])
        if not isinstance(history, list):
            history = []
        history.append(entry)
        setattr(stats, field, history[-LOG_MAX_ENTRIES:])

    def record(self, user_id: str, command: str, result: str, kind: str = "action", run=None, actor_name: str = "") -> None:
        command = str(command or "").strip()
        parts = _command_parts(command)
        stats = self._load_stats(user_id)
        if stats is None or not self._should_record_parts(parts, run, stats):
            return
        name = actor_name or getattr(stats, "player_name", "")
        entry = {
            "kind": "battle" if kind == "battle" else "action",
            "command": command,
            "text": str(result or "").strip(),
            "player": name,
            "coop_id": getattr(run, "coop_id", "") if run is not None else "",
        }
        self._append(stats, "log_history", entry)
        party_order = list(run.human_uids()) if run is not None and hasattr(run, "human_uids") else (list(getattr(run, "party_order", []) or []) if run is not None else [])
        if run is not None and len(party_order) > 1:
            for uid in party_order:
                if uid == user_id:
                    member = stats
                else:
                    member = self._load_stats(uid)
                if member is None:
                    continue
                self._append(member, "team_log_history", entry)
                if member is not stats:
                    self._save_stats(uid, member)
        self._save_stats(user_id, stats)

    def render(self, user_id: str, limit: int, team: bool = False) -> str:
        stats = self._load_stats(user_id)
        if stats is None:
            key = "i18n_logs.empty_team" if team else "i18n_logs.empty"
            return get_locale_text(key)
        field = "team_log_history" if team else "log_history"
        history = getattr(stats, field, [])
        if not isinstance(history, list):
            history = []
        entries = [entry for entry in history if isinstance(entry, dict)]
        try:
            count = max(1, min(int(limit), LOG_MAX_ENTRIES))
        except (TypeError, ValueError):
            count = LOG_DEFAULT_ENTRIES
        selected = entries[-count:]
        if not selected:
            key = "i18n_logs.empty_team" if team else "i18n_logs.empty"
            return get_locale_text(key)
        header_key = "i18n_logs.team_header" if team else "i18n_logs.header"
        lines = [get_locale_text(header_key, count=len(selected))]
        for entry in selected:
            kind = entry.get("kind", "action")
            kind_key = "i18n_logs.kind_battle" if kind == "battle" else "i18n_logs.kind_action"
            kind_label = get_locale_text(kind_key)
            command = str(entry.get("command", ""))
            text = str(entry.get("text", "")).strip()
            if team:
                player = str(entry.get("player", "")) or get_locale_text("i18n_logs.unknown_player")
                header = get_locale_text(
                    "i18n_logs.team_entry_header",
                    kind=kind_label,
                    player=player,
                    command=command,
                )
            else:
                header = get_locale_text(
                    "i18n_logs.entry_header",
                    kind=kind_label,
                    command=command,
                )
            lines.append(header)
            if text:
                lines.append(text)
            lines.append("")
        return "\n".join(lines).rstrip()
