import asyncio
import tempfile
import unittest

from game.test.core.base import CorePlugin, run_command
from game.models.state import EnemyState


class TestRogueHelp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.uid = "help_user"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, command, uid=None):
        return asyncio.run(run_command(self.plugin, command, uid or self.uid))

    def enter_battle(self):
        self.run_cmd("start confirm")
        run = self.plugin.save_manager.load_save(self.uid)
        run.node_type = "battle"
        run.node_data = {"options": []}
        run.enemies = [EnemyState("训练假人", 500, 500, 0), EnemyState("备用假人", 500, 500, 0)]
        self.plugin.save_manager.save_save(self.uid, run)

    def test_potion_subcommands(self):
        self.enter_battle()
        run = self.plugin.save_manager.load_save(self.uid)
        run.player.hp = 20
        run.player.potions = ["healing_potion", "fire_potion", "shield_potion"]
        self.plugin.save_manager.save_save(self.uid, run)

        listing = self.run_cmd("potion list")
        self.assertIn("治疗药水", listing)
        self.assertIn("火焰药水", listing)

        self.assertIn("回复了 10 点生命值", self.run_cmd("potion drink 1"))
        run = self.plugin.save_manager.load_save(self.uid)
        self.assertEqual(run.player.hp, 30)
        self.assertEqual(run.player.potions, ["fire_potion", "shield_potion"])

        enemy_hp_before = run.enemies[0].hp
        self.run_cmd("potion throw 1")
        run = self.plugin.save_manager.load_save(self.uid)
        self.assertEqual(run.player.potions, ["shield_potion"])
        self.assertLess(run.enemies[0].hp, enemy_hp_before)
        self.assertEqual(run.enemies[1].hp, 500)

        self.run_cmd("potion drop 1")
        run = self.plugin.save_manager.load_save(self.uid)
        self.assertEqual(run.player.potions, [])


if __name__ == "__main__":
    unittest.main()
