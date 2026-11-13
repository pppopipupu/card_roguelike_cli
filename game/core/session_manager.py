import uuid
from ..models.coop_view import apply_view, persist_view, scope_view
from ..models.state import EncounterSession


class SessionContextScoper:
    @staticmethod
    def ensure_full_party_order(run) -> list[str]:
        full = getattr(run, "_full_party_order", None)
        if not full:
            full = list(getattr(run, "party_order", []) or [])
            run._full_party_order = full
        return full

    @staticmethod
    def _expand_with_mercenaries(run, human_participants: list[str]) -> list[str]:
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
            run.party_order = list(full)
            return
        session = fm.active_sessions[sid]
        run.node_type = session.node_type
        run.enemies = session.enemies
        run.node_data = session.node_data
        scoped = [uid for uid in session.participants if uid in run.players]
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
            return
        persist_view(run, caller_uid)
        session = fm.active_sessions[sid]
        session.node_type = run.node_type
        session.enemies = run.enemies
        session.node_data = run.node_data

    @staticmethod
    def create_session(run, coord: str, node_type: str, participants: list[str], node_data: dict = None, enemies: list = None) -> EncounterSession:
        fm = run.floor_map
        expanded = SessionContextScoper._expand_with_mercenaries(run, participants)
        sid = f"sess_{uuid.uuid4().hex[:8]}"
        session = EncounterSession(
            session_id=sid,
            coord=coord,
            node_type=node_type,
            participants=expanded,
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
    def close_session(run, sid: str, mark_cleared: bool = True):
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return
        session = fm.active_sessions.pop(sid, None)
        if session is not None:
            for uid in list(session.participants):
                if fm.player_session_map.get(uid) == sid:
                    fm.player_session_map.pop(uid, None)
            if mark_cleared and session.coord and session.coord in fm.rooms:
                room = fm.rooms[session.coord]
                if room.room_type == "boss":
                    room.room_type = "downstairs"
                    room.cleared = False
                    room.explored = True
                elif room.room_type == "secret_boss":
                    room.cleared = True
                    room.explored = True
                    room.secret_unlocked = True
                else:
                    room.cleared = True
                    room.explored = True
        full = SessionContextScoper.ensure_full_party_order(run)
        run.party_order = list(full)
        run.node_type = "grid_map"
        run.enemies = []
        run.node_data = {}
