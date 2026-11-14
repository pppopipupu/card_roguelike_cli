import random
from ...data.grid_map_config import FLOOR_CONFIGS, LANDMARK_CONFIGS, QUEST_RELIC_CONFIG, SP_CONFIG
from ...data.locale_data import get_locale_text
from ...entities import ALL_CARDS, get_relic_name
from .ancient_reward import build_ancient_options, grant_ancient_blessing
from ...models.state import ensure_card_state
from .grid_map_generator import coord_to_xy, xy_to_coord
from ..party.session import SessionContextScoper
from .sp_system import consume_sp, restore_sp


def _has_curse_in_deck(player) -> bool:
    for c in getattr(player, "deck", []) or []:
        st = ensure_card_state(c)
        if st.id.startswith("curse_"):
            return True
    return False


def _quest_relic_name(qid: str) -> str:
    cfg = QUEST_RELIC_CONFIG.get(qid, {})
    key = cfg.get("name_key", "")
    return get_locale_text(key) if key else qid


def _ritual_desc_for(protocol: str) -> str:
    return get_locale_text(f"i18n_grid_map.ritual_protocol.{protocol}")


def _unlock_secret_boss(fm) -> str:
    fm.secret_unlocked = True
    if fm.secret_boss_coord and fm.secret_boss_coord in fm.rooms:
        room = fm.rooms[fm.secret_boss_coord]
        room.secret_unlocked = True
        room.explored = True
        if fm.secret_boss_coord not in fm.revealed_coords:
            fm.revealed_coords.append(fm.secret_boss_coord)
    return fm.secret_boss_coord


def build_landmark_options(run, uid: str) -> dict:
    fm = run.floor_map
    coord = fm.player_coords.get(uid, "")
    room = fm.rooms.get(coord)
    player = run.players.get(uid, run.player)
    lm_id = getattr(room, "landmark_id", "") if room else ""
    options = []
    title = ""
    desc = ""

    if lm_id == "observatory":
        title = get_locale_text(LANDMARK_CONFIGS["observatory"]["name_key"])
        desc = get_locale_text(LANDMARK_CONFIGS["observatory"]["desc_key"])
        options.append({
            "action": "obs_reveal_gold",
            "text": get_locale_text("i18n_grid_map.landmarks.observatory.opt_gold", cost=SP_CONFIG["observatory_gold_cost"], count=SP_CONFIG["observatory_reveal_count"]),
        })
        options.append({
            "action": "obs_reveal_sp",
            "text": get_locale_text("i18n_grid_map.landmarks.observatory.opt_sp", cost=SP_CONFIG["observatory_sp_cost"], count=SP_CONFIG["observatory_reveal_count"]),
        })
        if fm.secret_boss_coord and not fm.secret_clue_found:
            options.append({
                "action": "obs_secret_clue",
                "text": get_locale_text("i18n_grid_map.landmarks.observatory.opt_clue"),
            })
    elif lm_id == "broken_sword_camp":
        title = get_locale_text(LANDMARK_CONFIGS["broken_sword_camp"]["name_key"])
        desc = get_locale_text(LANDMARK_CONFIGS["broken_sword_camp"]["desc_key"])
        if "camp_ember" not in getattr(player, "quest_relics", []) and not fm.floor_flags.get("camp_ember_taken"):
            options.append({
                "action": "camp_take_ember",
                "text": get_locale_text("i18n_grid_map.landmarks.broken_sword_camp.opt_ember"),
            })
        if not fm.floor_flags.get("camp_rested"):
            options.append({
                "action": "camp_rest",
                "text": get_locale_text("i18n_grid_map.landmarks.broken_sword_camp.opt_rest"),
            })
        if not fm.floor_flags.get("camp_scavenged"):
            options.append({
                "action": "camp_scavenge",
                "text": get_locale_text("i18n_grid_map.landmarks.broken_sword_camp.opt_scavenge"),
            })
    elif lm_id == "ancient_stele":
        title = get_locale_text(LANDMARK_CONFIGS["ancient_stele"]["name_key"])
        desc = get_locale_text(LANDMARK_CONFIGS["ancient_stele"]["desc_key"])
        qrelics = getattr(player, "quest_relics", [])
        if "broken_rift_compass" in qrelics and "awakened_rift_compass" not in qrelics:
            options.append({
                "action": "stele_charge_max_sp",
                "text": get_locale_text("i18n_grid_map.landmarks.ancient_stele.opt_charge_sp", cost=SP_CONFIG["stele_charge_max_sp_cost"]),
            })
            options.append({
                "action": "stele_charge_hp",
                "text": get_locale_text("i18n_grid_map.landmarks.ancient_stele.opt_charge_hp", cost=SP_CONFIG["stele_charge_hp_cost"]),
            })
        if not fm.floor_flags.get("stele_inscribed"):
            options.append({
                "action": "stele_inscribe",
                "text": get_locale_text("i18n_grid_map.landmarks.ancient_stele.opt_inscribe"),
            })
    if coord == fm.ritual_coord and fm.secret_boss_coord and not fm.secret_unlocked:
        proto = fm.ritual_protocol
        options.append({
            "action": f"ritual_{proto}",
            "text": get_locale_text("i18n_grid_map.ritual_opt_label", desc=_ritual_desc_for(proto)),
        })
        if not title:
            title = get_locale_text("i18n_grid_map.ritual_title")
            desc = get_locale_text("i18n_grid_map.ritual_desc", desc=_ritual_desc_for(proto))

    options.append({
        "action": "landmark_leave",
        "text": get_locale_text("i18n_grid_map.opt_leave"),
    })
    return {"title": title, "desc": desc, "landmark_id": lm_id, "coord": coord, "options": options}


