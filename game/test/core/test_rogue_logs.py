import asyncio
import random
import tempfile
import unittest

from game.test.core.base import CorePlugin, move_to_room, run_command
from game.entities.cards.base import ALL_CARDS
from game.models.state import ensure_card_state


class TestRogueLogs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.random_state = random.getstate()
        random.seed(1)
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, command, uid):
        return asyncio.run(run_command(self.plugin, command, uid))

    def test_logs_records_actions_and_battle(self):
        uid = "logs_battle_user"
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        _, run = move_to_room(self.plugin, uid, ("battle", "elite"))
        self.assertEqual(run.node_type, "battle")
        damage_idx = next(
            idx
            for idx, state in enumerate(run.player.hand, 1)
            if getattr(ALL_CARDS[ensure_card_state(state)], "base_dmg", 0) > 0
        )
        self.run_cmd(f"p {damage_idx}", uid)
        result = self.run_cmd("logs 10", uid)
        self.assertIn("最近", result)
        self.assertIn("start confirm", result)
        self.assertIn("战斗", result)
        self.assertIn(f"p {damage_idx}", result)
        self.assertIn("造成", result)
        short = self.run_cmd("logs 2", uid)
        self.assertIn("最近 2 条", short)
        self.assertIn(f"p {damage_idx}", short)
        self.assertNotIn("start confirm", short)

    
