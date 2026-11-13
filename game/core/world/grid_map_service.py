import random
from ...data.corpse_config import CorpseConfig
from ...data.grid_map_config import (
    FLOOR_CONFIGS,
    HIGH_DANGER_CONFIG,
    PASSABLE_ROOM_TYPES,
    PERMANENT_ICON_TYPES,
    ROOM_ICONS,
    SP_CONFIG,
)
from ...data.locale_data import get_locale_text
from ...data.balance_config import MAP_GHOST_DEFAULT_MAX_HP
from .grid_map_generator import compute_effective_stage, coord_to_xy, xy_to_coord
from .landmark_system import build_downstairs_data, build_landmark_options
from ..party.coordinator import apply_and_scope, restore_player, swap_player
from ..party.session import SessionContextScoper
from .sp_system import check_exhaustion_death, consume_sp


DIR_DELTAS = {
    "w": (0, -1),
    "up": (0, -1),
    "s": (0, 1),
    "down": (0, 1),
    "a": (-1, 0),
    "left": (-1, 0),
    "d": (1, 0),
    "right": (1, 0),
}

TP_TYPE_ALIASES = {
    "出生点": "spawn",
    "spawn": "spawn",
    "咖啡馆": "cafe",
    "cafe": "cafe",
    "商店": "shop",
    "shop": "shop",
    "篝火": "rest",
    "休息": "rest",
    "休息点": "rest",
    "rest": "rest",
    "宝箱": "treasure",
    "treasure": "treasure",
    "地标": "landmark",
    "landmark": "landmark",
    "生命商人": "life_merchant",
    "life_merchant": "life_merchant",
    "boss": "boss",
    "首领": "boss",
    "下楼": "downstairs",
    "传送门": "downstairs",
    "downstairs": "downstairs",
    "隐秘首领": "secret_boss",
    "secret_boss": "secret_boss",
}


