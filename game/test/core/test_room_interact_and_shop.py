import asyncio
import os
import random
import tempfile
import unittest
from game.core.world.grid_map_generator import coord_to_xy, xy_to_coord
from game.test.core.base import CorePlugin, floor_of, load_run, move_to_room, require_run, run_command


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
        return load_run(self.plugin, uid)

    def test_obstacle_two_step_confirmation_and_cancel(self):
        uid = "obs_two_step_user"
        run = self._start_grid(uid)
        fm = floor_of(run)
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
        assert obs_dir is not None, "obstacle direction must exist"
        step1 = self.run_cmd(obs_dir, uid)
        self.assertIn("1/2", step1)
        self.assertIn("坍塌巨石堆", step1)
        step2 = self.run_cmd(obs_dir, uid)
        self.assertIn("2/2", step2)
        step3 = self.run_cmd(obs_dir, uid)
        self.assertIn("破除", step3)
        run_after = load_run(self.plugin, uid)
        self.assertLess(run_after.player.sp, run_after.player.max_sp)

    def test_fold_guide_touch_take_bag_use_and_drop(self):
        uid = "bag_touch_user"
        run = self._start_grid(uid)
        map_out = self.run_cmd("map", uid)
        self.assertIn("talk", map_out)
        self.assertIn("touch", map_out)
        folded = self.run_cmd("f", uid)
        self.assertIn("已折叠", folded)
        unfolded = self.run_cmd("f", uid)
        self.assertIn("w/a/s/d", unfolded)

        fm = floor_of(run)
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
        run_after = load_run(self.plugin, uid)
        self.assertNotIn("espresso_beans", run_after.player.bag_items)

    def _win_current_battle(self, uid: str):
        for _ in range(320):
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
        fm = floor_of(run)
        cur_coord = fm.player_coords[uid]
        room = fm.rooms[cur_coord]
        room.npcs = ["wandering_smith", "lost_scholar"]
        room.defeated_npcs = []
        self.plugin.save_manager.save_save(uid, run)

        talk_out = self.run_cmd("对话 托林", uid)
        self.assertIn("托林", talk_out)
        run_dlg = load_run(self.plugin, uid)
        self.assertEqual(run_dlg.node_type, "room_dialog")
        leave_out = self.run_cmd("离开", uid)
        self.assertIn("告别", leave_out)
        self.assertEqual(load_run(self.plugin, uid).node_type, "grid_map")

        atk_out = self.run_cmd("攻击 艾拉", uid)
        self.assertIn("发起攻击", atk_out)
        run_bat = load_run(self.plugin, uid)
        self.assertEqual(run_bat.node_type, "battle")
        run_end = require_run(self._win_current_battle(uid))
        if run_end.node_type == "reward":
            self.run_cmd("离开", uid)
            run_end = load_run(self.plugin, uid)
        self.assertEqual(run_end.node_type, "grid_map")
        self.assertIn("lost_scholar", floor_of(run_end).rooms[cur_coord].defeated_npcs)
        self.assertIn("[FAIL]", self.run_cmd("攻击 艾拉", uid))

    def test_shop_lobby_dialog_wares_and_merchant_attack(self):
        uid = "shop_interact_user"
        self.run_cmd("class warrior", uid)
        self._start_grid(uid)
        _, run = move_to_room(self.plugin, uid, ("shop",))
        if run.node_type != "shop":
            fm = floor_of(run)
            shop_coord = next(c for c, r in fm.rooms.items() if r.room_type == "shop")
            fm.revealed_coords.append(shop_coord)
            self.plugin.save_manager.save_save(uid, run)
            self.run_cmd(f"tp {shop_coord}", uid)
            run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "shop")
        self.assertEqual(run.node_data.get("shop_mode"), "lobby")
        lobby_view = self.run_cmd("i", uid)
        self.assertIsInstance(lobby_view, str)

        dlg_out = self.run_cmd("对话 维克多", uid)
        self.assertIn("讨价还价", dlg_out)
        self.assertEqual(load_run(self.plugin, uid).node_data.get("shop_mode"), "dialog")

        wares_out = self.run_cmd("c 1", uid)
        self.assertEqual(load_run(self.plugin, uid).node_data.get("shop_mode"), "wares")
        self.assertIn("商店", wares_out)
        back_lobby = self.run_cmd("离开", uid)
        self.assertEqual(load_run(self.plugin, uid).node_data.get("shop_mode"), "lobby")
        self.assertIn("行商", back_lobby)


        atk_res = self.run_cmd("攻击 维克多", uid)
        self.assertIn("维克多", atk_res)
        run_bat = load_run(self.plugin, uid)
        self.assertEqual(run_bat.node_type, "battle")
        run_post = require_run(self._win_current_battle(uid))
        if run_post.node_type == "reward":
            self.run_cmd("离开", uid)
            run_post = load_run(self.plugin, uid)
        self.assertEqual(run_post.node_type, "grid_map")
        cur_c = floor_of(run_post).player_coords[uid]
        self.assertTrue(floor_of(run_post).rooms[cur_c].shared_payload.get("merchant_defeated"))

    def test_cafe_barista_props_and_attack(self):
        uid = "cafe_barista_user"
        self._start_grid(uid)
        _, run = move_to_room(self.plugin, uid, ("cafe",))
        if run.node_type != "cafe":
            fm = floor_of(run)
            cafe_coord = next(c for c, r in fm.rooms.items() if r.room_type == "cafe")
            fm.revealed_coords.append(cafe_coord)
            self.plugin.save_manager.save_save(uid, run)
            self.run_cmd(f"tp {cafe_coord}", uid)
            run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "cafe")
        look_out = self.run_cmd("look", uid)
        self.assertIn("布鲁诺", look_out)
        self.assertIn("咖啡机", look_out)
        self.assertIn("展开", self.run_cmd("f", uid))
        self.assertIn("talk", self.run_cmd("f", uid))

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
        self.assertEqual(load_run(self.plugin, uid).node_type, "battle")

    def test_town_inventory_folds_and_uses_localized_names(self):
        uid = "town_inventory_fold_user"
        self.run_cmd("主城", uid)
        stats = self.plugin.save_manager.load_stats(uid)
        stats.town_inventory = [
            "wine_glass",
            "strange_ore",
            "lost_notebook",
            "lucky_coin",
            "smith_hammer",
            "rusty_key",
        ]
        stats.open_world_bag = [
            "espresso_beans",
            "merchant_ledger",
            "ancient_notes",
            "skeleton_key",
            "smuggler_token",
        ]
        stats.town_chest = list(stats.open_world_bag)
        self.plugin.save_manager.save_stats(uid, stats)
        folded = self.run_cmd("状态", uid)
        self.assertIn("共 6 件", folded)
        self.assertIn("已折叠", folded)
        self.assertNotIn("酒杯", folded)
        bag_out = self.run_cmd("bag", uid)
        chest_out = self.run_cmd("talk 储物箱", uid)
        self.run_cmd("0", uid)
        for name in ("浓缩咖啡豆", "行商账册", "先古残页", "万能骷髅钥匙", "走私者徽记"):
            self.assertIn(name, bag_out)
            self.assertIn(name, chest_out)
        for raw_id in ("espresso_beans", "merchant_ledger", "ancient_notes", "skeleton_key", "smuggler_token"):
            self.assertNotIn(raw_id, bag_out)
            self.assertNotIn(raw_id, chest_out)
        stats = self.plugin.save_manager.load_stats(uid)
        stats.town_inventory = stats.town_inventory[:5]
        self.plugin.save_manager.save_stats(uid, stats)
        unfolded = self.run_cmd("状态", uid)
        self.assertIn("精致的空酒杯", unfolded)
        self.assertNotIn("已折叠", unfolded)

    

    def test_bag_modes_and_universal_fold(self):
        uid = "bag_fold_all_user"
        random.seed(2026)
        start_out = self.run_cmd("start confirm", uid)
        self.assertIn("f 折叠", start_out)
        start_folded = self.run_cmd("f", uid)
        self.assertIn("f 展开提示", start_folded)
        start_unfolded = self.run_cmd("f", uid)
        self.assertIn("f 折叠", start_unfolded)

        self.run_cmd("c 1", uid)
        rogue_bag = self.run_cmd("bag", uid)
        self.assertIn("秘境冒险行囊", rogue_bag)
        self.assertIn("负重", rogue_bag)
        town_bag = self.run_cmd("bag t", uid)
        self.assertIn("广场", town_bag)
        self.assertIn("储物箱", town_bag)
        stats = self.plugin.save_manager.load_stats(uid)
        stats.open_world_bag = ["merchant_ledger", "merchant_ledger", "ancient_notes"]
        self.plugin.save_manager.save_stats(uid, stats)
        stacked_bag = self.run_cmd("bag o", uid)
        self.assertIn("【行商账册】 ×2", stacked_bag)
        self.assertEqual(stacked_bag.count("【行商账册】"), 1)
        self.assertEqual(stacked_bag.count("记录着秘密货源"), 1)
        rogue_explicit = self.run_cmd("bag r", uid)
        self.assertIn("秘境冒险行囊", rogue_explicit)
        bad_bag = self.run_cmd("bag xyz", uid)
        self.assertIn("[FAIL]", bad_bag)

        self.run_cmd("w", uid)
        self.run_cmd("talk 店长", uid)
        cafe_dialog_fold = self.run_cmd("f", uid)
        self.assertIn("展开提示", cafe_dialog_fold)
        self.run_cmd("f", uid)
        self.run_cmd("leave", uid)
        self.run_cmd("leave", uid)

        self.run_cmd("w", uid)
        self.run_cmd("d", uid)
        shop_fold = self.run_cmd("f", uid)
        self.assertIn("展开提示", shop_fold)
        self.run_cmd("f", uid)
        self.run_cmd("c 1", uid)
        shop_dlg_fold = self.run_cmd("f", uid)
        self.assertIn("展开提示", shop_dlg_fold)
        self.run_cmd("f", uid)
        self.run_cmd("leave", uid)
        self.run_cmd("leave", uid)

        _, run = move_to_room(self.plugin, uid, ("battle", "elite"))
        self.assertEqual(run.node_type, "battle")
        battle_fold = self.run_cmd("f", uid)
        self.assertIn("展开提示", battle_fold)
        battle_unfold = self.run_cmd("f", uid)
        self.assertIn("f 折叠", battle_unfold)

    def _finish_battle_in_test(self, uid: str):
        for _ in range(40):
            r = load_run(self.plugin, uid)
            if r.node_type == "battle":
                for _ in range(8):
                    r = load_run(self.plugin, uid)
                    if r.node_type != "battle":
                        break
                    pick = None
                    for prio in (("sunburst",), ("fire_bolt", "magic_missile"), ("shield", "first_aid")):
                        for idx, c in enumerate(r.player.hand, 1):
                            if c.id in prio and r.player.actions >= 1:
                                pick = idx
                                break
                        if pick is not None:
                            break
                    if pick is not None:
                        self.run_cmd(f"p {pick}", uid)
                        continue
                    break
                if load_run(self.plugin, uid).node_type == "battle":
                    self.run_cmd("e", uid)
            elif r.node_type in ("reward", "boss_chest"):
                if r.node_type == "boss_chest":
                    self.run_cmd("1", uid)
                if load_run(self.plugin, uid).node_type != "grid_map":
                    self.run_cmd("leave", uid)
            elif r.node_type == "grid_map":
                break
            else:
                self.run_cmd("leave", uid)

    def _walk_to_targets(self, uid: str, targets: set[str], *, avoid_high_danger: bool = False):
        import heapq

        last_res = ""
        for _ in range(8):
            run_cur = load_run(self.plugin, uid)
            fm = floor_of(run_cur)
            start_c = fm.player_coords[uid]
            if start_c in targets and run_cur.node_type != "grid_map":
                return last_res
            pq = [(0, start_c)]
            dist = {start_c: 0}
            prev = {}
            target_c = None
            while pq:
                d, cur = heapq.heappop(pq)
                if d > dist.get(cur, 10**9):
                    continue
                if cur in targets:
                    target_c = cur
                    break
                cx, cy = coord_to_xy(cur)
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < fm.width and 0 <= ny < fm.height):
                        continue
                    nc = xy_to_coord(nx, ny)
                    nr = fm.rooms.get(nc)
                    if not nr or nr.room_type in ("wall", "secret_boss"):
                        continue
                    if nr.cleared or nr.room_type in ("spawn", "empty") or nc in targets:
                        cost = 1
                    elif nr.room_type == "obstacle":
                        cost = 50
                    elif nr.room_type == "high_danger":
                        cost = 2000 if avoid_high_danger else 500
                    elif nr.room_type in ("battle", "elite", "boss"):
                        cost = 500
                    else:
                        cost = 10
                    if d + cost < dist.get(nc, 10**9):
                        dist[nc] = d + cost
                        prev[nc] = cur
                        heapq.heappush(pq, (d + cost, nc))
            assert target_c is not None, "target coord must exist"
            path = []
            cur = target_c
            while cur != start_c:
                p_c = prev[cur]
                px, py = coord_to_xy(p_c)
                cx, cy = coord_to_xy(cur)
                path.append((cur, {(0, -1): "w", (0, 1): "s", (-1, 0): "a", (1, 0): "d"}[(cx - px, cy - py)]))
                cur = p_c
            path.reverse()
            interrupted = False
            for step_idx, (coord, dcmd) in enumerate(path):
                last_res = self.run_cmd(dcmd, uid)
                cur_run = load_run(self.plugin, uid)
                if cur_run.node_type == "grid_map" and floor_of(cur_run).player_coords.get(uid) != coord:
                    last_res = self.run_cmd(dcmd, uid)
                    if load_run(self.plugin, uid).node_type == "grid_map" and floor_of(load_run(self.plugin, uid)).player_coords.get(uid) != coord:
                        last_res = self.run_cmd(dcmd, uid)
                    cur_run = load_run(self.plugin, uid)
                if step_idx < len(path) - 1:
                    if cur_run.node_type == "battle":
                        self._finish_battle_in_test(uid)
                        interrupted = True
                        break
                    if cur_run.node_type in ("shop", "rest", "cafe", "landmark", "life_merchant", "treasure"):
                        self.run_cmd("leave", uid)
                    elif cur_run.node_type == "event":
                        opts = cur_run.node_data.get("options", [])
                        if opts:
                            self.run_cmd(f"c {len(opts)}", uid)
            if not interrupted:
                return last_res
        return last_res

    def test_persistent_buffs_and_camp_scavenge(self):
        uid = "pbuff_camp_user"
        random.seed(2026)
        st_solo = self.plugin.save_manager.load_stats(uid)
        st_solo.town_health_bonus = 800
        st_solo.locked_cards = ["sunburst", "sunburst"]
        self.plugin.save_manager.save_stats(uid, st_solo)
        self._start_grid(uid)

        fm_solo = floor_of(load_run(self.plugin, uid))
        camp_targets = {
            c for c, r in fm_solo.rooms.items() if r.room_type == "landmark" and getattr(r, "landmark_id", "") == "broken_sword_camp"
        }
        camp_entry = self._walk_to_targets(uid, camp_targets, avoid_high_danger=True)
        self.assertEqual(load_run(self.plugin, uid).node_type, "landmark")
        self.assertIn("断剑残营", camp_entry)
        scavenge_res = self.run_cmd("c 3", uid)
        self.assertTrue("断剑残营" in scavenge_res and ("翻出了" in scavenge_res or "捡到了" in scavenge_res))
        run_camp = load_run(self.plugin, uid)
        if run_camp.node_type == "landmark":
            self.run_cmd("leave", uid)

        fm_after_camp = floor_of(load_run(self.plugin, uid))
        hd_solo_targets = {c for c, r in fm_after_camp.rooms.items() if r.room_type == "high_danger" and not r.cleared}
        hd_res = self._walk_to_targets(uid, hd_solo_targets)
        run_hd = load_run(self.plugin, uid)
        self.assertEqual(run_hd.node_type, "battle")
        self.assertIn("深渊寒蚀", hd_res)
        self.assertTrue(any(b.id == "weak" for b in run_hd.player.buffs))
        self.assertIn("不可用", self.run_cmd("map", uid))

        import re
        from game.data.progression.account_config import RENAME_COST_GP
        uid1, uid2 = "pb_c1", "pb_c2"
        for u in (uid1, uid2):
            st = self.plugin.save_manager.load_stats(u)
            st.gp = max(st.gp, RENAME_COST_GP)
            st.town_health_bonus = 800
            st.purchased_pool = ["glacier_fortress", "abyss_collapse", "frost_nova", "jack_brew", "meteor_swarm"]
            st.locked_cards = ["glacier_fortress", "abyss_collapse", "jack_brew"]
            self.plugin.save_manager.save_stats(u, st)
        self.run_cmd("friend name 队长pb", uid1)
        self.run_cmd("friend name 队员pb", uid2)
        s1 = self.plugin.save_manager.load_stats(uid1)
        s2 = self.plugin.save_manager.load_stats(uid2)
        pid1 = s1.player_handle or s1.player_name
        pid2 = s2.player_handle or s2.player_name
        self.run_cmd(f"friend add {pid2}", uid1)
        self.run_cmd(f"friend accept {pid1}", uid2)
        created = self.run_cmd("team create", uid1)
        match = re.search(r"队伍 ([A-Z0-9]{6})", created)
        assert match is not None, "team id must be present"
        lobby_id = match.group(1)
        self.run_cmd(f"friend invite {pid2}", uid1)
        self.run_cmd(f"team join {lobby_id}", uid2)
        self.run_cmd("team ready", uid2)
        random.seed(2026)
        self.run_cmd("team start", uid1)
        self.run_cmd("c 1", uid1)
        self.run_cmd("c 1", uid2)

        run_coop = load_run(self.plugin, uid1)
        fm = floor_of(run_coop)
        hd_targets = {c for c, r in fm.rooms.items() if r.room_type == "high_danger"}
        self._walk_to_targets(uid1, hd_targets)
        run_hd_coop = load_run(self.plugin, uid1)
        self.assertEqual(run_hd_coop.node_type, "battle")
        self.assertTrue(any(b.id == "weak" for b in run_hd_coop.player.buffs))
        self.assertFalse(any(b.id == "abyss_chill" for b in run_hd_coop.player.persistent_buffs))
        self._finish_battle_in_test(uid1)
        map_after_hd = self.run_cmd("map", uid1)
        self.assertIn("队长pb", map_after_hd)
        move_to_room(self.plugin, uid1, ("cafe",))
        gram_res = self.run_cmd("touch 留声机", uid1)
        self.assertIn("黑胶留声机", gram_res)
        run_cured = load_run(self.plugin, uid1)
        self.assertFalse(any(b.id == "abyss_chill" for b in run_cured.player.persistent_buffs))
