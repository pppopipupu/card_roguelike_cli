from scratch.rogue_tests.base import *
from scratch.rogue_tests.base import MyPlugin
from game.models.state import GameRun, PlayerState, EnemyState, MinionState, BuffState
from game.renderer.query import render_query_info

class TestRoguePotions(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.plugin = MyPlugin(DummyContext())
        self.user_id = "test_user_potions"
        self.plugin.save_manager.delete_save(self.user_id)
        
    async def asyncTearDown(self):
        self.plugin.save_manager.delete_save(self.user_id)

    async def test_potion_basics(self):
        await run_command(self.plugin, "start confirm", self.user_id)
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertIsNotNone(run)
        
        p = run.player
        p.potions = ["healing_potion", "shield_potion"]
        self.plugin.save_manager.save_save(self.user_id, run)
        
        run.node_type = "reward"
        run.node_data = {
            "items": [
                {"type": "potion", "potion_id": "fire_potion", "taken": False}
            ]
        }
        self.plugin.save_manager.save_save(self.user_id, run)
        
        res = await run_command(self.plugin, "1", self.user_id)
        self.assertIn("获得药水【火焰药水】并放入药水槽", res)
        
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertEqual(len(run.player.potions), 3)
        self.assertEqual(run.player.potions[2], "fire_potion")
        
        run.node_type = "reward"
        run.node_data = {
            "items": [
                {"type": "potion", "potion_id": "frost_potion", "taken": False}
            ]
        }
        self.plugin.save_manager.save_save(self.user_id, run)
        
        res = await run_command(self.plugin, "1", self.user_id)
        self.assertIn("药水槽已满", res)
        
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertEqual(len(run.player.potions), 3)
        
        res = await run_command(self.plugin, "丢弃药水 3", self.user_id)
        self.assertIn("已丢弃了药水：【火焰药水】", res)
        
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertEqual(len(run.player.potions), 2)
        
        run.node_type = "reward"
        run.node_data = {
            "items": [
                {"type": "potion", "potion_id": "frost_potion", "taken": False}
            ]
        }
        self.plugin.save_manager.save_save(self.user_id, run)
        res = await run_command(self.plugin, "1", self.user_id)
        self.assertIn("获得药水【冰霜药水】", res)
        
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertEqual(len(run.player.potions), 3)
        self.assertEqual(run.player.potions[2], "frost_potion")

    async def test_potion_battle_use(self):
        await run_command(self.plugin, "start confirm", self.user_id)
        run = self.plugin.save_manager.load_save(self.user_id)
        
        run.node_type = "battle"
        p = run.player
        p.hp = 20
        p.max_hp = 50
        p.shield = 5
        p.potions = ["healing_potion", "shield_potion", "fire_potion"]
        
        run.enemies = [
            EnemyState(name="小地精", hp=30, max_hp=30, shield=0)
        ]
        self.plugin.save_manager.save_save(self.user_id, run)
        
        res = await run_command(self.plugin, "喝药水 1", self.user_id)
        self.assertIn("回复了 10 点生命值", res)
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertEqual(run.player.hp, 30)
        self.assertEqual(len(run.player.potions), 2)
        
        res = await run_command(self.plugin, "喝药水 1", self.user_id)
        self.assertIn("施加了 25 点护盾", res)
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertEqual(run.player.shield, 30)
        
        res = await run_command(self.plugin, "投掷 1 e1", self.user_id)
        self.assertIn("被你投掷的【火焰药水】击中了", res)
        self.assertIn("钝击伤害", res)
        self.assertIn("火焰伤害", res)
        
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertEqual(len(run.enemies), 1)
        self.assertLess(run.enemies[0].hp, 30)

        run = self.plugin.save_manager.load_save(self.user_id)
        run.player.potions = ["poison_potion"]
        self.plugin.save_manager.save_save(self.user_id, run)
        res = await run_command(self.plugin, "投掷 1 e1", self.user_id)
        self.assertIn("投掷了【剧毒药水】", res)
        self.assertIn("造成 10 点毒素伤害并施加 4 层【中毒】", res)

        run = self.plugin.save_manager.load_save(self.user_id)
        run.enemies = [
            EnemyState(name="精英兽人", hp=50, max_hp=50, shield=0)
        ]
        run.enemies[0].buffs = [
            BuffState(id="poison", name="中毒", desc="", stacks=5),
            BuffState(id="doom", name="灾厄", desc="", stacks=10)
        ]
        self.plugin.save_manager.save_save(self.user_id, run)
        res = await run_command(self.plugin, "结束", self.user_id)
        self.assertIn("受到中毒造成的 5 点毒素伤害", res)

        run = self.plugin.save_manager.load_save(self.user_id)
        run.enemies = [
            EnemyState(name="精英兽人", hp=5, max_hp=50, shield=0),
            EnemyState(name="小骷髅", hp=20, max_hp=20, shield=0)
        ]
        run.enemies[0].buffs = [
            BuffState(id="doom", name="灾厄", desc="", stacks=10)
        ]
        self.plugin.save_manager.save_save(self.user_id, run)
        res = await run_command(self.plugin, "结束", self.user_id)
        self.assertIn("灾厄降临", res)
        self.assertIn("直接走向灭亡", res)
        
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertEqual(len(run.enemies), 1)
        self.assertEqual(run.enemies[0].name, "小骷髅")

    async def test_potion_non_battle_limit(self):
        await run_command(self.plugin, "start confirm", self.user_id)
        run = self.plugin.save_manager.load_save(self.user_id)
        
        run.node_type = "explore"
        p = run.player
        p.hp = 10
        p.max_hp = 50
        p.potions = ["healing_potion", "swift_potion"]
        self.plugin.save_manager.save_save(self.user_id, run)
        
        res = await run_command(self.plugin, "喝药水 2", self.user_id)
        self.assertIn("该药水只能在战斗中使用", res)
        
        res = await run_command(self.plugin, "喝药水 1", self.user_id)
        self.assertIn("回复了 10 点生命值", res)
        
        run = self.plugin.save_manager.load_save(self.user_id)
        self.assertEqual(run.player.hp, 20)
        self.assertEqual(len(run.player.potions), 1)

    async def test_potion_query(self):
        res = render_query_info("药水")
        self.assertIn("治疗药水", res)
        self.assertIn("毁灭药水", res)
        
        res_specific = render_query_info("毁灭药水")
        self.assertIn("受到 30 点力场伤害", res_specific)
        self.assertIn("造成 60 点力场伤害", res_specific)
        
        res_tier = render_query_info("epic")
        self.assertIn("能量药水", res_tier)
