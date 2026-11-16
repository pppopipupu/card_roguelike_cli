import asyncio
import re
import tempfile
import time
import unittest
from unittest.mock import patch

from game.cards import ALL_CARDS
from game.core.world.grid_map_generator import coord_to_xy, xy_to_coord
from game.core.world.presence import WorldPresenceService
from game.data.outer_plane_config import NECRONOMICON_ITEM
from game.data.world_social_config import WORLD_PRESENCE_TIMEOUT_SECONDS, WORLD_TOWN
from game.data.yog_quest_config import YOG_INFO_FLAG, YOG_QUEST_FLAG, YOG_SIGIL_ITEM
from game.test.core.base import CorePlugin, floor_of, load_run, move_to_room, run_command


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

    def _start_coop_run(self):
        self.enter_town()
        self.befriend()
        created = self.cmd("组队 创建", self.a)
        match = re.search(r"队伍 ([A-Z0-9]{6})", created)
        assert match is not None, "team id must be present"
        lobby_id = match.group(1)
        self.cmd("组队 邀请 Bob", self.a)
        self.cmd("组队 加入 " + lobby_id, self.b)
        self.cmd("组队 准备", self.b)
        started = self.cmd("team start", self.a)
        return started

    def _first_walkable_direction(self, uid: str) -> str:
        run = load_run(self.plugin, uid)
        fm = floor_of(run)
        cur = fm.player_coords.get(uid, "")
        cx, cy = coord_to_xy(cur)
        for dcmd, dx, dy in (("d", 1, 0), ("s", 0, 1), ("w", 0, -1), ("a", -1, 0)):
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < fm.width and 0 <= ny < fm.height):
                continue
            room = fm.rooms.get(xy_to_coord(nx, ny))
            if room is not None and room.room_type not in ("wall", "obstacle", "secret_boss"):
                return dcmd
        return "d"

    def _clear_battle_if_needed(self, uids: list[str]):
        for _ in range(40):
            progressed = False
            for uid in uids:
                run = self.plugin.save_manager.load_save(uid)
                if not run:
                    continue
                if run.node_type == "battle_prompt":
                    self.cmd("1", uid)
                    progressed = True
                elif run.node_type == "battle" and not run.node_data.get("coop_done"):
                    for _ in range(8):
                        r_now = self.plugin.save_manager.load_save(uid)
                        if not r_now or r_now.node_type != "battle" or r_now.node_data.get("coop_done"):
                            break
                        played = False
                        for idx, cs in enumerate(list(r_now.player.hand), 1):
                            card = ALL_CARDS.get(cs.id)
                            if card is None:
                                continue
                            cost_a = getattr(card, "cost_a", 0)
                            cost_ba = getattr(card, "cost_ba", 0)
                            if cost_a <= r_now.player.actions and cost_ba <= r_now.player.bonus_actions:
                                res = self.cmd(f"p {idx} 1", uid)
                                if "❌" not in res:
                                    played = True
                                    progressed = True
                                    break
                        if not played:
                            break
                    r_end = self.plugin.save_manager.load_save(uid)
                    if r_end and r_end.node_type == "battle" and not r_end.node_data.get("coop_done"):
                        self.cmd("e", uid)
                        progressed = True
                elif run.node_type == "reward" and not run.node_data.get("coop_done"):
                    res = self.cmd("离开", uid)
                    if "必须先领取" in res or "❌" in res:
                        self.cmd("c 1", uid)
                    progressed = True
                elif run.node_type in ("card_select", "gem_insert") and not run.node_data.get("coop_done"):
                    self.cmd("c 1", uid)
                    progressed = True
                elif run.node_type in ("event", "shop", "rest", "treasure", "life_merchant") and not run.node_data.get("coop_done"):
                    self.cmd("离开", uid)
                    progressed = True
            all_grid = True
            for uid in uids:
                r = self.plugin.save_manager.load_save(uid)
                if not r or r.node_type != "grid_map":
                    all_grid = False
                    break
            if all_grid:
                return
            if not progressed:
                break

    def test_town_players_dialog_logs_and_remote_friend_message(self):
        self.enter_town()
        town_view = self.cmd("tp C2", self.a)
        self.assertIn("Bob", town_view)
        self.assertIn("🧑Bob", town_view)
        self.assertNotIn("与玩家交谈", town_view)
        self.assertFalse(any("🧑" in line for line in self._map_rows(town_view)))

        self.cmd("d", self.a)
        bob_after_move = self.cmd("look", self.b)
        self.assertNotIn("🧑Alice", bob_after_move)
        self.assertIn("没有叫", self.cmd("talk Bob 你好", self.a))
        self.assertIn("没有找到", self.cmd("说 Bob 你好", self.a))

        self.cmd("tp C2", self.a)
        dialog = self.cmd("对话 Bob", self.a)
        self.assertIn("正在与【Bob】交互", dialog)
        self.assertIn("[1] 打声招呼", dialog)
        self.assertIn("[2] 申请加为好友", dialog)
        self.assertIn("[3] 查看名片", dialog)
        self.assertIn("[0] 离开", dialog)

        card_view = self.cmd("3", self.a)
        self.assertIn("【Bob】的名片", card_view)
        self.assertIn("正在与【Bob】交互", card_view)

        req_res = self.cmd("2", self.a)
        self.assertIn("好友", req_res)
        self.cmd("好友 accept Alice", self.b)

        greet_res = self.cmd("1", self.a)
        self.assertIn("你对【Bob】说：你好", greet_res)
        close_res = self.cmd("0", self.a)
        self.assertIn("结束了", close_res)

        self.cmd("对话 Bob", self.a)
        chatter = asyncio.run(self.plugin.server.handle_rogue_message(self.a, "Alice", "今天天气不错"))
        self.assertIsNone(chatter)
        after_auto_close = self.cmd("r", self.a)
        self.assertIn("先古主城", after_auto_close)
        self.assertFalse(self.plugin.cli_router.world_social.has_dialog(self.a))

        self.assertIn("你对【Bob】说：主城见", self.cmd("对话 Bob 主城见", self.a))
        bob_status = self.cmd("r", self.b)
        self.assertIn("💬 【Alice】对你说：你好", bob_status)
        self.assertIn("💬 【Alice】对你说：主城见", bob_status)

        inbox = self.cmd("消息", self.b)
        self.assertIn("📭", inbox)
        self.assertNotIn("主城见", inbox)

        bob_logs = self.cmd("logs", self.b)
        self.assertIn("主城见", bob_logs)

        self.assertIn("已向好友", self.cmd("sendmsg Alice 远程问候", self.b))
        self.cmd("d", self.a)
        remote = self.cmd("消息", self.a)
        self.assertIn("远程问候", remote)
        self.assertIn("消息信箱", remote)
        self.assertNotIn("💬", remote)

    def test_outer_plane_players_merged_and_social_commands(self):
        for uid in (self.a, self.b):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.town_inventory.append(NECRONOMICON_ITEM)
            self.plugin.save_manager.save_stats(uid, stats)
        self.enter_town()
        view_a = self.cmd("使用 死灵之书", self.a)
        view_b = self.cmd("使用 死灵之书", self.b)
        self.assertIn("在场人物", view_b)
        self.assertIn("【🧑Alice】", view_b)
        self.assertNotIn("与玩家交谈", view_b)

        refreshed_a = self.cmd("r", self.a)
        self.assertIn("在场人物", refreshed_a)
        self.assertIn("【🧑Bob】", refreshed_a)

        self.assertIn("你对【Bob】说：位面重逢", self.cmd("talk Bob 位面重逢", self.a))
        self.assertIn("💬 【Alice】对你说：位面重逢", self.cmd("r", self.b))
        self.assertIn("位面重逢", self.cmd("logs", self.b))
        created = self.cmd("team create", self.a)
        self.assertIn("队伍", created)
        self.cmd("team leave", self.a)
        self.assertIn("好友", self.cmd("friend list", self.a))

        b_say_menu = self.cmd("说", self.b)
        self.assertIn("Alice", b_say_menu)

    def test_snowfield_players_see_each_other(self):
        for uid in (self.a, self.b):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.yog_sothoth_kill_count = 1
            stats.town_flags[YOG_INFO_FLAG] = True
            stats.town_inventory.append(YOG_SIGIL_ITEM)
            stats.in_town = True
            stats.town_pos = "west_gate"
            self.plugin.save_manager.save_stats(uid, stats)
        self.assertIn("第 1 层 · 雾隐雪原", self.cmd("使用 星辉符印", self.a))
        self.assertIn("第 1 层 · 雾隐雪原", self.cmd("使用 星辉符印", self.b))
        rendered = self.cmd("看", self.a)
        self.assertIn("👤 【在场人物】【🧑Bob】", rendered)
        self.assertNotIn("与玩家交谈", rendered)
        self.assertFalse(any("🧑" in line for line in self._map_rows(rendered)))
        self.assertIn("你对【Bob】说：雪原见", self.cmd("对话 Bob 雪原见", self.a))
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
        match = re.search(r"队伍 ([A-Z0-9]{6})", created)
        assert match is not None, "team id must be present"
        lobby_id = match.group(1)
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
        self.assertIn("第 1 层 · 雾隐雪原", party_view)
        self.assertIn("👤 【在场人物】【🧑Alice】", party_view)
        self.assertFalse(any("🧑" in line or "👥" in line for line in self._map_rows(party_view)))
        self.assertIsNone(self.plugin.save_manager.get_lobby(lobby_id))

    def test_solo_dungeon_isolation_coop_visibility_battle_log_and_coord(self):
        self.cmd("start confirm", self.a)
        self.cmd("start confirm", self.b)
        solo_a = self.cmd("c 1", self.a)
        solo_b = self.cmd("c 1", self.b)
        self.assertNotIn("🧑Bob", solo_a)
        self.assertNotIn("🧑Alice", solo_b)
        self.assertIn("没有找到", self.cmd("talk Bob 听得到吗", self.a))
        self.cmd("放弃 confirm", self.a)
        self.cmd("放弃 confirm", self.b)

        for uid in (self.a, self.b):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.purchased_pool = ["ironclad_rampart", "abyss_collapse", "jack_brew"]
            stats.locked_cards = ["ironclad_rampart", "abyss_collapse", "jack_brew"]
            self.plugin.save_manager.save_stats(uid, stats)

        started = self._start_coop_run()
        self.assertIn("👤 【在场人物】【🧑Bob】", started)
        start_coord_view = self.cmd("team coord", self.a)
        self.assertIn("第 1 层", start_coord_view)
        self.assertIn("出生点", start_coord_view)

        self.cmd("c 1", self.a)
        b_grid = self.cmd("c 1", self.b)
        self.assertIn("👤 【在场人物】【🧑Alice】", b_grid)
        self.assertNotIn("与玩家交谈", b_grid)

        dcmd = self._first_walkable_direction(self.a)
        moved_a = self.cmd(dcmd, self.a)
        run_after_move = load_run(self.plugin, self.a)
        if run_after_move.node_type == "battle_prompt":
            self.cmd("3", self.a)
        self.assertNotIn("🧑Bob", moved_a)
        self.assertIn("没有找到", self.cmd("talk Bob 在吗", self.a))
        coord_view = self.cmd("team xyz", self.b)
        self.assertIn("第 1 层", coord_view)
        self.assertIn("Alice", coord_view)
        self.assertIn("Bob", coord_view)

        _, run_b_battle = move_to_room(self.plugin, self.b, ("battle", "elite", "boss"))
        self.assertIsNotNone(run_b_battle)
        if run_b_battle.node_type == "grid_map":
            move_to_room(self.plugin, self.b, ("battle", "elite", "boss"))
            run_b_battle = load_run(self.plugin, self.b)
        battle_coord = floor_of(run_b_battle).player_coords.get(self.b)
        self.cmd("1", self.b)
        run_b_battle = load_run(self.plugin, self.b)
        self.assertEqual(run_b_battle.node_type, "battle")

        move_res, run_a_moved = move_to_room(self.plugin, self.a, ("battle", "elite", "boss"))
        if run_a_moved and run_a_moved.node_type == "battle_prompt":
            self.cmd("3", self.a)
        run_a_now = load_run(self.plugin, self.a)
        if run_a_now and floor_of(run_a_now).player_coords.get(self.a) != battle_coord:
            self.cmd(f"tp {battle_coord}", self.a)
            run_a_now = load_run(self.plugin, self.a)
            if run_a_now and run_a_now.node_type == "battle_prompt":
                self.cmd("3", self.a)
        a_coord_now = floor_of(load_run(self.plugin, self.a)).player_coords.get(self.a)
        if a_coord_now == battle_coord:
            b_battle_render = self.cmd("r", self.b)
            self.assertIn("👤 【在场人物】【🧑Alice】", b_battle_render)
            self.assertIn("你对【Bob】说：战斗必胜", self.cmd("talk Bob 战斗必胜", self.a))
            turn_res = self.cmd("e", self.b)
            self.assertIn("💬 【Alice】对你说：战斗必胜", turn_res)

    def test_coop_downstairs_barrier_waits_for_all_alive_members(self):
        for uid in (self.a, self.b):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.purchased_pool = ["glacier_fortress", "abyss_collapse", "frost_nova", "jack_brew", "meteor_swarm"]
            stats.locked_cards = ["glacier_fortress", "abyss_collapse", "jack_brew"]
            self.plugin.save_manager.save_stats(uid, stats)

        self._start_coop_run()
        self.cmd("c 1", self.a)
        self.cmd("c 1", self.b)

        for _ in range(6):
            run = self.plugin.save_manager.load_save(self.a)
            if not run:
                break
            if run.node_type != "grid_map":
                self._clear_battle_if_needed([self.a, self.b])
            run = self.plugin.save_manager.load_save(self.a)
            if not run or any(r.room_type == "downstairs" for r in floor_of(run).rooms.values()):
                break
            _, moved = move_to_room(self.plugin, self.a, ("boss",), rally=True)
            if moved and moved.node_type != "grid_map":
                self._clear_battle_if_needed([self.a, self.b])
            run_check = self.plugin.save_manager.load_save(self.a)
            if not run_check or any(r.room_type == "downstairs" for r in floor_of(run_check).rooms.values()):
                break
            move_to_room(self.plugin, self.a, ("battle", "elite", "high_danger"))
            self._clear_battle_if_needed([self.a, self.b])

        self._clear_battle_if_needed([self.a, self.b])
        run = load_run(self.plugin, self.a)
        ds_coords = [c for c, r in floor_of(run).rooms.items() if r.room_type == "downstairs"]
        self.assertTrue(ds_coords)
        ds_coord = ds_coords[0]

        if floor_of(run).player_coords.get(self.a) != ds_coord:
            self.cmd(f"tp {ds_coord}", self.a)
        if floor_of(run).player_coords.get(self.b) != ds_coord:
            move_to_room(self.plugin, self.b, ("downstairs",))
            run_b_now = load_run(self.plugin, self.b)
            if floor_of(run_b_now).player_coords.get(self.b) != ds_coord:
                self.cmd(f"tp {ds_coord}", self.b)

        self.assertIn("第 1 层下楼回廊", self.cmd("talk", self.a))
        wait_res = self.cmd("c 1", self.a)
        self.assertIn("等待全队汇合下楼", wait_res)
        self.assertIn("已就绪队友：Alice", wait_res)
        self.assertIn("尚未到达：Bob", wait_res)

        run_still_floor1 = load_run(self.plugin, self.b)
        self.assertEqual(floor_of(run_still_floor1).floor_index, 1)

        coord_waiting = self.cmd("team coord", self.b)
        self.assertIn("等待下楼", coord_waiting)

        a_deck_count = len(load_run(self.plugin, self.a).player.deck)
        a_relic_count = len(load_run(self.plugin, self.a).player.relics)
        self.cmd("离开", self.a)
        reopen = self.cmd("talk", self.a)
        self.assertIn("确认原地等待全员下楼", reopen)
        self.assertNotIn("先古卡牌", reopen)
        self.cmd("1", self.a)
        self.assertEqual(len(load_run(self.plugin, self.a).player.deck), a_deck_count)
        self.assertEqual(len(load_run(self.plugin, self.a).player.relics), a_relic_count)

        self.assertIn("第 1 层下楼回廊", self.cmd("talk", self.b))
        descend_res = self.cmd("c 1", self.b)
        self.assertIn("第 2 层", descend_res)

        run_floor2_b = load_run(self.plugin, self.b)
        self.assertEqual(floor_of(run_floor2_b).floor_index, 2)
        alice_after_descend = self.cmd("r", self.a)
        self.assertIn("第 2 层", alice_after_descend)
        self.assertIn("已汇合确认下楼", alice_after_descend)
        self.assertIn("👤 【在场人物】【🧑Bob】", alice_after_descend)

    def test_presence_expires_after_timeout(self):
        service = WorldPresenceService(self.plugin.save_manager)
        service.touch(self.a, WORLD_TOWN, "C2")
        self.assertEqual(len(service.players(WORLD_TOWN)), 1)
        with patch("game.core.world.presence.time.time", return_value=time.time() + WORLD_PRESENCE_TIMEOUT_SECONDS + 1):
            self.assertEqual(service.players(WORLD_TOWN), [])
