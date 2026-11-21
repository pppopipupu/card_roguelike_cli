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


class ServerImAndProjectionTests(ServerTestBase):
    def test_im_start_and_render(self):
        response = self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertTrue(body["handled"])
        self.assertTrue(body["text"])
        self.assertIn("已创建游客账号", body["text"])
        self.assertIsNone(body["state"])
        self.assertFalse(body["account"]["is_formal"])
        self.assertEqual(body["account"]["im_user_id"], "im-user-1")
        self.assertTrue(body["account"]["id"])

        render = self.post(
            {"command": "", "channel": "im", "force": True}, self.im_headers()
        ).json()
        self.assertTrue(render["text"])
        self.assertEqual(render["account"]["id"], body["account"]["id"])

    def test_projection_poll_returns_and_clears_feed(self):
        self.post({"command": "uuid", "channel": "web"}, self.web_headers("web-projection"))
        uuid = self.internal_uuid(web="web-projection")
        stats = self.app.state.service.save_manager.load_stats(uuid)
        stats.projection_feed = [
            {
                "player": "队友",
                "command": "使用 火球术",
                "result": "造成 12 点伤害。",
                "text": "📡 队友投影\n[队友] 使用 火球术\n造成 12 点伤害。",
            }
        ]
        self.app.state.service.save_manager.save_stats(uuid, stats)
        polled = self.post(
            {"command": "", "channel": "web", "projection_poll": True},
            self.web_headers("web-projection"),
        ).json()
        self.assertEqual(len(polled["projections"]), 1)
        self.assertIn("使用 火球术", polled["projections"][0]["text"])
        empty = self.post(
            {"command": "", "channel": "web", "projection_poll": True},
            self.web_headers("web-projection"),
        ).json()
        self.assertEqual(empty["projections"], [])
        stats = self.app.state.service.save_manager.load_stats(uuid)
        stats.pending_logs = ["💬 【队友】对你说：晚上好"]
        self.app.state.service.save_manager.save_stats(uuid, stats)
        pushed = self.post(
            {"command": "", "channel": "web", "projection_poll": True},
            self.web_headers("web-projection"),
        ).json()
        self.assertEqual(len(pushed["projections"]), 1)
        self.assertEqual(pushed["projections"][0]["kind"], "push")
        self.assertIn("晚上好", pushed["projections"][0]["text"])
        stats = self.app.state.service.save_manager.load_stats(uuid)
        self.assertEqual(stats.pending_logs, [])
        stats.projection_feed = [
            {"player": "队友", "command": "结束", "result": "回合结束。", "text": "📡 队友投影"}
        ]
        self.app.state.service.save_manager.save_stats(uuid, stats)
        action = self.post(
            {"command": "team", "channel": "web"},
            self.web_headers("web-projection"),
        ).json()
        self.assertEqual(len(action["projections"]), 1)
        stats = self.app.state.service.save_manager.load_stats(uuid)
        self.assertEqual(stats.projection_feed, [])

    def test_im_projection_poll_pushes_pending_logs(self):
        self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("im-push"),
        )
        uuid = self.internal_uuid(im="im-push")
        stats = self.app.state.service.save_manager.load_stats(uuid)
        stats.pending_logs = ["💬 【队友】对你说：组队出发"]
        self.app.state.service.save_manager.save_stats(uuid, stats)
        polled = self.post(
            {"command": "", "channel": "im", "projection_poll": True},
            self.im_headers("im-push"),
        ).json()
        self.assertEqual(len(polled["projections"]), 1)
        self.assertEqual(polled["projections"][0]["kind"], "push")
        self.assertIn("组队出发", polled["projections"][0]["text"])
        stats = self.app.state.service.save_manager.load_stats(uuid)
        self.assertEqual(stats.pending_logs, [])

    def test_im_group_rejects_projection_command(self):
        body_unreg = self.post(
            {
                "command": ".rogue projection off",
                "channel": "im",
                "force": True,
                "group": True,
            },
            self.im_headers("im-group-projection"),
        ).json()
        self.assertFalse(body_unreg["ok"])
        self.assertEqual(body_unreg["error"], "projection_group_disabled")
        self.assertIn("群聊", body_unreg["text"])
        self.assertIsNone(
            self.app.state.service.accounts.get_by_im("im-group-projection")
        )

        self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("im-group-projection"),
        )
        body = self.post(
            {
                "command": ".rogue projection off",
                "channel": "im",
                "force": True,
                "group": True,
            },
            self.im_headers("im-group-projection"),
        ).json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "projection_group_disabled")
        self.assertIn("群聊", body["text"])
        uuid = self.internal_uuid(im="im-group-projection")
        stats = self.app.state.service.save_manager.load_stats(uuid)
        self.assertTrue(stats.projection_enabled)

    def test_im_non_game_message_unhandled(self):
        body = self.post(
            {"command": "今天天气不错", "channel": "im", "force": False},
            self.im_headers(),
        ).json()
        self.assertTrue(body["ok"])
        self.assertFalse(body["handled"])
        self.assertEqual(body["text"], "")
        self.assertIsNone(body["account"])
        self.assertIsNone(self.app.state.service.accounts.get_by_im("im-user-1"))

    def test_im_mode_toggle(self):
        start = self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("im-mode"),
        ).json()
        uuid = self.internal_uuid(im="im-mode")
        stats = self.app.state.service.save_manager.load_stats(uuid)
        self.assertFalse(stats.rogue_mode)

        help_text = self.post(
            {"command": ".rogue help", "channel": "im", "force": True},
            self.im_headers("im-mode"),
        ).json()["text"]
        self.assertIn("指令一览", help_text)
        self.assertIn("切换免前缀快捷指令模式", help_text)

        enabled = self.post(
            {"command": ".rogue mode", "channel": "im", "force": True},
            self.im_headers("im-mode"),
        ).json()
        self.assertIn("免前缀肉鸽模式已开启", enabled["text"])
        self.assertTrue(
            self.app.state.service.save_manager.load_stats(uuid).rogue_mode
        )

        disabled = self.post(
            {"command": ".rogue 模式", "channel": "im", "force": True},
            self.im_headers("im-mode"),
        ).json()
        self.assertIn("免前缀肉鸽模式已关闭", disabled["text"])
        self.assertFalse(
            self.app.state.service.save_manager.load_stats(uuid).rogue_mode
        )

    def test_im_uuid_command(self):
        unreg = self.post(
            {"command": "我的ID", "channel": "im", "force": True},
            self.im_headers("im-uuid-user"),
        ).json()
        self.assertTrue(unreg["ok"])
        self.assertIsNone(unreg["account"])
        self.assertIn("start", unreg["text"])
        self.assertIsNone(self.app.state.service.accounts.get_by_im("im-uuid-user"))

        self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("im-uuid-user"),
        )
        body = self.post(
            {"command": "我的ID", "channel": "im", "force": True},
            self.im_headers("im-uuid-user"),
        ).json()
        self.assertTrue(body["ok"])
        self.assertIn("玩家 ID", body["text"])
        self.assertIn("UUID", body["text"])
        self.assertIn("鉴权文件", body["text"])
        self.assertIn(body["account"]["uuid"], body["text"])
        self.assertIsNotNone(body["account"]["id"])

    def test_im_secrets_returns_auth_uuid(self):
        unreg = self.post(
            {"command": "secrets", "channel": "im", "force": True},
            self.im_headers("im-secrets-user"),
        ).json()
        self.assertTrue(unreg["ok"])
        self.assertIsNone(unreg["account"])
        self.assertIn("start", unreg["text"])
        self.assertIsNone(self.app.state.service.accounts.get_by_im("im-secrets-user"))

        self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("im-secrets-user"),
        )
        body = self.post(
            {"command": "secrets", "channel": "im", "force": True},
            self.im_headers("im-secrets-user"),
        ).json()
        self.assertTrue(body["ok"])
        self.assertIn(self.internal_uuid(im="im-secrets-user"), body["text"])
        self.assertIn("鉴权文件", body["text"])
        self.assertEqual(body["account"]["im_user_id"], "im-secrets-user")

    def test_group_uuid_help_is_private(self):
        self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("im-group-secret"),
        )
        account_uuid = self.internal_uuid(im="im-group-secret")
        body = self.post(
            {
                "command": "我的ID",
                "channel": "im",
                "force": True,
                "group": True,
            },
            self.im_headers("im-group-secret"),
        ).json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "uuid_private_only")
        self.assertNotIn(account_uuid, body["text"])
        self.assertIsNone(body["account"])

    def test_im_only_start_creates_account(self):
        store = self.app.state.service.accounts
        qq_id = "123456789"
        matrix_id = "@alice:example.org"
        shell_root = self.settings.data_dir / "shell"

        chat = self.post(
            {"command": "大家好今天玩啥", "channel": "im", "force": False, "group": True},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(chat["ok"])
        self.assertFalse(chat["handled"])
        self.assertIsNone(chat["account"])

        poll = self.post(
            {"command": "", "channel": "im", "projection_poll": True},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(poll["ok"])
        self.assertFalse(poll["handled"])
        self.assertEqual(poll["projections"], [])
        self.assertIsNone(poll["account"])

        menu = self.post(
            {"command": "/rogue", "channel": "im", "force": True, "name": "萌新"},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(menu["ok"])
        self.assertTrue(menu["handled"])
        self.assertIsNone(menu["account"])
        self.assertIn("魔法肉鸽", menu["text"])
        self.assertIn("start", menu["text"])

        help_index = self.post(
            {"command": ".rogue help", "channel": "im", "force": False},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(help_index["handled"])
        self.assertIn("指令一览", help_index["text"])

        help_start = self.post(
            {"command": "/rogue help start", "channel": "im", "force": True},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(help_start["handled"])
        self.assertIn("start", help_start["text"])

        tut = self.post(
            {"command": "/rogue tutorial", "channel": "im", "force": True},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(tut["handled"])
        self.assertTrue(tut["text"])

        cl = self.post(
            {"command": ".rogue cl", "channel": "im", "force": False},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(cl["handled"])
        self.assertIn("更新日志", cl["text"])
        self.assertIn("第 1 /", cl["text"])

        cl_next = self.post(
            {"command": ".rogue cl 2", "channel": "im", "force": False},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(cl_next["handled"])
        self.assertIn("第 2 /", cl_next["text"])

        lb = self.post(
            {"command": "leaderboard", "channel": "im", "force": True},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(lb["handled"])
        self.assertIn("排行榜", lb["text"])

        need_start = self.post(
            {"command": ".rogue achi", "channel": "im", "force": False},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(need_start["ok"])
        self.assertTrue(need_start["handled"])
        self.assertIsNone(need_start["account"])
        self.assertIn("start", need_start["text"])

        need_start_matrix = self.post(
            {"command": "/rogue checkin", "channel": "im", "force": True},
            self.im_headers(matrix_id),
        ).json()
        self.assertTrue(need_start_matrix["handled"])
        self.assertIsNone(need_start_matrix["account"])
        self.assertIn("start", need_start_matrix["text"])

        self.assertIsNone(store.get_by_im(qq_id))
        self.assertIsNone(store.get_by_im(matrix_id))
        self.assertEqual(list(self.settings.player_dir.glob("stats_*.json")), [])
        self.assertFalse(shell_root.exists() and any(shell_root.iterdir()))

        started = self.post(
            {"command": ".rogue start", "channel": "im", "force": False, "name": "萌新"},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(started["ok"])
        self.assertTrue(started["handled"])
        self.assertIsNotNone(started["account"])
        self.assertIn("新手试炼回廊", started["text"])
        self.assertIn("向导长老", started["text"])
        self.assertIsNotNone(store.get_by_im(qq_id))
        self.assertIsNone(store.get_by_im(matrix_id))

        skipped = self.post(
            {"command": ".rogue 跳过教程", "channel": "im", "force": False},
            self.im_headers(qq_id),
        ).json()
        self.assertTrue(skipped["ok"])
        self.assertIn("已跳过新手教程", skipped["text"])

        real_start = self.post(
            {"command": ".rogue start", "channel": "im", "force": False},
            self.im_headers(qq_id),
        ).json()
        self.assertIn("契约", real_start["text"])

        started_matrix = self.post(
            {"command": "/rogue 开启", "channel": "im", "force": True, "name": "矩阵用户"},
            self.im_headers(matrix_id),
        ).json()
        self.assertTrue(started_matrix["ok"])
        self.assertIsNotNone(started_matrix["account"])
        self.assertIn("新手试炼回廊", started_matrix["text"])
        self.assertIsNotNone(store.get_by_im(matrix_id))


if __name__ == "__main__":
    unittest.main()
