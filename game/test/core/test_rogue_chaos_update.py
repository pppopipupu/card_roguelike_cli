import unittest
import random
from game.test.core.base import *
from game.models.state import PlayerState, GameRun, EnemyState, CardState
from game.entities.cards.base import ALL_CARDS
from game.core.battle_engine import BattleEngine
from game.entities.events.chaos_events import (
    ReadVoidTomeOption, BurnVoidBooksOption, SacrificeMindOption,
    BuyBlackmarketRelicOption, RobBlackmarketOption, SellFleshOption,
    DrinkTimeSandOption, AccelerateCinderOption, TouchTimeRiftOption,
    LootWreckageOption, RepairEngineOption, BraveStormOption,
    DigGraveOption, ReadEpitaphOption, CarveOwnNameOption
)

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
            run = plugin.save_manager.load_save(user_id)
            run.player.actions = 5
            run.player.bonus_actions = 2
            plugin.save_manager.save_save(user_id, run)
            for _ in range(6):
                run = plugin.save_manager.load_save(user_id)
                idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "warrior_source_of_cinder"), None)
                if idx is not None:
                    await run_command(plugin, f".rogue p {idx}", user_id)
                    await run_command(plugin, ".rogue e", user_id)
                    after = plugin.save_manager.load_save(user_id)
                    self.assertEqual(after.player.actions, 3)
                    self.assertEqual(after.player.bonus_actions, 2)
                    break
                await run_command(plugin, ".rogue e", user_id)

        import asyncio
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)
    def test_no_retreat_events(self):
        class DummyEngine:
            def __init__(self):
                self.stage_entered = False
                class DummySaveManager:
                    def save_save(self, user_id, run): pass
                self.save_manager = DummySaveManager()
                class DummyExploreEngine:
                    def start_gem_insert_flow(self, run, gem_id, next_type, next_data):
                        return "inserted"
                self.explore_engine = DummyExploreEngine()
                class DummyBattleEngine:
                    def _init_battle_node(self, run, node_type): pass
                    def _append_logs_to_res(self, run, msg): return msg
                self.battle_engine = DummyBattleEngine()
            def enter_next_stage(self, run):
                self.stage_entered = True

        eng = DummyEngine()
        player = PlayerState(
            hp=30, max_hp=30, shield=0, gold=100, stage=1,
            deck=["fire_bolt", "shield_block"], hand=[], actions=3, bonus_actions=2
        )
        run = GameRun(user_id="test_events", node_type="event", player=player, enemies=[])
        
        opt1 = ReadVoidTomeOption()
        res1 = opt1.execute(run, eng)
        self.assertEqual(player.hp, 20)
        self.assertIn("curse_dimensional_tear", player.deck)
        self.assertTrue(eng.stage_entered)

        player.hp = 30
        player.max_hp = 30
        eng.stage_entered = False
        opt2 = BurnVoidBooksOption()
        res2 = opt2.execute(run, eng)
        self.assertEqual(player.max_hp, 23)
        self.assertEqual(player.hp, 23)
        self.assertIn("doomsday_core", player.relics)
        self.assertTrue(eng.stage_entered)

        player.hp = 30
        eng.stage_entered = False
        opt3 = SacrificeMindOption()
        res3 = opt3.execute(run, eng)
        self.assertEqual(player.hp, 22)
        self.assertIn("curse_dazed", player.deck)
        self.assertTrue(eng.stage_entered)

        player.gold = 100
        eng.stage_entered = False
        opt4 = BuyBlackmarketRelicOption()
        res4 = opt4.execute(run, eng)
        self.assertEqual(player.gold, 50)
        self.assertTrue(eng.stage_entered)

        player.gold = 10
        player.hp = 30
        eng.stage_entered = False
        opt5 = BuyBlackmarketRelicOption()
        res5 = opt5.execute(run, eng)
        self.assertEqual(player.hp, 15)
        self.assertTrue(eng.stage_entered)

        eng.stage_entered = False
        opt6 = RobBlackmarketOption()
        res6 = opt6.execute(run, eng)
        self.assertTrue(eng.stage_entered or run.node_type == "battle")

        player.max_hp = 30
        player.hp = 30
        player.gold = 10
        eng.stage_entered = False
        opt7 = SellFleshOption()
        res7 = opt7.execute(run, eng)
        self.assertEqual(player.max_hp, 25)
        self.assertEqual(player.hp, 25)
        self.assertEqual(player.gold, 90)
        self.assertTrue(eng.stage_entered)

        player.max_hp = 30
        player.hp = 30
        eng.stage_entered = False
        opt8 = DrinkTimeSandOption()
        res8 = opt8.execute(run, eng)
        self.assertEqual(player.max_hp, 23)
        self.assertEqual(player.hp, 23)
        self.assertIn("time_sand_blessing", player.relics)
        self.assertTrue(eng.stage_entered)

        player.hp = 30
        eng.stage_entered = False
        opt9 = AccelerateCinderOption()
        res9 = opt9.execute(run, eng)
        self.assertEqual(player.hp, 18)
        self.assertIn("warrior_source_of_cinder", player.deck)
        self.assertTrue(eng.stage_entered)

        player.hp = 30
        player.deck = ["fire_bolt", "shield_block", "arcane_torrent"]
        eng.stage_entered = False
        opt10 = TouchTimeRiftOption()
        res10 = opt10.execute(run, eng)
        self.assertEqual(player.hp, 24)
        self.assertIn("curse_dimensional_tear", player.deck)
        self.assertTrue(eng.stage_entered)

        player.hp = 30
        player.gold = 10
        eng.stage_entered = False
        opt11 = LootWreckageOption()
        res11 = opt11.execute(run, eng)
        self.assertEqual(player.hp, 18)
        self.assertEqual(player.gold, 130)
        self.assertIn("curse_dazed", player.deck)
        self.assertTrue(eng.stage_entered)

        player.max_hp = 30
        player.hp = 30
        player.gold = 100
        eng.stage_entered = False
        opt12 = RepairEngineOption()
        res12 = opt12.execute(run, eng)
        self.assertEqual(player.gold, 70)
        self.assertEqual(player.max_hp, 25)
        self.assertEqual(player.hp, 25)
        self.assertTrue(eng.stage_entered)

        player.hp = 30
        eng.stage_entered = False
        opt13 = BraveStormOption()
        res13 = opt13.execute(run, eng)
        self.assertEqual(player.hp, 18)
        self.assertTrue(eng.stage_entered)

        player.deck = ["fire_bolt"]
        eng.stage_entered = False
        opt14 = DigGraveOption()
        res14 = opt14.execute(run, eng)
        self.assertIn("necromancer_skull", player.relics)
        self.assertTrue(eng.stage_entered)

        player.max_hp = 30
        player.hp = 30
        player.gold = 100
        eng.stage_entered = False
        opt15 = ReadEpitaphOption()
        res15 = opt15.execute(run, eng)
        self.assertEqual(player.max_hp, 50)
        self.assertEqual(player.hp, 50)
        self.assertEqual(player.gold, 0)
        self.assertIn("curse_agony", player.deck)
        self.assertTrue(eng.stage_entered)

        player.hp = 30
        eng.stage_entered = False
        opt16 = CarveOwnNameOption()
        res16 = opt16.execute(run, eng)
        self.assertEqual(player.hp, 15)
        self.assertTrue(eng.stage_entered)

    def test_source_of_cinder_stack(self):
        class DummySaveManager:
            def save_save(self, user_id, run): pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=40, max_hp=40, shield=0, gold=100, stage=1,
            deck=["warrior_source_of_cinder"], hand=["warrior_source_of_cinder"],
            actions=3, bonus_actions=2, buffs=[]
        )
        run = GameRun(user_id="test_cinder_stack", node_type="battle", player=player, enemies=[EnemyState("e1", 10, 10, 0)])
        engine._add_buff_to(player, "source_of_cinder", "薪火之源", "每回合开始额外获得 1A 1BA", 2)
        player.actions = 2
        player.bonus_actions = 1
        from game.models.events import TurnStartEvent
        evt = TurnStartEvent(run, is_player=True)
        engine.event_bus.dispatch(evt)
        self.assertEqual(player.actions, 4)
        self.assertEqual(player.bonus_actions, 3)

    def test_gem_effects_independent(self):
        class DummySaveManager:
            def save_save(self, user_id, run): pass
            def settle_game_and_delete(self, user_id, run, is_victory): return ""
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
        class DummySaveManager:
            def save_save(self, user_id, run): pass
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
        self.assertEqual(run.node_data["state_stack"][-1]["type"], "overload_star_select")
        self.assertEqual(len(player.exhaust_pile), 0)
        has_copy = any("neutral_emperor_eye" in (cid.id if hasattr(cid, "id") else cid) for cid in player.hand)
        self.assertFalse(has_copy)
        ge.execute_emperor_eye_resolve(run, 0, False)
        self.assertEqual(len(player.exhaust_pile), 2)
        has_copy_after = any("neutral_emperor_eye" in (cid.id if hasattr(cid, "id") else cid) for cid in player.hand)
        self.assertTrue(has_copy_after)

    def test_discover_suspend_and_resolve(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_discover_resolve_cmd"
        plugin.save_manager.delete_save(user_id)
        stats = plugin.save_manager.load_stats(user_id)
        stats.locked_cards = ["discover:gems:gem_copy_1", "first_aid"]
        plugin.save_manager.save_stats(user_id, stats)

        async def go():
            await run_command(plugin, ".rogue 主城", user_id)
            await run_command(plugin, ".rogue home", user_id)
            await run_command(plugin, ".rogue up", user_id)
            await run_command(plugin, ".rogue talk Dummy", user_id)
            await run_command(plugin, ".rogue 2", user_id)
            for _ in range(8):
                run = plugin.save_manager.load_save(user_id)
                fa_idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "first_aid"), None)
                if fa_idx is not None:
                    await run_command(plugin, f".rogue p {fa_idx}", user_id)
                run = plugin.save_manager.load_save(user_id)
                disc_idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "discover"), None)
                if disc_idx is not None and run.player.exhaust_pile:
                    res = await run_command(plugin, f".rogue p {disc_idx}", user_id)
                    self.assertIn("请选择一张卡牌发掘", res)
                    run_mid = plugin.save_manager.load_save(user_id)
                    self.assertFalse(any(c.id == "discover" for c in run_mid.player.hand))
                    res_sel = await run_command(plugin, ".rogue 选择 1", user_id)
                    self.assertIn("发掘", res_sel)
                    run_end = plugin.save_manager.load_save(user_id)
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
        stats.locked_cards = ["discover:gems:gem_copy_1", "first_aid"]
        plugin.save_manager.save_stats(user_id, stats)

        async def go():
            await run_command(plugin, ".rogue 主城", user_id)
            await run_command(plugin, ".rogue home", user_id)
            await run_command(plugin, ".rogue up", user_id)
            await run_command(plugin, ".rogue talk Dummy", user_id)
            await run_command(plugin, ".rogue 2", user_id)
            for _ in range(8):
                run = plugin.save_manager.load_save(user_id)
                fa_idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "first_aid"), None)
                if fa_idx is not None:
                    await run_command(plugin, f".rogue p {fa_idx}", user_id)
                run = plugin.save_manager.load_save(user_id)
                disc_idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "discover"), None)
                if disc_idx is not None and run.player.exhaust_pile:
                    actions_before = run.player.actions
                    await run_command(plugin, f".rogue p {disc_idx}", user_id)
                    await run_command(plugin, ".rogue exit", user_id)
                    run_end = plugin.save_manager.load_save(user_id)
                    self.assertEqual(run_end.player.actions, actions_before)
                    self.assertTrue(any(c.id == "discover" and "gem_copy_1" in c.gems for c in run_end.player.hand))
                    break
                await run_command(plugin, ".rogue e", user_id)

        import asyncio
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)
