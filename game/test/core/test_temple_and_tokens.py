import asyncio
import os
import tempfile
import unittest

from game.core.battle.daily_blessing import _pick_random_card
from game.core.inventory.deck_service import DeckService
from game.test.core.base import CorePlugin, floor_of, require_run, run_command
from game.entities import ALL_CARDS
from game.models.state import CardState, EnemyState, GameRun, PlayerState, UserStats


class DummyContext:
    def __init__(self):
        self.data_dir = tempfile.mkdtemp()


class MyPlugin(CorePlugin):
    pass


class TestTempleAndTokens(unittest.TestCase):
    def setUp(self):
        self.plugin = MyPlugin(DummyContext())
        self.sm = self.plugin.save_manager

    def _cleanup(self, uid):
        self.sm.delete_save(uid)
        self.sm.delete_stats(uid)

    def _run(self, cmd, uid):
        return asyncio.run(run_command(self.plugin, cmd, uid))

    def test_yog_quest_starts_as_snowfield_grid_run(self):
        uid = "test_yog_quest_grid_user"
        self._cleanup(uid)
        try:
            self._run(".rogue 主城", uid)
            stats = self.sm.load_stats(uid)
            stats.yog_sothoth_kill_count = 1
            self.sm.save_stats(uid, stats)

            pre_quest = self._run(".rogue 任务", uid)
            self.assertIn("尤格索托斯死了吗？", pre_quest)
            self.assertIn("先与向导长老谈一谈", pre_quest)
            self.assertNotIn("死灵之书", pre_quest)
            self.assertNotIn("欧吕尔", pre_quest)

            talk_res = self._run(".rogue talk 向导长老", uid)
            self.assertIn("询问尤格索托斯的死讯", talk_res)
            report_num = None
            for line in talk_res.splitlines():
                if "询问尤格索托斯的死讯" in line and "." in line:
                    report_num = line.split(".", 1)[0].strip()
                    break
            self.assertIsNotNone(report_num)

            reply_res = self._run(f".rogue {report_num}", uid)
            self.assertIn("星形符印", reply_res)
            stats = self.sm.load_stats(uid)
            self.assertIn("star_sigil", stats.town_inventory)
            self._run(".rogue exit", uid)

            self._run(".rogue a", uid)
            self._run(".rogue a", uid)
            gate_talk = self._run(".rogue talk 西大门", uid)
            self.assertIn("出城前往雪原", gate_talk)
            enter_res = self._run(".rogue use 星辉符印", uid)
            self.assertIn("雾隐雪原", enter_res)
            self.assertIn("B11", enter_res)
            self.assertNotIn("尤格索托斯神殿", enter_res)
            run = require_run(self.sm.load_save(uid))
            self.assertEqual(run.node_type, "grid_map")
            self.assertEqual(floor_of(run).floor_index, 5)
            self.assertTrue(floor_of(run).floor_flags.get("yog_quest"))

            quest_res = self._run(".rogue 任务", uid)
            self.assertIn("穿过雾隐雪原，找到神殿大门", quest_res)
            move_res = self._run(".rogue d", uid)
            self.assertIn("C11", move_res)
        finally:
            self._cleanup(uid)

    
    def test_crpg_quest_branch_progression(self):
        uid = "test_crpg_quest_branch_user"
        self._cleanup(uid)
        try:
            self._run(".rogue 主城", uid)
            self._run(".rogue d", uid)
            self._run(".rogue d", uid)
            self._run(".rogue w", uid)
            self._run(".rogue talk Bartender_Jack", uid)
            self._run(".rogue 3", uid)
            self._run(".rogue exit", uid)

            q1 = self._run(".rogue 任务", uid)
            self.assertIn("在主城内打听并设法获取虚空草药", q1)
            self.assertNotIn("许愿喷泉", q1)
            self.assertNotIn("\u0336", q1)

            self._run(".rogue s", uid)
            self._run(".rogue a", uid)
            self._run(".rogue a", uid)
            self._run(".rogue a", uid)
            from game.data.text.locale_data import get_locale_text
            stats = self.sm.load_stats(uid)
            guard_room = stats.town_flags.get("pos_Town_Guard", "square")
            guard_room_name = get_locale_text(f"rooms.{guard_room}.name")
            self._run(f".rogue tp {guard_room_name}", uid)
            self._run(".rogue talk 巡逻卫兵", uid)
            self._run(".rogue 2", uid)
            self._run(".rogue exit", uid)

            q2 = self._run(".rogue 任务", uid)
            self.assertIn("向卫兵举报了非法倒卖草药的推销员", q2)
            self.assertIn("前往许愿喷泉，用泉水清洗虚空草药", q2)
            self.assertNotIn("在主城内打听并设法获取虚空草药", q2)
            self.assertNotIn("\u0336", q2)

            self._run(".rogue tp 许愿喷泉", uid)
            self._run(".rogue talk Fountain", uid)
            self._run(".rogue 1", uid)
            self._run(".rogue exit", uid)

            q3 = self._run(".rogue 任务", uid)
            self.assertIn("天外甘露草正散发着微光", q3)
            self.assertIn("将天外甘露草带回酒馆交给酒保杰克", q3)
            self.assertNotIn("\u0336", q3)

            self._run(".rogue d", uid)
            self._run(".rogue talk 神秘店主", uid)
            self._run(".rogue 3", uid)
            self._run(".rogue exit", uid)

            q4 = self._run(".rogue 任务", uid)
            self.assertIn("已完成", q4)
            self.assertIn("高价卖给了主城商店的神秘店主", q4)
            self.assertNotIn("当前目标：", q4)
            self.assertNotIn("\u0336", q4)
            self.assertNotIn("✔", q4)
        finally:
            self._cleanup(uid)

    

    def test_defiled_altar_route_fountain_outer_plane(self):
        uid = "test_defiled_fountain_outer_plane_user"
        self._cleanup(uid)
        try:
            self._run(".rogue 主城", uid)
            stats = self.sm.load_stats(uid)
            stats.gp = 10
            stats.town_flags["quest_yog_death_state"] = "completed"
            stats.town_flags["yog_quest_flags"] = {}
            self.sm.save_stats(uid, stats)

            self._run(".rogue d", uid)
            no_defile_talk = self._run(".rogue talk 许愿喷泉", uid)
            self.assertNotIn("向喷泉投入 1 GP 硬币", no_defile_talk)
            self._run(".rogue 1", uid)

            stats = self.sm.load_stats(uid)
            stats.town_flags["yog_quest_flags"] = {"altar_defiled": True}
            self.sm.save_stats(uid, stats)

            talk1 = self._run(".rogue talk 许愿喷泉", uid)
            self.assertIn("向喷泉投入 1 GP 硬币", talk1)
            self.assertNotIn("跳入喷泉", talk1)
            toss_num = None
            for line in talk1.splitlines():
                if "向喷泉投入 1 GP 硬币" in line and "." in line:
                    toss_num = line.split(".", 1)[0].strip()
                    break
            self.assertIsNotNone(toss_num)

            gp_before = self.sm.load_stats(uid).gp
            talk2 = self._run(f".rogue {toss_num}", uid)
            self.assertIn("跳入喷泉", talk2)
            self.assertEqual(self.sm.load_stats(uid).gp, gp_before - 1)
            jump_num = None
            for line in talk2.splitlines():
                if "跳入喷泉" in line and "." in line:
                    jump_num = line.split(".", 1)[0].strip()
                    break
            self.assertIsNotNone(jump_num)

            enter_res = self._run(f".rogue {jump_num}", uid)
            self.assertIn("外层位面", enter_res)
            self.assertIn("漂泊之岸", enter_res)
            updated = self.sm.load_stats(uid)
            self.assertTrue(updated.town_flags.get("outer_plane_active"))
        finally:
            self._cleanup(uid)


if __name__ == "__main__":
    unittest.main()
