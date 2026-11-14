import random
from typing import Any, Dict, List, Optional, Tuple

from ....data.locale_data import get_locale_raw, get_locale_text
from ....data.outer_plane_config import (
    NECRONOMICON_ITEM,
    OUTER_PLANE_ACTIVE_FLAG,
    OUTER_PLANE_COMBAT_COST,
    OUTER_PLANE_COMBAT_FLAG,
    OUTER_PLANE_DREAM_ROOM,
    OUTER_PLANE_ENCOUNTERS,
    OUTER_PLANE_FLAGS_KEY,
    OUTER_PLANE_LUCIDITY_KEY,
    OUTER_PLANE_MOVE_COST,
    OUTER_PLANE_PENDING_KEY,
    OUTER_PLANE_PHASE_KEY,
    OUTER_PLANE_ROOM_KEY,
    OUTER_PLANE_ROOMS,
    OUTER_PLANE_START_HP,
    OUTER_PLANE_START_LUCIDITY,
    OUTER_PLANE_START_ROOM,
    OUTER_PLANE_VISITED_KEY,
    OUTER_PLANE_WIP_ROOM,
    PHASE_DREAM,
    PHASE_QUEST,
    PHASE_WIP,
)
from ....models.state import EnemyState, GameRun
from ....renderer.outer_plane import render_outer_plane
from ...progress.achievement_service import AchievementService
from ..butcher_bonus import apply_butcher_bonus


def _scene(opt_id: str) -> str:
    key = f"i18n_outer_plane.scene.{opt_id}"
    if get_locale_raw(key) is None:
        return ""
    return get_locale_text(key)


