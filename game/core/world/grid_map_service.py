from ...data.battle.battle_mode_config import (
    BATTLE_MODE_FORCED_SOLO,
    BATTLE_MODE_SOLO,
    BATTLE_MODE_TEAM,
    resolve_battle_mode,
    session_battle_mode,
)
from ...data.entities.corpse_config import CorpseConfig
from ...data.world.event_data import TEAM_EVENT_IDS
from ...data.battle.team_config import TEAM_TP_SP_COST
from ...data.world.grid_map_config import (
    FLOOR_CONFIGS,
    HIGH_DANGER_CONFIG,
    PASSABLE_ROOM_TYPES,
    PERMANENT_ICON_TYPES,
    ROOM_ICONS,
    SP_CONFIG,
)
from ...data.text.locale_data import get_locale_text
from ...data.progression.balance_config import MAP_GHOST_DEFAULT_MAX_HP
from .grid_map_generator import coord_to_xy, xy_to_coord
from .landmark_system import build_landmark_options, ensure_descent_tunnel
from ..party.coordinator import apply_and_scope, restore_player, swap_player
from ..party.session import SessionContextScoper
from .rooms.big_room import (
    get_big_room,
    get_big_room_icon,
    get_big_room_name,
    reveal_big_room_if_needed,
    sync_big_room_clear_state,
)
from .rooms.hostile_npc import (
    ensure_room_hostile_npcs,
    ensure_treasure_chest_prop,
    get_alive_hostile_npcs,
    has_stealth_buff,
    resolve_room_true_sight_enemy,
    trigger_hostile_npc_battle,
)
from .persistent_buffs import break_map_invisibility
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
    "事件": "event",
    "event": "event",
}


