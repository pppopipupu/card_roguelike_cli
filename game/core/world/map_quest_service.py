import random
from collections import deque
from typing import Any, Optional

from ...data.grid_map_config import PASSABLE_ROOM_TYPES
from ...data.locale_data import get_locale_text
from ...data.map_quest_config import (
    ITEM_SURVEY_CHART,
    NPC_BRAZIER_KEEPER,
    NPC_MAP_SURVEYOR,
    PROP_NORDIC_BRAZIER,
    QUEST_ANCIENT_CARTOGRAPHER,
    QUEST_BLEAK_FALLS,
    QUEST_RUNIC_ECHOES,
    RANDOM_QUEST_CONFIG,
    TOWN_FLAG_BLEAK_ITEMS,
    TOWN_FLAG_BLEAK_OUTCOME,
    TOWN_FLAG_BLEAK_STAGE,
    TOWN_FLAG_BLEAK_STATE,
    TOWN_FLAG_BLEAK_TAVERN_READY,
    TOWN_FLAG_MULTI_QUESTS,
)
from ...models.state import GameRun, UserStats
from ..inventory.bag_service import add_bag_item
from ..text.events import JoinedText, LocaleText, RenderedText, TextDocument, locale_text
from ..text.pipeline import render_text, render_text_node
from .grid_map_generator import coord_to_xy, xy_to_coord


def _quest_store(run: GameRun) -> dict[str, Any]:
    if not isinstance(run.map_data, dict):
        run.map_data = {}
    return run.map_data.setdefault("map_quests", {})


def _multi_store(stats: UserStats) -> dict[str, Any]:
    if not isinstance(stats.town_flags, dict):
        stats.town_flags = {}
    return stats.town_flags.setdefault(TOWN_FLAG_MULTI_QUESTS, {})


def is_bleak_falls_done_or_tavern_ready(stats: Optional[UserStats]) -> bool:
    if stats is None:
        return False
    flags = getattr(stats, "town_flags", {}) or {}
    if flags.get(TOWN_FLAG_BLEAK_STATE) == "completed":
        return True
    if flags.get(TOWN_FLAG_BLEAK_TAVERN_READY):
        return True
    return False


def _sync_single_multi_entry(run_q: dict[str, Any], multi_entry: dict[str, Any]) -> None:
    if multi_entry.get("status") == "completed":
        run_q[QUEST_ANCIENT_CARTOGRAPHER] = dict(multi_entry)
        return
    if QUEST_ANCIENT_CARTOGRAPHER not in run_q and multi_entry.get("status") == "active":
        run_q[QUEST_ANCIENT_CARTOGRAPHER] = dict(multi_entry)


def init_run_quests(run: GameRun, stats: Optional[UserStats]) -> None:
    store = _quest_store(run)
    if stats is None:
        return
    flags = getattr(stats, "town_flags", {}) or {}
    multi = flags.get(TOWN_FLAG_MULTI_QUESTS) or {}
    if isinstance(multi, dict) and QUEST_ANCIENT_CARTOGRAPHER in multi:
        _sync_single_multi_entry(store, multi[QUEST_ANCIENT_CARTOGRAPHER])
    if flags.get(TOWN_FLAG_BLEAK_STATE) != "completed" and not flags.get(TOWN_FLAG_BLEAK_TAVERN_READY):
        if QUEST_BLEAK_FALLS not in store:
            flags.pop(TOWN_FLAG_BLEAK_STAGE, None)
            if flags.get(TOWN_FLAG_BLEAK_STATE) == "active":
                flags[TOWN_FLAG_BLEAK_STATE] = ""


