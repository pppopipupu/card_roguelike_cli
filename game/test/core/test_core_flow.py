import asyncio
import random
import tempfile
import unittest

from game.test.core.base import CorePlugin, run_command


class TestCoreFlow(unittest.TestCase):
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

    def enter_battle(self, uid):
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        run = self.plugin.save_manager.load_save(uid)
        options = run.node_data.get("options", [])
        battle_index = next(
            (index + 1 for index, option in enumerate(options)
             if option.get("node_type") == "battle"),
            None,
        )
        self.assertIsNotNone(battle_index)
        self.run_cmd("c " + str(battle_index), uid)
        return self.plugin.save_manager.load_save(uid)

    def test_start_map_battle_and_card_resolution(self):
        uid = "flow_battle_user"
        self.run_cmd("start confirm", uid)
        run = self.plugin.save_manager.load_save(uid)
        self.assertIsNotNone(run)
        self.assertEqual(run.node_type, "start_ancient")
        self.assertEqual(run.player.stage, 1)

        self.run_cmd("c 1", uid)
        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "map_select")
        options = run.node_data.get("options", [])
        self.assertTrue(options)
        battle_index = next(
            (index + 1 for index, option in enumerate(options)
             if option.get("node_type") == "battle"),
            None,
        )
        self.assertIsNotNone(battle_index)

        self.run_cmd("c " + str(battle_index), uid)
        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "battle")
        self.assertTrue(run.player.hand)
        self.assertGreater(run.player.actions, 0)
        self.assertTrue(run.enemies)
        self.assertTrue(all(enemy.hp > 0 for enemy in run.enemies))
        actions_before = run.player.actions

        self.run_cmd("p 1", uid)
        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "battle")
        self.assertGreater(len(run.player.discard_pile), 0)
        self.assertLess(run.player.actions, actions_before)

    def test_end_turn_resolves_enemy_actions_and_resets_actions(self):
        uid = "flow_turn_user"
        run = self.enter_battle(uid)
        hp_before = run.player.hp
        self.assertGreater(run.player.actions, 0)

        self.run_cmd("p 1", uid)
        run = self.plugin.save_manager.load_save(uid)
        actions_after_card = run.player.actions

        self.run_cmd("e", uid)
        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "battle")
        self.assertGreater(run.player.actions, actions_after_card)
        self.assertLessEqual(run.player.hp, hp_before)
        self.assertTrue(run.enemies)

        hp_after_first = run.player.hp
        self.run_cmd("e", uid)
        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "battle")
        self.assertLessEqual(run.player.hp, hp_after_first)

    def test_commands_rejected_outside_battle_and_saves_isolated(self):
        uid = "flow_guard_user"
        self.run_cmd("start confirm", uid)
        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "start_ancient")

        p_res = self.run_cmd("p 1", uid)
        self.assertIn("在当前状态下不可用", p_res)
        e_res = self.run_cmd("e", uid)
        self.assertIn("在当前状态下不可用", e_res)
        self.assertEqual(
            self.plugin.save_manager.load_save(uid).node_type,
            "start_ancient",
        )

        other = "flow_guard_other"
        self.run_cmd("start confirm", other)
        self.assertEqual(
            self.plugin.save_manager.load_save(other).node_type,
            "start_ancient",
        )

        self.run_cmd("c 1", uid)
        self.assertEqual(
            self.plugin.save_manager.load_save(uid).node_type,
            "map_select",
        )
        self.assertEqual(
            self.plugin.save_manager.load_save(other).node_type,
            "start_ancient",
        )


if __name__ == "__main__":
    unittest.main()
