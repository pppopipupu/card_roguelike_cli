import asyncio
import random
import tempfile
import unittest

from game.entities import ALL_CARDS
from game.models.state import CardState
from game.test.core.base import CorePlugin, floor_of, load_run, move_to_room, run_command


class TestKappaAndPancakeEvents(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20261124)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, cmd, sender_id=uid))

    def _start_solo(self, uid: str) -> None:
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)

    def _enter_forced_event(self, uid: str, event_id: str) -> str:
        run = load_run(self.plugin, uid)
        fm = floor_of(run)
        coord = next((c for c, r in fm.rooms.items() if r.room_type == "event"), None)
        if coord is None:
            for c, r in fm.rooms.items():
                if r.room_type == "empty":
                    r.room_type = "event"
                    coord = c
                    break
        assert coord is not None
        fm.rooms[coord].shared_payload["event_id"] = event_id
        fm.rooms[coord].explored = True
        if coord not in fm.revealed_coords:
            fm.revealed_coords.append(coord)
        self.plugin.save_manager.save_save(uid, run)
        return self.run_cmd(f"tp {coord}", uid)

    def test_kappa_invention_three_step_custom_science_device_and_battle_use(self):
        uid = "kappa_u"
        self._start_solo(uid)
        ev_out = self._enter_forced_event(uid, "kappa_invention")
        self.assertIn("河童技师", ev_out)
        self.assertEqual(load_run(self.plugin, uid).node_type, "event")

        step2 = self.run_cmd("c 1", uid)
        self.assertIn("附加组件", step2)
        self.assertEqual(load_run(self.plugin, uid).node_type, "event")

        step3 = self.run_cmd("c 1", uid)
        self.assertIn("供能方案", step3)
        self.assertEqual(load_run(self.plugin, uid).node_type, "event")

        done = self.run_cmd("c 3", uid)
        self.assertIn("科学装置", done)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "grid_map")
        devices = [c for c in run.player.deck if c.id == "science_device"]
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].custom_spec, "arc|poison|overload")

        card_obj = ALL_CARDS[devices[0]]
        self.assertEqual(card_obj.cost_a, 2)
        self.assertEqual(card_obj.base_dmg, 12)
        self.assertIn("闪电伤害", card_obj.desc)
        self.assertIn("中毒", card_obj.desc)
        self.assertIn("重放 1", card_obj.desc)

        _, b_run = move_to_room(self.plugin, uid, ("battle", "elite"))
        self.assertEqual(b_run.node_type, "battle")
        b_run.player.actions = 5
        b_run.player.hand = [devices[0]]
        b_run.enemies[0].hp = 100
        b_run.enemies[0].max_hp = 100
        self.plugin.save_manager.save_save(uid, b_run)

        play_out = self.run_cmd("p 1 e1", uid)
        self.assertIn("科学装置", play_out)
        after = load_run(self.plugin, uid)
        self.assertLess(after.enemies[0].hp, 100)
        poison_stacks = sum(b.stacks for b in after.enemies[0].buffs if b.id == "poison")
        self.assertGreaterEqual(poison_stacks, 6)

    def test_pancake_stack_event_and_strictly_ascending_cost_replay_combo(self):
        uid = "pancake_u"
        self._start_solo(uid)
        run0 = load_run(self.plugin, uid)
        hp_before = run0.player.hp
        ev_out = self._enter_forced_event(uid, "pancake_stack_event")
        self.assertIn("煎饼", ev_out)

        pick_out = self.run_cmd("c 2", uid)
        self.assertIn("煎饼叠高高", pick_out)
        run1 = load_run(self.plugin, uid)
        self.assertIn("pancake_stack", run1.player.relics)
        self.assertEqual(run1.player.hp, max(1, hp_before - 10))

        _, b_run = move_to_room(self.plugin, uid, ("battle", "elite"))
        self.assertEqual(b_run.node_type, "battle")
        b_run.player.actions = 10
        b_run.player.shield = 0
        b_run.enemies[0].hp = 300
        b_run.enemies[0].max_hp = 300
        b_run.player.hand = [
            CardState(id="neutral_hero_anthem"),
            CardState(id="magic_missile"),
            CardState(id="science_device", custom_spec="arc|draw|overload"),
            CardState(id="magic_missile"),
        ]
        self.plugin.save_manager.save_save(uid, b_run)

        self.run_cmd("p 1", uid)
        r1 = load_run(self.plugin, uid)
        combo1 = next((b.stacks for b in r1.player.buffs if b.id == "pancake_stack_combo"), 0)
        self.assertEqual(combo1, 1)

        hp_before_1a = r1.enemies[0].hp
        out_1a = self.run_cmd("p 1 e1", uid)
        self.assertIn("获得重放 1", out_1a)
        r2 = load_run(self.plugin, uid)
        combo2 = next((b.stacks for b in r2.player.buffs if b.id == "pancake_stack_combo"), 0)
        self.assertEqual(combo2, 2)
        dmg_1a = hp_before_1a - r2.enemies[0].hp
        self.assertGreaterEqual(dmg_1a, 18)

        hp_before_2a = r2.enemies[0].hp
        out_2a = self.run_cmd("p 1 e1", uid)
        self.assertIn("获得重放 2", out_2a)
        r3 = load_run(self.plugin, uid)
        combo3 = next((b.stacks for b in r3.player.buffs if b.id == "pancake_stack_combo"), 0)
        self.assertEqual(combo3, 3)
        self.assertGreaterEqual(hp_before_2a - r3.enemies[0].hp, 36)

        hp_before_break = r3.enemies[0].hp
        out_break = self.run_cmd("p 1 e1", uid)
        self.assertIn("连击中断", out_break)
        r4 = load_run(self.plugin, uid)
        combo4 = next((b.stacks for b in r4.player.buffs if b.id == "pancake_stack_combo"), 0)
        self.assertEqual(combo4, 0)
        self.assertEqual(hp_before_break - r4.enemies[0].hp, 9)
