from math import ceil

from ...data.balance_config import COOP_VOTE_RATIO
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


def vote_threshold(run):
    alive = alive_uids(run)
    return max(1, ceil(len(alive) * COOP_VOTE_RATIO))


def vote_option(run, uid, option_idx, recorded_key):
    alive = alive_uids(run)
    if len(alive) <= 1 or uid == run.leader_id:
        run.node_data["votes"] = {}
        return None
    votes = run.node_data.setdefault("votes", {})
    votes[uid] = option_idx
    same = sum(1 for member in alive if votes.get(member) == option_idx)
    if alive and same >= vote_threshold(run):
        run.node_data["votes"] = {}
        return None
    delimiter = get_locale_text("i18n_explore_core.list_delimiter")
    summary = delimiter.join(
        get_locale_text("i18n_explore_core.vote_summary_entry", name=run.players[member].name, index=index)
        for member, index in votes.items()
        if member in run.players
    )
    return get_locale_text(recorded_key, summary=summary)


def finish_player_node(save_manager, map_engine, run, uid, prefix="", on_all_ready=None):
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
        save_manager.save_save(run.user_id, run)
        if merc_notices:
            joined_notices = "\n".join(merc_notices)
            prefix = f"{prefix}\n{joined_notices}".strip() if prefix else joined_notices
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
