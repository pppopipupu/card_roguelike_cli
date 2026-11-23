import asyncio
import heapq
import random
import re
import tempfile
import unittest

from game.core.world.grid_map_generator import coord_to_xy, xy_to_coord
from game.entities.cards.market import is_card_available
from game.test.core.base import CorePlugin, floor_of, load_run, move_to_room, run_command


class TestBleakFallsAndSize(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(2026)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.sm = self.plugin.save_manager

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, cmd: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, cmd, sender_id=uid))

    def _prepare_seasoned_stats(self, uid: str, *, gp: int = 0):
        stats = self.sm.load_stats(uid)
        stats.selected_class = "法师"
        stats.town_health_bonus = 800
        stats.gp = gp
        stats.locked_cards = ["sunburst", "sunburst"]
        self.sm.save_stats(uid, stats)

    def _finish_current_battle(self, uid: str, *, max_turns: int = 80):
        last_grid_out = ""
        for _ in range(max_turns):
            run = load_run(self.plugin, uid)
            if run.node_type == "battle":
                for _ in range(8):
                    run = load_run(self.plugin, uid)
                    if run.node_type != "battle":
                        break
                    p = run.player
                    pick = None
                    for prio in (("sunburst",), ("fire_bolt", "magic_missile", "fus_ro_dah"), ("shield", "first_aid")):
                        for idx, c in enumerate(p.hand, 1):
                            if c.id in prio and p.actions >= 1:
                                pick = idx
                                break
                        if pick is not None:
                            break
                    if pick is not None:
                        res = self.run_cmd(f"p {pick}", uid)
                        if load_run(self.plugin, uid).node_type == "grid_map":
                            return res
                        continue
                    break
                run = load_run(self.plugin, uid)
                if run.node_type == "battle":
                    res = self.run_cmd("e", uid)
                    if load_run(self.plugin, uid).node_type == "grid_map":
                        return res
            elif run.node_type == "boss_chest":
                out = self.run_cmd("1", uid)
                if load_run(self.plugin, uid).node_type == "grid_map":
                    return out
                out = self.run_cmd("离开", uid)
                if load_run(self.plugin, uid).node_type == "grid_map":
                    return out
            elif run.node_type == "reward":
                out = self.run_cmd("离开", uid)
                if load_run(self.plugin, uid).node_type == "grid_map":
                    return out
            elif run.node_type == "grid_map":
                return last_grid_out
            else:
                out = self.run_cmd("exit", uid)
                if load_run(self.plugin, uid).node_type == "grid_map":
                    return out
                out = self.run_cmd("离开", uid)
                if load_run(self.plugin, uid).node_type == "grid_map":
                    return out
        return last_grid_out

    def _walk_to_coord(self, uid: str, target_coord: str) -> str:
        last = ""
        for _ in range(16):
            run = load_run(self.plugin, uid)
            if run.node_type == "battle":
                last = self._finish_current_battle(uid)
                run = load_run(self.plugin, uid)
            if run.node_type != "grid_map":
                self.run_cmd("离开", uid)
                run = load_run(self.plugin, uid)
            if run.node_type != "grid_map":
                break
            fm = floor_of(run)
            start = fm.player_coords.get(uid, "")
            if start == target_coord:
                break
            dist = {start: 0}
            prev = {}
            pq = [(0, start)]
            while pq:
                d, cur = heapq.heappop(pq)
                if cur == target_coord:
                    break
                if d > dist.get(cur, 10**9):
                    continue
                cx, cy = coord_to_xy(cur)
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < fm.width and 0 <= ny < fm.height):
                        continue
                    nc = xy_to_coord(nx, ny)
                    rm = fm.rooms.get(nc)
                    if rm is None or rm.room_type in ("wall", "solid_wall"):
                        continue
                    if rm.room_type == "secret_boss" and not fm.secret_unlocked:
                        continue
                    step_cost = 1 if (rm.cleared or nc == target_coord or rm.room_type in ("empty", "spawn")) else 20
                    nd = d + step_cost
                    if nd < dist.get(nc, 10**9):
                        dist[nc] = nd
                        prev[nc] = cur
                        heapq.heappush(pq, (nd, nc))
            if target_coord not in prev:
                break
            path = []
            cur = target_coord
            while cur != start:
                p = prev[cur]
                px, py = coord_to_xy(p)
                cx, cy = coord_to_xy(cur)
                dcmd = {(0, -1): "w", (0, 1): "s", (-1, 0): "a", (1, 0): "d"}[(cx - px, cy - py)]
                path.append((cur, dcmd))
                cur = p
            path.reverse()
            for idx, (step_coord, dcmd) in enumerate(path):
                for _ in range(4):
                    last = self.run_cmd(dcmd, uid)
                    run = load_run(self.plugin, uid)
                    if run.node_type != "grid_map" or floor_of(run).player_coords.get(uid) == step_coord:
                        break
                if run.node_type == "battle":
                    last = self._finish_current_battle(uid)
                elif run.node_type in ("shop", "rest", "cafe", "landmark", "life_merchant", "treasure") and idx < len(path) - 1:
                    self.run_cmd("离开", uid)
                elif run.node_type == "event" and idx < len(path) - 1:
                    opts = run.node_data.get("options", [])
                    if opts:
                        self.run_cmd(str(len(opts)), uid)
            if floor_of(load_run(self.plugin, uid)).player_coords.get(uid) == target_coord:
                break
        return last

    def _complete_barrow_from_floor1_to_floor2(self, uid: str):
        self.run_cmd("start confirm", uid)
        self.run_cmd("1", uid)
        boss_coord = next(c for c, r in floor_of(load_run(self.plugin, uid)).rooms.items() if r.room_type == "boss")
        boss_clear_out = self._walk_to_coord(uid, boss_coord)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "grid_map")
        self.assertIn("白漫城宫廷法师", boss_clear_out)
        self.assertIn("QGP炸弹", boss_clear_out)
        self.assertIn("qgp_bomb", run.player.bag_items)
        self.assertIn("farengar_court_mage", floor_of(run).rooms[floor_of(run).player_coords[uid]].npcs)

        quest_step1 = self.run_cmd("quest", uid)
        self.assertIn("荒爆古坟的秘密", quest_step1)
        self.assertIn("固体墙", quest_step1)
        self.assertNotIn("尸鬼领主", quest_step1)
        self.assertNotIn("黄金龙爪机关门", quest_step1)
        self.assertNotIn("[ ]", quest_step1)
        self.assertNotIn("[x]", quest_step1)

        talk_mage = self.run_cmd("talk 白漫城宫廷法师", uid)
        self.assertIn("QGP炸弹", talk_mage)
        self.run_cmd("1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "grid_map")

        wall_coord = next(c for c, r in floor_of(run).rooms.items() if r.room_type == "solid_wall")
        bomb_res = self.run_cmd("use QGP炸弹", uid)
        self.assertIn("荒爆古坟入口", bomb_res)
        run = load_run(self.plugin, uid)
        self.assertEqual(floor_of(run).rooms[wall_coord].room_type, "bleak_falls_entrance")

        self._walk_to_coord(uid, wall_coord)
        ent_talk = self.run_cmd("talk", uid)
        self.assertIn("踏入第 1.5 层", ent_talk)
        enter_1_5 = self.run_cmd("1", uid)
        self.assertIn("1.5", enter_1_5)
        self.assertIn("荒爆古坟", enter_1_5)
        run = load_run(self.plugin, uid)
        self.assertEqual(floor_of(run).floor_index, 1.5)
        if run.node_type == "ancient":
            self.run_cmd("c 1", uid)

        self._walk_to_coord(uid, "B3")
        self._walk_to_coord(uid, "B2")
        clue_res = self.run_cmd("touch 刻纹石碑", uid)
        self.assertIn("蛇 — 蛇 — 鲸", clue_res)

        self._walk_to_coord(uid, "C2")
        self.run_cmd("talk", uid)
        wrong_res = self.run_cmd("2", uid)
        self.assertIn("毒石镖", wrong_res)
        self.run_cmd("talk", uid)
        solved_res = self.run_cmd("1", uid)
        self.assertIn("精准卡位", solved_res)
        self.assertIn("诺德蜂蜜酒", solved_res)
        self.assertNotIn("i18n_", solved_res)

        spider_out = self._walk_to_coord(uid, "C3")
        self.assertIn("阿尔维尔", spider_out)
        arvel_dlg = self.run_cmd("talk", uid)
        self.assertIn("黄金龙爪", arvel_dlg)
        self.run_cmd("1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.node_type, "battle")
        arvel_win = self._finish_current_battle(uid)
        self.assertIn("黄金龙爪", arvel_win)
        run = load_run(self.plugin, uid)
        self.assertIn("golden_claw", run.player.bag_items)
        journal_out = self.run_cmd("use 阿尔维尔的日记", uid)
        self.assertIn("熊、飞蛾、猫头鹰", journal_out)

        self._walk_to_coord(uid, "E3")
        gate_talk = self.run_cmd("talk", uid)
        self.assertIn("1.67777", gate_talk)
        enter_sanctuary = self.run_cmd("1", uid)
        self.assertIn("1.67777", enter_sanctuary)
        self.assertIn("荒爆圣所", enter_sanctuary)
        run = load_run(self.plugin, uid)
        self.assertEqual(floor_of(run).floor_index, 1.67777)
        if run.node_type == "ancient":
            self.run_cmd("c 1", uid)

        self._walk_to_coord(uid, "B2")
        self._walk_to_coord(uid, "C2")
        blocked = self.run_cmd("d", uid)
        self.assertIn("黄金龙爪机关门尚未开启", blocked)

        claw_dlg = self.run_cmd("talk", uid)
        self.assertIn("熊 — 飞蛾 — 猫头鹰", claw_dlg)
        opened_msg = self.run_cmd("1", uid)
        self.assertIn("黄金龙爪", opened_msg)
        run = load_run(self.plugin, uid)
        self.assertIn("golden_claw", run.player.bag_items)

        self._walk_to_coord(uid, "D2")
        self.run_cmd("talk", uid)
        ww_msg = self.run_cmd("1", uid)
        self.assertIn("龙语", ww_msg)

        boss_out = self._walk_to_coord(uid, "E2")
        self.assertIn("龙石", boss_out)
        run = load_run(self.plugin, uid)
        self.assertEqual(floor_of(run).rooms["E2"].room_type, "barrow_exit")

        exit_dlg = self.run_cmd("talk", uid)
        self.assertIn("第 2 层", exit_dlg)
        to_floor2 = self.run_cmd("1", uid)
        self.assertIn("第 2 层", to_floor2)
        run = load_run(self.plugin, uid)
        self.assertEqual(floor_of(run).floor_index, 2)

        q_floor2 = self.run_cmd("quest", uid)
        self.assertIn("第 2 层", q_floor2)
        self.assertIn("主城酒馆", q_floor2)

        self.run_cmd("abandon confirm", uid)

    def test_bleak_falls_return_dragonstone_unlocks_fus_ro_dah(self):
        uid = "bf_return_user"
        pre_stats = self.sm.load_stats(uid)
        self.assertFalse(is_card_available("fus_ro_dah", pre_stats))

        self._prepare_seasoned_stats(uid)
        self._complete_barrow_from_floor1_to_floor2(uid)

        self.run_cmd("主城", uid)
        self.run_cmd("right", uid)
        self.run_cmd("right", uid)
        tavern_out = self.run_cmd("up", uid)
        self.assertIn("白漫城宫廷法师", tavern_out)

        talk_out = self.run_cmd("talk 法仁加", uid)
        self.assertIn("交回【龙石】", talk_out)
        self.assertIn("欺骗法仁加", talk_out)

        ret_num = None
        for line in talk_out.splitlines():
            if "交回【龙石】" in line and "." in line:
                ret_num = line.split(".", 1)[0].strip()
                break
        self.assertIsNotNone(ret_num)
        ret_out = self.run_cmd(str(ret_num), uid)
        self.assertIn("Fus Ro Dah!", ret_out)
        self.run_cmd("exit", uid)

        stats = self.sm.load_stats(uid)
        self.assertTrue(is_card_available("fus_ro_dah", stats))
        self.assertEqual(stats.town_flags.get("quest_bleak_falls_outcome"), "returned")
        self.assertNotIn("dragonstone", stats.town_inventory)

        q_done = self.run_cmd("quest", uid)
        self.assertIn("已完成", q_done)
        self.assertIn("Fus Ro Dah!", q_done)

    def test_bleak_falls_deceive_farengar_keeps_dragonstone_and_claw(self):
        uid = "bf_deceive_user"
        self._prepare_seasoned_stats(uid)
        self._complete_barrow_from_floor1_to_floor2(uid)

        self.run_cmd("主城", uid)
        self.run_cmd("right", uid)
        self.run_cmd("right", uid)
        self.run_cmd("up", uid)
        talk_dec = self.run_cmd("talk 法仁加", uid)
        dec_num = None
        for line in talk_dec.splitlines():
            if "欺骗法仁加" in line and "." in line:
                dec_num = line.split(".", 1)[0].strip()
                break
        self.assertIsNotNone(dec_num)
        dec_out = self.run_cmd(str(dec_num), uid)
        self.assertIn("根本空空如也", dec_out)
        self.run_cmd("exit", uid)

        stats = self.sm.load_stats(uid)
        self.assertFalse(is_card_available("fus_ro_dah", stats))
        self.assertEqual(stats.town_flags.get("quest_bleak_falls_outcome"), "kept")
        self.assertIn("dragonstone", stats.town_inventory)
        self.assertIn("golden_claw", stats.town_inventory)

        again_talk = self.run_cmd("talk 法仁加", uid)
        self.assertIn("难道龙石从一开始真的就不存在", again_talk)

    def test_fus_ro_dah_stuns_up_to_large_for_two_turns_and_spares_larger(self):
        uid = "fus_battle_user"
        stats = self.sm.load_stats(uid)
        stats.selected_class = "法师"
        stats.town_health_bonus = 200
        stats.town_flags["fus_ro_dah_unlocked"] = True
        stats.unlocked_new_cards.append("fus_ro_dah")
        stats.locked_cards = ["fus_ro_dah", "fus_ro_dah"]
        self.sm.save_stats(uid, stats)

        self.run_cmd("主城", uid)
        self.run_cmd("up", uid)
        self.run_cmd("attack xXx_SniperElite_xXx", uid)
        run = load_run(self.plugin, uid)
        fus_idx = next(i for i, c in enumerate(run.player.hand, 1) if c.id == "fus_ro_dah")
        shout_res = self.run_cmd(f"p {fus_idx}", uid)
        self.assertIn("正面吹飞", shout_res)
        self.assertIn("2 回合", shout_res)

        run = load_run(self.plugin, uid)
        stun_buff = next((b for b in run.enemies[0].buffs if b.id == "stun"), None)
        self.assertIsNotNone(stun_buff)
        assert stun_buff is not None
        self.assertEqual(stun_buff.stacks, 2)

        turn1_res = self.run_cmd("e", uid)
        self.assertIn("眩晕状态，本回合无法行动", turn1_res)
        turn2_res = self.run_cmd("e", uid)
        self.assertIn("眩晕状态，本回合无法行动", turn2_res)
        run_after_2 = load_run(self.plugin, uid)
        self.assertFalse(any(b.id == "stun" for b in run_after_2.enemies[0].buffs))
        self.run_cmd("abandon confirm", uid)

        boss_uid = "fus_dragon_user"
        b_stats = self.sm.load_stats(boss_uid)
        b_stats.selected_class = "法师"
        b_stats.town_health_bonus = 200
        b_stats.town_flags["fus_ro_dah_unlocked"] = True
        b_stats.unlocked_new_cards.append("fus_ro_dah")
        b_stats.locked_cards = ["fus_ro_dah", "fus_ro_dah"]
        self.sm.save_stats(boss_uid, b_stats)

        found_dragon = False
        for seed_val in range(1, 30):
            self.sm.delete_save(boss_uid)
            random.seed(seed_val)
            self.run_cmd("start confirm", boss_uid)
            self.run_cmd("1", boss_uid)
            _, run_try = move_to_room(self.plugin, boss_uid, "boss")
            if run_try.enemies and run_try.enemies[0].name == "远古红龙":
                found_dragon = True
                break
        self.assertTrue(found_dragon)
        for _ in range(3):
            run_d = load_run(self.plugin, boss_uid)
            if any(e.name == "魔仆" for e in run_d.enemies):
                break
            self.run_cmd("e", boss_uid)
        run_d = load_run(self.plugin, boss_uid)
        fus_idx2 = next((i for i, c in enumerate(run_d.player.hand, 1) if c.id == "fus_ro_dah"), None)
        if fus_idx2 is not None:
            dragon_out = self.run_cmd(f"p {fus_idx2}", boss_uid)
            self.assertIn("未被龙吼吹退", dragon_out)
            run_d_after = load_run(self.plugin, boss_uid)
            self.assertFalse(any(b.id == "stun" for b in run_d_after.enemies[0].buffs))
            for e in run_d_after.enemies[1:]:
                if e.hp > 0:
                    self.assertTrue(any(b.id == "stun" and b.stacks == 2 for b in e.buffs))

    def test_in_run_and_multi_run_map_quests(self):
        uid = "map_quest_user"
        self._prepare_seasoned_stats(uid)
        random.seed(1)
        self.run_cmd("start confirm", uid)
        self.run_cmd("1", uid)
        run = load_run(self.plugin, uid)
        fm = floor_of(run)
        keeper_coord = next(c for c, r in fm.rooms.items() if "brazier_keeper" in r.npcs)
        surveyor_coord = next(c for c, r in fm.rooms.items() if "map_surveyor" in r.npcs)

        self._walk_to_coord(uid, keeper_coord)
        k_dlg = self.run_cmd("talk 古坛守望者", uid)
        self.assertIn("熄灭的古坛火盆", k_dlg)
        self.run_cmd("1", uid)

        self._walk_to_coord(uid, surveyor_coord)
        s_dlg = self.run_cmd("talk 星界制图师", uid)
        self.assertIn("古代制图师的残卷", s_dlg)
        self.run_cmd("1", uid)

        q_mid = self.run_cmd("quest", uid)
        self.assertIn("熄灭的古坛火盆", q_mid)
        self.assertIn("古代制图师的残卷", q_mid)
        self.assertNotIn("[ ]", q_mid)

        self.run_cmd("abandon confirm", uid)
        self.run_cmd("start confirm", uid)
        self.run_cmd("1", uid)
        q_next = self.run_cmd("quest", uid)
        self.assertIn("古代制图师的残卷", q_next)
        self.assertIn("跨局", q_next)


    def _finish_coop_battle(self, uids: list[str], *, max_turns: int = 80) -> str:
        last_out = ""
        for _ in range(max_turns):
            if all(load_run(self.plugin, u).node_type == "grid_map" for u in uids):
                return last_out
            for u in uids:
                run = load_run(self.plugin, u)
                if run.node_type == "battle":
                    for _ in range(8):
                        run = load_run(self.plugin, u)
                        if run.node_type != "battle":
                            break
                        pl = run.player
                        pick = None
                        for prio in (("sunburst",), ("fire_bolt", "magic_missile", "fus_ro_dah"), ("shield", "first_aid")):
                            for idx, c in enumerate(pl.hand, 1):
                                if c.id in prio and pl.actions >= 1:
                                    pick = idx
                                    break
                            if pick is not None:
                                break
                        if pick is not None:
                            last_out = self.run_cmd(f"p {pick}", u)
                            continue
                        break
                    if load_run(self.plugin, u).node_type == "battle":
                        last_out = self.run_cmd("e", u)
                elif run.node_type == "boss_chest":
                    last_out = self.run_cmd("1", u)
                    if load_run(self.plugin, u).node_type != "grid_map":
                        last_out = self.run_cmd("离开", u)
                elif run.node_type == "reward":
                    last_out = self.run_cmd("离开", u)
                elif run.node_type == "event":
                    last_out = self.run_cmd("1", u)
                    if load_run(self.plugin, u).node_type == "event":
                        last_out = self.run_cmd("离开", u)
                elif run.node_type != "grid_map":
                    last_out = self.run_cmd("离开", u)
                    if load_run(self.plugin, u).node_type != "grid_map":
                        last_out = self.run_cmd("exit", u)
        return last_out

    def _walk_coop_to_coord(self, actor: str, uids: list[str], target_coord: str, *, stop_on_battle: bool = False) -> str:
        last = ""
        for _ in range(16):
            run = load_run(self.plugin, actor)
            if run.node_type == "battle":
                if stop_on_battle:
                    return last
                last = self._finish_coop_battle(uids)
                run = load_run(self.plugin, actor)
            if run.node_type != "grid_map":
                last = self._finish_coop_battle(uids)
                run = load_run(self.plugin, actor)
            if run.node_type != "grid_map":
                break
            fm = floor_of(run)
            start = fm.player_coords.get(actor, "")
            if start == target_coord:
                break
            dist = {start: 0}
            prev = {}
            pq = [(0, start)]
            while pq:
                d, cur = heapq.heappop(pq)
                if d > dist.get(cur, 10**9):
                    continue
                if cur == target_coord:
                    break
                cx, cy = coord_to_xy(cur)
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < fm.width and 0 <= ny < fm.height):
                        continue
                    nc = xy_to_coord(nx, ny)
                    rm = fm.rooms[nc]
                    if rm.room_type in ("wall", "solid_wall", "obstacle"):
                        continue
                    cost = 1 if (nc == target_coord or rm.cleared or rm.room_type in ("empty", "spawn")) else 6
                    nd = d + cost
                    if nd < dist.get(nc, 10**9):
                        dist[nc] = nd
                        prev[nc] = cur
                        heapq.heappush(pq, (nd, nc))
            if target_coord not in prev:
                break
            step = target_coord
            while prev[step] != start:
                step = prev[step]
            sx, sy = coord_to_xy(start)
            tx, ty = coord_to_xy(step)
            cmd = {(0, -1): "w", (0, 1): "s", (-1, 0): "a", (1, 0): "d"}[(tx - sx, ty - sy)]
            last = self.run_cmd(cmd, actor)
            if load_run(self.plugin, actor).node_type == "ally_summon_select":
                last = self.run_cmd("c 1", actor)
            if load_run(self.plugin, actor).node_type == "battle":
                if stop_on_battle and floor_of(load_run(self.plugin, actor)).player_coords.get(actor) == target_coord:
                    return last
                last = self._finish_coop_battle(uids)
        return last

    def test_bleak_falls_coop_arvel_solo_no_duplicate_and_boss_team(self):
        uid_a = "bf_coop_a"
        uid_b = "bf_coop_b"
        uids = [uid_a, uid_b]
        for u in uids:
            self._prepare_seasoned_stats(u, gp=5000)
        self.run_cmd("friend name 古坟队长", uid_a)
        self.run_cmd("friend name 古坟队员", uid_b)
        stats_a = self.sm.load_stats(uid_a)
        stats_b = self.sm.load_stats(uid_b)
        handle_a = stats_a.player_handle or stats_a.player_name
        handle_b = stats_b.player_handle or stats_b.player_name
        self.run_cmd(f"friend add {handle_b}", uid_a)
        self.run_cmd(f"friend accept {handle_a}", uid_b)
        created = self.run_cmd("team create", uid_a)
        match = re.search(r"队伍 ([A-Z0-9]{6})", created)
        assert match is not None
        room_code = match.group(1)
        self.run_cmd(f"friend invite {handle_b}", uid_a)
        self.run_cmd(f"team join {room_code}", uid_b)
        self.run_cmd("team ready", uid_b)
        self.run_cmd("team start", uid_a)
        for u in uids:
            self.run_cmd("c 1", u)

        boss_coord = next(c for c, r in floor_of(load_run(self.plugin, uid_a)).rooms.items() if r.room_type == "boss")
        self._walk_coop_to_coord(uid_a, uids, boss_coord)
        run_a = load_run(self.plugin, uid_a)
        self.assertEqual(run_a.node_type, "grid_map")
        wall_coord = next(c for c, r in floor_of(run_a).rooms.items() if r.room_type == "solid_wall")
        bomb_holder = uid_a if "qgp_bomb" in run_a.players[uid_a].bag_items else uid_b
        self.run_cmd("use QGP炸弹", bomb_holder)
        ent_map = self._walk_coop_to_coord(bomb_holder, uids, wall_coord)
        self.assertIn("talk .", ent_map)
        self.run_cmd("talk .", bomb_holder)
        self.run_cmd("1", bomb_holder)
        self.assertEqual(floor_of(load_run(self.plugin, uid_a)).floor_index, 1.5)
        for u in uids:
            if load_run(self.plugin, u).node_type == "ancient":
                self.run_cmd("c 1", u)

        self._walk_coop_to_coord(uid_a, uids, "B3", stop_on_battle=True)
        run_b3 = load_run(self.plugin, uid_a)
        self.assertEqual(run_b3.node_type, "battle")
        self.assertEqual(run_b3.node_data.get("battle_mode"), "solo")
        self.assertEqual(load_run(self.plugin, uid_b).node_type, "grid_map")
        self._finish_coop_battle(uids)

        self._walk_coop_to_coord(uid_a, uids, "C3", stop_on_battle=True)
        run_c3 = load_run(self.plugin, uid_a)
        self.assertEqual(run_c3.node_type, "battle")
        self.assertEqual(run_c3.node_data.get("battle_mode"), "solo")
        self._finish_coop_battle(uids)

        self.run_cmd("tp C3", uid_b)
        self.run_cmd("talk .", uid_a)
        self.run_cmd("talk .", uid_b)
        self.run_cmd("1", uid_a)
        arvel_a = load_run(self.plugin, uid_a)
        self.assertEqual(arvel_a.node_type, "battle")
        self.assertEqual(arvel_a.node_data.get("battle_mode"), "solo")
        sid_a = floor_of(arvel_a).player_session_map.get(uid_a, "")
        self.assertTrue(sid_a)

        join_out = self.run_cmd("1", uid_b)
        self.assertIn("加入", join_out)
        arvel_b = load_run(self.plugin, uid_b)
        self.assertEqual(arvel_b.node_type, "battle")
        fm_arvel = floor_of(arvel_b)
        battle_sessions = [s for s in fm_arvel.active_sessions.values() if s.node_type == "battle"]
        self.assertEqual(len(battle_sessions), 1)
        self.assertEqual(fm_arvel.player_session_map.get(uid_b), sid_a)
        self.assertIn(uid_a, battle_sessions[0].participants)
        self.assertIn(uid_b, battle_sessions[0].participants)
        self.assertEqual(len(arvel_b.enemies), 1)

        self._finish_coop_battle(uids)
        post_arvel = load_run(self.plugin, uid_a)
        self.assertIn("golden_claw", post_arvel.players[uid_a].bag_items + post_arvel.players[uid_b].bag_items)
        self.assertNotIn("arvel_trapped", floor_of(post_arvel).rooms["C3"].npcs)

        gate_map = self._walk_coop_to_coord(uid_a, uids, "E3")
        self.assertIn("talk .", gate_map)
        self.run_cmd("talk .", uid_a)
        self.run_cmd("1", uid_a)
        self.assertEqual(floor_of(load_run(self.plugin, uid_a)).floor_index, 1.67777)
        for u in uids:
            if load_run(self.plugin, u).node_type == "ancient":
                self.run_cmd("c 1", u)

        self._walk_coop_to_coord(uid_a, uids, "B2", stop_on_battle=True)
        run_s_b2 = load_run(self.plugin, uid_a)
        self.assertEqual(run_s_b2.node_type, "battle")
        self.assertEqual(run_s_b2.node_data.get("battle_mode"), "solo")
        self._finish_coop_battle(uids)

        claw_holder = uid_a if "golden_claw" in load_run(self.plugin, uid_a).player.bag_items else uid_b
        door_map = self._walk_coop_to_coord(claw_holder, uids, "C2")
        self.assertIn("talk .", door_map)
        self.run_cmd("talk .", claw_holder)
        self.run_cmd("1", claw_holder)

        self._walk_coop_to_coord(uid_a, uids, "E2", stop_on_battle=True)
        boss_a = load_run(self.plugin, uid_a)
        boss_b = load_run(self.plugin, uid_b)
        self.assertEqual(boss_a.node_type, "battle")
        self.assertEqual(boss_b.node_type, "battle")
        self.assertEqual(boss_a.node_data.get("battle_mode"), "team")
        fm_boss = floor_of(boss_a)
        self.assertEqual(fm_boss.player_session_map.get(uid_a), fm_boss.player_session_map.get(uid_b))
        self.assertIn(uid_a, boss_a.party_order)
        self.assertIn(uid_b, boss_a.party_order)
        milo = next((e for e in boss_a.enemies if "米洛克" in e.name), None)
        self.assertIsNotNone(milo)
        self.assertEqual(len(boss_a.enemies), 3)
        self.assertEqual(len(boss_a.node_data.get("enemy_targets", {})), 3)

if __name__ == "__main__":
    unittest.main()
