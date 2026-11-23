import asyncio
import random
import re
import tempfile
import unittest
from unittest.mock import patch

from game.test.core.base import CorePlugin, floor_of, load_run, require_run, run_command


class TestDungeonNpcCrpgDialog(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20261123)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str = "crpg_test_user") -> str:
        return asyncio.run(run_command(self.plugin, cmd, uid))

    def _start_grid(self, uid: str, card_class: str | None = None):
        if card_class:
            self.run_cmd(f"class {card_class}", uid)
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        return require_run(load_run(self.plugin, uid))

    def _place_npc_in_cur_room(self, uid: str, npc_id: str):
        run = require_run(load_run(self.plugin, uid))
        fm = floor_of(run)
        coord = fm.player_coords[uid]
        room = fm.rooms[coord]
        room.npcs = [npc_id]
        room.defeated_npcs = []
        self.plugin.save_manager.save_save(uid, run)
        return coord

    def _option_lines(self, screen_text: str) -> list[str]:
        return [line.strip() for line in screen_text.splitlines() if re.match(r"^\s*\[\d+\]", line)]

    def _find_option_idx(self, screen_text: str, keyword: str) -> int:
        for line in self._option_lines(screen_text):
            if keyword in line:
                m = re.match(r"^\[(\d+)\]", line)
                if m:
                    return int(m.group(1))
        raise AssertionError(f"Missing option containing {keyword!r} in:\n{screen_text}")

    def test_pure_action_options_and_hidden_attitude(self):
        uid = "crpg_purity_user"
        self._start_grid(uid)
        self._place_npc_in_cur_room(uid, "wandering_smith")

        out = self.run_cmd("talk 托林", uid)
        for forbidden in ("好感", "态度", "友善", "警惕", "厌恶", "信赖", "中立"):
            self.assertNotIn(forbidden, out)
        options = self._option_lines(out)
        self.assertGreaterEqual(len(options), 3)
        for line in options:
            for spoiler in ("(+", "(-", "免费", "奖励", "上限", "回血", "（", "("):
                self.assertNotIn(spoiler, line)
        self.assertIn("[离开]", options[-1])

    def test_dynamic_check_tier_scaling_fail_forward_and_single_attempt_lock(self):
        uid = "crpg_check_user"
        self._start_grid(uid, card_class="战士")
        run = require_run(load_run(self.plugin, uid))
        run.player.gold = 200
        run.player.bag_items.append("rusty_pickaxe")
        self.plugin.save_manager.save_save(uid, run)
        self._place_npc_in_cur_room(uid, "wandering_smith")

        root_view = self.run_cmd("talk 托林", uid)
        svc_idx = self._find_option_idx(root_view, "能接什么活计")
        svc_view_before = self.run_cmd(f"c {svc_idx}", uid)
        haggle_line_before = [l for l in self._option_lines(svc_view_before) if "讨价" in l or "通融" in l][0]
        self.assertIn("[讨价 · 中等]", haggle_line_before)

        back_idx = self._find_option_idx(svc_view_before, "回到刚才")
        return_view = self.run_cmd(f"c {back_idx}", uid)
        craft_idx = self._find_option_idx(return_view, "整座铁砧")
        craft_view = self.run_cmd(f"c {craft_idx}", uid)
        warrior_idx = self._find_option_idx(craft_view, "[战士]")
        svc_view_after = self.run_cmd(f"c {warrior_idx}", uid)
        haggle_line_after = [l for l in self._option_lines(svc_view_after) if "讨价" in l or "通融" in l][0]
        self.assertIn("[讨价 · 简单]", haggle_line_after)
        bellows_idx = self._find_option_idx(svc_view_after, "风箱")
        svc_view_after = self.run_cmd(f"c {bellows_idx}", uid)
        pickaxe_idx = self._find_option_idx(svc_view_after, "矿镐")
        svc_view_after = self.run_cmd(f"c {pickaxe_idx}", uid)
        back_idx2 = self._find_option_idx(svc_view_after, "回到刚才")
        ret_view2 = self.run_cmd(f"c {back_idx2}", uid)
        q_ask = self.run_cmd(f"c {self._find_option_idx(ret_view2, '需要搭手')}", uid)
        q_acc = self.run_cmd(f"c {self._find_option_idx(q_ask, '试出成色')}", uid)
        self.run_cmd(f"c {self._find_option_idx(q_acc, '[离开]')}", uid)

        auto_uid = "crpg_auto_pass_user"
        self._start_grid(auto_uid)
        run_a = require_run(load_run(self.plugin, auto_uid))
        run_a.player.gold = 200
        self.plugin.save_manager.save_save(auto_uid, run_a)
        self._place_npc_in_cur_room(auto_uid, "hakurei_reimu")
        reimu_view = self.run_cmd("talk 灵梦", auto_uid)
        self.assertIn("[说服 · 困难]", reimu_view)
        for _ in range(3):
            reimu_view = self.run_cmd(f"c {self._find_option_idx(reimu_view, '赛钱箱')}", auto_uid)
            if "[免检定]" in reimu_view:
                break
            if "回到" in reimu_view or "[离开]" in reimu_view:
                break
        if "[免检定]" not in reimu_view:
            with patch("game.core.world.rooms.dialog.checks.random.randint", return_value=18):
                beg_out = self.run_cmd(f"c {self._find_option_idx(reimu_view, '护身驱邪')}", auto_uid)
                self.assertIn("检定成功", beg_out)

        fail_uid = "crpg_check_fail_user"
        self._start_grid(fail_uid)
        run_f = require_run(load_run(self.plugin, fail_uid))
        run_f.player.gold = 200
        self.plugin.save_manager.save_save(fail_uid, run_f)
        self._place_npc_in_cur_room(fail_uid, "wandering_smith")

        root_f = self.run_cmd("talk 托林", fail_uid)
        svc_f = self.run_cmd(f"c {self._find_option_idx(root_f, '能接什么活计')}", fail_uid)
        self.assertIn("[讨价 · 困难]", svc_f)
        haggle_f_idx = self._find_option_idx(svc_f, "讨价")
        with patch("game.core.world.rooms.dialog.checks.random.randint", return_value=1):
            fail_out = self.run_cmd(f"c {haggle_f_idx}", fail_uid)
        self.assertIn("大失败", fail_out)
        self.assertIn("[花费 30 金币]", fail_out)
        self.assertFalse(any("讨价" in l for l in self._option_lines(fail_out)))

    def test_multi_turn_exclusive_exhausted_recap_and_facility_locks(self):
        uid = "crpg_exhaust_user"
        self._start_grid(uid)
        run = require_run(load_run(self.plugin, uid))
        run.player.gold = 300
        self.plugin.save_manager.save_save(uid, run)
        self._place_npc_in_cur_room(uid, "shrine_keeper")

        view = self.run_cmd("talk 守坛人", uid)
        quest_idx = self._find_option_idx(view, "执念")
        q_offer = self.run_cmd(f"c {quest_idx}", uid)
        q_acc = self._find_option_idx(q_offer, "记下")
        view = self.run_cmd(f"c {q_acc}", uid)

        oath_idx = self._find_option_idx(view, "古老誓约")
        oath_view = self.run_cmd(f"c {oath_idx}", uid)
        self.assertEqual(len(self._option_lines(oath_view)), 2)
        revere_idx = self._find_option_idx(oath_view, "仍须有人")
        ritual_view = self.run_cmd(f"c {revere_idx}", uid)

        bless_idx = self._find_option_idx(ritual_view, "[消耗")
        ritual_view = self.run_cmd(f"c {bless_idx}", uid)
        relic_idx = self._find_option_idx(ritual_view, "奉上香炉")
        exhausted_view = self.run_cmd(f"c {relic_idx}", uid)
        if "回到刚才" in exhausted_view:
            exhausted_view = self.run_cmd(f"c {self._find_option_idx(exhausted_view, '回到刚才')}", uid)

        self.assertIn("[回顾]", exhausted_view)
        self.assertIn("[离开]", exhausted_view)
        self.assertTrue(all(("[回顾]" in l or "[离开]" in l) for l in self._option_lines(exhausted_view)))
        self.run_cmd(f"c {self._find_option_idx(exhausted_view, '[离开]')}", uid)

        sp_before = require_run(load_run(self.plugin, uid)).player.sp
        gold_before = require_run(load_run(self.plugin, uid)).player.gold
        bag_before = len(require_run(load_run(self.plugin, uid)).player.bag_items)

        re_talk = self.run_cmd("talk 守坛人", uid)
        self.assertTrue(all(("[回顾]" in l or "[离开]" in l) for l in self._option_lines(re_talk)))
        self.assertIn("[回顾]", re_talk)
        self.assertIn("[离开]", re_talk)
        recap_out = self.run_cmd(f"c {self._find_option_idx(re_talk, '[回顾]')}", uid)
        self.assertIn("既有记录", recap_out)
        self.run_cmd(f"c {self._find_option_idx(recap_out, '[离开]')}", uid)

        run_after = require_run(load_run(self.plugin, uid))
        self.assertEqual(run_after.player.sp, sp_before)
        self.assertEqual(run_after.player.gold, gold_before)
        self.assertEqual(len(run_after.player.bag_items), bag_before)

        shop_uid = "crpg_shop_lock_user"
        self._start_grid(shop_uid)
        r_s = require_run(load_run(self.plugin, shop_uid))
        fm_s = floor_of(r_s)
        sc = next(c for c, rm in fm_s.rooms.items() if rm.room_type == "shop")
        if sc not in fm_s.revealed_coords:
            fm_s.revealed_coords.append(sc)
        self.plugin.save_manager.save_save(shop_uid, r_s)
        self.run_cmd(f"tp {sc}", shop_uid)
        shop_dlg = self.run_cmd("talk 维克多", shop_uid)
        gold_s0 = require_run(load_run(self.plugin, shop_uid)).player.gold
        ext_idx = self._find_option_idx(shop_dlg, "闹事")
        with patch("game.core.world.rooms.shop_dialog.random.random", return_value=0.0):
            ext1 = self.run_cmd(f"c {ext_idx}", shop_uid)
        self.assertIn("乖乖塞给你", ext1)
        gold_s1 = require_run(load_run(self.plugin, shop_uid)).player.gold
        self.assertGreater(gold_s1, gold_s0)
        ext2 = self.run_cmd(f"c {ext_idx}", shop_uid)
        self.assertIn("别想再讹第二次", ext2)
        self.assertEqual(require_run(load_run(self.plugin, shop_uid)).player.gold, gold_s1)

    def test_smith_deferred_cost_and_cancel_refund_guarantee(self):
        uid = "crpg_smith_defer_user"
        self._start_grid(uid)
        run = require_run(load_run(self.plugin, uid))
        run.player.gold = 100
        self.plugin.save_manager.save_save(uid, run)
        self._place_npc_in_cur_room(uid, "wandering_smith")

        root_view = self.run_cmd("talk 托林", uid)
        svc_view = self.run_cmd(f"c {self._find_option_idx(root_view, '能接什么活计')}", uid)
        forge_idx = self._find_option_idx(svc_view, "回火")
        up_view = self.run_cmd(f"c {forge_idx}", uid)
        self.assertTrue(require_run(load_run(self.plugin, uid)).node_data.get("pending_upgrade"))
        self.assertEqual(require_run(load_run(self.plugin, uid)).player.gold, 100)

        resumed = self.run_cmd("c cancel", uid)
        self.assertEqual(require_run(load_run(self.plugin, uid)).node_type, "room_dialog")
        self.assertFalse(require_run(load_run(self.plugin, uid)).node_data.get("pending_upgrade"))
        self.assertEqual(require_run(load_run(self.plugin, uid)).player.gold, 100)
        self.assertIn("回火", resumed)

        gem_idx = self._find_option_idx(resumed, "宝石")
        self.run_cmd(f"c {gem_idx}", uid)
        self.assertEqual(require_run(load_run(self.plugin, uid)).node_type, "gem_insert")
        resumed_gem = self.run_cmd("c cancel", uid)
        self.assertEqual(require_run(load_run(self.plugin, uid)).node_type, "room_dialog")
        self.assertEqual(require_run(load_run(self.plugin, uid)).player.gold, 100)
        self.assertIn("宝石", resumed_gem)

    def test_non_lethal_spar_execution_confirm_and_ancient_cycle_revival(self):
        uid_loss = "crpg_spar_loss_user"
        self._start_grid(uid_loss)
        run_l = require_run(load_run(self.plugin, uid_loss))
        run_l.player.hp = 1
        run_l.player.shield = 0
        run_l.player.hand = []
        run_l.player.draw_pile = []
        run_l.player.discard_pile = []
        self.plugin.save_manager.save_save(uid_loss, run_l)
        self._place_npc_in_cur_room(uid_loss, "wandering_smith")

        self.run_cmd("atk 托林", uid_loss)
        end_out = ""
        for _ in range(6):
            r_cur = require_run(load_run(self.plugin, uid_loss))
            if r_cur.node_type != "battle":
                break
            end_out = self.run_cmd("e", uid_loss)
        r_post_loss = require_run(load_run(self.plugin, uid_loss))
        self.assertEqual(r_post_loss.node_type, "room_dialog")
        self.assertEqual(r_post_loss.player.hp, 1)
        self.assertEqual(r_post_loss.node_data.get("node_id"), "spar_player_lost")
        leave_idx = self._find_option_idx(end_out, "[离开]")
        self.run_cmd(f"c {leave_idx}", uid_loss)
        self.assertEqual(require_run(load_run(self.plugin, uid_loss)).node_type, "grid_map")

        uid_win = "crpg_spar_win_user"
        self._start_grid(uid_win, card_class="战士")
        run_w = require_run(load_run(self.plugin, uid_win))
        run_w.player.max_hp = 999
        run_w.player.hp = 999
        self.plugin.save_manager.save_save(uid_win, run_w)
        coord_w = self._place_npc_in_cur_room(uid_win, "hakurei_reimu")

        talk_r = self.run_cmd("talk 灵梦", uid_win)
        provoke_idx = self._find_option_idx(talk_r, "结界")
        self.run_cmd(f"c {provoke_idx}", uid_win)
        for _ in range(160):
            cur = require_run(load_run(self.plugin, uid_win))
            if cur.node_type != "battle":
                break
            if cur.node_data.get("state_stack"):
                self.run_cmd("选择 1", uid_win)
                continue
            played = False
            for idx in range(1, len(cur.player.hand) + 1):
                res = self.run_cmd(f"p {idx} 1", uid_win)
                if "[FAIL]" not in res and "❌" not in res:
                    played = True
                    break
            if not played:
                self.run_cmd("e", uid_win)
        st_yield = self.run_cmd("status", uid_win)
        self.assertIn("到此为止", st_yield)
        spare_out = self.run_cmd(f"c {self._find_option_idx(st_yield, '到此为止')}", uid_win)
        self.assertIn("缓和", spare_out)
        self.run_cmd(f"c {self._find_option_idx(spare_out, '[离开]')}", uid_win)
        r_spared = require_run(load_run(self.plugin, uid_win))
        self.assertEqual(r_spared.node_type, "grid_map")
        self.assertNotIn("hakurei_reimu", floor_of(r_spared).rooms[coord_w].defeated_npcs)

        self.run_cmd("atk 灵梦", uid_win)
        for _ in range(160):
            cur = require_run(load_run(self.plugin, uid_win))
            if cur.node_type != "battle":
                break
            if cur.node_data.get("state_stack"):
                self.run_cmd("选择 1", uid_win)
                continue
            played = False
            for idx in range(1, len(cur.player.hand) + 1):
                res = self.run_cmd(f"p {idx} 1", uid_win)
                if "[FAIL]" not in res and "❌" not in res:
                    played = True
                    break
            if not played:
                self.run_cmd("e", uid_win)
        st_yield2 = self.run_cmd("status", uid_win)
        exec_ask = self.run_cmd(f"c {self._find_option_idx(st_yield2, '了结')}", uid_win)
        self.assertIn("先古循环", exec_ask)
        exec_done = self.run_cmd(f"c {self._find_option_idx(exec_ask, '确认')}", uid_win)
        self.assertIsInstance(exec_done, str)
        if require_run(load_run(self.plugin, uid_win)).node_type == "reward":
            self.run_cmd("离开", uid_win)
        r_dead = require_run(load_run(self.plugin, uid_win))
        self.assertIn("hakurei_reimu", floor_of(r_dead).rooms[coord_w].defeated_npcs)

        self.run_cmd("giveup confirm", uid_win)
        self._start_grid(uid_win)
        self._place_npc_in_cur_room(uid_win, "hakurei_reimu")
        revived_view = self.run_cmd("talk 灵梦", uid_win)
        self.assertIn("先古循环", revived_view)
        truth_out = self.run_cmd(f"c {self._find_option_idx(revived_view, '先古循环')}", uid_win)
        self.assertIn("永远没法真正杀死彼此", truth_out)

    def test_single_and_cross_run_quests_progression(self):
        uid = "crpg_quest_user"
        self._start_grid(uid)
        self._place_npc_in_cur_room(uid, "hakurei_reimu")

        talk_r = self.run_cmd("talk 灵梦", uid)
        q_idx = self._find_option_idx(talk_r, "境界是不是")
        after_acc = self.run_cmd(f"c {q_idx}", uid)
        self.assertIn("境界异变调查", after_acc)
        rumor_idx = self._find_option_idx(after_acc, "控制中心")
        after_rumor = self.run_cmd(f"c {rumor_idx}", uid)
        self.run_cmd(f"c {self._find_option_idx(after_rumor, '[离开]')}", uid)

        q_view = self.run_cmd("quest", uid)
        self.assertIn("境界缝隙的异常回响", q_view)
        self.assertIn("1/3", q_view)

        self.run_cmd("giveup confirm", uid)
        self._start_grid(uid)
        q_view_new_run = self.run_cmd("quest", uid)
        self.assertIn("境界缝隙的异常回响", q_view_new_run)
        self.assertIn("1/3", q_view_new_run)

        single_uid = "crpg_single_quest_user"
        self._start_grid(single_uid)
        smith_coord = self._place_npc_in_cur_room(single_uid, "wandering_smith")
        s_run = require_run(load_run(self.plugin, single_uid))
        s_fm = floor_of(s_run)
        col_ch, row_str = smith_coord[0], smith_coord[1:]
        row_num = int(row_str)
        adj_candidates = [
            ("d", f"{chr(ord(col_ch) + 1)}{row_num}"),
            ("a", f"{chr(ord(col_ch) - 1)}{row_num}"),
            ("s", f"{col_ch}{row_num + 1}"),
            ("w", f"{col_ch}{row_num - 1}"),
        ]
        exit_dir, adj_coord = next(
            (d, c) for d, c in adj_candidates if c in s_fm.rooms and s_fm.rooms[c].room_type not in ("boss", "start")
        )
        s_fm.rooms[adj_coord].room_type = "obstacle"
        s_fm.rooms[adj_coord].cleared = False
        s_run.player.bag_items.append("rusty_pickaxe")
        self.plugin.save_manager.save_save(single_uid, s_run)

        t_view = self.run_cmd("talk 托林", single_uid)
        q_offer = self.run_cmd(f"c {self._find_option_idx(t_view, '需要搭手')}", single_uid)
        q_acc = self.run_cmd(f"c {self._find_option_idx(q_offer, '试出成色')}", single_uid)
        self.run_cmd(f"c {self._find_option_idx(q_acc, '[离开]')}", single_uid)

        q_before = self.run_cmd("quest", single_uid)
        self.assertIn("0/1", q_before)
        self.run_cmd(f"dig {exit_dir}", single_uid)
        q_ready = self.run_cmd("quest", single_uid)
        self.assertIn("交付", q_ready)
        if floor_of(require_run(load_run(self.plugin, single_uid))).player_coords[single_uid] != smith_coord:
            rev_map = {"w": "s", "s": "w", "a": "d", "d": "a"}
            self.run_cmd(rev_map[exit_dir], single_uid)
        turnin_view = self.run_cmd("talk 托林", single_uid)
        self.assertIn("试得不错", turnin_view)
        turnin_out = self.run_cmd(f"c {self._find_option_idx(turnin_view, '结下这单')}", single_uid)
        if require_run(load_run(self.plugin, single_uid)).node_data.get("pending_upgrade"):
            self.run_cmd("c cancel", single_uid)
        q_done = self.run_cmd("quest", single_uid)
        self.assertIn("完成", q_done)

    def test_coop_two_players_isolated_dialog_memory(self):
        uid1 = "crpg_coop_p1"
        uid2 = "crpg_coop_p2"
        from game.data.progression.account_config import RENAME_COST_GP
        for u in (uid1, uid2):
            st = self.plugin.save_manager.load_stats(u)
            st.gp = max(st.gp, RENAME_COST_GP)
            self.plugin.save_manager.save_stats(u, st)
        self.run_cmd("friend name 队友甲", uid1)
        self.run_cmd("friend name 队友乙", uid2)
        s1 = self.plugin.save_manager.load_stats(uid1)
        s2 = self.plugin.save_manager.load_stats(uid2)
        pid1 = s1.player_handle or s1.player_name
        pid2 = s2.player_handle or s2.player_name
        self.run_cmd(f"friend add {pid2}", uid1)
        self.run_cmd(f"friend accept {pid1}", uid2)
        created = self.run_cmd("team create", uid1)
        m = re.search(r"队伍 ([A-Z0-9]{6})", created)
        assert m is not None
        lobby_id = m.group(1)
        self.run_cmd(f"friend invite {pid2}", uid1)
        self.run_cmd(f"team join {lobby_id}", uid2)
        self.run_cmd("team ready", uid2)
        self.run_cmd("team start", uid1)
        self.run_cmd("c 1", uid1)
        self.run_cmd("c 1", uid2)

        run1 = require_run(load_run(self.plugin, uid1))
        fm = floor_of(run1)
        coord1 = fm.player_coords[uid1]
        fm.player_coords[uid2] = coord1
        fm.rooms[coord1].npcs = ["wandering_smith"]
        fm.rooms[coord1].defeated_npcs = []
        self.plugin.save_manager.save_save(uid1, run1)

        p1_root = self.run_cmd("talk 托林", uid1)
        p1_craft = self.run_cmd(f"c {self._find_option_idx(p1_root, '整座铁砧')}", uid1)
        p1_svc = self.run_cmd(f"c {self._find_option_idx(p1_craft, '蓝焰')}", uid1)
        self.assertEqual(require_run(load_run(self.plugin, uid1)).node_type, "room_dialog")
        self.assertIn("回火", p1_svc)

        p2_root = self.run_cmd("talk 托林", uid2)
        self.assertEqual(require_run(load_run(self.plugin, uid2)).node_type, "room_dialog")
        self.assertTrue(any("整座铁砧" in l for l in self._option_lines(p2_root)))
        self.run_cmd("leave", uid1)
        self.assertEqual(require_run(load_run(self.plugin, uid1)).node_type, "grid_map")
        self.assertEqual(require_run(load_run(self.plugin, uid2)).node_type, "room_dialog")
