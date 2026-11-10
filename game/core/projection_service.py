from ..data.balance_config import PROJECTION_MAX_ENTRIES
from ..data.locale_data import get_locale_text
from .log_service import LOG_COMMANDS

PROJECTION_COMMANDS = {"projection", "投影", "pj"}
PROJECTION_SKIP_COMMANDS = PROJECTION_COMMANDS | LOG_COMMANDS | {"secrets"}
COMMAND_PREFIXES = {".rogue", "/rogue", "rogue"}


def _command_parts(command: str) -> list[str]:
    parts = str(command or "").strip().split()
    while parts and parts[0].lower() in COMMAND_PREFIXES:
        parts = parts[1:]
    return parts


def is_projection_command(command: str) -> bool:
    parts = _command_parts(command)
    return bool(parts) and parts[0].lower() in PROJECTION_COMMANDS


class ProjectionService:
    def __init__(self, save_manager):
        self.save_manager = save_manager

    def should_publish(self, command: str) -> bool:
        parts = _command_parts(command)
        return bool(parts) and parts[0].lower() not in PROJECTION_SKIP_COMMANDS

    def publish(self, actor_id: str, command: str, result: str, enabled: bool = True) -> None:
        command = str(command or "").strip()
        result = str(result or "").strip()
        if not enabled or not command or not result:
            return
        if not self.should_publish(command):
            return
        run = self.save_manager.load_save(actor_id)
        if run is None or not getattr(run, "coop_id", ""):
            return
        if actor_id not in getattr(run, "party_order", []):
            return
        actor = run.players.get(actor_id) or run.player
        if actor is None:
            return
        text = get_locale_text(
            "i18n_projection.message",
            player=actor.name,
            command=command,
            result=result,
        )
        for uid in run.party_order:
            if uid == actor_id or uid not in run.players:
                continue
            stats = self.save_manager.load_stats(uid)
            if not getattr(stats, "projection_enabled", True):
                continue
            if getattr(stats, "active_coop_id", "") != run.coop_id:
                continue
            feed = stats.projection_feed if isinstance(stats.projection_feed, list) else []
            feed.append({
                "coop_id": run.coop_id,
                "player": actor.name,
                "command": command,
                "result": result,
                "text": text,
            })
            stats.projection_feed = feed[-PROJECTION_MAX_ENTRIES:]
            self.save_manager.save_stats(uid, stats)

    def consume(self, user_id: str) -> list:
        stats = self.save_manager.load_stats(user_id)
        feed = stats.projection_feed if isinstance(stats.projection_feed, list) else []
        if not feed:
            return []
        stats.projection_feed = []
        self.save_manager.save_stats(user_id, stats)
        return feed
