import uuid
from ...models.coop_view import apply_view, persist_view, scope_view
from ...models.state import EncounterSession


class SessionContextScoper:
    @staticmethod
    def ensure_full_party_order(run) -> list[str]:
        full = getattr(run, "_full_party_order", None)
        if not full:
            full = list(getattr(run, "party_order", []) or [])
            run._full_party_order = full
        return full

    @staticmethod
    def expand_with_mercenaries(run, human_participants: list[str]) -> list[str]:
        full = SessionContextScoper.ensure_full_party_order(run)
        result = []
        human_set = set(human_participants)
        for uid in full:
            p = run.players.get(uid)
            if p is None:
                continue
            if getattr(p, "is_mercenary", False):
                if getattr(p, "mercenary_owner", "") in human_set:
                    result.append(uid)
            elif uid in human_set:
                result.append(uid)
        for uid in human_participants:
            if uid in run.players and uid not in result:
                result.append(uid)
        return result

    @staticmethod
    def bind_to_run(run, caller_uid: str):
        if run is None:
            return
        full = SessionContextScoper.ensure_full_party_order(run)
        if caller_uid in run.players:
            run.player = run.players[caller_uid]
            run.user_id = caller_uid
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return
        sid = fm.player_session_map.get(caller_uid)
        if not sid or sid not in fm.active_sessions:
            if sid:
                fm.player_session_map.pop(caller_uid, None)
            run.node_type = "grid_map"
            run.enemies = []
            run.node_data = {}
            md = (fm.floor_flags or {}).get("merc_dialogs")
            if isinstance(md, dict) and md:
                run.node_data["merc_dialogs"] = md
            gn = (fm.floor_flags or {}).get("grid_notices")
            if isinstance(gn, dict):
                uid_notice = gn.get(caller_uid)
                if uid_notice:
                    run.node_data["notice"] = uid_notice
            run.party_order = list(full)
            return
        session = fm.active_sessions[sid]
        run.node_type = session.node_type
        run.enemies = session.enemies
        run.node_data = session.node_data
        roster = session.roster or session.participants
        scoped = [uid for uid in roster if uid in run.players]
        if scoped:
            run.party_order = scoped
        apply_view(run, caller_uid)
        scope_view(run, caller_uid)

    @staticmethod
    def sync_from_run(run, caller_uid: str):
        if run is None:
            return
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return
        sid = fm.player_session_map.get(caller_uid)
        if not sid or sid not in fm.active_sessions:
            md = (run.node_data or {}).get("merc_dialogs")
            if isinstance(md, dict) and md:
                fm.floor_flags["merc_dialogs"] = md
            else:
                fm.floor_flags.pop("merc_dialogs", None)
            notice = (run.node_data or {}).get("notice")
            gn = fm.floor_flags.get("grid_notices")
            if notice:
                if not isinstance(gn, dict):
                    gn = {}
                    fm.floor_flags["grid_notices"] = gn
                gn[caller_uid] = notice
            elif isinstance(gn, dict):
                gn.pop(caller_uid, None)
                if not gn:
                    fm.floor_flags.pop("grid_notices", None)
            return
        persist_view(run, caller_uid)
        session = fm.active_sessions[sid]
        session.node_type = run.node_type
        session.enemies = run.enemies
        session.node_data = run.node_data

    @staticmethod
    def create_session(run, coord: str, node_type: str, participants: list[str], node_data: dict | None = None, enemies: list | None = None) -> EncounterSession:
        fm = run.floor_map
        expanded = SessionContextScoper.expand_with_mercenaries(run, participants)
        sid = f"sess_{uuid.uuid4().hex[:8]}"
        session = EncounterSession(
            session_id=sid,
            coord=coord,
            node_type=node_type,
            participants=list(expanded),
            roster=list(expanded),
            enemies=list(enemies) if enemies is not None else [],
            node_data=dict(node_data) if node_data is not None else {},
            status="active",
        )
        fm.active_sessions[sid] = session
        for uid in expanded:
            fm.player_session_map[uid] = sid
        SessionContextScoper.bind_to_run(run, run.user_id)
        return session

    @staticmethod
    def _mark_room_cleared(run, session) -> dict:
        fm = getattr(run, "floor_map", None)
        pending = {}
        if fm is None or session is None or session.status == "cleared":
            return pending
        if not session.coord or session.coord not in fm.rooms:
            return pending
        room = fm.rooms[session.coord]
        was_bleak_combat = bool(
            fm.floor_flags.get("bleak_falls_zone")
            or run.node_data.get("bleak_falls_combat_tag")
        )
        was_chireiden_combat = bool(
            fm.floor_flags.get("chireiden_zone")
            and (
                room.shared_payload.get("chireiden_combat_tag")
                or room.room_type in ("battle", "elite", "high_danger", "boss")
            )
        )
        if room.room_type == "boss":
            from ..world.rooms.big_room import mark_effective_npc_defeated
            hostile_id = str((session.node_data or {}).get("hostile_npc_id") or "") or "floor_boss"
            mark_effective_npc_defeated(fm, room, hostile_id)
            if hostile_id in room.npcs:
                room.npcs.remove(hostile_id)
            if fm.floor_flags.get("yog_quest") or fm.floor_flags.get("bleak_falls_zone") or fm.floor_flags.get("chireiden_zone"):
                room.cleared = True
                room.explored = True
            else:
                floor_idx = getattr(fm, "floor_index", 1)
                room.room_type = "downstairs"
                room.cleared = False
                room.explored = True
                from ..world.landmark_system import ensure_descent_tunnel
                ensure_descent_tunnel(room)
                if floor_idx == 1:
                    pending["bleak_falls_pending_floor1_boss"] = room.coord
            if was_bleak_combat:
                pending["bleak_falls_pending_clear"] = room.coord
            if was_chireiden_combat:
                pending["chireiden_pending_clear"] = room.coord
        elif room.room_type == "secret_boss":
            from ..world.rooms.big_room import mark_effective_npc_defeated
            hostile_id = str((session.node_data or {}).get("hostile_npc_id") or "") or "secret_boss_avatar"
            mark_effective_npc_defeated(fm, room, hostile_id)
            room.cleared = True
            room.explored = True
            room.secret_unlocked = True
        else:
            from ..world.rooms.big_room import get_big_room, mark_effective_npc_defeated, sync_big_room_clear_state
            from ..world.rooms.hostile_npc import get_alive_hostile_npcs
            hostile_id = str((session.node_data or {}).get("hostile_npc_id") or "")
            if hostile_id:
                mark_effective_npc_defeated(fm, room, hostile_id)
            elif session.node_type == "battle":
                for hid in list(get_alive_hostile_npcs(fm, room)):
                    mark_effective_npc_defeated(fm, room, hid)
            remaining_hostiles = get_alive_hostile_npcs(fm, room)
            br = get_big_room(fm, room)
            if not remaining_hostiles:
                room.cleared = True
                if br is not None and br.share_npcs and session.node_type == "battle":
                    br.cleared = True
                    for cell_c in br.cells:
                        if cell_c in fm.rooms:
                            fm.rooms[cell_c].cleared = True
            room.explored = True
            if br is not None:
                sync_big_room_clear_state(fm, room)
            if was_bleak_combat:
                pending["bleak_falls_pending_clear"] = room.coord
            if was_chireiden_combat:
                pending["chireiden_pending_clear"] = room.coord
        session.status = "cleared"
        if "bleak_falls_pending_clear" in pending:
            combat_tag = run.node_data.get("bleak_falls_combat_tag", "")
            if combat_tag:
                pending["bleak_falls_combat_tag"] = combat_tag
        return pending

    @staticmethod
    def _reset_run_to_grid(run, pending: dict | None = None):
        full = SessionContextScoper.ensure_full_party_order(run)
        run.party_order = list(full)
        run.node_type = "grid_map"
        run.enemies = []
        run.node_data = dict(pending) if pending else {}

    @staticmethod
    def leave_session(run, uids: list[str], mark_cleared: bool = True) -> bool:
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return True
        sid = ""
        for uid in uids:
            sid = fm.player_session_map.get(uid, "")
            if sid:
                break
        session = fm.active_sessions.get(sid) if sid else None
        if session is None:
            for uid in list(uids):
                if sid and fm.player_session_map.get(uid) == sid:
                    fm.player_session_map.pop(uid, None)
            SessionContextScoper._reset_run_to_grid(run)
            return True
        for uid in list(uids):
            if uid in session.participants:
                session.participants.remove(uid)
            if fm.player_session_map.get(uid) == sid:
                fm.player_session_map.pop(uid, None)
        remaining = [
            uid
            for uid in session.participants
            if uid in run.players and not getattr(run.players[uid], "is_mercenary", False)
        ]
        if not remaining:
            SessionContextScoper.close_session(run, sid, mark_cleared=mark_cleared)
            return True
        pending = SessionContextScoper._mark_room_cleared(run, session) if mark_cleared else {}
        SessionContextScoper._reset_run_to_grid(run, pending)
        return False

    @staticmethod
    def close_session(run, sid: str, mark_cleared: bool = True):
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return
        pending = {}
        session = fm.active_sessions.pop(sid, None)
        if session is not None:
            for uid in list(session.participants):
                if fm.player_session_map.get(uid) == sid:
                    fm.player_session_map.pop(uid, None)
            if mark_cleared:
                pending = SessionContextScoper._mark_room_cleared(run, session)
        if "merc_utsuho" in run.players or "merc_utsuho" in run.party_order:
            from ..world.chireiden import cleanup_utsuho_ally
            cleanup_utsuho_ally(run)
        SessionContextScoper._reset_run_to_grid(run, pending)
