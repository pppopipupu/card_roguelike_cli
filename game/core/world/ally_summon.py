from ...data.text.locale_data import get_locale_text
from ...data.world.grid_map_config import ALLY_SUMMON_SP_COST, SP_CONFIG
from ...data.battle.battle_mode_config import BATTLE_MODE_SOLO
from ..party.coordinator import add_notice
from ..party.session import SessionContextScoper
from .sp_system import consume_sp, restore_sp


def get_summonable_teammates(run, caller_uid: str) -> list[str]:
    fm = getattr(run, "floor_map", None)
    if fm is None:
        return []
    humans = run.all_human_uids() if hasattr(run, "all_human_uids") else []
    if len(humans) <= 1:
        return []
    result: list[str] = []
    for uid in humans:
        if uid == caller_uid:
            continue
        player = run.players.get(uid)
        if player is None or player.downed or player.hp <= 0:
            continue
        sid = fm.player_session_map.get(uid)
        if sid and sid in fm.active_sessions:
            nt = fm.active_sessions[sid].node_type
            if nt in ("battle", "ally_summon_select", "ally_summon_confirm"):
                continue
        result.append(uid)
    return result


def maybe_open_summon_select(
    grid_map_service,
    run,
    uid: str,
    coord: str,
    room,
    difficulty: str,
    corpse: dict | None,
    hostile_npc_id: str,
    mode: str,
) -> str | None:
    if mode != BATTLE_MODE_SOLO:
        return None
    candidates = get_summonable_teammates(run, uid)
    if not candidates:
        return None
    fm = run.floor_map
    label = grid_map_service._room_display_label(room, fm=fm)
    node_data = {
        "coord": coord,
        "difficulty": difficulty,
        "hostile_npc_id": hostile_npc_id,
        "corpse": corpse,
        "battle_mode": mode,
        "candidates": list(candidates),
        "room_label": label,
        "sp_cost": ALLY_SUMMON_SP_COST,
    }
    SessionContextScoper.create_session(run, coord, "ally_summon_select", [uid], node_data=node_data)
    grid_map_service.save_manager.save_save(uid, run)
    return render_ally_summon_select(run)


def _open_confirm_session(run, target_uid: str, invite: dict) -> None:
    fm = run.floor_map
    if fm is None:
        return
    ally_coord = fm.player_coords.get(target_uid, invite.get("coord", ""))
    prev_uid = run.user_id
    prev_player = run.player
    SessionContextScoper.create_session(
        run,
        ally_coord,
        "ally_summon_confirm",
        [target_uid],
        node_data=dict(invite),
    )
    run.user_id = prev_uid
    run.player = prev_player
    SessionContextScoper.bind_to_run(run, prev_uid)


def _dispatch_summon_confirm(run, caller_uid: str, target_uid: str, coord: str, battle_sid: str, room_label: str) -> None:
    fm = run.floor_map
    if fm is None:
        return
    caller = run.players.get(caller_uid)
    caller_name = caller.name if caller is not None else caller_uid
    invite = {
        "caller_uid": caller_uid,
        "caller_name": caller_name,
        "target_uid": target_uid,
        "coord": coord,
        "battle_sid": battle_sid,
        "room_label": room_label,
        "sp_cost": ALLY_SUMMON_SP_COST,
    }
    existing_sid = fm.player_session_map.get(target_uid)
    if not existing_sid or existing_sid not in fm.active_sessions:
        _open_confirm_session(run, target_uid, invite)
    else:
        pending = fm.floor_flags.setdefault("pending_summon_invites", {})
        if isinstance(pending, dict):
            pending[target_uid] = invite


def open_pending_summon_if_any(run, caller_uid: str) -> bool:
    fm = getattr(run, "floor_map", None)
    if fm is None:
        return False
    pending = (fm.floor_flags or {}).get("pending_summon_invites")
    if not isinstance(pending, dict) or caller_uid not in pending:
        return False
    invite = pending.pop(caller_uid)
    if not pending:
        fm.floor_flags.pop("pending_summon_invites", None)
    battle_sid = str(invite.get("battle_sid") or "")
    sess = fm.active_sessions.get(battle_sid)
    if sess is None or sess.node_type != "battle":
        return False
    player = run.players.get(caller_uid)
    if player is None or player.downed or player.hp <= 0:
        return False
    ally_coord = fm.player_coords.get(caller_uid, invite.get("coord", ""))
    SessionContextScoper.create_session(
        run,
        ally_coord,
        "ally_summon_confirm",
        [caller_uid],
        node_data=dict(invite),
    )
    return True