class OuterPlaneEngine:
    def __init__(self, save_manager, engine, town_engine):
        self.save_manager = save_manager
        self.engine = engine
        self.town_engine = town_engine

    def _flags(self, stats) -> Dict[str, Any]:
        flags = stats.town_flags.get(OUTER_PLANE_FLAGS_KEY)
        if not isinstance(flags, dict):
            flags = {}
            stats.town_flags[OUTER_PLANE_FLAGS_KEY] = flags
        return flags

    def _save(self, user_id: str, stats) -> None:
        self.save_manager.save_stats(user_id, stats)

    def is_active(self, stats) -> bool:
        return bool(stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG))

    def _room(self, stats) -> str:
        return stats.town_flags.get(OUTER_PLANE_ROOM_KEY) or OUTER_PLANE_START_ROOM

    def _phase(self, stats) -> str:
        return stats.town_flags.get(OUTER_PLANE_PHASE_KEY, "")

    def _lucidity(self, stats) -> int:
        value = stats.town_flags.get(OUTER_PLANE_LUCIDITY_KEY)
        return OUTER_PLANE_START_LUCIDITY if value is None else int(value)

    def _spend_lucidity(self, stats, cost: int) -> None:
        stats.town_flags[OUTER_PLANE_LUCIDITY_KEY] = max(0, self._lucidity(stats) - int(cost))

    def _mark_visited(self, stats, room_id: str) -> None:
        visited = stats.town_flags.get(OUTER_PLANE_VISITED_KEY)
        if not isinstance(visited, list):
            visited = []
            stats.town_flags[OUTER_PLANE_VISITED_KEY] = visited
        if room_id not in visited:
            visited.append(room_id)

    def _find_option(self, opt_id: str) -> Optional[Dict[str, Any]]:
        for cfg in OUTER_PLANE_ROOMS.values():
            for opt in cfg["options"]:
                if opt["id"] == opt_id:
                    return opt
        return None

    def _visible_options(self, stats) -> List[Tuple[int, Dict[str, Any]]]:
        flags = self._flags(stats)
        result = []
        for opt in OUTER_PLANE_ROOMS[self._room(stats)]["options"]:
            if any(not flags.get(name) for name in opt.get("requires", [])):
                continue
            if any(flags.get(name) for name in opt.get("forbids", [])):
                continue
            if opt.get("once") and flags.get(f"opt_{opt['id']}"):
                continue
            result.append((len(result) + 1, opt))
        return result

    def render(self, user_id: str, stats, scene_text: str = "", notice: str = "") -> str:
        options = [
            (num, get_locale_text(f"i18n_outer_plane.opt.{opt['id']}"))
            for num, opt in self._visible_options(stats)
        ]
        return render_outer_plane(
            stats, self._room(stats), options,
            self._lucidity(stats), OUTER_PLANE_START_LUCIDITY,
            scene_text, notice,
        )

    def enter_quest(self, user_id: str, stats) -> str:
        stats.town_flags[OUTER_PLANE_PHASE_KEY] = PHASE_QUEST
        stats.town_flags[OUTER_PLANE_ACTIVE_FLAG] = True
        stats.town_flags[OUTER_PLANE_ROOM_KEY] = OUTER_PLANE_START_ROOM
        stats.town_flags[OUTER_PLANE_VISITED_KEY] = []
        stats.town_flags[OUTER_PLANE_LUCIDITY_KEY] = OUTER_PLANE_START_LUCIDITY
        stats.town_flags.pop(OUTER_PLANE_PENDING_KEY, None)
        self._mark_visited(stats, OUTER_PLANE_START_ROOM)
        self._save(user_id, stats)
        return get_locale_text("i18n_outer_plane.ending.arrive") + "\n\n" + self.render(user_id, stats)

    def enter_wip(self, user_id: str, stats) -> str:
        stats.town_flags[OUTER_PLANE_PHASE_KEY] = PHASE_WIP
        stats.town_flags[OUTER_PLANE_ACTIVE_FLAG] = True
        stats.town_flags[OUTER_PLANE_ROOM_KEY] = OUTER_PLANE_WIP_ROOM
        stats.town_flags[OUTER_PLANE_VISITED_KEY] = []
        self._mark_visited(stats, OUTER_PLANE_WIP_ROOM)
        self._save(user_id, stats)
        return get_locale_text("i18n_outer_plane.ending.wip_arrive") + "\n\n" + self.render(user_id, stats)

    def choose(self, user_id: str, stats, raw: str) -> str:
        if not self.is_active(stats):
            return get_locale_text("i18n_outer_plane.ui.not_in_outer_plane")
        token = (raw or "").strip().lower()
        picked = None
        for num, opt in self._visible_options(stats):
            if token == str(num) or token == opt["id"].lower():
                picked = opt
                break
        if picked is None:
            return get_locale_text("i18n_outer_plane.ui.invalid_option") + "\n\n" + self.render(user_id, stats)
        return self._apply(user_id, stats, picked)

    def attack(self, user_id: str, stats) -> str:
        if not self.is_active(stats):
            return get_locale_text("i18n_outer_plane.ui.not_in_outer_plane")
        flags = self._flags(stats)
        for _, opt in self._visible_options(stats):
            if opt.get("butcher"):
                flags["butcher_path"] = True
                return self._apply(user_id, stats, opt)
        for room_id, cfg in OUTER_PLANE_ROOMS.items():
            if room_id == self._room(stats):
                continue
            for opt in cfg["options"]:
                if not opt.get("butcher") or not opt.get("encounter"):
                    continue
                reward_flag = OUTER_PLANE_ENCOUNTERS[opt["encounter"]].get("reward_flag")
                if reward_flag and flags.get(reward_flag):
                    continue
                if flags.get("forged_by_force"):
                    continue
                flags["butcher_path"] = True
                return self._apply(user_id, stats, {"id": f"attack_to_{room_id}", "to": room_id})
        for _, opt in self._visible_options(stats):
            if opt.get("fuse") or opt.get("to") or opt.get("leave") or opt.get("dream") or opt.get("wake"):
                flags["butcher_path"] = True
                return self._apply(user_id, stats, opt)
        return get_locale_text("i18n_outer_plane.ui.no_attack") + "\n\n" + self.render(user_id, stats)

    def look(self, user_id: str, stats) -> str:
        if not self.is_active(stats):
            return get_locale_text("i18n_outer_plane.ui.not_in_outer_plane")
        return self.render(user_id, stats)

    def leave(self, user_id: str, stats) -> str:
        if self._phase(stats) == PHASE_QUEST:
            return get_locale_text("i18n_outer_plane.ui.invalid_option") + "\n\n" + self.render(user_id, stats)
        if self._phase(stats) == PHASE_DREAM:
            self._flags(stats).pop("max_hp_zero", None)
            stats.town_flags[OUTER_PLANE_PHASE_KEY] = ""
        stats.town_flags[OUTER_PLANE_ACTIVE_FLAG] = False
        stats.town_flags.pop(OUTER_PLANE_PENDING_KEY, None)
        self._save(user_id, stats)
        return get_locale_text("i18n_outer_plane.ui.leave") + "\n\n" + self.town_engine.render_current_room(user_id, stats)

    def _apply(self, user_id: str, stats, opt) -> str:
        flags = self._flags(stats)
        flags[f"opt_{opt['id']}"] = True
        scene = _scene(opt["id"])
        notices = []
        if opt.get("lucidity"):
            gain = int(opt["lucidity"])
            stats.town_flags[OUTER_PLANE_LUCIDITY_KEY] = min(
                OUTER_PLANE_START_LUCIDITY, self._lucidity(stats) + gain)
            notices.append(get_locale_text("i18n_outer_plane.ui.lucidity_gain", gain=gain))
        if opt.get("encounter"):
            return self._start_encounter(user_id, stats, opt, scene, notices)
        if opt.get("fuse"):
            return self._fuse(user_id, stats, scene, "\n".join(notices))
        if opt.get("dream"):
            return self._enter_dream(user_id, stats, scene)
        if opt.get("wake"):
            return self._wake(user_id, stats, scene)
        if opt.get("leave"):
            return self.leave(user_id, stats)
        for name, value in opt.get("set", {}).items():
            flags[name] = value
        if opt.get("to"):
            stats.town_flags[OUTER_PLANE_ROOM_KEY] = opt["to"]
            self._mark_visited(stats, opt["to"])
            self._spend_lucidity(stats, OUTER_PLANE_MOVE_COST)
        self._save(user_id, stats)
        if self._lucidity(stats) <= 0:
            return self._blackout(user_id, stats)
        return self.render(user_id, stats, scene_text=scene, notice="\n".join(notices))

    def _blackout(self, user_id: str, stats) -> str:
        flags = self._flags(stats)
        flags["blackouts"] = int(flags.get("blackouts", 0)) + 1
        stats.town_flags[OUTER_PLANE_ROOM_KEY] = OUTER_PLANE_START_ROOM
        stats.town_flags[OUTER_PLANE_LUCIDITY_KEY] = OUTER_PLANE_START_LUCIDITY
        self._mark_visited(stats, OUTER_PLANE_START_ROOM)
        self._save(user_id, stats)
        text = "\n\n".join([
            get_locale_text("i18n_outer_plane.ending.blackout"),
            get_locale_text("i18n_outer_plane.ui.blackout_notice"),
        ])
        return text + "\n\n" + self.render(user_id, stats)

    def _start_encounter(self, user_id: str, stats, opt, scene: str, notices: List[str]) -> str:
        flags = self._flags(stats)
        encounter_id = opt["encounter"]
        cfg = OUTER_PLANE_ENCOUNTERS[encounter_id]
        is_boss = bool(cfg.get("boss"))
        enemies = []
        for entry in cfg["enemies"]:
            hp = int(entry["hp"])
            enemies.append(EnemyState(
                name=get_locale_text(entry["name_key"]),
                hp=hp,
                max_hp=hp,
                shield=0,
                actions=1,
                bonus_actions=1 if is_boss else 0,
                max_actions=1,
                max_bonus_actions=1 if is_boss else 0,
            ))
        p_state = self.town_engine.build_combat_player(
            user_id, stats, hp=OUTER_PLANE_START_HP, max_hp=OUTER_PLANE_START_HP)
        apply_butcher_bonus(p_state, flags)
        random.shuffle(p_state.draw_pile)
        for _ in range(min(5, len(p_state.draw_pile))):
            p_state.hand.append(p_state.draw_pile.pop(0))
        node_data = {
            "is_town_combat": True,
            OUTER_PLANE_COMBAT_FLAG: encounter_id,
            OUTER_PLANE_PENDING_KEY: opt["id"],
            "outer_plane_room": self._room(stats),
            "outer_plane_turn": 0,
        }
        run = GameRun(user_id=user_id, node_type="battle", player=p_state, enemies=enemies, node_data=node_data)
        self.engine.battle_engine.enemy_controller.roll_enemy_intent(run)
        self.save_manager.save_save(user_id, run)
        self._spend_lucidity(stats, OUTER_PLANE_COMBAT_COST)
        stats.town_flags[OUTER_PLANE_PENDING_KEY] = opt["id"]
        self._save(user_id, stats)
        from ....renderer import GameRenderer
        parts = [get_locale_text(f"i18n_outer_plane.encounter.{encounter_id}.scene"), GameRenderer.render_game(run)]
        if scene:
            parts.insert(0, scene)
        if notices:
            parts.append("\n".join(notices))
        return "\n\n".join(parts)

    def on_battle_win(self, user_id: str, stats, run) -> str:
        flags = self._flags(stats)
        pending_id = run.node_data.get(OUTER_PLANE_PENDING_KEY) or stats.town_flags.get(OUTER_PLANE_PENDING_KEY)
        stats.town_flags.pop(OUTER_PLANE_PENDING_KEY, None)
        encounter_id = run.node_data.get(OUTER_PLANE_COMBAT_FLAG, "")
        cfg = OUTER_PLANE_ENCOUNTERS.get(encounter_id, {})
        notices = []
        reward_flag = cfg.get("reward_flag")
        reward_card = cfg.get("reward_card")
        if reward_flag and not flags.get(reward_flag):
            flags[reward_flag] = True
            if reward_card:
                from ....entities.cards import ALL_CARDS
                card = ALL_CARDS.get(reward_card)
                name = card.name if card else reward_card
                notices.append(get_locale_text("i18n_outer_plane.ui.card_gain", name=name))
        opt = self._find_option(pending_id) if pending_id else None
        if opt:
            for name, value in opt.get("set", {}).items():
                flags[name] = value
        self._save(user_id, stats)
        win_text = get_locale_text(f"i18n_outer_plane.encounter.{encounter_id}.win")
        if flags.get("forged_by_force"):
            return self._fuse(user_id, stats, win_text, "\n".join(notices))
        if self._lucidity(stats) <= 0:
            return win_text + "\n\n" + self._blackout(user_id, stats)
        stats.town_flags[OUTER_PLANE_ROOM_KEY] = OUTER_PLANE_START_ROOM
        self._mark_visited(stats, OUTER_PLANE_START_ROOM)
        self._save(user_id, stats)
        return win_text + "\n\n" + self.render(user_id, stats, notice="\n".join(notices))

    def on_battle_lose(self, user_id: str, stats, run) -> str:
        stats.town_flags[OUTER_PLANE_ROOM_KEY] = OUTER_PLANE_START_ROOM
        stats.town_flags[OUTER_PLANE_LUCIDITY_KEY] = OUTER_PLANE_START_LUCIDITY
        stats.town_flags[OUTER_PLANE_PHASE_KEY] = PHASE_QUEST
        stats.town_flags[OUTER_PLANE_ACTIVE_FLAG] = True
        stats.town_flags.pop(OUTER_PLANE_PENDING_KEY, None)
        self._mark_visited(stats, OUTER_PLANE_START_ROOM)
        self._save(user_id, stats)
        return get_locale_text("i18n_outer_plane.combat.lose") + "\n\n" + self.render(user_id, stats)

    def _fuse(self, user_id: str, stats, scene: str, notice: str = "") -> str:
        flags = self._flags(stats)
        flags["shard_forged"] = True
        lines = [scene] if scene else []
        lines.append(get_locale_text("i18n_outer_plane.ending.fuse_done"))
        lines.append(get_locale_text("i18n_outer_plane.ending.return_book"))
        return "\n\n".join(lines) + "\n\n" + self._finish(user_id, stats, notice)

    def _finish(self, user_id: str, stats, notice: str = "") -> str:
        stats.town_flags[OUTER_PLANE_ACTIVE_FLAG] = False
        stats.town_flags[OUTER_PLANE_PHASE_KEY] = ""
        stats.town_flags[OUTER_PLANE_ROOM_KEY] = ""
        stats.town_flags.pop(OUTER_PLANE_PENDING_KEY, None)
        from ....data.temple_config import TEMPLE_FLAGS_KEY, TEMPLE_QUEST_FLAG
        stats.town_flags[TEMPLE_QUEST_FLAG] = "completed"
        if NECRONOMICON_ITEM not in stats.town_inventory:
            stats.town_inventory.append(NECRONOMICON_ITEM)
        stats.in_town = True
        stats.town_pos = "square"
        self._save(user_id, stats)
        ach = AchievementService(self.save_manager)
        ach.unlock(user_id, "temple_awakening", stats=stats)
        temple_flags = stats.town_flags.get(TEMPLE_FLAGS_KEY) or {}
        plane_flags = stats.town_flags.get(OUTER_PLANE_FLAGS_KEY) or {}
        if temple_flags.get("butcher_path") or plane_flags.get("butcher_path"):
            ach.unlock(user_id, "silent_passage", stats=stats)
        self._save(user_id, stats)
        lines = [
            get_locale_text("i18n_outer_plane.ending.wake_town"),
            get_locale_text("i18n_outer_plane.ending.quest_done"),
        ]
        if notice:
            lines.append(notice)
        return "\n\n".join(lines) + "\n\n" + self.town_engine.render_current_room(user_id, stats)

    def _enter_dream(self, user_id: str, stats, scene: str) -> str:
        flags = self._flags(stats)
        flags["max_hp_zero"] = True
        stats.town_flags[OUTER_PLANE_PHASE_KEY] = PHASE_DREAM
        stats.town_flags[OUTER_PLANE_ROOM_KEY] = OUTER_PLANE_DREAM_ROOM
        self._mark_visited(stats, OUTER_PLANE_DREAM_ROOM)
        self._save(user_id, stats)
        lines = [scene] if scene else []
        lines.append(get_locale_text("i18n_outer_plane.dream_shard.trigger"))
        lines.append(get_locale_text("i18n_outer_plane.ending.zero_arrive"))
        return "\n\n".join(lines) + "\n\n" + self.render(user_id, stats)

    def _wake(self, user_id: str, stats, scene: str) -> str:
        self._flags(stats).pop("max_hp_zero", None)
        stats.town_flags[OUTER_PLANE_ACTIVE_FLAG] = False
        stats.town_flags[OUTER_PLANE_PHASE_KEY] = ""
        stats.town_flags[OUTER_PLANE_ROOM_KEY] = ""
        stats.in_town = True
        stats.town_pos = "square"
        self._save(user_id, stats)
        lines = [scene] if scene else []
        lines.append(get_locale_text("i18n_outer_plane.ending.zero_wake"))
        return "\n\n".join(lines) + "\n\n" + self.town_engine.render_current_room(user_id, stats)

    def trigger_from_battle(self, user_id: str, stats) -> str:
        flags = self._flags(stats)
        flags["max_hp_zero"] = True
        stats.town_flags[OUTER_PLANE_PHASE_KEY] = PHASE_DREAM
        stats.town_flags[OUTER_PLANE_ACTIVE_FLAG] = True
        stats.town_flags[OUTER_PLANE_ROOM_KEY] = OUTER_PLANE_DREAM_ROOM
        self._mark_visited(stats, OUTER_PLANE_DREAM_ROOM)
        self._save(user_id, stats)
        return "\n\n".join([
            get_locale_text("i18n_outer_plane.dream_shard.hidden_trigger"),
            get_locale_text("i18n_outer_plane.ending.zero_arrive"),
        ]) + "\n\n" + self.render(user_id, stats)

    def apply_max_hp_zero(self, stats) -> bool:
        return bool(self._flags(stats).get("max_hp_zero"))
