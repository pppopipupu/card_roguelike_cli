from contextlib import nullcontext
import os
import logging
import math
import sqlite3
import uuid
from typing import Optional, Dict, List
from .state import GameRun, UserStats, PlayerState, ensure_card_state
from .records import Lobby, PlayerProfile
from .corpse_registry import CorpseRegistry
from .open_world_ghost_registry import OpenWorldGhostRegistry
from .pvp_registry import PvpRegistry
from .trade_registry import TradeRegistry
from .save_codec import SaveCodecMixin
from .settlement import SettlementMixin
from .sqlite_store import SqliteStore
from ..json_codec import load, loads
from ..core.social.player_names import fallback_player_name, unique_handle
from ..data.text.locale_data import get_locale_text
from ..data.progression.starting_deck_config import LOCK_SLOT_LIMIT

logger = logging.getLogger(__name__)

def _parse_total_damage(value) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        if not math.isfinite(value):
            return 0
        parsed = int(value)
    elif isinstance(value, str):
        try:
            parsed = int(value.strip() or "0")
        except ValueError:
            return 0
    else:
        return 0
    return parsed if parsed > 0 else 0

class SaveManager(SaveCodecMixin, SettlementMixin):
    _default_data_dir = None

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is not None:
            SaveManager._default_data_dir = data_dir
            self.data_dir = data_dir
        else:
            if SaveManager._default_data_dir is not None:
                self.data_dir = SaveManager._default_data_dir
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                self.data_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "data")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        self.store = SqliteStore.for_path(os.path.join(self.data_dir, "rogue.db"))
        self.corpses = CorpseRegistry(self.data_dir, store=self.store)
        self.open_world_ghosts = OpenWorldGhostRegistry(self.data_dir, store=self.store)
        self.pvp = PvpRegistry(self.data_dir, store=self.store)
        self.trades = TradeRegistry(self.data_dir, store=self.store)

    def batch(self):
        store = getattr(self, "store", None)
        if store is None:
            return nullcontext()
        return store.batch()

    def close(self) -> None:
        store = getattr(self, "store", None)
        if store is not None:
            store.close()

    def _load_json_or_legacy(self, table: str, key: str, legacy_path: str):
        data = self.store.get_json(table, key)
        if data is not None:
            return data
        if not os.path.exists(legacy_path):
            return None
        with open(legacy_path, "r", encoding="utf-8") as f:
            data = load(f)
        if data is None:
            return None
        self.store.put_json(table, key, data, updated_at=os.path.getmtime(legacy_path))
        return data

    def _remove_legacy_file(self, path: str) -> bool:
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def _sync_legacy_stats_dir(self) -> None:
        if not os.path.isdir(self.data_dir):
            return
        for name in os.listdir(self.data_dir):
            if not name.startswith("stats_") or not name.endswith(".json"):
                continue
            uid = name[len("stats_"):-len(".json")]
            if self.store.exists("user_stats", uid):
                continue
            path = os.path.join(self.data_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = load(f)
                if not isinstance(data, dict):
                    continue
                self.store.put_json("user_stats", uid, data, updated_at=os.path.getmtime(path))
            except (OSError, ValueError, sqlite3.Error) as exc:
                logger.warning(get_locale_text("i18n_models.manager.read_profile_failed", user_id=uid, error=exc))

    def get_save_path(self, user_id: str) -> str:
        safe_id = "".join([c for c in user_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"user_{safe_id}.json")

    def get_run_save_path(self, run_id: str) -> str:
        safe_id = "".join([c for c in run_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"run_{safe_id}.json")

    def get_lobbies_path(self) -> str:
        return os.path.join(self.data_dir, "party_lobbies.json")

    def has_active_save(self, user_id: str) -> bool:
        stats = self.load_stats(user_id)
        run_id = getattr(stats, "active_run_id", "")
        if run_id and (self.store.exists("run_saves", run_id) or os.path.exists(self.get_run_save_path(run_id))):
            return True
        return os.path.exists(self.get_save_path(user_id))

    def resolve_lock_key(self, user_id: str) -> str:
        stats = self.load_stats(user_id)
        run_id = getattr(stats, "active_run_id", "")
        if run_id:
            return f"run:{run_id}"
        lobby_id = getattr(stats, "active_lobby_id", "")
        if lobby_id:
            return f"lobby:{lobby_id}"
        return f"user:{user_id}"

    def get_stats_path(self, user_id: str) -> str:
        safe_id = "".join([c for c in user_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"stats_{safe_id}.json")

    def load_stats(self, user_id: str) -> UserStats:
        path = self.get_stats_path(user_id)
        try:
            d = self._load_json_or_legacy("user_stats", user_id, path)
            if d is None:
                return UserStats()
            if not isinstance(d, dict):
                raise TypeError(type(d).__name__)
            locked_cards = d.get("locked_cards", [])
            if not isinstance(locked_cards, list):
                locked_cards = []
            locked_cards = locked_cards[:LOCK_SLOT_LIMIT]
            projection_feed = d.get("projection_feed", [])
            if not isinstance(projection_feed, list):
                projection_feed = []
            log_history = d.get("log_history", [])
            if not isinstance(log_history, list):
                log_history = []
            team_log_history = d.get("team_log_history", [])
            if not isinstance(team_log_history, list):
                team_log_history = []
            world_mailbox = d.get("world_mailbox", [])
            if not isinstance(world_mailbox, list):
                world_mailbox = []
            world_mailbox = [item for item in world_mailbox if isinstance(item, dict)][-50:]
            pending_logs = d.get("pending_logs", [])
            if not isinstance(pending_logs, list):
                pending_logs = []
            pending_logs = [str(item) for item in pending_logs if str(item or "").strip()][-50:]
            unlocked_achievements = d.get("unlocked_achievements", [])
            if not isinstance(unlocked_achievements, list):
                unlocked_achievements = []
            achievement_stats = d.get("achievement_stats", {})
            if not isinstance(achievement_stats, dict):
                achievement_stats = {}
            return UserStats(
                total_damage=_parse_total_damage(d.get("total_damage", 0)),
                total_kills=d.get("total_kills", 0),
                total_stages=d.get("total_stages", 0),
                rogue_mode=d.get("rogue_mode", False),
                duel_mode=d.get("duel_mode", False),
                gp=d.get("gp", 0),
                unlocked_subclasses=d.get("unlocked_subclasses", []),
                selected_class=d.get("selected_class", "法师"),
                selected_subclass=d.get("selected_subclass", ""),
                killed_icerainboww=d.get("killed_icerainboww", False),
                unlocked_gatekey=d.get("unlocked_gatekey", False),
                yog_sothoth_kill_count=d.get("yog_sothoth_kill_count", 0),
                yog_sothoth_challenge_count=d.get("yog_sothoth_challenge_count", 0),
                reader_active=d.get("reader_active", False),
                reader_page=d.get("reader_page", 1),
                reader_title=d.get("reader_title", ""),
                reader_items=d.get("reader_items", []),
                reader_mode=d.get("reader_mode", "rogue"),
                in_town=d.get("in_town", False),
                town_pos=d.get("town_pos", "square"),
                guaranteed_card=d.get("guaranteed_card", None),
                locked_cards=locked_cards,
                purchased_pool=d.get("purchased_pool", []),
                defeated_town_npcs=d.get("defeated_town_npcs", []),
                town_inventory=list(d.get("town_inventory", []) or []) + [f"potion:{pid}" for pid in (d.get("town_potions", []) or [])],
                town_flags=d.get("town_flags", {}),
                town_health_bonus=d.get("town_health_bonus", 0),
                player_name=d.get("player_name", "玩家"),
                player_handle=d.get("player_handle", ""),
                name_customized=d.get("name_customized", False),
                im_account=d.get("im_account", ""),
                unlocked_new_cards=d.get("unlocked_new_cards", []),
                last_checkin_date=d.get("last_checkin_date", ""),
                daily_blessing=d.get("daily_blessing", ""),
                checkin_pending_stamp=d.get("checkin_pending_stamp", False),
                collection_stamps=d.get("collection_stamps", {}),
                friends=d.get("friends", []),
                friend_requests_in=d.get("friend_requests_in", []),
                friend_requests_out=d.get("friend_requests_out", []),
                world_mailbox=world_mailbox,
                active_lobby_id=d.get("active_lobby_id", ""),
                active_run_id=d.get("active_run_id") or d.get("active_coop_id") or "",
                projection_enabled=d.get("projection_enabled", True),
                projection_feed=projection_feed,
                log_history=log_history,
                team_log_history=team_log_history,
                pending_logs=pending_logs,
                unlocked_achievements=unlocked_achievements,
                achievement_all_view=bool(d.get("achievement_all_view", False)),
                achievement_stats=achievement_stats,
                hired_mercenaries=list(d.get("hired_mercenaries", [])),
                open_world_deck=[ensure_card_state(c) for c in (d.get("open_world_deck", []) or [])],
                open_world_relics=[str(r) for r in (d.get("open_world_relics", []) or []) if r],
                open_world_relic_counters={
                    str(k): int(v)
                    for k, v in (d.get("open_world_relic_counters", {}) or {}).items()
                } if isinstance(d.get("open_world_relic_counters"), dict) else {},
                open_world_bag=[str(item) for item in (d.get("open_world_bag", []) or []) if item],
                open_world_hp=int(d.get("open_world_hp", 0) or 0),
                open_world_max_hp=int(d.get("open_world_max_hp", 0) or 0),
                open_world_sp=int(d.get("open_world_sp", -1) if d.get("open_world_sp") is not None else -1),
                open_world_gold=int(d.get("open_world_gold", -1) if d.get("open_world_gold") is not None else -1),
                town_chest=[str(item) for item in (d.get("town_chest", []) or []) if item],
                town_chest_relics=[str(r) for r in (d.get("town_chest_relics", []) or []) if r],
                town_chest_relic_counters={
                    str(k): int(v)
                    for k, v in (d.get("town_chest_relic_counters", {}) or {}).items()
                } if isinstance(d.get("town_chest_relic_counters"), dict) else {},
                pvp_enabled=bool(d.get("pvp_enabled", True)),
                encountered_entities=[str(x) for x in (d.get("encountered_entities", []) or []) if x],
                tutorial_done=bool(d["tutorial_done"]) if "tutorial_done" in d else True,
            )
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_stats_failed", user_id=user_id, error=exc))
            return UserStats()

    def save_stats(self, user_id: str, stats: UserStats) -> bool:
        try:
            if not getattr(stats, "active_run_id", ""):
                existing = self.store.get_json("user_stats", user_id)
                if isinstance(existing, dict):
                    prev_run_id = existing.get("active_run_id") or existing.get("active_coop_id") or ""
                    if prev_run_id and self.store.exists("run_saves", prev_run_id):
                        stats.active_run_id = prev_run_id
            d = dict(stats.__dict__)
            d["total_damage"] = str(int(stats.total_damage))
            self.store.put_json("user_stats", user_id, d)
            return True
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_stats_failed", user_id=user_id, error=exc))
            return False

    def delete_stats(self, user_id: str) -> bool:
        try:
            deleted = self.store.delete("user_stats", user_id)
            if self._remove_legacy_file(self.get_stats_path(user_id)):
                deleted = True
            return deleted
        except (OSError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_stats_failed", user_id=user_id, error=exc))
            return False

    def record_damage(self, user_id: str, amount: int):
        if not user_id or amount <= 0:
            return
        stats = self.load_stats(user_id)
        stats.total_damage += amount
        self.save_stats(user_id, stats)

    def record_kill(self, user_id: str):
        if not user_id:
            return
        stats = self.load_stats(user_id)
        stats.total_kills += 1
        self.save_stats(user_id, stats)

    def record_stage_passed(self, user_id: str):
        if not user_id:
            return
        stats = self.load_stats(user_id)
        stats.total_stages += 1
        self.save_stats(user_id, stats)

    def load_save(self, user_id: str) -> Optional[GameRun]:
        stats = self.load_stats(user_id)
        run_id = getattr(stats, "active_run_id", "")
        try:
            d = None
            if run_id:
                d = self._load_json_or_legacy("run_saves", run_id, self.get_run_save_path(run_id))
            if d is None:
                legacy_path = self.get_save_path(user_id)
                if os.path.exists(legacy_path):
                    with open(legacy_path, "r", encoding="utf-8") as f:
                        legacy_data = load(f)
                    if isinstance(legacy_data, dict):
                        run_id = str(legacy_data.get("run_id") or legacy_data.get("coop_id") or uuid.uuid4().hex[:8])
                        legacy_data["run_id"] = run_id
                        self.store.put_json("run_saves", run_id, legacy_data, updated_at=os.path.getmtime(legacy_path))
                        stats.active_run_id = run_id
                        self.save_stats(user_id, stats)
                        d = legacy_data
            if d is None:
                return None
            run = self.from_dict(d)
            if run:
                if not run.run_id and run_id:
                    run.run_id = run_id
                if user_id in run.players:
                    run.player = run.players[user_id]
                    run.user_id = user_id
                from ..core.party.session import SessionContextScoper
                SessionContextScoper.bind_to_run(run, user_id)
                from .coop_view import apply_view, scope_view
                apply_view(run, user_id)
                scope_view(run, user_id)
                from ..data.world.pvp_config import PVP_MATCH_KEY
                if run.node_data.get(PVP_MATCH_KEY):
                    from ..core.battle.pvp_service import PvpService
                    PvpService.bind_run_from_match(self, run, user_id)
            return run
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_save_failed", user_id=user_id, error=exc))
            return None

    def _sync_open_world_from_run(self, run: Optional[GameRun]) -> None:
        if run is None:
            return
        from ..core.world.open_world.loadout_service import OpenWorldLoadoutService
        OpenWorldLoadoutService.sync_run_to_stats(self, run)

    def save_save(self, user_id: str, run: GameRun) -> bool:
        if not user_id:
            return False
        save_uid = user_id
        prev_player: Optional[PlayerState] = None
        prev_user_id: Optional[str] = None
        swapped_for_save = False
        if run:
            players = getattr(run, "players", {}) or {}
            target_p = players.get(user_id)
            if target_p is not None and getattr(target_p, "is_mercenary", False):
                owner_uid = getattr(target_p, "mercenary_owner", "")
                if owner_uid:
                    save_uid = owner_uid
            if save_uid in players:
                if run.player is players[save_uid]:
                    players[save_uid] = run.player
                    run.user_id = save_uid
                else:
                    prev_player = run.player
                    prev_user_id = run.user_id
                    run.player = players[save_uid]
                    run.user_id = save_uid
                    swapped_for_save = True
        try:
            if run:
                if not getattr(run, "run_id", ""):
                    run.run_id = uuid.uuid4().hex[:8]
                from .coop_view import persist_view
                from ..core.party.session import SessionContextScoper
                SessionContextScoper.sync_from_run(run, save_uid)
                persist_view(run, save_uid)
                self._sync_open_world_from_run(run)
                from ..data.world.pvp_config import PVP_MATCH_KEY
                if run.node_data.get(PVP_MATCH_KEY):
                    from ..core.battle.pvp_service import PvpService
                    PvpService.sync_match_from_run(self, run, save_uid)
                d = self.to_dict(run)
                self.store.put_json("run_saves", run.run_id, d)
                human_uids = list(run.all_human_uids())
                if save_uid not in human_uids:
                    human_uids.append(save_uid)
                for uid in human_uids:
                    st = self.load_stats(uid)
                    if getattr(st, "active_run_id", "") != run.run_id:
                        st.active_run_id = run.run_id
                        self.save_stats(uid, st)
            return True
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_save_failed", user_id=save_uid, error=exc))
            return False
        finally:
            if swapped_for_save and run:
                if prev_player is not None and prev_user_id is not None:
                    run.player = prev_player
                    run.user_id = prev_user_id

    def delete_save(self, user_id: str) -> bool:
        stats = self.load_stats(user_id)
        run_id = getattr(stats, "active_run_id", "")
        try:
            deleted = False
            member_uids = [user_id]
            if run_id:
                raw = self.store.get_json("run_saves", run_id)
                if isinstance(raw, dict):
                    players = raw.get("players") or {}
                    if isinstance(players, dict):
                        for uid, pdata in players.items():
                            if isinstance(pdata, dict) and pdata.get("is_mercenary"):
                                continue
                            if uid not in member_uids:
                                member_uids.append(uid)
                if self.store.delete("run_saves", run_id):
                    deleted = True
                if self._remove_legacy_file(self.get_run_save_path(run_id)):
                    deleted = True
                for uid in member_uids:
                    st = self.load_stats(uid)
                    if getattr(st, "active_run_id", "") == run_id:
                        st.active_run_id = ""
                        self.save_stats(uid, st)
            if self._remove_legacy_file(self.get_save_path(user_id)):
                deleted = True
            return deleted
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.delete_save_failed", user_id=user_id, error=exc))
            return False

    def load_lobbies(self) -> Dict[str, Lobby]:
        path = self.get_lobbies_path()
        try:
            data = self._load_json_or_legacy("kv_store", "coop_lobbies", path)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_lobbies_failed", error=exc))
            return {}

    def save_lobbies(self, lobbies: Dict[str, Lobby]) -> bool:
        try:
            self.store.put_json("kv_store", "coop_lobbies", lobbies)
            return True
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_lobbies_failed", error=exc))
            return False

    def get_lobby(self, lobby_id: str) -> Optional[Lobby]:
        lobbies = self.load_lobbies()
        return lobbies.get(lobby_id)

    def save_lobby(self, lobby: Lobby) -> bool:
        lobbies = self.load_lobbies()
        lobbies[lobby["lobby_id"]] = lobby
        return self.save_lobbies(lobbies)

    def delete_lobby(self, lobby_id: str) -> bool:
        lobbies = self.load_lobbies()
        if lobby_id in lobbies:
            del lobbies[lobby_id]
            return self.save_lobbies(lobbies)
        return False

    def ensure_player_handles(self) -> None:
        self._sync_legacy_stats_dir()
        entries = []
        for uid, blob, updated_at in self.store.list_rows("user_stats"):
            try:
                data = loads(blob)
            except (ValueError, TypeError) as exc:
                logger.warning(get_locale_text("i18n_models.manager.read_profile_failed", user_id=uid, error=exc))
                continue
            if not isinstance(data, dict):
                continue
            entries.append((updated_at, uid, data))
        entries.sort(key=lambda item: (item[0], item[1]))
        taken = set()
        with self.batch():
            for updated_at, uid, data in entries:
                base = fallback_player_name(
                    data.get("player_handle") or data.get("player_name") or ""
                )
                handle = unique_handle(str(base), taken)
                taken.add(handle)
                if data.get("player_handle") == handle and data.get("player_name") == handle:
                    continue
                data["player_handle"] = handle
                data["player_name"] = handle
                try:
                    self.store.put_json("user_stats", uid, data, updated_at=updated_at)
                except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
                    logger.warning(get_locale_text("i18n_models.manager.save_stats_failed", user_id=uid, error=exc))

    def list_player_profiles(self) -> List[PlayerProfile]:
        self._sync_legacy_stats_dir()
        profiles: List[PlayerProfile] = []
        for uid, blob, updated_at in self.store.list_rows("user_stats"):
            try:
                data = loads(blob)
                if not isinstance(data, dict):
                    continue
                profiles.append(PlayerProfile(
                    user_id=uid,
                    name=data.get("player_name", "玩家"),
                    player_handle=data.get("player_handle", ""),
                    im_account=data.get("im_account", ""),
                    selected_class=data.get("selected_class", "法师"),
                    selected_subclass=data.get("selected_subclass", ""),
                    gp=data.get("gp", 0),
                    active_run_id=data.get("active_run_id") or data.get("active_coop_id") or "",
                    active_lobby_id=data.get("active_lobby_id", ""),
                    in_town=data.get("in_town", False),
                    mtime=updated_at,
                ))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                logger.warning(get_locale_text("i18n_models.manager.read_profile_failed", user_id=uid, error=exc))
                continue
        return profiles

    def get_admin_config_path(self) -> str:
        return os.path.join(self.data_dir, "admin_config.json")

    def load_admin_config(self) -> dict:
        path = self.get_admin_config_path()
        try:
            data = self._load_json_or_legacy("kv_store", "admin_config", path)
            return data if isinstance(data, dict) else {"final_boss": "random"}
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_admin_config_failed", error=exc))
            return {"final_boss": "random"}

    def save_admin_config(self, cfg: dict) -> bool:
        try:
            self.store.put_json("kv_store", "admin_config", cfg)
            return True
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_admin_config_failed", error=exc))
            return False
