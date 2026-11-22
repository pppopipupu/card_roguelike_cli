from typing import Any, Dict, List, Optional
from .....data.text.locale_data import get_locale_text
from .....data.world.map_quest_config import TOWN_FLAG_MULTI_QUESTS
from .....data.world.npc_dialog.quests import NPC_QUEST_CONFIG
from .....models.state import GameRun, UserStats
from ....inventory.bag_service import add_bag_item, get_item_display_name
from ....inventory.card_distribution import CardDistributor
from ....inventory.deck_service import DeckService
from ....text.events import LocaleText, RenderedText, TextDocument, TextNode, locale_text
from ....text.pipeline import render_text_node
from ...persistent_buffs import add_persistent_buff
from ...sp_system import reduce_exhaustion, restore_sp
from .state import NpcMemoryStore

MAX_ACTIVE_SINGLE_RUN_QUESTS = 3


def _run_quests(run: Optional[GameRun]) -> Dict[str, dict]:
    if run is None:
        return {}
    if not isinstance(getattr(run, "map_data", None), dict):
        run.map_data = {}
    return run.map_data.setdefault("map_quests", {})


def _multi_quests(stats: Optional[UserStats]) -> Dict[str, dict]:
    if stats is None:
        return {}
    if not isinstance(getattr(stats, "town_flags", None), dict):
        stats.town_flags = {}
    return stats.town_flags.setdefault(TOWN_FLAG_MULTI_QUESTS, {})


def get_quest_entry(run: Optional[GameRun], stats: Optional[UserStats], qid: str) -> Optional[dict]:
    cfg = NPC_QUEST_CONFIG.get(qid)
    if cfg is None:
        return None
    if cfg.get("kind") == "multi":
        multi = (getattr(stats, "town_flags", None) or {}).get(TOWN_FLAG_MULTI_QUESTS) or {}
        if isinstance(multi, dict) and isinstance(multi.get(qid), dict):
            return multi[qid]
    run_q = (getattr(run, "map_data", None) or {}).get("map_quests") or {}
    if isinstance(run_q, dict) and isinstance(run_q.get(qid), dict):
        return run_q[qid]
    return None


def get_quest_status(run: Optional[GameRun], stats: Optional[UserStats], qid: str) -> str:
    entry = get_quest_entry(run, stats, qid)
    if not entry:
        return "unstarted"
    return str(entry.get("status", "active"))


def is_quest_ready_to_turn_in(run: Optional[GameRun], stats: Optional[UserStats], qid: str) -> bool:
    cfg = NPC_QUEST_CONFIG.get(qid)
    entry = get_quest_entry(run, stats, qid)
    if not cfg or not entry or entry.get("status") != "active":
        return False
    if cfg.get("objective_type") == "collect_item" and run is not None:
        item_id = str(cfg.get("target_item", ""))
        return item_id in (getattr(run.player, "bag_items", None) or ())
    return int(entry.get("progress", 0)) >= int(entry.get("target", cfg.get("target", 1)))


def active_single_npc_quest_count(run: Optional[GameRun]) -> int:
    run_q = (getattr(run, "map_data", None) or {}).get("map_quests") or {}
    count = 0
    for qid, entry in run_q.items():
        if qid in NPC_QUEST_CONFIG and NPC_QUEST_CONFIG[qid].get("kind") != "multi":
            if isinstance(entry, dict) and entry.get("status") == "active":
                count += 1
    return count


def can_accept_quest(run: Optional[GameRun], stats: Optional[UserStats], qid: str) -> bool:
    cfg = NPC_QUEST_CONFIG.get(qid)
    if cfg is None:
        return False
    if get_quest_status(run, stats, qid) != "unstarted":
        return False
    if cfg.get("kind") != "multi" and active_single_npc_quest_count(run) >= MAX_ACTIVE_SINGLE_RUN_QUESTS:
        return False
    return True


def has_active_quest_for_npc(run: Optional[GameRun], stats: Optional[UserStats], npc_id: str) -> bool:
    for qid, cfg in NPC_QUEST_CONFIG.items():
        givers = set(cfg.get("turnin_npcs") or ()) | {cfg.get("giver_npc_id", "")}
        if npc_id in givers and get_quest_status(run, stats, qid) == "active":
            return True
    return False


def accept_npc_quest(run: GameRun, stats: Optional[UserStats], save_manager, uid: str, qid: str) -> Optional[TextNode]:
    cfg = NPC_QUEST_CONFIG.get(qid)
    if cfg is None or not can_accept_quest(run, stats, qid):
        return None
    entry = {
        "kind": str(cfg.get("kind", "single")),
        "status": "active",
        "stage": "accepted",
        "history": ["accepted"],
        "progress": 0,
        "target": int(cfg.get("target", 1)),
        "seen_tokens": [],
    }
    _run_quests(run)[qid] = dict(entry)
    if cfg.get("kind") == "multi" and stats is not None:
        _multi_quests(stats)[qid] = dict(entry)
        NpcMemoryStore.save_stats(save_manager, uid, stats)
    return locale_text(str(cfg.get("accepted_key", "i18n_npc_crpg_core.quests.accepted")), params={"target": entry["target"]})


