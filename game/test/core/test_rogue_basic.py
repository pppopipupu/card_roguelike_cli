import os
import unittest
import asyncio
from game.test.core.base import *

class TestRogueBasic(unittest.TestCase):
    def test_basic_flow(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        save_manager.delete_save("test_user")
        stats_path = save_manager.get_stats_path("test_user")
        if os.path.exists(stats_path):
            try:
                os.remove(stats_path)
            except:
                pass
        
        async def go():
            res = await run_command(plugin, ".rogue 开启 确认")
            self.assertTrue(any(x in res for x in ["先古契约", "深渊契约", "极寒契约"]))
            res = await run_command(plugin, ".rogue 选择 1")
            self.assertIn("契约达成", res)
            res = await run_command(plugin, ".rogue 状态")
            self.assertIn("第 1 层", res)
            res = await run_command(plugin, ".rogue 牌组")
            self.assertIn("当前拥有的卡组", res)
            res, _ = await async_move_to_room(plugin, "test_user", ("battle", "elite", "shop", "rest", "treasure", "cafe"))
            self.assertTrue(any(x in res for x in ["战斗", "遭遇战", "回合", "神秘事件", "事件", "商店", "精英战", "营地", "选择", "咖啡", "宝箱", "地标", "商人"]))
            save_manager.delete_save("test_user")
            
        asyncio.run(go())

    def test_class_command_aliases(self):
        class DummySaveManagerLocal:
            def __init__(self):
                self.stats = UserStats()
                self.stats.rogue_mode = True
                self.stats.unlocked_subclasses = ["时序法师", "塑能法师"]
            def load_stats(self, user_id):
                return self.stats
            def save_stats(self, user_id, stats):
                self.stats = stats
                return True
            def load_save(self, user_id):
                return None
        mgr = DummySaveManagerLocal()
        plugin = MyPlugin(DummyContext())
        plugin.save_manager = mgr
        plugin.cli_router.save_manager = mgr

        async def go():
            res = await run_command(plugin, "class")
            self.assertIn("魔法肉鸽卡牌职业系统", res)
            await run_command(plugin, "class c 1")
            self.assertEqual(mgr.stats.selected_subclass, "时序法师")
            await run_command(plugin, "class c 2")
            self.assertEqual(mgr.stats.selected_subclass, "塑能法师")
            await run_command(plugin, "class 2")
            self.assertEqual(mgr.stats.selected_subclass, "塑能法师")
            await run_command(plugin, "class 0")
            self.assertEqual(mgr.stats.selected_subclass, "")
            await run_command(plugin, "class c 0")
            self.assertEqual(mgr.stats.selected_subclass, "")
            res = await run_command(plugin, "class c 4")
            self.assertIn("无效的子职业", res)
            await run_command(plugin, "class c 时序法师")
            self.assertEqual(mgr.stats.selected_subclass, "时序法师")
            await run_command(plugin, "class 无")
            self.assertEqual(mgr.stats.selected_subclass, "")

            res_conflict_wiz = await run_command(plugin, "c wizard")
            self.assertIn("使用 /rogue class", res_conflict_wiz)
            self.assertIn("选择命令 c 仅用于局内选项选择", res_conflict_wiz)

            res_conflict_num = await run_command(plugin, "c 1")
            self.assertIn("使用 /rogue class", res_conflict_num)

            res_normal_c = await run_command(plugin, "c")
            self.assertEqual("❌ 你当前没有正在进行的游戏。", res_normal_c)

        asyncio.run(go())

        class DummySaveManagerWithSave:
            def __init__(self):
                self.stats = UserStats()
                self.stats.rogue_mode = True
                self.stats.unlocked_subclasses = ["时序法师", "塑能法师"]
            def load_stats(self, user_id):
                return self.stats
            def save_stats(self, user_id, stats):
                self.stats = stats
                return True
            def load_save(self, user_id):
                player = PlayerState(hp=30, max_hp=30, shield=0, gold=100, stage=2, deck=[], hand=[], draw_pile=[], discard_pile=[], exhaust_pile=[], graveyard=[])
                return GameRun(user_id=user_id, node_type="event", player=player, enemies=[], node_data={"event_id": "test_event"})
        mgr_with_save = DummySaveManagerWithSave()
        plugin_with_save = MyPlugin(DummyContext())
        plugin_with_save.save_manager = mgr_with_save
        plugin_with_save.cli_router.save_manager = mgr_with_save

        async def go_save():
            res_in_game = await run_command(plugin_with_save, "c wizard")
            self.assertIn("使用 /rogue class", res_in_game)

        asyncio.run(go_save())

    def test_rogue_mode_and_shortcut(self):
        plugin = MyPlugin(DummyContext())
        plugin.save_manager.delete_save("test_user_rogue")
        stats_path = plugin.save_manager.get_stats_path("test_user_rogue")
        if os.path.exists(stats_path):
            os.remove(stats_path)
        stats = plugin.save_manager.load_stats("test_user_rogue")
        self.assertFalse(stats.rogue_mode)
        
        async def go():
            event_toggle = DummyEvent(".rogue mode", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_toggle)
            loaded_stats = plugin.save_manager.load_stats("test_user_rogue")
            self.assertTrue(loaded_stats.rogue_mode)
            self.assertIn("免前缀肉鸽模式已开启", "\n".join(event_toggle.results))
            
            event_start = DummyEvent("开启", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_start)
            self.assertTrue(event_start.stopped)
            self.assertTrue(any(x in "\n".join(event_start.results) for x in ["先古契约", "深渊契约", "极寒契约"]))
            
            event_chat = DummyEvent("你好吗", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_chat)
            self.assertFalse(event_chat.stopped)
            
            event_num_with_save = DummyEvent("1", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_num_with_save)
            self.assertTrue(event_num_with_save.stopped)
            
            event_alias_deck = DummyEvent("deck", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_alias_deck)
            self.assertTrue(event_alias_deck.stopped)
            self.assertIn("当前拥有的卡组", "\n".join(event_alias_deck.results))
            
            event_alias_overview = DummyEvent("overview", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_alias_overview)
            self.assertTrue(event_alias_overview.stopped)
            self.assertIn("魔法肉鸽卡牌总览", "\n".join(event_alias_overview.results))

            event_qi = DummyEvent("queue_interrupt [未知指令_测试, 帮助]", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_qi)
            self.assertTrue(event_qi.stopped)
            qi_res = "\n".join(event_qi.results)
            self.assertIn("未知操作", qi_res)
            self.assertNotIn("指令一览", qi_res)

            event_qi2 = DummyEvent("中断队列 [未知指令_测试, 帮助]", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_qi2)
            self.assertTrue(event_qi2.stopped)
            qi_res2 = "\n".join(event_qi2.results)
            self.assertIn("未知操作", qi_res2)
            self.assertNotIn("指令一览", qi_res2)
            
            event_alias_abandon = DummyEvent("abandon confirm", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_alias_abandon)
            self.assertTrue(event_alias_abandon.stopped)
            self.assertIn("已放弃当前局内游戏", "\n".join(event_alias_abandon.results))
            
            event_town = DummyEvent("主城", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_town)
            self.assertTrue(event_town.stopped)
            self.assertIn("先古主城", "\n".join(event_town.results))
            
            event_town_exit = DummyEvent("退出", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_town_exit)
            self.assertTrue(event_town_exit.stopped)
            
            event_num_no_save = DummyEvent("1", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_num_no_save)
            self.assertFalse(event_num_no_save.stopped)
            
            event_toggle_off = DummyEvent("模式", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_toggle_off)
            off_stats = plugin.save_manager.load_stats("test_user_rogue")
            self.assertFalse(off_stats.rogue_mode)
            
            event_start_disabled = DummyEvent("开启", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_start_disabled)
            self.assertFalse(event_start_disabled.stopped)
            
        asyncio.run(go())

    def test_new_english_aliases(self):
        class DummySaveManager:
            def __init__(self):
                self.stats = UserStats()
                self.stats.rogue_mode = True
                self.stats.unlocked_subclasses = ["时序法师", "塑能法师", "秘钥学者"]
                self.saved_run = None
            def load_stats(self, user_id):
                return self.stats
            def save_stats(self, user_id, stats):
                self.stats = stats
                return True
            def load_save(self, user_id):
                return self.saved_run
            def save_save(self, user_id, run):
                self.saved_run = run
            def settle_game_and_delete(self, user_id, run, is_victory=False):
                self.saved_run = None
                return "游戏已结算。"
        
        mgr = DummySaveManager()
        plugin = MyPlugin(DummyContext())
        plugin.save_manager = mgr
        plugin.engine.save_manager = mgr
        plugin.cli_router.save_manager = mgr
        plugin.cli_router.engine.save_manager = mgr
        plugin.cli_router.town_engine.save_manager = mgr
        
        async def go():
            player = PlayerState(hp=30, max_hp=30, shield=0, gold=100, stage=2, deck=[], hand=[], draw_pile=[], discard_pile=[], exhaust_pile=[], graveyard=[])
            mgr.saved_run = GameRun(user_id="test_user", node_type="event", player=player, enemies=[], node_data={"event_id": "test_event"})
            res = await run_command(plugin, "start confirm")
            self.assertIn("已重新开始新的一局游戏", res)
            
            mgr.saved_run = None
            await run_command(plugin, "class choose chronomancer")
            self.assertEqual(mgr.stats.selected_subclass, "时序法师")
            await run_command(plugin, "class select evoker")
            self.assertEqual(mgr.stats.selected_subclass, "塑能法师")
            await run_command(plugin, "class select arcanist")
            self.assertEqual(mgr.stats.selected_subclass, "秘钥学者")
            
            mgr.stats.gp = 99999
            mgr.stats.unlocked_subclasses = []
            mgr.stats.town_pos = "shop"
            await run_command(plugin, "town")
            await run_command(plugin, "talk 神秘店主")
            await run_command(plugin, "2")
            await run_command(plugin, "1")
            self.assertIn("时序法师", mgr.stats.unlocked_subclasses)
            await run_command(plugin, "2")
            self.assertIn("塑能法师", mgr.stats.unlocked_subclasses)
            await run_command(plugin, "3")
            self.assertIn("秘钥学者", mgr.stats.unlocked_subclasses)
            await run_command(plugin, "4")
            self.assertTrue(mgr.stats.unlocked_gatekey)
            

        asyncio.run(go())


    def test_play_card_by_pinyin_initials(self):
        from game.models.state import CardState

        class DummySaveManager:
            def __init__(self):
                self.stats = UserStats()
                self.stats.rogue_mode = True
                self.saved_run = None
            def load_stats(self, user_id):
                return self.stats
            def save_stats(self, user_id, stats):
                self.stats = stats
                return True
            def load_save(self, user_id):
                return self.saved_run
            def save_save(self, user_id, run):
                self.saved_run = run
            def settle_game_and_delete(self, user_id, run, is_victory=False):
                self.saved_run = None
                return "游戏已结算。"

        def build():
            mgr = DummySaveManager()
            plugin = MyPlugin(DummyContext())
            plugin.save_manager = mgr
            plugin.engine.save_manager = mgr
            plugin.cli_router.save_manager = mgr
            plugin.cli_router.engine.save_manager = mgr
            plugin.cli_router.town_engine.save_manager = mgr
            player = PlayerState(
                hp=30,
                max_hp=30,
                shield=0,
                gold=100,
                stage=2,
                deck=[],
                hand=[
                    CardState(id="adrenaline", upgraded=True),
                    CardState(id="thunderwave"),
                    CardState(id="adrenaline")
                ],
                draw_pile=[],
                discard_pile=[],
                exhaust_pile=[],
                graveyard=[],
                minions={},
                amulets={},
                buffs=[],
                actions=3,
                bonus_actions=2
            )
            enemies = [EnemyState("测试敌人A", 50, 50, 2), EnemyState("测试敌人B", 50, 50, 2)]
            mgr.saved_run = GameRun(user_id="test_user_pinyin", node_type="battle", player=player, enemies=enemies)
            return plugin, mgr

        async def go():
            for cmd in ("p ssxs", "p SSXS", "p sxs"):
                plugin, mgr = build()
                run = mgr.saved_run
                res = await run_command(plugin, cmd)
                self.assertNotIn("❌", res)
                self.assertEqual(run.player.hp, 27)
                self.assertEqual(run.player.actions, 4)
                self.assertEqual(run.player.bonus_actions, 3)
                self.assertEqual(run.player.hand[0].id, "thunderwave")
                self.assertEqual(len(run.player.hand), 2)

            plugin, mgr = build()
            run = mgr.saved_run
            res = await run_command(plugin, "p lmb")
            self.assertNotIn("❌", res)
            self.assertEqual([c.id for c in run.player.hand], ["adrenaline", "adrenaline"])
            self.assertTrue(all(e.hp < 50 for e in run.enemies))

            plugin, mgr = build()
            run = mgr.saved_run
            res = await run_command(plugin, "p zz")
            self.assertIn("❌", res)
            self.assertEqual(len(run.player.hand), 3)
            self.assertEqual(run.player.hp, 30)

            plugin, mgr = build()
            run = mgr.saved_run
            res = await run_command(plugin, "p 3")
            self.assertNotIn("❌", res)
            self.assertEqual(run.player.hp, 28)
            self.assertEqual(run.player.bonus_actions, 2)

            plugin, mgr = build()
            run = mgr.saved_run
            res = await run_command(plugin, "q [p ssxs, p lmb]")
            self.assertEqual([c.id for c in run.player.hand], ["adrenaline"])

        asyncio.run(go())


