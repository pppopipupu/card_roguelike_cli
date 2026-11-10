import os
import json
import logging
import tempfile
from dataclasses import asdict
from typing import Optional, Tuple, Dict, List
from .state import GameRun, UserStats
from .corpse_registry import CorpseRegistry
from .save_codec import SaveCodecMixin
from .settlement import SettlementMixin
from ..data.locale_data import get_locale_text

logger = logging.getLogger(__name__)

def _atomic_write_json(path: str, data, indent: int = 2) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".rogue-", suffix=".tmp", dir=directory or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

class SaveManager(SaveCodecMixin, SettlementMixin):
    _default_data_dir = None

    def __init__(self, data_dir: str = None):
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
        self.corpses = CorpseRegistry(self.data_dir)

    def get_save_path(self, user_id: str) -> str:
        safe_id = "".join([c for c in user_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"user_{safe_id}.json")

    def get_coop_save_path(self, coop_id: str) -> str:
        safe_id = "".join([c for c in coop_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"coop_{safe_id}.json")

    def get_lobbies_path(self) -> str:
        return os.path.join(self.data_dir, "coop_lobbies.json")

    def has_personal_save(self, user_id: str) -> bool:
        return os.path.exists(self.get_save_path(user_id))

    def resolve_lock_key(self, user_id: str) -> str:
        stats = self.load_stats(user_id)
        coop_id = getattr(stats, "active_coop_id", "")
        if coop_id:
            return f"coop:{coop_id}"
        lobby_id = getattr(stats, "active_lobby_id", "")
        if lobby_id:
            return f"lobby:{lobby_id}"
        return f"user:{user_id}"

    def get_stats_path(self, user_id: str) -> str:
        safe_id = "".join([c for c in user_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"stats_{safe_id}.json")

    def load_stats(self, user_id: str) -> UserStats:
        path = self.get_stats_path(user_id)
        if not os.path.exists(path):
            return UserStats()
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            projection_feed = d.get("projection_feed", [])
            if not isinstance(projection_feed, list):
                projection_feed = []
            log_history = d.get("log_history", [])
            if not isinstance(log_history, list):
                log_history = []
            team_log_history = d.get("team_log_history", [])
            if not isinstance(team_log_history, list):
                team_log_history = []
            return UserStats(
                total_damage=d.get("total_damage", 0),
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
                locked_cards=d.get("locked_cards", []),
                purchased_pool=d.get("purchased_pool", []),
                defeated_town_npcs=d.get("defeated_town_npcs", []),
                town_inventory=d.get("town_inventory", []),
                town_flags=d.get("town_flags", {}),
                town_health_bonus=d.get("town_health_bonus", 0),
                player_name=d.get("player_name", "玩家"),
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
                active_lobby_id=d.get("active_lobby_id", ""),
                active_coop_id=d.get("active_coop_id", ""),
                projection_enabled=d.get("projection_enabled", True),
                projection_feed=projection_feed,
                log_history=log_history,
                team_log_history=team_log_history
            )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_stats_failed", user_id=user_id, error=exc))
            return UserStats()

    def save_stats(self, user_id: str, stats: UserStats) -> bool:
        path = self.get_stats_path(user_id)
        try:
            d = asdict(stats)
            _atomic_write_json(path, d)
            return True
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
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

    def get_duel_registry_path(self) -> str:
        return os.path.join(self.data_dir, "duel_registry.json")

    def get_duel_registry(self) -> dict:
        path = self.get_duel_registry_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_duel_registry_failed", error=exc))
            return {}

    def save_duel_registry(self, reg: dict) -> bool:
        path = self.get_duel_registry_path()
        try:
            _atomic_write_json(path, reg)
            return True
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_duel_registry_failed", error=exc))
            return False

    def get_duel_game_id(self, user_id: str) -> Optional[str]:
        return self.get_duel_registry().get(user_id)

    def bind_duel_game(self, user_id1: str, user_id2: str, game_id: str):
        reg = self.get_duel_registry()
        reg[user_id1] = game_id
        reg[user_id2] = game_id
        self.save_duel_registry(reg)

    def unbind_duel_game(self, game_id: str):
        reg = self.get_duel_registry()
        keys_to_del = [k for k, v in reg.items() if v == game_id]
        for k in keys_to_del:
            del reg[k]
        self.save_duel_registry(reg)

    def get_duel_deck_path(self, user_id: str) -> str:
        safe_id = "".join([c for c in user_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"duel_decks_{safe_id}.json")

    def load_duel_decks(self, user_id: str) -> dict:
        path = self.get_duel_deck_path(user_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_duel_decks_failed", user_id=user_id, error=exc))
            return {}

    def save_duel_decks(self, user_id: str, decks: dict) -> bool:
        path = self.get_duel_deck_path(user_id)
        try:
            _atomic_write_json(path, decks)
            return True
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_duel_decks_failed", user_id=user_id, error=exc))
            return False

    def load_save(self, user_id: str) -> GameRun:
        stats = self.load_stats(user_id)
        coop_id = getattr(stats, "active_coop_id", "")
        if coop_id:
            run = self.load_coop_save(user_id, coop_id)
            if run:
                return run
        path = self.get_save_path(user_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return self.from_dict(d)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_save_failed", user_id=user_id, error=exc))
            return None

    def save_save(self, user_id: str, run: GameRun) -> bool:
        if run and getattr(run, "coop_id", "") and user_id in getattr(run, "players", {}):
            return self.save_coop_save(user_id, run)
        path = self.get_save_path(user_id)
        try:
            d = self.to_dict(run)
            _atomic_write_json(path, d)
            return True
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_save_failed", user_id=user_id, error=exc))
            return False

    def delete_save(self, user_id: str) -> bool:
        stats = self.load_stats(user_id)
        if getattr(stats, "active_coop_id", ""):
            return False
        path = self.get_save_path(user_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                logger.warning(get_locale_text("i18n_models.manager.delete_save_failed", user_id=user_id, error=exc))
                return False
        return False

    def load_coop_save(self, user_id: str, coop_id: str) -> GameRun:
        path = self.get_coop_save_path(coop_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            run = self.from_dict(d)
            if run and user_id in run.players:
                run.player = run.players[user_id]
                run.user_id = user_id
                from .coop_view import apply_view, scope_view
                apply_view(run, user_id)
                scope_view(run, user_id)
            return run
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_coop_save_failed", user_id=user_id, coop_id=coop_id, error=exc))
            return None

    def save_coop_save(self, user_id: str, run: GameRun) -> bool:
        run.players[user_id] = run.player
        run.user_id = user_id
        from .coop_view import persist_view
        persist_view(run, user_id)
        path = self.get_coop_save_path(run.coop_id)
        try:
            d = self.to_dict(run)
            _atomic_write_json(path, d)
            return True
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_coop_save_failed", user_id=user_id, coop_id=run.coop_id, error=exc))
            return False

    def delete_coop_save(self, coop_id: str) -> bool:
        path = self.get_coop_save_path(coop_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                logger.warning(get_locale_text("i18n_models.manager.delete_coop_save_failed", coop_id=coop_id, error=exc))
                return False
        return False

    def load_lobbies(self) -> dict:
        path = self.get_lobbies_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_lobbies_failed", error=exc))
            return {}

    def save_lobbies(self, lobbies: dict) -> bool:
        try:
            _atomic_write_json(self.get_lobbies_path(), lobbies)
            return True
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_lobbies_failed", error=exc))
            return False

    def get_lobby(self, lobby_id: str) -> dict:
        lobbies = self.load_lobbies()
        return lobbies.get(lobby_id)

    def save_lobby(self, lobby: dict) -> bool:
        lobbies = self.load_lobbies()
        lobbies[lobby["lobby_id"]] = lobby
        return self.save_lobbies(lobbies)

    def delete_lobby(self, lobby_id: str) -> bool:
        lobbies = self.load_lobbies()
        if lobby_id in lobbies:
            del lobbies[lobby_id]
            return self.save_lobbies(lobbies)
        return False

    def list_player_profiles(self) -> List[dict]:
        profiles = []
        if not os.path.isdir(self.data_dir):
            return profiles
        for name in os.listdir(self.data_dir):
            if not name.startswith("stats_") or not name.endswith(".json"):
                continue
            path = os.path.join(self.data_dir, name)
            uid = name[len("stats_"):-len(".json")]
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                profiles.append({
                    "user_id": uid,
                    "name": data.get("player_name", "玩家"),
                    "im_account": data.get("im_account", ""),
                    "selected_class": data.get("selected_class", "法师"),
                    "selected_subclass": data.get("selected_subclass", ""),
                    "gp": data.get("gp", 0),
                    "active_coop_id": data.get("active_coop_id", ""),
                    "active_lobby_id": data.get("active_lobby_id", ""),
                    "in_town": data.get("in_town", False),
                    "mtime": os.path.getmtime(path)
                })
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                logger.warning(get_locale_text("i18n_models.manager.read_profile_failed", user_id=uid, error=exc))
                continue
        return profiles

    def load_duel_save(self, user_id: str) -> GameRun:
        game_id = self.get_duel_game_id(user_id)
        if not game_id:
            return None
        path = os.path.join(self.data_dir, f"duel_{game_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            run = self.from_dict(d)
            if run:
                p2_id = run.node_data.get("player2_id")
                if p2_id == user_id:
                    run.player, run.player2 = run.player2, run.player
                    run.user_id = user_id
            return run
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_duel_save_failed", user_id=user_id, error=exc))
            return None

    def save_duel_save(self, user_id: str, run: GameRun) -> bool:
        game_id = self.get_duel_game_id(user_id)
        if not game_id:
            return False
        path = os.path.join(self.data_dir, f"duel_{game_id}.json")
        p2_id = run.node_data.get("player2_id")
        if p2_id == user_id:
            run.player, run.player2 = run.player2, run.player
            run.user_id = run.node_data.get("player1_id", run.user_id)
        try:
            d = self.to_dict(run)
            if p2_id == user_id:
                run.player, run.player2 = run.player2, run.player
                run.user_id = user_id
            _atomic_write_json(path, d)
            return True
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_duel_save_failed", user_id=user_id, error=exc))
            if p2_id == user_id:
                run.player, run.player2 = run.player2, run.player
                run.user_id = user_id
            return False

    def delete_duel_save(self, user_id: str) -> bool:
        game_id = self.get_duel_game_id(user_id)
        if not game_id:
            return False
        path = os.path.join(self.data_dir, f"duel_{game_id}.json")
        self.unbind_duel_game(game_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                logger.warning(get_locale_text("i18n_models.manager.delete_duel_save_failed", user_id=user_id, error=exc))
                return False
        return False

    def get_admin_config_path(self) -> str:
        return os.path.join(self.data_dir, "admin_config.json")

    def load_admin_config(self) -> dict:
        path = self.get_admin_config_path()
        if not os.path.exists(path):
            return {"final_boss": "random"}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.read_admin_config_failed", error=exc))
            return {"final_boss": "random"}

    def save_admin_config(self, cfg: dict) -> bool:
        path = self.get_admin_config_path()
        try:
            _atomic_write_json(path, cfg)
            return True
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(get_locale_text("i18n_models.manager.save_admin_config_failed", error=exc))
            return False
