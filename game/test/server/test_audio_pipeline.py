import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import jwt
from fastapi.testclient import TestClient

from game.core.audio import AudioPipeline, reset_audio_pipeline
from game.data.audio_config import CARD_PLAY_AUDIO_MAP
from game.data.ninja_card_data import NINJA_CARD_CONFIG
from game.models.state import CardState
from server.app import create_app
from server.config import Settings


def _make_settings(root: Path) -> Settings:
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


class TestAudioPipeline(unittest.TestCase):
    def setUp(self):
        reset_audio_pipeline()
        self.tmp = TemporaryDirectory()
        self.settings = _make_settings(Path(self.tmp.name))
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)

    def tearDown(self):
        reset_audio_pipeline()
        self.app.state.service.accounts.close()
        self.tmp.cleanup()

    def _web_headers(self, subject: str = "web-ninja-1") -> dict[str, str]:
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

    def _im_headers(self, user: str = "im-ninja-1") -> dict[str, str]:
        return {"X-Rogue-IM-Token": "im-secret", "X-Rogue-IM-User": user}

    def _prepare_ninja_battle(self, headers: dict[str, str], channel: str, is_im: bool = False) -> str:
        prefix = ".rogue " if is_im else ""

        def send(cmd: str) -> dict:
            r = self.client.post(
                "/api/v1/action",
                headers=headers,
                json={"command": f"{prefix}{cmd}", "channel": channel, "force": True},
            )
            self.assertEqual(r.status_code, 200)
            return r.json()

        if is_im:
            send("start")
            send("skip_tutorial")
        else:
            send("skip_tutorial")
        send("class ninja")
        send("start confirm")
        send("c 1")
        service = self.app.state.service
        acct = service.accounts.get_by_im("im-ninja-1") if is_im else service.accounts.get_by_web("web-ninja-1")
        assert acct is not None
        uid = acct["uuid"]
        run = service.save_manager.load_save(uid)
        assert run is not None
        fm = run.floor_map
        assert fm is not None
        b_coord = next((c for c, rm in fm.rooms.items() if rm.room_type == "battle"), None)
        if b_coord is None:
            for c, rm in fm.rooms.items():
                if rm.room_type == "empty":
                    rm.room_type = "battle"
                    b_coord = c
                    break
        assert b_coord is not None
        fm.rooms[b_coord].explored = True
        if b_coord not in fm.revealed_coords:
            fm.revealed_coords.append(b_coord)
        service.save_manager.save_save(uid, run)
        send(f"tp {b_coord}")
        run = service.save_manager.load_save(uid)
        assert run is not None and run.node_type == "battle"
        run.player.hand = [CardState(id="ninja_strike"), CardState(id="ninja_yi_cut")]
        run.player.actions = 2
        run.player.lex_kela = 2
        for enemy in run.enemies:
            enemy.hp = 100
            enemy.max_hp = 100
        service.save_manager.save_save(uid, run)
        return uid

    def test_all_ninja_cards_mapped_and_assets_resolvable(self):
        pipeline = AudioPipeline()
        for cid in NINJA_CARD_CONFIG:
            self.assertIn(cid, CARD_PLAY_AUDIO_MAP)
            cfg = CARD_PLAY_AUDIO_MAP[cid]
            resolved = pipeline.resolve_asset_path(str(cfg["pack"]), str(cfg["file"]))
            self.assertIsNotNone(resolved, f"Missing asset for {cid}")
        self.assertIsNone(pipeline.resolve_asset_path("..", "etc/passwd"))
        self.assertIsNone(pipeline.resolve_asset_path("ninja", "../audio_config.py"))
        self.assertIsNone(pipeline.resolve_asset_path("ninja", "nonexistent.mp3"))

    def test_web_channel_receives_audio_packets_and_serves_audio_file(self):
        headers = self._web_headers()
        self._prepare_ninja_battle(headers, "web", is_im=False)

        r = self.client.post(
            "/api/v1/action",
            headers=headers,
            json={"command": "p 1 e1", "channel": "web", "force": True},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("audio", body)
        self.assertGreaterEqual(len(body["audio"]), 1)
        pkt = body["audio"][0]
        self.assertEqual(pkt["pack"], "ninja")
        self.assertEqual(pkt["card_id"], "ninja_strike")
        self.assertTrue(str(pkt["url"]).startswith("/api/v1/audio/ninja/"))

        asset_resp = self.client.get(str(pkt["url"]))
        self.assertEqual(asset_resp.status_code, 200)
        self.assertTrue(asset_resp.headers.get("content-type", "").startswith("audio/"))
        self.assertGreater(len(asset_resp.content), 100)

        bad_resp = self.client.get("/api/v1/audio/ninja/does_not_exist.mp3")
        self.assertEqual(bad_resp.status_code, 404)

    def test_im_channel_never_receives_audio_packets(self):
        headers = self._im_headers()
        uid = self._prepare_ninja_battle(headers, "im", is_im=True)

        r = self.client.post(
            "/api/v1/action",
            headers=headers,
            json={"command": ".rogue p 1 e1", "channel": "im", "force": True},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertNotIn("audio", body)
        self.assertEqual(self.app.state.service.audio_pipeline.drain(uid, "web"), [])


if __name__ == "__main__":
    unittest.main()
