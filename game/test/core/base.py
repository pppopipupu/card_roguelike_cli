import os
import sys
import io
import unittest
import asyncio


if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from game.models.manager import SaveManager
from game.models.state import GameRun, PlayerState, EnemyState, MinionState, BuffState
from game.core.battle_engine import BattleEngine
from game.core.map_engine import MapEngine
from game.entities.cards.base import ALL_CARDS
from game.renderer.query import render_query_info
from game.core.cli_router import CLIRouter
from game.models.state import UserStats
from game.engine import GameEngine
from game.core.headless_server import HeadlessGameServer

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

async def async_move_to_room(plugin, uid: str, target_types, rally: bool = False):
    import heapq
    from game.core.grid_map_generator import coord_to_xy, xy_to_coord
    if isinstance(target_types, str):
        target_types = (target_types,)
    else:
        target_types = tuple(target_types)
    run = plugin.save_manager.load_save(uid)
    fm = run.floor_map
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
            elif nr.room_type in target_types:
                step_cost = 1
            elif nr.room_type in ("cafe", "shop", "rest", "landmark", "life_merchant"):
                step_cost = 6
            elif nr.room_type in ("treasure", "event"):
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
        run = plugin.save_manager.load_save(uid)
        if run is None:
            return last_res, None
        if run.node_type == "grid_map" and run.floor_map.player_coords.get(uid) != coord:
            last_res = await run_command(plugin, dcmd, uid)
            run = plugin.save_manager.load_save(uid)
        is_last = idx == len(path) - 1
        if is_last:
            if run and run.node_type == "battle_prompt":
                opt_cmd = "2" if rally else "1"
                last_res = await run_command(plugin, opt_cmd, uid)
                run = plugin.save_manager.load_save(uid)
            break
        if run and run.node_type == "battle_prompt":
            await run_command(plugin, "3", uid)
        elif run and run.node_type in ("shop", "rest", "cafe", "landmark", "life_merchant", "treasure"):
            await run_command(plugin, "离开", uid)
        elif run and run.node_type == "event":
            opts = run.node_data.get("options", [])
            if opts:
                await run_command(plugin, str(len(opts)), uid)
    return last_res, plugin.save_manager.load_save(uid)


def move_to_room(plugin, uid: str, target_types, rally: bool = False):
    return asyncio.run(async_move_to_room(plugin, uid, target_types, rally=rally))
