import asyncio
import random
import tempfile
import unittest

from game.core.world.grid_map_generator import xy_to_coord
from game.models.state import EnemyState, FloorMapState, RoomState
from game.test.core.base import CorePlugin, load_run, move_to_room, run_command


class TestInvisibilityPotion(unittest.TestCase):
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

    def _start_solo(self, uid: str):
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        return load_run(self.plugin, uid)

    def test_map_drink_bypass_true_sight_and_break_on_interact_or_battle(self):
        uid = "invis_map_user"
        stats = self.plugin.save_manager.load_stats(uid)
        stats.town_health_bonus = 300
        self.plugin.save_manager.save_stats(uid, stats)
        run = self._start_solo(uid)

        rooms = {}
        for y in range(4):
            for x in range(8):
                c = xy_to_coord(x, y)
                rooms[c] = RoomState(coord=c, room_type="empty", explored=(c == "A1"), cleared=(c == "A1"))
        rooms["B1"] = RoomState(
            coord="B1",
            room_type="battle",
            npcs=["dungeon_raiders"],
            items=["espresso_beans"],
            props=["ancient_brazier"],
        )
        rooms["C1"] = RoomState(
            coord="C1",
            room_type="boss",
            npcs=["floor_boss"],
            shared_payload={"preset_boss_name": "雷霆领主"},
        )
        rooms["D1"] = RoomState(
            coord="D1",
            room_type="empty",
            npcs=["lost_scholar"],
            props=["ancient_brazier"],
        )
        rooms["E1"] = RoomState(
            coord="E1",
            room_type="boss",
            npcs=["floor_boss"],
            shared_payload={"preset_boss_name": "远古红龙"},
        )
        rooms["F1"] = RoomState(
            coord="F1",
            room_type="boss",
            npcs=["floor_boss"],
            shared_payload={"preset_boss_name": "虚空之门·尤格-索托斯"},
        )
        rooms["G1"] = RoomState(
            coord="G1",
            room_type="battle",
            npcs=["dungeon_raiders"],
        )
        run.floor_map = FloorMapState(
            floor_index=1,
            width=8,
            height=4,
            rooms=rooms,
            revealed_coords=["A1"],
            player_coords={uid: "A1"},
            boss_coord="F1",
        )
        run.player.bag_items = [
            "potion:invisibility_potion",
            "potion:invisibility_potion",
            "potion:invisibility_potion",
            "potion:invisibility_potion",
        ]
        self.plugin.save_manager.save_save(uid, run)

        drink_res = self.run_cmd("drink 隐身药水", uid)
        self.assertIn("隐身", drink_res)
        run_drank = load_run(self.plugin, uid)
        self.assertTrue(any(b.id == "invisibility" for b in run_drank.player.persistent_buffs))

        step_b1 = self.run_cmd("d", uid)
        self.assertEqual(load_run(self.plugin, uid).node_type, "grid_map")
        self.assertIn("绕开了", step_b1)
        take_res = self.run_cmd("take 浓缩咖啡豆", uid)
        self.assertIn("拾取", take_res)
        self.assertTrue(any(b.id == "invisibility" for b in load_run(self.plugin, uid).player.persistent_buffs))

        step_c1 = self.run_cmd("d", uid)
        self.assertEqual(load_run(self.plugin, uid).node_type, "grid_map")
        self.assertIn("绕开了", step_c1)

        self.run_cmd("d", uid)
        touch_res = self.run_cmd("touch 火盆", uid)
        self.assertIn("解除了", touch_res)
        self.assertFalse(any(b.id == "invisibility" for b in load_run(self.plugin, uid).player.persistent_buffs))

        self.run_cmd("use 隐身药水", uid)
        self.assertTrue(any(b.id == "invisibility" for b in load_run(self.plugin, uid).player.persistent_buffs))
        talk_res = self.run_cmd("talk 艾拉", uid)
        self.assertIn("解除了", talk_res)
        self.assertEqual(load_run(self.plugin, uid).node_type, "room_dialog")
        self.assertFalse(any(b.id == "invisibility" for b in load_run(self.plugin, uid).player.persistent_buffs))
        self.run_cmd("leave", uid)

        self.run_cmd("drink 隐身药水", uid)
        dragon_res = self.run_cmd("d", uid)
        run_dragon = load_run(self.plugin, uid)
        self.assertEqual(run_dragon.node_type, "battle")
        self.assertIn("真实视觉", dragon_res)
        self.assertEqual(run_dragon.enemies[0].name, "远古红龙")
        self.assertFalse(any(b.id == "invisibility" for b in run_dragon.player.persistent_buffs))
        self.assertFalse(any(b.id == "invisibility" for b in run_dragon.player.buffs))

        self.run_cmd("abandon confirm", uid)
        stats2 = self.plugin.save_manager.load_stats(uid)
        stats2.town_health_bonus = 300
        self.plugin.save_manager.save_stats(uid, stats2)
        run2 = self._start_solo(uid)
        run2.floor_map = FloorMapState(
            floor_index=4,
            width=4,
            height=2,
            rooms={
                "A1": RoomState(coord="A1", room_type="spawn", explored=True, cleared=True),
                "B1": RoomState(
                    coord="B1",
                    room_type="boss",
                    npcs=["floor_boss"],
                    shared_payload={"preset_boss_name": "虚空之门·尤格-索托斯"},
                ),
            },
            revealed_coords=["A1"],
            player_coords={uid: "A1"},
            boss_coord="B1",
        )
        run2.player.bag_items = ["potion:invisibility_potion"]
        self.plugin.save_manager.save_save(uid, run2)
        self.run_cmd("drink 隐身药水", uid)
        yog_res = self.run_cmd("d", uid)
        run_yog = load_run(self.plugin, uid)
        self.assertEqual(run_yog.node_type, "battle")
        self.assertIn("真实视觉", yog_res)
        self.assertIn("尤格-索托斯", run_yog.enemies[0].name)

    def test_battle_invisibility_duration_dodge_probability_and_true_sight(self):
        uid = "invis_battle_user"
        stats = self.plugin.save_manager.load_stats(uid)
        stats.town_health_bonus = 500
        self.plugin.save_manager.save_stats(uid, stats)

        dodges = 0
        hits = 0
        for trial_seed in range(1, 25):
            self.plugin.save_manager.delete_save(uid)
            random.seed(trial_seed)
            self._start_solo(uid)
            _, run = move_to_room(self.plugin, uid, ("battle",))
            if run.node_type != "battle":
                continue
            run.player.hp = 400
            run.player.max_hp = 400
            run.player.shield = 0
            run.player.bag_items = ["potion:invisibility_potion"]
            run.enemies = [
                EnemyState(
                    name="测试训练假人",
                    hp=999999,
                    max_hp=999999,
                    shield=0,
                    actions=1,
                    bonus_actions=0,
                    max_actions=1,
                    max_bonus_actions=0,
                    intent_type="attack",
                    intent_val=10,
                    intent_desc="横扫击打 (造成 10 点钝击伤害)",
                    intent_a_type="attack",
                    intent_a_val=10,
                    intent_a_desc="横扫击打 (造成 10 点钝击伤害)",
                )
            ]
            self.plugin.save_manager.save_save(uid, run)

            drink_out = self.run_cmd("drink 1", uid)
            self.assertIn("3 回合【隐身】", drink_out)
            r1 = load_run(self.plugin, uid)
            inv_b = next((b for b in r1.player.buffs if b.id == "invisibility"), None)
            assert inv_b is not None
            self.assertEqual(inv_b.stacks, 3)

            hp_before = r1.player.hp
            e_res = self.run_cmd("e", uid)
            r2 = load_run(self.plugin, uid)
            inv_2 = next((b for b in r2.player.buffs if b.id == "invisibility"), None)
            assert inv_2 is not None
            self.assertEqual(inv_2.stacks, 2)
            if r2.player.hp == hp_before:
                dodges += 1
                self.assertIn("闪避了", e_res)
            else:
                hits += 1

            if dodges + hits == 1:
                self.run_cmd("e", uid)
                r3 = load_run(self.plugin, uid)
                inv_3 = next((b for b in r3.player.buffs if b.id == "invisibility"), None)
                assert inv_3 is not None
                self.assertEqual(inv_3.stacks, 1)
                self.run_cmd("e", uid)
                r4 = load_run(self.plugin, uid)
                self.assertFalse(any(b.id == "invisibility" for b in r4.player.buffs))

        self.assertGreater(dodges, 0)
        self.assertGreater(hits, 0)
        self.assertGreater(dodges, hits)

        self.plugin.save_manager.delete_save(uid)
        run_ts = self._start_solo(uid)
        run_ts.floor_map = FloorMapState(
            floor_index=1,
            width=4,
            height=2,
            rooms={
                "A1": RoomState(coord="A1", room_type="spawn", explored=True, cleared=True),
                "B1": RoomState(
                    coord="B1",
                    room_type="boss",
                    npcs=["floor_boss"],
                    shared_payload={"preset_boss_name": "远古红龙"},
                ),
            },
            revealed_coords=["A1"],
            player_coords={uid: "A1"},
            boss_coord="B1",
        )
        self.plugin.save_manager.save_save(uid, run_ts)
        self.run_cmd("d", uid)
        run_dragon = load_run(self.plugin, uid)
        self.assertEqual(run_dragon.node_type, "battle")
        run_dragon.player.hp = 400
        run_dragon.player.max_hp = 400
        run_dragon.player.shield = 0
        run_dragon.player.bag_items = ["potion:invisibility_potion"]
        self.plugin.save_manager.save_save(uid, run_dragon)
        self.run_cmd("drink 1", uid)
        hp_ts_before = load_run(self.plugin, uid).player.hp
        ts_turn = ""
        for _ in range(5):
            ts_turn = self.run_cmd("e", uid)
            if "真实视觉看穿" in ts_turn:
                break
        self.assertIn("真实视觉看穿", ts_turn)
        self.assertLess(load_run(self.plugin, uid).player.hp, hp_ts_before)


if __name__ == "__main__":
    unittest.main()
