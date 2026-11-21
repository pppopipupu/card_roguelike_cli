import re
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


    def test_class_switching_3a_lex_bar_and_action_cycle(self):
        out_cls = self.run_cmd("class")
        self.assertIn("蕾忍", out_cls)
        self.assertIn("3A + 蕾克拉", out_cls)

        self.run_cmd("start confirm")
        wiz_run = load_run(self.plugin, self.uid)
        self.assertEqual(wiz_run.player.max_hp, 50)
        self.run_cmd("1")
        _, wiz_run = self._enter_battle()
        self.assertEqual(wiz_run.player.actions, 2)
        self.assertEqual(wiz_run.player.bonus_actions, 1)
        self.assertNotIn("Lex", render_battle(wiz_run))

        self.run_cmd("abandon confirm")
        self.run_cmd("class ninja")
        self.run_cmd("start confirm")
        ninja_run = load_run(self.plugin, self.uid)
        self.assertEqual(ninja_run.player.selected_class, "蕾忍")
        self.assertEqual(ninja_run.player.max_hp, 40)
        self.assertIn("lotus_box", ninja_run.player.relics)
        self.run_cmd("1")

        _, ninja_run = self._enter_battle()
        self.assertEqual(ninja_run.player.actions, 3)
        self.assertEqual(ninja_run.player.bonus_actions, 0)
        self.assertEqual(ninja_run.player.lex_kela, 2)
        ninja_view = render_battle(ninja_run)
        self.assertIn("3A 2Lex", ninja_view)
        self.assertIn("🥷", ninja_view)

    def test_darkness_snake_hand_scrambles_costs_and_dynamic_cost_cards(self):
        self.run_cmd("class ninja")
        self.run_cmd("start confirm")
        self.run_cmd("1")
        _, run = self._enter_battle()
        for e in run.enemies:
            e.hp = 200
            e.max_hp = 200
        run.player.hand = [
            CardState(id="ninja_darkness_snake_hand"),
            CardState(id="ninja_strike"),
            CardState(id="ninja_defend"),
        ]
        run.player.draw_pile = [CardState(id="ninja_strike") for _ in range(6)]
        run.player.actions = 3
        self.plugin.save_manager.save_save(self.uid, run)

        out = self.run_cmd("p 1")
        self.assertNotIn("❌", out)
        self.assertIn("打乱了当前所有手牌", out)
        run = load_run(self.plugin, self.uid)
        self.assertTrue(len(run.player.hand) >= 5)
        self.assertTrue(all(st.temp_cost_a is not None and 0 <= st.temp_cost_a <= 3 for st in run.player.hand))

        run.player.hand = [CardState(id="ninja_go_back_hands")]
        run.player.discard_pile = [CardState(id="ninja_sand_defend_hand")]
        run.player.actions = 3
        run.player.lex_kela = 2
        self.plugin.save_manager.save_save(self.uid, run)

        self.run_cmd("p 1")
        run = load_run(self.plugin, self.uid)
        returned = next((st for st in run.player.hand if st.id == "ninja_sand_defend_hand"), None)
        assert returned is not None
        self.assertEqual(returned.temp_cost_a, 0)

    def test_hamood_kill_all_blasts_teammates_and_enemies_in_coop(self):
        uid_a, uid_b = "hamood_a", "hamood_b"
        self.run_cmd("class ninja", uid_a)
        self.run_cmd("class wizard", uid_b)
        for u in (uid_a, uid_b):
            st = self.plugin.save_manager.load_stats(u)
            st.gp = 5000
            self.plugin.save_manager.save_stats(u, st)
        self.run_cmd("friend name 哈姆队长", uid_a)
        self.run_cmd("friend name 哈姆队员", uid_b)
        st_a = self.plugin.save_manager.load_stats(uid_a)
        st_b = self.plugin.save_manager.load_stats(uid_b)
        handle_a = st_a.player_handle or st_a.player_name
        handle_b = st_b.player_handle or st_b.player_name
        self.run_cmd(f"friend add {handle_b}", uid_a)
        self.run_cmd(f"friend accept {handle_a}", uid_b)
        created = self.run_cmd("team create", uid_a)
        m = re.search(r"队伍 ([A-Z0-9]{6})", created)
        assert m is not None
        code = m.group(1)
        self.run_cmd(f"friend invite {handle_b}", uid_a)
        self.run_cmd(f"team join {code}", uid_b)
        self.run_cmd("team ready", uid_b)
        self.run_cmd("team start", uid_a)
        self.run_cmd("c 1", uid_a)
        self.run_cmd("c 1", uid_b)

        run_a = load_run(self.plugin, uid_a)
        fm = floor_of(run_a)
        boss_coord = fm.boss_coord
        fm.rooms[boss_coord].explored = True
        if boss_coord not in fm.revealed_coords:
            fm.revealed_coords.append(boss_coord)
        self.plugin.save_manager.save_save(uid_a, run_a)
        self.run_cmd(f"tp {boss_coord}", uid_a)

        run_a = load_run(self.plugin, uid_a)
        self.assertEqual(run_a.node_type, "battle")
        run_a.players[uid_a].hand = [CardState(id="ninja_hamood_kill_all")]
        run_a.players[uid_b].max_hp = 1200
        run_a.players[uid_b].hp = 1200
        for e in run_a.enemies:
            e.hp = 1500
            e.max_hp = 1500
        self.plugin.save_manager.save_save(uid_a, run_a)

        end_out = self.run_cmd("e", uid_a)
        self.assertIn("999", end_out)
        after = load_run(self.plugin, uid_a)
        self.assertEqual(after.players[uid_a].hp, 0)
        self.assertEqual(after.players[uid_b].hp, 201)
        self.assertLessEqual(after.enemies[0].hp, 501)



    def test_evil_twin_summon_chaotic_attacks_and_battle_end_cleanup(self):
        from game.core.party.mercenary import list_chaotic_targets
        from game.models.state import MinionState

        self.run_cmd("class ninja")
        self.run_cmd("start confirm")
        self.run_cmd("1")
        _, run = self._enter_battle()
        for e in run.enemies:
            e.hp = 300
            e.max_hp = 300
        run.player.hp = 100
        run.player.max_hp = 100
        run.player.deck = [CardState(id="ninja_strike") for _ in range(8)]
        run.player.hand = [CardState(id="ninja_evil_twin")]
        run.player.actions = 3
        run.player.minions["1"] = MinionState(id="test_m", name="测试随从", hp=50, max_hp=50, atk=5, actions=1, bonus_actions=0)
        self.plugin.save_manager.save_save(self.uid, run)

        out = self.run_cmd("p 1")
        self.assertNotIn("❌", out)
        self.assertIn("邪恶双生人", out)
        self.assertIn("a2", out)

        run = load_run(self.plugin, self.uid)
        self.assertEqual(run.player.actions, 2)
        self.assertEqual(len(run.party_order), 2)
        merc_uid = run.party_order[1]
        merc = run.players[merc_uid]
        self.assertTrue(merc.is_mercenary)
        self.assertEqual(merc.mercenary_id, "evil_twin")
        self.assertEqual(len(merc.deck), len(run.player.deck))

        chaotic_targets = list_chaotic_targets(run, merc_uid)
        self.assertIn("e1", chaotic_targets)
        self.assertIn("a1", chaotic_targets)
        self.assertIn("a1m1", chaotic_targets)

        pre_enemy_hp = run.enemies[0].hp
        pre_owner_hp = run.player.hp
        pre_minion_hp = run.player.minions["1"].hp
        end_out = self.run_cmd("e")
        self.assertIn("邪恶双生人", end_out)

        run = load_run(self.plugin, self.uid)
        total_dmg_dealt = (
            (pre_enemy_hp - run.enemies[0].hp)
            + (pre_owner_hp - run.player.hp)
            + (pre_minion_hp - (run.player.minions["1"].hp if "1" in run.player.minions else 0))
        )
        self.assertGreater(total_dmg_dealt, 0)

        for e in run.enemies:
            e.hp = 1
        run.player.hand = [CardState(id="ninja_yi_cut")]
        run.player.actions = 3
        run.player.lex_kela = 2
        self.plugin.save_manager.save_save(self.uid, run)
        self.run_cmd("p 1 e1")

        after_win = load_run(self.plugin, self.uid)
        self.assertNotEqual(after_win.node_type, "battle")
        self.assertNotIn(merc_uid, after_win.players)
        self.assertNotIn(merc_uid, after_win.party_order)

if __name__ == "__main__":
    unittest.main()