def render_ally_summon_select(run) -> str:
    data = run.node_data or {}
    p = run.player
    fm = run.floor_map
    sp = int(getattr(p, "sp", 0) or 0)
    max_sp = int(getattr(p, "max_sp", SP_CONFIG["default_max_sp"]))
    cost = int(data.get("sp_cost", ALLY_SUMMON_SP_COST))
    sep = get_locale_text("renderer_explore.separator")
    lines = [
        sep,
        get_locale_text(
            "i18n_ally_summon.select_title",
            label=data.get("room_label", ""),
            coord=data.get("coord", ""),
        ),
        get_locale_text("i18n_ally_summon.select_sp_line", sp=sp, max_sp=max_sp, cost=cost),
        "",
        get_locale_text("i18n_ally_summon.opt_solo"),
    ]
    for idx, ally_uid in enumerate(data.get("candidates") or [], 2):
        ally = run.players.get(ally_uid)
        name = ally.name if ally is not None else ally_uid
        ally_coord = fm.player_coords.get(ally_uid, "?") if fm is not None else "?"
        lines.append(
            get_locale_text(
                "i18n_ally_summon.opt_summon_ally",
                idx=idx,
                name=name,
                ally_coord=ally_coord,
                cost=cost,
            )
        )
    lines.append("")
    lines.append(get_locale_text("i18n_ally_summon.select_hint", cost=cost))
    lines.append(sep)
    return "\n".join(lines)


def render_ally_summon_confirm(run) -> str:
    data = run.node_data or {}
    cost = int(data.get("sp_cost", ALLY_SUMMON_SP_COST))
    coord = str(data.get("coord") or "")
    sep = get_locale_text("renderer_explore.separator")
    lines = [
        sep,
        get_locale_text("i18n_ally_summon.confirm_title"),
        get_locale_text(
            "i18n_ally_summon.confirm_desc",
            caller=data.get("caller_name", ""),
            label=data.get("room_label", ""),
            coord=coord,
            cost=cost,
        ),
        "",
        get_locale_text("i18n_ally_summon.confirm_opt_accept", coord=coord),
        get_locale_text("i18n_ally_summon.confirm_opt_decline", cost=cost),
        "",
        get_locale_text("i18n_ally_summon.confirm_hint"),
        sep,
    ]
    return "\n".join(lines)


def handle_summon_select_choose(grid_map_service, run, option_idx: int) -> str:
    uid = run.user_id
    fm = run.floor_map
    data = dict(run.node_data or {})
    candidates = list(data.get("candidates") or [])
    if option_idx == 0:
        option_idx = 1
    if option_idx < 1 or option_idx > 1 + len(candidates):
        return get_locale_text("err_invalid_option_idx")

    coord = str(data.get("coord") or "")
    difficulty = str(data.get("difficulty") or "normal")
    hostile_npc_id = str(data.get("hostile_npc_id") or "")
    corpse = data.get("corpse")
    battle_mode = str(data.get("battle_mode") or BATTLE_MODE_SOLO)
    room_label = str(data.get("room_label") or "")
    cost = int(data.get("sp_cost", ALLY_SUMMON_SP_COST))
    room = fm.rooms[coord]
    select_sid = fm.player_session_map.get(uid, "")

    if option_idx == 1:
        if select_sid:
            SessionContextScoper.close_session(run, select_sid, mark_cleared=False)
        return grid_map_service._launch_battle_session(
            run,
            coord,
            [uid],
            room,
            difficulty,
            corpse=corpse,
            hostile_npc_id=hostile_npc_id,
            battle_mode=battle_mode,
        )

    target_uid = candidates[option_idx - 2]
    target_player = run.players.get(target_uid)
    target_sid = fm.player_session_map.get(target_uid, "")
    target_in_battle = bool(
        target_sid
        and target_sid in fm.active_sessions
        and fm.active_sessions[target_sid].node_type in ("battle", "ally_summon_select", "ally_summon_confirm")
    )
    if target_player is None or target_player.downed or target_player.hp <= 0 or target_in_battle:
        tname = target_player.name if target_player is not None else target_uid
        return get_locale_text("i18n_ally_summon.err_ally_unavailable", name=tname)

    paid = consume_sp(run.player, cost, allow_overdraft=False)
    if paid.get("overdraft"):
        return get_locale_text(
            "i18n_ally_summon.err_not_enough_sp",
            cost=cost,
            sp=int(getattr(run.player, "sp", 0) or 0),
        )

    if select_sid:
        SessionContextScoper.close_session(run, select_sid, mark_cleared=False)
    battle_out = grid_map_service._launch_battle_session(
        run,
        coord,
        [uid],
        room,
        difficulty,
        corpse=corpse,
        hostile_npc_id=hostile_npc_id,
        battle_mode=battle_mode,
    )
    battle_sid = fm.player_session_map.get(uid, "")
    if battle_sid:
        _dispatch_summon_confirm(run, uid, target_uid, coord, battle_sid, room_label)
        grid_map_service.save_manager.save_save(uid, run)
    notice = get_locale_text("i18n_ally_summon.summon_sent_notice", cost=cost, name=target_player.name)
    return f"{notice}\n\n{battle_out}"


