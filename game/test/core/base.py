import os
import sys
import io
import unittest
import asyncio


if sys.platform.startswith("win"):
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass
from game.models.manager import SaveManager
from game.models.state import GameRun, PlayerState, EnemyState, MinionState, BuffState, FloorMapState
from game.core.battle.engine import BattleEngine
from game.core.world.map_engine import MapEngine
from game.entities.cards.base import ALL_CARDS
from game.renderer.query import render_query_info
from game.core.cli.router import CLIRouter
from game.models.state import UserStats
from game.engine import GameEngine
from game.core.api.headless_server import HeadlessGameServer


class DummySaveManagerBase(SaveManager):
    def __init__(self):
        pass

class DummyContext:
    pass

class CorePlugin:
    def __init__(self, context=None, config=None, data_dir=None):
        self.config = config or {}
        self.server = HeadlessGameServer(data_dir)
        self.save_manager = self.server.save_manager
        self.engine = self.server.engine
        self.cli_router = self.server.cli_router

    def _prefixes(self):
        value = self.config.get("shortcut_prefix", [".rogue"])
        if isinstance(value, str):
            return [value]
        return list(value)

    async def _dispatch(self, event, force_execute: bool):
        res = await self.server.handle_rogue_message(
            user_id=event.get_sender_id(),
            sender_name="玩家",
            message=event.message_str.strip(),
            shortcut_prefix=self._prefixes(),
            enable_shortcut=self.config.get("enable_shortcut", True),
            force_execute=force_execute,
        )
        if res is not None:
            event.results.append(res)
        return res

    async def rogue(self, event):
        res = await self._dispatch(event, True)
        if res is not None:
            yield res

    async def shortcut_rogue(self, event):
        res = await self._dispatch(event, False)
        if res is not None:
            event.stop_event()

    async def rogueadmin(self, event):
        res = await self.server.handle_admin_message(event.get_sender_id(), event.message_str.strip())
        event.results.append(res)
        yield res

MyPlugin = CorePlugin

class DummyEvent:
    def __init__(self, message_str: str, sender_id: str = "test_user"):
        self.message_str = message_str
        self.sender_id = sender_id
        self.results = []
        self.stopped = False

    def get_sender_id(self) -> str:
        return self.sender_id

    def plain_result(self, text: str):
        self.results.append(text)
        return text

    def stop_event(self):
        self.stopped = True

async def run_command(plugin, cmd_str: str, sender_id: str = "test_user") -> str:
    event = DummyEvent(cmd_str, sender_id)
    await plugin.shortcut_rogue(event)
    if not event.results:
        generator = plugin.rogue(event)
        async for _ in generator:
            pass
    return "\n".join(event.results)

def require_run(run: GameRun | None) -> GameRun:
    assert run is not None, "missing save"
    return run

def load_run(plugin, uid: str) -> GameRun:
    return require_run(plugin.save_manager.load_save(uid))

def floor_of(run: GameRun) -> FloorMapState:
    fm = run.floor_map
    assert fm is not None, "missing floor map"
    return fm

async def async_move_to_room(plugin, uid: str, target_types, rally: bool = False) -> tuple[str, GameRun]:
    import heapq
    from game.core.world.grid_map_generator import coord_to_xy, xy_to_coord
    if isinstance(target_types, str):
        target_types = (target_types,)
    else:
        target_types = tuple(target_types)
    run = load_run(plugin, uid)
    fm = run.floor_map
    assert fm is not None, "missing floor map"
    start = fm.player_coords.get(uid)
    if not start:
        return "", run
    dist = {start: 0}
    prev = {}
    pq = [(0, start)]
    found = None
    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist.get(cur, 10**9):
            continue
        room = fm.rooms.get(cur)
        if cur != start and room is not None and room.room_type in target_types:
            if room.room_type in ("cafe", "shop", "rest", "landmark", "downstairs") or not room.cleared:
                found = cur
                break
        cx, cy = coord_to_xy(cur)
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < fm.width and 0 <= ny < fm.height):
                continue
            nc = xy_to_coord(nx, ny)
            nr = fm.rooms.get(nc)
            if nr is None or nr.room_type == "wall":
                continue
            if nr.room_type == "secret_boss" and not fm.secret_unlocked:
                continue
            if nr.cleared or nr.room_type in ("spawn", "empty"):
                step_cost = 1
            elif nr.room_type == "big_room":
                from game.core.world.rooms.hostile_npc import get_alive_hostile_npcs
                step_cost = 500 if get_alive_hostile_npcs(fm, nr) else 1
            elif nr.room_type in target_types:
                step_cost = 1
            elif nr.room_type in ("cafe", "shop", "rest", "landmark", "life_merchant", "treasure"):
                step_cost = 6
            elif nr.room_type in ("event",):
                step_cost = 25
            elif nr.room_type == "obstacle":
                step_cost = 50
            else:
                step_cost = 500
            nd = d + step_cost
            if nd < dist.get(nc, 10**9):
                dist[nc] = nd
                prev[nc] = cur
                heapq.heappush(pq, (nd, nc))
    if not found:
        return "", run
    path = []
    c = found
    while c != start:
        p = prev[c]
        px, py = coord_to_xy(p)
        cx, cy = coord_to_xy(c)
        dx, dy = cx - px, cy - py
        dcmd = {(0, -1): "w", (0, 1): "s", (-1, 0): "a", (1, 0): "d"}[(dx, dy)]
        path.append((c, dcmd))
        c = p
    path.reverse()
    last_res = ""
    for idx, (coord, dcmd) in enumerate(path):
        last_res = await run_command(plugin, dcmd, uid)
        run = load_run(plugin, uid)
        if run.node_type == "grid_map" and run.floor_map is not None and run.floor_map.player_coords.get(uid) != coord:
            last_res = await run_command(plugin, dcmd, uid)
            run = load_run(plugin, uid)
        is_last = idx == len(path) - 1
        if is_last:
            break
        if run.node_type in ("shop", "rest", "cafe", "landmark", "life_merchant", "treasure"):
            await run_command(plugin, "离开", uid)
        elif run.node_type == "event":
            opts = run.node_data.get("options", [])
            if opts:
                await run_command(plugin, str(len(opts)), uid)
    final_run = load_run(plugin, uid)
    if rally and final_run is not None and final_run.node_type == "ally_summon_select":
        last_res = await run_command(plugin, "c 1", uid)
        final_run = load_run(plugin, uid)
    if rally and final_run is not None and final_run.node_type == "battle":
        await _rally_teammates(plugin, uid, final_run)
        final_run = load_run(plugin, uid)
    return last_res, final_run