def _apply_quest_rewards(run: GameRun, stats: Optional[UserStats], rewards: dict) -> dict:
    p = run.player
    params: Dict[str, Any] = {}
    gold = int(rewards.get("gold", 0) or 0)
    if gold:
        p.gold += gold
        params["gold"] = gold
    gp = int(rewards.get("gp", 0) or 0)
    if gp and stats is not None:
        stats.gp = int(getattr(stats, "gp", 0) or 0) + gp
        params["gp"] = gp
    heal = int(rewards.get("heal", 0) or 0)
    if heal:
        before = p.hp
        p.hp = min(p.max_hp, p.hp + heal)
        params["heal"] = p.hp - before
    sp_gain = int(rewards.get("sp", 0) or 0)
    if sp_gain:
        params["sp"] = restore_sp(p, sp_gain)
    ex_cure = int(rewards.get("exhaustion_cure", 0) or 0)
    if ex_cure:
        old_ex = int(getattr(p, "exhaustion", 0) or 0)
        new_ex = reduce_exhaustion(p, ex_cure)
        params["cured"] = max(0, old_ex - new_ex)
    buff = rewards.get("buff")
    if isinstance(buff, (list, tuple)) and len(buff) == 2:
        add_persistent_buff(p, str(buff[0]), int(buff[1]))
    item_id = str(rewards.get("item", "") or "")
    if item_id:
        ok, _ = add_bag_item(p, item_id)
        if not ok:
            fm = getattr(run, "floor_map", None)
            if fm is not None:
                coord = fm.player_coords.get(run.user_id, "")
                room = fm.rooms.get(coord)
                if room is not None:
                    room.items.append(item_id)
        params["item"] = get_item_display_name(item_id)
    if rewards.get("card_pool"):
        from .....entities import ALL_CARDS

        cid = CardDistributor.roll_one(str(rewards["card_pool"]), run, p, None, fallback="fireball") or "fireball"
        DeckService.add_card_to_deck(p, cid)
        params["card"] = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
    if rewards.get("reveal"):
        from ..interact import _reveal_any_special

        fm = getattr(run, "floor_map", None)
        revealed = _reveal_any_special(fm, int(rewards["reveal"])) if fm is not None else []
        params["coords"] = get_locale_text("i18n_cli_core.list_separator").join(revealed)
    if rewards.get("free_upgrade"):
        from .....data.cards.card_upgrade_data import CARD_UPGRADE_CONFIG
        from .....entities import ALL_CARDS
        import copy

        unupgraded = [c for c in p.deck if not c.upgraded and c.id in CARD_UPGRADE_CONFIG]
        if unupgraded:
            c = unupgraded[0]
            old_name = ALL_CARDS[c].name
            up = copy.copy(c)
            up.upgraded = True
            p.deck.remove(c)
            p.deck.append(up)
            params["old"] = old_name
            params["new"] = ALL_CARDS[up].name
        else:
            p.gold += 35
            params["gold"] = int(params.get("gold", 0)) + 35
    return params


def complete_npc_quest(run: GameRun, stats: Optional[UserStats], save_manager, uid: str, qid: str) -> Optional[TextNode]:
    cfg = NPC_QUEST_CONFIG.get(qid)
    entry = get_quest_entry(run, stats, qid)
    if cfg is None or entry is None:
        return None
    if cfg.get("objective_type") == "collect_item" and cfg.get("consume_item"):
        item_id = str(cfg.get("target_item", ""))
        if item_id in getattr(run.player, "bag_items", ()):
            run.player.bag_items.remove(item_id)
    entry["status"] = "completed"
    entry["stage"] = "completed"
    hist = entry.setdefault("history", ["accepted"])
    if "completed" not in hist:
        hist.append("completed")
    _run_quests(run)[qid] = dict(entry)
    if cfg.get("kind") == "multi" and stats is not None:
        _multi_quests(stats)[qid] = dict(entry)
    rewards = cfg.get("rewards") or {}
    params = _apply_quest_rewards(run, stats, rewards)
    if stats is not None:
        NpcMemoryStore.save_stats(save_manager, uid, stats)
    return locale_text(str(cfg.get("completed_key", "i18n_npc_crpg_core.quests.completed")), params=params)


