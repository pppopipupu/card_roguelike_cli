import asyncio
import random
import tempfile
import unittest

from game.data.ninja_card_data import (
    NINJA_BUFF_CONFIG,
    NINJA_CARD_CONFIG,
    NINJA_RELIC_CONFIG,
    NINJA_UPGRADE_CONFIG,
)
from game.data.starting_deck_config import CLASS_BASE_HP, DEFAULT_BASE_HP
from game.entities import ALL_CARDS
from game.entities.cards.base import get_card_color_icon
from game.entities.events import ALL_EVENTS
from game.models.state import CardState
from game.renderer.battle import render_battle
from game.test.core.base import CorePlugin, floor_of, load_run, run_command


class TestNinjaClass(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20261120)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.uid = "ninja_u1"

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str | None = None) -> str:
        return asyncio.run(run_command(self.plugin, cmd, sender_id=uid or self.uid))

    def _enter_battle(self, uid: str | None = None):
        target_uid = uid or self.uid
        run = load_run(self.plugin, target_uid)
        fm = floor_of(run)
        coord = next((c for c, r in fm.rooms.items() if r.room_type == "battle"), None)
        if coord is None:
            for c, r in fm.rooms.items():
                if r.room_type == "empty":
                    r.room_type = "battle"
                    coord = c
                    break
        assert coord is not None
        fm.rooms[coord].explored = True
        if coord not in fm.revealed_coords:
            fm.revealed_coords.append(coord)
        self.plugin.save_manager.save_save(target_uid, run)
        out = self.run_cmd(f"tp {coord}", target_uid)
        return out, load_run(self.plugin, target_uid)

    

    def test_class_switching_base_hp_and_action_bar_rendering(self):
        out_cls = self.run_cmd("class")
        self.assertIn("蕾忍", out_cls)
        self.assertIn("初始生命 50", out_cls)

        self.run_cmd("start confirm")
        wiz_run = load_run(self.plugin, self.uid)
        self.assertEqual(wiz_run.player.max_hp, 50)
        self.assertEqual(wiz_run.player.hp, 50)
        self.run_cmd("1")
        _, wiz_run = self._enter_battle()
        wiz_view = render_battle(wiz_run)
        self.assertNotIn("Lex", wiz_view)

        self.run_cmd("abandon confirm")
        out_sw = self.run_cmd("class ninja")
        self.assertIn("蕾忍", out_sw)
        out_nosub = self.run_cmd("class 1")
        self.assertIn("没有子职业", out_nosub)

        self.run_cmd("start confirm")
        ninja_run = load_run(self.plugin, self.uid)
        self.assertEqual(ninja_run.player.selected_class, "蕾忍")
        self.assertEqual(ninja_run.player.max_hp, 40)
        self.assertEqual(ninja_run.player.hp, 40)
        self.assertIn("lotus_box", ninja_run.player.relics)
        self.run_cmd("1")

        _, ninja_run = self._enter_battle()
        self.assertEqual(ninja_run.player.lex_kela, 2)
        ninja_view = render_battle(ninja_run)
        self.assertIn("2Lex", ninja_view)
        self.assertIn("🥷", ninja_view)

    def test_lex_kela_cycle_science_discount_and_sand_wall(self):
        self.run_cmd("class ninja")
        self.run_cmd("start confirm")
        self.run_cmd("1")
        _, run = self._enter_battle()
        self.assertEqual(run.node_type, "battle")
        self.assertEqual(run.player.lex_kela, 2)

        for enemy in run.enemies:
            enemy.hp = 200
            enemy.max_hp = 200
        self.plugin.save_manager.save_save(self.uid, run)

        self.run_cmd("e")
        run = load_run(self.plugin, self.uid)
        self.assertEqual(run.player.lex_kela, 3)

        run.player.hand = [
            CardState(id="ninja_yi_cut"),
            CardState(id="ninja_mamba_missile"),
            CardState(id="ninja_sand_defend_hand"),
        ]
        run.player.actions = 2
        run.player.bonus_actions = 1
        self.plugin.save_manager.save_save(self.uid, run)

        out_yi = self.run_cmd("p 1 e1")
        self.assertNotIn("❌", out_yi)
        run = load_run(self.plugin, self.uid)
        self.assertEqual(run.player.lex_kela, 1)

        run.player.actions = 2
        self.plugin.save_manager.save_save(self.uid, run)
        out_sci = self.run_cmd("p 1 e1")
        self.assertNotIn("❌", out_sci)
        run = load_run(self.plugin, self.uid)
        self.assertEqual(run.player.lex_kela, 0)
        self.assertEqual(run.player.actions, 0)

        run.player.actions = 1
        run.player.lex_kela = 1
        self.plugin.save_manager.save_save(self.uid, run)
        out_sw = self.run_cmd("p 1")
        self.assertNotIn("❌", out_sw)
        run = load_run(self.plugin, self.uid)
        sw_before = next((b for b in run.player.buffs if b.id == "sand_wall"), None)
        assert sw_before is not None and sw_before.stacks == 6

        self.run_cmd("e")
        run = load_run(self.plugin, self.uid)
        self.assertEqual(run.player.lex_kela, 0)
        sw_buff = next((b for b in run.player.buffs if b.id == "sand_wall"), None)
        assert sw_buff is not None
        self.assertEqual(sw_buff.stacks, 3)


if __name__ == "__main__":
    unittest.main()
