import unittest
import asyncio
from game.test.core.base import *
from game.models.state import GameRun, PlayerState, EnemyState, Card, BuffState, CardState
from game.models.events import BattleStartEvent, TurnStartEvent, CardPlayedEvent, DamageCalculateEvent
from game.core.world.cafe.engine import CafeEngine

class TestRogueCafe(unittest.TestCase):

    

    

    

    


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
            run = load_run(plugin, user_id)
            run.player.relics.append("crimson_heart")
            run.player.hp = 5
            plugin.save_manager.save_save(user_id, run)
            for _ in range(6):
                run = load_run(plugin, user_id)
                idx = next((i for i, c in enumerate(run.player.hand, 1) if c.id == "fire_bolt"), None)
                if idx is not None:
                    hp_before_enemy = run.enemies[0].hp
                    await run_command(plugin, f".rogue p {idx} e1", user_id)
                    after = load_run(plugin, user_id)
                    self.assertEqual(hp_before_enemy - after.enemies[0].hp, 6)
                    self.assertEqual(after.player.hp, 7)
                    break
                await run_command(plugin, ".rogue e", user_id)

        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)

    def test_cafe_bypass_prefix_talk_and_choose(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_bypass_cafe"
        plugin.save_manager.delete_save(user_id)
        p = PlayerState(
            hp=30, max_hp=30, shield=0, gold=100, stage=13,
            deck=[CardState(id="fire_bolt")], hand=[], draw_pile=[], discard_pile=[],
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
            
            latest_run = load_run(plugin, user_id)
            self.assertEqual(latest_run.node_data["cafe_data"]["active_npc"], "Blacksmith_Ironclad")
            
            res2 = await run_command(plugin, "1", user_id)
            self.assertIn("大锤猛砸", res2)
            
            latest_run2 = load_run(plugin, user_id)
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

    def test_queue_command_works_in_cafe(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_cafe_queue"
        plugin.save_manager.delete_save(user_id)
        stats = plugin.save_manager.load_stats(user_id)
        stats.rogue_mode = True
        plugin.save_manager.save_stats(user_id, stats)
        player = PlayerState(
            hp=30, max_hp=30, shield=0, gold=100, stage=13,
            deck=[CardState(id="fire_bolt")], hand=[], draw_pile=[], discard_pile=[],
            exhaust_pile=[], graveyard=[], relics=[]
        )
        run = GameRun(user_id=user_id, node_type="cafe", player=player, enemies=[], node_data={})
        run.node_data["cafe_data"] = {
            "npcs": ["Blacksmith_Ironclad", "杰斯"],
            "active_npc": None,
            "dialog_state": None,
            "talked_npcs": [],
            "card_master_stock": [],
            "gemcutter_stock": [],
            "hunter_stock": None,
        }
        plugin.save_manager.save_save(user_id, run)

        async def go():
            res = await run_command(plugin, "q [look]", user_id)
            self.assertNotIn("不可用", res)
            self.assertIn("咖啡厅", res)

        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)


