import asyncio
import os
import random
import unittest
from game.core.deck_service import DeckService
from game.core.reward_builder import build_reward_items
from game.test.core.base import DummyContext, MyPlugin, SaveManager, run_command


class TestRogueGemsAndUnlocks(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_user_gems_unlocks"
        self.save_manager = SaveManager()
        self.save_manager.delete_save(self.user_id)
        stats_path = self.save_manager.get_stats_path(self.user_id)
        if os.path.exists(stats_path):
            os.remove(stats_path)

    def tearDown(self):
        self.save_manager.delete_save(self.user_id)
        stats_path = self.save_manager.get_stats_path(self.user_id)
        if os.path.exists(stats_path):
            os.remove(stats_path)

    def test_gem_burn_gold_and_sturdy_exhaust_in_dummy_battle(self):
        plugin = MyPlugin(DummyContext())
        stats = self.save_manager.load_stats(self.user_id)
        stats.gp = 100
        stats.locked_cards = ["fire_bolt:gems:gem_burn_gold,gem_sturdy"]
        self.save_manager.save_stats(self.user_id, stats)
        async def run_battle():
            await run_command(plugin, ".rogue 主城", self.user_id)
            await run_command(plugin, ".rogue home", self.user_id)
            await run_command(plugin, ".rogue up", self.user_id)
            await run_command(plugin, ".rogue talk Dummy", self.user_id)
            await run_command(plugin, ".rogue 2", self.user_id)

            for turn in range(6):
                run = self.save_manager.load_save(self.user_id)
                target_idx = None
                for idx, cs in enumerate(run.player.hand, 1):
                    if cs.id == "fire_bolt" and "gem_burn_gold" in (cs.gems or []):
                        target_idx = idx
                        break
                if target_idx is not None:
                    status_res = await run_command(plugin, ".rogue r", self.user_id)
                    self.assertIn("消耗 2。", status_res)
                    self.assertIn("打出时获得 5GP。", status_res)
                    res = await run_command(plugin, f".rogue p {target_idx} e1", self.user_id)
                    self.assertIn("燃金宝石", res)
                    break
                await run_command(plugin, ".rogue e", self.user_id)

            stats_after_1 = self.save_manager.load_stats(self.user_id)
            self.assertEqual(stats_after_1.gp, 105)
            run_after_1 = self.save_manager.load_save(self.user_id)
            self.assertEqual(len(run_after_1.player.exhaust_pile), 0)
            discarded = [c for c in run_after_1.player.discard_pile if c.id == "fire_bolt" and "gem_burn_gold" in (c.gems or [])]
            self.assertEqual(len(discarded), 1)
            self.assertEqual(discarded[0].exhaust_used, 1)

            for turn in range(8):
                run = self.save_manager.load_save(self.user_id)
                target_idx = None
                for idx, cs in enumerate(run.player.hand, 1):
                    if cs.id == "fire_bolt" and "gem_burn_gold" in (cs.gems or []):
                        target_idx = idx
                        break
                if target_idx is not None:
                    status_res2 = await run_command(plugin, ".rogue r", self.user_id)
                    self.assertNotIn("消耗 2", status_res2)
                    self.assertIn("消耗。", status_res2)
                    res = await run_command(plugin, f".rogue p {target_idx} e1", self.user_id)
                    self.assertIn("燃金宝石", res)
                    break
                await run_command(plugin, ".rogue e", self.user_id)

            stats_after_2 = self.save_manager.load_stats(self.user_id)
            self.assertEqual(stats_after_2.gp, 110)
            run_after_2 = self.save_manager.load_save(self.user_id)
            exhausted = [c for c in run_after_2.player.exhaust_pile if c.id == "fire_bolt" and "gem_burn_gold" in (c.gems or [])]
            self.assertEqual(len(exhausted), 1)
            self.assertEqual(exhausted[0].exhaust_used, 2)

        asyncio.run(run_battle())

    def test_gem_sturdy_fleeting_in_dummy_battle(self):
        plugin = MyPlugin(DummyContext())
        stats = self.save_manager.load_stats(self.user_id)
        stats.locked_cards = ["fleeting_spark:gems:gem_sturdy"]
        self.save_manager.save_stats(self.user_id, stats)

        async def run_battle():
            await run_command(plugin, ".rogue 主城", self.user_id)
            await run_command(plugin, ".rogue home", self.user_id)
            await run_command(plugin, ".rogue up", self.user_id)
            await run_command(plugin, ".rogue talk Dummy", self.user_id)
            await run_command(plugin, ".rogue 2", self.user_id)
            deck_before = await run_command(plugin, ".rogue deck", self.user_id)
            self.assertIn("即逝 2。", deck_before)
            for _ in range(8):
                run = self.save_manager.load_save(self.user_id)
                target_idx = None
                for idx, cs in enumerate(run.player.hand, 1):
                    if cs.id == "fleeting_spark" and "gem_sturdy" in (cs.gems or []):
                        target_idx = idx
                        break
                if target_idx is not None:
                    res = await run_command(plugin, f".rogue p {target_idx} e1", self.user_id)
                    run_check = self.save_manager.load_save(self.user_id)
                    if run_check.node_data.get("pending_discard"):
                        await run_command(plugin, ".rogue 选择 1", self.user_id)
                    self.assertIn("剩余 1 次", res)
                    break
                await run_command(plugin, ".rogue e", self.user_id)

            deck_mid = await run_command(plugin, ".rogue deck", self.user_id)
            self.assertIn("即逝。", deck_mid)
            self.assertNotIn("即逝 2", deck_mid)
            for _ in range(10):
                run = self.save_manager.load_save(self.user_id)
                target_idx = None
                for idx, cs in enumerate(run.player.hand, 1):
                    if cs.id == "fleeting_spark" and "gem_sturdy" in (cs.gems or []):
                        target_idx = idx
                        break
                if target_idx is not None:
                    res = await run_command(plugin, f".rogue p {target_idx} e1", self.user_id)
                    run_check = self.save_manager.load_save(self.user_id)
                    if run_check.node_data.get("pending_discard"):
                        await run_command(plugin, ".rogue 选择 1", self.user_id)
                    self.assertIn("永久移除", res)
                    break
                await run_command(plugin, ".rogue e", self.user_id)

            run_end = self.save_manager.load_save(self.user_id)
            self.assertEqual([c for c in run_end.player.deck if c.id == "fleeting_spark"], [])

        asyncio.run(run_battle())

    def test_elf_archer_xiaomei_and_market_cards_in_battle_rewards_after_unlock(self):
        plugin = MyPlugin(DummyContext())

        async def run_checkin_unlock():
            await run_command(plugin, ".rogue start", self.user_id)
            await run_command(plugin, ".rogue 1", self.user_id)
            run = self.save_manager.load_save(self.user_id)
            stats_locked = self.save_manager.load_stats(self.user_id)
            pool_locked = DeckService.get_reward_card_pool(run, run.player, stats_locked)
            self.assertNotIn("elf_archer_xiaomei", pool_locked)

            await run_command(plugin, ".rogue checkin", self.user_id)
            res1 = await run_command(plugin, ".rogue checkin 1", self.user_id)
            self.assertIn("精灵射手小梅", res1)
            stats1 = self.save_manager.load_stats(self.user_id)
            stats1.last_checkin_date = "2000-01-01"
            self.save_manager.save_stats(self.user_id, stats1)

            await run_command(plugin, ".rogue checkin", self.user_id)
            res2 = await run_command(plugin, ".rogue checkin 1", self.user_id)
            self.assertIn("解锁", res2)
            stats2 = self.save_manager.load_stats(self.user_id)
            self.assertIn("elf_archer_xiaomei", stats2.unlocked_new_cards)

            pool_unlocked = DeckService.get_reward_card_pool(run, run.player, stats2)
            self.assertIn("elf_archer_xiaomei", pool_unlocked)

            found_in_rewards = False
            rng = random.Random(0)
            orig_sample = random.sample
            try:
                for seed in range(200):
                    random.seed(seed)
                    items = build_reward_items(self.save_manager, run, run.player, "normal")
                    for it in items:
                        if it.get("type") == "card_reward" and "elf_archer_xiaomei" in it.get("cards", []):
                            found_in_rewards = True
                            break
                    if found_in_rewards:
                        break
            finally:
                random.sample = orig_sample
            self.assertTrue(found_in_rewards)

        asyncio.run(run_checkin_unlock())

        self.save_manager.delete_save(self.user_id)
        stats_path = self.save_manager.get_stats_path(self.user_id)
        if os.path.exists(stats_path):
            os.remove(stats_path)

        async def run_gold_unlock():
            stats = self.save_manager.load_stats(self.user_id)
            stats.gp = 5000
            self.save_manager.save_stats(self.user_id, stats)
            await run_command(plugin, ".rogue 主城", self.user_id)
            await run_command(plugin, ".rogue home", self.user_id)
            await run_command(plugin, ".rogue down", self.user_id)
            await run_command(plugin, ".rogue talk Market_Merchant", self.user_id)
            menu_res = await run_command(plugin, ".rogue 2", self.user_id)
            self.assertIn("精灵射手小梅", menu_res)

            xiaomei_opt = None
            for line in menu_res.splitlines():
                if "精灵射手小梅" in line and "." in line:
                    xiaomei_opt = line.split(".", 1)[0].strip()
                    break
            self.assertIsNotNone(xiaomei_opt)
            buy_res = await run_command(plugin, f".rogue {xiaomei_opt}", self.user_id)
            self.assertIn("购买", buy_res)

            await run_command(plugin, ".rogue exit", self.user_id)
            await run_command(plugin, ".rogue start", self.user_id)
            await run_command(plugin, ".rogue 1", self.user_id)
            run = self.save_manager.load_save(self.user_id)
            stats_after = self.save_manager.load_stats(self.user_id)
            self.assertIn("elf_archer_xiaomei", stats_after.unlocked_new_cards)
            pool = DeckService.get_reward_card_pool(run, run.player, stats_after)
            self.assertIn("elf_archer_xiaomei", pool)

        asyncio.run(run_gold_unlock())