async def _rally_teammates(plugin, uid: str, run) -> None:
    fm = getattr(run, "floor_map", None)
    if fm is None:
        return
    coord = fm.player_coords.get(uid, "")
    if not coord:
        return
    for member in run.all_human_uids():
        if member == uid:
            continue
        member_run = load_run(plugin, member)
        if member_run is None or member_run.node_type != "grid_map":
            continue
        member_fm = getattr(member_run, "floor_map", None)
        if member_fm is None or member in member_fm.player_session_map:
            continue
        await run_command(plugin, f"tp {coord}", member)


def move_to_room(plugin, uid: str, target_types, rally: bool = False) -> tuple[str, GameRun]:
    return asyncio.run(async_move_to_room(plugin, uid, target_types, rally=rally))


def clear_battle_if_needed(plugin, uids: list[str], max_loops: int = 40) -> None:
    async def _drive():
        for _ in range(max_loops):
            progressed = False
            for uid in uids:
                run = plugin.save_manager.load_save(uid)
                if not run:
                    continue
                if run.node_type == "battle" and not run.node_data.get("coop_done"):
                    for _ in range(8):
                        r_now = plugin.save_manager.load_save(uid)
                        if not r_now or r_now.node_type != "battle" or r_now.node_data.get("coop_done"):
                            break
                        played = False
                        for idx, cs in enumerate(list(r_now.player.hand), 1):
                            card = ALL_CARDS.get(cs.id)
                            if card is None:
                                continue
                            cost_a = getattr(card, "cost_a", 0)
                            cost_ba = getattr(card, "cost_ba", 0)
                            if cost_a <= r_now.player.actions and cost_ba <= r_now.player.bonus_actions:
                                res = await run_command(plugin, f"p {idx} 1", uid)
                                if "❌" not in res:
                                    played = True
                                    progressed = True
                                    break
                        if not played:
                            break
                    r_end = plugin.save_manager.load_save(uid)
                    if r_end and r_end.node_type == "battle" and not r_end.node_data.get("coop_done"):
                        await run_command(plugin, "e", uid)
                        progressed = True
                elif run.node_type == "reward" and not run.node_data.get("coop_done"):
                    res = await run_command(plugin, "离开", uid)
                    if "必须先领取" in res or "❌" in res:
                        await run_command(plugin, "c 1", uid)
                    progressed = True
                elif run.node_type in ("card_select", "gem_insert") and not run.node_data.get("coop_done"):
                    await run_command(plugin, "c 1", uid)
                    progressed = True
                elif run.node_type == "event" and not run.node_data.get("coop_done"):
                    opts = run.node_data.get("options", [])
                    if opts:
                        await run_command(plugin, str(len(opts)), uid)
                        progressed = True
                elif run.node_type in ("shop", "rest", "treasure", "life_merchant", "landmark", "downstairs") and not run.node_data.get("coop_done"):
                    await run_command(plugin, "离开", uid)
                    progressed = True
            all_grid = True
            for uid in uids:
                r = plugin.save_manager.load_save(uid)
                if not r or r.node_type != "grid_map":
                    all_grid = False
                    break
            if all_grid:
                return
            if not progressed:
                return

    asyncio.run(_drive())


def walk_to_boss_battle(plugin, leader: str, max_steps: int = 15):
    for _ in range(max_steps):
        run = plugin.save_manager.load_save(leader)
        if run is None:
            return None
        if run.node_type != "grid_map":
            fm = getattr(run, "floor_map", None)
            coord = fm.player_coords.get(leader, "") if fm is not None else ""
            room = fm.rooms.get(coord) if fm is not None else None
            if run.node_type == "battle" and room is not None and room.room_type == "boss":
                return run
            clear_battle_if_needed(plugin, [leader])
            continue
        fm = getattr(run, "floor_map", None)
        if fm is None:
            return None
        if fm.player_coords.get(leader) == fm.boss_coord:
            return run
        move_to_room(plugin, leader, ("boss",))
    return plugin.save_manager.load_save(leader)
