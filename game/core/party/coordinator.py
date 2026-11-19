from ...data.locale_data import get_locale_text
from ...models.coop_view import SHARED_PERSIST_KEYS, apply_view, scope_view


def party_players(run):
    return [run.players[uid] for uid in run.party_order if uid in run.players]


def alive_uids(run):
    humans = run.human_uids() if hasattr(run, "human_uids") else run.party_order
    return [
        uid
        for uid in humans
        if uid in run.players and run.players[uid].hp > 0 and not run.players[uid].downed
    ]

def swap_player(run, player):
    previous = run.player
    previous_user = run.user_id
    run.player = player
    uid = run.uid_for(player)
    if uid:
        run.user_id = uid
    return previous, previous_user


def restore_player(run, previous, previous_user):
    run.player = previous
    run.user_id = previous_user


def add_notice(run, uid, text):
    per = run.node_data.setdefault("coop_notices_by_uid", {})
    bucket = per.setdefault(uid, [])
    bucket.append(text)
    if uid == run.user_id:
        run.node_data["coop_notices"] = bucket


def team_notice(run, text):
    for uid in run.party_order:
        if uid in run.players:
            add_notice(run, uid, text)


def collect_notices(run):
    carried = {}
    per = run.node_data.get("coop_notices_by_uid")
    if isinstance(per, dict):
        for uid, items in per.items():
            if isinstance(items, list) and items:
                carried[uid] = list(items)
    return carried


def attach_notices(run, notices_by_uid, uid):
    if not notices_by_uid:
        return
    run.node_data["coop_notices_by_uid"] = notices_by_uid
    own = notices_by_uid.get(uid, [])
    if own:
        run.node_data["coop_notices"] = list(own)
    else:
        run.node_data.pop("coop_notices", None)


def apply_and_scope(run, uid):
    apply_view(run, uid)
    return scope_view(run, uid)


def _consume_grid_session_hooks(save_manager, map_engine, run, prefix):
    if run.floor_map is None or run.node_type != "grid_map":
        return prefix
    pending_boss = run.node_data.pop("bleak_falls_pending_floor1_boss", None)
    if pending_boss and pending_boss in run.floor_map.rooms:
        from ..world.bleak_falls import on_floor1_boss_cleared
        on_floor1_boss_cleared(run, run.floor_map.rooms[pending_boss], save_manager=save_manager)
    pending_bleak = run.node_data.pop("bleak_falls_pending_clear", None)
    if pending_bleak and pending_bleak in run.floor_map.rooms:
        from ..world.bleak_falls import on_bleak_combat_resolved
        on_bleak_combat_resolved(run, run.floor_map.rooms[pending_bleak], save_manager=save_manager)
    pending_chireiden = run.node_data.pop("chireiden_pending_clear", None)
    if pending_chireiden and pending_chireiden in run.floor_map.rooms:
        from ..world.chireiden import on_chireiden_combat_resolved
        on_chireiden_combat_resolved(run, run.floor_map.rooms[pending_chireiden], save_manager=save_manager)
    post_notices = run.node_data.pop("post_session_notices", [])
    if post_notices:
        joined = "\n\n".join(str(n) for n in post_notices if n)
        if joined:
            prefix = f"{prefix}\n\n{joined}".strip() if prefix else joined
    return prefix


def _compose_free_roam(run, prefix):
    from ...renderer import GameRenderer
    parts = []
    text = str(prefix or "").strip()
    if text:
        parts.append(text)
    parts.append(get_locale_text("i18n_explore_core.node_done_free_roam"))
    rendered = GameRenderer.render_game(run)
    if rendered:
        parts.append(rendered)
    return "\n\n".join(parts)


def _finish_grid_free_roam(save_manager, map_engine, run, uid, prefix):
    carried = collect_notices(run)
    revived = map_engine.leave_node_for_free_roam(run, uid)
    for member_uid, text in revived.items():
        carried.setdefault(member_uid, []).append(text)
    prefix = _consume_grid_session_hooks(save_manager, map_engine, run, prefix)
    attach_notices(run, carried, uid)
    save_manager.save_save(uid, run)
    return _compose_free_roam(run, prefix)


