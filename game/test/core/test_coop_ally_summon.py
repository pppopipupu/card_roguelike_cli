from game.test.core.base import floor_of, load_run, move_to_room
from game.test.core.coop_base import CoopTestBase


class TestCoopAllySummon(CoopTestBase):
    def test_solo_battle_summon_accept_teleports_and_joins_battle(self):
        uids = ["sum_acc_a", "sum_acc_b"]
        self.start_coop(uids)
        out, run_a = move_to_room(self.plugin, uids[0], ("battle",), rally=False)
        self.assertEqual(run_a.node_type, "ally_summon_select")
        self.assertIn("征召队友", out)
        battle_coord = floor_of(run_a).player_coords[uids[0]]
        sp_before = run_a.player.sp

        summon_out = self.run_cmd("c 2", uids[0])
        self.assertIn("发出战斗征召", summon_out)
        run_a_after = load_run(self.plugin, uids[0])
        self.assertEqual(run_a_after.node_type, "battle")
        self.assertEqual(run_a_after.player.sp, sp_before - 1)

        run_b = load_run(self.plugin, uids[1])
        self.assertEqual(run_b.node_type, "ally_summon_confirm")
        self.assertNotEqual(floor_of(run_b).player_coords[uids[1]], battle_coord)

        accept_out = self.run_cmd("c 1", uids[1])
        self.assertIn("接受了", accept_out)
        run_b_after = load_run(self.plugin, uids[1])
        self.assertEqual(run_b_after.node_type, "battle")
        self.assertEqual(floor_of(run_b_after).player_coords[uids[1]], battle_coord)
        self.assertEqual(
            floor_of(run_b_after).player_session_map[uids[0]],
            floor_of(run_b_after).player_session_map[uids[1]],
        )

        end_a = self.run_cmd("e", uids[0])
        self.assertIn("等待队友", end_a)
        end_b = self.run_cmd("e", uids[1])
        self.assertIn("进入第 2 回合", end_b)

    def test_solo_battle_summon_decline_refunds_sp_and_stays_in_place(self):
        uids = ["sum_dec_a", "sum_dec_b"]
        self.start_coop(uids)
        _, run_a = move_to_room(self.plugin, uids[0], ("battle",), rally=False)
        self.assertEqual(run_a.node_type, "ally_summon_select")
        sp_before = run_a.player.sp
        b_start_coord = floor_of(run_a).player_coords[uids[1]]

        self.run_cmd("c 2", uids[0])
        run_a_mid = load_run(self.plugin, uids[0])
        self.assertEqual(run_a_mid.player.sp, sp_before - 1)

        dec_out = self.run_cmd("c 2", uids[1])
        self.assertIn("拒绝了", dec_out)
        run_b_after = load_run(self.plugin, uids[1])
        self.assertEqual(run_b_after.node_type, "grid_map")
        self.assertEqual(floor_of(run_b_after).player_coords[uids[1]], b_start_coord)

        run_a_after = load_run(self.plugin, uids[0])
        self.assertEqual(run_a_after.node_type, "battle")
        self.assertEqual(run_a_after.player.sp, sp_before)

    def test_solo_battle_summon_solo_option_and_insufficient_sp(self):
        uids = ["sum_sp_a", "sum_sp_b"]
        self.start_coop(uids)
        _, run_a = move_to_room(self.plugin, uids[0], ("battle",), rally=False)
        self.assertEqual(run_a.node_type, "ally_summon_select")
        run_a.player.sp = 0
        self.plugin.save_manager.save_save(uids[0], run_a)

        err_out = self.run_cmd("c 2", uids[0])
        self.assertIn("体力不足", err_out)
        still_select = load_run(self.plugin, uids[0])
        self.assertEqual(still_select.node_type, "ally_summon_select")

        solo_out = self.run_cmd("c 1", uids[0])
        self.assertNotIn("❌", solo_out)
        run_a_battle = load_run(self.plugin, uids[0])
        self.assertEqual(run_a_battle.node_type, "battle")
        run_b = load_run(self.plugin, uids[1])
        self.assertEqual(run_b.node_type, "grid_map")
