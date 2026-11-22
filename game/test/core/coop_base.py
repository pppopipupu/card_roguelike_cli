import asyncio
import random
import re
import tempfile
import unittest
from unittest.mock import patch
from game.entities.events import ALL_EVENTS
from game.test.core.base import CorePlugin, floor_of, load_run, move_to_room, run_command, walk_to_boss_battle
from game.core.party.session import SessionContextScoper
from game.data.progression.account_config import RENAME_COST_GP
from game.data.entities.gem_data import GEM_CONFIG
from game.entities.cards.base import ALL_CARDS
from game.models.state import CardState, GameRun, PlayerState


class CoopTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.random_state = random.getstate()

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, command, uid):
        return asyncio.run(run_command(self.plugin, command, uid))

    def player_id(self, uid):
        stats = self.plugin.save_manager.load_stats(uid)
        return stats.player_handle or stats.player_name

    def rename_player(self, uid, name):
        stats = self.plugin.save_manager.load_stats(uid)
        stats.gp = max(stats.gp, RENAME_COST_GP)
        self.plugin.save_manager.save_stats(uid, stats)
        result = self.run_cmd(f"friend name {name}", uid)
        self.assertIn("已修改", result)
        return self.player_id(uid)

    def make_friends(self, leader, others, suffix=""):
        self.rename_player(leader, f"队长{suffix}")
        for index, uid in enumerate(others, 1):
            self.rename_player(uid, f"队员{index}{suffix}")
            self.run_cmd(f"friend add {self.player_id(uid)}", leader)
            self.run_cmd(f"friend accept {self.player_id(leader)}", uid)

    def create_team(self, leader, others):
        result = self.run_cmd("team create", leader)
        self.assertIn("已创建队伍", result)
        match = re.search(r"队伍 ([A-Z0-9]{6})", result)
        assert match is not None, "team id must be present"
        lobby_id = match.group(1)
        for uid in others:
            invited = self.run_cmd(f"friend invite {self.player_id(uid)}", leader)
            self.assertIn("已邀请", invited)
            joined = self.run_cmd(f"team join {lobby_id}", uid)
            self.assertIn("已加入队伍", joined)
        return lobby_id

    def start_coop(self, uids):
        self._coop_run_index = getattr(self, "_coop_run_index", 0) + 1
        suffix = "" if self._coop_run_index == 1 else f"_{self._coop_run_index}"
        leader = uids[0]
        self.make_friends(leader, uids[1:], suffix)
        self.create_team(leader, uids[1:])
        for uid in uids[1:]:
            ready = self.run_cmd("team ready", uid)
            self.assertIn("已准备就绪", ready)
        random.seed(0)
        from game.data.progression.starting_deck_config import STARTING_ROLL_COUNTS
        legacy_roll_calls = 8 - sum(STARTING_ROLL_COUNTS.values())
        for _ in range(legacy_roll_calls * len(uids)):
            random.choice([0, 1])
        started = self.run_cmd("team start", leader)
        self.assertIn("已开启联机牌局", started)
        for uid in uids:
            chosen = self.run_cmd("c 1", uid)
            self.assertIn("契约达成", chosen)
        run = load_run(self.plugin, leader)
        self.assertEqual(run.node_type, "grid_map")
        self.assertEqual(len(run.players), len(uids))
        return run

    def _force_event(self, uids, event_id):
        run = load_run(self.plugin, uids[0])
        SessionContextScoper.create_session(run, "A1", "event", uids)
        explore = self.plugin.engine.map_engine.explore_engine
        event = next(e for e in ALL_EVENTS if e.id == event_id)
        with patch("game.core.world.explore_engine.random.choice", return_value=event):
            explore._init_event_node(run)
        self.plugin.save_manager.save_save(uids[0], run)
        return run

    def _event_option_index(self, run, action):
        return next(
            index + 1
            for index, option in enumerate(run.node_data.get("options", []))
            if option.get("action") == action
        )

    def enter_coop_battle(self, uids):
        run = self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        self.assertEqual(run.node_type, "battle")
        return run

    def set_hand(self, uid, states):
        run = load_run(self.plugin, uid)
        run.player = run.players[uid]
        run.players[uid].hand = list(states)
        self.plugin.save_manager.save_save(uid, run)
        return run
