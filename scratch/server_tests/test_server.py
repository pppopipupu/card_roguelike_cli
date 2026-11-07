import json
import os
import subprocess
import sys
import time
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import jwt
from fastapi.testclient import TestClient

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
        admin_token="admin-secret",
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

    def post(self, payload: dict, headers: dict):
        return self.client.post("/api/v1/action", json=payload, headers=headers)

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
        self.assertIsNone(body["state"])
        uuid = body["account"]["uuid"]
        self.assertEqual(body["account"]["im_user_id"], "im-user-1")

        render = self.post(
            {"command": "", "channel": "im", "force": True}, self.im_headers()
        ).json()
        self.assertTrue(render["text"])
        self.assertIn(uuid, render["account"]["uuid"])

    def test_im_non_game_message_unhandled(self):
        body = self.post(
            {"command": "今天天气不错", "channel": "im", "force": False},
            self.im_headers(),
        ).json()
        self.assertTrue(body["ok"])
        self.assertFalse(body["handled"])
        self.assertEqual(body["text"], "")

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
        self.assertIn(start["account"]["uuid"], uuid_body["text"])

    def test_web_bind_requires_force(self):
        im = self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("im-bind-target"),
        ).json()
        target_uuid = im["account"]["uuid"]

        self.post({"command": "start confirm", "channel": "web"}, self.web_headers("web-bind"))
        refused = self.post(
            {"command": f"绑定 {target_uuid}", "channel": "web"},
            self.web_headers("web-bind"),
        ).json()
        self.assertIn("force", refused["text"])
        self.assertNotEqual(refused["account"]["uuid"], target_uuid)

        accepted = self.post(
            {"command": f"绑定 {target_uuid} force", "channel": "web"},
            self.web_headers("web-bind"),
        ).json()
        self.assertEqual(accepted["account"]["uuid"], target_uuid)
        self.assertEqual(accepted["account"]["im_user_id"], "im-bind-target")
        self.assertEqual(accepted["account"]["web_user_id"], "web-bind")

        render = self.post(
            {"command": "", "channel": "web"}, self.web_headers("web-bind")
        ).json()
        self.assertIsNotNone(render["state"])
        self.assertIsNotNone(render["state"]["player"])

    def test_admin_requires_token(self):
        denied = self.post(
            {"command": "admin accounts", "channel": "web"}, self.web_headers()
        ).json()
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"], "admin_required")

        allowed = self.post(
            {"command": "admin accounts", "channel": "web"},
            {**self.web_headers(), "X-Rogue-Admin-Token": "admin-secret"},
        ).json()
        self.assertTrue(allowed["ok"])
        self.assertIn("UUID", allowed["text"])

    def test_web_bind_fresh_account_without_force(self):
        im = self.post(
            {"command": "start confirm", "channel": "im", "force": True},
            self.im_headers("im-fresh-target"),
        ).json()
        target_uuid = im["account"]["uuid"]

        self.post({"command": "uuid", "channel": "web"}, self.web_headers("web-fresh"))
        bound = self.post(
            {"command": f"绑定 {target_uuid}", "channel": "web"},
            self.web_headers("web-fresh"),
        ).json()
        self.assertEqual(bound["account"]["uuid"], target_uuid)
        self.assertEqual(bound["account"]["web_user_id"], "web-fresh")

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
        body = self.post(
            {"command": "我的ID", "channel": "im"}, self.im_headers("im-uuid-user")
        ).json()
        self.assertTrue(body["ok"])
        self.assertIn("UUID", body["text"])
        self.assertIsNotNone(body["account"]["uuid"])

    def test_im_secrets_returns_migration_uuid(self):
        body = self.post(
            {"command": "secrets", "channel": "im"}, self.im_headers("im-secrets-user")
        ).json()
        self.assertTrue(body["ok"])
        self.assertIn(body["account"]["uuid"], body["text"])
        self.assertIn("绑定", body["text"])
        self.assertEqual(body["account"]["im_user_id"], "im-secrets-user")

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


if __name__ == "__main__":
    unittest.main()