class GridMapService:
    def __init__(self, save_manager, map_engine):
        self.save_manager = save_manager
        self.map_engine = map_engine

    def idle_teammates(self, run, exclude_uid: str) -> list[str]:
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return []
        res = []
        for uid in run.all_human_uids():
            if uid == exclude_uid:
                continue
            p = run.players.get(uid)
            if p is None or getattr(p, "downed", False) or p.hp <= 0:
                continue
            if uid in fm.player_session_map:
                continue
            res.append(uid)
        return res

    def _reveal_coord(self, fm, coord: str):
        room = fm.rooms.get(coord)
        if room is not None:
            room.explored = True
        if coord not in fm.revealed_coords:
            fm.revealed_coords.append(coord)

    def _sync_stage_for_coord(self, run, player, coord: str):
        fm = run.floor_map
        room = fm.rooms.get(coord)
        cfg = FLOOR_CONFIGS.get(fm.floor_index, FLOOR_CONFIGS[1])
        if room and room.room_type in ("boss", "downstairs"):
            player.stage = int(cfg["stage_max"])
        else:
            player.stage = compute_effective_stage(fm, coord)

    def move_player(self, run, direction: str) -> str:
        from ...renderer import GameRenderer
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return get_locale_text("i18n_grid_map.err_no_floor_map")
        uid = run.user_id
        if uid in fm.player_session_map:
            return get_locale_text("i18n_grid_map.err_in_session")
        dkey = direction.strip().lower()
        if dkey not in DIR_DELTAS:
            return get_locale_text("i18n_grid_map.err_invalid_direction")
        cur = fm.player_coords.get(uid) or xy_to_coord(0, fm.height // 2)
        cx, cy = coord_to_xy(cur)
        dx, dy = DIR_DELTAS[dkey]
        nx, ny = cx + dx, cy + dy
        if not (0 <= nx < fm.width and 0 <= ny < fm.height):
            fm.floor_flags.get("pending_obstacle", {}).pop(uid, None)
            return get_locale_text("i18n_grid_map.err_out_of_bounds")
        target_coord = xy_to_coord(nx, ny)
        room = fm.rooms.get(target_coord)
        if room is None or room.room_type == "wall" or (room.room_type == "secret_boss" and not fm.secret_unlocked):
            fm.floor_flags.get("pending_obstacle", {}).pop(uid, None)
            return get_locale_text("i18n_grid_map.err_blocked_wall")

        p = run.player
        pending_map = fm.floor_flags.setdefault("pending_obstacle", {})
        if room.room_type == "obstacle":
            cost = max(1, int(room.obstacle_sp or SP_CONFIG["obstacle_cost_min"]))
            prev_pending = pending_map.get(uid)
            step = int(prev_pending.get("step", 0)) if (prev_pending and prev_pending.get("coord") == target_coord) else 0
            if step < 2:
                from ...data.room_interact_data import OBSTACLE_STYLES
                style_key = room.obstacle_style or "collapsed_boulders"
                scfg = OBSTACLE_STYLES.get(style_key, OBSTACLE_STYLES["collapsed_boulders"])
                obs_name = get_locale_text(scfg["name_key"])
                obs_desc = get_locale_text(scfg["desc_key"])
                if p.sp >= cost:
                    sp_warn = get_locale_text("i18n_room_interact.obstacle.sp_warn_ok")
                else:
                    sp_warn = get_locale_text(
                        "i18n_room_interact.obstacle.sp_warn_overdraft",
                        loss=SP_CONFIG["forced_obstacle_hp_loss"],
                    )
                next_step = step + 1
                pending_map[uid] = {"coord": target_coord, "dir": dkey, "step": next_step}
                self.save_manager.save_save(uid, run)
                key = "i18n_room_interact.obstacle.confirm_step1" if next_step == 1 else "i18n_room_interact.obstacle.confirm_step2"
                return get_locale_text(
                    key,
                    coord=target_coord,
                    name=obs_name,
                    desc=obs_desc,
                    cost=cost,
                    sp=p.sp,
                    sp_warn=sp_warn,
                    direction=dkey,
                )
            pending_map.pop(uid, None)
            if p.sp >= cost:
                consume_sp(p, cost, allow_overdraft=False)
                room.room_type = "empty"
                room.cleared = True
                room.obstacle_sp = 0
                fm.player_coords[uid] = target_coord
                self._reveal_coord(fm, target_coord)
                self._sync_stage_for_coord(run, p, target_coord)
                self.save_manager.save_save(uid, run)
                prefix = get_locale_text("i18n_grid_map.obstacle_cleared", coord=target_coord, cost=cost, sp=p.sp, max_sp=p.max_sp)
                return f"{prefix}\n\n{GameRenderer.render_game(run)}"
            sp_res = consume_sp(p, cost, allow_overdraft=True)
            hp_loss = SP_CONFIG["forced_obstacle_hp_loss"]
            p.hp = max(0, p.hp - hp_loss)
            if p.hp <= 0 or p.exhaustion >= 5:
                run.node_data["death_cause"] = get_locale_text("i18n_grid_map.exhaustion_death_cause")
                return self.save_manager.settle_game_and_delete(uid, run, is_victory=False, create_corpse=True)
            room.room_type = "empty"
            room.cleared = True
            room.obstacle_sp = 0
            fm.player_coords[uid] = target_coord
            self._reveal_coord(fm, target_coord)
            self._sync_stage_for_coord(run, p, target_coord)
            self.save_manager.save_save(uid, run)
            prefix = get_locale_text(
                "i18n_grid_map.obstacle_forced",
                coord=target_coord,
                hp_loss=hp_loss,
                sp=p.sp,
                exhaustion=sp_res["new_exhaustion"],
            )
            return f"{prefix}\n\n{GameRenderer.render_game(run)}"
        pending_map.pop(uid, None)
        fm.player_coords[uid] = target_coord
        self._reveal_coord(fm, target_coord)
        self._sync_stage_for_coord(run, p, target_coord)
        return self._enter_room(run, uid, target_coord)

    def _room_display_label(self, room) -> str:
        if room.room_type == "landmark" and room.landmark_id:
            from ...data.grid_map_config import LANDMARK_CONFIGS
            lcfg = LANDMARK_CONFIGS.get(room.landmark_id, {})
            if lcfg.get("name_key"):
                return get_locale_text(lcfg["name_key"])
        return get_locale_text(f"i18n_grid_map.room_name.{room.room_type}")

    def list_teleportable_nodes(self, run) -> str:
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return get_locale_text("i18n_grid_map.err_no_floor_map")
        entries = []
        for c, r in fm.rooms.items():
            if not (r.explored or c in fm.revealed_coords):
                continue
            if r.room_type in ("wall", "obstacle"):
                continue
            if r.room_type == "secret_boss" and not fm.secret_unlocked:
                continue
            icon = ROOM_ICONS.get(r.room_type, "")
            entries.append(f"  {icon} {c} · {self._room_display_label(r)}")
        if not entries:
            return get_locale_text("i18n_grid_map.tp_list_empty")
        return get_locale_text("i18n_grid_map.tp_list_header", items="\n".join(entries))

    def _resolve_tp_target(self, fm, raw_target: str) -> str:
        from ..cli.base.pinyin_match import find_entry_by_query
        t = raw_target.strip()
        if not t:
            return ""
        upper = t.upper()
        if upper in fm.rooms:
            return upper
        alias_type = TP_TYPE_ALIASES.get(t.lower()) or TP_TYPE_ALIASES.get(t)
        if alias_type:
            for c, r in fm.rooms.items():
                if r.room_type == alias_type and (r.explored or c in fm.revealed_coords):
                    return c
        entries = []
        for c, r in fm.rooms.items():
            if not (r.explored or c in fm.revealed_coords):
                continue
            if r.room_type in ("wall", "obstacle") or (r.room_type == "secret_boss" and not fm.secret_unlocked):
                continue
            label = self._room_display_label(r)
            entries.append((c, label))
            type_name = get_locale_text(f"i18n_grid_map.room_name.{r.room_type}")
            if type_name != label:
                entries.append((c, type_name))
        return find_entry_by_query(entries, t) or ""
    def teleport_player(self, run, target: str) -> str:
        from ...renderer import GameRenderer
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return get_locale_text("i18n_grid_map.err_no_floor_map")
        uid = run.user_id
        if uid in fm.player_session_map:
            return get_locale_text("i18n_grid_map.err_in_session")
        fm.floor_flags.get("pending_obstacle", {}).pop(uid, None)
        coord = self._resolve_tp_target(fm, target)
        if not coord:
            return get_locale_text("i18n_grid_map.tp_not_found", target=target)
        room = fm.rooms.get(coord)
        if room is None:
            return get_locale_text("i18n_grid_map.tp_not_found", target=target)
        if not (room.explored or coord in fm.revealed_coords):
            return get_locale_text("i18n_grid_map.tp_unexplored", coord=coord)
        if room.room_type in ("wall", "obstacle") or (room.room_type == "secret_boss" and not fm.secret_unlocked):
            return get_locale_text("i18n_grid_map.tp_blocked", coord=coord)
        fm.player_coords[uid] = coord
        self._sync_stage_for_coord(run, run.player, coord)
        if room.room_type in PERMANENT_ICON_TYPES or not room.cleared:
            return self._enter_room(run, uid, coord)
        self.save_manager.save_save(uid, run)
        return f"{get_locale_text('i18n_grid_map.tp_success', coord=coord)}\n\n{GameRenderer.render_game(run)}"

    def _enter_room(self, run, uid: str, coord: str) -> str:
        from ...renderer import GameRenderer
        fm = run.floor_map
        room = fm.rooms[coord]
        p = run.player

        if room.room_type in ("empty", "spawn"):
            room.cleared = True
            self.save_manager.save_save(uid, run)
            return f"{get_locale_text('i18n_grid_map.moved_to', coord=coord)}\n\n{GameRenderer.render_game(run)}"

        if room.cleared and room.room_type not in PERMANENT_ICON_TYPES:
            self.save_manager.save_save(uid, run)
            return f"{get_locale_text('i18n_grid_map.moved_cleared', coord=coord)}\n\n{GameRenderer.render_game(run)}"

        if room.room_type == "corpse":
            corpse_id = room.shared_payload.get("corpse_id", "")
            corpse = self.save_manager.corpses.get(corpse_id) if corpse_id else None
            if not corpse or corpse.get("claimed_by"):
                room.room_type = "empty"
                room.cleared = True
                self.save_manager.save_save(uid, run)
                return f"{get_locale_text('i18n_grid_map.corpse_gone', coord=coord)}\n\n{GameRenderer.render_game(run)}"
            return self._start_or_prompt_battle(run, uid, coord, room, "ghost", corpse=corpse)

        if room.room_type in ("battle", "elite", "high_danger", "boss", "secret_boss"):
            if room.room_type == "high_danger" and not room.shared_payload.get("hazard_applied"):
                loss = max(HIGH_DANGER_CONFIG["hazard_hp_min"], int(p.max_hp * HIGH_DANGER_CONFIG["hazard_hp_ratio"]))
                p.hp = max(1, p.hp - loss)
                room.shared_payload["hazard_applied"] = True
                room.shared_payload["hazard_loss"] = loss
            diff = {
                "battle": "normal",
                "elite": "elite",
                "high_danger": "elite",
                "boss": "boss",
                "secret_boss": "secret_boss",
            }[room.room_type]
            return self._start_or_prompt_battle(run, uid, coord, room, diff)

        if room.room_type == "landmark":
            data = build_landmark_options(run, uid)
            SessionContextScoper.create_session(run, coord, "landmark", [uid], node_data=data)
            self.save_manager.save_save(uid, run)
            return GameRenderer.render_game(run)

        if room.room_type == "downstairs":
            data = build_downstairs_data(run)
            SessionContextScoper.create_session(run, coord, "downstairs", [uid], node_data=data)
            self.save_manager.save_save(uid, run)
            return GameRenderer.render_game(run)

        if room.room_type == "cafe":
            existing_sid = self._find_session_at(fm, coord, "cafe")
            if existing_sid:
                sess = fm.active_sessions[existing_sid]
                if uid not in sess.participants:
                    sess.participants.append(uid)
                    views = sess.node_data.setdefault("player_views", {})
                    shared_cafe = sess.node_data.get("coop_cafe", {})
                    views[uid] = {
                        "node_type": "cafe",
                        "data": {
                            "cafe_data": {"npcs": list(shared_cafe.get("npcs", [])), "active_npc": None, "dialog_state": None},
                            "coop_done": p.downed,
                        },
                    }
                    sess.node_data.setdefault("stage_ready", {})[uid] = p.downed
                fm.player_session_map[uid] = existing_sid
                SessionContextScoper.bind_to_run(run, uid)
                self.save_manager.save_save(uid, run)
                return GameRenderer.render_game(run)
            SessionContextScoper.create_session(run, coord, "cafe", [uid])
            from .cafe.engine import CafeEngine
            CafeEngine(self.save_manager, self.map_engine).init_cafe(run, persist=True, player_count=len(run.all_human_uids()))
            return GameRenderer.render_game(run)

        SessionContextScoper.create_session(run, coord, room.room_type, [uid])
        if room.room_type == "event":
            self.map_engine.explore_engine._init_event_node(run, event_id=room.shared_payload.get("event_id", ""))
        elif room.room_type == "shop":
            self.map_engine.explore_engine._init_shop_node(run, enter_lobby=True)
        elif room.room_type == "rest":
            self.map_engine.explore_engine._init_rest_node(run)
        elif room.room_type == "treasure":
            self.map_engine.explore_engine._init_treasure_node(run)
        elif room.room_type == "life_merchant":
            self.map_engine.explore_engine._init_life_merchant_node(run)
        self.save_manager.save_save(uid, run)
        return GameRenderer.render_game(run)

    def _find_session_at(self, fm, coord: str, node_type: str) -> str:
        for sid, sess in fm.active_sessions.items():
            if sess.coord == coord and sess.node_type == node_type:
                return sid
        return ""

    def _start_or_prompt_battle(self, run, uid: str, coord: str, room, difficulty: str, corpse: dict = None) -> str:
        from ...renderer import GameRenderer
        fm = run.floor_map
        existing_sid = self._find_session_at(fm, coord, "battle")
        if existing_sid:
            sess = fm.active_sessions[existing_sid]
            if uid not in sess.participants:
                sess.participants.append(uid)
            fm.player_session_map[uid] = existing_sid
            SessionContextScoper.bind_to_run(run, uid)
            self.save_manager.save_save(uid, run)
            return GameRenderer.render_game(run)

        idle = self.idle_teammates(run, exclude_uid=uid)
        if idle:
            teammate_names = "、".join(run.players[u].name for u in idle if u in run.players)
            node_data = {
                "coord": coord,
                "difficulty": difficulty,
                "room_type": room.room_type,
                "is_high_danger": room.is_high_danger,
                "hazard_loss": room.shared_payload.get("hazard_loss", 0),
                "corpse_id": room.shared_payload.get("corpse_id", ""),
                "idle_uids": idle,
                "options": [
                    {"action": "solo", "text": get_locale_text("i18n_grid_map.battle_prompt.opt_solo")},
                    {"action": "rally", "text": get_locale_text("i18n_grid_map.battle_prompt.opt_rally", count=len(idle), teammates=teammate_names)},
                    {"action": "retreat", "text": get_locale_text("i18n_grid_map.battle_prompt.opt_retreat")},
                ],
            }
            SessionContextScoper.create_session(run, coord, "battle_prompt", [uid], node_data=node_data)
            self.save_manager.save_save(uid, run)
            return GameRenderer.render_game(run)

        return self._launch_battle_session(run, coord, [uid], room, difficulty, corpse=corpse)

    def _launch_battle_session(self, run, coord: str, participants: list[str], room, difficulty: str, corpse: dict = None, include_render: bool = True) -> str:
        from ...renderer import GameRenderer
        fm = run.floor_map
        caller = run.user_id
        for u in participants:
            fm.player_coords[u] = coord
            if u in run.players:
                self._sync_stage_for_coord(run, run.players[u], coord)
        node_data = {}
        if room.is_high_danger or room.room_type == "high_danger":
            node_data["is_high_danger"] = True
        if room.room_type == "secret_boss":
            cfg = FLOOR_CONFIGS.get(fm.floor_index, FLOOR_CONFIGS[1])
            node_data["is_secret_boss"] = True
            node_data["secret_boss_name"] = cfg.get("secret_boss_name", "")
        if difficulty == "ghost" and corpse is not None:
            dead_name = str(corpse.get("player_name", get_locale_text("i18n_map_cafe.default_player_name")))
            cause = str(corpse.get("cause", get_locale_text("i18n_map_cafe.default_cause")))
            node_data.update({
                "corpse_battle": True,
                "corpse_id": corpse.get("id"),
                "corpse_stage": int(corpse.get("stage", run.player.stage)),
                "corpse_dead_name": dead_name,
                "corpse_cause": cause,
                "ghost_name": get_locale_text("i18n_map_cafe.ghost_name", dead_name=dead_name),
                "ghost_max_hp": max(CorpseConfig.GHOST_MIN_HP, int(corpse.get("max_hp", MAP_GHOST_DEFAULT_MAX_HP) or MAP_GHOST_DEFAULT_MAX_HP)),
                "ghost_deck": list(corpse.get("deck", [])),
            })
        SessionContextScoper.create_session(run, coord, "battle", participants, node_data=node_data)
        self.map_engine.battle_engine._init_battle_node(run, difficulty)
        self.save_manager.save_save(caller, run)
        from .rooms.interact import format_room_extras
        hazard_loss = room.shared_payload.get("hazard_loss", 0)
        intro_lines = []
        if hazard_loss > 0:
            intro_lines.append(get_locale_text("i18n_grid_map.high_danger_entry", loss=hazard_loss))
        if include_render:
            room_label = self._room_display_label(room)
            intro_lines.append(get_locale_text("i18n_room_interact.combat.room_entry_intro", label=room_label, coord=coord))
            intro_lines.extend(format_room_extras(run, include_env=True))
        prefix = ("\n".join(intro_lines) + "\n") if intro_lines else ""
        base_text = prefix + (GameRenderer.render_game(run) if include_render else "")
        return self.map_engine.battle_engine._append_logs_to_res(run, base_text.strip())

    def handle_battle_prompt(self, run, option_idx: int) -> str:
        from ...renderer import GameRenderer
        fm = run.floor_map
        uid = run.user_id
        sid = fm.player_session_map.get(uid, "")
        options = run.node_data.get("options", [])
        if option_idx < 1 or option_idx > len(options):
            return get_locale_text("err_invalid_option_idx")
        action = options[option_idx - 1].get("action", "")
        coord = run.node_data.get("coord", "")
        difficulty = run.node_data.get("difficulty", "normal")
        corpse_id = run.node_data.get("corpse_id", "")
        room = fm.rooms.get(coord)
        if action == "retreat" or room is None:
            SessionContextScoper.close_session(run, sid, mark_cleared=False)
            self.save_manager.save_save(uid, run)
            return get_locale_text("i18n_grid_map.battle_prompt.retreated")
        if action == "rally":
            idle = self.idle_teammates(run, exclude_uid=uid)
            participants = [uid] + idle
        else:
            participants = [uid]
        SessionContextScoper.close_session(run, sid, mark_cleared=False)
        corpse = self.save_manager.corpses.get(corpse_id) if corpse_id else None
        return self._launch_battle_session(run, coord, participants, room, difficulty, corpse=corpse, include_render=False)