def ensure_descent_tunnel(room):
    if room is None:
        return
    if "descent_tunnel" not in room.props:
        room.props = list(room.props or []) + ["descent_tunnel"]
    room.env_id = "downstairs_hall"


def build_downstairs_data(run, save_manager, uid) -> dict:
    fm = run.floor_map
    nxt = fm.floor_index + 1
    nxt_name = get_locale_text(FLOOR_CONFIGS.get(nxt, FLOOR_CONFIGS[4])["name_key"])
    coord = fm.player_coords.get(uid, "")
    room = fm.rooms.get(coord)
    store = room.shared_payload.setdefault("descent_options_by_uid", {}) if room is not None else {}
    options = store.get(uid)
    if not options:
        options = []
        for opt in build_ancient_options(run, save_manager)["options"]:
            options.append({
                "action": "ancient_pick",
                "type": opt["type"],
                "card": opt["card"],
                "relic": opt["relic"],
                "text": get_locale_text(
                    "i18n_explore_core.ancient_blessing_card_relic",
                    card_name=ALL_CARDS[opt["card"]].name,
                    relic_name=get_relic_name(opt["relic"]),
                ),
            })
        options.append({"action": "downstairs_leave", "text": get_locale_text("i18n_grid_map.opt_leave")})
        if room is not None:
            store[uid] = options
    return {
        "title": get_locale_text("i18n_grid_map.downstairs.title", floor=fm.floor_index),
        "desc": get_locale_text("i18n_grid_map.downstairs.desc", next_floor=nxt, nxt_name=nxt_name),
        "options": options,
    }


def open_room_talk(save_manager, run, uid: str) -> str:
    fm = getattr(run, "floor_map", None)
    if fm is None:
        return get_locale_text("i18n_grid_map.no_talk_target")
    coord = fm.player_coords.get(uid, "")
    room = fm.rooms.get(coord)
    if room is None:
        return get_locale_text("i18n_grid_map.no_talk_target")
    if room.room_type == "downstairs":
        ensure_descent_tunnel(room)
        data = build_downstairs_data(run, save_manager, uid)
        SessionContextScoper.create_session(run, coord, "downstairs", [uid], node_data=data)
        save_manager.save_save(uid, run)
        return ""
    if room.room_type == "landmark" or (coord == fm.ritual_coord and fm.secret_boss_coord and not fm.secret_unlocked):
        data = build_landmark_options(run, uid)
        SessionContextScoper.create_session(run, coord, "landmark", [uid], node_data=data)
        save_manager.save_save(uid, run)
        return ""
    return get_locale_text("i18n_grid_map.no_talk_target")