def _matches_event(cfg: dict, event_type: str, payload: dict) -> bool:
    obj = str(cfg.get("objective_type", ""))
    if obj == "any_of":
        return any(_matches_event(sub, event_type, payload) for sub in (cfg.get("any_objectives") or ()))
    if obj != event_type:
        return False
    if event_type == "win_battles":
        req_diff = cfg.get("difficulty")
        if req_diff:
            allowed = req_diff if isinstance(req_diff, (list, tuple, set)) else [req_diff]
            if payload.get("difficulty", "normal") not in allowed:
                return False
    if event_type == "touch_props" and cfg.get("prop_ids"):
        if payload.get("prop_id") not in cfg["prop_ids"]:
            return False
    if event_type == "collect_item" and cfg.get("target_item"):
        if payload.get("item_id") != cfg["target_item"]:
            return False
    if event_type == "deliver_message" and cfg.get("target_token"):
        if payload.get("token") != cfg["target_token"]:
            return False
    if event_type == "cycle_event" and cfg.get("allowed_tokens"):
        if payload.get("token") not in cfg["allowed_tokens"]:
            return False
    return True


def record_npc_quest_event(
    run: Optional[GameRun],
    stats: Optional[UserStats],
    event_type: str,
    payload: Optional[dict] = None,
    save_manager=None,
) -> List[TextNode]:
    if run is None:
        return []
    info = dict(payload or {})
    notes: List[TextNode] = []
    run_q = _run_quests(run)
    multi = _multi_quests(stats) if stats is not None else {}
    touched_multi = False
    for qid, cfg in NPC_QUEST_CONFIG.items():
        entry = multi.get(qid) if cfg.get("kind") == "multi" and isinstance(multi.get(qid), dict) else run_q.get(qid)
        if not isinstance(entry, dict) or entry.get("status") != "active":
            continue
        if not _matches_event(cfg, event_type, info):
            continue
        token = info.get("unique_token")
        seen = entry.setdefault("seen_tokens", [])
        if token:
            if token in seen:
                continue
            seen.append(token)
        target = int(entry.get("target", cfg.get("target", 1)))
        prog = int(entry.get("progress", 0))
        if prog >= target:
            continue
        entry["progress"] = prog + 1
        if entry["progress"] >= target:
            entry["stage"] = "ready"
            hist = entry.setdefault("history", ["accepted"])
            if "ready" not in hist:
                hist.append("ready")
            ready_key = cfg.get("ready_notice_key")
            if ready_key:
                notes.append(locale_text(str(ready_key)))
        run_q[qid] = dict(entry)
        if cfg.get("kind") == "multi" and stats is not None:
            multi[qid] = dict(entry)
            touched_multi = True
    if touched_multi and stats is not None and save_manager is not None:
        NpcMemoryStore.save_stats(save_manager, run.user_id, stats)
    return notes


def render_npc_quest_entries(merged: dict) -> TextDocument:
    doc: TextDocument = []
    for qid, qdata in merged.items():
        cfg = NPC_QUEST_CONFIG.get(qid)
        if cfg is None or not isinstance(qdata, dict):
            continue
        title_str = render_text_node(locale_text(str(cfg["title_key"])))
        kind_key = "i18n_bleak_falls.quest_ui.tag_multi" if qdata.get("kind") == "multi" else "i18n_bleak_falls.quest_ui.tag_single"
        status = qdata.get("status", "active")
        status_key = "i18n_bleak_falls.quest_ui.tag_completed" if status == "completed" else "i18n_bleak_falls.quest_ui.tag_active"
        kind_str = render_text_node(locale_text(kind_key))
        status_str = render_text_node(locale_text(status_key))
        if doc:
            doc.append(RenderedText(text=""))
        doc.append(RenderedText(text=f"  {title_str} ({kind_str} · {status_str})"))
        h_prefix = render_text_node(locale_text("i18n_bleak_falls.quest_ui.history_prefix"))
        stages_map = cfg.get("stage_keys") or {}
        for skey in list(qdata.get("history") or ["accepted"]):
            lkey = stages_map.get(skey)
            if lkey:
                doc.append(RenderedText(text=f"    {h_prefix}{render_text_node(locale_text(str(lkey)))}"))
        if status == "active":
            cur_stage = str(qdata.get("stage") or "accepted")
            obj_key = (cfg.get("objective_keys") or {}).get(cur_stage)
            if obj_key:
                obj_prefix = render_text_node(locale_text("i18n_bleak_falls.quest_ui.objective_prefix"))
                obj_text = render_text_node(
                    locale_text(
                        str(obj_key),
                        params={
                            "progress": int(qdata.get("progress", 0)),
                            "target": int(qdata.get("target", cfg.get("target", 1))),
                        },
                    )
                )
                doc.append(RenderedText(text=f"    {obj_prefix}{obj_text}"))
    return doc
