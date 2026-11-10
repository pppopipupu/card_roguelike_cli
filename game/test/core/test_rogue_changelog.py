import asyncio
import tempfile
import unittest

from game.test.core.base import CorePlugin, run_command
from game.models.state import EnemyState


class TestRogueChangelog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.uid = "changelog_user"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, command, uid=None):
        return asyncio.run(run_command(self.plugin, command, uid or self.uid))

    def enter_battle(self):
        self.run_cmd("start confirm")
        run = self.plugin.save_manager.load_save(self.uid)
        run.node_type = "battle"
        run.node_data = {"options": []}
        run.enemies = [EnemyState("训练假人", 500, 500, 0)]
        self.plugin.save_manager.save_save(self.uid, run)

    def test_changelog_aliases_show_recent_changes(self):
        for alias in ("changelog", "cl", "更新日志", "更新"):
            result = self.run_cmd(alias)
            self.assertIn("更新日志", result)
            self.assertIn("2026-11-11", result)
            self.assertIn("2026-11-10", result)
            self.assertIn("fastfetch", result)
            self.assertNotIn("未找到更新日志文档", result)

    def test_changelog_output_is_plain_text(self):
        result = self.run_cmd("changelog")
        self.assertIn("🔹 2026-11-11", result)
        self.assertIn("• 新增", result)
        self.assertNotIn("## ", result)
        self.assertNotIn("`", result)

    def test_help_lists_changelog(self):
        self.assertIn("changelog", self.run_cmd("help"))
        detail = self.run_cmd("help changelog")
        self.assertIn("【更新日志】", detail)
        self.assertIn("cl", detail)

    def test_changelog_available_in_battle(self):
        self.enter_battle()
        result = self.run_cmd("cl")
        self.assertIn("2026-11-11", result)
        self.assertNotIn("在当前状态下不可用", result)


if __name__ == "__main__":
    unittest.main()
