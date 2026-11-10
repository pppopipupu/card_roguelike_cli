import asyncio
import random
import tempfile
import unittest

from game.test.core.base import CorePlugin, run_command


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
        run = self.plugin.save_manager.load_save(uid)
        options = run.node_data.get("options", [])
        battle_index = next(
            (index + 1 for index, option in enumerate(options) if option.get("node_type") == "battle"),
            None,
        )
        self.assertIsNotNone(battle_index)
        self.run_cmd(f"c {battle_index}", uid)
        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "battle")
        self.run_cmd("p 1", uid)
        result = self.run_cmd("logs 10", uid)
        self.assertIn("最近", result)
        self.assertIn("start confirm", result)
        self.assertIn("战斗", result)
        self.assertIn("p 1", result)
        self.assertIn("造成", result)
        short = self.run_cmd("logs 2", uid)
        self.assertIn("最近 2 条", short)
        self.assertIn("p 1", short)
        self.assertNotIn("start confirm", short)

    def test_logs_default_and_maximum(self):
        uid = "logs_limit_user"
        for _ in range(55):
            self.run_cmd("mode", uid)
        result = self.run_cmd("logs", uid)
        self.assertIn("最近 20 条", result)
        maximum = self.run_cmd("logs 999", uid)
        self.assertIn("最近 50 条", maximum)
        invalid = self.run_cmd("logs 0", uid)
        self.assertIn("必须是", invalid)
        invalid_text = self.run_cmd("logs abc", uid)
        self.assertIn("必须是", invalid_text)

    def test_queue_command_limit(self):
        uid = "queue_limit_user"
        commands = ",".join(["mode"] * 51)
        result = self.run_cmd(f"q [{commands}]", uid)
        self.assertIn("最多支持 50 条命令", result)
        stats = self.plugin.save_manager.load_stats(uid)
        self.assertFalse(stats.rogue_mode)
