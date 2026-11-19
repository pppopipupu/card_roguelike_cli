import asyncio
import heapq
import random
import tempfile
import unittest
from unittest.mock import patch

from game.core.world.grid_map_generator import coord_to_xy, xy_to_coord
from game.test.core.base import CorePlugin, floor_of, load_run, run_command


class TestChireidenFusionCenter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.random_state = random.getstate()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def _cmd(self, cmd: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, cmd, uid))

    def _prepare_seasoned_stats(self, uid: str, *, locked_cards=None):
        stats = self.plugin.save_manager.load_stats(uid)
        stats.selected_class = "法师"
        stats.town_health_bonus = 2500
        stats.gp = 500
        stats.unlocked_gatekey = True
        stats.locked_cards = list(locked_cards or ["d_he3_fusion_ignition+", "lunar_he3_orbital_drop+"])
        stats.purchased_pool = [
            "hisoutensoku_thermonuclear_cannon+",
            "hisoutensoku_thermonuclear_cannon+",
            "d_he3_fusion_ignition+",
            "lunar_he3_orbital_drop+",
            "penning_trap_lockdown+",
            "pb_bi_coolant_loop+",
        ]
        self.plugin.save_manager.save_stats(uid, stats)

    def _pick_safe_start_option(self, uid: str):
        run = load_run(self.plugin, uid)
        opts = run.node_data.get("options", [])
        for idx, opt in enumerate(opts, 1):
            rel = str(opt.get("relic", ""))
            if "curse" not in rel and "shadow" not in rel and "trash" not in rel:
                return self._cmd(str(idx), uid)
        return self._cmd("1", uid)

    def _clear_reward_or_menu(self, uid: str):
        for _ in range(10):
            run = load_run(self.plugin, uid)
            nt = run.node_type
            if nt in ("grid_map", "battle"):
                return
            if nt in ("card_select", "upgrade_select", "remove_select"):
                self._cmd("0", uid)
                if load_run(self.plugin, uid).node_type == nt:
                    self._cmd("1", uid)
                continue
            if nt in ("reward", "boss_chest", "treasure"):
                items = run.node_data.get("items", [])
                forced_idx = next(
                    (i for i, it in enumerate(items, 1) if it.get("force") and not it.get("taken")),
                    None,
                )
                if forced_idx is not None:
                    self._cmd(str(forced_idx), uid)
                    continue
                if nt == "boss_chest":
                    opts = run.node_data.get("options", []) or items
                    picked = False
                    for idx, opt in enumerate(opts, 1):
                        oid = str(opt.get("id", opt.get("card_id", opt.get("relic_id", ""))))
                        if oid in (
                            "hisoutensoku_thermonuclear_cannon",
                            "d_he3_fusion_ignition",
                            "lunar_he3_orbital_drop",
                            "pb_bi_coolant_loop",
                            "penning_trap_lockdown",
                            "int19_tokamak_calculus",
                            "lunar_he3_capsule",
                            "penning_ion_stabilizer",
                            "lbe_fast_reactor_core",
                            "headband_of_intellect_int19",
                        ):
                            self._cmd(str(idx), uid)
                            picked = True
                            break
                    if not picked and opts and any(not it.get("taken") for it in items):
                        self._cmd("1", uid)
                self._cmd("离开", uid)
                continue
            if nt == "event":
                opts = run.node_data.get("options", [])
                if opts:
                    self._cmd(str(len(opts)), uid)
                else:
                    self._cmd("离开", uid)
                continue
            if nt == "landmark":
                opts = run.node_data.get("options", [])
                if opts:
                    self._cmd(str(len(opts)), uid)
                else:
                    self._cmd("离开", uid)
                continue
            if nt in ("shop", "rest", "cafe", "life_merchant"):
                self._cmd("离开", uid)
                continue
            self._cmd("离开", uid)

    def _finish_current_battle(self, uid: str, *, max_turns: int = 120, observe_portal: bool = False) -> dict:
        stats = {
            "phases_seen": set(),
            "utsuho_joined": False,
            "xen_seen": False,
            "reflect_or_curse_seen": False,
            "ally_played": False,
        }
        prio = (
            "int19_tokamak_calculus",
            "lunar_he3_orbital_drop",
            "penning_trap_lockdown",
            "hisoutensoku_thermonuclear_cannon",
            "sunburst",
            "d_he3_fusion_ignition",
            "pb_bi_coolant_loop",
            "fire_bolt",
            "magic_missile",
            "shield",
            "first_aid",
        )
        for _ in range(max_turns):
            run = load_run(self.plugin, uid)
            if run.node_type == "battle":
                if observe_portal:
                    for e in run.enemies:
                        if "超级传送门" in e.name:
                            stats["phases_seen"].add(e.name)
                        if getattr(e, "is_summon", False) and e.name.startswith("Xen"):
                            stats["xen_seen"] = True
                        for b in e.buffs:
                            if "reflect" in b.id or "thorns" in b.id:
                                stats["reflect_or_curse_seen"] = True
                    for c in (*run.player.hand, *run.player.draw_pile, *run.player.discard_pile):
                        if c.id in ("curse", "wound", "burn", "dazed", "void", "slimed"):
                            stats["reflect_or_curse_seen"] = True
                    if "merc_utsuho" in run.party_order and "merc_utsuho" in run.players:
                        stats["utsuho_joined"] = True
                for _ in range(18):
                    run = load_run(self.plugin, uid)
                    if run.node_type != "battle":
                        break
                    p = run.player
                    boss_idx = next(
                        (i + 1 for i, e in enumerate(run.enemies) if e.hp > 0 and not getattr(e, "is_summon", False)),
                        1,
                    )
                    candidates = []
                    for cid in prio:
                        for idx, c in enumerate(p.hand, 1):
                            if c.id == cid:
                                candidates.append(idx)
                    if not candidates:
                        break
                    a0, ba0, h0 = p.actions, p.bonus_actions, len(p.hand)
                    any_played = False
                    for pick in candidates:
                        for cmd_str in (f"p {pick} e{boss_idx}", f"p {pick}"):
                            self._cmd(cmd_str, uid)
                            chk = self.plugin.save_manager.load_save(uid)
                            if chk is None or chk.node_type != "battle":
                                any_played = True
                                break
                            if chk.player.actions != a0 or chk.player.bonus_actions != ba0 or len(chk.player.hand) != h0:
                                any_played = True
                                break
                        if any_played:
                            break
                    if not any_played:
                        break
                run = load_run(self.plugin, uid)
                if run.node_type == "battle":
                    self._cmd("e", uid)
                    run_after = load_run(self.plugin, uid)
                    self.assertNotIn(run_after.node_type, ("dead", "gameover"))
                    if observe_portal and "merc_utsuho" in run_after.players:
                        u = run_after.players["merc_utsuho"]
                        if u.discard_pile or u.hand:
                            stats["ally_played"] = True
            elif run.node_type == "grid_map":
                return stats
            else:
                self._clear_reward_or_menu(uid)
                if load_run(self.plugin, uid).node_type == "grid_map":
                    return stats
        return stats

    def _walk_to_coord(self, uid: str, target_coord: str, *, stop_on_target_battle: bool = False):
        for _ in range(18):
            run = load_run(self.plugin, uid)
            if run.node_type == "battle":
                self._finish_current_battle(uid)
                run = load_run(self.plugin, uid)
            if run.node_type != "grid_map":
                self._clear_reward_or_menu(uid)
                run = load_run(self.plugin, uid)
            if run.node_type != "grid_map":
                break
            fm = floor_of(run)
            start = fm.player_coords.get(uid, "")
            if start == target_coord:
                return
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
                    if rm is None or rm.room_type in ("wall", "solid_wall") or rm.locked:
                        continue
                    if rm.room_type == "secret_boss" and not fm.secret_unlocked:
                        continue
                    if rm.room_type == "boss" and not rm.cleared and nc != target_coord:
                        continue
                    if rm.room_type == "obstacle":
                        step_cost = 200
                    elif rm.room_type == "high_danger" and nc != target_coord:
                        step_cost = 80
                    elif rm.cleared or nc == target_coord or rm.room_type in ("empty", "start", "spawn"):
                        step_cost = 1
                    else:
                        step_cost = 20
                    nd = d + step_cost
                    if nd < dist.get(nc, 10**9):
                        dist[nc] = nd
                        prev[nc] = cur
                        heapq.heappush(pq, (nd, nc))
            self.assertIn(target_coord, prev, f"No path from {start} to {target_coord}")
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
                    self._cmd(dcmd, uid)
                    run = load_run(self.plugin, uid)
                    if run.node_type != "grid_map" or floor_of(run).player_coords.get(uid) == step_coord:
                        break
                if run.node_type == "battle":
                    if idx == len(path) - 1 and stop_on_target_battle:
                        return
                    self._finish_current_battle(uid)
                elif run.node_type != "grid_map" and idx < len(path) - 1:
                    self._clear_reward_or_menu(uid)
            if floor_of(load_run(self.plugin, uid)).player_coords.get(uid) == target_coord:
                return
        self.assertEqual(floor_of(load_run(self.plugin, uid)).player_coords.get(uid), target_coord)

    def test_touhou_npcs_hint_chireiden_rumors_and_greetings(self):
        uid = "touhou_rumor_u"
        self._prepare_seasoned_stats(uid)

        for hidden_query in (
            "i 智力头环",
            "i 地灵殿核聚变控制中心",
            "i 非想天则热核炮",
            "i 铅铋快堆实验大厅",
            "i 彭宁离子井·超级传送门·初阶裂隙",
            "i 灵乌路空",
            "i 聚变超载",
        ):
            pre_res = self._cmd(hidden_query, uid)
            self.assertIn("未找到", pre_res, f"Unexpectedly unlocked before meeting: {hidden_query}")

        found_reimu_room = None
        for seed_val in range(1, 35):
            self.plugin.save_manager.delete_save(uid)
            random.seed(seed_val)
            self._cmd("start confirm", uid)
            self._pick_safe_start_option(uid)
            run = load_run(self.plugin, uid)
            fm = floor_of(run)
            for coord, room in fm.rooms.items():
                if not room.locked and room.room_type == "big_room":
                    br = fm.big_rooms.get(room.big_room_id)
                    if br and "hakurei_reimu" in (br.npcs or []):
                        found_reimu_room = coord
                        break
            if found_reimu_room:
                break
        self.assertIsNotNone(found_reimu_room)
        assert found_reimu_room is not None
        self._walk_to_coord(uid, found_reimu_room)
        with patch("game.core.world.rooms.chaos_npcs.random.random", return_value=0.1):
            dlg = self._cmd("talk 博丽灵梦", uid)
            self.assertIn("博丽灵梦", dlg)
            reply = self._cmd("1", uid)
            self.assertIn("地灵殿", reply)
            self.assertIn("维修电梯", reply)
            self.assertIn("智力头环", reply)
            self.assertNotIn("INT 19", reply)
            self.assertNotIn("智力飙升", reply)
            self.assertNotIn("智力暴涨", reply)
            self.assertIn("chireiden_rumor_seeker", self.plugin.save_manager.load_stats(uid).unlocked_achievements)

            rumor_headband = self._cmd("i 智力头环", uid)
            self.assertIn("headband_of_intellect", rumor_headband)
            self.assertIn("灵乌路空", rumor_headband)
            self.assertNotIn("设定为 19", rumor_headband)
            self.assertNotIn("偶数回合", rumor_headband)

            rumor_floor = self._cmd("i 地灵殿核聚变控制中心", uid)
            self.assertIn("维修电梯", rumor_floor)
            self.assertIn("传闻线索", rumor_floor)

            rumor_utsuho = self._cmd("i 灵乌路空", uid)
            self.assertIn("未知（尚未", rumor_utsuho)
            self.assertNotIn("伪狱热核终焉日轮", rumor_utsuho)

            still_hidden_card = self._cmd("i 非想天则热核炮", uid)
            self.assertIn("未找到", still_hidden_card)
            still_hidden_portal = self._cmd("i 彭宁离子井·超级传送门·初阶裂隙", uid)
            self.assertIn("未找到", still_hidden_portal)

    def test_chireiden_cards_mechanics_against_training_dummy(self):
        card_pairs = (
            ("d_he3_fusion_ignition", "pb_bi_coolant_loop"),
            ("lunar_he3_orbital_drop", "int19_tokamak_calculus"),
            ("penning_trap_lockdown", "hisoutensoku_thermonuclear_cannon"),
        )
        all_used = set()
        for pair_idx, pair in enumerate(card_pairs):
            uid = f"chireiden_dummy_cards_u_{pair_idx}"
            stats = self.plugin.save_manager.load_stats(uid)
            stats.gp = 200
            stats.locked_cards = list(pair)
            self.plugin.save_manager.save_stats(uid, stats)
            self._cmd("主城", uid)
            self._cmd("home", uid)
            self._cmd("up", uid)
            self._cmd("talk Dummy", uid)
            self._cmd("2", uid)

            used_cards = set()
            for _ in range(18):
                run = load_run(self.plugin, uid)
                if run.node_type != "battle" or not run.enemies or run.enemies[0].hp <= 0:
                    break
                played_this_step = False
                for target_id in pair:
                    if target_id in used_cards:
                        continue
                    idx = next((i for i, cs in enumerate(run.player.hand, 1) if cs.id == target_id), None)
                    if idx is not None:
                        a0, ba0, h0 = run.player.actions, run.player.bonus_actions, len(run.player.hand)
                        self._cmd(f"p {idx} e1", uid)
                        chk = load_run(self.plugin, uid)
                        if chk.player.actions != a0 or chk.player.bonus_actions != ba0 or len(chk.player.hand) != h0:
                            used_cards.add(target_id)
                            all_used.add(target_id)
                            played_this_step = True
                            break
                if not played_this_step:
                    self._cmd("e", uid)
                if len(used_cards) == len(pair):
                    break
            self.assertEqual(used_cards, set(pair))
        self.assertEqual(len(all_used), 6)

        uid_oc = "chireiden_overcharge_u"
        stats_oc = self.plugin.save_manager.load_stats(uid_oc)
        stats_oc.gp = 200
        stats_oc.purchased_pool = [
            "int19_tokamak_calculus",
            "int19_tokamak_calculus",
            "d_he3_fusion_ignition",
            "d_he3_fusion_ignition",
            "d_he3_fusion_ignition",
            "d_he3_fusion_ignition",
            "d_he3_fusion_ignition",
            "d_he3_fusion_ignition",
        ]
        self.plugin.save_manager.save_stats(uid_oc, stats_oc)
        self._cmd("主城", uid_oc)
        self._cmd("home", uid_oc)
        self._cmd("up", uid_oc)
        self._cmd("talk Dummy", uid_oc)
        self._cmd("2", uid_oc)
        for _ in range(45):
            run_oc = load_run(self.plugin, uid_oc)
            if run_oc.node_type != "battle":
                break
            if any(b.id == "fusion_overcharge" and b.stacks >= 8 for b in run_oc.player.buffs):
                break
            played_any = False
            for target_id in ("int19_tokamak_calculus", "d_he3_fusion_ignition"):
                idx = next((i for i, cs in enumerate(run_oc.player.hand, 1) if cs.id == target_id), None)
                if idx is not None:
                    a0, ba0, h0 = run_oc.player.actions, run_oc.player.bonus_actions, len(run_oc.player.hand)
                    self._cmd(f"p {idx} e1", uid_oc)
                    chk_oc = load_run(self.plugin, uid_oc)
                    if chk_oc.player.actions != a0 or chk_oc.player.bonus_actions != ba0 or len(chk_oc.player.hand) != h0:
                        played_any = True
                        break
            if not played_any:
                self._cmd("e", uid_oc)
        stats_oc_after = self.plugin.save_manager.load_stats(uid_oc)
        self.assertIn("chireiden_overcharge_master", stats_oc_after.unlocked_achievements)

    def test_floor3_elevator_5x20_chireiden_bosses_and_utsuho_ally(self):
        uid = "chireiden_full_run_u"
        random.seed(2026)
        self._prepare_seasoned_stats(uid)

        self._cmd("start confirm", uid)
        self._pick_safe_start_option(uid)

        for floor_no in (1, 2, 3):
            run = load_run(self.plugin, uid)
            fm = floor_of(run)
            self.assertEqual(fm.floor_index, floor_no)
            self._walk_to_coord(uid, fm.boss_coord)
            self._finish_current_battle(uid)
            run = load_run(self.plugin, uid)
            fm = floor_of(run)
            downstairs_coord = next(c for c, r in fm.rooms.items() if r.room_type == "downstairs")
            self._walk_to_coord(uid, downstairs_coord)
            talk_out = self._cmd("talk", uid)
            if floor_no < 3:
                self._cmd("1", uid)
                run2 = load_run(self.plugin, uid)
                if run2.node_type == "downstairs":
                    self._cmd("1", uid)
                self._finish_current_battle(uid)
            else:
                self.assertIn("地灵殿核聚变控制中心", talk_out)
                run_ds = load_run(self.plugin, uid)
                opts = run_ds.node_data.get("options", [])
                elv_idx = next(i for i, o in enumerate(opts, 1) if o.get("action") == "enter_chireiden_3_5")
                enter_msg = self._cmd(str(elv_idx), uid)
                self.assertIn("地灵殿核聚变控制中心", enter_msg)

        run35 = load_run(self.plugin, uid)
        fm35 = floor_of(run35)
        self.assertEqual(fm35.floor_index, 3.5)
        self.assertEqual(fm35.width, 5)
        self.assertEqual(fm35.height, 20)
        self.assertEqual(len(fm35.rooms), 100)
        self.assertEqual(fm35.player_coords[uid], "C1")
        br_templates = {br.template_id for br in fm35.big_rooms.values()}
        self.assertEqual(
            br_templates,
            {
                "lunar_he3_elevator_hub",
                "pb_bi_fast_reactor_chamber",
                "d_he3_tokamak_array",
                "penning_ion_well_sanctum",
            },
        )
        self.assertTrue(fm35.rooms["C16"].locked)
        self.assertTrue(fm35.rooms["C19"].locked)
        self.assertTrue(fm35.rooms["C20"].locked)

        self._cmd("take 氦三聚变燃料罐", uid)
        use_he3 = self._cmd("use 氦三聚变燃料罐", uid)
        self.assertIn("氦三", use_he3)

        q_floor_full = self._cmd("i 地灵殿核聚变控制中心", uid)
        self.assertIn("5×20", q_floor_full)
        q_env_shaft = self._cmd("i 竖井维修电梯井道", uid)
        self.assertIn("chireiden_elevator_shaft", q_env_shaft)
        q_he3_item = self._cmd("i 氦三聚变燃料罐", uid)
        self.assertIn("he3_fuel_canister", q_he3_item)

        self._walk_to_coord(uid, "B3")
        cylinder_out = self._cmd("touch 氦三高纯物流储罐", uid)
        self.assertIn("储罐", cylinder_out)

        q_hub = self._cmd("i 月都氦三物流中继大厅", uid)
        self.assertIn("lunar_he3_elevator_hub", q_hub)
        q_prop = self._cmd("i 氦三高纯物流储罐", uid)
        self.assertIn("he3_storage_cylinder", q_prop)

        self._walk_to_coord(uid, "C5")
        self._cmd("talk", uid)
        term_out = self._cmd("2", uid)
        self.assertIn("铅铋冷却", term_out)
        q_term = self._cmd("i D-He3 聚变主控终端", uid)
        self.assertIn("chireiden_fusion_terminal", q_term)

        self._walk_to_coord(uid, "B7")
        rin_talk = self._cmd("talk 火焰猫燐", uid)
        self.assertIn("铅铋", rin_talk)
        rin_res = self._cmd("1", uid)
        self.assertIn("铅铋共晶冷却剂", rin_res)
        self._cmd("use 铅铋共晶冷却剂", uid)

        self._walk_to_coord(uid, "C10")
        self._finish_current_battle(uid)
        run_post_rin = load_run(self.plugin, uid)
        self.assertIn("lbe_fast_reactor_core", run_post_rin.player.relics)

        self._walk_to_coord(uid, "C13")
        self._cmd("talk", uid)
        stab_out = self._cmd("2", uid)
        self.assertIn("恢复", stab_out)

        self._walk_to_coord(uid, "C14")
        fm_pre_u = floor_of(load_run(self.plugin, uid))
        self.assertTrue(fm_pre_u.rooms["C16"].locked)
        self.assertFalse(fm_pre_u.floor_flags.get("chireiden_utsuho_defeated"))

        self._walk_to_coord(uid, "C15", stop_on_target_battle=True)
        run_at_c15 = load_run(self.plugin, uid)
        self.assertEqual(run_at_c15.node_type, "battle")
        self.assertTrue(any(e.name == "灵乌路空" for e in run_at_c15.enemies))
        self._finish_current_battle(uid)

        run_after_utsuho = load_run(self.plugin, uid)
        fm_after_u = floor_of(run_after_utsuho)
        self.assertTrue(fm_after_u.floor_flags.get("chireiden_utsuho_defeated"))
        self.assertFalse(fm_after_u.rooms["C16"].locked)
        self.assertFalse(fm_after_u.rooms["C19"].locked)
        self.assertTrue(fm_after_u.rooms["C20"].locked)
        self.assertIn("headband_of_intellect_int19", run_after_utsuho.player.relics)

        utsuho_info = self._cmd("i 灵乌路空", uid)
        self.assertIn("智力头环", utsuho_info)
        self.assertNotIn("INT 19", utsuho_info)
        self.assertNotIn("INT 飙升", utsuho_info)
        self.assertNotIn("智力飙升", utsuho_info)
        self.assertNotIn("智力提升到 19", utsuho_info)

        headband_query = self._cmd("i 智力头环", uid)
        self.assertIn("headband_of_intellect", headband_query)
        self.assertIn("智力头环", headband_query)
        self.assertIn("设定为 19", headband_query)

        pre_portal_p4 = self._cmd("i 彭宁离子井·超级传送门·四阶终焉极井", uid)
        self.assertIn("未找到", pre_portal_p4)

        self._walk_to_coord(uid, "C18")
        self._walk_to_coord(uid, "C19", stop_on_target_battle=True)
        run_portal = load_run(self.plugin, uid)
        self.assertEqual(run_portal.node_type, "battle")
        self.assertTrue(any("彭宁离子井·超级传送门·初阶裂隙" == e.name for e in run_portal.enemies))
        portal_stats = self._finish_current_battle(uid, max_turns=160, observe_portal=True)
        self.assertIn("彭宁离子井·超级传送门·初阶裂隙", portal_stats["phases_seen"])
        self.assertIn("彭宁离子井·超级传送门·二阶扩口", portal_stats["phases_seen"])
        self.assertIn("彭宁离子井·超级传送门·三阶超临界", portal_stats["phases_seen"])
        self.assertIn("彭宁离子井·超级传送门·四阶终焉极井", portal_stats["phases_seen"])
        self.assertTrue(portal_stats["xen_seen"])
        self.assertTrue(portal_stats["utsuho_joined"])
        self.assertTrue(portal_stats["ally_played"])
        self.assertFalse(portal_stats["reflect_or_curse_seen"])

        run_post_portal = load_run(self.plugin, uid)
        fm_post = floor_of(run_post_portal)
        self.assertTrue(fm_post.floor_flags.get("chireiden_portal_defeated"))
        self.assertFalse(fm_post.rooms["C20"].locked)
        self.assertNotIn("merc_utsuho", run_post_portal.players)
        self.assertNotIn("merc_utsuho", run_post_portal.party_order)
        self.assertIn("penning_ion_stabilizer", run_post_portal.player.relics)

        post_portal_p4 = self._cmd("i 彭宁离子井·超级传送门·四阶终焉极井", uid)
        self.assertIn("终焉极井", post_portal_p4)
        self.assertIn("460", post_portal_p4)

        post_utsuho_ally = self._cmd("i 灵乌路空", uid)
        self.assertIn("协同助战档案", post_utsuho_ally)

        post_cannon_card = self._cmd("i 非想天则热核炮", uid)
        self.assertIn("hisoutensoku_thermonuclear_cannon", post_cannon_card)

        post_xen = self._cmd("i Xen猎头蟹", uid)
        self.assertIn("寄生猎手", post_xen)
        self.assertNotIn("未知（尚未", post_xen)

        post_stab = self._cmd("i 彭宁井谐振稳压桩", uid)
        self.assertIn("chireiden_penning_stabilizer", post_stab)

        self._walk_to_coord(uid, "C20")
        self._cmd("talk", uid)
        self._cmd("1", uid)
        run_ds4 = load_run(self.plugin, uid)
        if run_ds4.node_type == "downstairs":
            self._cmd("1", uid)
        self._finish_current_battle(uid)
        run_floor4 = load_run(self.plugin, uid)
        self.assertEqual(floor_of(run_floor4).floor_index, 4)
        self.assertNotIn("merc_utsuho", run_floor4.party_order)

        stats_final = self.plugin.save_manager.load_stats(uid)
        for ach_id in (
            "chireiden_elevator_descent",
            "chireiden_facility_surveyor",
            "chireiden_lbe_quench",
            "chireiden_utsuho_headband",
            "chireiden_utsuho_ally",
            "chireiden_penning_sealer",
        ):
            self.assertIn(ach_id, stats_final.unlocked_achievements)
        achi_epic_p1 = self._cmd("achi 珍奇", uid)
        self.assertIn("非想天则维修电梯", achi_epic_p1)
        self.assertIn("控制中心设施测绘员", achi_epic_p1)
        achi_epic_p2 = self._cmd("n", uid)
        self.assertIn("铅铋共晶安全员", achi_epic_p2)
        self.assertIn("智慧的核聚变之巅", achi_epic_p2)
        self.assertIn("地狱鸦协战阵线", achi_epic_p2)
        self._cmd("q", uid)
        achi_legend = self._cmd("achi 传奇", uid)
        self.assertIn("异界共振终焉封堵", achi_legend)