def handle_summon_confirm_choose(grid_map_service, run, option_idx: int) -> str:
    from ...renderer import GameRenderer

    uid = run.user_id
    fm = run.floor_map
    data = dict(run.node_data or {})
    caller_uid = str(data.get("caller_uid") or "")
    caller_name = str(data.get("caller_name") or caller_uid)
    coord = str(data.get("coord") or "")
    battle_sid = str(data.get("battle_sid") or "")
    cost = int(data.get("sp_cost", ALLY_SUMMON_SP_COST))
    confirm_sid = fm.player_session_map.get(uid, "")

    if option_idx not in (0, 1, 2):
        return get_locale_text("err_invalid_option_idx")

    if confirm_sid:
        SessionContextScoper.close_session(run, confirm_sid, mark_cleared=False)

    ally_name = run.player.name if run.player is not None else uid
    caller_player = run.players.get(caller_uid)
    battle_sess = fm.active_sessions.get(battle_sid)
    battle_active = bool(battle_sess is not None and battle_sess.node_type == "battle")

    if option_idx == 1:
        if not battle_active:
            if caller_player is not None:
                restore_sp(caller_player, cost)
            grid_map_service.save_manager.save_save(uid, run)
            msg = get_locale_text("i18n_ally_summon.battle_already_ended", caller=caller_name, coord=coord, cost=cost)
            return f"{msg}\n\n{GameRenderer.render_game(run)}"
        joined_out = grid_map_service._join_battle_session(run, uid, coord, battle_sid)
        add_notice(
            run,
            caller_uid,
            get_locale_text("i18n_ally_summon.accepted_caller_notice", ally=ally_name, coord=coord),
        )
        grid_map_service.save_manager.save_save(uid, run)
        msg = get_locale_text("i18n_ally_summon.accepted_self", caller=caller_name, coord=coord)
        return f"{msg}\n\n{joined_out}"

    if caller_player is not None:
        restore_sp(caller_player, cost)
    if battle_active:
        prev_uid = run.user_id
        prev_player = run.player
        SessionContextScoper.bind_to_run(run, caller_uid)
        add_notice(
            run,
            caller_uid,
            get_locale_text("i18n_ally_summon.declined_caller_notice", ally=ally_name, cost=cost),
        )
        SessionContextScoper.sync_from_run(run, caller_uid)
        run.user_id = prev_uid
        run.player = prev_player
        SessionContextScoper.bind_to_run(run, prev_uid)
    grid_map_service.save_manager.save_save(uid, run)
    msg = get_locale_text("i18n_ally_summon.declined_self", caller=caller_name, cost=cost)
    return f"{msg}\n\n{GameRenderer.render_game(run)}"


def get_summon_snapshot_options(run) -> list[dict]:
    data = run.node_data or {}
    fm = getattr(run, "floor_map", None)
    cost = int(data.get("sp_cost", ALLY_SUMMON_SP_COST))
    if run.node_type == "ally_summon_select":
        opts = [
            {
                "index": 1,
                "kind": "ally_summon_solo",
                "label": get_locale_text("i18n_ally_summon.snap_solo"),
            }
        ]
        for idx, ally_uid in enumerate(data.get("candidates") or [], 2):
            ally = run.players.get(ally_uid)
            name = ally.name if ally is not None else ally_uid
            ally_coord = fm.player_coords.get(ally_uid, "?") if fm is not None else "?"
            opts.append(
                {
                    "index": idx,
                    "kind": "ally_summon_ally",
                    "label": get_locale_text(
                        "i18n_ally_summon.snap_summon_ally",
                        name=name,
                        ally_coord=ally_coord,
                        cost=cost,
                    ),
                }
            )
        return opts
    if run.node_type == "ally_summon_confirm":
        coord = str(data.get("coord") or "")
        return [
            {
                "index": 1,
                "kind": "ally_summon_accept",
                "label": get_locale_text("i18n_ally_summon.snap_accept", coord=coord),
            },
            {
                "index": 2,
                "kind": "ally_summon_decline",
                "label": get_locale_text("i18n_ally_summon.snap_decline", cost=cost),
            },
        ]
    return []
