import os
import re
import sqlite3
import subprocess
import sys
import time
import unittest
import uuid
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import jwt
from fastapi.testclient import TestClient
from game.data.account_config import GITHUB_BIND_REWARD_GP, RENAME_COST_GP
from game.json_codec import dumps, loads
from server.accounts import AccountStore
from server.app import create_app
from server.config import Settings
from game.test.server.base import ServerTestBase, make_settings


class ServerShellAndFeaturesTests(ServerTestBase):
    def test_web_shell_commands(self):
        help_game = self.post(
            {"command": "help", "channel": "web"}, self.web_headers("web-shell")
        ).json()
        self.assertIn("指令一览", help_game["text"])
        self.assertNotIn("可用终端命令", help_game["text"])

        game_touch = self.post(
            {"command": "touch 火盆", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertIn("在当前状态下不可用", game_touch["text"])
        self.assertNotIn("touch: 缺少文件", game_touch["text"])

        game_stat = self.post(
            {"command": "stat", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()["text"]
        self.assertIn("生涯统计", game_stat)

        game_exit = self.post(
            {"command": "exit", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertNotIn("无法退出", game_exit["text"])

        fallback_ls = self.post(
            {"command": "ls", "channel": "web"}, self.web_headers("web-shell")
        ).json()
        self.assertIn("README.md", fallback_ls["text"])
        self.assertEqual(fallback_ls["shell"]["status"], 0)

        fallback_touch = self.post(
            {"command": "touch note.txt", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertIn("在当前状态下不可用", fallback_touch["text"])
        self.assertNotIn(
            "note.txt",
            self.post(
                {"command": "ls", "channel": "web"},
                self.web_headers("web-shell"),
            ).json()["text"],
        )

        trigger = self.post(
            {"command": "bash", "channel": "web"}, self.web_headers("web-shell")
        ).json()
        self.assertIn("可用终端命令", trigger["text"])
        self.assertIn("bash", trigger["text"])
        self.assertEqual(trigger["shell"]["status"], 0)

        bash_help = self.post(
            {"command": "bash help", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertIn("可用终端命令", bash_help["text"])
        self.assertIn("优先级低于游戏指令", bash_help["text"])
        self.assertNotIn("可写：", bash_help["text"])
        self.assertNotIn("受保护：", bash_help["text"])

        bash_touch = self.post(
            {"command": "bash touch note.txt", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertEqual(bash_touch["shell"]["status"], 0)
        self.assertIn(
            "note.txt",
            self.post(
                {"command": "ls", "channel": "web"},
                self.web_headers("web-shell"),
            ).json()["text"],
        )

        unknown = self.post(
            {"command": "bash notashellcmd", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertIn("未找到命令", unknown["text"])
        self.assertEqual(unknown["shell"]["status"], 1)

        bash_listing = self.post(
            {"command": "bash ls", "channel": "web"}, self.web_headers("web-shell")
        ).json()
        self.assertTrue(bash_listing["ok"])
        self.assertIn("README.md", bash_listing["text"])
        self.assertEqual(bash_listing["shell"]["cwd"], "~")
        self.assertEqual(bash_listing["shell"]["status"], 0)

        readme = self.post(
            {"command": "cat README.md", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertNotIn("可写区域", readme["text"])
        self.assertNotIn("512 KB", readme["text"])

        self.post(
            {"command": "echo hello > note.txt", "channel": "web"},
            self.web_headers("web-shell"),
        )
        reading = self.post(
            {"command": "cat note.txt", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertIn("hello", reading["text"])

        protected = self.post(
            {"command": "rm README.md", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertTrue(protected["ok"])
        self.assertEqual(protected["shell"]["status"], 1)
        self.assertIn("权限被拒", protected["text"])

        changed = self.post(
            {"command": "cd dungeon", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertEqual(changed["shell"]["cwd"], "~/dungeon")

        cleared = self.post(
            {"command": "clear", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertTrue(cleared["clear"])

        fixed_mode = self.post(
            {"command": "mode", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertIn("模式切换指令已移除", fixed_mode["text"])

        help_text = self.post(
            {"command": "help", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()["text"]
        self.assertNotIn("mode --", help_text)
        self.assertNotIn("免前缀肉鸽模式", help_text)
        self.assertNotIn("/rogue ", help_text)

        stat_text = self.post(
            {"command": "stats", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()["text"]
        self.assertIn("生涯统计", stat_text)
        self.assertNotIn("免前缀肉鸽模式", stat_text)

        menu = self.post(
            {"command": "", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()["text"]
        self.assertNotIn("对决模式", menu)
        self.assertNotIn("/rogue ", menu)

        bash_exit = self.post(
            {"command": "bash exit", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertIn("无法退出", bash_exit["text"])
        self.assertEqual(bash_exit["shell"]["status"], 1)

        self.post(
            {"command": "start confirm", "channel": "web"},
            self.web_headers("web-shell"),
        )
        active_exit = self.post(
            {"command": "exit", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertNotIn("无法退出", active_exit["text"])
        self.assertEqual(active_exit["shell"]["status"], 0)

    def test_leaderboard_and_online_commands(self):
        high = self.post(
            {"command": "start confirm", "channel": "web", "name": "高GP"},
            self.web_headers("web-lb-high"),
        ).json()
        low = self.post(
            {"command": "start confirm", "channel": "web", "name": "低GP"},
            self.web_headers("web-lb-low"),
        ).json()
        high_uuid = self.internal_uuid(web="web-lb-high")
        low_uuid = self.internal_uuid(web="web-lb-low")
        high_stats = self.app.state.service.save_manager.load_stats(high_uuid)
        high_stats.gp = 5000
        self.app.state.service.save_manager.save_stats(high_uuid, high_stats)
        low_stats = self.app.state.service.save_manager.load_stats(low_uuid)
        low_stats.gp = 100
        self.app.state.service.save_manager.save_stats(low_uuid, low_stats)

        ranking = self.post(
            {"command": "leaderboard", "channel": "web"},
            self.web_headers("web-lb-high"),
        ).json()
        self.assertIn("GP 排行榜", ranking["text"])
        self.assertIn("高GP", ranking["text"])
        self.assertIn("5000 GP", ranking["text"])
        self.assertLess(ranking["text"].index("高GP"), ranking["text"].index("低GP"))

        online = self.post(
            {"command": "leaderboard online", "channel": "web"},
            self.web_headers("web-lb-low"),
        ).json()
        self.assertIn("当前在线玩家", online["text"])
        self.assertIn("高GP", online["text"])
        self.assertIn("低GP", online["text"])

    def test_server_output_scientific_notation_and_account_id_preservation(self):
        self.post(
            {"command": "start confirm", "channel": "im", "force": True, "name": "大数玩家"},
            self.im_headers("12345678901234"),
        )
        uid = self.internal_uuid(im="12345678901234")
        stats = self.app.state.service.save_manager.load_stats(uid)
        stats.gp = 12345678901234
        stats.total_damage = 9999999999999
        self.app.state.service.save_manager.save_stats(uid, stats)

        ranking = self.post(
            {"command": "leaderboard", "channel": "im", "force": True},
            self.im_headers("12345678901234"),
        ).json()
        self.assertIn("1.23e+13 GP", ranking["text"])
        self.assertNotIn("12345678901234 GP", ranking["text"])
        online = self.post(
            {"command": "leaderboard online", "channel": "im", "force": True},
            self.im_headers("12345678901234"),
        ).json()
        self.assertIn("1.23e+13 GP", online["text"])

        web_stat = self.post(
            {"command": "stats", "channel": "web"},
            self.guest_headers(uid, create=False),
        ).json()
        self.assertIn("1.00e+13", web_stat["text"])
        self.assertEqual(web_stat["state"]["stats"]["gp"], 12345678901234)
        self.assertEqual(web_stat["state"]["stats"]["total_damage"], "1.00e+13")

        myid = self.post(
            {"command": "我的id", "channel": "im", "force": True},
            self.im_headers("12345678901234"),
        ).json()
        self.assertIn(uid, myid["text"])

    def test_new_user_registration_enters_tutorial_and_can_skip_or_replay(self):
        first_login = self.post(
            {"command": "", "channel": "web"},
            self.web_headers("web-newbie-tutorial"),
        ).json()
        self.assertTrue(first_login["ok"])
        self.assertTrue(first_login["state"]["tutorial"])
        self.assertFalse(first_login["state"]["stats"]["tutorial_done"])
        self.assertEqual(first_login["state"]["screen"], "grid_map")
        self.assertEqual(first_login["state"]["map"]["floor"], 0)
        self.assertIn("新手试炼回廊", first_login["text"])
        self.assertIn("向导长老", first_login["text"])

        talk = self.post(
            {"command": "talk 向导长老", "channel": "web"},
            self.web_headers("web-newbie-tutorial"),
        ).json()
        self.assertEqual(talk["state"]["screen"], "room_dialog")
        self.assertTrue(len(talk["state"]["options"]) >= 4)

        skipped = self.post(
            {"command": "4", "channel": "web"},
            self.web_headers("web-newbie-tutorial"),
        ).json()
        self.assertIn("已跳过新手教程", skipped["text"])
        self.assertTrue(skipped["state"]["stats"]["tutorial_done"])
        self.assertFalse(skipped["state"]["tutorial"])
        self.assertEqual(skipped["state"]["screen"], "menu")

        town = self.post(
            {"command": "主城", "channel": "web"},
            self.web_headers("web-newbie-tutorial"),
        ).json()
        self.assertEqual(town["state"]["screen"], "town")
        elder_town = self.post(
            {"command": "talk 向导长老", "channel": "web"},
            self.web_headers("web-newbie-tutorial"),
        ).json()
        self.assertIn("重玩新手教程", elder_town["text"])
        replay_num = None
        for line in elder_town["text"].splitlines():
            if "重玩新手教程" in line and "." in line:
                replay_num = line.split(".", 1)[0].strip()
                break
        self.assertIsNotNone(replay_num)
        replayed = self.post(
            {"command": str(replay_num), "channel": "web"},
            self.web_headers("web-newbie-tutorial"),
        ).json()
        self.assertTrue(replayed["state"]["tutorial"])
        self.assertEqual(replayed["state"]["screen"], "grid_map")
        self.assertIn("再次踏入了新手试炼回廊", replayed["text"])


if __name__ == "__main__":
    unittest.main()
