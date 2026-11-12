import unittest
import asyncio
from game.test.core.base import *
from game.models.state import GameRun, PlayerState, EnemyState, Card, BuffState
from game.models.events import BattleStartEvent, TurnStartEvent, CardPlayedEvent, DamageCalculateEvent
from game.core.cafe_engine import CafeEngine

class TestRogueCafe(unittest.TestCase):

    def test_talk_blacksmith(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_blacksmith"
        plugin.save_manager.delete_save(user_id)
        p = PlayerState(
            hp=30, max_hp=30, shield=0, gold=100, stage=13,
            deck=["fire_bolt"], hand=[], draw_pile=[], discard_pile=[],
            exhaust_pile=[], graveyard=[], relics=[]
        )
        run = GameRun(user_id=user_id, node_type="cafe", player=p, enemies=[], node_data={})
        cafe_data = {
            "npcs": ["Blacksmith_Ironclad", "杰斯", "艾琳", "雷恩"],
            "active_npc": None,
            "dialog_state": None,
            "talked_npcs": [],
            "card_master_stock": [],
            "gemcutter_stock": [],
            "hunter_stock": None
        }
        run.node_data["cafe_data"] = cafe_data
        plugin.save_manager.save_save(user_id, run)
        
        async def go():
            res1 = await run_command(plugin, ".rogue talk 铁匠", user_id)
            self.assertIn("铁匠艾恩克拉德", res1)
            
            latest_run = plugin.save_manager.load_save(user_id)
            self.assertEqual(latest_run.node_data["cafe_data"]["active_npc"], "Blacksmith_Ironclad")
            
            res2 = await run_command(plugin, ".rogue 1", user_id)
            self.assertIn("大锤猛砸", res2)
            
            latest_run2 = plugin.save_manager.load_save(user_id)
            self.assertEqual(latest_run2.player.gold, 30)
            self.assertEqual(latest_run2.node_data["cafe_data"]["active_npc"], None)
            has_upgraded = any(card.id == "fire_bolt" and card.upgraded for card in latest_run2.player.deck)
            self.assertTrue(has_upgraded)
            
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)

    def test_talk_pppopipupu_silence(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_pppo_silence"
        plugin.save_manager.delete_save(user_id)
        p = PlayerState(
            hp=30, max_hp=30, shield=0, gold=100, stage=13,
            deck=["fire_bolt"], hand=[], draw_pile=[], discard_pile=[],
            exhaust_pile=[], graveyard=[], relics=[]
        )
        run = GameRun(user_id=user_id, node_type="cafe", player=p, enemies=[], node_data={})
        cafe_data = {
            "npcs": ["pppopipupu"],
            "active_npc": None,
            "dialog_state": None,
            "talked_npcs": [],
            "card_master_stock": [],
            "gemcutter_stock": [],
            "hunter_stock": None
        }
        run.node_data["cafe_data"] = cafe_data
        plugin.save_manager.save_save(user_id, run)
        
        async def go():
            await run_command(plugin, ".rogue talk pppopipupu", user_id)
            await run_command(plugin, ".rogue 1", user_id)
            res = await run_command(plugin, ".rogue 1", user_id)
            
            latest_run = plugin.save_manager.load_save(user_id)
            self.assertEqual(latest_run.node_type, "gem_insert")
            self.assertEqual(latest_run.node_data["pending_gem"], "gem_return_5")
            
            await run_command(plugin, ".rogue c 1", user_id)
            latest_run2 = plugin.save_manager.load_save(user_id)
            self.assertEqual(latest_run2.node_type, "cafe")
            self.assertTrue(any(c.id == "fire_bolt" and "gem_return_5" in c.gems for c in latest_run2.player.deck))
            
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)

    def test_talk_pppopipupu_purge(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_pppo_purge"
        plugin.save_manager.delete_save(user_id)
        p = PlayerState(
            hp=30, max_hp=30, shield=0, gold=100, stage=13,
            deck=["fire_bolt", "curse_indigestion"], hand=[], draw_pile=[], discard_pile=[],
            exhaust_pile=[], graveyard=[], relics=[]
        )
        run = GameRun(user_id=user_id, node_type="cafe", player=p, enemies=[], node_data={})
        cafe_data = {
            "npcs": ["pppopipupu"],
            "active_npc": None,
            "dialog_state": None,
            "talked_npcs": [],
            "card_master_stock": [],
            "gemcutter_stock": [],
            "hunter_stock": None
        }
        run.node_data["cafe_data"] = cafe_data
        plugin.save_manager.save_save(user_id, run)
        
        async def go():
            await run_command(plugin, ".rogue talk pppopipupu", user_id)
            await run_command(plugin, ".rogue 1", user_id)
            res = await run_command(plugin, ".rogue 2", user_id)
            self.assertIn("净化", res)
            
            latest_run = plugin.save_manager.load_save(user_id)
            self.assertEqual(latest_run.player.gold, 80)
            self.assertNotIn("curse_indigestion", latest_run.player.deck)
            self.assertEqual(latest_run.node_data["cafe_data"]["active_npc"], None)
            
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)

    def test_talk_crimson(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_crimson_talk"
        plugin.save_manager.delete_save(user_id)
        p = PlayerState(
            hp=30, max_hp=30, shield=0, gold=100, stage=13,
            deck=["fire_bolt"], hand=[], draw_pile=[], discard_pile=[],
            exhaust_pile=[], graveyard=[], relics=[]
        )
        run = GameRun(user_id=user_id, node_type="cafe", player=p, enemies=[], node_data={})
        cafe_data = {
            "npcs": ["绯红"],
            "active_npc": None,
            "dialog_state": None,
            "talked_npcs": [],
            "card_master_stock": [],
            "gemcutter_stock": [],
            "hunter_stock": None
        }
        run.node_data["cafe_data"] = cafe_data
        plugin.save_manager.save_save(user_id, run)
        
        async def go():
            await run_command(plugin, ".rogue talk 绯红", user_id)
            res = await run_command(plugin, ".rogue 2", user_id)
            self.assertIn("深吻", res)
            
            latest_run = plugin.save_manager.load_save(user_id)
            self.assertEqual(latest_run.player.max_hp, 36)
            self.assertNotIn("fire_bolt", latest_run.player.deck)
            self.assertEqual(latest_run.node_data["cafe_data"]["active_npc"], None)
            
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)


    def test_relic_crimson_heart(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_crimson"
        plugin.save_manager.delete_save(user_id)
        stats = plugin.save_manager.load_stats(user_id)
        stats.locked_cards = ["fire_bolt"]
        plugin.save_manager.save_stats(user_id, stats)

        async def go():
            await run_command(plugin, ".rogue 主城", user_id)
            await run_command(plugin, ".rogue home", user_id)
            await run_command(plugin, ".rogue up", user_id)
            await run_command(plugin, ".rogue talk Dummy", user_id)
            await run_command(plugin, ".rogue 2", user_id)
            run = plugin.save_manager.load_save(user_id)
            run.player.relics.append("crimson_heart")
            run.player.hp = 5
            plugin.save_manager.save_save(user_id, run)
            for _ in range(6):
                run = plugin.save_manager.load_save(user_id)
                idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "fire_bolt"), None)
                if idx is not None:
                    hp_before_enemy = run.enemies[0].hp
                    await run_command(plugin, f".rogue p {idx} e1", user_id)
                    after = plugin.save_manager.load_save(user_id)
                    self.assertEqual(hp_before_enemy - after.enemies[0].hp, 6)
                    self.assertEqual(after.player.hp, 7)
                    break
                await run_command(plugin, ".rogue e", user_id)

        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)

    def test_relic_espresso(self):
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine.battle_engine
        p = PlayerState(
            hp=20, max_hp=20, shield=0, gold=100, stage=13,
            deck=[], hand=[], draw_pile=[], discard_pile=[],
            exhaust_pile=[], graveyard=[], relics=["espresso_relic"]
        )
        run = GameRun(user_id="test_user_espresso", node_type="battle", player=p, enemies=[], node_data={})
        
        evt = TurnStartEvent(run=run, is_player=True)
        p.actions = 2
        engine.event_bus.dispatch(evt)
        self.assertEqual(p.actions, 3)
        
        plugin.engine.map_engine.enter_next_stage(run)
        self.assertNotIn("espresso_relic", p.relics)

    def test_relic_anthem(self):
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine.battle_engine
        p = PlayerState(
            hp=20, max_hp=20, shield=0, gold=100, stage=13,
            deck=["fire_bolt"], hand=[], draw_pile=[], discard_pile=[],
            exhaust_pile=[], graveyard=[], relics=["anthem_relic_3"]
        )
        run = GameRun(user_id="test_user_anthem", node_type="battle", player=p, enemies=[], node_data={})
        
        engine._init_battle_node(run, "normal")
        self.assertEqual(p.shield, 2)
        self.assertNotIn("anthem_relic_3", p.relics)
        self.assertIn("anthem_relic_2", p.relics)
        
        p.shield = 0
        engine._init_battle_node(run, "normal")
        self.assertEqual(p.shield, 2)
        self.assertNotIn("anthem_relic_2", p.relics)
        self.assertIn("anthem_relic_1", p.relics)
        
        p.shield = 0
        engine._init_battle_node(run, "normal")
        self.assertEqual(p.shield, 2)
        self.assertNotIn("anthem_relic_1", p.relics)

    def test_cafe_bypass_prefix_talk_and_choose(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_bypass_cafe"
        plugin.save_manager.delete_save(user_id)
        p = PlayerState(
            hp=30, max_hp=30, shield=0, gold=100, stage=13,
            deck=["fire_bolt"], hand=[], draw_pile=[], discard_pile=[],
            exhaust_pile=[], graveyard=[], relics=[]
        )
        run = GameRun(user_id=user_id, node_type="cafe", player=p, enemies=[], node_data={})
        cafe_data = {
            "npcs": ["Blacksmith_Ironclad", "杰斯"],
            "active_npc": None,
            "dialog_state": None,
            "talked_npcs": [],
            "card_master_stock": [],
            "gemcutter_stock": [],
            "hunter_stock": None
        }
        run.node_data["cafe_data"] = cafe_data
        plugin.save_manager.save_save(user_id, run)
        
        stats = plugin.save_manager.load_stats(user_id)
        stats.rogue_mode = True
        plugin.save_manager.save_stats(user_id, stats)
        
        async def go():
            res_look = await run_command(plugin, "look", user_id)
            self.assertNotIn("可交互", res_look)
            self.assertNotIn("已交互", res_look)
            
            res1 = await run_command(plugin, "talk 铁匠", user_id)
            self.assertIn("铁匠艾恩克拉德", res1)
            
            latest_run = plugin.save_manager.load_save(user_id)
            self.assertEqual(latest_run.node_data["cafe_data"]["active_npc"], "Blacksmith_Ironclad")
            
            res2 = await run_command(plugin, "1", user_id)
            self.assertIn("大锤猛砸", res2)
            
            latest_run2 = plugin.save_manager.load_save(user_id)
            self.assertEqual(latest_run2.player.gold, 30)
            self.assertEqual(latest_run2.node_data["cafe_data"]["active_npc"], None)
            
            res_look2 = await run_command(plugin, "look", user_id)
            self.assertIn("铁匠艾恩克拉德 (已交互)", res_look2)
            self.assertNotIn("卡牌大师 · 杰斯 (已交互)", res_look2)
            
            res3 = await run_command(plugin, "talk 卡牌大师", user_id)
            self.assertIn("卡牌大师 · 杰斯", res3)
            
            res4 = await run_command(plugin, "1", user_id)
            self.assertIn("你告别了交谈的旅客", res4)
            self.assertIn("卡牌大师 · 杰斯 (已交互)", res4)
            
            res5 = await run_command(plugin, "离开", user_id)
            self.assertIn("重新踏上了", res5)
            
        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)

