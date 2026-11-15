import random
from typing import Any, Dict, List, Optional, Tuple

from ....data.locale_data import get_locale_raw, get_locale_text
from ....data.temple_config import (
    ENDING_BRANCH_FLAGS,
    TEMPLE_ACTIVE_FLAG,
    TEMPLE_BOSS_HP_MODIFIERS,
    TEMPLE_ENCOUNTERS,
    TEMPLE_ENTER_ROOM,
    TEMPLE_FLAGS_KEY,
    TEMPLE_HP_KEY,
    TEMPLE_INFO_FLAG,
    TEMPLE_MAX_HP_KEY,
    TEMPLE_PENDING_KEY,
    TEMPLE_QUEST_FLAG,
    TEMPLE_ROOM_FLAG,
    TEMPLE_ROOMS,
    TEMPLE_START_HP,
    TEMPLE_VISITED_KEY,
    TEMPLE_WIN_HEAL,
)
from ....models.state import EnemyState, GameRun
from ....renderer.temple import render_temple
from ...text.events import LocaleText, RenderedText, ScreenText, TextDocument
from ...text.pipeline import render_text
from ..butcher_bonus import apply_butcher_bonus

TEMPLE_SCREEN = "temple"


def _line(key: str, section: str = "body", **params) -> LocaleText:
    return LocaleText(key=key, params=params, section=section)


def _scene_node(opt_id: str) -> LocaleText | None:
    key = f"i18n_temple.scene.{opt_id}"
    if get_locale_raw(key) is None:
        return None
    return LocaleText(key=key, section="scene")


def _screen_node(scene: LocaleText | None = None, notice: list[LocaleText] | None = None) -> ScreenText:
    return ScreenText(
        section="screen",
        screen=TEMPLE_SCREEN,
        scene=[scene] if scene else [],
        notice=list(notice or []),
    )


