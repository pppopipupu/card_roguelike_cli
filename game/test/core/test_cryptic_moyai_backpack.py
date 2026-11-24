import tempfile
import unittest

from game.data.entities.relic_data import BACKPACK_RELIC_IDS, RELIC_CONFIG
from game.models.state import CardState, EnemyState, GameRun, PlayerState
from game.test.core.base import CorePlugin, load_run, run_command


class TestCrypticMoyaiBackpack(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmpdir.name)
        self.sm = self.plugin.save_manager
        self.uid = "test_cryptic_user"

    def tearDown(self):
        self.tmpdir.cleanup()

    async def test_moyai_discard_triggers_cryptic_demon_form_and_minion(self):
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=100,
            actions=3,
            bonus_actions=0,
            deck=[
                CardState(id="moyai_trio"),
                CardState(id="demon_form"),
                CardState(id="moyai_trio", upgraded=True),
                CardState(id="mercenary"),
            ],
            hand=[
                CardState(id="moyai_trio"),
                CardState(id="demon_form"),
                CardState(id="moyai_trio", upgraded=True),
                CardState(id="mercenary"),
            ],
        )
        enemy = EnemyState(name="木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")
        run = GameRun(user_id=self.uid, player=player, enemies=[enemy], node_type="battle")
        self.sm.save_save(self.uid, run)

        res1 = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertIn("🗿", res1)
        run_mid = load_run(self.plugin, self.uid)
        self.assertEqual(len(run_mid.node_data.get("state_stack", [])), 1)

        res2 = await run_command(self.plugin, "c 1", sender_id=self.uid)
        self.assertIn("诡秘", res2)
        run_after_df = load_run(self.plugin, self.uid)
        self.assertEqual(run_after_df.player.shield, 10)
        self.assertTrue(any(b.id == "demon_form" for b in run_after_df.player.buffs))
        self.assertEqual(run_after_df.player.actions, 2)
        self.assertEqual(run_after_df.player.bonus_actions, 0)

        res3 = await run_command(self.plugin, "p 1 h1", sender_id=self.uid)
        self.assertIn("诡秘", res3)
        run_final = load_run(self.plugin, self.uid)
        self.assertEqual(run_final.player.shield, 24)
        self.assertTrue(any(m.id == "mercenary" for m in run_final.player.minions.values()))

    async def test_backpack_relics_always_in_shop_and_expand_weight(self):
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=1000,
            deck=[CardState(id="strike")],
        )
        run = GameRun(user_id=self.uid, player=player, node_type="explore")
        self.plugin.engine.map_engine._init_shop_node(run)
        self.sm.save_save(self.uid, run)

        items = run.node_data.get("items", [])
        shop_relics = {
            item["relic_id"]: item["price"]
            for item in items
            if item.get("type") == "relic"
        }
        expected_prices = {
            "backpack_small": 50,
            "backpack_medium": 100,
            "backpack_large": 200,
            "backpack_giant": 500,
        }
        for rid, price in expected_prices.items():
            self.assertIn(rid, shop_relics)
            self.assertEqual(shop_relics[rid], price)

        initial_max_weight = run.player.bag_max_weight
        total_bonus = 0
        for rid in BACKPACK_RELIC_IDS:
            current_run = load_run(self.plugin, self.uid)
            cur_items = current_run.node_data.get("items", [])
            idx = next(i + 1 for i, it in enumerate(cur_items) if it.get("relic_id") == rid)
            res = await run_command(self.plugin, f"c {idx}", sender_id=self.uid)
            self.assertIn(RELIC_CONFIG[rid]["name"], res)
            total_bonus += RELIC_CONFIG[rid]["bag_weight_bonus"]

        final_run = load_run(self.plugin, self.uid)
        self.assertEqual(final_run.player.bag_max_weight, initial_max_weight + total_bonus)
        self.assertEqual(final_run.player.gold, 1000 - (50 + 100 + 200 + 500))

        self.plugin.engine.map_engine._init_shop_node(final_run)
        next_relic_ids = {
            item["relic_id"]
            for item in final_run.node_data.get("items", [])
            if item.get("type") == "relic"
        }
        for rid in BACKPACK_RELIC_IDS:
            self.assertNotIn(rid, next_relic_ids)