def _bfs_reachable(fm, blocked_coord: str) -> set[str]:
    start = xy_to_coord(0, fm.height // 2)
    if start == blocked_coord or start not in fm.rooms:
        return set()
    visited = {start}
    q = deque([start])
    while q:
        c = q.popleft()
        cx, cy = coord_to_xy(c)
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < fm.width and 0 <= ny < fm.height):
                continue
            nc = xy_to_coord(nx, ny)
            if nc in visited or nc == blocked_coord or nc not in fm.rooms:
                continue
            rt = fm.rooms[nc].room_type
            if rt in PASSABLE_ROOM_TYPES or rt == "obstacle":
                visited.add(nc)
                q.append(nc)
    return visited


def ensure_floor1_solid_wall_candidate(fm, stats: Optional[UserStats]) -> None:
    if fm is None or fm.floor_index != 1:
        return
    if fm.floor_flags.get("yog_quest") or fm.floor_flags.get("bleak_falls_zone"):
        return
    if is_bleak_falls_done_or_tavern_ready(stats):
        return
    boss_coord = xy_to_coord(fm.width - 1, fm.height // 2)
    boss_room = fm.rooms.get(boss_coord)
    if boss_room is None:
        return
    bx, by = fm.width - 1, fm.height // 2
    neighbors = []
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = bx + dx, by + dy
        if 0 <= nx < fm.width and 0 <= ny < fm.height:
            nc = xy_to_coord(nx, ny)
            if nc in fm.rooms:
                neighbors.append(nc)
    for nc in neighbors:
        if fm.rooms[nc].room_type in ("wall", "solid_wall"):
            return
    for nc in neighbors:
        r = fm.rooms[nc]
        if r.room_type not in ("empty", "obstacle", "battle", "event"):
            continue
        reachable = _bfs_reachable(fm, nc)
        if boss_coord not in reachable:
            continue
        all_critical_ok = all(
            (rc in reachable or rm.room_type in ("wall", "secret_boss"))
            for rc, rm in fm.rooms.items()
            if rc != nc and rm.room_type not in ("wall", "secret_boss")
        )
        if all_critical_ok:
            r.room_type = "wall"
            r.explored = False
            r.cleared = False
            r.npcs.clear()
            r.items.clear()
            r.props.clear()
            return


def populate_floor_quests(run: GameRun, fm, stats: Optional[UserStats]) -> None:
    if fm is None or fm.floor_flags.get("yog_quest") or fm.floor_flags.get("bleak_falls_zone"):
        return
    if fm.floor_index == 1:
        ensure_floor1_solid_wall_candidate(fm, stats)
    candidates = [
        room
        for room in fm.rooms.values()
        if room.room_type == "empty" and not room.npcs and not room.landmark_id
    ]
    if not candidates:
        return
    seed_token = f"{run.user_id}:{fm.floor_index}:{','.join(r.room_type for r in fm.rooms.values())}"
    local_rng = random.Random(seed_token)
    local_rng.shuffle(candidates)
    store = _quest_store(run)
    placed_coords = set()

    if QUEST_RUNIC_ECHOES not in store and candidates and local_rng.random() < 0.7:
        room = candidates.pop(0)
        room.npcs.append(NPC_BRAZIER_KEEPER)
        placed_coords.add(room.coord)

    brazier_rooms = [
        room
        for room in fm.rooms.values()
        if room.room_type in ("empty", "battle", "event")
        and room.coord not in placed_coords
        and PROP_NORDIC_BRAZIER not in room.props
    ]
    local_rng.shuffle(brazier_rooms)
    for r in brazier_rooms[:2]:
        r.props.append(PROP_NORDIC_BRAZIER)

    carto_multi = (_multi_store(stats).get(QUEST_ANCIENT_CARTOGRAPHER) if stats else None) or {}
    carto_done = carto_multi.get("status") == "completed"
    if not carto_done and candidates and local_rng.random() < 0.65:
        room = candidates.pop(0)
        room.npcs.append(NPC_MAP_SURVEYOR)


def get_bleak_falls_entry(run: Optional[GameRun], stats: Optional[UserStats]) -> Optional[dict[str, Any]]:
    if run is not None:
        q = _quest_store(run).get(QUEST_BLEAK_FALLS)
        if q:
            return q
    if stats is None:
        return None
    flags = getattr(stats, "town_flags", {}) or {}
    state = flags.get(TOWN_FLAG_BLEAK_STATE)
    stage = flags.get(TOWN_FLAG_BLEAK_STAGE)
    outcome = flags.get(TOWN_FLAG_BLEAK_OUTCOME)
    if state == "completed":
        end_stage = "done_kept" if outcome == "kept" else "done_returned"
        return {
            "kind": "multi",
            "status": "completed",
            "stage": end_stage,
            "history": [
                "need_bomb",
                "wall_breached",
                "in_barrow",
                "got_claw",
                "in_sanctuary",
                "door_opened",
                "dragonstone_taken",
                "back_on_surface",
                "tavern_ready",
                end_stage,
            ],
        }
    if flags.get(TOWN_FLAG_BLEAK_TAVERN_READY):
        return {
            "kind": "multi",
            "status": "active",
            "stage": "tavern_ready",
            "history": [
                "need_bomb",
                "wall_breached",
                "in_barrow",
                "got_claw",
                "in_sanctuary",
                "door_opened",
                "dragonstone_taken",
                "back_on_surface",
                "tavern_ready",
            ],
        }
    if state == "active" and stage:
        return {
            "kind": "multi",
            "status": "active",
            "stage": stage,
            "history": [stage],
        }
    return None


def update_bleak_falls_stage(run: GameRun, stats: Optional[UserStats], stage: str, status: str = "active") -> None:
    store = _quest_store(run)
    entry = store.setdefault(
        QUEST_BLEAK_FALLS,
        {
            "kind": "multi",
            "status": status,
            "stage": stage,
            "history": [],
        },
    )
    entry["status"] = status
    entry["stage"] = stage
    hist = entry.setdefault("history", [])
    if stage not in hist:
        hist.append(stage)
    if stats is not None:
        if not isinstance(stats.town_flags, dict):
            stats.town_flags = {}
        stats.town_flags[TOWN_FLAG_BLEAK_STATE] = status
        stats.town_flags[TOWN_FLAG_BLEAK_STAGE] = stage
        multi = _multi_store(stats)
        multi[QUEST_BLEAK_FALLS] = dict(entry)


def record_room_explored(run: GameRun, stats: Optional[UserStats]) -> None:
    store = _quest_store(run)
    echoes = store.get(QUEST_RUNIC_ECHOES)
    if echoes and echoes.get("status") == "active":
        target = int(echoes.get("target", 3))
        prog = int(echoes.get("progress", 0))
        if prog < target:
            echoes["progress"] = prog + 1
    carto = store.get(QUEST_ANCIENT_CARTOGRAPHER)
    if carto and carto.get("status") == "active":
        target = int(carto.get("target", 5))
        prog = int(carto.get("progress", 0))
        if prog < target:
            carto["progress"] = prog + 1
        if stats is not None:
            _multi_store(stats)[QUEST_ANCIENT_CARTOGRAPHER] = dict(carto)


def record_brazier_lit(run: GameRun) -> None:
    store = _quest_store(run)
    echoes = store.get(QUEST_RUNIC_ECHOES)
    if echoes and echoes.get("status") == "active":
        target = int(echoes.get("target", 3))
        prog = int(echoes.get("progress", 0))
        if prog < target:
            echoes["progress"] = prog + 1


def record_battle_won(run: GameRun, stats: Optional[UserStats], is_elite_or_boss: bool) -> None:
    if not is_elite_or_boss:
        return
    store = _quest_store(run)
    carto = store.get(QUEST_ANCIENT_CARTOGRAPHER)
    if carto and carto.get("status") == "active":
        target = int(carto.get("target", 5))
        prog = int(carto.get("progress", 0))
        if prog < target:
            carto["progress"] = prog + 1
        if stats is not None:
            _multi_store(stats)[QUEST_ANCIENT_CARTOGRAPHER] = dict(carto)


def sync_run_to_stats(run: GameRun, stats: Optional[UserStats]) -> None:
    if run is None or stats is None:
        return
    store = (run.map_data or {}).get("map_quests") or {}
    multi = _multi_store(stats)
    carto = store.get(QUEST_ANCIENT_CARTOGRAPHER)
    if carto:
        multi[QUEST_ANCIENT_CARTOGRAPHER] = dict(carto)
    bleak = store.get(QUEST_BLEAK_FALLS)
    if not isinstance(stats.town_flags, dict):
        stats.town_flags = {}
    if bleak:
        completed_barrow = bool(bleak.get("completed_barrow"))
        stage = bleak.get("stage", "")
        if completed_barrow or stage in ("dragonstone_taken", "back_on_surface", "tavern_ready"):
            if stats.town_flags.get(TOWN_FLAG_BLEAK_STATE) != "completed":
                stats.town_flags[TOWN_FLAG_BLEAK_TAVERN_READY] = True
                stats.town_flags[TOWN_FLAG_BLEAK_STATE] = "active"
                stats.town_flags[TOWN_FLAG_BLEAK_STAGE] = "tavern_ready"
                hist = list(bleak.get("history") or [])
                if "tavern_ready" not in hist:
                    hist.append("tavern_ready")
                bleak["stage"] = "tavern_ready"
                bleak["history"] = hist
                multi[QUEST_BLEAK_FALLS] = dict(bleak)
                carried = list(bleak.get("barrow_items") or [])
                if carried:
                    saved = list(stats.town_flags.get(TOWN_FLAG_BLEAK_ITEMS) or [])
                    for item_id in carried:
                        if item_id not in saved:
                            saved.append(item_id)
                        if item_id not in stats.town_inventory:
                            stats.town_inventory.append(item_id)
                    stats.town_flags[TOWN_FLAG_BLEAK_ITEMS] = saved
        elif stats.town_flags.get(TOWN_FLAG_BLEAK_STATE) != "completed" and not stats.town_flags.get(TOWN_FLAG_BLEAK_TAVERN_READY):
            stats.town_flags[TOWN_FLAG_BLEAK_STATE] = ""
            stats.town_flags.pop(TOWN_FLAG_BLEAK_STAGE, None)
            multi.pop(QUEST_BLEAK_FALLS, None)


def _quest_doc_entry(qid: str, qdata: dict[str, Any]) -> TextDocument:
    kind_key = "i18n_bleak_falls.quest_ui.tag_multi" if qdata.get("kind") == "multi" else "i18n_bleak_falls.quest_ui.tag_single"
    status = qdata.get("status", "active")
    status_key = "i18n_bleak_falls.quest_ui.tag_completed" if status == "completed" else "i18n_bleak_falls.quest_ui.tag_active"
    title_str = get_locale_text(f"i18n_bleak_falls.quests.{qid}.title")
    kind_str = get_locale_text(kind_key)
    status_str = get_locale_text(status_key)
    header = RenderedText(text=f"  {title_str} ({kind_str} · {status_str})")
    nodes: TextDocument = [header]
    history = list(qdata.get("history") or [])
    if not history and qdata.get("stage"):
        history = [qdata["stage"]]
    h_prefix = get_locale_text("i18n_bleak_falls.quest_ui.history_prefix")
    for stage_key in history:
        stage_text = get_locale_text(f"i18n_bleak_falls.quests.{qid}.stages.{stage_key}")
        nodes.append(RenderedText(text=f"    {h_prefix}{stage_text}"))
    if status == "active":
        cur_stage = qdata.get("stage") or (history[-1] if history else "accepted")
        obj_text = get_locale_text(
            f"i18n_bleak_falls.quests.{qid}.objectives.{cur_stage}",
            progress=int(qdata.get("progress", 0)),
            target=int(qdata.get("target", RANDOM_QUEST_CONFIG.get(qid, {}).get("target", 1))),
        )
        if obj_text and not obj_text.startswith("i18n_bleak_falls."):
            obj_prefix = get_locale_text("i18n_bleak_falls.quest_ui.objective_prefix")
            nodes.append(RenderedText(text=f"    {obj_prefix}{obj_text}"))
    return nodes


def render_map_quests(stats: Optional[UserStats], run: Optional[GameRun] = None) -> str:
    merged: dict[str, dict[str, Any]] = {}
    if stats is not None:
        multi = (getattr(stats, "town_flags", {}) or {}).get(TOWN_FLAG_MULTI_QUESTS) or {}
        if isinstance(multi, dict):
            for qid, qval in multi.items():
                if isinstance(qval, dict) and qid != QUEST_BLEAK_FALLS:
                    merged[qid] = dict(qval)
    if run is not None:
        run_quests = (getattr(run, "map_data", {}) or {}).get("map_quests") or {}
        for qid, qval in run_quests.items():
            if isinstance(qval, dict) and qid != QUEST_BLEAK_FALLS:
                merged[qid] = dict(qval)
    bleak_entry = get_bleak_falls_entry(run, stats)
    if bleak_entry is not None:
        ordered: dict[str, dict[str, Any]] = {QUEST_BLEAK_FALLS: bleak_entry}
        ordered.update(merged)
        merged = ordered
    if not merged:
        return ""
    doc: TextDocument = [locale_text("i18n_bleak_falls.quest_ui.section_map_quests")]
    for idx, (qid, qdata) in enumerate(merged.items()):
        if idx > 0:
            doc.append(RenderedText(text=""))
        doc.extend(_quest_doc_entry(qid, qdata))
    return render_text(doc, "battle")


def give_item_or_drop(run: GameRun, room, item_id: str) -> tuple[bool, bool]:
    ok, _ = add_bag_item(run.player, item_id)
    if ok:
        return True, False
    if room is not None:
        room.items.append(item_id)
        return False, True
    return False, False


def accept_random_quest(run: GameRun, stats: Optional[UserStats], qid: str) -> dict[str, Any]:
    cfg = RANDOM_QUEST_CONFIG[qid]
    store = _quest_store(run)
    entry = {
        "kind": cfg["kind"],
        "status": "active",
        "stage": "accepted",
        "history": ["accepted"],
        "progress": 0,
        "target": int(cfg["target"]),
    }
    store[qid] = entry
    if cfg["kind"] == "multi" and stats is not None:
        _multi_store(stats)[qid] = dict(entry)
    return entry


def complete_random_quest(run: GameRun, stats: Optional[UserStats], qid: str) -> str:
    cfg = RANDOM_QUEST_CONFIG[qid]
    store = _quest_store(run)
    entry = store.get(qid) or {}
    entry["status"] = "completed"
    entry["stage"] = "completed"
    hist = entry.setdefault("history", ["accepted"])
    if "completed" not in hist:
        hist.append("completed")
    store[qid] = entry
    if qid == QUEST_RUNIC_ECHOES:
        gold = int(cfg["reward_gold"])
        heal = int(cfg["reward_heal"])
        run.player.gold += gold
        run.player.hp = min(run.player.max_hp, run.player.hp + heal)
        return render_text_node(locale_text("i18n_bleak_falls.npcs.brazier_keeper.reward", params={"gold": gold}))
    gold = int(cfg["reward_gold"])
    gp = int(cfg["reward_gp"])
    run.player.gold += gold
    if stats is not None:
        stats.gp += gp
        _multi_store(stats)[qid] = dict(entry)
    add_bag_item(run.player, ITEM_SURVEY_CHART)
    return render_text_node(locale_text("i18n_bleak_falls.npcs.map_surveyor.reward", params={"gold": gold}))
