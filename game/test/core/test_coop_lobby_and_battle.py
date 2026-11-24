import asyncio
import random
import re
import tempfile
import unittest
from unittest.mock import patch
from game.entities.events import ALL_EVENTS
from game.test.core.base import CorePlugin, floor_of, load_run, move_to_room, run_command, walk_to_boss_battle
from game.core.party.session import SessionContextScoper
from game.data.progression.account_config import RENAME_COST_GP
from game.data.entities.gem_data import GEM_CONFIG
from game.entities.cards.base import ALL_CARDS
from game.models.state import CardState, GameRun, PlayerState
from game.test.core.coop_base import CoopTestBase


class TestCoopLobbyAndBattle(CoopTestBase):
    def test_friend_and_team_rules(self):
        leader = "rules_leader"
        friends = [f"rules_friend_{index}" for index in range(6)]
        stranger = "rules_stranger"
        self.rename_player(leader, "队长")
        self.rename_player(stranger, "路人")
        for index, uid in enumerate(friends, 1):
            self.rename_player(uid, f"好友{index}")
            self.run_cmd(f"friend add {self.player_id(uid)}", leader)
            self.run_cmd(f"friend accept {self.player_id(leader)}", uid)
        result = self.run_cmd("friend list", leader)
        self.assertIn("好友列表(6 人)", result)
        self.run_cmd("friend bind qq_rule_test", friends[0])
        searched = self.run_cmd("friend search qq_rule_test", leader)
        self.assertIn(self.player_id(friends[0]), searched)
        self.assertIn("好友1", searched)
        named = self.run_cmd("friend search 好友2", leader)
        self.assertIn(self.player_id(friends[1]), named)
        result = self.run_cmd("team create", leader)
        match = re.search(r"队伍 ([A-Z0-9]{6})", result)
        assert match is not None, "team id must be present"
        lobby_id = match.group(1)
        rejected = self.run_cmd(f"team invite {self.player_id(stranger)}", leader)
        self.assertIn("还不是你的好友", rejected)
        for uid in friends[:5]:
            invited = self.run_cmd(f"team invite {self.player_id(uid)}", leader)
            self.assertIn("已邀请", invited)
        overflow = self.run_cmd(f"team invite {self.player_id(friends[5])}", leader)
        self.assertIn("最多 6 人", overflow)
        joined = self.run_cmd(f"team join {lobby_id}", friends[0])
        self.assertIn("已加入队伍", joined)
        not_ready = self.run_cmd("team start", leader)
        self.assertIn("尚未准备", not_ready)
        left = self.run_cmd("team disband", leader)
        self.assertIn("已解散", left)
        mutual_a = "mutual_a"
        mutual_b = "mutual_b"
        self.rename_player(mutual_a, "互加甲")
        self.rename_player(mutual_b, "互加乙")
        self.run_cmd(f"friend add {self.player_id(mutual_b)}", mutual_a)
        mutual = self.run_cmd(f"friend add {self.player_id(mutual_a)}", mutual_b)
        self.assertIn("已成为好友", mutual)
        self.assertIn(self.player_id(mutual_b), self.run_cmd("friend list", mutual_a))

    def test_turn_barrier_and_coop_card_pool(self):
        uids = ["turn_a", "turn_b"]
        run = self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        first = self.run_cmd("e", uids[0])
        self.assertIn("等待队友", first)
        run = load_run(self.plugin, uids[0])
        self.assertTrue(run.node_data["turn_ready"][uids[0]])
        self.assertFalse(run.node_data["turn_ready"][uids[1]])
        second = self.run_cmd("e", uids[1])
        self.assertIn("进入第 2 回合", second)
        run = load_run(self.plugin, uids[0])
        self.assertEqual(run.node_data.get("turn_count"), 2)
        self.assertFalse(any(run.node_data["turn_ready"].values()))
        from game.core.inventory.deck_service import DeckService
        from game.entities.cards.market import is_coop_only
        stats = self.plugin.save_manager.load_stats(uids[0])
        pool = set(DeckService.get_reward_card_pool(run, run.players[uids[0]], stats, include_coop=True))
        coop_ids = {
            "coop_tactical_command",
            "coop_phalanx_bulwark",
            "coop_resonance_hymn",
            "coop_soul_link",
            "coop_unison_crusade",
        }
        self.assertTrue(coop_ids.issubset(pool))
        for cid in coop_ids:
            self.assertTrue(is_coop_only(cid))
        solo_player = self.plugin.engine._build_player_state("solo_check")
        solo_ids = {state.id for state in solo_player.deck}
        self.assertFalse(coop_ids & solo_ids)
        from server.snapshot import build_snapshot
        snapshot = build_snapshot(run, stats, "")
        self.assertTrue(snapshot["coop"])
        self.assertEqual(len(snapshot["party"]), 2)
        self.assertEqual(snapshot["party"][0]["slot"], 1)
        self.assertTrue(snapshot["party"][0]["is_self"])

    def test_downed_revive_and_enemy_targeting(self):
        uids = ["down_a", "down_b"]
        run = self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        from game.core.battle.party_battle import assign_enemy_targets, is_all_downed, mark_downed, revive_downed_players
        be = self.plugin.engine.battle_engine
        mark_downed(be, run, run.players[uids[1]])
        self.assertTrue(run.players[uids[1]].downed)
        self.assertFalse(is_all_downed(run))
        self.assertTrue(run.node_data["turn_ready"][uids[1]])
        self.plugin.save_manager.save_save(uids[0], run)
        downed = self.run_cmd("e", uids[1])
        self.assertIn("倒地", downed)
        assign_enemy_targets(run)
        for target in run.node_data.get("enemy_targets", {}).values():
            if target != "ALL":
                self.assertNotEqual(target, uids[1])
        notices = list(revive_downed_players(run).values())
        self.assertTrue(any(run.players[uids[1]].name in notice for notice in notices))
        self.assertEqual(run.players[uids[1]].hp, 1)
        self.assertFalse(run.players[uids[1]].downed)
        mark_downed(be, run, run.players[uids[0]])
        mark_downed(be, run, run.players[uids[1]])
        self.assertTrue(is_all_downed(run))

    def test_solo_battle_waits_for_teammate_arrival(self):
        uids = ["solo_wait_a", "solo_wait_b"]
        self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"))
        if run.node_type == "ally_summon_select":
            self.run_cmd("c 1", uids[0])
            run = load_run(self.plugin, uids[0])
        self.assertEqual(run.node_type, "battle")
        self.assertEqual(run.node_data.get("battle_mode"), "solo")
        self.assertEqual(run.party_order, [uids[0]])
        idle = load_run(self.plugin, uids[1])
        self.assertEqual(idle.node_type, "grid_map")
        self.assertNotIn(uids[1], floor_of(idle).player_session_map)
        coord = floor_of(run).player_coords.get(uids[0])
        self.run_cmd(f"tp {coord}", uids[1])
        joined = load_run(self.plugin, uids[1])
        self.assertEqual(joined.node_type, "battle")
        self.assertIn(uids[1], joined.party_order)
        sid = floor_of(joined).player_session_map.get(uids[1], "")
        self.assertTrue(sid)
        participants = floor_of(joined).active_sessions[sid].participants
        self.assertIn(uids[0], participants)
        self.assertIn(uids[1], participants)

    def test_forced_solo_battle_blocks_teammate_entry(self):
        uids = ["forced_a", "forced_b"]
        self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("shop",))
        self.assertEqual(run.node_type, "shop")
        coord = floor_of(run).player_coords.get(uids[0])
        fight = self.run_cmd("c 2", uids[0])
        self.assertIn("战斗", fight)
        active = load_run(self.plugin, uids[0])
        self.assertEqual(active.node_type, "battle")
        self.assertEqual(active.node_data.get("battle_mode"), "forced_solo")
        blocked = self.run_cmd(f"tp {coord}", uids[1])
        self.assertIn("独自战斗", blocked)
        blocked_run = load_run(self.plugin, uids[1])
        self.assertEqual(blocked_run.node_type, "grid_map")
        self.assertNotIn(uids[1], floor_of(blocked_run).player_session_map)
        sid = floor_of(active).player_session_map.get(uids[0], "")
        self.assertTrue(sid)
        self.assertEqual(floor_of(active).active_sessions[sid].participants, [uids[0]])

    def test_grid_map_battle_and_coop_abandon(self):
        uids = ["vote_a", "vote_b"]
        self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"))
        if run.node_type == "ally_summon_select":
            self.run_cmd("c 1", uids[0])
            run = load_run(self.plugin, uids[0])
        self.assertEqual(run.node_type, "battle")
        blocked = self.run_cmd("start confirm", uids[0])
        self.assertIn("无法覆盖开启新局", blocked)
        self.assertIsNotNone(load_run(self.plugin, uids[0]))
        abandoned = self.run_cmd("abandon confirm", uids[0])
        self.assertIn("全队进度已结算", abandoned)
        for uid in uids:
            self.assertIsNone(self.plugin.save_manager.load_save(uid))
            self.assertEqual(getattr(self.plugin.save_manager.load_stats(uid), "active_run_id", ""), "")

    def test_coop_battle_logs_not_replayed(self):
        uids = ["log_leader", "log_member"]
        self.enter_coop_battle(uids)
        uid = uids[0]
        self.set_hand(uid, [CardState(id="mercenary"), CardState(id="mercenary")])
        first = self.run_cmd("p 1", uid)
        self.assertIn("✨ [消耗] 【雇佣兵】进入战场。", first)
        second = self.run_cmd("p 1", uid)
        self.assertEqual(second.count("✨ [消耗] 【雇佣兵】进入战场。"), 1)
        run = load_run(self.plugin, uid)
        self.assertFalse(run.node_data.get("battle_logs"))

    def test_coop_last_ender_clears_single_turn_buff(self):
        uids = ["focus_leader", "focus_member"]
        self.enter_coop_battle(uids)
        from game.models.state import BuffState
        waiting = self.run_cmd("e", uids[0])
        self.assertIn("等待队友", waiting)
        run = load_run(self.plugin, uids[1])
        run.player = run.players[uids[1]]
        run.players[uids[1]].buffs.append(BuffState("tactical_focus", "无法抽牌", 1, None, ""))
        self.plugin.save_manager.save_save(uids[1], run)
        self.run_cmd("e", uids[1])
        run = load_run(self.plugin, uids[1])
        self.assertFalse(any(b.id == "tactical_focus" for b in run.players[uids[1]].buffs))
        self.assertEqual(len(run.players[uids[1]].hand), 6)

    def test_coop_echo_form_uses_per_player_play_count(self):
        uids = ["echo_leader", "echo_member"]
        self.enter_coop_battle(uids)
        from game.models.state import BuffState
        self.set_hand(uids[0], [CardState(id="quick_strike")] * 3)
        self.run_cmd("p 1", uids[0])
        self.run_cmd("p 1", uids[0])
        run = load_run(self.plugin, uids[1])
        run.player = run.players[uids[1]]
        run.players[uids[1]].buffs.append(BuffState("echo_form", "回响形态", 1, None, ""))
        run.players[uids[1]].hand = [CardState(id="arcane_spark")]
        run.players[uids[1]].actions = 2
        run.players[uids[1]].bonus_actions = 1
        self.plugin.save_manager.save_save(uids[1], run)
        res = self.run_cmd("p 1", uids[1])
        self.assertIn("[回响触发]", res)

    def test_echo_and_replay_extra_plays_are_additive(self):
        uids = ["stack_leader", "stack_member"]
        self.enter_coop_battle(uids)
        from game.models.state import BuffState
        uid = uids[0]
        run = load_run(self.plugin, uid)
        run.player = run.players[uid]
        player = run.players[uid]
        player.buffs.append(BuffState("echo_form", "回响形态", 1, None, ""))
        player.hand = [CardState(id="quick_strike", replay=1)]
        player.actions = 3
        player.bonus_actions = 3
        self.plugin.save_manager.save_save(uid, run)
        res = self.run_cmd("p 1", uid)
        self.assertEqual(res.count("[回响触发]"), 1)
        self.assertEqual(res.count("[重放触发]"), 1)

    def test_coop_minion_card_leaves_hand_and_stays(self):
        uids = ["minion_leader", "minion_member"]
        self.enter_coop_battle(uids)
        uid = uids[0]
        self.set_hand(uid, [CardState(id="mercenary", upgraded=True)])
        self.run_cmd("p 1", uid)
        run = load_run(self.plugin, uid)
        player = run.players[uid]
        self.assertEqual(player.minions["1"].id, "mercenary+")
        self.assertFalse([c for c in player.hand if c.id == "mercenary"])
        self.assertFalse([c for c in player.discard_pile if c.id == "mercenary"])
        self.assertFalse([c for c in player.exhaust_pile if c.id == "mercenary"])
        self.run_cmd("e", uid)
        self.run_cmd("e", uids[1])
        run = load_run(self.plugin, uid)
        player = run.players[uid]
        self.assertIn("1", player.minions)
        self.assertEqual(player.minions["1"].id, "mercenary+")
        self.assertEqual(player.minions["1"].atk, 5)
        self.assertFalse([c for c in player.hand if c.id == "mercenary"])


if __name__ == "__main__":
    unittest.main()
