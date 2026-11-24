import asyncio
import tempfile
import unittest

from game.renderer import format_large_int, format_output_numbers
from game.test.core.base import CorePlugin, run_command


class TestOutputScientificNotation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, command: str, uid: str = "sci_user") -> str:
        return asyncio.run(run_command(self.plugin, command, uid))

    

    

    def test_cli_commands_convert_over_12_digit_stats_and_gp(self):
        uid = "sci_cli_user"
        stats = self.plugin.save_manager.load_stats(uid)
        stats.gp = 1234567890123
        stats.total_damage = 98765432109876
        stats.total_kills = 999999999999
        self.plugin.save_manager.save_stats(uid, stats)

        menu_out = self.run_cmd(".rogue status", uid)
        self.assertIn("1.23e+12", menu_out)
        self.assertNotIn("1234567890123", menu_out)

        bag_out = self.run_cmd(".rogue bag", uid)
        self.assertIn("1.23e+12", bag_out)
        self.assertNotIn("1234567890123", bag_out)

        stat_out = self.run_cmd(".rogue stat", uid)
        self.assertIn("9.88e+13", stat_out)
        self.assertIn("999999999999", stat_out)
        self.assertNotIn("98765432109876", stat_out)

    def test_total_damage_saved_as_string_and_loaded_as_int(self):
        uid = "sci_save_user"
        stats = self.plugin.save_manager.load_stats(uid)
        stats.total_damage = 10 ** 400
        self.assertTrue(self.plugin.save_manager.save_stats(uid, stats))
        raw = self.plugin.save_manager.store.get_json("user_stats", uid)
        if not isinstance(raw, dict):
            self.fail("stats payload is not an object")
        self.assertIsInstance(raw["total_damage"], str)
        self.assertEqual(int(raw["total_damage"]), 10 ** 400)
        self.assertEqual(self.plugin.save_manager.load_stats(uid).total_damage, 10 ** 400)


if __name__ == "__main__":
    unittest.main()
