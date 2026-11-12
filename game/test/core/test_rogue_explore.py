import unittest
import asyncio
from game.test.core.base import *

class TestRogueExplore(unittest.TestCase):
    def test_inner_shop_flow(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_inner_shop_user"
        plugin.save_manager.delete_save(user_id)
        
        async def go():
            await run_command(plugin, ".rogue 开启", sender_id=user_id)
            await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            run = plugin.save_manager.load_save(user_id)
            self.assertIsNotNone(run)
            run.node_type = "shop"
            plugin.engine.map_engine.explore_engine._init_shop_node(run)
            plugin.save_manager.save_save(user_id, run)
            
            status_output = await run_command(plugin, ".rogue 状态", sender_id=user_id)
            self.assertIn("奇妙商店", status_output)
            self.assertIn("净化服务", status_output)
            self.assertIn("离开商店", status_output)
            
            run = plugin.save_manager.load_save(user_id)
            run.player.gold = 500
            plugin.save_manager.save_save(user_id, run)
            initial_gold = 500
            initial_deck_len = len(run.player.deck)
            
            items = run.node_data.get("items", [])
            card_idx = -1
            for idx, item in enumerate(items):
                if item.get("type") == "card":
                    card_idx = idx + 1
                    break
            self.assertNotEqual(card_idx, -1)
            buy_res = await run_command(plugin, f".rogue 选择 {card_idx}", sender_id=user_id)
            self.assertIn("购买成功", buy_res)
            
            run = plugin.save_manager.load_save(user_id)
            self.assertEqual(len(run.player.deck), initial_deck_len + 1)
            self.assertLess(run.player.gold, initial_gold)
            
            relic_idx = -1
            for idx, item in enumerate(items):
                if item.get("type") == "relic":
                    relic_idx = idx + 1
                    break
            if relic_idx != -1:
                run = plugin.save_manager.load_save(user_id)
                run.player.gold = 500
                plugin.save_manager.save_save(user_id, run)
                buy_relic_res = await run_command(plugin, f".rogue 选择 {relic_idx}", sender_id=user_id)
                self.assertIn("购买成功", buy_relic_res)
                run = plugin.save_manager.load_save(user_id)
                relic_id = items[relic_idx - 1].get("relic_id")
                self.assertIn(relic_id, run.player.relics)
                
            remove_idx = -1
            for idx, item in enumerate(items):
                if item.get("type") == "remove":
                    remove_idx = idx + 1
                    break
            if remove_idx != -1:
                run = plugin.save_manager.load_save(user_id)
                run.player.gold = 500
                run.node_type = "shop"
                plugin.engine.map_engine.explore_engine._init_shop_node(run)
                for it in run.node_data["items"]:
                    if it.get("type") == "remove":
                        it["sold"] = False
                plugin.save_manager.save_save(user_id, run)
                remove_trigger_res = await run_command(plugin, f".rogue 选择 {remove_idx}", sender_id=user_id)
                self.assertIn("净化服务已启动", remove_trigger_res)
                run = plugin.save_manager.load_save(user_id)
                self.assertTrue(run.node_data.get("pending_remove"))
                cancel_res = await run_command(plugin, ".rogue 选择 取消", sender_id=user_id)
                self.assertIn("已取消卡牌移除操作", cancel_res)
                run = plugin.save_manager.load_save(user_id)
                self.assertFalse(run.node_data.get("pending_remove"))
                await run_command(plugin, f".rogue 选择 {remove_idx}", sender_id=user_id)
                run = plugin.save_manager.load_save(user_id)
                deck_before = len(run.player.deck)
                remove_card_res = await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
                self.assertIn("已成功从你的卡组中移除", remove_card_res)
                run = plugin.save_manager.load_save(user_id)
                self.assertEqual(len(run.player.deck), deck_before - 1)
                self.assertFalse(run.node_data.get("pending_remove"))

            leave_idx = -1
            for idx, item in enumerate(items):
                if item.get("type") == "leave":
                    leave_idx = idx + 1
                    break
            self.assertNotEqual(leave_idx, -1)
            leave_res = await run_command(plugin, f".rogue 选择 {leave_idx}", sender_id=user_id)
            self.assertIn("你离开了商店", leave_res)
            run = plugin.save_manager.load_save(user_id)
            self.assertNotEqual(run.node_type, "shop")
            
        asyncio.run(go())

    def test_treasure_three_choices(self):
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=10,
            stage=4,
            deck=["first_aid", "dagger_throw", "agile_strike"],
            draw_pile=[],
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            hand=[]
        )
        run = GameRun(
            user_id="test_user_treasure",
            node_type="treasure",
            player=player,
            enemies=[]
        )
        plugin = MyPlugin(DummyContext())
        map_engine = plugin.engine.map_engine
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def record_stage_passed(self, user_id):
                pass
        map_engine.save_manager = DummySaveManager()
        map_engine._init_treasure_node(run)
        self.assertEqual(run.node_data.get("state"), "pending_remove")
        map_engine.choose_option(run, 3)
        self.assertEqual(run.node_type, "gem_insert")
        map_engine.gem_insert_cancel(run)
        self.assertEqual(run.node_type, "card_select")
        self.assertEqual(len(run.node_data.get("cards", [])), 3)
        self.assertGreater(player.gold, 10)
        self.assertEqual(len(player.deck), 2)
        self.assertNotIn("first_aid", player.deck)
        map_engine.choose_option(run, 4)
        self.assertEqual(player.stage, 5)
        self.assertEqual(len(player.deck), 2)
        player.stage = 3
        run.node_type = "rest"
        map_engine.choose_option(run, 2)
        self.assertEqual(run.node_type, "card_select")
        self.assertEqual(len(run.node_data.get("cards", [])), 3)
        chosen_card = run.node_data["cards"][0]
        map_engine.choose_option(run, 1)
        self.assertEqual(player.stage, 4)
        self.assertEqual(len(player.deck), 3)
        self.assertIn(chosen_card, player.deck)
        player.stage = 5
        player.gold = 20
        run.node_type = "event"
        from game.entities.events import CoinFountainOption
        opt = CoinFountainOption("投入金币", "coin_fountain")
        opt.execute(run, map_engine)
        self.assertEqual(player.gold, 10)
        self.assertEqual(run.node_type, "card_select")
        self.assertEqual(len(run.node_data.get("cards", [])), 3)
        map_engine.choose_option(run, 4)
        self.assertEqual(player.stage, 6)
        self.assertEqual(len(player.deck), 3)

    def test_card_upgrade_and_forge(self):
        from game.models.state import CardState
        mhw = ALL_CARDS.get("mass_healing_word")
        mhw_plus = ALL_CARDS[CardState(id="mass_healing_word", upgraded=True)]
        self.assertIsNotNone(mhw)
        self.assertIsNotNone(mhw_plus)
        self.assertTrue(mhw_plus.upgraded)
        self.assertEqual(mhw_plus.heal_amount, 12)

        fb = ALL_CARDS.get("fireball")
        fb_plus = ALL_CARDS[CardState(id="fireball", upgraded=True)]
        self.assertIsNotNone(fb)
        self.assertIsNotNone(fb_plus)
        self.assertTrue(fb_plus.upgraded)
        self.assertEqual(fb_plus.base_dmg, 24)
        q_res_normal = render_query_info("fireball")
        self.assertIn("升级变体", q_res_normal)
        self.assertIn("24", q_res_normal)
        q_res_plus = render_query_info("fireball")
        self.assertIn("升级变体", q_res_plus)
        self.assertIn("24", q_res_plus)
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        save_manager.delete_save("test_user_upg")
        
        async def go():
            await run_command(plugin, ".rogue 开启 确认", sender_id="test_user_upg")
            await run_command(plugin, ".rogue 选择 1", sender_id="test_user_upg")
            run = save_manager.load_save("test_user_upg")
            run.node_type = "rest"
            run.node_data = {}
            save_manager.save_save("test_user_upg", run)
            res = await run_command(plugin, ".rogue 选择 4", sender_id="test_user_upg")
            self.assertIn("卡牌升级强化已启动", res)
            run = save_manager.load_save("test_user_upg")
            self.assertTrue(run.node_data.get("pending_upgrade"))
            res_upg = await run_command(plugin, ".rogue 选择 1", sender_id="test_user_upg")
            self.assertIn("升级成功", res_upg)
            run = save_manager.load_save("test_user_upg")
            self.assertTrue(any(card.upgraded for card in run.player.deck))
            run.node_type = "event"
            run.node_data = {
                "event_id": "forge_furnace",
                "description": "奥术符文熔炉描述",
                "options": [
                    {"text": "使用常规重铸", "action": "forge_fire"},
                    {"text": "过载重铸", "action": "overload_forge"},
                    {"text": "汲取熔炉余温", "action": "forge_backfire"},
                    {"text": "强行破坏熔炉", "action": "shatter_forge"},
                    {"text": "安全离开", "action": "leave_event"}
                ]
            }
            save_manager.save_save("test_user_upg", run)
            res_event_fire = await run_command(plugin, ".rogue 选择 1", sender_id="test_user_upg")
            self.assertIn("卡牌升级强化已启动", res_event_fire)
            run = save_manager.load_save("test_user_upg")
            run.node_type = "event"
            run.node_data = {
                "event_id": "forge_furnace",
                "description": "奥术符文熔炉描述",
                "options": [
                    {"text": "使用常规重铸", "action": "forge_fire"},
                    {"text": "过载重铸", "action": "overload_forge"},
                    {"text": "汲取熔炉余温", "action": "forge_backfire"},
                    {"text": "强行破坏熔炉", "action": "shatter_forge"},
                    {"text": "安全离开", "action": "leave_event"}
                ]
            }
            save_manager.save_save("test_user_upg", run)
            res_backfire = await run_command(plugin, ".rogue 选择 3", sender_id="test_user_upg")
            self.assertIn("炉温反噬", res_backfire)
            run = save_manager.load_save("test_user_upg")
            self.assertTrue(any(b.id == "forge_backfire" for b in run.player.buffs))
            save_manager.delete_save("test_user_upg")
            
        asyncio.run(go())

    def test_awaiting_target_cancel(self):
        save_manager = SaveManager()
        plugin = MyPlugin(DummyContext())
        plugin.save_manager = save_manager
        plugin.engine.save_manager = save_manager
        plugin.cli_router.save_manager = save_manager
        plugin.cli_router.engine.save_manager = save_manager
        plugin.cli_router.town_engine.save_manager = save_manager
        
        user_id = "test_user_awaiting_cancel"
        save_manager.delete_save(user_id)
        
        stats = save_manager.load_stats(user_id)
        stats.rogue_mode = True
        save_manager.save_stats(user_id, stats)
        
        player = PlayerState(
            hp=45,
            max_hp=45,
            shield=0,
            gold=20,
            stage=3,
            deck=["fleeting_spark", "fleeting_spark"],
            hand=["fleeting_spark", "fleeting_spark"],
            actions=2,
            bonus_actions=1
        )
        enemies = [
            EnemyState(
                name="哥布林 A",
                hp=18,
                max_hp=18,
                shield=0,
                intent_type="attack",
                intent_val=6,
                intent_desc="攻击",
                intent_a_type="attack",
                intent_a_val=6,
                intent_a_desc="攻击"
            ),
            EnemyState(
                name="哥布林 B",
                hp=18,
                max_hp=18,
                shield=0,
                intent_type="shield",
                intent_val=7,
                intent_desc="防御",
                intent_a_type="shield",
                intent_a_val=7,
                intent_a_desc="防御"
            )
        ]
        run = GameRun(
            user_id=user_id,
            node_type="battle",
            player=player,
            enemies=enemies
        )
        run.node_data["state_stack"] = [{
            "type": "awaiting_target",
            "action": "play_card",
            "hand_idx": 1
        }]
        save_manager.save_save(user_id, run)
        
        async def go():
            output_text = await run_command(plugin, "p 2", sender_id=user_id)
            loaded_run = save_manager.load_save(user_id)
            state_stack = loaded_run.node_data.get("state_stack", [])
            self.assertNotIn("❌ 取消使用操作。", output_text)
            self.assertEqual(len(state_stack), 0)
            self.assertIn("使用", output_text)
            save_manager.delete_save(user_id)
            
        asyncio.run(go())


    def test_new_ancient_features(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=1,
            deck=["break_limits", "abyss_collapse", "demon_contract", "frost_nova", "glacier_fortress"],
            hand=["break_limits", "abyss_collapse", "demon_contract", "frost_nova", "glacier_fortress"],
            actions=5,
            bonus_actions=5,
            buffs=[]
        )
        enemies = [
            EnemyState("测试敌人A", 50, 50, 0)
        ]
        run = GameRun(
            user_id="test_new_features_user",
            node_type="battle",
            player=player,
            enemies=enemies
        )
        engine._add_buff_to(player, "strength", "力量", "造成的伤害增加", 3)
        engine._add_buff_to(player, "stun", "眩晕", "无法行动", 1)
        card_limits = ALL_CARDS["break_limits"]
        card_limits.execute(run, None, engine)
        strength_buff = next(b for b in player.buffs if b.id == "strength")
        stun_buff = next(b for b in player.buffs if b.id == "stun")
        self.assertEqual(strength_buff.stacks, 6)
        self.assertEqual(stun_buff.stacks, 1)
        card_collapse = ALL_CARDS["abyss_collapse"]
        enemies[0].hp = 50
        card_collapse.execute(run, None, engine)
        self.assertEqual(enemies[0].hp, 26)
        engine._add_buff_to(enemies[0], "stun", "眩晕", "无法行动", 1)
        enemies[0].hp = 50
        card_collapse.execute(run, None, engine)
        self.assertEqual(enemies[0].hp, 2)

    def test_more_ancient_relics_and_cards(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def load_stats(self, user_id):
                class DummyStats:
                    def __init__(self):
                        self.unlocked_gatekey = True
                        self.killed_icerainboww = True
                        self.killed_yog_sothoth = False
                return DummyStats()
            def save_stats(self, user_id, stats):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=40,
            max_hp=40,
            shield=20,
            gold=100,
            stage=1,
            deck=[],
            hand=["abyss_altar", "abyss_erosion", "glacier_tempest", "abyss_altar+"],
            actions=5,
            bonus_actions=5,
            buffs=[],
            relics=["abyss_contract", "glacier_core"]
        )
        enemies = [
            EnemyState("测试敌人A", 600, 600, 0)
        ]
        run = GameRun(
            user_id="test_more_features_user",
            node_type="battle",
            player=player,
            enemies=enemies
        )
        engine.card_player.end_turn(run)
        self.assertEqual(enemies[0].hp, 595)
        self.assertEqual(player.shield, 10)
        player.draw_pile = ["mass_healing_word"]
        initial_hand_len = len(player.hand)
        engine._damage_target(run, "p0", 2, damage_type="true", source="test")
        self.assertEqual(len(player.hand), initial_hand_len + 1)
        self.assertIn("mass_healing_word", player.hand)
        card_erosion = ALL_CARDS["abyss_erosion"]
        card_erosion.execute(run, "e1", engine)
        self.assertEqual(enemies[0].hp, 585)
        weakness_buff = next(b for b in enemies[0].buffs if b.id == "void_weakness")
        self.assertEqual(weakness_buff.stacks, 3)
        player.minions["1"] = MinionState("mercenary", "雇佣兵", 5, 5, 4, 1, 0)
        card_tempest = ALL_CARDS["glacier_tempest"]
        card_tempest.execute(run, None, engine)
        self.assertEqual(enemies[0].hp, 573)
        self.assertEqual(player.shield, 16)
        card_altar_up = ALL_CARDS["abyss_altar+"]
        card_altar_up.execute(run, None, engine)
        self.assertIn("2", player.amulets)
        self.assertEqual(player.amulets["2"].id, "abyss_altar_awaken")
        card_altar = ALL_CARDS["abyss_altar"]
        card_altar.execute(run, None, engine)
        self.assertIn("3", player.amulets)
        self.assertEqual(player.amulets["3"].id, "abyss_altar")
        engine.card_player.end_turn(run)
        self.assertEqual(player.amulets["3"].id, "abyss_altar_awaken")
        engine.card_player.end_turn(run)
        self.assertEqual(player.amulets["3"].id, "abyss_altar_converge")
        engine.card_player.end_turn(run)
        self.assertEqual(player.amulets["3"].id, "abyss_altar_burst")
        engine.card_player.end_turn(run)
        self.assertEqual(player.amulets["3"].id, "abyss_altar_end")
        prev_player_hp = player.hp
        engine.card_player.end_turn(run)
        self.assertNotIn("3", player.amulets)
        self.assertEqual(player.hp, prev_player_hp - 10)

    def test_gatekey_and_ancient_mechanics(self):
        class DummySaveManager:
            def __init__(self):
                self.stats = UserStats()
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return self.stats
            def save_stats(self, user_id, stats):
                self.stats = stats
                return True
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=40,
            max_hp=40,
            shield=0,
            gold=100,
            stage=32,
            deck=["arcane_torrent", "arcane_barrier"],
            hand=["arcane_torrent", "arcane_barrier"],
            actions=3,
            bonus_actions=2,
            minion_graveyard=["mercenary"]
        )
        run = GameRun(
            user_id="test_ancient_user",
            node_type="battle",
            player=player,
            enemies=[EnemyState("虚空之门·尤格-索托斯", 5, 5, 0, max_actions=0)]
        )
        engine.combat_resolver.damage_target(run, "e1", 10, damage_type="bludgeoning")
        self.assertEqual(run.enemies[0].name, "虚空之门·尤格-索托斯")
        self.assertEqual(run.enemies[0].hp, 1)
        engine._enemy_turn(run)
        self.assertEqual(run.enemies[0].name, "【觉醒】虚空之门·尤格-索托斯")
        self.assertEqual(run.enemies[0].hp, 260)
        self.assertTrue(any(b.id == "end_gate_passive" for b in run.enemies[0].buffs))
        msg = engine.combat_resolver.recall_dead_minion(run, 15)
        self.assertIn("召回", msg)
        self.assertEqual(len(player.minion_graveyard), 0)
        self.assertEqual(player.minions["1"].id, "mercenary")
        res = engine.play_card(run, 1, "e1")
        self.assertEqual(player.actions, 0, f"Actions not zero! Result: {res}")
        self.assertEqual(run.node_data.get("last_x_cost_a"), 3)
        player.actions = 3
        player.bonus_actions = 2
        player.relics.append("chemical_x")
        res2 = engine.play_card(run, 1, "e1")
        self.assertEqual(player.bonus_actions, 0, f"Bonus actions not zero! Result: {res2}")
        self.assertEqual(run.node_data.get("last_x_cost_ba"), 4)
        self.assertEqual(player.actions, 3)
        player.relics = ["ancient_compass"]
        run.node_data = {"ghost_name": "测试假人", "ghost_max_hp": 10}
        engine._init_battle_node(run, "ghost")
        self.assertEqual(run.enemies[0].actions, 0)
        run.node_type = "battle"
        player.stage = 25
        sm.stats.unlocked_gatekey = False
        engine.card_player.handle_battle_win(run)
        self.assertEqual(run.node_type, "victory")
        run.node_type = "battle"
        player.stage = 25
        sm.stats.unlocked_gatekey = True
        engine.card_player.handle_battle_win(run)
        self.assertEqual(run.node_type, "boss_chest")
        player.hand = ["void_beacon"]
        player.actions = 2
        player.bonus_actions = 1
        player.amulets = {}
        enemy_test2 = EnemyState("测试敌人", 10, 10, 0, actions=2, max_actions=2)
        run.enemies = [enemy_test2]
        run.node_type = "battle"
        engine.play_card(run, 1, None)
        self.assertIn("1", player.amulets)
        self.assertEqual(player.amulets["1"].id, "void_beacon")
        engine.end_turn(run)
        self.assertTrue(any(b.id == "vulnerable_force" for b in enemy_test2.buffs))
        run.node_type = "battle"
        player.stage = 32
        engine.card_player.handle_battle_win(run)
        self.assertEqual(run.node_type, "victory")
        self.assertTrue(sm.stats.yog_sothoth_kill_count > 0)

    def test_amulet_exhaust_and_graveyard(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def load_stats(self, user_id):
                class DummyStats:
                    def __init__(self):
                        self.unlocked_gatekey = False
                        self.killed_icerainboww = False
                        self.killed_yog_sothoth = False
                return DummyStats()
            def save_stats(self, user_id, stats):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=40,
            max_hp=40,
            shield=20,
            gold=100,
            stage=1,
            deck=["lucky_coin", "thorns_necklace"],
            hand=["lucky_coin", "thorns_necklace"],
            actions=5,
            bonus_actions=5,
            buffs=[],
            relics=[]
        )
        enemies = [
            EnemyState("测试敌人A", 50, 50, 0)
        ]
        run = GameRun(
            user_id="test_amulet_user",
            node_type="battle",
            player=player,
            enemies=enemies
        )
        engine.card_player.play_card(run, 1)
        self.assertIn("1", player.amulets)
        self.assertEqual(player.amulets["1"].id, "lucky_coin")
        self.assertNotIn("lucky_coin", player.discard_pile)
        self.assertNotIn("lucky_coin", player.exhaust_pile)
        engine.card_player.end_turn(run)
        self.assertEqual(player.amulets["1"].countdown, 2)
        engine.card_player.end_turn(run)
        self.assertEqual(player.amulets["1"].countdown, 1)
        prev_gold = player.gold
        engine.card_player.end_turn(run)
        self.assertNotIn("1", player.amulets)
        self.assertIn("lucky_coin", player.minion_graveyard)
        self.assertNotIn("lucky_coin", player.discard_pile)
        self.assertEqual(player.gold, prev_gold + 13)
        res = engine.combat_resolver.recall_dead_minion(run, 999)
        self.assertIn("没有符合条件的随从", res)
        player.hand = ["master_key"]
        player.actions = 2
        player.bonus_actions = 1
        card_thorns = ALL_CARDS["thorns_necklace"]
        card_thorns.execute(run, None, engine)
        engine.card_player._handle_card_post_play(run, card_thorns, "thorns_necklace")
        self.assertIn("1", player.amulets)
        self.assertEqual(player.amulets["1"].id, "thorns_necklace")
        self.assertNotIn("thorns_necklace", player.discard_pile)
        engine.card_player.play_card(run, 1)
        self.assertNotIn("1", player.amulets)
        self.assertIn("thorns_necklace", player.minion_graveyard)

    def test_max_hp_event_debuffs_and_time_sand_blessing(self):
        from game.entities.events.chaos_events import BurnVoidBooksOption, SellFleshOption, DrinkTimeSandOption, RepairEngineOption
        from game.entities.events.lost_maze import FishPoolOption
        from game.entities.events.void_contract import ContractLegendOption
        from game.entities.events.portal_chamber import ContractPortalOption
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine
        user_id = "test_max_hp"
        plugin.save_manager.delete_save(user_id)
        player = PlayerState(hp=40, max_hp=40, shield=0, gold=100, stage=1)
        run = GameRun(user_id=user_id, node_type="event", player=player, enemies=[])
        BurnVoidBooksOption()._run_effect(run, engine)
        self.assertEqual(player.max_hp, 33)
        player.max_hp = 40
        player.hp = 40
        SellFleshOption()._run_effect(run, engine)
        self.assertEqual(player.max_hp, 35)
        player.max_hp = 40
        player.hp = 40
        player.relics = []
        DrinkTimeSandOption()._run_effect(run, engine)
        self.assertEqual(player.max_hp, 30)
        self.assertEqual(player.hp, 30)
        self.assertIn("time_sand_blessing", player.relics)
        player.max_hp = 40
        player.hp = 40
        RepairEngineOption()._run_effect(run, engine)
        self.assertEqual(player.max_hp, 35)
        player.max_hp = 40
        player.hp = 40
        while True:
            player.max_hp = 40
            player.hp = 40
            res = FishPoolOption()._run_effect(run, engine)
            if "最大生命上限减少了" in res:
                break
        self.assertEqual(player.max_hp, 38)
        player.max_hp = 40
        player.hp = 40
        ContractLegendOption()._run_effect(run, engine)
        self.assertEqual(player.max_hp, 37)
        player.max_hp = 40
        player.hp = 40
        ContractPortalOption()._run_effect(run, engine)
        self.assertEqual(player.max_hp, 38)
        player.relics = ["time_sand_blessing"]
        player.bonus_actions = 1
        from game.models.events import TurnStartEvent
        evt = TurnStartEvent(run, is_player=True)
        engine.battle_engine.event_bus.dispatch(evt)
        self.assertEqual(player.bonus_actions, 3)
        plugin.save_manager.delete_save(user_id)

    def test_redesigned_reward_flows(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_redesigned_rewards"
        plugin.save_manager.delete_save(user_id)
        
        async def go():
            player = PlayerState(
                hp=30, max_hp=30, shield=0, gold=10, stage=4,
                deck=["first_aid"], hand=[], draw_pile=[], discard_pile=[], exhaust_pile=[], graveyard=[]
            )
            run = GameRun(
                user_id=user_id, node_type="reward", player=player, enemies=[]
            )
            plugin.save_manager.save_save(user_id, run)
            
            items = [
                {"type": "gold", "amount": 50, "taken": False, "bind_group": "pack1", "force": True},
                {"type": "relic", "relic_id": "lucky_coin", "taken": False, "bind_group": "pack1"},
                {"type": "card_reward", "cards": ["fireball"], "taken": False, "group_id": "select1"},
                {"type": "card_reward", "cards": ["magic_shield"], "taken": False, "group_id": "select1"}
            ]
            run.node_data = {"items": items}
            plugin.save_manager.save_save(user_id, run)
            
            res_exit = await run_command(plugin, ".rogue 选择 exit", sender_id=user_id)
            self.assertIn("你必须先拿取强制奖励", res_exit)
            
            res_take1 = await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            self.assertIn("金币", res_take1)
            
            run_after = plugin.save_manager.load_save(user_id)
            self.assertIn("lucky_coin", run_after.player.relics)
            self.assertEqual(run_after.player.gold, 60)
            self.assertTrue(run_after.node_data["items"][0]["taken"])
            self.assertTrue(run_after.node_data["items"][1]["taken"])
            
            res_take_card = await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            run_after = plugin.save_manager.load_save(user_id)
            self.assertEqual(run_after.node_type, "card_select")
            self.assertTrue(run_after.node_data["next_node_data"]["items"][2]["taken"])
            self.assertTrue(run_after.node_data["next_node_data"]["items"][3]["taken"])
            
            res_skip = await run_command(plugin, ".rogue 选择 2", sender_id=user_id)
            run_after = plugin.save_manager.load_save(user_id)
            self.assertEqual(run_after.player.stage, 5)
            
            run_after.stage = 4
            run_after.player.stage = 4
            run_after.player.relics = ["trash_mountain"]
            run_after.node_type = "reward"
            run_after.node_data = {
                "items": [
                    {"type": "card_reward", "cards": ["fireball"], "taken": False, "force": True}
                ]
            }
            plugin.save_manager.save_save(user_id, run_after)
            
            card_select_res = await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            run_after = plugin.save_manager.load_save(user_id)
            self.assertEqual(run_after.node_type, "card_select")
            self.assertIn("造成 24 点", card_select_res)
            self.assertNotIn("造成 18 点", card_select_res)
            
            res_skip_err = await run_command(plugin, ".rogue 选择 2", sender_id=user_id)
            self.assertIn("由于遗物【垃圾山】的效果，你无法跳过", res_skip_err)
            
            await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            run_after = plugin.save_manager.load_save(user_id)
            self.assertEqual(run_after.player.stage, 5)
            from game.models.state import ensure_card_state
            last_card = ensure_card_state(run_after.player.deck[-1])
            self.assertEqual(last_card.id, "fireball")
            run_after = plugin.save_manager.load_save(user_id)
            run_after.node_type = "map_select"
            run_after.node_data = {
                "options": [
                    {"node_id": "node_rest", "node_type": "rest", "desc": "篝火营地"}
                ]
            }
            run_after.map_data = {
                "nodes": {
                    "5": [
                        {"id": "node_rest", "type": "rest", "stage": 5, "desc": "篝火营地", "connections": []}
                    ]
                },
                "current_node_id": None
            }
            plugin.save_manager.save_save(user_id, run_after)
            
            res_rest_enter = await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            self.assertIn("🍖 休息", res_rest_enter)
            self.assertIn("🔮 冥想", res_rest_enter)
            self.assertIn("🔨 强化", res_rest_enter)
            
        asyncio.run(go())

    def test_rest_node_bare_exit_and_cancel(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_rest_bare_exit"
        plugin.save_manager.delete_save(user_id)

        async def go():
            def setup_rest_node():
                player = PlayerState(
                    hp=60, max_hp=80, shield=0, gold=10, stage=9,
                    deck=["first_aid", "fireball"], hand=[], draw_pile=[], discard_pile=[], exhaust_pile=[], graveyard=[]
                )
                run = GameRun(user_id=user_id, node_type="map_select", player=player, enemies=[])
                run.node_data = {"options": [{"node_id": "node_rest", "node_type": "rest", "desc": "篝火营地 (恢复生命值或冥想领悟卡牌)"}]}
                run.map_data = {
                    "nodes": {"9": [{"id": "node_rest", "type": "rest", "next": []}]},
                    "current_node_id": None
                }
                plugin.save_manager.save_save(user_id, run)

            stats = plugin.save_manager.load_stats(user_id)
            stats.rogue_mode = True
            plugin.save_manager.save_stats(user_id, stats)

            for alias in ("exit", "离开", "退出", "quit"):
                setup_rest_node()
                enter_res = await run_command(plugin, "1", sender_id=user_id)
                self.assertIn("篝火营地", enter_res)
                exit_res = await run_command(plugin, alias, sender_id=user_id)
                self.assertNotEqual(exit_res, "")
                self.assertIn("你离开了当前节点", exit_res)
                run_after = plugin.save_manager.load_save(user_id)
                self.assertEqual(run_after.node_type, "map_select")

            setup_rest_node()
            await run_command(plugin, "1", sender_id=user_id)
            upgrade_res = await run_command(plugin, "3", sender_id=user_id)
            self.assertIn("卡牌升级强化已启动", upgrade_res)
            cancel_res = await run_command(plugin, "取消", sender_id=user_id)
            self.assertIn("已取消卡牌升级操作", cancel_res)
            run_after = plugin.save_manager.load_save(user_id)
            self.assertFalse(run_after.node_data.get("pending_upgrade"))
            self.assertEqual(run_after.node_type, "rest")
            self.assertIn("🍖 休息", cancel_res)
            self.assertIn("🔨 强化", cancel_res)

        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)
