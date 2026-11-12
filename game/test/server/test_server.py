import json
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
from server.accounts import AccountStore
from server.app import create_app
from server.config import Settings


def make_settings(root: Path) -> Settings:
    return Settings(
        data_dir=root,
        db_path=root / "accounts.sqlite3",
        player_dir=root / "players",
        supabase_url="https://example.supabase.co",
        supabase_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
        supabase_jwt_issuer="https://example.supabase.co/auth/v1",
        supabase_jwt_audience="authenticated",
        supabase_jwt_secret="test-secret-0123456789abcdef0123456789abcdef",
        im_token="im-secret",
        origin_key="",
        allowed_origins=("http://testserver",),
        im_prefixes=(".rogue", "/rogue"),
    )


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.settings = make_settings(Path(self.tmp.name))
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.state.service.accounts.close()
        self.tmp.cleanup()

    def web_headers(self, subject: str = "web-user-1") -> dict:
        token = jwt.encode(
            {
                "sub": subject,
                "aud": "authenticated",
                "iss": self.settings.supabase_jwt_issuer,
                "exp": int(time.time()) + 3600,
            },
            self.settings.supabase_jwt_secret,
            algorithm="HS256",
        )
        return {"Authorization": f"Bearer {token}"}

    def im_headers(self, user: str = "im-user-1") -> dict:
        return {"X-Rogue-IM-Token": "im-secret", "X-Rogue-IM-User": user}

    def guest_headers(self, guest_id: str, create: bool = True) -> dict:
        headers = {"X-Rogue-Guest-Id": guest_id}
        if create:
            headers["X-Rogue-Guest-Create"] = "1"
        return headers

    def guest_login(self, name: str, guest_id: str = "") -> tuple[str, dict]:
        guest_id = guest_id or str(uuid.uuid4())
        body = self.post(
            {"command": "", "channel": "web", "name": name},
            self.guest_headers(guest_id),
        ).json()
        return guest_id, body

    def post(self, payload: dict, headers: dict):
        return self.client.post("/api/v1/action", json=payload, headers=headers)

    def internal_uuid(self, web: str = "", im: str = "") -> str:
        store = self.app.state.service.accounts
        account = store.get_by_web(web) if web else store.get_by_im(im)
        return account["uuid"]

    def test_health(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_missing_auth_rejected(self):
        response = self.post({"command": "start", "channel": "web"}, {})
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["ok"])

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

    def test_web_state_and_uuid(self):
        start = self.post(
            {"command": "start confirm", "channel": "web"}, self.web_headers()
        ).json()
        self.assertTrue(start["ok"])
        self.assertIsNotNone(start["state"])
        self.assertEqual(start["state"]["screen"], "start_ancient")
        self.assertEqual(start["state"]["player"]["hp"], 45)
        self.assertTrue(start["state"]["options"])

        uuid_body = self.post(
            {"command": "uuid", "channel": "web"}, self.web_headers()
        ).json()
        self.assertIn(start["account"]["id"], uuid_body["text"])
        stats = self.app.state.service.save_manager.load_stats(
            self.internal_uuid(web="web-user-1")
        )
        self.assertTrue(stats.rogue_mode)

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

    def test_bind_code_links_im(self):
        web = self.post(
            {"command": "", "channel": "web"}, self.web_headers("web-bind")
        ).json()
        code_body = self.post(
            {"command": "绑定码", "channel": "web"}, self.web_headers("web-bind")
        ).json()
        match = re.search(r"绑定码：([A-Z0-9]{8})", code_body["text"])
        self.assertIsNotNone(match)
        code = match.group(1)

        im = self.post(
            {"command": f"start {code}", "channel": "im", "force": True},
            self.im_headers("im-bind-target"),
        ).json()
        self.assertTrue(im["ok"])
        self.assertEqual(im["account"]["uuid"], web["account"]["uuid"])
        self.assertEqual(im["account"]["im_user_id"], "im-bind-target")
        self.assertEqual(im["account"]["web_user_id"], "web-bind")
        self.assertIn("已关联网页账号", im["text"])

        reused = self.post(
            {"command": f"start {code}", "channel": "im", "force": True},
            self.im_headers("im-bind-other"),
        ).json()
        self.assertFalse(reused["ok"])
        self.assertEqual(reused["error"], "bind_code")
        self.assertIsNone(self.app.state.service.accounts.get_by_im("im-bind-other"))

        bad = self.post(
            {"command": "start ZZZZZZZZ", "channel": "im", "force": True},
            self.im_headers("im-bind-bad"),
        ).json()
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["error"], "bind_code")

        malformed = self.post(
            {"command": "start 随便", "channel": "im", "force": True},
            self.im_headers("im-bind-malformed"),
        ).json()
        self.assertFalse(malformed["ok"])
        self.assertEqual(malformed["error"], "bind_code")
        self.assertIsNone(
            self.app.state.service.accounts.get_by_im("im-bind-malformed")
        )

        uuid_hint = self.post(
            {"command": f"start {uuid.uuid4()}", "channel": "im", "force": True},
            self.im_headers("im-bind-uuid"),
        ).json()
        self.assertFalse(uuid_hint["ok"])
        self.assertIn("UUID 不能直接用于即时通讯登录", uuid_hint["text"])
        self.assertIsNone(
            self.app.state.service.accounts.get_by_im("im-bind-uuid")
        )

        render = self.post(
            {"command": "", "channel": "web"}, self.web_headers("web-bind")
        ).json()
        self.assertIsNotNone(render["state"])
        self.assertIsNotNone(render["state"]["player"])

    def _grant_admin(self, identity: str, value: bool = True) -> None:
        self.app.state.service.accounts.set_admin_by_identity(identity, value)

    def test_admin_requires_is_admin_field(self):
        denied = self.post(
            {"command": "admin accounts", "channel": "web"}, self.web_headers()
        ).json()
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"], "admin_required")
        self.assertFalse(denied["account"]["is_admin"])

        legacy = self.post(
            {"command": "admin accounts", "channel": "web"},
            {**self.web_headers(), "X-Rogue-Admin-Token": "admin-secret"},
        ).json()
        self.assertFalse(legacy["ok"])
        self.assertEqual(legacy["error"], "admin_required")

        name_only = self.post(
            {"command": "admin accounts", "channel": "web", "name": "pppopipupu"},
            self.web_headers("web-user-1"),
        ).json()
        self.assertFalse(name_only["ok"])
        self.assertEqual(name_only["error"], "admin_required")

    def test_admin_grant_and_revoke(self):
        self.post({"command": "uuid", "channel": "web"}, self.web_headers("web-admin"))
        self._grant_admin("web-admin")

        allowed = self.post(
            {"command": "admin accounts", "channel": "web"}, self.web_headers("web-admin")
        ).json()
        self.assertTrue(allowed["ok"])
        self.assertIn("UUID", allowed["text"])
        self.assertTrue(allowed["account"]["is_admin"])

        self._grant_admin("web-admin", False)
        revoked = self.post(
            {"command": "admin accounts", "channel": "web"}, self.web_headers("web-admin")
        ).json()
        self.assertFalse(revoked["ok"])
        self.assertEqual(revoked["error"], "admin_required")

    def test_admin_field_persists_in_store(self):
        store = self.app.state.service.accounts
        self.post({"command": "uuid", "channel": "web"}, self.web_headers("web-persist"))
        self.assertFalse(store.get_by_web("web-persist")["is_admin"])
        self._grant_admin("web-persist")
        self.assertTrue(store.get_by_web("web-persist")["is_admin"])

    def test_rogueadmin_requires_is_admin_field(self):
        denied = self.post(
            {"command": "rogueadmin boss", "channel": "web"}, self.web_headers()
        ).json()
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"], "admin_required")

        self.post({"command": "uuid", "channel": "web"}, self.web_headers("web-rogueadmin"))
        self._grant_admin("web-rogueadmin")
        allowed = self.post(
            {"command": "rogueadmin boss", "channel": "web"},
            self.web_headers("web-rogueadmin"),
        ).json()
        self.assertTrue(allowed["ok"])
        self.assertIn("最终BOSS", allowed["text"])

    def test_im_admin_requires_is_admin_field(self):
        denied = self.post(
            {"command": "rogueadmin boss", "channel": "im", "force": True},
            self.im_headers("im-user-1"),
        ).json()
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"], "admin_required")
        self.assertIsNone(self.app.state.service.accounts.get_by_im("im-user-1"))

        self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("im-admin"),
        )
        self._grant_admin("im-admin")
        allowed = self.post(
            {"command": "rogueadmin boss", "channel": "im", "force": True},
            self.im_headers("im-admin"),
        ).json()
        self.assertTrue(allowed["ok"])
        self.assertIn("最终BOSS", allowed["text"])

    def test_guest_login_cross_device_and_duplicate_handles(self):
        guest_id, body = self.guest_login("小明")
        self.assertTrue(body["ok"])
        self.assertFalse(body["account"]["is_formal"])
        self.assertEqual(body["account"]["id"], "小明")
        self.assertIn("游客账号", body["text"])
        self.assertIn("UUID", body["text"])

        same = self.post(
            {"command": "uuid", "channel": "web"},
            self.guest_headers(guest_id, create=False),
        ).json()
        self.assertEqual(same["account"]["uuid"], guest_id)
        self.assertEqual(same["account"]["id"], "小明")
        self.assertIn(guest_id, same["text"])
        self.assertIn("鉴权文件", same["text"])

        _, second = self.guest_login("小明")
        self.assertEqual(second["account"]["id"], "小明#2")

        missing = self.post(
            {"command": "", "channel": "web"},
            self.guest_headers(str(uuid.uuid4()), create=False),
        )
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.json()["error"], "guest_invalid")

    def test_github_bind_rewards_and_formalizes_guest(self):
        guest_id, guest = self.guest_login("游客甲")
        account_uuid = guest["account"]["uuid"]
        self.assertEqual(
            self.app.state.service.save_manager.load_stats(account_uuid).gp, 0
        )
        headers = {
            **self.web_headers("web-guest-bind"),
            **self.guest_headers(guest_id, create=False),
        }
        bound = self.post(
            {"command": "", "channel": "web", "name": "游客甲"}, headers
        ).json()
        self.assertTrue(bound["account"]["is_formal"])
        self.assertEqual(bound["account"]["uuid"], account_uuid)
        self.assertEqual(bound["account"]["web_user_id"], "web-guest-bind")
        self.assertIn("1000", bound["text"])
        self.assertIn("GitHub", bound["text"])
        stats = self.app.state.service.save_manager.load_stats(account_uuid)
        self.assertEqual(stats.gp, GITHUB_BIND_REWARD_GP)

        again = self.post(
            {"command": "", "channel": "web", "name": "游客甲"}, headers
        ).json()
        self.assertTrue(again["ok"])
        stats = self.app.state.service.save_manager.load_stats(account_uuid)
        self.assertEqual(stats.gp, GITHUB_BIND_REWARD_GP)

    def test_rename_costs_gp_and_rejects_duplicates(self):
        first = self.post(
            {"command": "改名 同名", "channel": "web"},
            self.web_headers("web-rename-a"),
        ).json()
        self.assertTrue(first["ok"])
        self.assertEqual(first["account"]["id"], "同名")
        self.assertIn("消耗 1000 GP", first["text"])
        first_uuid = first["account"]["uuid"]
        first_stats = self.app.state.service.save_manager.load_stats(first_uuid)
        self.assertEqual(first_stats.gp, GITHUB_BIND_REWARD_GP - RENAME_COST_GP)
        self.assertEqual(first_stats.player_handle, "同名")

        second_account = self.post(
            {"command": "uuid", "channel": "web"},
            self.web_headers("web-rename-b"),
        ).json()["account"]
        second_before = self.app.state.service.save_manager.load_stats(
            second_account["uuid"]
        )
        second = self.post(
            {"command": "friend name 同名", "channel": "web"},
            self.web_headers("web-rename-b"),
        ).json()
        self.assertFalse(second["ok"])
        self.assertIn("已被占用", second["text"])
        self.assertEqual(second["account"]["id"], second_account["id"])
        second_stats = self.app.state.service.save_manager.load_stats(
            second_account["uuid"]
        )
        self.assertEqual(second_stats.gp, GITHUB_BIND_REWARD_GP)
        self.assertEqual(second_stats.player_handle, second_before.player_handle)

        same = self.post(
            {"command": "改名 同名", "channel": "web"},
            self.web_headers("web-rename-a"),
        ).json()
        self.assertTrue(same["ok"])
        self.assertIn("无需改名", same["text"])
        self.assertEqual(
            self.app.state.service.save_manager.load_stats(first_uuid).gp,
            GITHUB_BIND_REWARD_GP - RENAME_COST_GP,
        )

        refused = self.post(
            {"command": "改名 新名字", "channel": "web"},
            self.web_headers("web-rename-a"),
        ).json()
        self.assertFalse(refused["ok"])
        self.assertIn("改名需要", refused["text"])

    def test_legacy_account_duplicates_get_suffix(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "accounts.sqlite3"
            conn = sqlite3.connect(db)
            conn.execute(
                """
                CREATE TABLE players (
                    id TEXT PRIMARY KEY,
                    im_user_id TEXT UNIQUE,
                    web_user_id TEXT UNIQUE,
                    display_name TEXT,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO players (id, im_user_id, web_user_id, display_name, is_admin, created_at, last_seen) VALUES (?, ?, ?, ?, 0, ?, ?)",
                ("a" * 36, None, "legacy-web-a", "同名", "2026-01-01", "2026-01-01"),
            )
            conn.execute(
                "INSERT INTO players (id, im_user_id, web_user_id, display_name, is_admin, created_at, last_seen) VALUES (?, ?, ?, ?, 0, ?, ?)",
                ("b" * 36, None, "legacy-web-b", "同名", "2026-01-02", "2026-01-02"),
            )
            conn.commit()
            conn.close()
            store = AccountStore(db, root / "players")
            try:
                rows = store.list_all()
                self.assertEqual([row["handle"] for row in rows], ["同名", "同名#2"])
                self.assertTrue(all(row["is_formal"] for row in rows))
                self.assertTrue(all(row["bind_reward_claimed"] for row in rows))
            finally:
                store.close()

    def test_origin_key_enforced(self):
        settings = replace(self.settings, origin_key="origin-secret")
        app = create_app(settings)
        client = TestClient(app)
        try:
            denied = client.post(
                "/api/v1/action",
                json={"command": "", "channel": "web"},
                headers=self.web_headers(),
            )
            self.assertEqual(denied.status_code, 403)
            self.assertEqual(denied.json()["error"], "origin")

            allowed = client.post(
                "/api/v1/action",
                json={"command": "", "channel": "web"},
                headers={**self.web_headers(), "X-Rogue-Origin-Key": "origin-secret"},
            )
            self.assertEqual(allowed.status_code, 200)
            self.assertTrue(allowed.json()["ok"])
        finally:
            app.state.service.accounts.close()

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
        self.assertIn("第 1 关", started["text"])
        self.assertIsNotNone(store.get_by_im(qq_id))
        self.assertIsNone(store.get_by_im(matrix_id))

        started_matrix = self.post(
            {"command": "/rogue 开启", "channel": "im", "force": True, "name": "矩阵用户"},
            self.im_headers(matrix_id),
        ).json()
        self.assertTrue(started_matrix["ok"])
        self.assertIsNotNone(started_matrix["account"])
        self.assertIn("第 1 关", started_matrix["text"])
        self.assertIsNotNone(store.get_by_im(matrix_id))

    def test_import_legacy_copies_saves_and_registry(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / "legacy"
            legacy.mkdir()
            (legacy / "stats_legacy-user.json").write_text(
                json.dumps({"player_name": "旧玩家", "gp": 77}, ensure_ascii=False),
                encoding="utf-8",
            )
            (legacy / "user_legacy-user.json").write_text(
                json.dumps({"screen": "menu"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (legacy / "duel_decks_legacy-user.json").write_text(
                json.dumps({"deck": ["a"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (legacy / "duel_registry.json").write_text(
                json.dumps({"legacy-user": "duel-1"}), encoding="utf-8"
            )
            (legacy / "duel_duel-1.json").write_text(
                json.dumps({"state": "x"}), encoding="utf-8"
            )
            db = root / "accounts.sqlite3"
            players = root / "players"
            csv_path = root / "migration.csv"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path.cwd())
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "server.import_legacy",
                    "--data-dir",
                    str(legacy),
                    "--db",
                    str(db),
                    "--player-dir",
                    str(players),
                    "--csv",
                    str(csv_path),
                ],
                cwd=Path.cwd(),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            store = AccountStore(db, players)
            try:
                account = store.get_by_im("legacy-user")
                self.assertIsNotNone(account)
                player_uuid = account["uuid"]
                self.assertEqual(account["display_name"], "旧玩家")
            finally:
                store.close()
            self.assertTrue((players / f"user_{player_uuid}.json").exists())
            self.assertTrue((players / f"stats_{player_uuid}.json").exists())
            self.assertTrue((players / f"duel_decks_{player_uuid}.json").exists())
            self.assertTrue((players / "duel_duel-1.json").exists())
            registry = json.loads(
                (players / "duel_registry.json").read_text(encoding="utf-8")
            )
            self.assertEqual(registry[player_uuid], "duel-1")


    def test_web_shell_commands(self):
        help_game = self.post(
            {"command": "help", "channel": "web"}, self.web_headers("web-shell")
        ).json()
        self.assertIn("指令一览", help_game["text"])
        self.assertNotIn("可用终端命令", help_game["text"])

        help_system = self.post(
            {"command": "help system", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertIn("可用终端命令", help_system["text"])
        self.assertNotIn("可写：", help_system["text"])
        self.assertNotIn("受保护：", help_system["text"])

        listing = self.post(
            {"command": "ls", "channel": "web"}, self.web_headers("web-shell")
        ).json()
        self.assertTrue(listing["ok"])
        self.assertIn("README.md", listing["text"])
        self.assertEqual(listing["shell"]["cwd"], "~")
        self.assertEqual(listing["shell"]["status"], 0)

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

        idle_exit = self.post(
            {"command": "exit", "channel": "web"},
            self.web_headers("web-shell"),
        ).json()
        self.assertIn("无法退出", idle_exit["text"])
        self.assertEqual(idle_exit["shell"]["status"], 1)

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


if __name__ == "__main__":
    unittest.main()