def execute_landmark_option(save_manager, map_engine, run, idx: int) -> str:
    options = run.node_data.get("options", [])
    if idx < 0 or idx >= len(options):
        return get_locale_text("err_invalid_option_idx")
    action = options[idx].get("action", "")
    p = run.player
    fm = run.floor_map
    uid = run.user_id

    if action == "landmark_leave":
        map_engine.complete_session(run, mark_cleared=False)
        save_manager.save_save(uid, run)
        return get_locale_text("i18n_grid_map.landmark_left")

    if action in ("obs_reveal_gold", "obs_reveal_sp"):
        if action == "obs_reveal_gold":
            cost = SP_CONFIG["observatory_gold_cost"]
            if p.gold < cost:
                return get_locale_text("i18n_grid_map.not_enough_gold", cost=cost)
            p.gold -= cost
        else:
            consume_sp(p, SP_CONFIG["observatory_sp_cost"], allow_overdraft=True)
        unexplored = [
            c for c, r in fm.rooms.items()
            if r.room_type not in ("wall", "secret_boss") and not r.explored
        ]
        special = [c for c in unexplored if fm.rooms[c].room_type in ("treasure", "cafe", "shop", "rest", "landmark", "boss", "life_merchant")]
        pick_pool = special if special else unexplored
        count = min(SP_CONFIG["observatory_reveal_count"], len(pick_pool))
        picked = random.sample(pick_pool, count) if count > 0 else []
        for c in picked:
            fm.rooms[c].explored = True
            if c not in fm.revealed_coords:
                fm.revealed_coords.append(c)
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        coords_str = ", ".join(picked) if picked else get_locale_text("i18n_grid_map.none")
        return get_locale_text("i18n_grid_map.landmarks.observatory.revealed_msg", coords=coords_str)

    if action == "obs_secret_clue":
        fm.secret_clue_found = True
        if fm.ritual_coord and fm.ritual_coord in fm.rooms:
            fm.rooms[fm.ritual_coord].explored = True
            if fm.ritual_coord not in fm.revealed_coords:
                fm.revealed_coords.append(fm.ritual_coord)
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        return get_locale_text(
            "i18n_grid_map.landmarks.observatory.clue_msg",
            ritual_coord=fm.ritual_coord,
            protocol=_ritual_desc_for(fm.ritual_protocol),
        )

    if action == "camp_take_ember":
        if "camp_ember" not in p.quest_relics:
            p.quest_relics.append("camp_ember")
        if "broken_rift_compass" not in p.quest_relics and "awakened_rift_compass" not in p.quest_relics:
            p.quest_relics.append("broken_rift_compass")
        fm.floor_flags["camp_ember_taken"] = True
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        return get_locale_text("i18n_grid_map.landmarks.broken_sword_camp.ember_gained", name=_quest_relic_name("camp_ember"))

    if action == "camp_rest":
        fm.floor_flags["camp_rested"] = True
        restore_sp(p, 3)
        p.hp = min(p.max_hp, p.hp + 6)
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        return get_locale_text("i18n_grid_map.landmarks.broken_sword_camp.rest_msg", hp=p.hp, sp=p.sp, max_sp=p.max_sp)

    if action == "camp_scavenge":
        from ..inventory.bag_service import add_bag_item, get_item_display_name
        fm.floor_flags["camp_scavenged"] = True
        loot = random.choice(["field_bandage", "espresso_beans"])
        ok, _ = add_bag_item(p, loot)
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        if ok:
            return get_locale_text("i18n_grid_map.landmarks.broken_sword_camp.scavenge_item_msg", item=get_item_display_name(loot))
        p.gold += 15
        return get_locale_text("i18n_grid_map.landmarks.broken_sword_camp.scavenge_gold_msg", gold=15)

    if action == "stele_inscribe":
        from .persistent_buffs import add_persistent_buff
        from .rooms.interact import _reveal_any_special
        fm.floor_flags["stele_inscribed"] = True
        consume_sp(p, 1, allow_overdraft=True)
        add_persistent_buff(p, "ancient_ward", 1)
        revealed = _reveal_any_special(fm, 1)
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        coord_str = revealed[0] if revealed else get_locale_text("i18n_grid_map.none")
        return get_locale_text("i18n_grid_map.landmarks.ancient_stele.inscribed_msg", coord=coord_str)

    if action == "stele_charge_max_sp":
        cost = SP_CONFIG["stele_charge_max_sp_cost"]
        p.max_sp = max(2, p.max_sp - cost)
        p.sp = min(p.sp, p.max_sp)
        if "broken_rift_compass" in p.quest_relics:
            p.quest_relics.remove("broken_rift_compass")
        if "awakened_rift_compass" not in p.quest_relics:
            p.quest_relics.append("awakened_rift_compass")
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        return get_locale_text("i18n_grid_map.landmarks.ancient_stele.charged_msg", name=_quest_relic_name("awakened_rift_compass"))

    if action == "stele_charge_hp":
        cost = SP_CONFIG["stele_charge_hp_cost"]
        p.hp = max(1, p.hp - cost)
        if "broken_rift_compass" in p.quest_relics:
            p.quest_relics.remove("broken_rift_compass")
        if "awakened_rift_compass" not in p.quest_relics:
            p.quest_relics.append("awakened_rift_compass")
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        return get_locale_text("i18n_grid_map.landmarks.ancient_stele.charged_msg", name=_quest_relic_name("awakened_rift_compass"))
    if action.startswith("ritual_"):
        proto = action[len("ritual_"):]
        if proto == "exhaustion_or_curse":
            if getattr(p, "exhaustion", 0) < 1 and not _has_curse_in_deck(p):
                return get_locale_text("i18n_grid_map.ritual_fail_exhaustion_or_curse")
        elif proto == "camp_ember":
            if "camp_ember" not in getattr(p, "quest_relics", []):
                return get_locale_text("i18n_grid_map.ritual_fail_camp_ember")
            p.quest_relics.remove("camp_ember")
        elif proto == "sp_sacrifice":
            consume_sp(p, SP_CONFIG["ritual_sp_cost"], allow_overdraft=True)
            p.hp = max(1, p.hp - SP_CONFIG["ritual_hp_cost"])
            from .sp_system import check_exhaustion_death
            died, dmsg = check_exhaustion_death(save_manager, run, p)
            if died:
                return dmsg
        elif proto == "awakened_compass":
            if "awakened_rift_compass" not in getattr(p, "quest_relics", []):
                return get_locale_text("i18n_grid_map.ritual_fail_compass")
            p.quest_relics.remove("awakened_rift_compass")
        secret_coord = _unlock_secret_boss(fm)
        map_engine.complete_session(run, mark_cleared=True)
        save_manager.save_save(uid, run)
        return get_locale_text("i18n_grid_map.ritual_success", coord=secret_coord)

    return get_locale_text("err_invalid_option_idx")


def execute_downstairs_option(save_manager, map_engine, run, idx: int) -> str:
    options = run.node_data.get("options", [])
    if idx < 0 or idx >= len(options):
        return get_locale_text("err_invalid_option_idx")
    chosen = options[idx]
    action = chosen.get("action", "")
    uid = run.user_id
    if action == "downstairs_leave":
        map_engine.complete_session(run, mark_cleared=False)
        save_manager.save_save(uid, run)
        return get_locale_text("i18n_grid_map.downstairs.left_msg")
    if action != "ancient_pick":
        return get_locale_text("err_invalid_option_idx")
    reward_msg = ""
    for pid in run.all_human_uids():
        pl = run.players.get(pid)
        if pl is None:
            continue
        reward_msg = grant_ancient_blessing(run, chosen, player=pl)
    map_engine.complete_session(run, mark_cleared=False)
    advance_msg = map_engine.advance_to_next_floor(run)
    save_manager.save_save(uid, run)
    return "\n".join([reward_msg, advance_msg])
