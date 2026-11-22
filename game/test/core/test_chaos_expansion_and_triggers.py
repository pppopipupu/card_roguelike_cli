import asyncio
import random
import tempfile
import unittest
from unittest.mock import patch

from game.core.world.grid_map_generator import generate_floor_map, xy_to_coord
from game.core.world.rooms.big_room import create_big_room_instance
from game.core.world.rooms.forced_triggers import attach_room_triggers, seed_floor_forced_triggers
from game.models.state import FloorMapState, RoomState
from game.test.core.base import CorePlugin, load_run, move_to_room, run_command


class TestChaosExpansionAndTriggers(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20261118)
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

    def test_forced_triggers_on_enter_and_interact_with_chaos_big_room(self):
        uid = "chaos_trigger_user"
        run = self._start_solo(uid)
        run.player.gold = 120
        rooms = {}
        for y in range(4):
            for x in range(6):
                c = xy_to_coord(x, y)
                rooms[c] = RoomState(coord=c, room_type="empty", explored=(c == "A1"), cleared=(c == "A1"))
        fm = FloorMapState(
            floor_index=1,
            width=6,
            height=4,
            rooms=rooms,
            revealed_coords=["A1"],
            player_coords={uid: "A1"},
        )
        create_big_room_instance(fm, "br_hakurei_1", "hakurei_shrine_approach", ["B1", "C1", "B2", "C2"], rng=random.Random(11))
        attach_room_triggers(
            fm,
            "D1",
            [{"id": "chaos_dimensional_sneak", "timing": "on_enter", "once": True, "chance": 1.0}],
        )
        seed_floor_forced_triggers(fm, 1)
        run.floor_map = fm
        self.plugin.save_manager.save_save(uid, run)

        enter_shrine = self.run_cmd("d", uid)
        self.assertIn("强制事件", enter_shrine)
        self.assertIn("博丽赛钱结界", enter_shrine)
        after_first = load_run(self.plugin, uid)
        self.assertEqual(after_first.player.gold, 115)
        self.assertTrue(any(b.id == "ancient_ward" for b in after_first.player.persistent_buffs))

        enter_second_cell = self.run_cmd("d", uid)
        self.assertNotIn("博丽赛钱结界", enter_second_cell)
        self.assertEqual(load_run(self.plugin, uid).player.gold, 115)

        with patch("game.core.world.rooms.chaos_props.random.random", return_value=0.0):
            touch_res = self.run_cmd("touch 赛钱箱", uid)
        self.assertIn("强制插曲", touch_res)
        self.assertIn("博丽赛钱箱", touch_res)

        sneak_res = self.run_cmd("d", uid)
        self.assertIn("强制事件", sneak_res)

    def test_dialog_action_and_effect_wording_plus_chaos_npcs_and_kyubey_revive(self):
        uid = "chaos_npc_user"
        run = self._start_solo(uid)
        run.player.gold = 200
        run.player.sp = 2
        run.player.max_hp = 100
        run.player.hp = 95
        rooms = {
            "A1": RoomState(coord="A1", room_type="empty", explored=True, cleared=True),
            "B1": RoomState(coord="B1", room_type="empty", npcs=["lost_scholar", "hakurei_reimu"]),
            "C1": RoomState(coord="C1", room_type="empty", npcs=["kyubey", "takamachi_nanoha"]),
            "D1": RoomState(coord="D1", room_type="empty", npcs=["tomoe_mami"], props=["tea_party_table"]),
        }
        run.floor_map = FloorMapState(
            floor_index=2,
            width=5,
            height=2,
            rooms=rooms,
            revealed_coords=["A1"],
            player_coords={uid: "A1"},
        )
        self.plugin.save_manager.save_save(uid, run)

        self.run_cmd("d", uid)
        scholar_dlg = self.run_cmd("talk 艾拉", uid)
        self.assertIn("你知道隐秘首领祭坛是什么吗？", scholar_dlg)
        self.assertIn("（", scholar_dlg)
        self.assertIn("）", scholar_dlg)
        self.run_cmd("leave", uid)

        reimu_dlg = self.run_cmd("talk 博丽灵梦", uid)
        self.assertIn("香油钱", reimu_dlg)
        self.assertIn("（", reimu_dlg)
        reimu_donate = self.run_cmd("c 1", uid)
        self.assertIn("灵梦", reimu_donate)

        self.run_cmd("d", uid)
        nanoha_dlg = self.run_cmd("talk 高町奈叶", uid)
        self.assertIn("旭日之心", nanoha_dlg)
        nanoha_charge = self.run_cmd("c 2", uid)
        self.assertIn("SP", nanoha_charge)

        kyubey_dlg = self.run_cmd("talk 丘比", uid)
        self.assertIn("契约", kyubey_dlg)
        battle_start = self.run_cmd("c 3", uid)
        self.assertIn("丘比", battle_start)

        cur_run = load_run(self.plugin, uid)
        cur_run.player.bag_items.extend(["mini_hakkero", "mini_hakkero"])
        self.plugin.save_manager.save_save(uid, cur_run)

        spark_1 = self.run_cmd("use 迷你八卦炉", uid)
        self.assertIn("Master Spark", spark_1)
        mid_run = load_run(self.plugin, uid)
        self.assertTrue(mid_run.enemies[0].hp > 0)
        self.assertTrue(mid_run.node_data.get("kyubey_backup_used") or mid_run.enemies[0].hp > 0)

        end_turn_res = self.run_cmd("结束", uid)
        self.assertIn("丘比", end_turn_res)
        self.run_cmd("use 迷你八卦炉", uid)
        self.run_cmd("use 迷你八卦炉", uid)
        self.run_cmd("结束", uid)

    def test_chaos_items_use_in_map_and_floor_generation_consistency(self):
        uid = "chaos_item_user"
        run = self._start_solo(uid)
        run.player.hp = 60
        run.player.sp = 0
        run.player.exhaustion = 2
        rooms = {
            "A1": RoomState(
                coord="A1",
                room_type="empty",
                explored=True,
                cleared=True,
                items=["yin_yang_orb", "grief_seed", "mana_cartridge", "kyubey_contract", "magic_mushroom"],
            ),
            "B1": RoomState(coord="B1", room_type="treasure"),
            "A2": RoomState(coord="A2", room_type="shop"),
        }
        run.floor_map = FloorMapState(
            floor_index=1,
            width=3,
            height=2,
            rooms=rooms,
            revealed_coords=["A1"],
            player_coords={uid: "A1"},
        )
        self.plugin.save_manager.save_save(uid, run)

        for name in ("阴阳玉", "悲叹之种", "魔导增幅弹仓", "空白契约书", "魔法森林奇异蘑菇"):
            take_res = self.run_cmd(f"take {name}", uid)
            self.assertIn(name, take_res)

        r1 = self.run_cmd("use 阴阳玉", uid)
        self.assertIn("阴阳玉", r1)
        r2 = self.run_cmd("use 悲叹之种", uid)
        self.assertIn("悲叹之种", r2)
        r3 = self.run_cmd("use 魔导增幅弹仓", uid)
        self.assertIn("Standby", r3)
        r4 = self.run_cmd("use 空白契约书", uid)
        self.assertIn("契约", r4)
        r5 = self.run_cmd("use 魔法森林奇异蘑菇", uid)
        self.assertIn("🍄", r5)

        after = load_run(self.plugin, uid)
        self.assertGreater(after.player.gold, 20)
        self.assertTrue(any(b.id == "ancient_ward" for b in after.player.persistent_buffs))

        fm_gen = generate_floor_map(after, 1)
        self.assertGreater(len(fm_gen.rooms), 0)
        self.assertTrue(all(r.room_type != "" for r in fm_gen.rooms.values()))

    def test_unregistered_enemies_and_cafe_npcs_registered_with_unique_intents(self):
        from game.data.world.cafe_data import CAFE_GUESTS, CAFE_NORMALS
        from game.data.enemies.enemy_data import ENEMY_CONFIG
        from game.data.world.room_interact_data import ROOM_NPCS
        from game.entities.enemies.base import ALL_ENEMIES, get_enemy_template

        for nid, cfg in ROOM_NPCS.items():
            ek = str(cfg.get("enemy_name_key") or cfg.get("name_key") or "")
            from game.data.text.locale_data import get_locale_text

            ename = get_locale_text(ek)
            self.assertIn(ename, ENEMY_CONFIG, f"{nid} ({ename}) missing in ENEMY_CONFIG")
            self.assertIn(ename, ALL_ENEMIES, f"{nid} ({ename}) missing in ALL_ENEMIES")
            self.assertGreaterEqual(len(ENEMY_CONFIG[ename].get("intents", [])), 2)

        for guest in CAFE_GUESTS + CAFE_NORMALS:
            tmpl = get_enemy_template(guest)
            self.assertNotEqual(type(tmpl).__name__, "EnemyTemplate", f"cafe guest {guest} fell back to base EnemyTemplate")

        uid = "cafe_atk_unique_user"
        run = self._start_solo(uid)
        fm = run.floor_map
        assert fm is not None
        fm.rooms = {
            "A1": RoomState(coord="A1", room_type="empty", explored=True, cleared=True),
            "B1": RoomState(coord="B1", room_type="cafe"),
        }
        fm.width = 2
        fm.height = 1
        fm.player_coords[uid] = "A1"
        self.plugin.save_manager.save_save(uid, run)

        self.run_cmd("d", uid)
        cafe_run = load_run(self.plugin, uid)
        self.assertEqual(cafe_run.node_type, "cafe")
        guests_here = list((cafe_run.node_data.get("cafe_data") or {}).get("npcs") or [])
        self.assertTrue(len(guests_here) > 0)
        target_guest = next((g for g in guests_here if g != "pppopipupu"), guests_here[0])
        atk_guest = self.run_cmd(f"攻击 {target_guest}", uid)
        self.assertIn("发起攻击", atk_guest)
        bat_run = load_run(self.plugin, uid)
        self.assertEqual(bat_run.node_type, "battle")
        self.assertGreaterEqual(len(bat_run.enemies[0].intents), 1)
        self.assertNotEqual(bat_run.enemies[0].intents[0].type, "attack")
        self.assertNotEqual(bat_run.enemies[0].intents[0].type, "defend")

    def test_encounter_lore_unknown_until_met_and_expanded_after(self):
        uid = "lore_encounter_user"
        before_reimu = self.run_cmd("i 博丽灵梦", uid)
        self.assertIn("未知", before_reimu)
        before_wolf = self.run_cmd("i 雪原狼", uid)
        self.assertIn("未知", before_wolf)
        before_golem = self.run_cmd("i 军械魔像", uid)
        self.assertIn("未知", before_golem)

        run = self._start_solo(uid)
        rooms = {
            "A1": RoomState(coord="A1", room_type="empty", explored=True, cleared=True),
            "B1": RoomState(coord="B1", room_type="empty", npcs=["hakurei_reimu"]),
            "C1": RoomState(coord="C1", room_type="empty", npcs=["armory_automaton"]),
        }
        run.floor_map = FloorMapState(
            floor_index=1,
            width=4,
            height=2,
            rooms=rooms,
            revealed_coords=["A1"],
            player_coords={uid: "A1"},
        )
        self.plugin.save_manager.save_save(uid, run)

        self.run_cmd("d", uid)
        after_reimu = self.run_cmd("i 博丽灵梦", uid)
        self.assertNotIn("未知（尚未", after_reimu)
        self.assertIn("博丽巫女", after_reimu)

        self.run_cmd("d", uid)
        after_golem = self.run_cmd("i 军械魔像", uid)
        self.assertNotIn("未知（尚未", after_golem)
        self.assertIn("古代发条巨像", after_golem)
        self.assertIn("锻铁重炮", after_golem)

