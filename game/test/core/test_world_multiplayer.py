import asyncio
import re
import tempfile
import time
import unittest
from unittest.mock import patch

from game.core.world.presence import WorldPresenceService
from game.data.world_social_config import WORLD_PRESENCE_TIMEOUT_SECONDS, WORLD_TOWN
from game.data.yog_quest_config import YOG_INFO_FLAG, YOG_QUEST_FLAG, YOG_SIGIL_ITEM
from game.test.core.base import CorePlugin, run_command


class WorldMultiplayerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.a = "mp_a"
        self.b = "mp_b"
        for uid, name in ((self.a, "Alice"), (self.b, "Bob")):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.player_name = name
            stats.player_handle = name
            stats.name_customized = True
            self.plugin.save_manager.save_stats(uid, stats)

    def tearDown(self):
        self.tmp.cleanup()

    def cmd(self, text: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, text, uid))

    @staticmethod
    def _map_rows(text: str) -> list[str]:
        return [line for line in text.splitlines() if line[:2].strip().isdigit()]

    def enter_town(self):
        self.cmd("主城", self.a)
        self.cmd("主城", self.b)

    def befriend(self):
        self.cmd("好友 add Bob", self.a)
        self.cmd("好友 accept Alice", self.b)

    def test_town_players_talk_live_and_remote_friend_message(self):
        self.enter_town()
        town_view = self.cmd("tp C2", self.a)
        self.assertIn("Bob", town_view)
        self.assertIn("🧑Bob", town_view)
        self.assertFalse(any("🧑" in line for line in self._map_rows(town_view)))
        self.assertIn("你好", self.cmd("对话 Bob 你好", self.a))
        inbox = self.cmd("消息", self.b)
        self.assertIn("💬", inbox)
        self.assertIn("你好", inbox)
        self.assertIn("📭", inbox)
        self.assertNotIn("共 1 条", inbox)
        self.assertNotIn("💬", self.cmd("消息", self.b))
        self.assertIn("还没有好友", self.cmd("sendmsg Alice 远程", self.b))
        self.befriend()
        self.assertIn("已向好友", self.cmd("sendmsg Alice 远程问候", self.b))
        remote = self.cmd("消息", self.a)
        self.assertIn("远程问候", remote)
        self.assertIn("消息信箱", remote)
        self.assertNotIn("💬", remote)

    def test_snowfield_players_see_each_other(self):
        for uid in (self.a, self.b):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.yog_sothoth_kill_count = 1
            stats.town_flags[YOG_INFO_FLAG] = True
            stats.town_inventory.append(YOG_SIGIL_ITEM)
            stats.in_town = True
            stats.town_pos = "west_gate"
            self.plugin.save_manager.save_stats(uid, stats)
        self.assertIn("第 5 层", self.cmd("使用 星辉符印", self.a))
        self.assertIn("第 5 层", self.cmd("使用 星辉符印", self.b))
        rendered = self.cmd("看", self.a)
        self.assertIn("🧑Bob", rendered)
        self.assertIn("与玩家交谈", rendered)
        self.assertFalse(any("🧑" in line for line in self._map_rows(rendered)))
        self.assertIn("你对【Bob】说", self.cmd("对话 Bob 雪原见", self.a))
        b_view = self.cmd("看", self.b)
        self.assertIn("💬 【Alice】对你说：雪原见", b_view)

    def test_party_quest_entry_is_shared_instance(self):
        for uid in (self.a, self.b):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.yog_sothoth_kill_count = 1
            stats.town_flags[YOG_INFO_FLAG] = True
            stats.town_inventory.append(YOG_SIGIL_ITEM)
            self.plugin.save_manager.save_stats(uid, stats)
        self.enter_town()
        self.befriend()
        created = self.cmd("组队 创建", self.a)
        lobby_id = re.search(r"队伍 ([A-Z0-9]{6})", created).group(1)
        self.cmd("组队 邀请 Bob", self.a)
        self.cmd("组队 加入 " + lobby_id, self.b)
        self.cmd("组队 准备", self.b)
        stats = self.plugin.save_manager.load_stats(self.a)
        stats.town_pos = "west_gate"
        self.plugin.save_manager.save_stats(self.a, stats)
        started = self.cmd("使用 星辉符印", self.a)
        self.assertIn("雪原", started)
        self.assertIn("队伍状态", started)
        self.assertEqual(
            self.plugin.save_manager.load_stats(self.a).active_coop_id,
            self.plugin.save_manager.load_stats(self.b).active_coop_id,
        )
        self.assertNotEqual(self.plugin.save_manager.load_stats(self.a).active_coop_id, "")
        self.assertEqual(self.plugin.save_manager.load_stats(self.a).town_flags.get(YOG_QUEST_FLAG), "started")
        party_view = self.cmd("看", self.b)
        self.assertIn("第 5 层", party_view)
        self.assertIn("🧑Alice", party_view)
        self.assertFalse(any("👥" in line for line in self._map_rows(party_view)))
        self.assertIsNone(self.plugin.save_manager.get_lobby(lobby_id))

    def test_presence_expires_after_timeout(self):
        service = WorldPresenceService(self.plugin.save_manager)
        service.touch(self.a, WORLD_TOWN, "C2")
        self.assertEqual(len(service.players(WORLD_TOWN)), 1)
        with patch("game.core.world.presence.time.time", return_value=time.time() + WORLD_PRESENCE_TIMEOUT_SECONDS + 1):
            self.assertEqual(service.players(WORLD_TOWN), [])
