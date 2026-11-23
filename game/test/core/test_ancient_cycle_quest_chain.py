import asyncio
import random
import tempfile
import unittest
from unittest.mock import patch

from game.data.world.map_quest_config import FLOOR5_KEY_ITEM, TOWN_FLAG_FLOOR5_KEY
from game.test.core.base import CorePlugin, floor_of, load_run, require_run, run_command


class TestAncientCycleQuestChain(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(20261125)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, cmd, sender_id=uid))

    def _start_grid(self, uid: str) -> None:
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)

    def _place_npc(self, uid: str, npc_id: str) -> str:
        run = require_run(load_run(self.plugin, uid))
        fm = floor_of(run)
        coord = fm.player_coords[uid]
        room = fm.rooms[coord]
        room.npcs = [npc_id]
        room.defeated_npcs = []
        self.plugin.save_manager.save_save(uid, run)
        return coord

    def _find_opt(self, text: str, keyword: str) -> int:
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("[") and "]" in s and keyword in s:
                head = s[1:s.index("]")].strip()
                if head.isdigit():
                    return int(head)
        raise AssertionError(f"Option {keyword!r} not found in:\n{text}")

    def test_three_stage_branching_ancient_cycle_unlocks_floor5_key_and_achievement(self):
        uid = "ancient_cycle_u"
        self._start_grid(uid)

        self._place_npc(uid, "hakurei_reimu")
        v = self.run_cmd("talk 灵梦", uid)
        v = self.run_cmd(f"c {self._find_opt(v, '境界是不是')}", uid)
        self.assertIn("第一段", v)
        v = self.run_cmd(f"c {self._find_opt(v, '控制中心')}", uid)
        self.run_cmd(f"c {self._find_opt(v, '[离开]')}", uid)

        self._place_npc(uid, "kirisame_marisa")
        v = self.run_cmd("talk 魔理沙", uid)
        v = self.run_cmd(f"c {self._find_opt(v, '红魔馆印章')}", uid)
        v = self.run_cmd(f"c {self._find_opt(v, '打个掩护')}", uid)
        self.run_cmd(f"c {self._find_opt(v, '[离开]')}", uid)

        self._place_npc(uid, "izayoi_sakuya")
        v = self.run_cmd("talk 咲夜", uid)
        v = self.run_cmd(f"c {self._find_opt(v, '时间')}", uid)
        self.assertIn("第一段", v)
        self.run_cmd(f"c {self._find_opt(v, '[离开]')}", uid)

        self._place_npc(uid, "akemi_homura")
        v_homura_early = self.run_cmd("talk 晓美焰", uid)
        self.assertNotIn("交付", v_homura_early)
        self.run_cmd("leave", uid)

        self._place_npc(uid, "patchouli_knowledge")
        v_patch = self.run_cmd("talk 帕秋莉", uid)
        done1 = self.run_cmd(f"c {self._find_opt(v_patch, '封存')}", uid)
        self.assertIn("第二段", done1)
        self.run_cmd("leave", uid)

        q2 = self.run_cmd("quest", uid)
        self.assertIn("先古循环", q2)
        self.assertIn("轮回尽头的因果秤", q2)
        self.assertIn("0/3", q2)

        self.run_cmd("giveup confirm", uid)
        self._start_grid(uid)
        q2_persist = self.run_cmd("quest", uid)
        self.assertIn("轮回尽头的因果秤", q2_persist)

        self._place_npc(uid, "tomoe_mami")
        v = self.run_cmd("talk 巴麻美", uid)
        v = self.run_cmd(f"c {self._find_opt(v, '红茶')}", uid)
        self.run_cmd(f"c {self._find_opt(v, '[离开]')}", uid)

        self._place_npc(uid, "kyubey")
        v = self.run_cmd("talk 丘比", uid)
        v = self.run_cmd(f"c {self._find_opt(v, '契约')}", uid)
        with patch("game.core.world.rooms.dialog.checks.random.randint", return_value=20):
            v = self.run_cmd(f"c {self._find_opt(v, '漏洞')}", uid)
        v = self.run_cmd(f"c {self._find_opt(v, '签')}", uid)
        self.assertIn("第二段", v)
        self.run_cmd("leave", uid)

        v_qb_turnin = self.run_cmd("talk 丘比", uid)
        done2 = self.run_cmd(f"c {self._find_opt(v_qb_turnin, '因果')}", uid)
        self.assertIn("第三段", done2)
        self.run_cmd("leave", uid)

        self._place_npc(uid, "pppopipupu_dungeon")
        v = self.run_cmd("talk pppopipupu", uid)
        v = self.run_cmd(f"c {self._find_opt(v, '死掉的人')}", uid)
        self.run_cmd("leave", uid)

        self._place_npc(uid, "komeiji_koishi")
        v = self.run_cmd("talk 古明地恋", uid)
        with patch("game.core.world.rooms.dialog.checks.random.randint", return_value=20):
            v = self.run_cmd(f"c {self._find_opt(v, '歌谣')}", uid)
        self.run_cmd("leave", uid)

        self._place_npc(uid, "akemi_homura")
        v = self.run_cmd("talk 晓美焰", uid)
        v = self.run_cmd(f"c {self._find_opt(v, '你也记得先古循环')}", uid)
        self.assertIn("第三段", v)
        self.run_cmd("leave", uid)

        self._place_npc(uid, "pppopipupu_dungeon")
        v_pppo_turnin = self.run_cmd("talk pppopipupu", uid)
        done3 = self.run_cmd(f"c {self._find_opt(v_pppo_turnin, '见证账本')}", uid)
        self.assertIn("先古循环之钥", done3)

        stats = self.plugin.save_manager.load_stats(uid)
        self.assertTrue(stats.town_flags.get(TOWN_FLAG_FLOOR5_KEY))
        self.assertIn(FLOOR5_KEY_ITEM, stats.town_inventory)
        self.assertIn("ancient_cycle_breaker", stats.unlocked_achievements)

        q_final = self.run_cmd("quest", uid)
        self.assertIn("先古循环", q_final)
        self.assertIn("先古循环之钥", q_final)
