import asyncio
import random
import tempfile
import unittest

from game.test.core.base import CorePlugin, floor_of, load_run, run_command


class TestTutorial(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.uid = "tutorial_player_1"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, cmd: str, uid: str | None = None) -> str:
        return asyncio.run(run_command(self.plugin, cmd, uid or self.uid))

    def _find_hand_idx(self, run, card_id: str) -> int | None:
        for idx, card_state in enumerate(run.player.hand, 1):
            if card_state.id == card_id:
                return idx
        return None

    def test_full_tutorial_walkthrough_and_replay(self):
        random.seed(7)
        start_res = self._run("新手教程")
        self.assertIn("新手试炼回廊", start_res)
        self.assertIn("向导长老", start_res)
        self.assertIn("跳过教程", start_res)

        run = load_run(self.plugin, self.uid)
        self.assertIsNotNone(run)
        assert run is not None
        self.assertEqual(run.node_type, "grid_map")
        self.assertEqual(floor_of(run).floor_index, 0)
        self.assertEqual(floor_of(run).player_coords.get(self.uid), "A2")

        talk_res = self._run("talk 向导长老")
        self.assertIn("向导长老", talk_res)
        self.assertIn("请教基本操作", talk_res)
        self.assertIn("请教卡牌玩法", talk_res)
        self.assertIn("请教示例地图", talk_res)

        ops_res = self._run("1")
        self.assertIn("w / a / s / d", ops_res)
        cards_res = self._run("2")
        self.assertIn("行动点", cards_res)
        map_res = self._run("3")
        self.assertIn("体力（SP）", map_res)
        leave_res = self._run("5")
        self.assertIn("A2", leave_res)

        battle_entry = self._run("d")
        self.assertIn("新手战斗指引", battle_entry)
        self.assertIn("新手训练木偶", battle_entry)
        self.assertIn("轻击造成 4 点钝击伤害", battle_entry)

        run = load_run(self.plugin, self.uid)
        assert run is not None
        self.assertEqual(run.node_type, "battle")
        self.assertEqual(len(run.enemies), 1)
        self.assertEqual(run.enemies[0].name, "新手训练木偶")

        for _ in range(8):
            run = load_run(self.plugin, self.uid)
            assert run is not None
            if run.node_type != "battle":
                break
            if run.player.minions:
                for grid in sorted(run.player.minions.keys()):
                    if run.player.minions[grid].attack_actions > 0:
                        self._run(f"m {grid} a e1")
                        run = load_run(self.plugin, self.uid)
                        assert run is not None
                        if run.node_type != "battle":
                            break
            if run.node_type != "battle":
                break
            for cid in ("misty_step", "shield", "fire_bolt", "mercenary", "lucky_coin", "magic_missile", "warrior_bash"):
                run = load_run(self.plugin, self.uid)
                assert run is not None
                if run.node_type != "battle":
                    break
                idx = self._find_hand_idx(run, cid)
                if idx is not None:
                    self._run(f"p {idx} e1")
            run = load_run(self.plugin, self.uid)
            assert run is not None
            if run.node_type == "battle":
                self._run("e")

        run = load_run(self.plugin, self.uid)
        assert run is not None
        self.assertEqual(run.node_type, "reward")

        gold_res = self._run("1")
        self.assertIn("40", gold_res)
        leave_reward = self._run("c 离开")
        self.assertIn("B2", leave_reward)

        dig_res = self._run("dig w")
        self.assertIn("B1", dig_res)
        run = load_run(self.plugin, self.uid)
        assert run is not None
        self.assertLess(run.player.sp, 10)

        treasure_res = self._run("d")
        self.assertIn("试炼藏宝室", treasure_res)
        take_res = self._run("take 绷带")
        self.assertIn("战地绷带", take_res)

        self._run("a")
        self._run("s")
        shrine_enter = self._run("s")
        self.assertIn("向导试炼碑", shrine_enter)
        recover_res = self._run("1")
        self.assertIn("体力恢复", recover_res)
        self._run("4")

        rest_enter = self._run("w")
        rest_enter = self._run("d")
        self.assertIn("安全篝火", rest_enter)
        self._run("c 离开")

        shop_enter = self._run("d")
        self.assertIn("旅途补给摊", shop_enter)
        self._run("3")

        exit_enter = self._run("d")
        self.assertIn("试炼回廊出口", exit_enter)
        complete_res = self._run("1")
        self.assertIn("恭喜完成新手教程", complete_res)

        stats = self.plugin.save_manager.load_stats(self.uid)
        self.assertTrue(stats.tutorial_done)
        self.assertIsNone(self.plugin.save_manager.load_save(self.uid))

        town_res = self._run("主城")
        self.assertIn("向导长老", town_res)
        elder_talk = self._run("talk 向导长老")
        self.assertIn("重玩新手教程", elder_talk)
        replay_num = None
        for line in elder_talk.splitlines():
            if "重玩新手教程" in line and "." in line:
                replay_num = line.split(".", 1)[0].strip()
                break
        self.assertIsNotNone(replay_num)
        replay_res = self._run(str(replay_num))
        self.assertIn("再次踏入了新手试炼回廊", replay_res)
        self.assertIn("A2", replay_res)

        skip_res = self._run("skip")
        self.assertIn("已跳过新手教程", skip_res)
        self.assertIn("中心广场", skip_res)
        self.assertIsNone(self.plugin.save_manager.load_save(self.uid))

    def test_tutorial_defeat_rescues_without_corpse(self):
        self._run("新手教程")
        self._run("d")
        run = load_run(self.plugin, self.uid)
        assert run is not None
        self.assertEqual(run.node_type, "battle")
        for _ in range(40):
            run = load_run(self.plugin, self.uid)
            assert run is not None
            if run.node_type != "battle":
                break
            self._run("e")
        run = load_run(self.plugin, self.uid)
        assert run is not None
        self.assertEqual(run.node_type, "grid_map")
        self.assertEqual(floor_of(run).player_coords.get(self.uid), "A2")
        self.assertEqual(run.player.hp, run.player.max_hp)
        self.assertEqual(self.plugin.save_manager.corpses._load().get("corpses", []), [])


if __name__ == "__main__":
    unittest.main()
