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
from game.data.progression.account_config import GITHUB_BIND_REWARD_GP, RENAME_COST_GP
from game.json_codec import dumps, loads
from server.accounts import AccountStore
from server.app import create_app
from server.config import Settings
from game.test.server.base import ServerTestBase, make_settings


class ServerAuthAndAccountsTests(ServerTestBase):
    def test_health(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_missing_auth_rejected(self):
        response = self.post({"command": "start", "channel": "web"}, {})
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["ok"])

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

    def test_web_state_and_uuid(self):
        tutorial_start = self.post(
            {"command": "start confirm", "channel": "web"}, self.web_headers()
        ).json()
        self.assertTrue(tutorial_start["ok"])
        self.assertIsNotNone(tutorial_start["state"])
        self.assertEqual(tutorial_start["state"]["screen"], "grid_map")
        self.assertTrue(tutorial_start["state"]["tutorial"])
        self.assertIn("新手试炼回廊", tutorial_start["text"])

        skipped = self.post(
            {"command": "跳过教程", "channel": "web"}, self.web_headers()
        ).json()
        self.assertTrue(skipped["ok"])
        self.assertTrue(skipped["state"]["stats"]["tutorial_done"])

        start = self.post(
            {"command": "start confirm", "channel": "web"}, self.web_headers()
        ).json()
        self.assertTrue(start["ok"])
        self.assertIsNotNone(start["state"])
        self.assertEqual(start["state"]["screen"], "start_ancient")
        self.assertEqual(start["state"]["player"]["hp"], 50)
        self.assertTrue(start["state"]["options"])

        uuid_body = self.post(
            {"command": "uuid", "channel": "web"}, self.web_headers()
        ).json()
        self.assertIn(start["account"]["id"], uuid_body["text"])
        stats = self.app.state.service.save_manager.load_stats(
            self.internal_uuid(web="web-user-1")
        )
        self.assertTrue(stats.rogue_mode)

    def test_bind_code_links_im(self):
        web = self.post(
            {"command": "", "channel": "web"}, self.web_headers("web-bind")
        ).json()
        code_body = self.post(
            {"command": "绑定码", "channel": "web"}, self.web_headers("web-bind")
        ).json()
        match = re.search(r"绑定码：([A-Z0-9]{8})", code_body["text"])
        assert match is not None, "bind code must be present"
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

        jump_removed = self.post(
            {"command": ".rogueadmin jump 2", "channel": "im", "force": True},
            self.im_headers("im-admin"),
        ).json()
        self.assertTrue(jump_removed["ok"])
        self.assertIn("未知管理命令", jump_removed["text"])

    def test_rogueadmin_target_user_option_resolves_im_id(self):
        self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("admin-caller"),
        )
        self._grant_admin("admin-caller")
        self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("2655439416"),
        )
        self.post(
            {"command": "1", "channel": "im", "force": True},
            self.im_headers("2655439416"),
        )
        spawned = self.post(
            {
                "command": ".rogueadmin -u 2655439416 spawn enemy 腐化之心",
                "channel": "im",
                "force": True,
            },
            self.im_headers("admin-caller"),
        ).json()
        self.assertTrue(spawned["ok"])
        self.assertNotIn("未找到该玩家的活跃游戏存档", spawned["text"])
        self.assertIn("腐化之心", spawned["text"])

        target_acc = self.app.state.service.accounts.get_by_im("2655439416")
        self.assertIsNotNone(target_acc)
        target_run = self.app.state.service.save_manager.load_save(target_acc["uuid"])
        self.assertIsNotNone(target_run)
        self.assertEqual(target_run.node_type, "battle")
        self.assertTrue(any(e.name == "腐化之心" for e in target_run.enemies))

        missing = self.post(
            {
                "command": ".rogueadmin -u nonexistent_qq_99999 spawn enemy 腐化之心",
                "channel": "im",
                "force": True,
            },
            self.im_headers("admin-caller"),
        ).json()
        self.assertTrue(missing["ok"])
        self.assertIn("未找到玩家", missing["text"])

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

    def test_import_legacy_copies_saves_and_registry(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / "legacy"
            legacy.mkdir()
            (legacy / "stats_legacy-user.json").write_bytes(
                dumps({"player_name": "旧玩家", "gp": 77})
            )
            (legacy / "user_legacy-user.json").write_bytes(
                dumps({"screen": "menu"})
            )
            (legacy / "duel_decks_legacy-user.json").write_bytes(
                dumps({"deck": ["a"]})
            )
            (legacy / "duel_registry.json").write_bytes(
                dumps({"legacy-user": "duel-1"})
            )
            (legacy / "duel_duel-1.json").write_bytes(
                dumps({"state": "x"})
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
                if account is None:
                    self.fail("legacy account missing")
                player_uuid = account["uuid"]
                self.assertEqual(account["display_name"], "旧玩家")
            finally:
                store.close()
            self.assertTrue((players / f"user_{player_uuid}.json").exists())
            self.assertTrue((players / f"stats_{player_uuid}.json").exists())
            self.assertTrue((players / f"duel_decks_{player_uuid}.json").exists())
            self.assertTrue((players / "duel_duel-1.json").exists())
            registry = loads(
                (players / "duel_registry.json").read_bytes()
            )
            if not isinstance(registry, dict):
                self.fail("duel registry is not an object")
            self.assertEqual(registry[player_uuid], "duel-1")


if __name__ == "__main__":
    unittest.main()
