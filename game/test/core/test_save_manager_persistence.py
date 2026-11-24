import asyncio
import random
import tempfile
import unittest

from game.core.world.presence import WorldPresenceService
from game.models.manager import SaveManager
from game.models.state import CardState, GameRun, PlayerState, UserStats
from game.test.core.base import CorePlugin, floor_of, load_run, run_command


class TestSaveManagerPersistence(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20261126)
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def test_stats_and_saves_roundtrip_across_restart(self):
        sm1 = SaveManager(self.tmp.name)
        st = UserStats(
            total_damage=12345678901234567890,
            total_kills=42,
            gp=777,
            player_name="测试者",
            player_handle="测试者",
            town_flags={"custom_flag": {"nested": [1, 2, 3]}},
            unlocked_achievements=["ancient_cycle_breaker"],
            open_world_deck=[
                CardState(
                    id="science_device",
                    upgraded=True,
                    gems=["ruby"],
                    enchantments=["echo"],
                    custom_spec="arc|poison|overload",
                )
            ],
        )
        self.assertTrue(sm1.save_stats("u_rt", st))

        p = PlayerState(
            hp=44,
            max_hp=60,
            shield=5,
            gold=123,
            stage=2,
            deck=[CardState(id="science_device", custom_spec="prism|armor|std")],
            hand=[CardState(id="fire_bolt", upgraded=True)],
        )
        run = GameRun(user_id="u_rt", node_type="grid_map", player=p, enemies=[], node_data={"k": "v"})
        self.assertTrue(sm1.save_save("u_rt", run))
        self.assertTrue(sm1.has_personal_save("u_rt"))
        self.assertTrue(sm1.save_lobbies({"L1": {"lobby_id": "L1", "leader_id": "u_rt", "members": ["u_rt"], "invited": [], "ready": {}, "created_at": "2026-11-24T00:00:00Z"}}))
        self.assertTrue(sm1.save_admin_config({"final_boss": "yog_sothoth"}))
        sm1.close()

        sm2 = SaveManager(self.tmp.name)
        st2 = sm2.load_stats("u_rt")
        self.assertEqual(st2.total_damage, 12345678901234567890)
        self.assertEqual(st2.gp, 777)
        self.assertEqual(st2.town_flags.get("custom_flag"), {"nested": [1, 2, 3]})
        self.assertIn("ancient_cycle_breaker", st2.unlocked_achievements)
        self.assertEqual(len(st2.open_world_deck), 1)
        self.assertEqual(st2.open_world_deck[0].custom_spec, "arc|poison|overload")
        self.assertEqual(st2.open_world_deck[0].enchantments, ["echo"])

        run2 = sm2.load_save("u_rt")
        self.assertIsNotNone(run2)
        assert run2 is not None
        self.assertEqual(run2.player.hp, 44)
        self.assertEqual(run2.player.deck[0].custom_spec, "prism|armor|std")
        self.assertEqual(sm2.load_lobbies().get("L1", {}).get("leader_id"), "u_rt")
        self.assertEqual(sm2.load_admin_config().get("final_boss"), "yog_sothoth")

        self.assertTrue(sm2.delete_save("u_rt"))
        self.assertFalse(sm2.has_personal_save("u_rt"))
        self.assertIsNone(sm2.load_save("u_rt"))

    def test_dirty_read_isolation_without_save(self):
        sm = SaveManager(self.tmp.name)
        st = UserStats(gp=500, player_name="原名")
        sm.save_stats("u_iso", st)
        loaded_st = sm.load_stats("u_iso")
        loaded_st.gp = 99999
        loaded_st.player_name = "被污染"
        reloaded_st = sm.load_stats("u_iso")
        self.assertEqual(reloaded_st.gp, 500)
        self.assertEqual(reloaded_st.player_name, "原名")

        run = GameRun(user_id="u_iso", node_type="grid_map", player=PlayerState(hp=30, max_hp=50, shield=0, gold=0, stage=1), enemies=[], node_data={})
        sm.save_save("u_iso", run)
        loaded_run = sm.load_save("u_iso")
        assert loaded_run is not None
        loaded_run.player.hp = 1
        reloaded_run = sm.load_save("u_iso")
        assert reloaded_run is not None
        self.assertEqual(reloaded_run.player.hp, 30)

    def test_coop_view_isolation_and_delete_guard(self):
        plugin = CorePlugin(data_dir=self.tmp.name)
        uids = ["iso_a", "iso_b"]
        plugin.engine.start_party_game(uids, uids[0], shared_save=True)
        asyncio.run(run_command(plugin, "c 1", uids[0]))
        asyncio.run(run_command(plugin, "c 1", uids[1]))

        sm = plugin.save_manager
        run_a = sm.load_save(uids[0])
        run_b = sm.load_save(uids[1])
        assert run_a is not None and run_b is not None
        self.assertEqual(run_a.user_id, uids[0])
        self.assertEqual(run_b.user_id, uids[1])
        self.assertIsNot(run_a.player, run_b.player)
        self.assertTrue(sm.resolve_lock_key(uids[0]).startswith("coop:"))
        self.assertFalse(sm.delete_save(uids[0]))

        coop_id = run_a.coop_id
        self.assertTrue(sm.delete_coop_save(coop_id))
        for u in uids:
            st = sm.load_stats(u)
            st.active_coop_id = ""
            sm.save_stats(u, st)
        self.assertIsNone(sm.load_save(uids[0]))

    def test_registries_presence_profiles_and_cli_restart(self):
        plugin1 = CorePlugin(data_dir=self.tmp.name)
        sm1 = plugin1.save_manager
        sm1.save_stats("p1", UserStats(player_name="甲", player_handle="甲", gp=100))
        sm1.save_stats("p2", UserStats(player_name="乙", player_handle="乙", gp=200))
        profiles = sm1.list_player_profiles()
        self.assertEqual({pr.user_id for pr in profiles}, {"p1", "p2"})

        pres1 = WorldPresenceService(sm1)
        pres1.touch("p1", "town", "C2")
        self.assertTrue(pres1.send_live("p1", "p2", "乙", "你好"))

        asyncio.run(run_command(plugin1, "start confirm", "cli_u"))
        asyncio.run(run_command(plugin1, "c 1", "cli_u"))
        before_coord = floor_of(load_run(plugin1, "cli_u")).player_coords["cli_u"]
        plugin1.close()

        plugin2 = CorePlugin(data_dir=self.tmp.name)
        pres2 = WorldPresenceService(plugin2.save_manager)
        msgs = pres2.pop_live("p1")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["text"], "你好")

        after_run = load_run(plugin2, "cli_u")
        self.assertEqual(floor_of(after_run).player_coords["cli_u"], before_coord)
        status_out = asyncio.run(run_command(plugin2, "r", "cli_u"))
        self.assertIn("第 1 层", status_out)

    def test_lazy_legacy_json_migration_and_delete(self):
        import os
        from game.json_codec import dumps
        legacy_dir = tempfile.TemporaryDirectory()
        try:
            stats_file = os.path.join(legacy_dir.name, "stats_leg1.json")
            with open(stats_file, "wb") as f:
                f.write(dumps({"gp": 456, "player_name": "旧档案", "total_damage": "99999999999999999999"}))
            save_file = os.path.join(legacy_dir.name, "user_leg1.json")
            with open(save_file, "wb") as f:
                f.write(dumps({
                    "user_id": "leg1",
                    "node_type": "grid_map",
                    "player": {"hp": 33, "max_hp": 50, "shield": 0, "gold": 12, "stage": 1},
                    "enemies": [],
                    "node_data": {},
                    "map_data": {},
                }))
            sm = SaveManager(legacy_dir.name)
            st = sm.load_stats("leg1")
            self.assertEqual(st.gp, 456)
            self.assertEqual(st.total_damage, 99999999999999999999)
            self.assertIsNotNone(sm.store.get_row("user_stats", "leg1"))
            self.assertTrue(sm.has_personal_save("leg1"))
            run = sm.load_save("leg1")
            self.assertIsNotNone(run)
            assert run is not None
            self.assertEqual(run.player.hp, 33)
            self.assertTrue(sm.delete_save("leg1"))
            self.assertFalse(os.path.exists(save_file))
            self.assertIsNone(sm.load_save("leg1"))
            self.assertTrue(sm.delete_stats("leg1"))
            self.assertFalse(os.path.exists(stats_file))
            self.assertEqual(sm.load_stats("leg1").gp, 0)
            sm.close()
        finally:
            legacy_dir.cleanup()

    def test_batch_transaction_rollback_restores_db_and_cache(self):
        sm = SaveManager(self.tmp.name)
        sm.save_stats("u_tx", UserStats(gp=100, player_name="初始"))
        seen_in_batch = None
        with self.assertRaises(RuntimeError):
            with sm.batch():
                st = sm.load_stats("u_tx")
                st.gp = 9999
                sm.save_stats("u_tx", st)
                seen_in_batch = SaveManager().load_stats("u_tx").gp
                sm.save_stats("u_tx_new", UserStats(gp=555))
                raise RuntimeError("abort")
        self.assertEqual(seen_in_batch, 9999)
        self.assertEqual(sm.load_stats("u_tx").gp, 100)
        self.assertEqual(sm.load_stats("u_tx_new").gp, 0)
        sm.close()
        sm2 = SaveManager(self.tmp.name)
        self.assertEqual(sm2.load_stats("u_tx").gp, 100)
        self.assertEqual(sm2.load_stats("u_tx_new").gp, 0)
        sm2.close()
