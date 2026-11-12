VIEW_KEYS = {
    "items",
    "options",
    "cards",
    "title",
    "desc",
    "text",
    "can_skip",
    "force_upgraded",
    "next_node_type",
    "next_node_data",
    "state",
    "pending_remove",
    "remove_source",
    "pending_upgrade",
    "upgrade_source",
    "upgrade_price",
    "pending_gem",
    "style",
    "event_id",
    "description",
    "base_options",
    "quest_bonus",
    "no_reward",
    "coop_done",
    "coop_downed",
    "coop_pending_upgrade",
    "cafe_data",
}

SHARED_PERSIST_KEYS = {
    "coop_node_type",
    "player_views",
    "player_rewards",
    "player_shops",
    "player_rests",
    "stage_ready",
    "turn_ready",
    "votes",
    "coop_relic_pool",
    "coop_cafe",
    "coop_notices",
    "coop_notices_by_uid",
    "enemy_targets",
    "coop_aggro_cursor",
    "coop_node_round",
    "gem_prev_coop_type",
    "cthulhu_puzzle_active",
    "cthulhu_seal_stage",
    "cthulhu_revive_count",
    "cthulhu_mist_turns",
    "cthulhu_puzzle_advanced",
    "merc_dialogs",
    "merc_acted_round",
}

VIEW_NODES = {
    "start_ancient",
    "ancient",
    "reward",
    "shop",
    "life_merchant",
    "rest",
    "card_select",
    "treasure",
    "boss_chest",
    "gem_insert",
    "cafe",
}


def apply_view(run, uid):
    if not run or not uid:
        return run
    node_data = run.node_data if run.node_data is not None else {}
    run._coop_shared = {
        key: node_data.get(key)
        for key in SHARED_PERSIST_KEYS
        if key in node_data
    }
    base_type = node_data.get("coop_node_type", run.node_type)
    if base_type not in VIEW_NODES:
        return run
    views = node_data.setdefault("player_views", {})
    view = views.get(uid)
    if not view:
        view = {
            "node_type": run.node_type,
            "data": {key: value for key, value in node_data.items() if key in VIEW_KEYS},
        }
        views[uid] = view
    for key in VIEW_KEYS:
        node_data.pop(key, None)
    for key, value in view.get("data", {}).items():
        node_data[key] = value
    run.node_type = view.get("node_type", run.node_type)
    return run


def persist_view(run, uid):
    if not run or not uid:
        return
    node_data = run.node_data if run.node_data is not None else {}
    if run.node_type not in VIEW_NODES:
        node_data.pop("coop_node_type", None)
        node_data.pop("player_views", None)
        run._coop_shared = {}
        return
    shared = {}
    for key in SHARED_PERSIST_KEYS:
        if key in node_data:
            shared[key] = node_data[key]
    for key, value in getattr(run, "_coop_shared", {}).items():
        if key not in shared:
            shared[key] = value
            node_data[key] = value
    base_type = node_data.get("coop_node_type", "")
    if base_type not in VIEW_NODES:
        base_type = run.node_type
    node_data["coop_node_type"] = base_type
    shared["coop_node_type"] = base_type
    views = node_data.setdefault("player_views", shared.get("player_views", {}))
    views[uid] = {
        "node_type": run.node_type,
        "data": {key: value for key, value in node_data.items() if key in VIEW_KEYS},
    }
    node_data["player_views"] = views
    shared["player_views"] = views
    for key, value in shared.items():
        node_data[key] = value
    run._coop_shared = shared


def strip_shared(data):
    if not isinstance(data, dict):
        return {}
    return {key: value for key, value in data.items() if key not in SHARED_PERSIST_KEYS}


def scope_view(run, uid):
    if not run or not uid:
        return run
    node_data = run.node_data if run.node_data is not None else {}
    notices_map = node_data.get("coop_notices_by_uid")
    if isinstance(notices_map, dict):
        node_data["coop_notices"] = list(notices_map.get(uid, []))
    shared = getattr(run, "_coop_shared", None)
    if isinstance(shared, dict) and "coop_notices" in node_data:
        shared["coop_notices"] = node_data["coop_notices"]
    return run
