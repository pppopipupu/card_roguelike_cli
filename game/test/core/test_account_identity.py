import asyncio
import os
import tempfile
import unittest

from game.core.api.headless_server import HeadlessGameServer
from game.data.progression.account_config import RENAME_COST_GP
from game.json_codec import dumps
from game.test.core.base import CorePlugin, run_command


class TestAccountIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, command, uid):
        return asyncio.run(run_command(self.plugin, command, uid))

    def grant_gp(self, uid, amount):
        stats = self.plugin.save_manager.load_stats(uid)
        stats.gp = amount
        self.plugin.save_manager.save_stats(uid, stats)

    def test_rename_costs_gp_and_rejects_duplicates(self):
        first = "rename_first"
        second = "rename_second"
        self.grant_gp(first, RENAME_COST_GP)
        self.grant_gp(second, RENAME_COST_GP)

        first_result = self.run_cmd("rename 同名", first)
        self.assertIn("已修改", first_result)
        self.assertIn("消耗 1000 GP", first_result)
        first_stats = self.plugin.save_manager.load_stats(first)
        self.assertEqual(first_stats.gp, 0)
        self.assertEqual(first_stats.player_handle, "同名")

        second_before = self.plugin.save_manager.load_stats(second)
        second_result = self.run_cmd("friend name 同名", second)
        self.assertIn("已被占用", second_result)
        second_stats = self.plugin.save_manager.load_stats(second)
        self.assertEqual(second_stats.gp, RENAME_COST_GP)
        self.assertEqual(second_stats.player_handle, second_before.player_handle)

        refused = self.run_cmd("rename 另一个名字", first)
        self.assertIn("改名需要", refused)
        self.assertEqual(
            self.plugin.save_manager.load_stats(first).player_handle, "同名"
        )

    


if __name__ == "__main__":
    unittest.main()