class GridMapService:
    def __init__(self, save_manager, map_engine):
        self.save_manager = save_manager
        self.map_engine = map_engine

    def _reveal_coord(self, fm, coord: str):
        reveal_big_room_if_needed(fm, coord)

    def _format_map_output(self, run, log_text: str, in_queue: bool | None = None) -> str:
        from ...models.state import is_in_queue
        log = (log_text or "").strip()
        queued = is_in_queue(run) if in_queue is None else bool(in_queue)
        if queued:
            return log
        from ...renderer import GameRenderer
        rendered = GameRenderer.render_game(run)
        return f"{log}\n\n{rendered}" if log else rendered

    def _break_obstacle_and_enter(self, run, fm, uid: str, room, target_coord: str) -> str:
        from ...renderer import GameRenderer
        from .presence import sync_active
        p = run.player
        cost = max(1, int(room.obstacle_sp or SP_CONFIG["obstacle_cost_min"]))
        fm.floor_flags.setdefault("pending_obstacle", {}).pop(uid, None)
        if p.sp >= cost:
            consume_sp(p, cost, allow_overdraft=False)
            prefix = get_locale_text("i18n_grid_map.obstacle_cleared", coord=target_coord, cost=cost, sp=p.sp, max_sp=p.max_sp)
        else:
            sp_res = consume_sp(p, cost, allow_overdraft=True)
            hp_loss = SP_CONFIG["forced_obstacle_hp_loss"]
            p.hp = max(0, p.hp - hp_loss)
            if p.hp <= 0 or p.exhaustion >= 5:
                run.node_data["death_cause"] = get_locale_text("i18n_grid_map.exhaustion_death_cause")
                return self.save_manager.settle_game_and_delete(uid, run, is_victory=False, create_corpse=True)
            prefix = get_locale_text(
                "i18n_grid_map.obstacle_forced",
                coord=target_coord,
                hp_loss=hp_loss,
                sp=p.sp,
                exhaustion=sp_res["new_exhaustion"],
            )
        room.room_type = "empty"
        room.cleared = True
        room.obstacle_sp = 0
        fm.player_coords[uid] = target_coord
        self._reveal_coord(fm, target_coord)
        from .rooms.dialog.quest_hooks import record_npc_quest_event
        record_npc_quest_event(run, self.save_manager.load_stats(uid), "clear_obstacle", {"coord": target_coord}, save_manager=self.save_manager)
        broken_msg = break_map_invisibility(run, reason="interact", player=p)
        if broken_msg:
            prefix = f"{prefix}\n{broken_msg}"
        self.save_manager.save_save(uid, run)
        sync_active(uid, run=run)
        return self._format_map_output(run, prefix)

    def move_player(self, run, direction: str, dig: bool = False) -> str:
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
        from .bleak_falls import check_move_blocked_by_claw_door
        claw_blocked = check_move_blocked_by_claw_door(fm, cur, target_coord)
        if claw_blocked:
            return claw_blocked
        from .chireiden import check_move_blocked_by_chireiden_gate
        chireiden_blocked = check_move_blocked_by_chireiden_gate(fm, cur, target_coord)
        if chireiden_blocked:
            return chireiden_blocked
        if room is None or room.room_type in ("wall", "solid_wall") or (room.room_type == "secret_boss" and not fm.secret_unlocked):
            fm.floor_flags.get("pending_obstacle", {}).pop(uid, None)
            return get_locale_text("i18n_grid_map.err_blocked_wall")
        if room.locked:
            boss_room = fm.rooms.get(fm.boss_coord) if fm.boss_coord else None
            if not (boss_room is not None and boss_room.cleared):
                fm.floor_flags.get("pending_obstacle", {}).pop(uid, None)
                return get_locale_text("i18n_yog_quest.room_locked")

        p = run.player
        pending_map = fm.floor_flags.setdefault("pending_obstacle", {})
        if dig and room.room_type != "obstacle":
            pending_map.pop(uid, None)
            return get_locale_text("i18n_grid_map.err_not_obstacle", coord=target_coord)
        if room.room_type == "obstacle":
            if not dig:
                cost = max(1, int(room.obstacle_sp or SP_CONFIG["obstacle_cost_min"]))
                prev_pending = pending_map.get(uid)
                step = int(prev_pending.get("step", 0)) if (prev_pending and prev_pending.get("coord") == target_coord) else 0
                if step < 2:
                    from ...data.world.room_interact_data import OBSTACLE_STYLES
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
            return self._break_obstacle_and_enter(run, fm, uid, room, target_coord)
        was_explored = bool(room.explored)
        pending_map.pop(uid, None)
        fm.player_coords[uid] = target_coord
        self._reveal_coord(fm, target_coord)
        if not was_explored:
            from .map_quest_service import record_room_explored
            record_room_explored(run, self.save_manager.load_stats(uid), save_manager=self.save_manager)
        from .presence import sync_active
        sync_active(uid, run=run)
        return self._enter_room(run, uid, target_coord)

    def _update_quest_zone(self, run, room) -> None:
        from ...data.world.yog_quest_config import YOG_QUEST_ZONE_KEY
        if room.room_type == "boss":
            zone = 2
        elif room.landmark_id == "yog_necronomicon":
            zone = 3
        else:
            return
        stats = self.save_manager.load_stats(run.user_id)
        if stats.town_flags.get(YOG_QUEST_ZONE_KEY) == zone:
            return
        stats.town_flags[YOG_QUEST_ZONE_KEY] = zone
        self.save_manager.save_stats(run.user_id, stats)

    def _room_display_label(self, room, fm=None) -> str:
        if getattr(room, "big_room_id", "") and fm is not None:
            bname = get_big_room_name(fm, room)
            if bname:
                return bname
        shared = getattr(room, "shared_payload", None) or {}
        name_key = shared.get("name_key")
        if name_key:
            return get_locale_text(name_key)
        if room.room_type == "landmark" and room.landmark_id:
            from ...data.world.grid_map_config import LANDMARK_CONFIGS
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
            icon = get_big_room_icon(fm, r) if getattr(r, "big_room_id", "") else ROOM_ICONS.get(r.room_type, "")
            entries.append(f"  {icon} {c} · {self._room_display_label(r, fm=fm)}")
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
            if r.room_type in ("wall", "solid_wall", "obstacle") or (r.room_type == "secret_boss" and not fm.secret_unlocked):
                continue
            label = self._room_display_label(r, fm=fm)
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
        if room.room_type in ("wall", "solid_wall", "obstacle") or (room.room_type == "secret_boss" and not fm.secret_unlocked):
            return get_locale_text("i18n_grid_map.tp_blocked", coord=coord)
        fm.player_coords[uid] = coord
        self._reveal_coord(fm, coord)
        from .presence import sync_active
        sync_active(uid, run=run)
        if room.room_type in PERMANENT_ICON_TYPES or room.room_type == "big_room" or not room.cleared:
            return self._enter_room(run, uid, coord)
        self.save_manager.save_save(uid, run)
        return self._format_map_output(run, get_locale_text("i18n_grid_map.tp_success", coord=coord))

    def team_teleport_player(self, run, query: str) -> str:
        from ..cli.base.pinyin_match import find_entry_by_query
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return get_locale_text("i18n_social.team_teleport.no_floor_map")
        uid = run.user_id
        if uid in fm.player_session_map:
            return get_locale_text("i18n_social.team_teleport.in_session")
        p = run.player
        if p is None or getattr(p, "downed", False) or int(getattr(p, "hp", 0) or 0) <= 0:
            return get_locale_text("i18n_social.team_teleport.self_downed")
        raw = str(query or "").strip()
        if not raw:
            return get_locale_text("i18n_social.team_teleport.need_target")
        entries = []
        for pid in run.all_human_uids():
            pl = run.players.get(pid)
            if pl is None:
                continue
            entries.append((pid, pl.name))
            entries.append((pid, pid))
        target_uid = find_entry_by_query(entries, raw)
        if not target_uid:
            return get_locale_text("i18n_social.team_teleport.not_found", query=raw)
        if target_uid == uid:
            return get_locale_text("i18n_social.team_teleport.self")
        target = run.players.get(target_uid)
        if target is None:
            return get_locale_text("i18n_social.team_teleport.not_found", query=raw)
        if getattr(target, "downed", False) or int(getattr(target, "hp", 0) or 0) <= 0:
            return get_locale_text("i18n_social.team_teleport.target_downed", name=target.name)
        coord = fm.player_coords.get(target_uid, "")
        room = fm.rooms.get(coord) if coord else None
        if not coord or room is None:
            return get_locale_text("i18n_social.team_teleport.target_no_position", name=target.name)
        if room.room_type in ("wall", "solid_wall", "obstacle") or (room.room_type == "secret_boss" and not fm.secret_unlocked):
            return get_locale_text("i18n_social.team_teleport.target_blocked", name=target.name, coord=coord)
        if not (room.explored or coord in fm.revealed_coords):
            return get_locale_text("i18n_social.team_teleport.target_unexplored", name=target.name, coord=coord)
        target_sid = fm.player_session_map.get(target_uid)
        if target_sid and target_sid in fm.active_sessions:
            sess = fm.active_sessions[target_sid]
            sess_type = str(sess.get("node_type") or "") if isinstance(sess, dict) else str(getattr(sess, "node_type", "") or "")
            sess_data = (sess.get("node_data") or {}) if isinstance(sess, dict) else (getattr(sess, "node_data", {}) or {})
            if sess_type != "battle":
                return get_locale_text("i18n_social.team_teleport.target_in_session", name=target.name)
            if session_battle_mode(sess_data) == BATTLE_MODE_FORCED_SOLO:
                participants = list(sess.get("participants") or []) if isinstance(sess, dict) else list(getattr(sess, "participants", []) or [])
                owner = next(
                    (u for u in participants if not getattr(run.players.get(u), "is_mercenary", False)),
                    "",
                )
                owner_name = run.players[owner].name if owner in run.players else owner
                return get_locale_text("i18n_grid_map.battle_forced_solo_notice", name=owner_name, coord=coord)
        cost = int(TEAM_TP_SP_COST)
        current_sp = int(getattr(p, "sp", 0) or 0)
        if current_sp < cost:
            return get_locale_text("i18n_social.team_teleport.no_sp", cost=cost, sp=current_sp)
        consume_sp(p, cost, allow_overdraft=False)
        result = self.teleport_player(run, coord)
        self.save_manager.save_save(uid, run)
        prefix = get_locale_text(
            "i18n_social.team_teleport.success",
            name=target.name,
            coord=coord,
            cost=cost,
        )
        return f"{prefix}\n{result}"

    def _enter_room(self, run, uid: str, coord: str) -> str:
        from .rooms.forced_triggers import run_forced_triggers
        fm = run.floor_map
        room = fm.rooms[coord]
        trigger_logs = run_forced_triggers(run, fm, room, "on_enter")
        res = self._enter_room_body(run, uid, coord)
        if not trigger_logs:
            return res
        self.save_manager.save_save(uid, run)
        prefix = "\n".join(trigger_logs)
        return f"{prefix}\n\n{res}"

    def _enter_room_body(self, run, uid: str, coord: str) -> str:
        from ...renderer import GameRenderer
        from ...data.world.room_interact_data import ROOM_NPCS
        fm = run.floor_map
        room = fm.rooms[coord]
        p = run.player
        forced_solo_block = self._forced_solo_battle_block(run, uid, coord)
        if forced_solo_block:
            self.save_manager.save_save(uid, run)
            return forced_solo_block
        if fm.floor_flags.get("yog_quest"):
            self._update_quest_zone(run, room)

        ensure_room_hostile_npcs(fm, room)
        ensure_treasure_chest_prop(room)
        if getattr(room, "npcs", None):
            from .encounter_lore import record_encounter_for_run

            record_encounter_for_run(self.save_manager, run, *room.npcs)

        if room.room_type in ("empty", "spawn"):
            room.cleared = True
            self.save_manager.save_save(uid, run)
            return self._format_map_output(run, get_locale_text("i18n_grid_map.moved_to", coord=coord))

        alive_hostiles = get_alive_hostile_npcs(fm, room)
        if alive_hostiles:
            if has_stealth_buff(p):
                hid = alive_hostiles[0]
                true_sight_enemy = resolve_room_true_sight_enemy(fm, room, hid, p)
                if true_sight_enemy:
                    break_map_invisibility(run, reason="battle", player=p)
                    pierce_notice = get_locale_text("i18n_buffs.invisibility_true_sight_ambush_notice", enemy=true_sight_enemy)
                    res_text = trigger_hostile_npc_battle(self, run, uid, coord, room, hid)
                    return f"{pierce_notice}\n{res_text}"
                ncfg = ROOM_NPCS.get(hid, {})
                nname = get_locale_text(ncfg["name_key"]) if ncfg.get("name_key") else hid
                notice = get_locale_text("i18n_big_room.ui.stealth_bypass_notice", npc=nname)
                self.save_manager.save_save(uid, run)
                return self._format_map_output(run, notice)
            return trigger_hostile_npc_battle(self, run, uid, coord, room, alive_hostiles[0])

        existing_battle_sid = self._find_session_at(fm, coord, "battle")
        if existing_battle_sid and not has_stealth_buff(p):
            sess = fm.active_sessions[existing_battle_sid]
            if session_battle_mode(sess.node_data) != BATTLE_MODE_FORCED_SOLO and uid not in sess.participants:
                return self._join_battle_session(run, uid, coord, existing_battle_sid)

        if room.room_type == "big_room":
            if "treasure_chest" not in room.props or "treasure_chest" in room.interacted_props:
                room.cleared = True
            sync_big_room_clear_state(fm, room)
            self.save_manager.save_save(uid, run)
            return self._format_map_output(run, get_locale_text("i18n_grid_map.moved_to", coord=coord))

        if room.room_type == "treasure":
            self.save_manager.save_save(uid, run)
            return self._format_map_output(run, get_locale_text("i18n_grid_map.moved_to", coord=coord))

        if room.cleared and room.room_type not in PERMANENT_ICON_TYPES:
            self.save_manager.save_save(uid, run)
            return self._format_map_output(run, get_locale_text("i18n_grid_map.moved_cleared", coord=coord))

        from ...models.state import is_in_queue
        in_queue = is_in_queue(run)
        if room.room_type == "landmark":
            broken_msg = break_map_invisibility(run, reason="interact", player=p)
            data = build_landmark_options(run, uid)
            SessionContextScoper.create_session(run, coord, "landmark", [uid], node_data=data)
            self.save_manager.save_save(uid, run)
            if in_queue:
                return "\n".join(x for x in (get_locale_text("i18n_grid_map.moved_to", coord=coord), broken_msg) if x)
            rendered = GameRenderer.render_game(run)
            return f"{broken_msg}\n\n{rendered}" if broken_msg else rendered

        if room.room_type == "downstairs":
            ensure_descent_tunnel(room)
            self.save_manager.save_save(uid, run)
            return self._format_map_output(run, get_locale_text("i18n_grid_map.moved_to", coord=coord))

        from .bleak_falls import BLEAK_LANDMARK_TYPES
        if room.room_type in BLEAK_LANDMARK_TYPES:
            self.save_manager.save_save(uid, run)
            return self._format_map_output(run, get_locale_text("i18n_grid_map.moved_to", coord=coord))

        if room.room_type == "cafe":
            from .cafe.engine import CafeEngine
            CafeEngine(self.save_manager, self.map_engine).ensure_cafe_room(run, room)
            room.cleared = True
            self.save_manager.save_save(uid, run)
            return self._format_map_output(run, get_locale_text("i18n_grid_map.moved_to", coord=coord))

        broken_msg = break_map_invisibility(run, reason="interact", player=p)
        if room.room_type == "event":
            event = self.map_engine.explore_engine.resolve_event(run, str(room.shared_payload.get("event_id", "")))
            participants = [uid]
            if event.id in TEAM_EVENT_IDS:
                participants = self._team_participants(run, uid)
                self._move_participants_to(run, coord, participants)
            SessionContextScoper.create_session(run, coord, room.room_type, participants)
            self.map_engine.explore_engine._init_event_node(run, event=event)
        else:
            SessionContextScoper.create_session(run, coord, room.room_type, [uid])
            if room.room_type == "shop":
                self.map_engine.explore_engine._init_shop_node(run, enter_lobby=True)
            elif room.room_type == "rest":
                self.map_engine.explore_engine._init_rest_node(run)
            elif room.room_type == "treasure":
                bonus_item = room.shared_payload.pop("bonus_item", "")
                if bonus_item:
                    from ..inventory.bag_service import add_bag_item
                    ok, _ = add_bag_item(run.player, bonus_item)
                    if not ok and bonus_item not in room.items:
                        room.items.append(bonus_item)
                self.map_engine.explore_engine._init_treasure_node(run)
            elif room.room_type == "life_merchant":
                self.map_engine.explore_engine._init_life_merchant_node(run)
        self.save_manager.save_save(uid, run)
        if in_queue:
            return "\n".join(x for x in (get_locale_text("i18n_grid_map.moved_to", coord=coord), broken_msg) if x)
        rendered = GameRenderer.render_game(run)
        return f"{broken_msg}\n\n{rendered}" if broken_msg else rendered

    def _find_session_at(self, fm, coord: str, node_type: str) -> str:
        br = get_big_room(fm, coord)
        for sid, sess in fm.active_sessions.items():
            if sess.node_type != node_type:
                continue
            if sess.coord == coord:
                return sid
            if br is not None and br.share_npcs and sess.coord in br.cells:
                return sid
        return ""

    def _forced_solo_battle_block(self, run, uid: str, coord: str) -> str:
        fm = run.floor_map
        if fm is None:
            return ""
        existing_sid = self._find_session_at(fm, coord, "battle")
        if not existing_sid:
            return ""
        sess = fm.active_sessions[existing_sid]
        if session_battle_mode(sess.node_data) != BATTLE_MODE_FORCED_SOLO:
            return ""
        if uid in sess.participants:
            return ""
        owner = next(
            (u for u in sess.participants if not getattr(run.players.get(u), "is_mercenary", False)),
            "",
        )
        owner_name = run.players[owner].name if owner in run.players else owner
        notice = get_locale_text("i18n_grid_map.battle_forced_solo_notice", name=owner_name, coord=coord)
        return self._format_map_output(run, notice)

    def _team_participants(self, run, coordinator_uid: str) -> list[str]:
        fm = run.floor_map
        participants = []
        for uid in run.all_human_uids():
            player = run.players.get(uid)
            if player is None:
                continue
            if uid != coordinator_uid:
                if player.downed or player.hp <= 0:
                    continue
                if uid in fm.player_session_map:
                    continue
            participants.append(uid)
        if coordinator_uid in run.players and coordinator_uid not in participants:
            participants.append(coordinator_uid)
        return participants

    def _move_participants_to(self, run, coord: str, participants: list[str]):
        from .presence import sync_active
        fm = run.floor_map
        for uid in participants:
            fm.player_coords[uid] = coord
            player = run.players.get(uid)
            if player is None:
                continue
            if not getattr(player, "is_mercenary", False):
                sync_active(uid, run=run)

    def _join_battle_session(self, run, uid: str, coord: str, existing_sid: str) -> str:
        from .presence import sync_active
        from ...models.state import is_in_queue
        in_queue = is_in_queue(run)
        fm = run.floor_map
        sess = fm.active_sessions[existing_sid]
        if session_battle_mode(sess.node_data) == BATTLE_MODE_FORCED_SOLO and uid not in sess.participants:
            return self._forced_solo_battle_block(run, uid, coord)
        joined = uid not in sess.participants
        new_members = SessionContextScoper.expand_with_mercenaries(run, [uid]) if joined else []
        for member in new_members:
            if member not in sess.participants:
                sess.participants.append(member)
            if member not in sess.roster:
                sess.roster.append(member)
            fm.player_coords[member] = coord
            player = run.players.get(member)
            if player is not None:
                sync_active(member, run=run)
            fm.player_session_map[member] = existing_sid
        fm.player_session_map[uid] = existing_sid
        SessionContextScoper.bind_to_run(run, uid)
        for member in new_members:
            self.map_engine.battle_engine.join_battle(run, member)
        self.save_manager.save_save(uid, run)
        join_msg = get_locale_text("i18n_grid_map.battle_joined", coord=coord) if joined else ""
        return self._format_map_output(run, join_msg, in_queue=in_queue)

    def _start_battle(self, run, uid: str, coord: str, room, difficulty: str, corpse: dict | None = None, hostile_npc_id: str = "", battle_mode: str = "") -> str:
        fm = run.floor_map
        mode = battle_mode or resolve_battle_mode(getattr(room, "room_type", ""), difficulty)
        existing_sid = self._find_session_at(fm, coord, "battle")
        if existing_sid:
            return self._join_battle_session(run, uid, coord, existing_sid)

        if mode == BATTLE_MODE_SOLO:
            from .ally_summon import maybe_open_summon_select
            prompt = maybe_open_summon_select(
                self,
                run,
                uid,
                coord,
                room,
                difficulty,
                corpse,
                hostile_npc_id,
                mode,
            )
            if prompt is not None:
                return prompt

        participants = [uid]
        if mode == BATTLE_MODE_TEAM:
            participants = self._team_participants(run, uid)
        return self._launch_battle_session(
            run,
            coord,
            participants,
            room,
            difficulty,
            corpse=corpse,
            hostile_npc_id=hostile_npc_id,
            battle_mode=mode,
        )

    def _launch_battle_session(self, run, coord: str, participants: list[str], room, difficulty: str, corpse: dict | None = None, include_render: bool = True, hostile_npc_id: str = "", battle_mode: str = BATTLE_MODE_SOLO) -> str:
        from ...renderer import GameRenderer
        from ...models.state import is_in_queue
        in_queue = is_in_queue(run)
        fm = run.floor_map
        caller = run.user_id
        self._move_participants_to(run, coord, participants)
        node_data: dict = {"battle_mode": battle_mode}
        if hostile_npc_id:
            node_data["hostile_npc_id"] = hostile_npc_id
        preset_boss = str(room.shared_payload.get("preset_boss_name") or "")
        if preset_boss:
            node_data["preset_boss_name"] = preset_boss
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
                "corpse_floor": corpse.get("floor", fm.floor_index),
                "corpse_dead_name": dead_name,
                "corpse_cause": cause,
                "ghost_name": get_locale_text("i18n_map_cafe.ghost_name", dead_name=dead_name),
                "ghost_max_hp": max(CorpseConfig.GHOST_MIN_HP, int(corpse.get("max_hp", MAP_GHOST_DEFAULT_MAX_HP) or MAP_GHOST_DEFAULT_MAX_HP)),
                "ghost_deck": list(corpse.get("deck", [])),
            })
        SessionContextScoper.create_session(run, coord, "battle", participants, node_data=node_data)
        self.map_engine.battle_engine._init_battle_node(run, difficulty)
        if room.shared_payload.get("yog_encounter"):
            from .yog_quest.floor import apply_quest_encounter
            apply_quest_encounter(run, room)
            self.map_engine.battle_engine.enemy_controller.roll_enemy_intent(run)
        elif fm.floor_flags.get("bleak_falls_zone"):
            from .bleak_falls import apply_bleak_falls_encounter
            apply_bleak_falls_encounter(self.map_engine.battle_engine, run, room)
        elif fm.floor_flags.get("chireiden_zone"):
            from .chireiden import apply_chireiden_encounter
            apply_chireiden_encounter(self.map_engine.battle_engine, run, room)
        elif fm.floor_flags.get("tutorial_zone"):
            from .tutorial import apply_tutorial_encounter
            apply_tutorial_encounter(self.map_engine.battle_engine, run, room)
        self.save_manager.save_save(caller, run)
        from .rooms.interact import format_room_extras
        hazard_loss = room.shared_payload.get("hazard_loss", 0)
        intro_lines = []
        if hazard_loss > 0:
            intro_lines.append(get_locale_text("i18n_grid_map.high_danger_entry", loss=hazard_loss))
        if include_render:
            room_label = self._room_display_label(room, fm=fm)
            intro_lines.append(get_locale_text("i18n_room_interact.combat.room_entry_intro", label=room_label, coord=coord))
            intro_lines.extend(format_room_extras(run, include_env=True))
        log_text = self.map_engine.battle_engine._append_logs_to_res(run, "\n".join(intro_lines).strip()).strip()
        if not include_render or in_queue:
            return log_text
        rendered = GameRenderer.render_game(run)
        return f"{log_text}\n{rendered}" if log_text else rendered