def finish_player_node(save_manager, map_engine, run, uid, prefix="", on_all_ready=None):
    if run.floor_map is not None and not (run.node_data or {}).get("coop_relic_pool"):
        return _finish_grid_free_roam(save_manager, map_engine, run, uid, prefix)
    ready = run.node_data.setdefault("stage_ready", {})
    ready[uid] = True
    views = run.node_data.get("player_views", {})
    view = views.get(uid)
    if view:
        view["data"]["coop_done"] = True
        view["data"]["options"] = []
        view["data"]["items"] = []
        for key, value in view["data"].items():
            run.node_data[key] = value
    members = [u for u in run.party_order if u in run.players]
    human_members = [u for u in (run.human_uids() if hasattr(run, "human_uids") else members) if u in run.players]
    if not human_members or all(ready.get(u, False) or run.players[u].downed for u in human_members):
        pool = run.node_data.get("coop_relic_pool") or []
        merc_notices = []
        if pool:
            from ...entities import get_relic_name
            for merc_uid in members:
                merc = run.players.get(merc_uid)
                if not merc or not getattr(merc, "is_mercenary", False) or merc.downed or merc.hp <= 0:
                    continue
                for entry in pool:
                    rid = entry.get("relic_id")
                    if not entry.get("claimed_by") and rid and rid not in merc.relics:
                        entry["claimed_by"] = merc_uid
                        merc.relics.append(rid)
                        if rid == "red_bottle":
                            merc.max_hp += 5
                            merc.hp += 5
                        notice = get_locale_text(
                            "i18n_mercenary.relic_leftover_claimed",
                            name=merc.name,
                            relic_name=get_relic_name(rid),
                        )
                        merc_notices.append(notice)
                        for human_uid in human_members:
                            add_notice(run, human_uid, notice)
                        break
        advance = on_all_ready or map_engine.enter_next_stage
        advance(run)
        prefix = _consume_grid_session_hooks(save_manager, map_engine, run, prefix)
        save_manager.save_save(run.user_id, run)
        if merc_notices:
            joined_notices = "\n".join(merc_notices)
            prefix = f"{prefix}\n{joined_notices}".strip() if prefix else joined_notices
        if run.floor_map is not None:
            return _compose_free_roam(run, prefix)
        if len(human_members) <= 1:
            return prefix
        player_names = get_locale_text("i18n_explore_core.list_delimiter").join(run.players[u].name for u in human_members)
        return get_locale_text("i18n_explore_core.team_all_ready", prefix=prefix, player_names=player_names, extra="").strip()
    waiting = [
        run.players[u].name
        for u in human_members
        if not ready.get(u, False) and not run.players[u].downed
    ]
    save_manager.save_save(uid, run)
    waiting_names = get_locale_text("i18n_explore_core.list_delimiter").join(waiting) if waiting else get_locale_text("i18n_explore_core.waiting_none")
    return get_locale_text("i18n_explore_core.team_waiting", prefix=prefix, waiting=waiting_names)


def begin_party_gem(run, previous):
    if not previous:
        return
    for key in SHARED_PERSIST_KEYS:
        if key in previous and key != "coop_node_type":
            run.node_data[key] = previous[key]
    if "coop_node_type" in previous:
        run.node_data["gem_prev_coop_type"] = previous["coop_node_type"]
    run.node_data["coop_node_type"] = "gem_insert"


def end_party_gem(run, gem_data, next_type, next_data):
    run.node_type = next_type
    run.node_data = next_data if next_data is not None else {}
    prev_type = gem_data.get("gem_prev_coop_type") or next_type
    for key in SHARED_PERSIST_KEYS:
        if key in gem_data and key not in run.node_data:
            run.node_data[key] = gem_data[key]
    if prev_type:
        run.node_data["coop_node_type"] = prev_type
    shared = getattr(run, "_coop_shared", None)
    if isinstance(shared, dict):
        shared["coop_node_type"] = prev_type
        shared.pop("gem_prev_coop_type", None)
