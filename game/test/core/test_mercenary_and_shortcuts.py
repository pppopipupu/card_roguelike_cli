import asyncio
import os
import random
import re
import tempfile
import unittest

from game.data.account_config import RENAME_COST_GP
from game.test.core.base import CorePlugin, move_to_room, run_command

class TestMercenaryAndShortcuts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.random_state = random.getstate()
        random.seed(42)
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, command: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, command, uid))

    def _hire_harry(self, uid: str, gp: int = 100):
        stats = self.plugin.save_manager.load_stats(uid)
        stats.gp = gp
        self.plugin.save_manager.save_stats(uid, stats)
        self.run_cmd("主城", uid)
        self.run_cmd("d", uid)
        self.run_cmd("d", uid)
        self.run_cmd("w", uid)
        talk_res = self.run_cmd("talk 哈里", uid)
        self.assertIn("哈里·杜博阿", talk_res)
        hire_res = self.run_cmd("2", uid)
        self.assertIn("50 GP", hire_res)
        dup_res = self.run_cmd("2", uid)
        self.assertIn("收据我收着呢", dup_res)
        self.run_cmd("离开", uid)
        self.run_cmd("退出", uid)

    def test_s_fixed_move_down_and_r_status_shorthand(self):
        uid = "shortcut_user"
        menu_r = self.run_cmd("r", uid)
        self.assertIn("魔法肉鸽卡牌游戏", menu_r)
        menu_s = self.run_cmd("s", uid)
        self.assertIn("不可用", menu_s)

        self.run_cmd("主城", uid)
        town_s = self.run_cmd("s", uid)
        self.assertIn("卡牌大卖场", town_s)
        town_r = self.run_cmd("r", uid)
        self.assertIn("卡牌大卖场", town_r)
        self.run_cmd("退出", uid)

        self.run_cmd("start confirm", uid)
        explore_s = self.run_cmd("s", uid)
        self.assertIn("不可用", explore_s)
        explore_r = self.run_cmd("r", uid)
        self.assertIn("第 1 关", explore_r)

    def test_tavern_hire_requires_enough_gp(self):
        uid = "poor_hirer"
        stats = self.plugin.save_manager.load_stats(uid)
        stats.gp = 20
        self.plugin.save_manager.save_stats(uid, stats)
        self.run_cmd("主城", uid)
        self.run_cmd("d", uid)
        self.run_cmd("d", uid)
        self.run_cmd("w", uid)
        self.run_cmd("talk 哈里", uid)
        res = self.run_cmd("2", uid)
        self.assertIn("50", res)
        after = self.plugin.save_manager.load_stats(uid)
        self.assertEqual(after.hired_mercenaries, [])
        self.assertEqual(after.gp, 20)

    def test_solo_mercenary_battle_dialog_swap_timing_and_stats(self):
        uid = "harry_employer"
        self._hire_harry(uid, gp=100)
        stats_after_hire = self.plugin.save_manager.load_stats(uid)
        self.assertEqual(stats_after_hire.gp, 50)
        self.assertEqual(stats_after_hire.hired_mercenaries, ["harry_du_bois"])

        start_res = self.run_cmd("start confirm", uid)
        self.assertIn("第 1 关", start_res)
        stats_after_start = self.plugin.save_manager.load_stats(uid)
        self.assertEqual(stats_after_start.hired_mercenaries, [])

        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.player_count(), 2)
        self.assertEqual(run.human_uids(), [uid])
        merc_uid = [u for u in run.party_order if u != uid][0]
        merc = run.players[merc_uid]
        self.assertTrue(merc.is_mercenary)
        self.assertEqual(merc.mercenary_id, "harry_du_bois")
        self.assertEqual(merc.mercenary_owner, uid)
        self.assertEqual(merc.hp, 72)

        self.run_cmd("c 1", uid)
        status_res = self.run_cmd("r", uid)
        self.assertIn("哈里·杜博阿（雇佣兵）", status_res)

        dialog_res = self.run_cmd("talk", uid)
        self.assertIn("雇佣兵交互", dialog_res)
        self.assertNotIn("pale_", dialog_res)
        self.assertNotIn("thought_", dialog_res)
        self.assertIn("横渡灰域", dialog_res)
        chat_res = self.run_cmd("1", uid)
        self.assertIn("哈里·杜博阿", chat_res)
        self.assertNotIn("['", chat_res)
        self.assertNotIn('["', chat_res)
        self.assertNotIn("', '", chat_res)
        timing_res = self.run_cmd("3", uid)
        self.assertIn("回合最开始出牌", timing_res)
        leave_res = self.run_cmd("4", uid)
        self.assertIn("结束了与【哈里·杜博阿】的交谈", leave_res)

        battle_res, run = move_to_room(self.plugin, uid, ("battle", "elite"))
        self.assertIn("哈里·杜博阿", battle_res)

        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "battle")
        battle_r = self.run_cmd("r", uid)
        self.assertIn("哈里·杜博阿", battle_r)
        battle_s = self.run_cmd("s", uid)
        self.assertIn("不可用", battle_s)

        self.run_cmd("talk 哈里", uid)
        self.run_cmd("2", uid)
        self.run_cmd("1", uid)
        swap_res = self.run_cmd("1", uid)
        self.assertIn("交换完成", swap_res)
        self.run_cmd("3", uid)
        self.run_cmd("4", uid)

        end_res = self.run_cmd("e", uid)
        self.assertIn("哈里·杜博阿", end_res)

        for _ in range(30):
            run = self.plugin.save_manager.load_save(uid)
            if not run or run.node_type != "battle":
                break
            self.run_cmd("e", uid)

        stats_after_turn = self.plugin.save_manager.load_stats(uid)
        self.assertGreater(stats_after_turn.total_damage, 0)
        for fname in os.listdir(self.tmp.name):
            self.assertFalse(fname.startswith("stats_merc"))
        if run and run.node_type == "reward":
            items = run.node_data.get("items") or []
            for idx, item in enumerate(items, 1):
                if item.get("type") == "gold":
                    self.run_cmd(f"c {idx}", uid)
                    break

    def test_solo_human_death_settles_without_waiting_on_mercenary(self):
        uid = "harry_defeat_user"
        self._hire_harry(uid, gp=100)
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)

        for _ in range(300):
            run = self.plugin.save_manager.load_save(uid)
            if not run:
                break
            if run.node_type == "grid_map":
                _, moved_run = move_to_room(self.plugin, uid, ("battle", "elite", "high_danger", "boss"))
                if moved_run and moved_run.node_type == "grid_map":
                    move_to_room(self.plugin, uid, ("downstairs",))
                    self.run_cmd("talk", uid)
                    self.run_cmd("1", uid)
            elif run.node_type == "battle":
                self.run_cmd("e", uid)
            elif run.node_type == "reward":
                pool = run.node_data.get("coop_relic_pool") or []
                if pool:
                    self.run_cmd("c 1", uid)
                else:
                    self.run_cmd("离开", uid)
            elif run.node_type == "card_select":
                cards = run.node_data.get("cards") or []
                self.run_cmd(f"c {len(cards) + 1}", uid)
            elif run.node_type in ("shop", "treasure"):
                self.run_cmd("离开", uid)
            else:
                self.run_cmd("c 1", uid)

        self.assertIsNone(self.plugin.save_manager.load_save(uid))

    def test_coop_with_mercenary_does_not_block_votes_or_turns(self):
        uids = ["coop_h1", "coop_h2"]
        self._hire_harry(uids[0], gp=100)
        for uid, name in zip(uids, ["雇主一号", "队友二号"]):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.gp = max(stats.gp, RENAME_COST_GP)
            self.plugin.save_manager.save_stats(uid, stats)
            self.run_cmd(f"friend name {name}", uid)
        h2_handle = self.plugin.save_manager.load_stats(uids[1]).player_handle
        h1_handle = self.plugin.save_manager.load_stats(uids[0]).player_handle
        self.run_cmd(f"friend add {h2_handle}", uids[0])
        self.run_cmd(f"friend accept {h1_handle}", uids[1])
        create_res = self.run_cmd("team create", uids[0])
        lobby_id = re.search(r"队伍 ([A-Z0-9]{6})", create_res).group(1)
        self.run_cmd(f"friend invite {h2_handle}", uids[0])
        self.run_cmd(f"team join {lobby_id}", uids[1])
        self.run_cmd("team ready", uids[1])
        self.run_cmd("team start", uids[0])

        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.player_count(), 3)
        self.assertEqual(run.human_uids(), uids)

        self.run_cmd("c 1", uids[0])
        self.run_cmd("c 1", uids[1])
        after_ancient = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(after_ancient.node_type, "grid_map")

        move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        res1 = self.run_cmd("e", uids[0])
        self.assertIn("等待队友", res1)
        res2 = self.run_cmd("e", uids[1])
        self.assertIn("进入第 2 回合", res2)
        after_turn = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(after_turn.node_data.get("turn_count"), 2)

    def test_mercenary_plays_cards_cycles_hand_and_resolves_interactions(self):
        uid = "harry_battle_ai_user"
        self._hire_harry(uid, gp=100)
        stats = self.plugin.save_manager.load_stats(uid)
        stats.locked_cards = ["fleeting_spark", "neutral_emperor_eye", "discover"]
        self.plugin.save_manager.save_stats(uid, stats)

        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)

        for target_name in ("飞逝火花", "帝王之眼", "发掘"):
            self.run_cmd("talk 哈里", uid)
            pick_self = self.run_cmd("2", uid)
            match = re.search(rf"\[(\d+)\]\s*{re.escape(target_name)}", pick_self)
            if match:
                self.run_cmd(match.group(1), uid)
                self.run_cmd("1", uid)
            else:
                self.run_cmd("0", uid)
            self.run_cmd("4", uid)

        move_to_room(self.plugin, uid, ("battle", "elite"))

        played_seen = False
        for turn_i in range(4):
            run = self.plugin.save_manager.load_save(uid)
            if not run or run.node_type != "battle":
                break
            if turn_i == 2:
                self.run_cmd("talk 哈里", uid)
                self.run_cmd("3", uid)
                self.run_cmd("4", uid)
            res = self.run_cmd("e", uid)
            if "打出【" in res:
                played_seen = True
            self.assertNotIn("没有出牌", res if "打出【" in res else "")
            after = self.plugin.save_manager.load_save(uid)
            if after and after.node_type == "battle":
                self.assertFalse(after.node_data.get("state_stack"))
                self.assertFalse(after.node_data.get("pending_discard"))
                merc_uid = [u for u in after.party_order if u != uid][0]
                merc = after.players[merc_uid]
                if merc.hp > 0 and not merc.downed:
                    self.assertLessEqual(len(merc.hand), 8)

        self.assertTrue(played_seen)
        for fname in os.listdir(self.tmp.name):
            self.assertFalse(fname.startswith("save_merc"))
            self.assertFalse(fname.startswith("stats_merc"))


if __name__ == "__main__":
    unittest.main()
