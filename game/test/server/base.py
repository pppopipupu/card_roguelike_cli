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
import tempfile
from tempfile import TemporaryDirectory
import jwt
from fastapi.testclient import TestClient
from game.data.progression.account_config import GITHUB_BIND_REWARD_GP, RENAME_COST_GP
from game.json_codec import dumps, loads
from game.models.sqlite_store import close_stores_under
from server.accounts import AccountStore
from server.app import create_app
from server.config import Settings

if not getattr(tempfile.TemporaryDirectory.cleanup, "_rogue_sqlite_patched", False):
    _orig_tempdir_cleanup = tempfile.TemporaryDirectory.cleanup

    def _rogue_tempdir_cleanup(self):
        close_stores_under(getattr(self, "name", ""))
        return _orig_tempdir_cleanup(self)

    setattr(_rogue_tempdir_cleanup, "_rogue_sqlite_patched", True)
    tempfile.TemporaryDirectory.cleanup = _rogue_tempdir_cleanup


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


class ServerTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.settings = make_settings(Path(self.tmp.name))
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.state.service.close()
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

    def _grant_admin(self, identity: str, value: bool = True) -> None:
        self.app.state.service.accounts.set_admin_by_identity(identity, value)
