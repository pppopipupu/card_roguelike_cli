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

    def test_threshold_12_digits_vs_13_digits(self):
        self.assertEqual(format_large_int(999999999999), "999999999999")
        self.assertEqual(format_large_int(-999999999999), "-999999999999")
        self.assertEqual(format_large_int(1000000000000), "1.00e+12")
        self.assertEqual(format_large_int(-1000000000000), "-1.00e+12")
        self.assertEqual(format_large_int(9995000000000), "1.00e+13")
        self.assertEqual(format_large_int(10 ** 5000), "1.00e+5000")

    def test_output_stream_formats_large_game_integers_and_keeps_protected_tokens(self):
        raw = (
            "生命: 12345678901234/9999999999999 护盾: 999999999999 "
            "动作: 1000000000000A 2000000000000BA "
            "Buff: 力量 x1234567890123 坚盾(1000000000000,9999999999999) "
            "负面: -1234567890123 "
            "Boss: 0x7FFFFFFFFFFFFFFF "
            "UUID: 550e8400-e29b-41d4-a716-001122334455 "
            "小数: 3.141592653589793 1234567890123.45 "
            "科学: 1.23e+12 "
            "编码: 0000000000001 token_1234567890123"
        )
        formatted = format_output_numbers(raw)
        self.assertIn("生命: 1.23e+13/1.00e+13", formatted)
        self.assertIn("护盾: 999999999999", formatted)
        self.assertIn("动作: 1.00e+12A 2.00e+12BA", formatted)
        self.assertIn("Buff: 力量 x1.23e+12", formatted)
        self.assertIn("坚盾(1.00e+12,1.00e+13)", formatted)
        self.assertIn("负面: -1.23e+12", formatted)
        self.assertIn("0x7FFFFFFFFFFFFFFF", formatted)
        self.assertIn("550e8400-e29b-41d4-a716-001122334455", formatted)
        self.assertIn("3.141592653589793", formatted)
        self.assertIn("1234567890123.45", formatted)
        self.assertIn("1.23e+12", formatted)
        self.assertIn("0000000000001", formatted)
        self.assertIn("token_1234567890123", formatted)
        self.assertEqual(format_output_numbers(formatted), formatted)

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


if __name__ == "__main__":
    unittest.main()
