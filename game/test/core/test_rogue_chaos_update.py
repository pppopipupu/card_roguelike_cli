import unittest
import random
from game.test.core.base import *
from game.models.state import PlayerState, GameRun, EnemyState, CardState, UserStats
from game.entities.cards.base import ALL_CARDS
from game.core.battle.engine import BattleEngine

class TestRogueChaosUpdate(unittest.TestCase):
    def test_source_of_cinder(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_cinder_cmd"
        plugin.save_manager.delete_save(user_id)
        stats = plugin.save_manager.load_stats(user_id)
        stats.locked_cards = ["warrior_source_of_cinder"]
        plugin.save_manager.save_stats(user_id, stats)

        async def go():
            await run_command(plugin, ".rogue 主城", user_id)
            await run_command(plugin, ".rogue home", user_id)
            await run_command(plugin, ".rogue up", user_id)
            await run_command(plugin, ".rogue talk Dummy", user_id)
            await run_command(plugin, ".rogue 2", user_id)
            run = load_run(plugin, user_id)
            run.player.actions = 5
            run.player.bonus_actions = 2
            plugin.save_manager.save_save(user_id, run)
            for _ in range(6):
                run = load_run(plugin, user_id)
                idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "warrior_source_of_cinder"), None)
                if idx is not None:
                    await run_command(plugin, f".rogue p {idx}", user_id)
                    await run_command(plugin, ".rogue e", user_id)
                    after = load_run(plugin, user_id)
                    self.assertEqual(after.player.actions, 3)
                    self.assertEqual(after.player.bonus_actions, 2)
                    break
                await run_command(plugin, ".rogue e", user_id)

        import asyncio
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)

    def test_gem_effects_independent(self):
        class DummySaveManager(DummySaveManagerBase):
            def save_save(self, user_id, run) -> bool:
                return True
            def load_stats(self, user_id) -> UserStats:
                return UserStats()
            def save_stats(self, user_id, stats) -> bool:
                return True
            def settle_game_and_delete(self, user_id: str, run, is_victory: bool = False, create_corpse: bool = True, force: bool = False) -> str:
                return ""
        from game.engine import GameEngine
        sm = DummySaveManager()
        ge = GameEngine(sm)
        player = PlayerState(
            hp=40, max_hp=40, shield=0, gold=100, stage=1,
            deck=[CardState(id="tactical_focus", gems=["gem_shield_add_8"]), CardState(id="fire_bolt", gems=["gem_shield_add_8"])],
            hand=[CardState(id="tactical_focus", gems=["gem_shield_add_8"]), CardState(id="fire_bolt", gems=["gem_shield_add_8"])],
            actions=3, bonus_actions=3, buffs=[]
        )
        run = GameRun(user_id="test_gems", node_type="battle", player=player, enemies=[EnemyState("e1", 20, 20, 0)])
        ge.play_card(run, 1, "p0")
        self.assertEqual(player.shield, 8)
        ge.play_card(run, 1, "e1")
        self.assertEqual(player.shield, 16)

    def test_emperor_eye_suspend_post_play(self):
        class DummySaveManager(DummySaveManagerBase):
            def save_save(self, user_id, run) -> bool:
                return True
            def load_stats(self, user_id) -> UserStats:
                return UserStats()
            def save_stats(self, user_id, stats) -> bool:
                return True
        from game.engine import GameEngine
        sm = DummySaveManager()
        ge = GameEngine(sm)
        player = PlayerState(
            hp=40, max_hp=40, shield=0, gold=100, stage=1,
            deck=[CardState(id="neutral_emperor_eye", gems=["gem_copy_1"]), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
            hand=[CardState(id="neutral_emperor_eye", gems=["gem_copy_1"]), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
            actions=3, bonus_actions=2, buffs=[]
        )
        run = GameRun(user_id="test_eye_suspend", node_type="battle", player=player, enemies=[EnemyState("e1", 10, 10, 0)])
        ge.play_card(run, 1, None)
        self.assertEqual(run.node_data["state_stack"][-1]["type"], "card_selection")
        self.assertEqual(len(player.exhaust_pile), 0)
        has_copy = any(getattr(cid, "id", cid) == "neutral_emperor_eye" for cid in player.hand)
        self.assertFalse(has_copy)
        ge.execute_emperor_eye_resolve(run, 0, False)
        self.assertEqual(len(player.exhaust_pile), 2)
        has_copy_after = any(getattr(cid, "id", cid) == "neutral_emperor_eye" for cid in player.hand)
        self.assertTrue(has_copy_after)

    def test_discover_suspend_and_resolve(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_discover_resolve_cmd"
        plugin.save_manager.delete_save(user_id)
        stats = plugin.save_manager.load_stats(user_id)
        stats.locked_cards = ["discover:gems:gem_copy_1", "first_aid", "mana_potion"]
        plugin.save_manager.save_stats(user_id, stats)

        async def go():
            await run_command(plugin, ".rogue 主城", user_id)
            await run_command(plugin, ".rogue home", user_id)
            await run_command(plugin, ".rogue up", user_id)
            await run_command(plugin, ".rogue talk Dummy", user_id)
            await run_command(plugin, ".rogue 2", user_id)
            for _ in range(8):
                run = load_run(plugin, user_id)
                for cid in ("first_aid", "mana_potion"):
                    c_idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == cid), None)
                    if c_idx is not None:
                        await run_command(plugin, f".rogue p {c_idx}", user_id)
                        run = load_run(plugin, user_id)
                disc_idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "discover"), None)
                if disc_idx is not None and len(run.player.exhaust_pile) >= 2:
                    res = await run_command(plugin, f".rogue p {disc_idx}", user_id)
                    self.assertIn("请选择一张卡牌发掘", res)
                    run_mid = load_run(plugin, user_id)
                    self.assertFalse(any(c.id == "discover" for c in run_mid.player.hand))
                    res_sel = await run_command(plugin, ".rogue 选择 1", user_id)
                    self.assertIn("发掘", res_sel)
                    run_end = load_run(plugin, user_id)
                    self.assertTrue(any(c.id == "discover" and c.no_copy for c in run_end.player.hand))
                    break
                await run_command(plugin, ".rogue e", user_id)

        import asyncio
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)

    def test_discover_suspend_and_cancel(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_discover_cancel_cmd"
        plugin.save_manager.delete_save(user_id)
        stats = plugin.save_manager.load_stats(user_id)
        stats.locked_cards = ["discover:gems:gem_copy_1", "first_aid", "mana_potion"]
        plugin.save_manager.save_stats(user_id, stats)

        async def go():
            await run_command(plugin, ".rogue 主城", user_id)
            await run_command(plugin, ".rogue home", user_id)
            await run_command(plugin, ".rogue up", user_id)
            await run_command(plugin, ".rogue talk Dummy", user_id)
            await run_command(plugin, ".rogue 2", user_id)
            for _ in range(8):
                run = load_run(plugin, user_id)
                for cid in ("first_aid", "mana_potion"):
                    c_idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == cid), None)
                    if c_idx is not None:
                        await run_command(plugin, f".rogue p {c_idx}", user_id)
                        run = load_run(plugin, user_id)
                disc_idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "discover"), None)
                if disc_idx is not None and len(run.player.exhaust_pile) >= 2:
                    actions_before = run.player.actions
                    await run_command(plugin, f".rogue p {disc_idx}", user_id)
                    await run_command(plugin, ".rogue exit", user_id)
                    run_end = load_run(plugin, user_id)
                    self.assertEqual(run_end.player.actions, actions_before)
                    self.assertTrue(any(c.id == "discover" and "gem_copy_1" in c.gems for c in run_end.player.hand))
                    break
                await run_command(plugin, ".rogue e", user_id)

        import asyncio
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)
