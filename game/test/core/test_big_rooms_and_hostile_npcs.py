import asyncio
import random
import tempfile
import unittest

from game.core.world.grid_map_generator import coord_to_xy, xy_to_coord
from game.core.world.persistent_buffs import add_persistent_buff
from game.core.world.rooms.big_room import create_big_room_instance, get_big_room
from game.data.big_room_config import build_rect_offsets
from game.models.state import FloorMapState, RoomState
from game.test.core.base import CorePlugin, floor_of, load_run, move_to_room, require_run, run_command


class TestBigRoomsAndHostileNpcs(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(1)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, cmd, uid))

    def _start_solo(self, uid: str):
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        return load_run(self.plugin, uid)

    def _win_current_battle(self, uid: str):
        for _ in range(80):
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

    def test_generated_big_room_whole_reveal_and_shared_npc_local_items(self):
        uid = "br_gen_user"
        run = self._start_solo(uid)
        fm = floor_of(run)
        self.assertTrue(fm.big_rooms)

        scriptorium = next(
            (br for br in fm.big_rooms.values() if br.template_id == "sunken_scriptorium"),
            None,
        )
        if scriptorium is None:
            for seed_val in range(2, 20):
                self.plugin.save_manager.delete_save(uid)
                random.seed(seed_val)
                run = self._start_solo(uid)
                fm = floor_of(run)
                scriptorium = next(
                    (br for br in fm.big_rooms.values() if br.template_id == "sunken_scriptorium"),
                    None,
                )
                if scriptorium is not None:
                    break
        assert scriptorium is not None, "sunken_scriptorium big room must generate"

        c0 = scriptorium.cells[0]
        c0_xy = coord_to_xy(c0)
        adj_c1 = None
        move_dir = None
        for dcmd, (dx, dy) in (("d", (1, 0)), ("a", (-1, 0)), ("s", (0, 1)), ("w", (0, -1))):
            cand = xy_to_coord(c0_xy[0] + dx, c0_xy[1] + dy)
            if cand in scriptorium.cells:
                adj_c1 = cand
                move_dir = dcmd
                break
        assert adj_c1 is not None and move_dir is not None

        fm.rooms[c0].items = ["espresso_beans"]
        fm.rooms[adj_c1].items = ["field_bandage"]
        fm.revealed_coords.append(c0)
        fm.rooms[c0].explored = True
        self.plugin.save_manager.save_save(uid, run)

        tp_out = self.run_cmd(f"tp {c0}", uid)
        self.assertIn("沉没抄经厅", tp_out)
        self.assertIn("📖", tp_out)

        run_after_enter = load_run(self.plugin, uid)
        fm_after = floor_of(run_after_enter)
        for cell_c in scriptorium.cells:
            self.assertTrue(fm_after.rooms[cell_c].explored)
            self.assertIn(cell_c, fm_after.revealed_coords)

        talk_out = self.run_cmd("talk 艾拉", uid)
        self.assertIn("艾拉", talk_out)
        self.run_cmd("leave", uid)

        take1 = self.run_cmd("take 浓缩咖啡豆", uid)
        self.assertIn("拾取", take1)

        move_out = self.run_cmd(move_dir, uid)
        self.assertIn("仍属于当前【沉没抄经厅】", move_out)
        self.assertIn("战地绷带", move_out)
        self.assertIn("迷途学者·艾拉", move_out)
        take2 = self.run_cmd("take 战地绷带", uid)
        self.assertIn("拾取", take2)

    def test_big_room_l_shape_cell_reveal_shared_items_and_stealth_combat(self):
        uid = "br_custom_user"
        stats = self.plugin.save_manager.load_stats(uid)
        stats.town_health_bonus = 400
        self.plugin.save_manager.save_stats(uid, stats)
        run = self._start_solo(uid)

        rooms = {}
        for y in range(6):
            for x in range(8):
                c = xy_to_coord(x, y)
                rooms[c] = RoomState(coord=c, room_type="empty", explored=(c == "A1"), cleared=(c == "A1"))
        fm = FloorMapState(
            floor_index=1,
            width=8,
            height=6,
            rooms=rooms,
            revealed_coords=["A1"],
            player_coords={uid: "A1"},
            boss_coord="H6",
        )
        bazaar = create_big_room_instance(fm, "br_bazaar", "smuggler_bazaar", ["B1", "C1"])
        bazaar.items = ["smuggler_token"]
        catacomb = create_big_room_instance(fm, "br_catacomb", "labyrinth_catacomb", ["B2", "C2", "B3", "B4"])
        for cell_c in catacomb.cells:
            fm.rooms[cell_c].npcs = []
        fm.rooms["B3"].npcs = ["crypt_warden"]
        run.floor_map = fm
        add_persistent_buff(run.player, "stealth_cloak", 1, name="潜行斗篷", desc="免除踩格自动开战")
        self.plugin.save_manager.save_save(uid, run)

        enter_bazaar = self.run_cmd("d", uid)
        self.assertIn("地下走私集市", enter_bazaar)
        self.assertIn("走私者徽记", enter_bazaar)
        self.assertIn("拾取", self.run_cmd("take 走私者徽记", uid))
        move_bazaar = self.run_cmd("d", uid)
        self.assertNotIn("走私者徽记", move_bazaar)
        self.assertIn("黑市掮客·莫斯", move_bazaar)

        self.run_cmd("a", uid)
        enter_catacomb = self.run_cmd("s", uid)
        self.assertIn("错综地穴墓室", enter_catacomb)
        fm_cat = floor_of(load_run(self.plugin, uid))
        self.assertTrue(fm_cat.rooms["B2"].explored)
        self.assertFalse(fm_cat.rooms["B4"].explored)

        step_warden = self.run_cmd("s", uid)
        run_stealth = load_run(self.plugin, uid)
        self.assertEqual(run_stealth.node_type, "grid_map")
        self.assertIn("隐匿", step_warden)
        self.assertIn("墓穴守卫", step_warden)

        atk_out = self.run_cmd("atk 墓穴守卫", uid)
        self.assertEqual(load_run(self.plugin, uid).node_type, "battle")
        self.assertIn("墓穴守卫", atk_out)
        run_post = require_run(self._win_current_battle(uid))
        if run_post.node_type == "reward":
            self.run_cmd("leave", uid)
            run_post = load_run(self.plugin, uid)
        self.assertEqual(run_post.node_type, "grid_map")
        fm_done = floor_of(run_post)
        self.assertIn("crypt_warden", fm_done.rooms["B3"].defeated_npcs)
        self.assertTrue(fm_done.rooms["B3"].cleared)

    def test_big_room_10x10_limit_and_save_roundtrip(self):
        uid = "br_10x10_user"
        run = self._start_solo(uid)
        with self.assertRaises(ValueError):
            build_rect_offsets(11, 1)
        with self.assertRaises(ValueError):
            build_rect_offsets(1, 11)

        rooms = {}
        for y in range(12):
            for x in range(12):
                c = xy_to_coord(x, y)
                rooms[c] = RoomState(coord=c, room_type="wall")
        rooms["A1"] = RoomState(coord="A1", room_type="spawn", explored=True, cleared=True)
        fm = FloorMapState(
            floor_index=1,
            width=12,
            height=12,
            rooms=rooms,
            revealed_coords=["A1"],
            player_coords={uid: "A1"},
            boss_coord="L12",
        )
        cells_10x10 = [xy_to_coord(1 + dx, 0 + dy) for dx, dy in build_rect_offsets(10, 10)]
        br = create_big_room_instance(fm, "br_max_10x10", "forgotten_armory", cells_10x10)
        self.assertEqual(br.width, 10)
        self.assertEqual(br.height, 10)
        self.assertEqual(len(br.cells), 100)
        run.floor_map = fm
        add_persistent_buff(run.player, "stealth_cloak", 1, name="潜行斗篷", desc="免除踩格自动开战")
        self.plugin.save_manager.save_save(uid, run)

        reloaded = load_run(self.plugin, uid)
        fm_re = floor_of(reloaded)
        re_br = get_big_room(fm_re, "B1")
        assert re_br is not None
        self.assertEqual(re_br.width, 10)
        self.assertEqual(re_br.height, 10)
        self.assertEqual(len(re_br.cells), 100)

        enter_out = self.run_cmd("d", uid)
        self.assertIn("旧式军械库", enter_out)
        self.assertIn("🛡️", enter_out)
        fm_entered = floor_of(load_run(self.plugin, uid))
        self.assertTrue(all(fm_entered.rooms[c].explored for c in cells_10x10))

    def test_treasure_chest_prop_and_hostile_npc_battle(self):
        uid = "treasure_prop_user"
        stats = self.plugin.save_manager.load_stats(uid)
        stats.town_health_bonus = 300
        self.plugin.save_manager.save_stats(uid, stats)
        self._start_solo(uid)

        res_t = ""
        for _ in range(10):
            res_t, run_t = move_to_room(self.plugin, uid, ("treasure",))
            if run_t.node_type == "battle":
                run_w = require_run(self._win_current_battle(uid))
                if run_w.node_type == "reward":
                    self.run_cmd("leave", uid)
                continue
            if run_t.node_type in ("shop", "rest", "cafe", "landmark", "life_merchant"):
                self.run_cmd("leave", uid)
                continue
            if run_t.node_type == "event":
                opts = run_t.node_data.get("options", [])
                if opts:
                    self.run_cmd(f"c {len(opts)}", uid)
                continue
            if run_t.node_type == "grid_map" and floor_of(run_t).rooms[floor_of(run_t).player_coords[uid]].room_type == "treasure":
                break
        run_t = load_run(self.plugin, uid)
        self.assertEqual(run_t.node_type, "grid_map")
        self.assertIn("宝箱", res_t)

        open_res = self.run_cmd("open 宝箱", uid)
        run_open = load_run(self.plugin, uid)
        self.assertEqual(run_open.node_type, "treasure")
        self.assertIn("宝箱", open_res)
        self.run_cmd("c 1", uid)
        self.run_cmd("c 1", uid)
        for _ in range(10):
            r_cur = load_run(self.plugin, uid)
            if r_cur.node_type == "grid_map":
                break
            if r_cur.node_type == "gem_insert":
                self.run_cmd("leave", uid)
            elif r_cur.node_type == "card_select":
                cards = r_cur.node_data.get("cards") or []
                self.run_cmd(f"c {len(cards) + 1}", uid)
            elif r_cur.node_type == "treasure":
                self.run_cmd("leave", uid)
            else:
                self.run_cmd("leave", uid)
        run_after_t = load_run(self.plugin, uid)
        self.assertEqual(run_after_t.node_type, "grid_map")
        t_coord = floor_of(run_after_t).player_coords[uid]
        self.assertIn("treasure_chest", floor_of(run_after_t).rooms[t_coord].interacted_props)
        self.assertIn("没有什么新发现", self.run_cmd("touch 宝箱", uid))

        _, run_b = move_to_room(self.plugin, uid, ("battle",))
        self.assertEqual(run_b.node_type, "battle")
        b_coord = floor_of(run_b).player_coords[uid]
        run_won = require_run(self._win_current_battle(uid))
        if run_won.node_type == "reward":
            self.run_cmd("leave", uid)
            run_won = load_run(self.plugin, uid)
        self.assertEqual(run_won.node_type, "grid_map")
        b_room = floor_of(run_won).rooms[b_coord]
        self.assertTrue(b_room.cleared)
        self.assertIn("dungeon_raiders", b_room.defeated_npcs)


if __name__ == "__main__":
    unittest.main()
