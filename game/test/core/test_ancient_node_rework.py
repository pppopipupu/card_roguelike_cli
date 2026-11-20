import asyncio
import random
import tempfile
import unittest

from game.core.world.bleak_falls import enter_bleak_floor
from game.core.world.chireiden import enter_chireiden_elevator
from game.data.ancient_node_config import ANCIENT_DEITIES
from game.data.balance_config import MAP_ANCIENT_OPTION_SLOTS
from game.data.map_quest_config import BLEAK_FALLS_FLOOR_INDEX, BLEAK_SANCTUARY_FLOOR_INDEX
from game.entities import ALL_CARDS
from game.models.state import CardState
from game.test.core.base import CorePlugin, floor_of, load_run, run_command


class TestAncientNodeRework(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20261120)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.uid = "ancient_rework_u1"

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str | None = None) -> str:
        return asyncio.run(run_command(self.plugin, cmd, sender_id=uid or self.uid))

    def test_start_ancient_has_5_options_and_deity_banner(self):
        self.assertEqual(MAP_ANCIENT_OPTION_SLOTS, 5)
        self.assertEqual(len(ANCIENT_DEITIES), 5)
        out = self.run_cmd("start confirm")
        self.assertIn("降临神明", out)
        self.assertIn("五座石碑", out)
        run = load_run(self.plugin, self.uid)
        self.assertEqual(run.node_type, "start_ancient")
        self.assertEqual(len(run.node_data.get("options", [])), 5)
        self.assertIn(run.node_data.get("deity"), ANCIENT_DEITIES)

        pick_out = self.run_cmd("c 1")
        self.assertIn("契约达成", pick_out)
        run_after = load_run(self.plugin, self.uid)
        self.assertEqual(run_after.node_type, "grid_map")

    def test_downstairs_grants_5_choice_ancient_after_descending(self):
        self.run_cmd("start confirm")
        self.run_cmd("c 1")
        run = load_run(self.plugin, self.uid)
        fm = floor_of(run)
        ds_coord = fm.boss_coord
        ds_room = fm.rooms[ds_coord]
        ds_room.room_type = "downstairs"
        ds_room.cleared = False
        ds_room.explored = True
        fm.player_coords[self.uid] = ds_coord
        before_relics = len(run.player.relics)
        before_deck = len(run.player.deck)
        self.plugin.save_manager.save_save(self.uid, run)

        open_ds = self.run_cmd("talk .")
        self.assertNotIn("传奇卡牌", open_ds)
        ds_run = load_run(self.plugin, self.uid)
        self.assertEqual(ds_run.node_type, "downstairs")
        actions = [o.get("action") for o in ds_run.node_data.get("options", [])]
        self.assertNotIn("ancient_pick", actions)
        self.assertIn("downstairs_confirm", actions)

        descend_out = self.run_cmd("c 1")
        self.assertIn("第 2 层", descend_out)
        self.assertIn("降临神明", descend_out)
        floor2 = load_run(self.plugin, self.uid)
        self.assertEqual(floor_of(floor2).floor_index, 2)
        self.assertEqual(floor2.node_type, "ancient")
        self.assertEqual(len(floor2.node_data.get("options", [])), 5)
        self.assertEqual(len(floor2.player.relics), before_relics)
        self.assertEqual(len(floor2.player.deck), before_deck)

        bless_out = self.run_cmd("c 1")
        self.assertIn("先古赐福", bless_out)
        after_bless = load_run(self.plugin, self.uid)
        self.assertEqual(after_bless.node_type, "grid_map")
        self.assertEqual(len(after_bless.player.relics), before_relics + 1)
        self.assertEqual(len(after_bless.player.deck), before_deck + 1)

    def test_decimal_floors_open_ancient_as_first_node(self):
        self.run_cmd("start confirm")
        self.run_cmd("c 1")
        run = load_run(self.plugin, self.uid)

        out_15 = enter_bleak_floor(self.plugin.save_manager, self.plugin.engine.map_engine, run, BLEAK_FALLS_FLOOR_INDEX, "in_barrow")
        self.assertIn("降临神明", out_15)
        run_15 = load_run(self.plugin, self.uid)
        self.assertEqual(floor_of(run_15).floor_index, BLEAK_FALLS_FLOOR_INDEX)
        self.assertEqual(run_15.node_type, "ancient")
        self.assertEqual(len(run_15.node_data.get("options", [])), 5)
        self.run_cmd("c 1")
        self.assertEqual(load_run(self.plugin, self.uid).node_type, "grid_map")

        run_15_done = load_run(self.plugin, self.uid)
        enter_bleak_floor(self.plugin.save_manager, self.plugin.engine.map_engine, run_15_done, BLEAK_SANCTUARY_FLOOR_INDEX, "in_sanctuary")
        run_16 = load_run(self.plugin, self.uid)
        self.assertAlmostEqual(floor_of(run_16).floor_index, BLEAK_SANCTUARY_FLOOR_INDEX)
        self.assertEqual(run_16.node_type, "ancient")
        self.assertEqual(len(run_16.node_data.get("options", [])), 5)
        self.run_cmd("c 1")
        self.assertEqual(load_run(self.plugin, self.uid).node_type, "grid_map")

        run_35_src = load_run(self.plugin, self.uid)
        enter_chireiden_elevator(self.plugin.engine.map_engine, run_35_src, self.uid)
        self.plugin.save_manager.save_save(self.uid, run_35_src)
        run_35 = load_run(self.plugin, self.uid)
        self.assertAlmostEqual(floor_of(run_35).floor_index, 3.5)
        self.assertEqual(run_35.node_type, "ancient")
        self.assertEqual(len(run_35.node_data.get("options", [])), 5)

    def test_reworked_glacier_and_curse_mechanics(self):
        self.run_cmd("start confirm")
        self.run_cmd("c 1")
        run = load_run(self.plugin, self.uid)
        fm = floor_of(run)
        b_coord = next((c for c, r in fm.rooms.items() if r.room_type == "battle"), None)
        if b_coord is None:
            for c, r in fm.rooms.items():
                if r.room_type == "empty":
                    r.room_type = "battle"
                    b_coord = c
                    break
        assert b_coord is not None
        fm.rooms[b_coord].explored = True
        if b_coord not in fm.revealed_coords:
            fm.revealed_coords.append(b_coord)
        run.player.relics = ["glacier_chill", "wither_seed"]
        self.plugin.save_manager.save_save(self.uid, run)

        self.run_cmd(f"tp {b_coord}")
        run = load_run(self.plugin, self.uid)
        self.assertEqual(run.node_type, "battle")
        self.assertEqual(run.player.actions, 1)
        self.assertGreaterEqual(run.player.shield, 8)

        for e in run.enemies:
            e.hp = 120
            e.max_hp = 120
        self.plugin.save_manager.save_save(self.uid, run)

        self.run_cmd("e")
        run = load_run(self.plugin, self.uid)
        self.assertEqual(run.player.actions, 2)

        tempest_card = ALL_CARDS["glacier_tempest"]
        self.assertEqual(tempest_card.cost_a, 2)
        self.assertEqual(ALL_CARDS["glacier_tempest+"].cost_a, 1)

        run.player.hand = [CardState(id="glacier_tempest")]
        run.player.shield = 0
        run.player.minions.clear()
        self.plugin.save_manager.save_save(self.uid, run)

        play_out = self.run_cmd("p 1")
        self.assertNotIn("❌", play_out)
        run = load_run(self.plugin, self.uid)
        self.assertGreater(run.player.shield, 0)
        self.assertTrue(any(b.id == "minor_vulnerable_cold" for b in run.enemies[0].buffs))

        run.player.hp = 20
        self.plugin.engine.battle_engine.combat_resolver.heal_target(run, "p0", 6)
        self.assertEqual(run.player.hp, 23)


if __name__ == "__main__":
    unittest.main()
