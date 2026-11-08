import os
import unittest
import asyncio
from scratch.rogue_tests.base import *

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
            self.assertIn("第 2 层", res)
            res = await run_command(plugin, ".rogue 牌组")
            self.assertIn("当前拥有的卡组", res)
            res = await run_command(plugin, ".rogue 选择 1")
            self.assertTrue(any(x in res for x in ["战斗", "遭遇战", "神秘事件", "商店", "精英战", "营地", "选择"]))
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
            self.assertNotIn("游戏指令帮助", qi_res)

            event_qi2 = DummyEvent("中断队列 [未知指令_测试, 帮助]", sender_id="test_user_rogue")
            await plugin.shortcut_rogue(event_qi2)
            self.assertTrue(event_qi2.stopped)
            qi_res2 = "\n".join(event_qi2.results)
            self.assertIn("未知操作", qi_res2)
            self.assertNotIn("游戏指令帮助", qi_res2)
            
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
            
            player_minion = PlayerState(
                hp=30, max_hp=30, shield=0, gold=100, stage=2, deck=[], hand=[], draw_pile=[], discard_pile=[], exhaust_pile=[], graveyard=[],
                minions={"1": MinionState("mercenary", "雇佣兵", 10, 10, 4, 2, 0)}
            )
            class MockEngine:
                def __init__(self):
                    self.attack_called = False
                    self.skill_called = False
                def minion_attack(self, run, g, opp):
                    self.attack_called = True
                    return "攻击成功"
                def minion_skill(self, run, g, idx, target):
                    self.skill_called = True
                    return "技能成功"
                def is_battle_won(self, run):
                    return False
            mock_engine = MockEngine()
            mgr.saved_run = GameRun(user_id="test_user", node_type="battle", player=player_minion, enemies=[EnemyState("e1", 10, 10, 0)])
            plugin.cli_router.engine = mock_engine
            await run_command(plugin, "m 1 attack e1")
            self.assertTrue(mock_engine.attack_called)
            await run_command(plugin, "m 1 skill e1")
            self.assertTrue(mock_engine.skill_called)

        asyncio.run(go())

    def test_admin_jump_command(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_jump_user"
        plugin.save_manager.delete_save(user_id)

        async def go():
            await run_command(plugin, ".rogue 开启", sender_id=user_id)
            await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            run = plugin.save_manager.load_save(user_id)
            self.assertIsNotNone(run)

            event_help = DummyEvent("/rogueadmin", sender_id=user_id)
            generator = plugin.rogueadmin(event_help)
            async for _ in generator:
                pass
            self.assertIn("立即跳到某一层", "\n".join(event_help.results))

            event_jump_26 = DummyEvent(f"/rogueadmin jump {user_id} 26", sender_id=user_id)
            generator = plugin.rogueadmin(event_jump_26)
            async for _ in generator:
                pass
            res_text = "\n".join(event_jump_26.results)
            self.assertIn("成功跳转到第 26 层", res_text)
            self.assertIn("咖啡厅", res_text)

            run = plugin.save_manager.load_save(user_id)
            self.assertEqual(run.player.stage, 26)
            self.assertEqual(run.node_type, "cafe")

            res_leave = await run_command(plugin, ".rogue 离开", sender_id=user_id)
            self.assertIn("先古赐福", res_leave)

            run = plugin.save_manager.load_save(user_id)
            self.assertEqual(run.player.stage, 26)
            self.assertEqual(run.node_type, "ancient")

            event_jump_25 = DummyEvent(f"/rogueadmin jump {user_id} 25", sender_id=user_id)
            generator = plugin.rogueadmin(event_jump_25)
            async for _ in generator:
                pass
            res_text = "\n".join(event_jump_25.results)
            self.assertIn("成功跳转到第 25 层", res_text)
            self.assertIn("战斗阶段", res_text)

            run = plugin.save_manager.load_save(user_id)
            self.assertEqual(run.player.stage, 25)
            self.assertEqual(run.node_type, "battle")

            event_jump_15 = DummyEvent(f"/rogueadmin jump {user_id} 15", sender_id=user_id)
            generator = plugin.rogueadmin(event_jump_15)
            async for _ in generator:
                pass
            res_text = "\n".join(event_jump_15.results)
            self.assertIn("成功跳转到第 15 层", res_text)
            self.assertTrue(any(x in res_text for x in ["路线选择", "遭遇战", "神秘事件", "奇妙商店", "篝火营地", "古老宝箱"]))

            run = plugin.save_manager.load_save(user_id)
            self.assertEqual(run.player.stage, 15)
            self.assertEqual(run.node_type, "map_select")

            plugin.save_manager.delete_save(user_id)

        asyncio.run(go())

    def test_admin_icerainboww_command(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_icerainboww_admin_user"
        
        async def go():
            event_check = DummyEvent("/rogueadmin icerainboww", sender_id=user_id)
            generator = plugin.rogueadmin(event_check)
            async for _ in generator:
                pass
            res_text = "\n".join(event_check.results)
            self.assertIn("配置状态", res_text)

            event_off = DummyEvent("/rogueadmin icerainboww off", sender_id=user_id)
            generator = plugin.rogueadmin(event_off)
            async for _ in generator:
                pass
            self.assertIn("成功【关闭】", "\n".join(event_off.results))

            cfg = plugin.save_manager.load_admin_config()
            self.assertFalse(cfg.get("icerainboww_enabled", True))

            event_on = DummyEvent("/rogueadmin icerainboww on", sender_id=user_id)
            generator = plugin.rogueadmin(event_on)
            async for _ in generator:
                pass
            self.assertIn("成功【开启】", "\n".join(event_on.results))

            cfg = plugin.save_manager.load_admin_config()
            self.assertTrue(cfg.get("icerainboww_enabled", True))

        asyncio.run(go())

    def test_admin_add_card_command(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_add_card_admin_user"
        plugin.save_manager.delete_save(user_id)

        async def go():
            await run_command(plugin, ".rogue 开启", sender_id=user_id)
            await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            
            event_help = DummyEvent("/rogueadmin", sender_id=user_id)
            generator = plugin.rogueadmin(event_help)
            async for _ in generator:
                pass
            self.assertIn("add_card", "\n".join(event_help.results))

            event_add_1 = DummyEvent(f"/rogueadmin add_card 火球术", sender_id=user_id)
            generator = plugin.rogueadmin(event_add_1)
            async for _ in generator:
                pass
            res_text = "\n".join(event_add_1.results)
            self.assertIn("成功将卡牌", res_text)
            self.assertIn("火球术", res_text)

            run = plugin.save_manager.load_save(user_id)
            self.assertIn("fireball", run.player.deck)

            event_add_2 = DummyEvent(f"/rogueadmin add_card user_other warrior_strike", sender_id=user_id)
            event_add_2_alt = DummyEvent(f"/rogueadmin add_card warrior_strike+ user_other", sender_id=user_id)
            
            plugin.save_manager.delete_save("user_other")
            await run_command(plugin, ".rogue 开启", sender_id="user_other")
            await run_command(plugin, ".rogue 选择 1", sender_id="user_other")

            generator = plugin.rogueadmin(event_add_2)
            async for _ in generator:
                pass
            res_text2 = "\n".join(event_add_2.results)
            self.assertIn("成功将卡牌", res_text2)

            run_other = plugin.save_manager.load_save("user_other")
            self.assertIn("warrior_strike", run_other.player.deck)

            generator = plugin.rogueadmin(event_add_2_alt)
            async for _ in generator:
                pass
            res_text_alt = "\n".join(event_add_2_alt.results)
            self.assertIn("成功将卡牌", res_text_alt)

            run_other = plugin.save_manager.load_save("user_other")
            self.assertTrue(any(c.id == "warrior_strike" and c.upgraded for c in run_other.player.deck))

            run = plugin.save_manager.load_save(user_id)
            run.node_type = "battle"
            plugin.save_manager.save_save(user_id, run)

            event_add_battle = DummyEvent(f"/rogueadmin add_card fireball+ {user_id}", sender_id=user_id)
            generator = plugin.rogueadmin(event_add_battle)
            async for _ in generator:
                pass
            res_battle = "\n".join(event_add_battle.results)
            self.assertIn("直接加入手牌", res_battle)

            run = plugin.save_manager.load_save(user_id)
            self.assertTrue(any(c.id == "fireball" and c.upgraded for c in run.player.deck))
            self.assertTrue(any(c.id == "fireball" and c.upgraded for c in run.player.hand))

            plugin.save_manager.delete_save(user_id)
            plugin.save_manager.delete_save("user_other")

        asyncio.run(go())

    def test_battle_turn_count(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_turn_count"
        plugin.save_manager.delete_save(user_id)

        async def go():
            await run_command(plugin, ".rogue 开启", sender_id=user_id)
            await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            run = plugin.save_manager.load_save(user_id)
            run.node_type = "battle"
            run.node_data["turn_count"] = 1
            run.enemies = [EnemyState("dummy_enemy", 20, 20, 0)]
            plugin.save_manager.save_save(user_id, run)

            res = await run_command(plugin, ".rogue 状态", sender_id=user_id)
            self.assertIn("战斗阶段 (第 1 回合)", res)

            res_detailed = await run_command(plugin, ".rogue 查询", sender_id=user_id)
            self.assertIn("实时战斗详细情报 (第 1 回合)", res_detailed)

            await run_command(plugin, ".rogue 结束", sender_id=user_id)
            run = plugin.save_manager.load_save(user_id)
            self.assertEqual(run.node_data.get("turn_count"), 2)

            res2 = await run_command(plugin, ".rogue 状态", sender_id=user_id)
            self.assertIn("战斗阶段 (第 2 回合)", res2)

            res_detailed2 = await run_command(plugin, ".rogue 查询", sender_id=user_id)
            self.assertIn("实时战斗详细情报 (第 2 回合)", res_detailed2)

            plugin.save_manager.delete_save(user_id)

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