class TempleEngine:
    def __init__(self, save_manager, engine, town_engine):
        self.save_manager = save_manager
        self.engine = engine
        self.town_engine = town_engine

    def _flags(self, stats) -> Dict[str, Any]:
        flags = stats.town_flags.get(TEMPLE_FLAGS_KEY)
        if not isinstance(flags, dict):
            flags = {}
            stats.town_flags[TEMPLE_FLAGS_KEY] = flags
        return flags

    def _save(self, user_id: str, stats) -> None:
        self.save_manager.save_stats(user_id, stats)

    def is_active(self, stats) -> bool:
        return bool(stats.town_flags.get(TEMPLE_ACTIVE_FLAG))

    def _room(self, stats) -> str:
        return stats.town_flags.get(TEMPLE_ROOM_FLAG) or TEMPLE_ENTER_ROOM

    def _mark_visited(self, stats, room_id: str) -> None:
        visited = stats.town_flags.get(TEMPLE_VISITED_KEY)
        if not isinstance(visited, list):
            visited = []
            stats.town_flags[TEMPLE_VISITED_KEY] = visited
        if room_id not in visited:
            visited.append(room_id)

    def _find_option(self, opt_id: str) -> Optional[Dict[str, Any]]:
        for cfg in TEMPLE_ROOMS.values():
            for opt in cfg["options"]:
                if opt["id"] == opt_id:
                    return opt
        return None

    def _render_document(self, user_id: str, stats, document: TextDocument) -> str:
        return render_text(
            document,
            "temple",
            {
                TEMPLE_SCREEN: lambda scene, notice: self.render(
                    user_id, stats, scene_text=scene, notice=notice
                )
            },
        )

    def attack(self, user_id: str, stats) -> str:
        if not self.is_active(stats):
            return self._render_document(user_id, stats, [
                _line("i18n_temple.ui.not_in_temple"),
            ])
        options = self._visible_options(stats)
        for _, opt in options:
            if opt.get("encounter"):
                self._flags(stats)["butcher_path"] = True
                return self._render_document(user_id, stats, self._apply_events(user_id, stats, opt))
        for _, opt in options:
            if opt.get("to") or opt.get("ending"):
                self._flags(stats)["butcher_path"] = True
                return self._render_document(user_id, stats, self._apply_events(user_id, stats, opt))
        return self._render_document(user_id, stats, [
            _line("i18n_temple.ui.no_attack"),
            _screen_node(),
        ])

    def can_enter(self, stats) -> Tuple[bool, Optional[LocaleText]]:
        if stats.town_flags.get(TEMPLE_QUEST_FLAG) in ("completed", "outer_plane"):
            return False, _line("i18n_temple.enter.finished")
        if self.is_active(stats):
            return False, _line("i18n_temple.enter.already")
        if int(getattr(stats, "yog_sothoth_kill_count", 0) or 0) <= 0:
            return False, _line("i18n_temple.enter.need_kill")
        if not stats.town_flags.get(TEMPLE_INFO_FLAG):
            return False, _line("i18n_temple.enter.need_info")
        if stats.town_pos != "west_gate":
            return False, _line("i18n_temple.enter.need_gate")
        return True, None

    def enter(self, user_id: str, stats) -> str:
        ok, msg = self.can_enter(stats)
        if not ok:
            return self._render_document(user_id, stats, [msg] if msg else [])
        flags = self._flags(stats)
        if not flags.get("initialized"):
            flags["initialized"] = True
            stats.town_flags[TEMPLE_HP_KEY] = TEMPLE_START_HP
            stats.town_flags[TEMPLE_MAX_HP_KEY] = TEMPLE_START_HP
            stats.town_flags[TEMPLE_VISITED_KEY] = []
            stats.town_flags[TEMPLE_ROOM_FLAG] = TEMPLE_ENTER_ROOM
        elif not stats.town_flags.get(TEMPLE_ROOM_FLAG):
            stats.town_flags[TEMPLE_ROOM_FLAG] = TEMPLE_ENTER_ROOM
        stats.town_flags[TEMPLE_ACTIVE_FLAG] = True
        self._mark_visited(stats, self._room(stats))
        self._save(user_id, stats)
        return self._render_document(user_id, stats, [
            _line("i18n_temple.enter.banner"),
            _screen_node(),
        ])

    def _visible_options(self, stats) -> List[Tuple[int, Dict[str, Any]]]:
        flags = self._flags(stats)
        result = []
        for opt in TEMPLE_ROOMS[self._room(stats)]["options"]:
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
            (num, get_locale_text(f"i18n_temple.opt.{opt['id']}"))
            for num, opt in self._visible_options(stats)
        ]
        return render_temple(stats, self._room(stats), options, scene_text, notice)

    def choose(self, user_id: str, stats, raw: str) -> str:
        if not self.is_active(stats):
            return self._render_document(user_id, stats, [
                _line("i18n_temple.ui.not_in_temple"),
            ])
        token = (raw or "").strip().lower()
        picked = None
        for num, opt in self._visible_options(stats):
            if token == str(num) or token == opt["id"].lower():
                picked = opt
                break
        if picked is None:
            return self._render_document(user_id, stats, [
                _line("i18n_temple.ui.invalid_option"),
                _screen_node(),
            ])
        return self._render_document(user_id, stats, self._apply_events(user_id, stats, picked))

    def read(self, user_id: str, stats) -> str:
        if not self.is_active(stats):
            return self._render_document(user_id, stats, [
                _line("i18n_temple.ui.not_in_temple"),
            ])
        for _, opt in self._visible_options(stats):
            if opt.get("ending"):
                return self._render_document(user_id, stats, self._apply_events(user_id, stats, opt))
        return self._render_document(user_id, stats, [
            _line("i18n_temple.ui.no_read"),
            _screen_node(),
        ])

    def leave(self, user_id: str, stats) -> str:
        return self._render_document(user_id, stats, self._leave_events(user_id, stats))

    def _leave_events(self, user_id: str, stats) -> TextDocument:
        stats.town_flags[TEMPLE_ACTIVE_FLAG] = False
        stats.town_flags.pop(TEMPLE_PENDING_KEY, None)
        self._save(user_id, stats)
        return [
            _line("i18n_temple.ui.leave"),
            RenderedText(text=self.town_engine.render_current_room(user_id, stats), section="body"),
        ]

    def _apply_gains(self, stats, opt) -> List[LocaleText]:
        notices = []
        if opt.get("heal"):
            hp = int(stats.town_flags.get(TEMPLE_HP_KEY, TEMPLE_START_HP) or TEMPLE_START_HP)
            max_hp = int(stats.town_flags.get(TEMPLE_MAX_HP_KEY, TEMPLE_START_HP) or TEMPLE_START_HP)
            stats.town_flags[TEMPLE_HP_KEY] = min(max_hp, hp + int(opt["heal"]))
            notices.append(_line("i18n_temple.ui.hp_gain", "notice", heal=opt["heal"]))
        if opt.get("gp"):
            stats.gp = int(getattr(stats, "gp", 0) or 0) + int(opt["gp"])
            notices.append(_line("i18n_temple.ui.gp_gain", "notice", gp=opt["gp"]))
        return notices

    def _apply_events(self, user_id: str, stats, opt) -> TextDocument:
        flags = self._flags(stats)
        flags[f"opt_{opt['id']}"] = True
        scene = _scene_node(opt["id"])
        notices = self._apply_gains(stats, opt)
        for name, value in opt.get("set", {}).items():
            flags[name] = value
        if opt.get("leave"):
            return self._leave_events(user_id, stats)
        if opt.get("ending"):
            return self._ending_events(user_id, stats, scene)
        if opt.get("encounter"):
            return self._start_encounter_events(user_id, stats, opt, scene, notices)
        if opt.get("to"):
            stats.town_flags[TEMPLE_ROOM_FLAG] = opt["to"]
            self._mark_visited(stats, opt["to"])
        self._save(user_id, stats)
        return [_screen_node(scene, notices)]

    def _start_encounter_events(self, user_id: str, stats, opt, scene: LocaleText | None, notices: List[LocaleText]) -> TextDocument:
        encounter_id = opt["encounter"]
        cfg = TEMPLE_ENCOUNTERS[encounter_id]
        flags = self._flags(stats)
        is_boss = bool(cfg.get("boss"))
        boss_mod = 0
        if is_boss:
            for name, delta in TEMPLE_BOSS_HP_MODIFIERS.items():
                if flags.get(name):
                    boss_mod += delta
        enemies = []
        for name, base_hp in cfg["enemies"]:
            hp = max(1, int(base_hp) + (boss_mod if is_boss else 0))
            enemies.append(EnemyState(
                name=name,
                hp=hp,
                max_hp=hp,
                shield=0,
                actions=1,
                bonus_actions=1 if is_boss else 0,
                max_actions=1,
                max_bonus_actions=1 if is_boss else 0,
            ))
        hp = int(stats.town_flags.get(TEMPLE_HP_KEY, TEMPLE_START_HP) or TEMPLE_START_HP)
        max_hp = int(stats.town_flags.get(TEMPLE_MAX_HP_KEY, TEMPLE_START_HP) or TEMPLE_START_HP)
        p_state = self.town_engine.build_combat_player(user_id, stats, hp=hp, max_hp=max_hp)
        apply_butcher_bonus(p_state, flags)
        random.shuffle(p_state.draw_pile)
        for _ in range(min(5, len(p_state.draw_pile))):
            p_state.hand.append(p_state.draw_pile.pop(0))
        node_data = {
            "is_town_combat": True,
            "temple_encounter": encounter_id,
            "temple_pending_option": opt["id"],
            "temple_room": self._room(stats),
            "npc_name": "",
            "temple_attack_bonus": 3 if flags.get("altar_defiled") else 0,
            "temple_cultist_turn": 0,
            "temple_boss_turn": 0,
        }
        run = GameRun(user_id=user_id, node_type="battle", player=p_state, enemies=enemies, node_data=node_data)
        self.engine.battle_engine.enemy_controller.roll_enemy_intent(run)
        self.save_manager.save_save(user_id, run)
        stats.town_flags[TEMPLE_PENDING_KEY] = opt["id"]
        self._save(user_id, stats)
        from ....renderer import GameRenderer
        document: TextDocument = [scene] if scene else []
        document.append(_line(f"i18n_temple.encounter.{encounter_id}.scene", "encounter"))
        document.append(RenderedText(text=GameRenderer.render_game(run), section="combat"))
        document.extend(notices)
        return document

    def on_battle_win(self, user_id: str, stats, run) -> str:
        return self._render_document(user_id, stats, self._on_battle_win_events(user_id, stats, run))

    def _on_battle_win_events(self, user_id: str, stats, run) -> TextDocument:
        flags = self._flags(stats)
        pending_id = run.node_data.get("temple_pending_option") or stats.town_flags.get(TEMPLE_PENDING_KEY)
        stats.town_flags.pop(TEMPLE_PENDING_KEY, None)
        hp = max(1, int(run.player.hp or 1))
        max_hp = int(stats.town_flags.get(TEMPLE_MAX_HP_KEY, TEMPLE_START_HP) or TEMPLE_START_HP)
        stats.town_flags[TEMPLE_HP_KEY] = min(max_hp, hp + TEMPLE_WIN_HEAL)
        encounter_id = run.node_data.get("temple_encounter", "")
        notices = [
            _line("i18n_temple.combat.win_heal", "notice", heal=TEMPLE_WIN_HEAL)
        ]
        opt = self._find_option(pending_id) if pending_id else None
        if opt:
            for name, value in opt.get("set", {}).items():
                flags[name] = value
            if opt.get("gp"):
                stats.gp = int(getattr(stats, "gp", 0) or 0) + int(opt["gp"])
                notices.append(_line("i18n_temple.ui.gp_gain", "notice", gp=opt["gp"]))
            if opt.get("to"):
                stats.town_flags[TEMPLE_ROOM_FLAG] = opt["to"]
                self._mark_visited(stats, opt["to"])
        self._save(user_id, stats)
        return [
            _line(f"i18n_temple.encounter.{encounter_id}.win", "combat"),
            _screen_node(None, notices),
        ]

    def on_battle_lose(self, user_id: str, stats, run) -> str:
        stats.town_flags[TEMPLE_HP_KEY] = TEMPLE_START_HP
        stats.town_flags[TEMPLE_MAX_HP_KEY] = TEMPLE_START_HP
        stats.town_flags[TEMPLE_ROOM_FLAG] = run.node_data.get("temple_room") or TEMPLE_ENTER_ROOM
        stats.town_flags.pop(TEMPLE_PENDING_KEY, None)
        self._save(user_id, stats)
        return self._render_document(user_id, stats, [
            _line("i18n_temple.combat.lose", "combat"),
            _screen_node(),
        ])

    def _ending_events(self, user_id: str, stats, scene: LocaleText | None) -> TextDocument:
        flags = self._flags(stats)
        document: TextDocument = [scene] if scene else []
        for key in ("open", "faint", "outer_plane", "yog_arrive", "yog_reveal"):
            document.append(_line(f"i18n_temple.ending.{key}", "ending"))
        for name in ENDING_BRANCH_FLAGS:
            if not flags.get(name):
                continue
            key = f"i18n_temple.ending.branch.{name}"
            if get_locale_raw(key) is not None:
                document.append(_line(key, "ending"))
        document.append(_line("i18n_temple.ending.detain", "ending"))
        stats.town_flags[TEMPLE_QUEST_FLAG] = "outer_plane"
        stats.town_flags[TEMPLE_ACTIVE_FLAG] = False
        stats.town_flags[TEMPLE_ROOM_FLAG] = ""
        stats.town_flags.pop(TEMPLE_PENDING_KEY, None)
        stats.in_town = True
        stats.town_pos = "square"
        self._save(user_id, stats)
        document.append(RenderedText(
            text=self.town_engine.outer_plane_engine.enter_quest(user_id, stats),
            section="body",
        ))
        return document
