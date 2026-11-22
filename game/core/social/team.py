import random
import string
from typing import TYPE_CHECKING, Optional, Dict

from ...data.progression.checkin_data import (
    LOBBY_ID_LENGTH,
    TEAM_MAX_MEMBERS,
    TEAM_MIN_PLAYERS,
)
from ...data.text.locale_data import get_locale_text


if TYPE_CHECKING:
    from ...models.manager import SaveManager
    from ...models.records import Lobby, PlayerProfile
    from ...models.state import UserStats
    from ...engine import GameEngine


class SocialTeamMixin:
    if TYPE_CHECKING:
        save_manager: SaveManager
        engine: Optional[GameEngine]

        def _now(self) -> str: ...

        def _stats(self, uid: str) -> UserStats: ...

        def _profile(self, uid: str) -> Dict[str, str]: ...

        def _find_profile(self, query) -> Optional[PlayerProfile]: ...

        def _class_text(self, stats: UserStats) -> str: ...
    def _lobby_of(self, uid) -> Optional[Lobby]:
        stats = self._stats(uid)
        lobby_id = getattr(stats, "active_lobby_id", "")
        if not lobby_id:
            return None
        lobby = self.save_manager.get_lobby(lobby_id)
        if not lobby:
            stats.active_lobby_id = ""
            self.save_manager.save_stats(uid, stats)
            return None
        return lobby

    def _lobby_status(self, lobby):
        members = lobby.get("members", [])
        ready = lobby.get("ready", {})
        leader_id = lobby.get("leader_id", "")
        lines = [
            get_locale_text(
                "i18n_social.lobby_status.header",
                lobby_id=lobby.get("lobby_id"),
                leader=self._profile(leader_id)["name"],
            )
        ]
        for member_uid in members:
            profile = self._profile(member_uid)
            marker = get_locale_text("i18n_social.lobby_status.leader_marker") if member_uid == leader_id else ""
            ready_text = (
                get_locale_text("i18n_social.lobby_status.ready")
                if ready.get(member_uid)
                else get_locale_text("i18n_social.lobby_status.not_ready")
            )
            lines.append(
                get_locale_text(
                    "i18n_social.lobby_status.member_entry",
                    name=profile["name"],
                    marker=marker,
                    class_text=self._class_text(self._stats(member_uid)),
                    ready_text=ready_text,
                )
            )
        invited = lobby.get("invited", [])
        if invited:
            separator = get_locale_text("i18n_social.common.list_separator")
            names = separator.join(self._profile(member_uid)["name"] for member_uid in invited)
            lines.append(get_locale_text("i18n_social.lobby_status.invited", names=names))
        lines.append(
            get_locale_text(
                "i18n_social.lobby_status.member_count",
                count=len(members),
                max_members=TEAM_MAX_MEMBERS,
            )
        )
        if len(members) >= 2:
            lines.append(get_locale_text("i18n_social.lobby_status.quest_hint"))
        return "\n".join(lines)

    def team_create(self, uid):
        stats = self._stats(uid)
        lobby = self._lobby_of(uid)
        if lobby:
            return get_locale_text(
                "i18n_social.team_create.already_in_team",
                lobby_id=lobby.get("lobby_id"),
                lobby_status=self._lobby_status(lobby),
            )
        if getattr(stats, "active_coop_id", ""):
            return get_locale_text("i18n_social.team_create.in_coop")
        if self.save_manager.has_personal_save(uid):
            return get_locale_text("i18n_social.team_create.personal_save")
        lobby_id = self._new_lobby_id()
        new_lobby: Lobby = {
            "lobby_id": lobby_id,
            "leader_id": uid,
            "members": [uid],
            "invited": [],
            "ready": {uid: True},
            "created_at": self._now(),
        }
        self.save_manager.save_lobby(new_lobby)
        stats.active_lobby_id = lobby_id
        self.save_manager.save_stats(uid, stats)
        return get_locale_text(
            "i18n_social.team_create.success",
            lobby_id=lobby_id,
            lobby_status=self._lobby_status(new_lobby),
        )

    def _new_lobby_id(self):
        while True:
            lobby_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=LOBBY_ID_LENGTH))
            if not self.save_manager.get_lobby(lobby_id):
                return lobby_id

    def team_invite(self, uid, query):
        lobby = self._lobby_of(uid)
        if not lobby:
            return get_locale_text("i18n_social.team_invite.no_team")
        if lobby.get("leader_id") != uid:
            return get_locale_text("i18n_social.team_invite.not_leader")
        if getattr(self._stats(uid), "active_coop_id", ""):
            return get_locale_text("i18n_social.team_invite.in_coop")
        target = self._find_profile(query)
        if not target:
            return get_locale_text("i18n_social.common.player_not_found", query=query)
        target_uid = target.user_id
        if target_uid == uid:
            return get_locale_text("i18n_social.team_invite.self")
        leader_stats = self._stats(uid)
        if target_uid not in leader_stats.friends:
            return get_locale_text("i18n_social.team_invite.not_friend", name=target.name)
        if target_uid in lobby.get("members", []):
            return get_locale_text("i18n_social.team_invite.already_member", name=target.name)
        if target_uid in lobby.get("invited", []):
            return get_locale_text("i18n_social.team_invite.already_invited", name=target.name)
        if len(lobby.get("members", [])) + len(lobby.get("invited", [])) >= TEAM_MAX_MEMBERS:
            return get_locale_text("i18n_social.team_invite.full", max_members=TEAM_MAX_MEMBERS)
        target_stats = self._stats(target_uid)
        if getattr(target_stats, "active_coop_id", ""):
            return get_locale_text("i18n_social.team_invite.target_in_coop", name=target.name)
        lobby.setdefault("invited", []).append(target_uid)
        self.save_manager.save_lobby(lobby)
        return get_locale_text(
            "i18n_social.team_invite.success",
            name=target.name,
            lobby_id=lobby.get("lobby_id"),
        )

    def team_invites(self, uid):
        lobbies = self.save_manager.load_lobbies()
        lines = []
        for lobby in lobbies.values():
            if uid in lobby.get("invited", []):
                leader = self._profile(lobby.get("leader_id", ""))
                lines.append(
                    get_locale_text(
                        "i18n_social.team_invites.entry",
                        lobby_id=lobby.get("lobby_id"),
                        leader=leader["name"],
                        count=len(lobby.get("members", [])),
                        max_members=TEAM_MAX_MEMBERS,
                    )
                )
        if not lines:
            return get_locale_text("i18n_social.team_invites.empty")
        return (
            get_locale_text("i18n_social.team_invites.header")
            + "\n"
            + "\n".join(lines)
            + "\n"
            + get_locale_text("i18n_social.team_invites.hint")
        )

    def team_join(self, uid, lobby_id):
        if not lobby_id:
            lobbies = [
                lobby for lobby in self.save_manager.load_lobbies().values()
                if uid in lobby.get("invited", [])
            ]
            if len(lobbies) == 1:
                lobby_id = lobbies[0].get("lobby_id")
            else:
                return get_locale_text("i18n_social.team_join.need_id")
        lobby = self.save_manager.get_lobby(str(lobby_id).upper())
        if not lobby:
            return get_locale_text("i18n_social.team_join.not_found", lobby_id=lobby_id)
        if uid not in lobby.get("invited", []):
            return get_locale_text("i18n_social.team_join.not_invited")
        if uid in lobby.get("members", []):
            return get_locale_text("i18n_social.team_join.already_member")
        stats = self._stats(uid)
        if getattr(stats, "active_coop_id", ""):
            return get_locale_text("i18n_social.team_join.in_coop")
        current_lobby = self._lobby_of(uid)
        if current_lobby and current_lobby.get("lobby_id") != lobby.get("lobby_id"):
            return get_locale_text("i18n_social.team_join.already_in_other", lobby_id=current_lobby.get("lobby_id"))
        if self.save_manager.has_personal_save(uid):
            return get_locale_text("i18n_social.team_join.personal_save")
        if len(lobby.get("members", [])) >= TEAM_MAX_MEMBERS:
            return get_locale_text("i18n_social.team_join.full")
        lobby.setdefault("members", []).append(uid)
        lobby.setdefault("ready", {})[uid] = False
        lobby["invited"] = [item for item in lobby.get("invited", []) if item != uid]
        self.save_manager.save_lobby(lobby)
        stats.active_lobby_id = str(lobby.get("lobby_id") or "")
        self.save_manager.save_stats(uid, stats)
        return get_locale_text(
            "i18n_social.team_join.success",
            lobby_id=lobby.get("lobby_id"),
            lobby_status=self._lobby_status(lobby),
        )

    def team_leave(self, uid):
        lobby = self._lobby_of(uid)
        if not lobby:
            return get_locale_text("i18n_social.common.not_in_team")
        lobby_id = lobby.get("lobby_id")
        stats = self._stats(uid)
        if uid in lobby.get("members", []) and getattr(stats, "active_coop_id", ""):
            return get_locale_text("i18n_social.team_leave.in_coop")
        if uid not in lobby.get("members", []):
            lobby["invited"] = [item for item in lobby.get("invited", []) if item != uid]
            self.save_manager.save_lobby(lobby)
            stats = self._stats(uid)
            stats.active_lobby_id = ""
            self.save_manager.save_stats(uid, stats)
            return get_locale_text("i18n_social.team_leave.invite_cancelled")
        members = [item for item in lobby.get("members", []) if item != uid]
        lobby["ready"] = {key: value for key, value in lobby.get("ready", {}).items() if key != uid}
        stats = self._stats(uid)
        stats.active_lobby_id = ""
        self.save_manager.save_stats(uid, stats)
        if not members:
            self.save_manager.delete_lobby(lobby_id)
            return get_locale_text("i18n_social.team_leave.disbanded", lobby_id=lobby_id)
        lobby["members"] = members
        if lobby.get("leader_id") == uid:
            lobby["leader_id"] = members[0]
            lobby.setdefault("ready", {})[members[0]] = True
        self.save_manager.save_lobby(lobby)
        return get_locale_text(
            "i18n_social.team_leave.success",
            lobby_id=lobby_id,
            lobby_status=self._lobby_status(lobby),
        )

    def team_disband(self, uid):
        lobby = self._lobby_of(uid)
        if not lobby:
            return get_locale_text("i18n_social.common.not_in_team")
        if lobby.get("leader_id") != uid:
            return get_locale_text("i18n_social.team_disband.not_leader")
        if any(getattr(self._stats(member_uid), "active_coop_id", "") for member_uid in lobby.get("members", [])):
            return get_locale_text("i18n_social.team_disband.in_coop")
        for member_uid in lobby.get("members", []) + lobby.get("invited", []):
            stats = self._stats(member_uid)
            if getattr(stats, "active_lobby_id", "") == lobby.get("lobby_id"):
                stats.active_lobby_id = ""
                self.save_manager.save_stats(member_uid, stats)
        self.save_manager.delete_lobby(lobby.get("lobby_id"))
        return get_locale_text("i18n_social.team_disband.success", lobby_id=lobby.get("lobby_id"))

    def team_kick(self, uid, query):
        lobby = self._lobby_of(uid)
        if not lobby:
            return get_locale_text("i18n_social.common.not_in_team")
        if lobby.get("leader_id") != uid:
            return get_locale_text("i18n_social.team_kick.not_leader")
        target = self._find_profile(query)
        if not target:
            return get_locale_text("i18n_social.common.player_not_found", query=query)
        target_uid = target.user_id
        if target_uid == uid:
            return get_locale_text("i18n_social.team_kick.self")
        if getattr(self._stats(target_uid), "active_coop_id", ""):
            return get_locale_text("i18n_social.team_kick.target_in_coop", name=target.name)
        removed = False
        if target_uid in lobby.get("members", []):
            lobby["members"] = [item for item in lobby["members"] if item != target_uid]
            lobby.get("ready", {}).pop(target_uid, None)
            removed = True
        if target_uid in lobby.get("invited", []):
            lobby["invited"] = [item for item in lobby["invited"] if item != target_uid]
            removed = True
        if not removed:
            return get_locale_text("i18n_social.team_kick.not_member", name=target.name)
        target_stats = self._stats(target_uid)
        if getattr(target_stats, "active_lobby_id", "") == lobby.get("lobby_id"):
            target_stats.active_lobby_id = ""
            self.save_manager.save_stats(target_uid, target_stats)
        self.save_manager.save_lobby(lobby)
        return get_locale_text(
            "i18n_social.team_kick.success",
            name=target.name,
            lobby_status=self._lobby_status(lobby),
        )

    def team_ready(self, uid, ready=True):
        lobby = self._lobby_of(uid)
        if not lobby:
            return get_locale_text("i18n_social.common.not_in_team")
        if uid not in lobby.get("members", []):
            return get_locale_text("i18n_social.team_ready.not_member")
        lobby.setdefault("ready", {})[uid] = bool(ready)
        self.save_manager.save_lobby(lobby)
        if ready:
            return get_locale_text(
                "i18n_social.team_ready.ready",
                lobby_status=self._lobby_status(lobby),
            )
        return get_locale_text(
            "i18n_social.team_ready.unready",
            lobby_status=self._lobby_status(lobby),
        )

    def team_status(self, uid):
        lobby = self._lobby_of(uid)
        if lobby:
            return self._lobby_status(lobby)
        stats = self._stats(uid)
        return (
            self.team_invites(uid)
            if not getattr(stats, "active_coop_id", "")
            else get_locale_text("i18n_social.team_status.in_coop")
        )

    def team_start(self, uid):
        lobby = self._lobby_of(uid)
        if not lobby:
            return get_locale_text("i18n_social.common.not_in_team")
        if lobby.get("leader_id") != uid:
            return get_locale_text("i18n_social.team_start.not_leader")
        members = list(lobby.get("members", []))
        if len(members) < TEAM_MIN_PLAYERS:
            return get_locale_text("i18n_social.team_start.min_players", min_players=TEAM_MIN_PLAYERS)
        if len(members) > TEAM_MAX_MEMBERS:
            return get_locale_text("i18n_social.team_start.max_players", max_members=TEAM_MAX_MEMBERS)
        ready = lobby.get("ready", {})
        separator = get_locale_text("i18n_social.common.list_separator")
        not_ready = [self._profile(member_uid)["name"] for member_uid in members if not ready.get(member_uid)]
        if uid in not_ready:
            not_ready.remove(uid)
        if not_ready:
            return get_locale_text("i18n_social.team_start.not_ready", names=separator.join(not_ready))
        stale = []
        for member_uid in members:
            stats = self._stats(member_uid)
            if getattr(stats, "active_lobby_id", "") != lobby.get("lobby_id"):
                stale.append(self._profile(member_uid)["name"])
                continue
            if getattr(stats, "active_coop_id", ""):
                return get_locale_text(
                    "i18n_social.team_start.member_in_coop",
                    name=self._profile(member_uid)["name"],
                )
            if self.save_manager.has_personal_save(member_uid):
                return get_locale_text(
                    "i18n_social.team_start.member_personal_save",
                    name=self._profile(member_uid)["name"],
                )
        if stale:
            return get_locale_text("i18n_social.team_start.stale", names=separator.join(stale))
        if not self.engine:
            return get_locale_text("i18n_social.team_start.no_engine")
        run = self.engine.start_party_game(members, uid, shared_save=True)
        self.save_manager.delete_lobby(lobby.get("lobby_id"))
        notice = get_locale_text(
            "i18n_social.team_start.success",
            lobby_id=lobby.get("lobby_id"),
            names=separator.join(self._profile(member_uid)["name"] for member_uid in members),
        )
        return notice, run

    def team_coordinate(self, uid):
        run = self.save_manager.load_save(uid)
        if run is None or not getattr(run, "coop_id", ""):
            if self._lobby_of(uid) is not None:
                return get_locale_text("i18n_social.team_coordinate.not_started")
            return get_locale_text("i18n_social.team_coordinate.not_in_coop")
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return get_locale_text("i18n_social.team_coordinate.no_floor_map")
        from ...data.world.grid_map_config import FLOOR_CONFIGS, get_display_floor
        from ...renderer.world_grid import format_floor_number
        cfg = FLOOR_CONFIGS.get(fm.floor_index, FLOOR_CONFIGS[1])
        floor_name = get_locale_text(cfg["name_key"])
        lines = [
            get_locale_text(
                "i18n_social.team_coordinate.header",
                floor=format_floor_number(get_display_floor(fm.floor_index)),
                floor_name=floor_name,
            )
        ]
        ready_map = fm.floor_flags.get("downstairs_ready", {}) if isinstance(fm.floor_flags.get("downstairs_ready"), dict) else {}
        for pid in run.all_human_uids():
            pl = run.players.get(pid)
            if pl is None:
                continue
            coord = fm.player_coords.get(pid, "?")
            room = fm.rooms.get(coord)
            room_name = get_locale_text(f"i18n_grid_map.room_name.{room.room_type}") if room is not None else "?"
            sid = fm.player_session_map.get(pid)
            sess = fm.active_sessions.get(sid) if sid else None
            if isinstance(sess, dict):
                sess_type = str(sess.get("node_type") or "")
            elif sess is not None:
                sess_type = str(getattr(sess, "node_type", "") or "")
            else:
                sess_type = ""
            is_waiting_descend = bool(ready_map.get(pid))
            if pl.downed or pl.hp <= 0:
                state = get_locale_text("i18n_social.team_coordinate.state_downed")
            elif is_waiting_descend:
                state = get_locale_text("i18n_social.team_coordinate.state_waiting_descend")
            elif sess_type == "battle":
                state = get_locale_text("i18n_social.team_coordinate.state_battle")
            elif sess_type == "event":
                state = get_locale_text("i18n_social.team_coordinate.state_event")
            elif sess_type:
                state = get_locale_text("i18n_social.team_coordinate.state_interact")
            else:
                state = get_locale_text("i18n_social.team_coordinate.state_ready")
            marker = get_locale_text("i18n_social.team_coordinate.you_marker") if pid == uid else ""
            lines.append(
                get_locale_text(
                    "i18n_social.team_coordinate.member_line",
                    name=pl.name,
                    marker=marker,
                    coord=coord,
                    room_name=room_name,
                    state=state,
                )
            )
        return "\n".join(lines)

    def team_teleport(self, uid, query):
        run = self.save_manager.load_save(uid)
        if run is None or not getattr(run, "coop_id", ""):
            if self._lobby_of(uid) is not None:
                return get_locale_text("i18n_social.team_teleport.not_started")
            return get_locale_text("i18n_social.team_teleport.not_in_coop")
        if not self.engine:
            return get_locale_text("i18n_social.team_teleport.no_engine")
        return self.engine.map_engine.grid_map_service.team_teleport_player(run, query)
