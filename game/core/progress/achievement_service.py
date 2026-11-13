from typing import Any, Dict, List, Optional, Tuple

from ...data.achievement_data import (
    ACHIEVEMENT_ALL_VIEW_PRICE,
    ACHIEVEMENT_MYSTERY_ITEM_ID,
    ACHIEVEMENT_ORDER,
    ACHIEVEMENT_RARITY_ORDER,
    ACHIEVEMENT_SUBCLASS_IDS,
    ACHIEVEMENT_TOWN_GUARD_NPC,
    ACHIEVEMENT_TOWN_HIDDEN_BOSS_NPC,
    ACHIEVEMENTS_CONFIG,
    HIDDEN_ACHIEVEMENT_RARITIES,
)
from ...data.locale_data import get_locale_text

_PENDING_NOTICES: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}


def _stat_int(stats, key: str, default: int = 0) -> int:
    ach_stats = getattr(stats, "achievement_stats", None)
    if not isinstance(ach_stats, dict):
        return default
    try:
        return int(ach_stats.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _check_first_step(stats) -> bool:
    return int(getattr(stats, "total_stages", 0) or 0) >= 10


def _check_battle_rookie(stats) -> bool:
    return int(getattr(stats, "total_kills", 0) or 0) >= 30


def _check_damage_apprentice(stats) -> bool:
    return int(getattr(stats, "total_damage", 0) or 0) >= 2000


def _check_life_merchant_visit(stats) -> bool:
    return _stat_int(stats, "life_merchant_visits") >= 1


def _check_first_checkin(stats) -> bool:
    if getattr(stats, "last_checkin_date", ""):
        return True
    stamps = getattr(stats, "collection_stamps", None) or {}
    return sum(int(v or 0) for v in stamps.values()) >= 1


def _check_town_challenger(stats) -> bool:
    return len(getattr(stats, "defeated_town_npcs", None) or []) >= 1


def _check_first_subclass(stats) -> bool:
    unlocked = getattr(stats, "unlocked_subclasses", None) or []
    return any(sub in unlocked for sub in ACHIEVEMENT_SUBCLASS_IDS)


def _check_first_act_clear(stats) -> bool:
    return _stat_int(stats, "act1_boss_kills") >= 1


def _check_slayer_master(stats) -> bool:
    return int(getattr(stats, "total_kills", 0) or 0) >= 200


def _check_damage_master(stats) -> bool:
    return int(getattr(stats, "total_damage", 0) or 0) >= 25000


def _check_stage_explorer(stats) -> bool:
    return int(getattr(stats, "total_stages", 0) or 0) >= 100


def _check_gatekey_holder(stats) -> bool:
    return bool(getattr(stats, "unlocked_gatekey", False))


def _check_act2_victory(stats) -> bool:
    return (
        _stat_int(stats, "wins") >= 1
        or bool(getattr(stats, "killed_icerainboww", False))
        or int(getattr(stats, "yog_sothoth_kill_count", 0) or 0) > 0
    )


def _check_life_merchant_patron(stats) -> bool:
    return _stat_int(stats, "life_merchant_purchases") >= 5


def _check_collection_complete(stats) -> bool:
    return len(getattr(stats, "unlocked_new_cards", None) or []) >= 1


def _check_boss_icerainboww(stats) -> bool:
    return bool(getattr(stats, "killed_icerainboww", False))


def _check_face_yog_sothoth(stats) -> bool:
    return int(getattr(stats, "yog_sothoth_challenge_count", 0) or 0) > 0


def _check_boss_avergomon(stats) -> bool:
    return _stat_int(stats, "avergomon_kills") >= 1


def _check_life_limit_one(stats) -> bool:
    return _stat_int(stats, "min_max_hp_reached") == 1


def _check_tau_conductor(stats) -> bool:
    return _stat_int(stats, "tau_conducts") >= 1


def _check_town_guard_defeated(stats) -> bool:
    return ACHIEVEMENT_TOWN_GUARD_NPC in (getattr(stats, "defeated_town_npcs", None) or [])


def _check_boss_yog_sothoth(stats) -> bool:
    return int(getattr(stats, "yog_sothoth_kill_count", 0) or 0) > 0


def _check_town_pppopipupu(stats) -> bool:
    return ACHIEVEMENT_TOWN_HIDDEN_BOSS_NPC in (getattr(stats, "defeated_town_npcs", None) or [])


def _check_mystery_collector(stats) -> bool:
    return ACHIEVEMENT_MYSTERY_ITEM_ID in (getattr(stats, "unlocked_subclasses", None) or [])


def _check_one_hp_boss_slayer(stats) -> bool:
    return _stat_int(stats, "one_hp_boss_kills") >= 1


def _check_shou_hui_karma(stats) -> bool:
    return _stat_int(stats, "shou_hui_kills") >= 1


def _check_fusion_overclock(stats) -> bool:
    return _stat_int(stats, "fusion_overclocks") >= 1


ACHIEVEMENT_EVALUATORS = {
    "first_step": _check_first_step,
    "battle_rookie": _check_battle_rookie,
    "damage_apprentice": _check_damage_apprentice,
    "life_merchant_first_visit": _check_life_merchant_visit,
    "first_checkin": _check_first_checkin,
    "town_challenger": _check_town_challenger,
    "first_subclass": _check_first_subclass,
    "first_act_clear": _check_first_act_clear,
    "slayer_master": _check_slayer_master,
    "damage_master": _check_damage_master,
    "stage_explorer": _check_stage_explorer,
    "gatekey_holder": _check_gatekey_holder,
    "act2_victory": _check_act2_victory,
    "life_merchant_patron": _check_life_merchant_patron,
    "collection_complete": _check_collection_complete,
    "boss_icerainboww": _check_boss_icerainboww,
    "face_yog_sothoth": _check_face_yog_sothoth,
    "boss_avergomon": _check_boss_avergomon,
    "life_limit_one": _check_life_limit_one,
    "tau_conductor": _check_tau_conductor,
    "town_guard_defeated": _check_town_guard_defeated,
    "boss_yog_sothoth": _check_boss_yog_sothoth,
    "town_pppopipupu": _check_town_pppopipupu,
    "mystery_collector": _check_mystery_collector,
    "one_hp_boss_slayer": _check_one_hp_boss_slayer,
    "shou_hui_karma": _check_shou_hui_karma,
    "fusion_overclock": _check_fusion_overclock,
}


class AchievementService:
    def __init__(self, save_manager):
        self.save_manager = save_manager

    def _queue_key(self, user_id: str) -> Tuple[str, str]:
        data_dir = str(getattr(self.save_manager, "data_dir", id(self.save_manager)))
        return (data_dir, str(user_id or ""))

    def _can_persist_achievements(self, stats) -> bool:
        return (
            stats is not None
            and hasattr(stats, "unlocked_achievements")
            and isinstance(getattr(stats, "unlocked_achievements", None), list)
        )

    def _rarity_label(self, rarity: str) -> str:
        return get_locale_text(f"i18n_achievement.rarity_{rarity}")

    def format_notice(self, entry: Dict[str, Any]) -> str:
        return get_locale_text(
            "i18n_achievement.unlock_notice",
            rarity=self._rarity_label(entry["rarity"]),
            name=entry["name"],
            desc=entry["desc"],
            gp=entry["gp_reward"],
        )

    def format_notices(self, entries: List[Dict[str, Any]]) -> str:
        return "\n".join(self.format_notice(entry) for entry in entries)

    def _push_notice(self, user_id: str, entry: Dict[str, Any], run=None, battle_engine=None) -> None:
        if battle_engine is not None and run is not None and getattr(run, "node_type", "") == "battle":
            battle_engine._log_event(run, self.format_notice(entry))
            return
        key = self._queue_key(user_id)
        _PENDING_NOTICES.setdefault(key, []).append(entry)

    def pop_pending_notices(self, user_id: str) -> List[Dict[str, Any]]:
        if not user_id:
            return []
        return _PENDING_NOTICES.pop(self._queue_key(user_id), [])

    def _grant_unlocked(self, user_id: str, stats, achievement_id: str, run=None, battle_engine=None) -> Optional[Dict[str, Any]]:
        if achievement_id not in ACHIEVEMENTS_CONFIG:
            return None
        unlocked = getattr(stats, "unlocked_achievements", None)
        if not isinstance(unlocked, list):
            return None
        if achievement_id in unlocked:
            return None
        cfg = ACHIEVEMENTS_CONFIG[achievement_id]
        unlocked.append(achievement_id)
        gp_reward = int(cfg.get("gp_reward", 0) or 0)
        stats.gp = int(getattr(stats, "gp", 0) or 0) + gp_reward
        entry = {
            "id": achievement_id,
            "name": cfg["name"],
            "rarity": cfg["rarity"],
            "desc": cfg["desc"],
            "gp_reward": gp_reward,
        }
        self._push_notice(user_id, entry, run=run, battle_engine=battle_engine)
        return entry

    def reconcile(self, user_id: str, stats=None, save: bool = True, run=None, battle_engine=None) -> List[Dict[str, Any]]:
        if not user_id or self.save_manager is None or not hasattr(self.save_manager, "load_stats"):
            return []
        if stats is None:
            stats = self.save_manager.load_stats(user_id)
        if not self._can_persist_achievements(stats):
            return []
        unlocked = stats.unlocked_achievements
        newly_unlocked: List[Dict[str, Any]] = []
        for aid in ACHIEVEMENT_ORDER:
            if aid in unlocked:
                continue
            evaluator = ACHIEVEMENT_EVALUATORS.get(aid)
            if evaluator is not None and evaluator(stats):
                entry = self._grant_unlocked(user_id, stats, aid, run=run, battle_engine=battle_engine)
                if entry is not None:
                    newly_unlocked.append(entry)
        if newly_unlocked and save and hasattr(self.save_manager, "save_stats"):
            self.save_manager.save_stats(user_id, stats)
        return newly_unlocked

    def unlock(self, user_id: str, achievement_id: str, stats=None, save: bool = True, run=None, battle_engine=None) -> Optional[Dict[str, Any]]:
        if not user_id or self.save_manager is None or not hasattr(self.save_manager, "load_stats"):
            return None
        if stats is None:
            stats = self.save_manager.load_stats(user_id)
        if not self._can_persist_achievements(stats):
            return None
        entry = self._grant_unlocked(user_id, stats, achievement_id, run=run, battle_engine=battle_engine)
        if entry is not None and save and hasattr(self.save_manager, "save_stats"):
            self.save_manager.save_stats(user_id, stats)
        return entry

    def record_stat(
        self,
        user_id: str,
        key: str,
        value: int = 1,
        mode: str = "add",
        stats=None,
        save: bool = True,
        run=None,
        battle_engine=None,
    ) -> List[Dict[str, Any]]:
        if not user_id or self.save_manager is None or not hasattr(self.save_manager, "load_stats"):
            return []
        if stats is None:
            stats = self.save_manager.load_stats(user_id)
        if not self._can_persist_achievements(stats):
            return []
        ach_stats = getattr(stats, "achievement_stats", None)
        if not isinstance(ach_stats, dict):
            ach_stats = {}
            stats.achievement_stats = ach_stats
        curr = int(ach_stats.get(key, 0) or 0)
        if mode == "min":
            if key not in ach_stats or value < curr:
                ach_stats[key] = value
        elif mode == "max":
            if key not in ach_stats or value > curr:
                ach_stats[key] = value
        else:
            ach_stats[key] = curr + int(value)
        newly = self.reconcile(user_id, stats=stats, save=False, run=run, battle_engine=battle_engine)
        if save and hasattr(self.save_manager, "save_stats"):
            self.save_manager.save_stats(user_id, stats)
        return newly

    def purchase_all_view(self, user_id: str, confirmed: bool = False) -> Tuple[bool, str]:
        stats = self.save_manager.load_stats(user_id)
        self.reconcile(user_id, stats=stats, save=True)
        if getattr(stats, "achievement_all_view", False):
            return False, get_locale_text("i18n_achievement.all_view_already")
        gp = int(getattr(stats, "gp", 0) or 0)
        if not confirmed:
            return False, get_locale_text(
                "i18n_achievement.all_view_confirm_prompt",
                price=ACHIEVEMENT_ALL_VIEW_PRICE,
                gp=gp,
            )
        if gp < ACHIEVEMENT_ALL_VIEW_PRICE:
            return False, get_locale_text(
                "i18n_achievement.all_view_insufficient_gp",
                price=ACHIEVEMENT_ALL_VIEW_PRICE,
                gp=gp,
            )
        stats.gp = gp - ACHIEVEMENT_ALL_VIEW_PRICE
        stats.achievement_all_view = True
        self.save_manager.save_stats(user_id, stats)
        return True, get_locale_text(
            "i18n_achievement.all_view_unlocked",
            price=ACHIEVEMENT_ALL_VIEW_PRICE,
        )

    def build_reader_data(
        self,
        stats,
        rarity_filter: Optional[str] = None,
        only_unlocked: bool = False,
    ) -> Tuple[str, List[str]]:
        unlocked_set = set(getattr(stats, "unlocked_achievements", None) or [])
        all_view = bool(getattr(stats, "achievement_all_view", False))
        gp = int(getattr(stats, "gp", 0) or 0)
        all_view_status = (
            get_locale_text("i18n_achievement.all_view_on")
            if all_view
            else get_locale_text("i18n_achievement.all_view_off", price=ACHIEVEMENT_ALL_VIEW_PRICE)
        )
        title = get_locale_text(
            "i18n_achievement.title",
            unlocked=len(unlocked_set),
            total=len(ACHIEVEMENT_ORDER),
            gp=gp,
            all_view_status=all_view_status,
        )
        items: List[str] = []
        status_unlocked = get_locale_text("i18n_achievement.status_unlocked")
        status_locked = get_locale_text("i18n_achievement.status_locked")
        hidden_name = get_locale_text("i18n_achievement.hidden_name")
        hidden_desc = get_locale_text("i18n_achievement.hidden_desc")
        for rarity in ACHIEVEMENT_RARITY_ORDER:
            if rarity_filter and rarity != rarity_filter:
                continue
            for aid in ACHIEVEMENT_ORDER:
                cfg = ACHIEVEMENTS_CONFIG[aid]
                if cfg["rarity"] != rarity:
                    continue
                is_unlocked = aid in unlocked_set
                if only_unlocked and not is_unlocked:
                    continue
                rarity_str = self._rarity_label(rarity)
                status_str = status_unlocked if is_unlocked else status_locked
                is_hidden = (rarity in HIDDEN_ACHIEVEMENT_RARITIES) and (not is_unlocked) and (not all_view)
                if is_hidden:
                    items.append(
                        get_locale_text(
                            "i18n_achievement.entry_hidden",
                            rarity=rarity_str,
                            name=hidden_name,
                            status=status_str,
                            desc=hidden_desc,
                        )
                    )
                else:
                    items.append(
                        get_locale_text(
                            "i18n_achievement.entry_visible",
                            rarity=rarity_str,
                            name=cfg["name"],
                            status=status_str,
                            gp=cfg["gp_reward"],
                            desc=cfg["desc"],
                        )
                    )
        return title, items
