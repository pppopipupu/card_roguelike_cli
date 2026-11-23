import asyncio
import random
import tempfile
import unittest

from game.test.core.base import CorePlugin, floor_of, load_run, run_command


class TestSpeedDescent(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20261123)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, cmd, sender_id=uid))

    def _unlock_yog(self, uid: str, gp: int) -> None:
        stats = self.plugin.save_manager.load_stats(uid)
        if "boss_yog_sothoth" not in stats.unlocked_achievements:
            stats.unlocked_achievements.append("boss_yog_sothoth")
        stats.gp = gp
        self.plugin.save_manager.save_stats(uid, stats)

    def test_locked_player_has_no_speed_descent_option(self):
        uid = "sd_locked"
        out = self.run_cmd("start confirm", uid)
        self.assertNotIn("速降！！", out)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "start_ancient")
        self.assertEqual(len(run.node_data.get("options", [])), 5)

    def test_speed_descent_floor2_three_picks_and_insufficient_gp(self):
        uid = "sd_f2"
        self._unlock_yog(uid, gp=50)
        start_out = self.run_cmd("start confirm", uid)
        self.assertIn("速降！！", start_out)
        run = load_run(self.plugin, uid)
        self.assertEqual(len(run.node_data.get("options", [])), 6)

        menu_out = self.run_cmd("c 6", uid)
        self.assertIn("速降至第 2 层", menu_out)
        self.assertIn("速降至第 3 层", menu_out)

        no_gp_out = self.run_cmd("c 1", uid)
        self.assertIn("GP 不足", no_gp_out)

        back_out = self.run_cmd("c 3", uid)
        self.assertIn("速降！！", back_out)

        self._unlock_yog(uid, gp=150)
        self.run_cmd("c 6", uid)
        go_out = self.run_cmd("c 1", uid)
        self.assertIn("速降启动", go_out)
        self.assertIn("第 1/3 次", go_out)

        stats_after = self.plugin.save_manager.load_stats(uid)
        self.assertEqual(stats_after.gp, 50)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "ancient")
        self.assertEqual(floor_of(run).floor_index, 2)

        pick1 = self.run_cmd("c 1", uid)
        self.assertIn("第 2/3 次", pick1)
        self.assertEqual(load_run(self.plugin, uid).node_type, "ancient")

        pick2 = self.run_cmd("c 1", uid)
        self.assertIn("第 3/3 次", pick2)
        self.assertEqual(load_run(self.plugin, uid).node_type, "ancient")

        self.run_cmd("c 1", uid)
        final_run = load_run(self.plugin, uid)
        self.assertEqual(final_run.node_type, "grid_map")
        self.assertEqual(floor_of(final_run).floor_index, 2)
        self.assertGreaterEqual(len(final_run.player.relics), 3)

    def test_speed_descent_floor3_four_picks(self):
        uid = "sd_f3"
        self._unlock_yog(uid, gp=320)
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 6", uid)
        go_out = self.run_cmd("c 2", uid)
        self.assertIn("第 1/4 次", go_out)
        self.assertEqual(self.plugin.save_manager.load_stats(uid).gp, 20)
        self.assertEqual(floor_of(load_run(self.plugin, uid)).floor_index, 3)

        for expected_next in (2, 3, 4):
            step_out = self.run_cmd("c 1", uid)
            self.assertIn(f"第 {expected_next}/4 次", step_out)
            self.assertEqual(load_run(self.plugin, uid).node_type, "ancient")

        self.run_cmd("c 1", uid)
        final_run = load_run(self.plugin, uid)
        self.assertEqual(final_run.node_type, "grid_map")
        self.assertEqual(floor_of(final_run).floor_index, 3)
        self.assertGreaterEqual(len(final_run.player.relics), 4)
