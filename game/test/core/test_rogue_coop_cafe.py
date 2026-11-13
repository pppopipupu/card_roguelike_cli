import asyncio
import random
import tempfile
import unittest

from game.models.state import CardState
from game.data.balance_config import COOP_MAX_PLAYERS
from game.data.cafe_data import CAFE_GUESTS, CAFE_NORMALS, CAFE_NPCS_PER_EXTRA_PLAYER, CAFE_TOTAL_NPCS, NPC_SHOW_NAMES
from game.data.map_config import MapConfig
from game.test.core.base import CorePlugin, move_to_room, run_command


class TestRogueCoopCafeAndCapacity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.random_state = random.getstate()

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, command, uid):
        return asyncio.run(run_command(self.plugin, command, uid))

    def _start_coop_direct(self, uids):
        for index, uid in enumerate(uids, 1):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.player_name = f"玩家{index}"
            stats.player_handle = f"玩家{index}"
            self.plugin.save_manager.save_stats(uid, stats)
        self.plugin.engine.start_party_game(uids, uids[0], shared_save=True)
        for uid in uids:
            res = self.run_cmd("c 1", uid)
            self.assertIn("契约达成", res)
        return self.plugin.save_manager.load_save(uids[0])

    def _enter_cafe_for_party(self, uids):
        self._start_coop_direct(uids)
        run = self.plugin.save_manager.load_save(uids[0])
        for uid in uids:
            run.players[uid].gold = 500
        cafe_coord = next((c for c, r in run.floor_map.rooms.items() if r.room_type == "cafe"), "A1")
        from game.core.party.session import SessionContextScoper
        SessionContextScoper.create_session(run, cafe_coord, "cafe", uids)
        from game.core.world.cafe.engine import CafeEngine
        CafeEngine(self.plugin.save_manager, self.plugin.engine.map_engine).init_cafe(run, persist=False)
        self.plugin.save_manager.save_save(uids[0], run)
        return self.plugin.save_manager.load_save(uids[0])

    def test_coop_max_16_players_and_difficulty_capped_at_4(self):
        random.seed(1)
        uids = [f"cap_{i}" for i in range(COOP_MAX_PLAYERS)]
        run = self._start_coop_direct(uids)
        self.assertEqual(len(run.players), 16)
        self.assertEqual(len(run.party_order), 16)

        with self.assertRaises(ValueError):
            self.plugin.engine.start_party_game(uids + ["cap_overflow"], uids[0], shared_save=True)

        _, battle_run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        self.assertEqual(battle_run.node_type, "battle")
        self.assertEqual(battle_run.node_data.get("coop_hp_mult"), 2.0)
        self.assertEqual(len(battle_run.enemies) % 2, 0)

        before_actions = battle_run.players[uids[15]].actions
        battle_run.players[uids[0]].hand = [CardState(id="coop_tactical_command")]
        self.plugin.save_manager.save_save(uids[0], battle_run)
        res = self.run_cmd("p 1 a16", uids[0])
        self.assertIn("战术指挥", res)
        after = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(after.players[uids[15]].actions, before_actions + 1)

    def test_coop_cafe_shared_npcs_and_scales_with_player_count(self):
        expected_counts = {
            2: min(len(CAFE_GUESTS) + len(CAFE_NORMALS), CAFE_TOTAL_NPCS + CAFE_NPCS_PER_EXTRA_PLAYER),
            4: min(len(CAFE_GUESTS) + len(CAFE_NORMALS), CAFE_TOTAL_NPCS + 3 * CAFE_NPCS_PER_EXTRA_PLAYER),
            6: min(len(CAFE_GUESTS) + len(CAFE_NORMALS), CAFE_TOTAL_NPCS + 5 * CAFE_NPCS_PER_EXTRA_PLAYER),
            16: len(CAFE_GUESTS) + len(CAFE_NORMALS),
        }
        for count, expected_npcs in expected_counts.items():
            with self.subTest(players=count):
                uids = [f"cafe_scale_{count}_{i}" for i in range(count)]
                run = self._enter_cafe_for_party(uids)
                shared_npcs = run.node_data.get("coop_cafe", {}).get("npcs", [])
                self.assertEqual(len(shared_npcs), expected_npcs)
                first_look = self.run_cmd("look", uids[0])
                last_look = self.run_cmd("look", uids[-1])
                for npc in shared_npcs:
                    show_name = NPC_SHOW_NAMES[npc]
                    self.assertIn(show_name, first_look)
                    self.assertIn(show_name, last_look)

    def test_coop_cafe_npc_lock_shared_talked_and_gem_insert_sync(self):
        uids = ["shared_a", "shared_b", "shared_c"]
        run = self._enter_cafe_for_party(uids)
        coop_cafe = run.node_data["coop_cafe"]
        coop_cafe["npcs"] = ["艾琳", "辛普森", "Blacksmith_Ironclad", "杰斯"]
        coop_cafe["gemcutter_stock"] = ["gem_dmg_add_2", "gem_shield_add_3"]
        coop_cafe["card_master_stock"] = ["quick_strike"]
        for uid in uids:
            run.node_data["player_views"][uid]["data"]["cafe_data"]["npcs"] = list(coop_cafe["npcs"])
        self.plugin.save_manager.save_save(uids[0], run)

        talk_erin = self.run_cmd("talk 艾琳", uids[0])
        self.assertIn("艾琳", talk_erin)

        look_b = self.run_cmd("look", uids[1])
        self.assertIn("正与 玩家1 交谈中", look_b)

        blocked_b = self.run_cmd("talk 艾琳", uids[1])
        self.assertIn("正在与 玩家1 交谈中", blocked_b)

        left_a = self.run_cmd("离开", uids[0])
        self.assertIn("回到了大堂", left_a)

        talk_erin_b = self.run_cmd("talk 艾琳", uids[1])
        self.assertIn("艾琳", talk_erin_b)
        gem_flow_b = self.run_cmd("c 2", uids[1])
        self.assertIn("强制镶嵌", gem_flow_b)

        member_b = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(member_b.node_type, "gem_insert")

        talk_simpson_a = self.run_cmd("talk 辛普森", uids[0])
        self.assertIn("辛普森", talk_simpson_a)
        done_simpson_a = self.run_cmd("c 1", uids[0])
        self.assertIn("赞歌", done_simpson_a)

        cancel_gem_b = self.run_cmd("c 取消", uids[1])
        self.assertIn("不进行镶嵌", cancel_gem_b)
        look_after_b = self.run_cmd("look", uids[1])
        self.assertIn("已交互 · 玩家2", look_after_b)
        self.assertIn("已交互 · 玩家1", look_after_b)

        tired_c = self.run_cmd("talk 辛普森", uids[2])
        self.assertIn("有些疲惫", tired_c)
        self.run_cmd("c 1", uids[2])

        self.run_cmd("离开", uids[0])
        self.run_cmd("离开", uids[1])
        completed = self.run_cmd("离开", uids[2])
        self.assertIn("继续前进", completed)
        for uid in uids:
            after = self.plugin.save_manager.load_save(uid)
            self.assertEqual(after.node_type, "grid_map")

    def test_six_player_team_start_via_lobby(self):
        uids = [f"six_{i}" for i in range(6)]
        leader = uids[0]
        for index, uid in enumerate(uids, 1):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.player_name = f"六人测试{index}"
            stats.player_handle = f"六人测试{index}"
            self.plugin.save_manager.save_stats(uid, stats)
        for index, uid in enumerate(uids[1:], 2):
            self.run_cmd(f"friend add 六人测试{index}", leader)
            self.run_cmd("friend accept 六人测试1", uid)
        created = self.run_cmd("team create", leader)
        lobby_id = created.split("队伍 ")[1][:6]
        for index, uid in enumerate(uids[1:], 2):
            invited = self.run_cmd(f"team invite 六人测试{index}", leader)
            self.assertIn("已邀请", invited)
            joined = self.run_cmd(f"team join {lobby_id}", uid)
            self.assertIn("已加入队伍", joined)
            ready = self.run_cmd("team ready", uid)
            self.assertIn("已准备就绪", ready)
        started = self.run_cmd("team start", leader)
        self.assertIn("已开启联机牌局", started)
        run = self.plugin.save_manager.load_save(leader)
        self.assertEqual(len(run.players), 6)

    def test_solo_mode_is_one_player_party_and_supports_a_selector(self):
        random.seed(1)
        uid = "solo_party_user"
        self.run_cmd("start", uid)
        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.player_count(), 1)
        self.assertEqual(run.party_order, [uid])
        self.assertFalse(run.is_multiplayer())

        res = self.run_cmd("c 1", uid)
        self.assertIn("契约达成", res)
        run = self.plugin.save_manager.load_save(uid)
        self.assertEqual(run.node_type, "grid_map")

        _, battle_run = move_to_room(self.plugin, uid, ("battle", "elite"))
        self.assertEqual(battle_run.node_type, "battle")

        battle_run.player.hp = 10
        battle_run.player.potions = ["healing_potion"]
        battle_run.player.hand = [
            CardState(id="coop_resonance_hymn", upgraded=True),
            CardState(id="coop_phalanx_bulwark", upgraded=True),
        ]
        battle_run.player.actions = 4
        battle_run.player.bonus_actions = 2
        self.plugin.save_manager.save_save(uid, battle_run)

        pot_res = self.run_cmd("pot 1 a1", uid)
        self.assertIn("回复了", pot_res)
        after_pot = self.plugin.save_manager.load_save(uid)
        self.assertGreater(after_pot.player.hp, 10)

        hymn_res = self.run_cmd("p 1 a1", uid)
        self.assertIn("共鸣圣歌", hymn_res)
        bulwark_res = self.run_cmd("p 1 a1", uid)
        self.assertIn("方阵掩护", bulwark_res)
        after_cards = self.plugin.save_manager.load_save(uid)
        self.assertGreater(after_cards.player.shield, 0)

    def test_ally_minion_selector_a2m1_and_no_a_aliases(self):
        random.seed(1)
        from game.models.state import MinionState
        uids = ["minion_sel_a", "minion_sel_b"]
        run = self._start_coop_direct(uids)
        _, battle_run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        self.assertEqual(battle_run.node_type, "battle")

        p1 = battle_run.players[uids[0]]
        p2 = battle_run.players[uids[1]]
        p1.minions["1"] = MinionState("mercenary", "己方佣兵", 5, 10, 3, 1, 0)
        p2.minions["1"] = MinionState("mercenary", "队友佣兵", 4, 10, 3, 1, 0)
        p1.actions = 6
        p1.bonus_actions = 4
        p1.potions = ["healing_potion", "healing_potion"]
        p1.hand = [
            CardState(id="coop_tactical_command"),
            CardState(id="coop_resonance_hymn"),
            CardState(id="neutral_shou_lai"),
            CardState(id="coop_tactical_command"),
            CardState(id="coop_tactical_command"),
            CardState(id="coop_tactical_command"),
        ]
        self.plugin.save_manager.save_save(uids[0], battle_run)

        rejected_t = self.run_cmd("p 4 t2", uids[0])
        self.assertIn("❌", rejected_t)
        rejected_tm = self.run_cmd("p 4 t2m1", uids[0])
        self.assertIn("❌", rejected_tm)
        rejected_ap = self.run_cmd("p 4 a2p1", uids[0])
        self.assertIn("❌", rejected_ap)
        rejected_empty_pot = self.run_cmd("pot 1 a2m2", uids[0])
        self.assertIn("❌", rejected_empty_pot)

        cmd_res = self.run_cmd("p 1 a2m1", uids[0])
        self.assertIn("队友佣兵", cmd_res)
        after_cmd = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(after_cmd.players[uids[1]].minions["1"].actions, 2)
        self.assertEqual(after_cmd.players[uids[1]].minions["1"].bonus_actions, 1)

        hymn_res = self.run_cmd("p 1 a2m1", uids[0])
        self.assertIn("共鸣圣歌", hymn_res)
        after_hymn = self.plugin.save_manager.load_save(uids[0])
        self.assertTrue(any(b.id == "strength" for b in after_hymn.players[uids[1]].minions["1"].buffs))

        pot_ally_res = self.run_cmd("pot 1 a2m1", uids[0])
        self.assertIn("回复了", pot_ally_res)
        after_pot_ally = self.plugin.save_manager.load_save(uids[0])
        self.assertGreater(after_pot_ally.players[uids[1]].minions["1"].hp, 4)

        shou_lai_res = self.run_cmd("p 1 a2m1", uids[0])
        self.assertIn("寿来", shou_lai_res)
        after_sl = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(after_sl.players[uids[1]].minions["1"].max_hp, 4)

        pot_self_m_res = self.run_cmd("pot 1 a1m1", uids[0])
        self.assertIn("回复了", pot_self_m_res)
        after_pot_self = self.plugin.save_manager.load_save(uids[0])
        self.assertGreater(after_pot_self.players[uids[0]].minions["1"].hp, 5)

    def test_party_wide_spells_affect_ax_and_axmx(self):
        random.seed(1)
        from game.models.state import AmuletState, BuffState, MinionState

        uids = ["wide_a", "wide_b"]
        run = self._start_coop_direct(uids)
        _, battle_run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        self.assertEqual(battle_run.node_type, "battle")

        p1 = battle_run.players[uids[0]]
        p2 = battle_run.players[uids[1]]
        p1.relics = []
        p2.relics = []
        p1.hp = 20
        p1.max_hp = 40
        p2.hp = 30
        p2.max_hp = 40
        p2.shield = 0
        p1.actions = 8
        p1.bonus_actions = 4
        p1.minions["1"] = MinionState("mercenary", "己方佣兵", 25, 30, 3, 1, 0)
        p2.minions["1"] = MinionState("mercenary", "队友佣兵", 25, 30, 3, 1, 0)
        p1.minions["1"].buffs.append(BuffState("weak", "虚弱", 2, desc="desc"))
        p2.minions["1"].buffs.append(BuffState("weak", "虚弱", 2, desc="desc"))
        p1.buffs.append(BuffState("strength", "力量", 2, desc="desc"))
        p2.buffs.append(BuffState("strength", "力量", 2, desc="desc"))
        p1.amulets["2"] = AmuletState("lucky_coin", "幸运币", 2, "desc")
        p2.amulets["2"] = AmuletState("lucky_coin", "幸运币", 2, "desc")
        battle_run.enemies = [battle_run.enemies[0]]
        battle_run.enemies[0].hp = 200
        battle_run.enemies[0].max_hp = 200
        battle_run.enemies[0].buffs.append(BuffState("strength", "力量", 2, desc="desc"))
        p1.hand = [
            CardState(id="sunburst"),
            CardState(id="mass_healing_word"),
            CardState(id="quick_strike", upgraded=True),
            CardState(id="wizard_antimagic_field"),
        ]
        self.plugin.save_manager.save_save(uids[0], battle_run)

        sun_res = self.run_cmd("p 1", uids[0])
        self.assertIn("阳炎爆", sun_res)
        after_sun = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(after_sun.players[uids[0]].hp, 20)
        self.assertEqual(after_sun.players[uids[1]].hp, 14)
        self.assertEqual(after_sun.players[uids[0]].minions["1"].hp, 9)
        self.assertEqual(after_sun.players[uids[1]].minions["1"].hp, 9)
        self.assertEqual(after_sun.enemies[0].hp, 184)

        heal_res = self.run_cmd("p 1", uids[0])
        self.assertIn("群体治愈真言", heal_res)
        after_heal = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(after_heal.players[uids[0]].hp, 28)
        self.assertEqual(after_heal.players[uids[1]].hp, 22)
        self.assertEqual(after_heal.players[uids[0]].minions["1"].hp, 17)
        self.assertEqual(after_heal.players[uids[1]].minions["1"].hp, 17)

        qs_res = self.run_cmd("p 1 e1", uids[0])
        self.assertIn("迅捷打击", qs_res)
        after_qs = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(after_qs.players[uids[0]].minions["1"].atk, 4)
        self.assertEqual(after_qs.players[uids[1]].minions["1"].atk, 4)

        amf_res = self.run_cmd("p 1", uids[0])
        self.assertIn("反魔法力场", amf_res)
        after_amf = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(after_amf.players[uids[0]].buffs, [])
        self.assertEqual(after_amf.players[uids[1]].buffs, [])
        self.assertEqual(after_amf.players[uids[0]].amulets, {})
        self.assertEqual(after_amf.players[uids[1]].amulets, {})
        self.assertEqual(after_amf.players[uids[0]].minions["1"].buffs, [])
        self.assertEqual(after_amf.players[uids[1]].minions["1"].buffs, [])
        self.assertEqual(after_amf.enemies[0].buffs, [])


    def test_coop_cafe_and_ancient_wait_for_all_players(self):
        uids = ["cafe_wait_leader", "cafe_wait_member"]
        run = self._start_coop_direct(uids)
        from game.core.world.cafe.engine import CafeEngine
        from game.core.party.session import SessionContextScoper
        SessionContextScoper.create_session(run, "A1", "cafe", uids)
        CafeEngine(self.plugin.save_manager, self.plugin.engine.map_engine).init_cafe(run, persist=False)
        self.plugin.save_manager.save_save(uids[0], run)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.node_type, "cafe")
        self.assertEqual(run.node_data.get("coop_node_type"), "cafe")
        views = run.node_data.get("player_views", {})
        self.assertEqual(set(views), set(uids))
        self.assertTrue(views[uids[0]]["data"]["cafe_data"])

        waiting = self.run_cmd("离开", uids[0])
        self.assertIn("等待队友", waiting)
        member = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(member.node_type, "cafe")
        self.assertTrue(member.node_data.get("cafe_data"))
        self.assertFalse(member.node_data.get("coop_done"))

        completed = self.run_cmd("离开", uids[1])
        self.assertIn("继续前进", completed)
        for uid in uids:
            grid = self.plugin.save_manager.load_save(uid)
            self.assertEqual(grid.node_type, "grid_map")

        SessionContextScoper.create_session(run, "A1", "ancient", uids)
        self.plugin.engine.map_engine.enter_ancient_node(run)
        self.plugin.save_manager.save_save(uids[0], run)

        waiting = self.run_cmd("c 1", uids[0])
        self.assertIn("等待队友", waiting)
        member = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(member.node_type, "ancient")

        completed = self.run_cmd("c 1", uids[1])
        self.assertIn("继续前进", completed)
        for uid in uids:
            advanced = self.plugin.save_manager.load_save(uid)
            self.assertEqual(advanced.node_type, "grid_map")

    def test_coop_ally_card_defaults_to_first_teammate(self):
        uids = ["ally_default_leader", "ally_default_member", "ally_default_third"]
        self._start_coop_direct(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        uid = uids[0]
        p = run.players[uid]
        from game.models.state import CardState
        p.hand = [CardState(id="coop_tactical_command")]
        p.actions = 2
        p.bonus_actions = 1
        self.plugin.save_manager.save_save(uid, run)
        before = self.plugin.save_manager.load_save(uids[1]).players[uids[1]].actions
        result = self.run_cmd("p 1", uid)
        self.assertNotIn("请指定", result)
        self.assertIn("战术指挥", result)
        after = self.plugin.save_manager.load_save(uids[1]).players[uids[1]].actions
        self.assertEqual(after, before + 1)


if __name__ == "__main__":
    unittest.main()
