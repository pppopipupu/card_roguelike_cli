import asyncio
import random
import tempfile
import unittest

from game.data.entities.enchantment_data import ENCHANTMENT_CONFIG
from game.entities import ALL_CARDS
from game.test.core.base import CorePlugin, floor_of, load_run, move_to_room, run_command


class TestCardEnchantments(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20261120)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, cmd, sender_id=uid))

    def _start_solo(self, uid: str) -> None:
        self.run_cmd("start confirm", uid)
        self.run_cmd("1", uid)

    def _enter_room_type(self, uid: str, target_type: str):
        run = load_run(self.plugin, uid)
        fm = floor_of(run)
        coord = next((c for c, r in fm.rooms.items() if r.room_type == target_type), None)
        if coord is None:
            for c, r in fm.rooms.items():
                if r.room_type == "empty":
                    r.room_type = target_type
                    coord = c
                    break
        assert coord is not None
        fm.rooms[coord].explored = True
        if coord not in fm.revealed_coords:
            fm.revealed_coords.append(coord)
        self.plugin.save_manager.save_save(uid, run)
        out = self.run_cmd(f"tp {coord}", uid)
        return out, load_run(self.plugin, uid)

    def test_rest_preview_reselect_and_confirm_enchant(self):
        uid = "ench_rest_u"
        self._start_solo(uid)
        _, run = self._enter_room_type(uid, "rest")
        self.assertEqual(run.node_type, "rest")

        open_out = self.run_cmd("c 4", uid)
        self.assertIn("卡牌附魔台", open_out)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "enchant_card")
        self.assertEqual(run.node_data.get("stage"), "choose_enchant")
        offers = list(run.node_data.get("offers") or [])
        self.assertEqual(len(offers), 3)

        choose_card_out = self.run_cmd("c 1", uid)
        self.assertIn("选择要附魔", choose_card_out)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_data.get("stage"), "choose_card")

        preview_out = self.run_cmd("c 1", uid)
        self.assertIn("附魔预览确认", preview_out)
        self.assertIn("附魔前", preview_out)
        self.assertIn("附魔后", preview_out)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_data.get("stage"), "confirm_preview")

        reselect_out = self.run_cmd("c 2", uid)
        self.assertIn("选择要附魔", reselect_out)
        self.run_cmd("c 1", uid)
        confirm_out = self.run_cmd("c 1", uid)
        self.assertIn("附魔成功", confirm_out)
        after_run = load_run(self.plugin, uid)
        self.assertEqual(after_run.node_type, "grid_map")
        chosen_eid = offers[0]
        self.assertTrue(any(chosen_eid in (c.enchantments or []) for c in after_run.player.deck))

    def test_shop_preview_cancel_and_confirm_enchant_with_gem_compat(self):
        uid = "ench_shop_u"
        self._start_solo(uid)
        _, run = self._enter_room_type(uid, "shop")
        self.assertEqual(run.node_type, "shop")
        self.run_cmd("c 1", uid)
        wares_out = self.run_cmd("c 1", uid)
        self.assertIn("附魔服务", wares_out)
        run = load_run(self.plugin, uid)
        run.player.gold = 300
        self.plugin.save_manager.save_save(uid, run)
        items = run.node_data.get("items", [])
        enchant_idx = next(i for i, it in enumerate(items, 1) if it.get("type") == "enchant")
        enchant_price = int(items[enchant_idx - 1]["price"])
        gold_before = run.player.gold
        self.assertGreaterEqual(gold_before, enchant_price)

        self.run_cmd(f"c {enchant_idx}", uid)
        self.run_cmd("c 1", uid)
        preview_out = self.run_cmd("c 1", uid)
        self.assertIn("确认附魔将消耗", preview_out)

        cancel_out = self.run_cmd("c 3", uid)
        self.assertIn("取消了本次附魔", cancel_out)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "shop")
        self.assertEqual(run.player.gold, gold_before)

        self.run_cmd(f"c {enchant_idx}", uid)
        chosen_eid = load_run(self.plugin, uid).node_data["offers"][0]
        self.run_cmd("c 1", uid)
        self.run_cmd("c 1", uid)
        confirm_out = self.run_cmd("c 1", uid)
        self.assertIn("附魔成功", confirm_out)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "shop")
        self.assertEqual(run.player.gold, gold_before - enchant_price)
        self.assertTrue(run.node_data["items"][enchant_idx - 1]["sold"])

        enchanted = next(c for c in run.player.deck if chosen_eid in (c.enchantments or []))
        card_obj = ALL_CARDS[enchanted]
        self.assertIn("[附魔:", card_obj.desc)
        deck_out = self.run_cmd("deck", uid)
        self.assertIn("[附魔:", deck_out)

    def test_echo_folding_and_gem_compatibility_and_starting_enchant_chance(self):
        uid = "ench_start_u"
        seen_with_ench = False
        seen_without_ench = False
        for i in range(16):
            u = f"{uid}_{i}"
            self._start_solo(u)
            run = load_run(self.plugin, u)
            ench_cards = [c for c in run.player.deck if c.enchantments]
            if ench_cards:
                seen_with_ench = True
                self.assertGreaterEqual(len(ench_cards), 1)
                self.assertLessEqual(len(ench_cards), 2)
            else:
                seen_without_ench = True
            self.run_cmd("abandon confirm", u)
            if seen_with_ench and seen_without_ench:
                break
        self.assertTrue(seen_with_ench)
        self.assertTrue(seen_without_ench)
        self.assertGreaterEqual(len(ENCHANTMENT_CONFIG), 50)

        from game.models.state import CardState
        base_card = ALL_CARDS[CardState(id="fire_bolt")]
        echo_twice_with_gem = CardState(id="fire_bolt", gems=["gem_dmg_add_2"], enchantments=["echo", "echo"])
        card_echo2 = ALL_CARDS[echo_twice_with_gem]
        self.assertEqual(card_echo2.name, base_card.name)
        self.assertIn("回响x2", card_echo2.desc)
        self.assertEqual(card_echo2.replay, 2)
        self.assertIn("红宝石", card_echo2.desc)

        brutal_card = ALL_CARDS[CardState(id="fire_bolt", enchantments=["brutal", "brutal"])]
        self.assertTrue(brutal_card.name.startswith("残暴"))
        self.assertNotIn("残暴残暴", brutal_card.name)
        self.assertIn("残暴x2", brutal_card.desc)

    def test_forced_event_enchant_altar(self):
        uid = "ench_event_u"
        self._start_solo(uid)
        run = load_run(self.plugin, uid)
        fm = floor_of(run)
        event_coords = [c for c, r in fm.rooms.items() if r.room_type == "event"]
        if not event_coords:
            for c, r in fm.rooms.items():
                if r.room_type == "empty":
                    r.room_type = "event"
                    event_coords.append(c)
                    break
        self.assertTrue(event_coords)
        for ec in event_coords:
            fm.rooms[ec].shared_payload["event_id"] = "enchant_altar"
        self.plugin.save_manager.save_save(uid, run)

        self._enter_room_type(uid, "event")
        ev_run = load_run(self.plugin, uid)
        self.assertEqual(ev_run.node_type, "event")
        self.assertEqual(ev_run.node_data.get("event_id"), "enchant_altar")
        res = self.run_cmd("c 1", uid)
        self.assertIn("回响", res)
        after = load_run(self.plugin, uid)
        self.assertEqual(after.node_type, "grid_map")
        self.assertTrue(any("echo" in (c.enchantments or []) for c in after.player.deck))


if __name__ == "__main__":
    unittest.main()
