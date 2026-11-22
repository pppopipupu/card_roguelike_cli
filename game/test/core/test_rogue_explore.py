import unittest
import asyncio
from game.test.core.base import *
from game.models.state import CardState, UserStats

class TestRogueExplore(unittest.TestCase):
    def test_inner_shop_flow(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_inner_shop_user"
        plugin.save_manager.delete_save(user_id)
        
        async def go():
            await run_command(plugin, ".rogue 开启", sender_id=user_id)
            await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            run = load_run(plugin, user_id)
            self.assertIsNotNone(run)
            from game.core.party.session import SessionContextScoper
            shop_coord = next((c for c, r in floor_of(run).rooms.items() if r.room_type == "shop"), "A1")
            SessionContextScoper.create_session(run, shop_coord, "shop", [user_id])
            run.node_type = "shop"
            plugin.engine.map_engine.explore_engine._init_shop_node(run)
            plugin.save_manager.save_save(user_id, run)
            
            status_output = await run_command(plugin, ".rogue 状态", sender_id=user_id)
            self.assertIn("奇妙商店", status_output)
            self.assertIn("净化服务", status_output)
            self.assertIn("离开商店", status_output)
            
            run = load_run(plugin, user_id)
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
            
            run = load_run(plugin, user_id)
            self.assertEqual(len(run.player.deck), initial_deck_len + 1)
            self.assertLess(run.player.gold, initial_gold)
            
            relic_idx = -1
            for idx, item in enumerate(items):
                if item.get("type") == "relic":
                    relic_idx = idx + 1
                    break
            if relic_idx != -1:
                run = load_run(plugin, user_id)
                run.player.gold = 500
                plugin.save_manager.save_save(user_id, run)
                buy_relic_res = await run_command(plugin, f".rogue 选择 {relic_idx}", sender_id=user_id)
                self.assertIn("购买成功", buy_relic_res)
                run = load_run(plugin, user_id)
                relic_id = items[relic_idx - 1].get("relic_id")
                self.assertIn(relic_id, run.player.relics)
                
            remove_idx = -1
            for idx, item in enumerate(items):
                if item.get("type") == "remove":
                    remove_idx = idx + 1
                    break
            if remove_idx != -1:
                run = load_run(plugin, user_id)
                run.player.gold = 500
                from game.core.party.session import SessionContextScoper
                SessionContextScoper.create_session(run, "A1", "shop", [user_id])
                plugin.engine.map_engine.explore_engine._init_shop_node(run)
                for it in run.node_data["items"]:
                    if it.get("type") == "remove":
                        it["sold"] = False
                plugin.save_manager.save_save(user_id, run)
                remove_trigger_res = await run_command(plugin, f".rogue 选择 {remove_idx}", sender_id=user_id)
                self.assertIn("净化服务已启动", remove_trigger_res)
                run = load_run(plugin, user_id)
                self.assertTrue(run.node_data.get("pending_remove"))
                cancel_res = await run_command(plugin, ".rogue 选择 取消", sender_id=user_id)
                self.assertIn("已取消卡牌移除操作", cancel_res)
                run = load_run(plugin, user_id)
                self.assertFalse(run.node_data.get("pending_remove"))
                await run_command(plugin, f".rogue 选择 {remove_idx}", sender_id=user_id)
                run = load_run(plugin, user_id)
                deck_before = len(run.player.deck)
                remove_card_res = await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
                self.assertIn("已成功从你的卡组中移除", remove_card_res)
                run = load_run(plugin, user_id)
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
            run = load_run(plugin, user_id)
            self.assertNotEqual(run.node_type, "shop")
            
        asyncio.run(go())


    def test_card_upgrade_and_forge(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        save_manager.delete_save("test_user_upg")
        
        async def go():
            await run_command(plugin, ".rogue 开启 确认", sender_id="test_user_upg")
            await run_command(plugin, ".rogue 选择 1", sender_id="test_user_upg")
            run = require_run(save_manager.load_save("test_user_upg"))
            rest_coord = next((c for c, r in floor_of(run).rooms.items() if r.room_type == "rest"), "A1")
            from game.core.party.session import SessionContextScoper
            SessionContextScoper.create_session(run, rest_coord, "rest", ["test_user_upg"])
            plugin.engine.map_engine.explore_engine._init_rest_node(run)
            save_manager.save_save("test_user_upg", run)
            self.assertEqual(run.node_type, "rest")
            res = await run_command(plugin, ".rogue 选择 3", sender_id="test_user_upg")
            self.assertIn("卡牌升级强化已启动", res)
            run = require_run(save_manager.load_save("test_user_upg"))
            self.assertTrue(run.node_data.get("pending_upgrade"))
            res_upg = await run_command(plugin, ".rogue 选择 1", sender_id="test_user_upg")
            self.assertIn("升级成功", res_upg)
            run = require_run(save_manager.load_save("test_user_upg"))
            self.assertTrue(any(card.upgraded for card in run.player.deck))
            from game.core.party.session import SessionContextScoper
            forge_data = {
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
            SessionContextScoper.create_session(run, "A1", "event", ["test_user_upg"], node_data=dict(forge_data))
            save_manager.save_save("test_user_upg", run)
            res_event_fire = await run_command(plugin, ".rogue 选择 1", sender_id="test_user_upg")
            self.assertIn("卡牌升级强化已启动", res_event_fire)
            run = require_run(save_manager.load_save("test_user_upg"))
            SessionContextScoper.create_session(run, "A1", "event", ["test_user_upg"], node_data=dict(forge_data))
            save_manager.save_save("test_user_upg", run)
            res_backfire = await run_command(plugin, ".rogue 选择 3", sender_id="test_user_upg")
            self.assertIn("炉温反噬", res_backfire)
            run = require_run(save_manager.load_save("test_user_upg"))
            self.assertTrue(any(b.id == "forge_backfire" for b in run.player.buffs))
            save_manager.delete_save("test_user_upg")
            
        asyncio.run(go())

    def test_redesigned_reward_flows(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_redesigned_rewards"
        plugin.save_manager.delete_save(user_id)
        
        async def go():
            player = PlayerState(
                hp=30, max_hp=30, shield=0, gold=10, stage=4,
                deck=[CardState(id="first_aid")], hand=[], draw_pile=[], discard_pile=[], exhaust_pile=[], graveyard=[]
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
            
            run_after = load_run(plugin, user_id)
            self.assertIn("lucky_coin", run_after.player.relics)
            self.assertEqual(run_after.player.gold, 60)
            self.assertTrue(run_after.node_data["items"][0]["taken"])
            self.assertTrue(run_after.node_data["items"][1]["taken"])
            
            res_take_card = await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            run_after = load_run(plugin, user_id)
            self.assertEqual(run_after.node_type, "card_select")
            self.assertTrue(run_after.node_data["next_node_data"]["items"][2]["taken"])
            self.assertTrue(run_after.node_data["next_node_data"]["items"][3]["taken"])
            
            res_skip = await run_command(plugin, ".rogue 选择 2", sender_id=user_id)
            run_after = load_run(plugin, user_id)
            self.assertEqual(run_after.player.stage, 5)
            
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
            run_after = load_run(plugin, user_id)
            self.assertEqual(run_after.node_type, "card_select")
            self.assertIn("造成 24 点", card_select_res)
            self.assertNotIn("造成 18 点", card_select_res)
            
            res_skip_err = await run_command(plugin, ".rogue 选择 2", sender_id=user_id)
            self.assertIn("由于遗物【垃圾山】的效果，你无法跳过", res_skip_err)
            
            await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
            run_after = load_run(plugin, user_id)
            self.assertEqual(run_after.player.stage, 5)
            from game.models.state import ensure_card_state
            last_card = ensure_card_state(run_after.player.deck[-1])
            self.assertEqual(last_card.id, "fireball")
            run_after = load_run(plugin, user_id)
            run_after.node_type = "rest"
            plugin.engine.map_engine.explore_engine._init_rest_node(run_after)
            plugin.save_manager.save_save(user_id, run_after)

            res_rest_enter = await run_command(plugin, ".rogue 状态", sender_id=user_id)
            self.assertIn("🍖 休息", res_rest_enter)
            self.assertIn("🔮 冥想", res_rest_enter)
            self.assertIn("🔨 强化", res_rest_enter)
            
        asyncio.run(go())

    def test_rest_node_bare_exit_and_cancel(self):
        plugin = MyPlugin(DummyContext())
        user_id = "test_rest_bare_exit"
        plugin.save_manager.delete_save(user_id)

        async def go():
            async def setup_rest_node():
                plugin.save_manager.delete_save(user_id)
                await run_command(plugin, ".rogue 开启", sender_id=user_id)
                await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
                run = load_run(plugin, user_id)
                from game.core.party.session import SessionContextScoper
                rest_coord = next((c for c, r in floor_of(run).rooms.items() if r.room_type == "rest"), "A1")
                SessionContextScoper.create_session(run, rest_coord, "rest", [user_id])
                plugin.engine.map_engine.explore_engine._init_rest_node(run)
                plugin.save_manager.save_save(user_id, run)
                return await run_command(plugin, "r", sender_id=user_id)

            stats = plugin.save_manager.load_stats(user_id)
            stats.rogue_mode = True
            plugin.save_manager.save_stats(user_id, stats)

            for alias in ("exit", "离开", "退出", "quit"):
                enter_res = await setup_rest_node()
                self.assertIn("篝火营地", enter_res)
                exit_res = await run_command(plugin, alias, sender_id=user_id)
                self.assertNotEqual(exit_res, "")
                self.assertIn("你离开了当前节点", exit_res)
                run_after = load_run(plugin, user_id)
                self.assertEqual(run_after.node_type, "grid_map")

            await setup_rest_node()
            upgrade_res = await run_command(plugin, "3", sender_id=user_id)
            self.assertIn("卡牌升级强化已启动", upgrade_res)
            cancel_res = await run_command(plugin, "取消", sender_id=user_id)
            self.assertIn("已取消卡牌升级操作", cancel_res)
            run_after = load_run(plugin, user_id)
            self.assertFalse(run_after.node_data.get("pending_upgrade"))
            self.assertEqual(run_after.node_type, "rest")
            self.assertIn("🍖 休息", cancel_res)
            self.assertIn("🔨 强化", cancel_res)

        asyncio.run(go())
        plugin.save_manager.delete_save(user_id)
