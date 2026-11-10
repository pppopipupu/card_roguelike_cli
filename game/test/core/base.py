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
