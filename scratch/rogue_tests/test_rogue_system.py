import os
import unittest
import asyncio
from scratch.rogue_tests.base import *

class TestRogueSystem(unittest.TestCase):
    @unittest.skip("对决模式已移至独立插件")
    def test_duel_mode_and_exclusivity(self):
        plugin = MyPlugin(DummyContext())
        plugin.save_manager.delete_save("test_user_excl")
        stats_path = plugin.save_manager.get_stats_path("test_user_excl")
        if os.path.exists(stats_path):
            os.remove(stats_path)
            
        async def go():
            event_help = DummyEvent(".duel 帮助", sender_id="test_user_excl")
            async for res in plugin.duel_cmd(event_help):
                event_help.results.append(res)
            self.assertTrue(any("对决模式" in r for r in event_help.results))
            
            event_shortcut_duel = DummyEvent(".duel 帮助", sender_id="test_user_excl")
            await plugin.shortcut_rogue(event_shortcut_duel)
            self.assertTrue(event_shortcut_duel.stopped)
            self.assertTrue(any("对决模式" in r for r in event_shortcut_duel.results))
            
            stats = plugin.save_manager.load_stats("test_user_excl")
            stats.rogue_mode = True
            plugin.save_manager.save_stats("test_user_excl", stats)
            
            event_toggle_duel = DummyEvent(".duel 模式", sender_id="test_user_excl")
            async for res in plugin.duel_cmd(event_toggle_duel):
                event_toggle_duel.results.append(res)
            self.assertTrue(any("免前缀对决模式已开启" in r for r in event_toggle_duel.results))
            
            stats = plugin.save_manager.load_stats("test_user_excl")
            self.assertTrue(stats.duel_mode)
            self.assertFalse(stats.rogue_mode)
            
            event_duel_help = DummyEvent("帮助", sender_id="test_user_excl")
            await plugin.shortcut_rogue(event_duel_help)
            self.assertTrue(event_duel_help.stopped)
            
            event_rogue_start = DummyEvent("开启", sender_id="test_user_excl")
            await plugin.shortcut_rogue(event_rogue_start)
            self.assertFalse(event_rogue_start.stopped)
            
            event_toggle_rogue = DummyEvent(".rogue 模式", sender_id="test_user_excl")
            await plugin.shortcut_rogue(event_toggle_rogue)
            
            stats = plugin.save_manager.load_stats("test_user_excl")
            self.assertTrue(stats.rogue_mode)
            self.assertFalse(stats.duel_mode)
            
            event_rogue_duel = DummyEvent(".rogue 对决 帮助", sender_id="test_user_excl")
            await plugin.shortcut_rogue(event_rogue_duel)
            self.assertTrue(any("未知子命令" in r for r in event_rogue_duel.results))
            
        asyncio.run(go())

        sm = plugin.save_manager
        sm.delete_save("test_user_excl")
        sm.delete_duel_save("test_user_excl")
        
        run_rogue = GameRun(
            user_id="test_user_excl",
            node_type="battle",
            player=PlayerState(hp=50, max_hp=50, shield=0, gold=10, stage=1),
            enemies=[]
        )
        sm.save_save("test_user_excl", run_rogue)
        
        sm.bind_duel_game("test_user_excl", "another_user_excl", "game_excl_123")
        run_duel = GameRun(
            user_id="test_user_excl",
            node_type="duel_battle",
            player=PlayerState(hp=200, max_hp=200, shield=0, gold=0, stage=1),
            enemies=[],
            player2=PlayerState(hp=200, max_hp=200, shield=0, gold=0, stage=1),
            node_data={"player1_id": "test_user_excl", "player2_id": "another_user_excl"}
        )
        sm.save_duel_save("test_user_excl", run_duel)
        
        loaded_rogue = sm.load_save("test_user_excl")
        self.assertIsNotNone(loaded_rogue)
        self.assertEqual(loaded_rogue.node_type, "battle")
        self.assertEqual(loaded_rogue.player.hp, 50)
        
        loaded_duel = sm.load_duel_save("test_user_excl")
        self.assertIsNotNone(loaded_duel)
        self.assertEqual(loaded_duel.node_type, "duel_battle")
        self.assertEqual(loaded_duel.player.hp, 200)
        
        loaded_rogue.player.hp = 35
        sm.save_save("test_user_excl", loaded_rogue)
        
        loaded_duel_check = sm.load_duel_save("test_user_excl")
        self.assertEqual(loaded_duel_check.player.hp, 200)
        
        loaded_duel.player.hp = 180
        sm.save_duel_save("test_user_excl", loaded_duel)
        
        loaded_rogue_check = sm.load_save("test_user_excl")
        self.assertEqual(loaded_rogue_check.player.hp, 35)
        
        sm.delete_save("test_user_excl")
        self.assertIsNone(sm.load_save("test_user_excl"))
        
        loaded_duel_after_rogue_del = sm.load_duel_save("test_user_excl")
        self.assertIsNotNone(loaded_duel_after_rogue_del)
        self.assertEqual(loaded_duel_after_rogue_del.player.hp, 180)
        
        sm.delete_duel_save("test_user_excl")
        self.assertIsNone(sm.load_duel_save("test_user_excl"))

    def test_battle_logs_persistence(self):
        save_manager = SaveManager()
        user_id = "test_user_logs_persistence"
        save_manager.delete_save(user_id)
        player = PlayerState(
            hp=45,
            max_hp=45,
            shield=0,
            gold=20,
            stage=3,
            deck=[],
            hand=[],
            actions=2,
            bonus_actions=1
        )
        run = GameRun(
            user_id=user_id,
            node_type="battle",
            player=player,
            enemies=[]
        )
        run.node_data["battle_logs"] = ["log1", "log2"]
        save_manager.save_save(user_id, run)
        self.assertIn("battle_logs", run.node_data)
        loaded_run = save_manager.load_save(user_id)
        self.assertIsNotNone(loaded_run)
        self.assertNotIn("battle_logs", loaded_run.node_data)
        save_manager.delete_save(user_id)

    def test_warrior_class_and_features(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                class DummyStats:
                    def __init__(self):
                        self.selected_class = "战士"
                        self.selected_subclass = ""
                return DummyStats()
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=20,
            stage=1,
            deck=["warrior_strike", "warrior_defend", "power_through", "barricade", "heavy_blade", "bludgeon"],
            hand=["warrior_strike", "warrior_defend", "power_through", "barricade", "heavy_blade", "bludgeon"],
            actions=2,
            bonus_actions=1
        )
        enemies = [EnemyState("测试敌人A", 100, 100, 0)]
        run = GameRun(
            user_id="test_warrior_user",
            node_type="battle",
            player=player,
            enemies=enemies
        )
        run.node_data["action_surge_uses"] = 2
        
        card_strike = ALL_CARDS["warrior_strike"]
        card_strike.execute(run, "e1", engine)
        self.assertEqual(enemies[0].hp, 94)
        
        card_defend = ALL_CARDS["warrior_defend"]
        card_defend.execute(run, None, engine)
        self.assertEqual(player.shield, 5)
        
        card_power = ALL_CARDS["power_through"]
        card_power.execute(run, None, engine)
        self.assertEqual(player.shield, 20)
        self.assertEqual(player.hand.count("curse_wound"), 2)
        
        card_wound = ALL_CARDS["curse_wound"]
        self.assertTrue(getattr(card_wound, "unplayable", False))
        
        card_barricade = ALL_CARDS["barricade"]
        card_barricade.execute(run, None, engine)
        self.assertTrue(any(b.id == "barricade" for b in player.buffs))
        
        prev_shield = player.shield
        engine.card_player.end_turn(run)
        self.assertEqual(player.shield, prev_shield)
        
        engine._add_buff_to(player, "strength", "力量", "伤害加成", 3)
        card_heavy = ALL_CARDS["heavy_blade"]
        enemies[0].hp = 100
        engine.combat_resolver.card_player = engine.card_player
        
        damage = engine.combat_resolver.get_modified_spell_damage(run, card_heavy, 14)
        self.assertEqual(damage, 14 + 3 * 3)
        
        card_heavy_up = ALL_CARDS["heavy_blade+"]
        damage_up = engine.combat_resolver.get_modified_spell_damage(run, card_heavy_up, 18)
        self.assertEqual(damage_up, 18 + 3 * 5)
        
        plugin = MyPlugin(DummyContext())
        run.node_data["action_surge_uses"] = 2
        
        class DummySaveManagerWithSave:
            def __init__(self, run):
                self.run = run
                self.stats = UserStats()
                self.stats.selected_class = "战士"
                self.stats.selected_subclass = ""
                self.stats.rogue_mode = True
            def load_save(self, user_id):
                return self.run
            def save_save(self, user_id, run):
                self.run = run
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return self.stats
            def save_stats(self, user_id, stats):
                pass
        
        mgr = DummySaveManagerWithSave(run)
        plugin.save_manager = mgr
        plugin.cli_router.save_manager = mgr
        plugin.cli_router.engine = engine

        async def go():
            run.node_data["action_surge_turn_used"] = False
            res_text = await run_command(plugin, "技能 as", sender_id="test_warrior_user")
            self.assertIn("额外", res_text)
            self.assertEqual(run.player.actions, 4)
            self.assertEqual(run.player.bonus_actions, 2)
            self.assertEqual(run.node_data["action_surge_uses"], 1)
            self.assertTrue(run.node_data["action_surge_turn_used"])

            run.node_data["action_surge_uses"] = 2
            run.node_data["action_surge_turn_used"] = False
            run.player.actions = 2
            run.player.bonus_actions = 1
            res_text_sk = await run_command(plugin, "sk", sender_id="test_warrior_user")
            self.assertIn("额外", res_text_sk)
            self.assertEqual(run.player.actions, 4)
            self.assertEqual(run.player.bonus_actions, 2)
            self.assertEqual(run.node_data["action_surge_uses"], 1)
            self.assertTrue(run.node_data["action_surge_turn_used"])

            run.node_data["action_surge_uses"] = 2
            run.node_data["action_surge_turn_used"] = False
            run.player.actions = 2
            run.player.bonus_actions = 1
            res_text_k = await run_command(plugin, "k", sender_id="test_warrior_user")
            self.assertIn("额外", res_text_k)
            self.assertEqual(run.player.actions, 4)
            self.assertEqual(run.player.bonus_actions, 2)
            self.assertEqual(run.node_data["action_surge_uses"], 1)
            self.assertTrue(run.node_data["action_surge_turn_used"])

        asyncio.run(go())

    def test_warrior_ward_and_rally(self):
        from game.core.battle_engine import BattleEngine
        from game.models.state import GameRun, PlayerState, EnemyState, MinionState, Card
        from game.entities.enemies.base import EnemyTemplate
        class DummySaveManager:
            def load_admin_config(self):
                return {}
            def load_stats(self, uid):
                class DummyStats:
                    def __init__(self):
                        self.selected_class = "战士"
                        self.selected_subclass = ""
                return DummyStats()
            def save_save(self, uid, run):
                pass
            def save_stats(self, uid, stats):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=100,
            stage=1,
            deck=["officer_recruit_vanguard"],
            hand=["officer_recruit_vanguard"],
            actions=2,
            bonus_actions=1
        )
        run = GameRun("test_user_w", "battle", player=player, enemies=[EnemyState("测试史莱姆", 20, 20, 0, 1, 0, 1, 0)])
        p = run.player
        p.selected_class = "战士"
        engine._init_battle_node(run)
        self.assertIn("rally_count", run.node_data)
        self.assertEqual(run.node_data["rally_count"], 0)
        engine._summon_minion(run, "shield_guard", "盾卫", 6, 2, 0)
        self.assertEqual(run.node_data["rally_count"], 1)
        self.assertIn("1", p.minions)
        m = p.minions["1"]
        self.assertTrue(any(b.id == "ward" for b in m.buffs))
        enemy_template = EnemyTemplate("test_slime")
        run.enemies[0].hp = 20
        enemy_template._perform_attack(run, engine, run.enemies[0], 5, [])
        self.assertEqual(p.minions["1"].hp, 1)
        p.hand = ["officer_recruit_vanguard"]
        run.node_data["free_minion_cards"] = ["officer_recruit_vanguard"]
        engine.play_card(run, 1, "e1")
        self.assertEqual(run.player.actions, 2)

    def test_deck_contains_all_class_cards(self):
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=20,
            stage=1,
            deck=["warrior_strike", "doomsday_judgment", "time_warp", "arcane_spark"],
            draw_pile=[],
            discard_pile=[],
            hand=[],
            actions=1,
            bonus_actions=1,
            selected_class="战士"
        )
        run = GameRun(
            user_id="test_user_class_cards",
            node_type="map_select",
            player=player,
            enemies=[],
            node_data={}
        )
        from game.renderer import GameRenderer
        output = GameRenderer.render_deck(run)
        self.assertIn("奥术星火", output)
        self.assertIn("末日审判", output)
        self.assertIn("时光倒流", output)
        self.assertIn("打击", output)

    def test_rogue_query_isolation(self):
        res = render_query_info("ancient_eye")
        self.assertNotIn("未找到", res)
        self.assertIn("🎒 遗物", res)
        
        res_duel = render_query_info("duel_warrior_strike")
        self.assertIn("未找到", res_duel)

    @unittest.skip("对决查询已移至独立插件")
    def test_rogue_query_keywords_and_buffs(self):
        for term in ("守护", "ward", "重放", "replay", "烈焰成长", "fire_grow", "炉温反噬", "forge_backfire", "时空强化", "time_warp_spell_boost", "极光圣域", "commander_aurora_emperor"):
            res = render_query_info(term)
            self.assertNotIn("未找到", res)
            
        from game.core.duel.query_manager import QueryManager
        from game.models.manager import SaveManager
        qm = QueryManager(SaveManager())
        for term in ("守护", "ward", "重放", "replay", "烈焰成长", "fire_grow", "炉温反噬", "forge_backfire", "时空强化", "time_warp_spell_boost", "极光圣域", "commander_aurora_emperor"):
            res = qm.render_duel_query_info(term)
            self.assertNotIn("未在对决模式中匹配到", res)

    def test_rogue_query_gems_and_new_keywords(self):
        for term in ("复制", "返回", "copy", "return", "裂变金刚石", "永恒祖母绿", "宝石", "gem", "gem_copy_1", "入场曲", "fanfare", "谢幕曲", "last_words", "吟唱", "countdown"):
            res = render_query_info(term)
            self.assertNotIn("未找到", res)

    def test_rogue_overview_reader(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        save_manager.delete_save("test_user_reader")
        
        async def go():
            stats = save_manager.load_stats("test_user_reader")
            stats.rogue_mode = True
            save_manager.save_stats("test_user_reader", stats)
            
            res = await run_command(plugin, ".rogue overview", sender_id="test_user_reader")
            self.assertIn("魔法肉鸽卡牌总览", res)
            self.assertIn("第 1 /", res)
            
            stats = save_manager.load_stats("test_user_reader")
            self.assertTrue(stats.reader_active)
            self.assertEqual(stats.reader_page, 1)
            
            res2 = await run_command(plugin, "n", sender_id="test_user_reader")
            self.assertIn("第 2 /", res2)
            stats = save_manager.load_stats("test_user_reader")
            self.assertEqual(stats.reader_page, 2)
            
            res3 = await run_command(plugin, "b", sender_id="test_user_reader")
            self.assertIn("第 1 /", res3)
            stats = save_manager.load_stats("test_user_reader")
            self.assertEqual(stats.reader_page, 1)
            
            res4 = await run_command(plugin, "exit", sender_id="test_user_reader")
            self.assertIn("已退出阅读器", res4)
            stats = save_manager.load_stats("test_user_reader")
            self.assertFalse(stats.reader_active)
            
            await run_command(plugin, "overview", sender_id="test_user_reader")
            stats = save_manager.load_stats("test_user_reader")
            self.assertTrue(stats.reader_active)
            
            res5 = await run_command(plugin, "牌组", sender_id="test_user_reader")
            self.assertIn("你当前没有正在进行的游戏", res5)
            stats = save_manager.load_stats("test_user_reader")
            self.assertFalse(stats.reader_active)
            
            save_manager.delete_save("test_user_reader")
            
        asyncio.run(go())

    def test_rogue_action_surge_execution(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        save_manager.delete_save("test_user_warrior")
        
        async def go():
            stats = save_manager.load_stats("test_user_warrior")
            stats.selected_class = "战士"
            stats.selected_subclass = ""
            stats.rogue_mode = True
            save_manager.save_stats("test_user_warrior", stats)
            
            player = PlayerState(
                hp=80, max_hp=80, shield=0, gold=100, stage=1,
                deck=["strike"], draw_pile=["strike"], discard_pile=[], exhaust_pile=[], graveyard=[]
            )
            run = GameRun("test_user_warrior", "battle", player=player, enemies=[EnemyState("测试怪物", 20, 20, 0, 1, 0, 1, 0)])
            save_manager.save_save("test_user_warrior", run)
            
            plugin.engine.battle_engine._init_battle_node(run)
            save_manager.save_save("test_user_warrior", run)
            
            self.assertEqual(run.node_data.get("action_surge_uses"), 2)
            self.assertFalse(run.node_data.get("action_surge_turn_used", False))
            
            res = await run_command(plugin, "k", sender_id="test_user_warrior")
            self.assertIn("战士发动了【动作如潮】", res)
            self.assertIn("还可使用 1 次", res)
            
            run = save_manager.load_save("test_user_warrior")
            self.assertEqual(run.node_data.get("action_surge_uses"), 1)
            self.assertTrue(run.node_data.get("action_surge_turn_used"))
            self.assertEqual(run.player.actions, 4)
            self.assertEqual(run.player.bonus_actions, 2)
            
            res2 = await run_command(plugin, "k", sender_id="test_user_warrior")
            self.assertIn("每回合只能使用一次", res2)
            
            run = save_manager.load_save("test_user_warrior")
            self.assertEqual(run.node_data.get("action_surge_uses"), 1)
            self.assertEqual(run.player.actions, 4)
            self.assertEqual(run.player.bonus_actions, 2)
            
            await run_command(plugin, "e", sender_id="test_user_warrior")
            
            run = save_manager.load_save("test_user_warrior")
            self.assertFalse(run.node_data.get("action_surge_turn_used", False))
            self.assertEqual(run.node_data.get("action_surge_uses"), 1)
            
            res3 = await run_command(plugin, "k", sender_id="test_user_warrior")
            self.assertIn("战士发动了【动作如潮】", res3)
            self.assertIn("还可使用 0 次", res3)
            
            run = save_manager.load_save("test_user_warrior")
            self.assertEqual(run.node_data.get("action_surge_uses"), 0)
            self.assertTrue(run.node_data.get("action_surge_turn_used"))
            
            res4 = await run_command(plugin, "k", sender_id="test_user_warrior")
            self.assertIn("本场战斗的使用次数已用尽", res4)
            
            save_manager.delete_save("test_user_warrior")
            
        asyncio.run(go())

    def test_rogue_import_path_isolation(self):
        import subprocess
        import os
        import sys
        
        cwd = os.getcwd()
        parent_dir = os.path.dirname(cwd)
        basename = os.path.basename(cwd)
        
        env = os.environ.copy()
        if "PYTHONPATH" in env:
            del env["PYTHONPATH"]
            
        script = "import sys, asyncio; sys.path.insert(0, '" + parent_dir.replace('\\', '/') + "'); sys.path.insert(0, '" + cwd.replace('\\', '/') + "'); from scratch.rogue_tests.base import MyPlugin; from scratch.rogue_tests.base import run_command; plugin = MyPlugin(None); stats = plugin.save_manager.load_stats('test_import'); stats.rogue_mode = True; plugin.save_manager.save_stats('test_import', stats); asyncio.run(run_command(plugin, 'overview', 'test_import'))"
        
        res = subprocess.run(
            [sys.executable, "-c", script],
            cwd=parent_dir,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        self.assertEqual(res.returncode, 0, f"Import test failed: {res.stderr}")

    def test_rogue_discover_card(self):
        plugin = MyPlugin(DummyContext())
        save_manager = plugin.save_manager
        save_manager.delete_save("test_user_discover")
        
        async def go():
            stats = save_manager.load_stats("test_user_discover")
            stats.rogue_mode = True
            save_manager.save_stats("test_user_discover", stats)
            
            player = PlayerState(
                hp=80, max_hp=80, shield=0, gold=100, stage=1,
                deck=["discover", "dagger_throw", "first_aid"],
                hand=["discover", "dagger_throw"],
                draw_pile=[], discard_pile=[],
                exhaust_pile=[]
            )
            run = GameRun("test_user_discover", "battle", player=player, enemies=[EnemyState("测试怪物", 20, 20, 0)])
            save_manager.save_save("test_user_discover", run)
            
            res_empty = await run_command(plugin, "使用 1", sender_id="test_user_discover")
            self.assertIn("没有任何可以发掘的卡牌", res_empty)
            
            run = save_manager.load_save("test_user_discover")
            run.player.exhaust_pile = ["dagger_throw", "first_aid", "adrenaline"]
            run.player.hand = ["discover", "dagger_throw"]
            run.player.actions = 2
            run.player.bonus_actions = 1
            save_manager.save_save("test_user_discover", run)
            
            res_param = await run_command(plugin, "使用 1 2", sender_id="test_user_discover")
            self.assertIn("发掘了消耗堆中的【绷带包扎】", res_param)
            run = save_manager.load_save("test_user_discover")
            self.assertNotIn("discover", run.player.hand)
            self.assertIn("first_aid", run.player.hand)
            self.assertNotIn("first_aid", run.player.exhaust_pile)
            self.assertEqual(run.player.actions, 1)
            self.assertEqual(len(run.node_data.get("state_stack", [])), 0)
            
            run.player.hand = ["discover", "dagger_throw"]
            run.player.exhaust_pile = ["dagger_throw", "first_aid", "adrenaline"]
            run.player.actions = 2
            save_manager.save_save("test_user_discover", run)
            
            res_no_param = await run_command(plugin, "使用 1", sender_id="test_user_discover")
            self.assertIn("请选择一张卡牌发掘", res_no_param)
            self.assertIn("1. 匕首投掷", res_no_param)
            self.assertIn("2. 绷带包扎", res_no_param)
            
            res_invalid = await run_command(plugin, "使用 1", sender_id="test_user_discover")
            self.assertIn("你必须从消耗堆中选择卡牌", res_invalid)
            
            res_choose = await run_command(plugin, "选择 2", sender_id="test_user_discover")
            self.assertIn("你完成了发掘", res_choose)
            self.assertIn("绷带包扎", res_choose)
            
            run = save_manager.load_save("test_user_discover")
            self.assertIn("first_aid", run.player.hand)
            self.assertNotIn("first_aid", run.player.exhaust_pile)
            self.assertEqual(len(run.node_data.get("state_stack", [])), 0)
            
            run.player.hand = ["discover+", "dagger_throw"]
            run.player.exhaust_pile = ["dagger_throw", "first_aid", "adrenaline"]
            run.player.actions = 2
            save_manager.save_save("test_user_discover", run)
            
            res_up = await run_command(plugin, "使用 1", sender_id="test_user_discover")
            self.assertIn("请选择一张卡牌发掘", res_up)
            
            res_up_c1 = await run_command(plugin, "c 2", sender_id="test_user_discover")
            self.assertIn("请继续选择第 2 张", res_up_c1)
            
            res_up_c2 = await run_command(plugin, "c 1", sender_id="test_user_discover")
            self.assertIn("你完成了发掘", res_up_c2)
            self.assertIn("匕首投掷", res_up_c2)
            
            run = save_manager.load_save("test_user_discover")
            self.assertIn("first_aid", run.player.hand)
            self.assertIn("dagger_throw", run.player.hand)
            self.assertEqual(len(run.node_data.get("state_stack", [])), 0)
            
            run.player.hand = ["discover", "dagger_throw"]
            run.player.exhaust_pile = ["dagger_throw", "first_aid"]
            run.player.actions = 2
            save_manager.save_save("test_user_discover", run)
            
            await run_command(plugin, "使用 1", sender_id="test_user_discover")
            event_cancel = DummyEvent("exit", sender_id="test_user_discover")
            await plugin.shortcut_rogue(event_cancel)
            self.assertTrue(event_cancel.stopped)
            self.assertTrue(any("取消发掘操作" in r for r in event_cancel.results))
            run = save_manager.load_save("test_user_discover")
            from game.models.state import CardState
            run.player.exhaust_pile = [
                CardState(id="discover", upgraded=False),
                CardState(id="dagger_throw"),
                CardState(id="discover", upgraded=True)
            ]
            run.player.hand = [
                CardState(id="discover"),
                CardState(id="first_aid")
            ]
            run.player.actions = 2
            save_manager.save_save("test_user_discover", run)
            res_excl = await run_command(plugin, "使用 1", sender_id="test_user_discover")
            self.assertIn("1. 匕首投掷", res_excl)
            self.assertNotIn("发掘+", res_excl)
            self.assertNotIn("2. ", res_excl.split("━━━━━━━━━━━━━━━━━━━━")[0])
            res_sel_fail = await run_command(plugin, "选择 2", sender_id="test_user_discover")
            self.assertIn("无效的消耗堆序号", res_sel_fail)
            res_sel_ok = await run_command(plugin, "选择 1", sender_id="test_user_discover")
            self.assertIn("获得了【匕首投掷】", res_sel_ok)
            
            save_manager.delete_save("test_user_discover")
            
        asyncio.run(go())

    def test_multi_card_lock_system(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_multi_lock"
        plugin.save_manager.delete_save(user_id)
        stats_path = plugin.save_manager.get_stats_path(user_id)
        if os.path.exists(stats_path):
            os.remove(stats_path)

        async def go():
            stats = plugin.save_manager.load_stats(user_id)
            stats.gp = 1000
            stats.locked_cards = []
            plugin.save_manager.save_stats(user_id, stats)

            res_menu = await run_command(plugin, "lock", sender_id=user_id)
            self.assertIn("锁定卡牌管理系统", res_menu)
            self.assertIn("暂无任何锁定的卡牌", res_menu)

            res_fail_notfound = await run_command(plugin, "lock 绝无此卡", sender_id=user_id)
            self.assertIn("未找到", res_fail_notfound)

            res_fail_legendary = await run_command(plugin, "lock fireball_upgrade_legendary", sender_id=user_id)
            if "fireball_upgrade_legendary" in ALL_CARDS:
                self.assertIn("无法锁定", res_fail_legendary)

            stats.gp = 200
            plugin.save_manager.save_stats(user_id, stats)
            res_fail_gp = await run_command(plugin, "lock 痛击", sender_id=user_id)
            self.assertIn("当前仅有", res_fail_gp.replace(" ", ""))

            stats.gp = 1000
            plugin.save_manager.save_stats(user_id, stats)
            res_success = await run_command(plugin, "lock 痛击", sender_id=user_id)
            self.assertIn("锁定成功", res_success)
            self.assertIn("痛击", res_success)

            stats = plugin.save_manager.load_stats(user_id)
            self.assertEqual(stats.gp, 700)
            self.assertIn("warrior_bash", stats.locked_cards)

            res_fail_dup = await run_command(plugin, "lock 痛击", sender_id=user_id)
            self.assertIn("已经", res_fail_dup)

            stats.gp = 5000
            stats.locked_cards.append("dummy_card_0")
            plugin.save_manager.save_stats(user_id, stats)
            self.assertEqual(len(plugin.save_manager.load_stats(user_id).locked_cards), 2)

            res_fail_limit = await run_command(plugin, "lock 防御", sender_id=user_id)
            self.assertIn("最多只能同时锁定", res_fail_limit)

            res_unlock = await run_command(plugin, "unlock 痛击", sender_id=user_id)
            self.assertIn("解锁成功", res_unlock)
            stats = plugin.save_manager.load_stats(user_id)
            self.assertNotIn("warrior_bash", stats.locked_cards)

            res_clear = await run_command(plugin, "lock clear", sender_id=user_id)
            self.assertIn("成功清空", res_clear)
            stats = plugin.save_manager.load_stats(user_id)
            self.assertEqual(len(stats.locked_cards), 0)

            stats.guaranteed_card = "warrior_bash"
            stats.locked_cards = ["warrior_defend"]
            plugin.save_manager.save_stats(user_id, stats)

            stats.rogue_mode = True
            stats.selected_class = "战士"
            plugin.save_manager.save_stats(user_id, stats)
            
            res_start = await run_command(plugin, "start", sender_id=user_id)
            self.assertIn("契约", res_start)

            run = plugin.save_manager.load_save(user_id)
            self.assertIsNotNone(run)
            card_ids = [c.id for c in run.player.deck]
            self.assertIn("warrior_bash", card_ids)
            self.assertIn("warrior_defend", card_ids)

            stats_after = plugin.save_manager.load_stats(user_id)
            self.assertIsNone(stats_after.guaranteed_card)
            self.assertIn("warrior_bash", stats_after.locked_cards)
            self.assertIn("warrior_defend", stats_after.locked_cards)

            plugin.save_manager.delete_save(user_id)
            stats_path = plugin.save_manager.get_stats_path(user_id)
            if os.path.exists(stats_path):
                os.remove(stats_path)

        asyncio.run(go())

    def test_locked_cards_truncated_to_two(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_lock_truncate"
        stats_path = plugin.save_manager.get_stats_path(user_id)
        if os.path.exists(stats_path):
            os.remove(stats_path)

        stats = plugin.save_manager.load_stats(user_id)
        stats.locked_cards = ["warrior_strike", "warrior_defend", "warrior_bash", "fire_bolt", "shield"]
        plugin.save_manager.save_stats(user_id, stats)

        loaded = plugin.save_manager.load_stats(user_id)
        self.assertEqual(loaded.locked_cards, ["warrior_strike", "warrior_defend"])

        async def go():
            res = await run_command(plugin, "lock", sender_id=user_id)
            self.assertIn("(2 / 2)", res)

        asyncio.run(go())
        if os.path.exists(stats_path):
            os.remove(stats_path)

    def test_starting_deck_class_cards(self):
        plugin = MyPlugin(DummyContext())

        async def go():
            for class_name, tag, expected in (
                ("战士", "warrior", ["warrior_strike", "warrior_defend", "warrior_bash"]),
                ("法师", "wizard", ["fire_bolt", "shield", "magic_missile"]),
            ):
                user_id = "test_user_starting_" + tag
                stats_path = plugin.save_manager.get_stats_path(user_id)
                if os.path.exists(stats_path):
                    os.remove(stats_path)
                stats = plugin.save_manager.load_stats(user_id)
                stats.rogue_mode = True
                stats.selected_class = class_name
                plugin.save_manager.save_stats(user_id, stats)

                await run_command(plugin, "start", sender_id=user_id)
                run = plugin.save_manager.load_save(user_id)
                self.assertIsNotNone(run)
                card_ids = [c.id for c in run.player.deck]
                self.assertEqual(card_ids[:3], expected)
                self.assertEqual(len(card_ids), 8)

                plugin.save_manager.delete_save(user_id)
                if os.path.exists(stats_path):
                    os.remove(stats_path)

        asyncio.run(go())

    def test_yog_sothoth_phase4_and_compat(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_user_yog"
        plugin.save_manager.delete_save(user_id)
        
        stats_path = plugin.save_manager.get_stats_path(user_id)
        if os.path.exists(stats_path):
            os.remove(stats_path)
            
        import json
        old_data = {
            "user_id": user_id,
            "gp": 500,
            "killed_yog_sothoth": True,
            "unlocked_classes": []
        }
        os.makedirs(os.path.dirname(stats_path), exist_ok=True)
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(old_data, f)
            
        stats = plugin.save_manager.load_stats(user_id)
        self.assertFalse(hasattr(stats, "killed_yog_sothoth") or "killed_yog_sothoth" in stats.__dict__)
        self.assertEqual(stats.yog_sothoth_kill_count, 0)
        self.assertEqual(stats.yog_sothoth_challenge_count, 0)
        
        from game.models.state import EnemyState, GameRun, PlayerState
        run = GameRun(
            user_id=user_id,
            node_type="battle",
            player=PlayerState(hp=100, max_hp=100, shield=0, gold=10, stage=32),
            enemies=[EnemyState(
                name="【万物归一】虚空之门·尤格-索托斯",
                hp=2147483647,
                max_hp=2147483647,
                shield=0
            )]
        )
        from game.renderer.battle import render_battle
        rendered = render_battle(run)
        self.assertIn("0x7FFFFFFF/0x7FFFFFFF", rendered)
        
        from game.models.state import BuffState
        run.player.buffs.append(BuffState(id="all_resonance", name="万物共振", stacks=2, desc="造成的伤害翻 10^S 倍"))
        
        from game.core.battle.combat_resolver import CombatResolver
        resolver = CombatResolver(plugin.engine.battle_engine)
        run.node_data["battle_logs"] = []
        resolver.damage_target(run, "e1", 5, source="p0", damage_type="force")
        self.assertEqual(run.enemies[0].hp, 2147483647 - 500)
        
        plugin.save_manager.delete_save(user_id)
        if os.path.exists(stats_path):
            os.remove(stats_path)

    def test_query_pendulum_resonance(self):
        from game.renderer.query import render_query_info
        res = render_query_info("钟摆共振")
        self.assertIn("钟摆共振", res)
        self.assertIn("受打出牌数*2点真伤惩罚", res)


