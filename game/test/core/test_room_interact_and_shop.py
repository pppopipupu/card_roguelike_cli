import asyncio
import os
import random
import tempfile
import unittest
from game.core.world.grid_map_generator import coord_to_xy, xy_to_coord
from game.test.core.base import CorePlugin, move_to_room, run_command


class TestRoomInteractAndShop(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(2026)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, cmd, uid))

    def _start_grid(self, uid: str):
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        return self.plugin.save_manager.load_save(uid)

    def test_obstacle_two_step_confirmation_and_cancel(self):
        uid = "obs_two_step_user"
        run = self._start_grid(uid)
        fm = run.floor_map
        sx, sy = coord_to_xy(fm.player_coords[uid])
        obs_dir = None
        other_dir = None
        for d, (dx, dy) in (("w", (0, -1)), ("s", (0, 1)), ("a", (-1, 0)), ("d", (1, 0))):
            nx, ny = sx + dx, sy + dy
            if 0 <= nx < fm.width and 0 <= ny < fm.height:
                nc = xy_to_coord(nx, ny)
                r = fm.rooms.get(nc)
                if r and r.room_type == "obstacle" and obs_dir is None:
                    obs_dir = d
                elif r and r.room_type != "wall" and other_dir is None:
                    other_dir = d
        if obs_dir is None:
            for d, (dx, dy) in (("w", (0, -1)), ("s", (0, 1)), ("a", (-1, 0)), ("d", (1, 0))):
                nx, ny = sx + dx, sy + dy
                if 0 <= nx < fm.width and 0 <= ny < fm.height:
                    nc = xy_to_coord(nx, ny)
                    if fm.rooms[nc].room_type != "wall":
                        fm.rooms[nc].room_type = "obstacle"
                        fm.rooms[nc].obstacle_sp = 2
                        fm.rooms[nc].obstacle_style = "collapsed_boulders"
                        obs_dir = d
                        break
            self.plugin.save_manager.save_save(uid, run)
        step1 = self.run_cmd(obs_dir, uid)
        self.assertIn("1/2", step1)
        self.assertIn("坍塌巨石堆", step1)
        step2 = self.run_cmd(obs_dir, uid)
        self.assertIn("2/2", step2)
        step3 = self.run_cmd(obs_dir, uid)
        self.assertIn("破除", step3)
        run_after = self.plugin.save_manager.load_save(uid)
        self.assertLess(run_after.player.sp, run_after.player.max_sp)

    def test_fold_guide_touch_take_bag_use_and_drop(self):
        uid = "bag_touch_user"
        run = self._start_grid(uid)
        map_out = self.run_cmd("map", uid)
        self.assertIn("对话", map_out)
        self.assertIn("触摸", map_out)
        folded = self.run_cmd("f", uid)
        self.assertIn("已折叠", folded)
        unfolded = self.run_cmd("f", uid)
        self.assertIn("w/a/s/d", unfolded)

        fm = run.floor_map
        cur_coord = fm.player_coords[uid]
        room = fm.rooms[cur_coord]
        prop_id = room.props[0]
        touch_res = self.run_cmd(f"触摸 {prop_id}", uid)
        self.assertNotIn("[FAIL]", touch_res)
        touch_again = self.run_cmd(f"触摸 {prop_id}", uid)
        self.assertIn("没有什么新发现", touch_again)

        room.items.extend(["espresso_beans", "rusty_pickaxe", "smuggler_token", "potion:healing_potion"])
        self.plugin.save_manager.save_save(uid, run)

        self.assertIn("浓缩咖啡豆", self.run_cmd("拿取 浓缩咖啡豆", uid))
        self.assertIn("药水", self.run_cmd("拿取 治疗药水", uid))
        self.assertIn("锈蚀矿镐", self.run_cmd("拿取 锈蚀矿镐", uid))
        self.assertIn("走私者徽记", self.run_cmd("拿取 走私者徽记", uid))

        drop_out = self.run_cmd("丢弃物品 走私者徽记", uid)
        self.assertIn("丢弃", drop_out)

        use_out = self.run_cmd("使用 浓缩咖啡豆", uid)
        self.assertIn("SP", use_out)
        run_after = self.plugin.save_manager.load_save(uid)
        self.assertNotIn("espresso_beans", run_after.player.bag_items)

    def _win_current_battle(self, uid: str):
        for _ in range(120):
            r = self.plugin.save_manager.load_save(uid)
            if not r or r.node_type != "battle":
                return r
            played = False
            for idx, _ in enumerate(r.player.hand, 1):
                res = self.run_cmd(f"p {idx} 1", uid)
                if "[FAIL]" not in res and "❌" not in res:
                    played = True
                    break
            if not played:
                self.run_cmd("e", uid)
        return self.plugin.save_manager.load_save(uid)

    def test_room_npc_dialog_and_attack_combat(self):
        uid = "npc_dialog_atk_user"
        run = self._start_grid(uid)
        fm = run.floor_map
        cur_coord = fm.player_coords[uid]
        room = fm.rooms[cur_coord]
        room.npcs = ["wandering_smith", "lost_scholar"]
        room.defeated_npcs = []
        self.plugin.save_manager.save_save(uid, run)

        talk_out = self.run_cmd("对话 托林", uid)
        self.assertIn("托林", talk_out)
        run_dlg = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run_dlg.node_type, "room_dialog")
        leave_out = self.run_cmd("离开", uid)
        self.assertIn("告别", leave_out)
        self.assertEqual(self.plugin.save_manager.load_save(uid).node_type, "grid_map")

        atk_out = self.run_cmd("攻击 艾拉", uid)
        self.assertIn("发起攻击", atk_out)
        run_bat = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run_bat.node_type, "battle")
        run_end = self._win_current_battle(uid)
        if run_end.node_type == "reward":
            self.run_cmd("离开", uid)
            run_end = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run_end.node_type, "grid_map")
        self.assertIn("lost_scholar", run_end.floor_map.rooms[cur_coord].defeated_npcs)
        self.assertIn("[FAIL]", self.run_cmd("攻击 艾拉", uid))

    def test_shop_lobby_dialog_wares_and_merchant_attack(self):
        uid = "shop_interact_user"
        self.run_cmd("class warrior", uid)
        self._start_grid(uid)
        _, run = move_to_room(self.plugin, uid, ("shop",))
        if run.node_type != "shop":
            fm = run.floor_map
            shop_coord = next(c for c, r in fm.rooms.items() if r.room_type == "shop")
            fm.revealed_coords.append(shop_coord)
            self.plugin.save_manager.save_save(uid, run)
            self.run_cmd(f"tp {shop_coord}", uid)
            run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "shop")
        self.assertEqual(run.node_data.get("shop_mode"), "lobby")
        lobby_view = self.run_cmd("i", uid)
        self.assertIsInstance(lobby_view, str)

        dlg_out = self.run_cmd("对话 维克多", uid)
        self.assertIn("讨价还价", dlg_out)
        self.assertEqual(self.plugin.save_manager.load_save(uid).node_data.get("shop_mode"), "dialog")

        wares_out = self.run_cmd("c 1", uid)
        self.assertEqual(self.plugin.save_manager.load_save(uid).node_data.get("shop_mode"), "wares")
        self.assertIn("商店", wares_out)
        back_lobby = self.run_cmd("离开", uid)
        self.assertEqual(self.plugin.save_manager.load_save(uid).node_data.get("shop_mode"), "lobby")
        self.assertIn("行商", back_lobby)


        atk_res = self.run_cmd("攻击 维克多", uid)
        self.assertIn("维克多", atk_res)
        run_bat = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run_bat.node_type, "battle")
        run_post = self._win_current_battle(uid)
        if run_post.node_type == "reward":
            self.run_cmd("离开", uid)
            run_post = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run_post.node_type, "grid_map")
        cur_c = run_post.floor_map.player_coords[uid]
        self.assertTrue(run_post.floor_map.rooms[cur_c].shared_payload.get("merchant_defeated"))

    def test_cafe_barista_props_and_attack(self):
        uid = "cafe_barista_user"
        self._start_grid(uid)
        _, run = move_to_room(self.plugin, uid, ("cafe",))
        if run.node_type != "cafe":
            fm = run.floor_map
            cafe_coord = next(c for c, r in fm.rooms.items() if r.room_type == "cafe")
            fm.revealed_coords.append(cafe_coord)
            self.plugin.save_manager.save_save(uid, run)
            self.run_cmd(f"tp {cafe_coord}", uid)
            run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "cafe")
        look_out = self.run_cmd("look", uid)
        self.assertIn("布鲁诺", look_out)
        self.assertIn("咖啡机", look_out)
        self.assertIn("展开", self.run_cmd("f", uid))
        self.assertIn("对话", self.run_cmd("f", uid))

        touch_out = self.run_cmd("触摸 咖啡机", uid)
        self.assertIn("SP", touch_out)

        talk_barista = self.run_cmd("对话 店长", uid)
        self.assertIn("布鲁诺", talk_barista)
        mac_out = self.run_cmd("c 3", uid)
        self.assertIn("25 金币", mac_out)
        drink_out = self.run_cmd("c 1", uid)
        self.assertIn("浓缩咖啡", drink_out)

        self.run_cmd("c 7", uid)
        atk_barista = self.run_cmd("攻击 店长", uid)
        self.assertIn("布鲁诺", atk_barista)
        self.assertEqual(self.plugin.save_manager.load_save(uid).node_type, "battle")

    def test_combat_room_entry_shows_environment_intro(self):
        uid = "combat_env_intro_user"
        self._start_grid(uid)
        res, run = move_to_room(self.plugin, uid, ("battle", "elite"))
        self.assertEqual(run.node_type, "battle")
        self.assertIn("你踏入了", res)
        self.assertIn("可交互物件", res)
