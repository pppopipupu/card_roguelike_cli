import os
import unittest
import asyncio
import sys
from scratch.rogue_tests.base import *

class TestRogueTown(unittest.TestCase):
    def test_town_full_loop(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        stats_path = save_manager.get_stats_path("test_user")
        if os.path.exists(stats_path):
            try:
                os.remove(stats_path)
            except:
                pass
        save_manager.delete_save("test_user")

        async def run_test():
            res = await run_command(plugin, ".rogue 主城")
            self.assertIn("中心广场", res)
            self.assertIn("向导长老", res)

            res_q = await run_command(plugin, ".rogue 查询 力量")
            self.assertIn("查询结果", res_q)
            self.assertIn("力量", res_q)

            res_s = await run_command(plugin, ".rogue 统计")
            self.assertIn("生涯统计", res_s)

            res_h = await run_command(plugin, ".rogue 帮助")
            self.assertIn("游戏指令帮助", res_h)

            res = await run_command(plugin, ".rogue talk Guide_Elder")
            self.assertIn("与向导长老闲聊", res)

            res = await run_command(plugin, ".rogue 2")
            self.assertIn("游览商业 A 区", res)
            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("quest_town_tour_state"), "started")
            
            res = await run_command(plugin, ".rogue exit")
            self.assertIn("你结束了与【向导长老】的交谈", res)

            moves = [
                ("right", "fountain"),
                ("right", "shop"),
                ("up", "tavern"),
                ("right", "vip_room"),
                ("left", "tavern"),
                ("down", "shop"),
                ("left", "fountain"),
                ("left", "square"),
                ("down", "market"),
                ("left", "blacksmith"),
                ("right", "market"),
                ("up", "square"),
                ("left", "alley"),
                ("left", "west_gate"),
                ("up", "watch_tower"),
                ("down", "west_gate"),
                ("right", "alley"),
                ("right", "square"),
                ("up", "range"),
                ("down", "square")
            ]

            for direction, expected_room in moves:
                res = await run_command(plugin, f".rogue {direction}")
                stats = save_manager.load_stats("test_user")
                self.assertEqual(stats.town_pos, expected_room)

            stats = save_manager.load_stats("test_user")
            visited = stats.town_flags.get("quest_town_tour_visited", [])
            self.assertEqual(len(visited), 11)

            res = await run_command(plugin, f".rogue up")
            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_pos, "range")
            res = await run_command(plugin, f".rogue up")
            self.assertIn("往这个方向没有路", res)

            res = await run_command(plugin, f".rogue home")
            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_pos, "square")

            await run_command(plugin, ".rogue talk 向导长老")
            res = await run_command(plugin, ".rogue 2")
            self.assertIn("这是奖励你的 2000 GP", res)
            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("quest_town_tour_state"), "completed")
            self.assertEqual(stats.gp, 2000)

            await run_command(plugin, ".rogue exit")

            await run_command(plugin, ".rogue right")
            res = await run_command(plugin, ".rogue take lucky_coin")
            self.assertIn("成功拿取", res)
            stats = save_manager.load_stats("test_user")
            self.assertIn("lucky_coin", stats.town_inventory)

            await run_command(plugin, ".rogue right")
            await run_command(plugin, ".rogue up")
            await run_command(plugin, ".rogue right")
            res = await run_command(plugin, ".rogue pick lost_notebook")
            self.assertIn("成功拿取", res)
            
            res = await run_command(plugin, ".rogue use lost_notebook")
            self.assertIn("先古冒险者秘籍", res)

            await run_command(plugin, ".rogue talk Chest")
            res = await run_command(plugin, ".rogue 1")
            print("CHEST RES IS:", repr(res))
            self.assertIn("结束了与", res)

            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue down")
            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue down")
            await run_command(plugin, ".rogue left")
            res = await run_command(plugin, ".rogue pick strange_ore")
            self.assertIn("成功拿取", res)

            await run_command(plugin, ".rogue right")
            await run_command(plugin, ".rogue up")
            await run_command(plugin, ".rogue left")
            res = await run_command(plugin, ".rogue take wine_glass")
            self.assertIn("成功拿取", res)

            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue up")
            res = await run_command(plugin, ".rogue take rusty_key")
            self.assertIn("成功拿取", res)

            await run_command(plugin, ".rogue down")
            await run_command(plugin, ".rogue right")
            await run_command(plugin, ".rogue right")
            await run_command(plugin, ".rogue right")
            await run_command(plugin, ".rogue right")
            await run_command(plugin, ".rogue up")
            await run_command(plugin, ".rogue right")
            await run_command(plugin, ".rogue talk Chest")
            res = await run_command(plugin, ".rogue 1")
            self.assertIn("你使用锈蚀的钥匙开启了宝箱", res)
            stats = save_manager.load_stats("test_user")
            self.assertIn("discover", stats.locked_cards)
            self.assertNotIn("rusty_key", stats.town_inventory)
            await run_command(plugin, ".rogue exit")

            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue talk Bartender_Jack")
            res = await run_command(plugin, ".rogue 2")
            self.assertIn("答谢金", res)
            stats = save_manager.load_stats("test_user")
            self.assertNotIn("wine_glass", stats.town_inventory)
            await run_command(plugin, ".rogue exit")

            await run_command(plugin, ".rogue down")
            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue down")
            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue talk Blacksmith_Ironclad")
            res = await run_command(plugin, ".rogue 2")
            self.assertIn("铁匠艾恩克拉德满意地接过", res)
            await run_command(plugin, ".rogue exit")

            await run_command(plugin, ".rogue right")
            await run_command(plugin, ".rogue up")
            await run_command(plugin, ".rogue right")
            await run_command(plugin, ".rogue talk Fountain")
            res = await run_command(plugin, ".rogue 1")
            self.assertIn("许愿喷泉", res)
            await run_command(plugin, ".rogue exit")

            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue talk West_Gate")
            res = await run_command(plugin, ".rogue 1")
            res = await run_command(plugin, ".rogue 1")
            res = await run_command(plugin, ".rogue 1")
            self.assertIn("先古支票", res)

            for _ in range(6):
                await run_command(plugin, ".rogue 1")
            res = await run_command(plugin, ".rogue 1")
            self.assertIn("Gate_Guardian", res)
            self.assertIn("Gate_Guardian 破门而出", res)

            stats = save_manager.load_stats("test_user")
            run = save_manager.load_save("test_user")
            self.assertIsNotNone(run)
            self.assertTrue(run.node_data.get("is_town_combat"))

            res = await run_command(plugin, ".rogue 放弃 确认")
            self.assertIn("回到了靶场房间", res)
            run = save_manager.load_save("test_user")
            self.assertIsNone(run)

            res = await run_command(plugin, ".rogue talk NoobSlayer99")
            res = await run_command(plugin, ".rogue 1")
            self.assertTrue(any(x in res for x in ["地精大军克星", "NoobSlayer99"]))
            await run_command(plugin, ".rogue exit")

            res = await run_command(plugin, ".rogue quit")
            self.assertIn("回到主菜单", res)

            save_manager.delete_save("test_user")

        asyncio.run(run_test())

    def test_pppopipupu_awakening(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        save_manager.delete_save("test_user")
        stats_path = save_manager.get_stats_path("test_user")
        if os.path.exists(stats_path):
            try:
                os.remove(stats_path)
            except:
                pass

        async def run_p_test():
            await run_command(plugin, ".rogue 主城")
            await run_command(plugin, ".rogue home")
            await run_command(plugin, ".rogue up")
            await run_command(plugin, ".rogue talk pppopipupu")
            res = await run_command(plugin, ".rogue 2")
            self.assertIn("pppopipupu", res)

            run = save_manager.load_save("test_user")
            self.assertEqual(len(run.enemies), 1)
            enemy = run.enemies[0]
            self.assertEqual(enemy.name, "pppopipupu")
            self.assertEqual(enemy.hp, 1)

            plugin.engine.battle_engine.combat_resolver.damage_target(
                run, "e1", 10, source="player", damage_type="slashing"
            )

            self.assertEqual(enemy.name, "pppopipupu")
            self.assertEqual(enemy.hp, 1)

            res = plugin.engine.battle_engine.enemy_controller.enemy_turn(run)
            self.assertEqual(enemy.name, "【觉醒】pppopipupu")
            self.assertEqual(enemy.hp, 9999)
            self.assertIn("热更新", res)

            save_manager.delete_save("test_user")

        asyncio.run(run_p_test())

    def test_town_map_style(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        stats_path = save_manager.get_stats_path("test_user")
        if os.path.exists(stats_path):
            try:
                os.remove(stats_path)
            except:
                pass
        save_manager.delete_save("test_user")

        async def run_p_test():
            await run_command(plugin, ".rogue 主城")
            res = await run_command(plugin, ".rogue 地图")
            self.assertIn("已成功将主城小地图样式切换为", res)
            self.assertIn("局部雷达十字小地图", res)
            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("map_style"), "radar")
            res = await run_command(plugin, ".rogue map classic")
            self.assertIn("已成功将主城小地图样式切换为", res)
            self.assertIn("经典全局大地图", res)
            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("map_style"), "classic")
            res = await run_command(plugin, ".rogue 地图 雷达")
            self.assertIn("已成功将主城小地图样式切换为", res)
            self.assertIn("局部雷达十字小地图", res)
            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("map_style"), "radar")
            res = await run_command(plugin, ".rogue 地图 invalid")
            self.assertIn("无效的地图样式", res)
            await run_command(plugin, ".rogue quit")
            res_fail = await run_command(plugin, ".rogue 地图")
            self.assertIn("地图样式切换指令仅在主城模式下有效", res_fail)
            save_manager.delete_save("test_user")

        asyncio.run(run_p_test())

    def test_deck_replacement_logic(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        save_manager.delete_save("test_user")
        stats_path = save_manager.get_stats_path("test_user")
        if os.path.exists(stats_path):
            try:
                os.remove(stats_path)
            except:
                pass

        async def run_repl_test():
            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.gp = 1000
            stats.selected_class = "战士"
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue s")
            await run_command(plugin, ".rogue talk 卡牌商人")
            await run_command(plugin, ".rogue 3")
            await run_command(plugin, ".rogue 痛击")
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertIn("warrior_bash", stats.locked_cards)

            await run_command(plugin, ".rogue talk 卡牌商人")
            await run_command(plugin, ".rogue 2")
            res_buy = await run_command(plugin, ".rogue 1")
            self.assertIn("成功", res_buy)
            res_buy2 = await run_command(plugin, ".rogue 2")
            self.assertIn("成功", res_buy2)
            res_buy3 = await run_command(plugin, ".rogue 3")
            self.assertIn("成功", res_buy3)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertEqual(len(stats.purchased_pool), 3)

            stats.town_flags["market_shelf"] = ["invalid_card"]
            save_manager.save_stats("test_user", stats)
            from game.core.town_engine import TownEngine
            town_eng = TownEngine(save_manager, None)
            shelf = town_eng._get_market_shelf(stats)
            self.assertEqual(len(shelf), 10)
            self.assertEqual(shelf[0], "")
            self.assertEqual(shelf[1], "")
            self.assertEqual(shelf[2], "")
            self.assertEqual(shelf[3], "wizard_antimagic_field")

            await run_command(plugin, ".rogue quit")
            res_new = await run_command(plugin, ".rogue 开启")
            self.assertIn("契约", res_new)
            run = save_manager.load_save("test_user")
            self.assertEqual(len(run.player.deck), 8)
            save_manager.delete_save("test_user")

        asyncio.run(run_repl_test())

    def test_networked_quest_hammer(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()

        async def run_ham_test():
            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                try:
                    os.remove(stats_path)
                except:
                    pass

            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.gp = 1000
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue s")
            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue talk Blacksmith_Ironclad")
            await run_command(plugin, ".rogue 2")
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("quest_hammer_state"), "started")

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue w")
            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue pick 铁锤")

            stats = save_manager.load_stats("test_user")
            self.assertIn("smith_hammer", stats.town_inventory)

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue s")
            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue talk Blacksmith_Ironclad")
            res_finish = await run_command(plugin, ".rogue 2")
            self.assertIn("交付", res_finish)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("quest_hammer_state"), "completed")
            self.assertEqual(stats.town_health_bonus, 5)

            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                os.remove(stats_path)

            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.gp = 1000
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue s")
            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue talk Blacksmith_Ironclad")
            await run_command(plugin, ".rogue 2")
            await run_command(plugin, ".rogue exit")

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue w")
            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue d")

            stats = save_manager.load_stats("test_user")
            stats.town_flags[f"pos_Crypto_Whale"] = "shop"
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue talk 推销员")
            res_buy = await run_command(plugin, ".rogue 2")
            self.assertIn("高仿铁锤", res_buy)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertIn("fake_hammer", stats.town_inventory)

            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue s")
            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue talk Blacksmith_Ironclad")
            res_finish_fake = await run_command(plugin, ".rogue 2")
            self.assertIn("高仿铁锤", res_finish_fake)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("quest_hammer_state"), "completed")

            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                os.remove(stats_path)

            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.gp = 1000
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue s")
            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue talk Blacksmith_Ironclad")
            await run_command(plugin, ".rogue 2")
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            stats.player_name = "我的测试名"
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue w")
            await run_command(plugin, ".rogue w")
            await run_command(plugin, ".rogue talk NoobSlayer99")
            res_challenge = await run_command(plugin, ".rogue 2")
            self.assertIn("我的测试名", res_challenge)

            run = save_manager.load_save("test_user")
            self.assertIsNotNone(run)
            self.assertEqual(run.enemies[0].name, "NoobSlayer99")

            run.enemies[0].hp = 0
            save_manager.save_save("test_user", run)
            res_win = await run_command(plugin, ".rogue 结束")
            self.assertIn("战斗胜利", res_win)

            stats = save_manager.load_stats("test_user")
            self.assertTrue(stats.town_flags.get("noob_coerced_hammer"))

            await run_command(plugin, ".rogue s")
            await run_command(plugin, ".rogue s")
            await run_command(plugin, ".rogue a")
            res_talk_smith = await run_command(plugin, ".rogue talk Blacksmith_Ironclad")
            self.assertIn("我的测试名", res_talk_smith)
            res_force_finish = await run_command(plugin, ".rogue 2")
            self.assertIn("NoobSlayer99", res_force_finish)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("quest_hammer_state"), "completed")

            save_manager.delete_save("test_user")

        asyncio.run(run_ham_test())

    def test_networked_quest_brew(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()

        async def run_brew_test():
            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                try:
                    os.remove(stats_path)
                except:
                    pass

            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.gp = 1000
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue w")
            await run_command(plugin, ".rogue talk Bartender_Jack")
            await run_command(plugin, ".rogue 3")
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("quest_brew_state"), "started")

            await run_command(plugin, ".rogue s")

            stats = save_manager.load_stats("test_user")
            stats.town_flags[f"pos_Crypto_Whale"] = "shop"
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue talk 推销员")
            res_buy = await run_command(plugin, ".rogue 2")
            self.assertIn("虚空草药", res_buy)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertIn("void_herb", stats.town_inventory)

            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue talk Fountain")
            res_wash = await run_command(plugin, ".rogue 1")
            self.assertIn("天外甘露草", res_wash)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertIn("wishing_dew", stats.town_inventory)

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue w")
            await run_command(plugin, ".rogue talk Bartender_Jack")
            res_finish = await run_command(plugin, ".rogue 3")
            self.assertIn("甘露草", res_finish)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("quest_brew_state"), "completed")
            self.assertEqual(stats.town_health_bonus, 5)

            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                os.remove(stats_path)

            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.gp = 1000
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue w")
            await run_command(plugin, ".rogue talk Bartender_Jack")
            await run_command(plugin, ".rogue 3")
            await run_command(plugin, ".rogue exit")

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue pick lost_notebook")

            await run_command(plugin, ".rogue left")
            await run_command(plugin, ".rogue talk Bartender_Jack")
            await run_command(plugin, ".rogue 3")
            await run_command(plugin, ".rogue 1")
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertIn("promotional_agreement", stats.town_inventory)

            await run_command(plugin, ".rogue s")

            stats = save_manager.load_stats("test_user")
            stats.town_flags[f"pos_Crypto_Whale"] = "shop"
            save_manager.save_stats("test_user", stats)

            res_talk = await run_command(plugin, ".rogue talk 推销员")
            self.assertIn("物易物", res_talk)
            res_trade = await run_command(plugin, ".rogue 3")
            self.assertIn("独家推广协议", res_trade)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertIn("void_herb", stats.town_inventory)

            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                os.remove(stats_path)

            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.gp = 1000
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue w")
            await run_command(plugin, ".rogue talk Bartender_Jack")
            await run_command(plugin, ".rogue 3")
            await run_command(plugin, ".rogue exit")
            await run_command(plugin, ".rogue talk Bartender_Jack")
            await run_command(plugin, ".rogue 3")
            await run_command(plugin, ".rogue 1")
            await run_command(plugin, ".rogue 2")
            await run_command(plugin, ".rogue 2")
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertIn("promotional_agreement", stats.town_inventory)

            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                os.remove(stats_path)

            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.gp = 1000
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue w")
            await run_command(plugin, ".rogue talk Bartender_Jack")
            await run_command(plugin, ".rogue 3")
            await run_command(plugin, ".rogue exit")

            await run_command(plugin, ".rogue s")
            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue a")

            stats = save_manager.load_stats("test_user")
            stats.town_flags[f"pos_Town_Guard"] = "alley"
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue talk 巡逻卫兵")
            res_guard = await run_command(plugin, ".rogue 2")
            self.assertIn("虚空草药", res_guard)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertTrue(stats.town_flags.get("reported_whale"))
            self.assertIn("void_herb", stats.town_inventory)

            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue d")

            stats = save_manager.load_stats("test_user")
            stats.town_flags[f"pos_Crypto_Whale"] = "shop"
            save_manager.save_stats("test_user", stats)

            res_reported_dialog = await run_command(plugin, ".rogue talk 推销员")
            self.assertIn("告密者", res_reported_dialog)
            await run_command(plugin, ".rogue exit")

            await run_command(plugin, ".rogue a")
            await run_command(plugin, ".rogue talk Fountain")
            await run_command(plugin, ".rogue 1")
            await run_command(plugin, ".rogue exit")
            
            await run_command(plugin, ".rogue d")
            await run_command(plugin, ".rogue talk 神秘店主")
            res_sell = await run_command(plugin, ".rogue 3")
            self.assertIn("天外甘露草", res_sell)
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            self.assertEqual(stats.town_flags.get("quest_brew_state"), "completed")
            self.assertEqual(stats.gp, 3000)

            save_manager.delete_save("test_user")

        asyncio.run(run_brew_test())

    def test_quest_command_log(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()

        async def run_quest_test():
            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                try:
                    os.remove(stats_path)
                except:
                    pass

            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.town_flags["quest_town_tour_state"] = "started"
            stats.town_flags["quest_hammer_state"] = "started"
            save_manager.save_stats("test_user", stats)

            res = await run_command(plugin, ".rogue 任务")
            self.assertIn("冒险者任务日志", res)
            self.assertIn("向导的观光指引", res)
            self.assertIn("铁锤谜案", res)

            res2 = await run_command(plugin, ".rogue quest")
            self.assertIn("冒险者任务日志", res2)

            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                try:
                    os.remove(stats_path)
                except:
                    pass

        asyncio.run(run_quest_test())

    def test_town_shopkeeper_jack(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()

        async def run_shop_test():
            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                try:
                    os.remove(stats_path)
                except:
                    pass

            await run_command(plugin, ".rogue 主城")
            stats = save_manager.load_stats("test_user")
            stats.town_pos = "shop"
            stats.gp = 100000
            save_manager.save_stats("test_user", stats)

            res = await run_command(plugin, ".rogue talk 神秘店主")
            self.assertIn("神秘店主", res)

            res_menu = await run_command(plugin, ".rogue 2")
            self.assertIn("购买 【时序法师】", res_menu)

            res_buy_1 = await run_command(plugin, ".rogue 1")
            self.assertIn("已成功解锁【时序法师】", res_buy_1)

            await run_command(plugin, ".rogue 6")
            await run_command(plugin, ".rogue exit")

            stats = save_manager.load_stats("test_user")
            stats.unlocked_subclasses.append("神秘物品")
            stats.killed_icerainboww = True
            stats.yog_sothoth_kill_count = 1
            save_manager.save_stats("test_user", stats)

            await run_command(plugin, ".rogue talk 神秘店主")
            res_menu_2 = await run_command(plugin, ".rogue 2")
            self.assertIn("购买 【神秘物品】 (已解锁)", res_menu_2)
            self.assertIn("【Icerainboww】 (已解锁)", res_menu_2)
            self.assertIn("【尤格-索托斯】 (已解锁)", res_menu_2)

            res_buy_already = await run_command(plugin, ".rogue 5")
            self.assertIn("你已经解锁了【神秘物品】", res_buy_already)

            res_buy_readonly = await run_command(plugin, ".rogue 6")
            self.assertIn("为通关解锁内容，无需在此处购买", res_buy_readonly)

            await run_command(plugin, ".rogue 8")
            await run_command(plugin, ".rogue exit")

            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                try:
                    os.remove(stats_path)
                except:
                    pass

        asyncio.run(run_shop_test())

    def test_town_combat_victory(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()

        async def run_victory_test():
            save_manager.delete_save("test_user")
            stats_path = save_manager.get_stats_path("test_user")
            if os.path.exists(stats_path):
                try:
                    os.remove(stats_path)
                except:
                    pass

            await run_command(plugin, ".rogue 主城")
            await run_command(plugin, ".rogue up")
            await run_command(plugin, ".rogue talk 训练假人")
            await run_command(plugin, ".rogue 2")

            run = save_manager.load_save("test_user")
            self.assertIsNotNone(run)
            self.assertTrue(run.node_data.get("is_town_combat"))

            plugin.engine.battle_engine.combat_resolver.damage_target(
                run, "e1", 200, source="player", damage_type="slashing"
            )
            save_manager.save_save("test_user", run)

            res = await run_command(plugin, ".rogue 结束")
            self.assertTrue(any(x in res for x in ["训练假人已被摧毁", "战斗胜利"]))

            run_after = save_manager.load_save("test_user")
            self.assertIsNone(run_after)

        asyncio.run(run_victory_test())

    def test_no_absolute_imports_from_game(self):
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        targets = [
            os.path.join(base_dir, "game", "core", "town", "dialog_handler.py"),
            os.path.join(base_dir, "game", "core", "cli", "commands", "general", "class_cmd.py"),
            os.path.join(base_dir, "game", "core", "town_engine.py")
        ]
        for path in targets:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("from game.data", content)


