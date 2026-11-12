import asyncio
import random
import re
import tempfile
import unittest
from collections import Counter
from unittest.mock import patch

from game.entities.events import ALL_EVENTS

from game.test.core.base import CorePlugin, run_command
from game.data.account_config import RENAME_COST_GP
from game.data.gem_data import GEM_CONFIG
from game.entities.cards.base import ALL_CARDS
from game.models.state import CardState, GameRun, PlayerState


class TestRogueCoop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.random_state = random.getstate()

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, command, uid):
        return asyncio.run(run_command(self.plugin, command, uid))

    def player_id(self, uid):
        stats = self.plugin.save_manager.load_stats(uid)
        return stats.player_handle or stats.player_name

    def rename_player(self, uid, name):
        stats = self.plugin.save_manager.load_stats(uid)
        stats.gp = max(stats.gp, RENAME_COST_GP)
        self.plugin.save_manager.save_stats(uid, stats)
        result = self.run_cmd(f"friend name {name}", uid)
        self.assertIn("已修改", result)
        return self.player_id(uid)

    def make_friends(self, leader, others, suffix=""):
        self.rename_player(leader, f"队长{suffix}")
        for index, uid in enumerate(others, 1):
            self.rename_player(uid, f"队员{index}{suffix}")
            self.run_cmd(f"friend add {self.player_id(uid)}", leader)
            self.run_cmd(f"friend accept {self.player_id(leader)}", uid)

    def create_team(self, leader, others):
        result = self.run_cmd("team create", leader)
        self.assertIn("已创建队伍", result)
        lobby_id = re.search(r"队伍 ([A-Z0-9]{6})", result).group(1)
        for uid in others:
            invited = self.run_cmd(f"friend invite {self.player_id(uid)}", leader)
            self.assertIn("已邀请", invited)
            joined = self.run_cmd(f"team join {lobby_id}", uid)
            self.assertIn("已加入队伍", joined)
        return lobby_id

    def start_coop(self, uids):
        self._coop_run_index = getattr(self, "_coop_run_index", 0) + 1
        suffix = "" if self._coop_run_index == 1 else f"_{self._coop_run_index}"
        leader = uids[0]
        self.make_friends(leader, uids[1:], suffix)
        self.create_team(leader, uids[1:])
        for uid in uids[1:]:
            ready = self.run_cmd("team ready", uid)
            self.assertIn("已准备就绪", ready)
        random.seed(0)
        from game.data.starting_deck_config import STARTING_ROLL_COUNTS
        legacy_roll_calls = 8 - sum(STARTING_ROLL_COUNTS.values())
        for _ in range(legacy_roll_calls * len(uids)):
            random.choice([0, 1])
        started = self.run_cmd("team start", leader)
        self.assertIn("已开启联机牌局", started)
        for uid in uids:
            chosen = self.run_cmd("c 1", uid)
            self.assertIn("契约达成", chosen)
        run = self.plugin.save_manager.load_save(leader)
        self.assertEqual(run.node_type, "map_select")
        self.assertEqual(len(run.players), len(uids))
        return run

    def test_friend_and_team_rules(self):
        leader = "rules_leader"
        friends = [f"rules_friend_{index}" for index in range(5)]
        stranger = "rules_stranger"
        self.rename_player(leader, "队长")
        self.rename_player(stranger, "路人")
        for index, uid in enumerate(friends, 1):
            self.rename_player(uid, f"好友{index}")
            self.run_cmd(f"friend add {self.player_id(uid)}", leader)
            self.run_cmd(f"friend accept {self.player_id(leader)}", uid)
        result = self.run_cmd("friend list", leader)
        self.assertIn("好友列表(5 人)", result)
        self.run_cmd("friend bind qq_rule_test", friends[0])
        searched = self.run_cmd("friend search qq_rule_test", leader)
        self.assertIn(self.player_id(friends[0]), searched)
        self.assertIn("好友1", searched)
        named = self.run_cmd("friend search 好友2", leader)
        self.assertIn(self.player_id(friends[1]), named)
        result = self.run_cmd("team create", leader)
        lobby_id = re.search(r"队伍 ([A-Z0-9]{6})", result).group(1)
        rejected = self.run_cmd(f"team invite {self.player_id(stranger)}", leader)
        self.assertIn("还不是你的好友", rejected)
        for uid in friends[:3]:
            invited = self.run_cmd(f"team invite {self.player_id(uid)}", leader)
            self.assertIn("已邀请", invited)
        overflow = self.run_cmd(f"team invite {self.player_id(friends[3])}", leader)
        self.assertIn("最多 4 人", overflow)
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

    def test_enemy_scaling_for_two_three_four_players(self):
        expected = {2: 1.0, 3: 1.5, 4: 2.0}
        for count, multiplier in expected.items():
            with self.subTest(players=count):
                uids = [f"scale_{count}_{index}" for index in range(count)]
                run = self.start_coop(uids)
                options = run.node_data.get("options", [])
                battle_index = next(
                    (index + 1 for index, option in enumerate(options) if option.get("node_type") in ("battle", "elite")),
                    None,
                )
                self.assertIsNotNone(battle_index)
                self.run_cmd(f"c {battle_index}", uids[0])
                run = self.plugin.save_manager.load_save(uids[0])
                self.assertEqual(run.node_type, "battle")
                self.assertEqual(len(run.players), count)
                self.assertEqual(run.node_data.get("coop_hp_mult"), multiplier)
                self.assertEqual(len(run.enemies) % 2, 0)
                base_names = []
                for enemy in run.enemies:
                    name = enemy.name
                    parts = name.rsplit(" ", 1)
                    if len(parts) == 2 and len(parts[1]) == 1:
                        name = parts[0]
                    base_names.append(name)
                counts = Counter(base_names)
                self.assertTrue(all(value == 2 for value in counts.values()))
                for uid in uids:
                    member_run = self.plugin.save_manager.load_save(uid)
                    self.assertEqual(len(member_run.players), count)
                    self.assertFalse(member_run.players[uid].downed)

    def test_turn_barrier_and_coop_card_pool(self):
        uids = ["turn_a", "turn_b"]
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        battle_index = next(
            index + 1 for index, option in enumerate(options) if option.get("node_type") in ("battle", "elite")
        )
        self.run_cmd(f"c {battle_index}", uids[0])
        first = self.run_cmd("e", uids[0])
        self.assertIn("等待队友", first)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertTrue(run.node_data["turn_ready"][uids[0]])
        self.assertFalse(run.node_data["turn_ready"][uids[1]])
        second = self.run_cmd("e", uids[1])
        self.assertIn("进入第 2 回合", second)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.node_data.get("turn_count"), 2)
        self.assertFalse(any(run.node_data["turn_ready"].values()))
        from game.core.coop_engine import CoopEngine
        from game.entities.cards.market import is_coop_only
        coop = CoopEngine(self.plugin.save_manager, self.plugin.engine)
        stats = self.plugin.save_manager.load_stats(uids[0])
        pool = set(coop._reward_card_pool(run, run.players[uids[0]], stats))
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

    def test_independent_shop_and_rest_mend(self):
        uids = ["shop_a", "shop_b"]
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        shop_index = next(index + 1 for index, option in enumerate(options) if option.get("node_type") == "shop")
        self.run_cmd(f"c {shop_index}", uids[0])
        shop_a = self.plugin.save_manager.load_save(uids[0])
        shop_b = self.plugin.save_manager.load_save(uids[1])
        cards_a = [item.get("card_id") for item in shop_a.node_data.get("items", []) if item.get("type") == "card"]
        cards_b = [item.get("card_id") for item in shop_b.node_data.get("items", []) if item.get("type") == "card"]
        self.assertNotEqual(cards_a, cards_b)
        items_a = shop_a.node_data.get("items", [])
        buy_index = next(
            index + 1
            for index, item in enumerate(items_a)
            if item.get("type") == "card" and item.get("price", 999) <= shop_a.player.gold
        )
        bought_card = items_a[buy_index - 1].get("card_id")
        bought = self.run_cmd(f"c {buy_index}", uids[0])
        self.assertIn("购买成功", bought)
        after_a = self.plugin.save_manager.load_save(uids[0])
        after_b = self.plugin.save_manager.load_save(uids[1])
        self.assertIn(bought_card, {state.id for state in after_a.player.deck})
        self.assertEqual(after_b.player.gold, shop_b.player.gold)
        self.assertFalse(after_b.node_data["items"][buy_index - 1].get("sold"))
        leave_index = len(items_a)
        self.run_cmd(f"c {leave_index}", uids[0])
        self.run_cmd(f"c {leave_index}", uids[1])
        advanced = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(advanced.node_type, "map_select")

        uids = ["rest_a", "rest_b"]
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        rest_index = next(index + 1 for index, option in enumerate(options) if option.get("node_type") == "rest")
        self.run_cmd(f"c {rest_index}", uids[0])
        status = self.run_cmd("status", uids[0])
        self.assertIn("救治队友", status)
        mend = self.run_cmd("c 4", uids[0])
        self.assertIn("救治", mend)
        mend = self.run_cmd("c 4", uids[1])
        self.assertIn("救治", mend)
        advanced = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(advanced.node_type, "map_select")


    def test_downed_revive_and_enemy_targeting(self):
        uids = ["down_a", "down_b"]
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        battle_index = next(
            index + 1
            for index, option in enumerate(options)
            if option.get("node_type") in ("battle", "elite")
        )
        self.run_cmd(f"c {battle_index}", uids[0])
        run = self.plugin.save_manager.load_save(uids[0])
        from game.core.coop_engine import CoopEngine
        coop = CoopEngine(self.plugin.save_manager, self.plugin.engine)
        coop.mark_downed(run, run.players[uids[1]])
        self.assertTrue(run.players[uids[1]].downed)
        self.assertFalse(coop.is_all_downed(run))
        self.assertTrue(run.node_data["turn_ready"][uids[1]])
        self.plugin.save_manager.save_coop_save(uids[0], run)
        downed = self.run_cmd("e", uids[1])
        self.assertIn("倒地", downed)
        coop.assign_enemy_targets(run)
        for target in run.node_data.get("enemy_targets", {}).values():
            if target != "ALL":
                self.assertNotEqual(target, uids[1])
        notices = coop.revive_downed_players(run)
        self.assertTrue(any(run.players[uids[1]].name in notice for notice in notices))
        self.assertEqual(run.players[uids[1]].hp, 1)
        self.assertFalse(run.players[uids[1]].downed)
        coop.mark_downed(run, run.players[uids[0]])
        coop.mark_downed(run, run.players[uids[1]])
        self.assertTrue(coop.is_all_downed(run))

    def test_shared_relic_coin_toss(self):
        uids = ["relic_a", "relic_b"]
        run = self.start_coop(uids)
        from game.core.coop_engine import CoopEngine
        from game.entities import get_relic_name
        coop = CoopEngine(self.plugin.save_manager, self.plugin.engine)
        relic_id = next(
            rid
            for rid in ("ancient_eye", "dragon_blood", "energy_core")
            if all(rid not in run.players[uid].relics for uid in uids)
        )
        before_gold = {uid: run.players[uid].gold for uid in uids}
        coop.gain_shared_relic(run, uids[0], relic_id)
        coop.gain_shared_relic(run, uids[1], relic_id)
        random.seed(7)
        notices = coop.resolve_relic_claims(run)
        winners = [uid for uid in uids if relic_id in run.players[uid].relics]
        self.assertEqual(len(winners), len(uids))
        for uid in uids:
            self.assertEqual(run.players[uid].gold, before_gold[uid])
        self.assertIn(get_relic_name(relic_id), "\n".join(notices))
        self.assertEqual(run.node_data.get("relic_claims"), {})

    def test_map_vote_and_coop_abandon(self):
        uids = ["vote_a", "vote_b"]
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        self.assertGreaterEqual(len(options), 2)
        started = self.run_cmd("c 1", uids[1])
        self.assertNotIn("路线意向", started)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertNotEqual(run.node_type, "map_select")
        blocked = self.run_cmd("start confirm", uids[0])
        self.assertIn("联机", blocked)
        self.assertIsNotNone(self.plugin.save_manager.load_save(uids[0]))
        abandoned = self.run_cmd("abandon confirm", uids[0])
        self.assertIn("全队进度已结算", abandoned)
        for uid in uids:
            self.assertIsNone(self.plugin.save_manager.load_save(uid))
            self.assertEqual(getattr(self.plugin.save_manager.load_stats(uid), "active_coop_id", ""), "")

    def test_map_vote_half_threshold(self):
        uids = ["half_a", "half_b", "half_c", "half_d"]
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        self.assertGreaterEqual(len(options), 2)
        first = self.run_cmd("c 1", uids[1])
        self.assertIn("路线意向", first)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.node_type, "map_select")
        self.assertEqual(run.node_data.get("votes", {}).get(uids[1]), 1)
        second = self.run_cmd("c 1", uids[2])
        self.assertNotIn("路线意向", second)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertNotEqual(run.node_type, "map_select")

    def test_map_vote_leader_direct_for_three(self):
        uids = ["lead_a", "lead_b", "lead_c"]
        self.start_coop(uids)
        result = self.run_cmd("c 1", uids[0])
        self.assertNotIn("路线意向", result)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertNotEqual(run.node_type, "map_select")

    def test_independent_battle_rewards(self):
        uids = ["reward_a", "reward_b"]
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        battle_index = next(
            index + 1
            for index, option in enumerate(options)
            if option.get("node_type") in ("battle", "elite")
        )
        self.run_cmd(f"c {battle_index}", uids[0])
        run = self.plugin.save_manager.load_save(uids[0])
        from game.core.coop_engine import CoopEngine
        coop = CoopEngine(self.plugin.save_manager, self.plugin.engine)
        before = {uid: run.players[uid].gold for uid in uids}
        coop.init_coop_rewards(run, "normal")
        self.plugin.save_manager.save_coop_save(uids[0], run)
        amounts = {}
        for uid in uids:
            member_run = self.plugin.save_manager.load_save(uid)
            self.assertEqual(member_run.node_type, "reward")
            self.assertTrue(member_run.node_data.get("items"))
            amounts[uid] = member_run.node_data["items"][0].get("amount", 0)
            claimed = self.run_cmd("c 1", uid)
            self.assertIn("金币", claimed)
            self.run_cmd("c 取消", uid)
        advanced = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(advanced.node_type, "map_select")
        for uid in uids:
            self.assertEqual(advanced.players[uid].gold, before[uid] + amounts[uid])

    def test_own_action_logs_only(self):
        player_a = PlayerState(30, 30, 0, 0, 1, "甲")
        player_b = PlayerState(30, 30, 0, 0, 1, "乙")
        run = GameRun(
            user_id="log_a",
            node_type="battle",
            player=player_a,
            coop_id="coop_log",
            party_order=["log_a", "log_b"],
            players={"log_a": player_a, "log_b": player_b},
        )
        engine = self.plugin.engine.battle_engine
        run.user_id = "log_a"
        run.player = player_a
        engine._log_event(run, "甲的记录")
        run.user_id = "log_b"
        run.player = player_b
        engine._log_event(run, "乙的记录")
        run.user_id = "log_a"
        run.player = player_a
        res_a = engine._append_logs_to_res(run, "行动")
        self.assertIn("甲的记录", res_a)
        self.assertNotIn("乙的记录", res_a)
        run.user_id = "log_b"
        run.player = player_b
        res_b = engine._append_logs_to_res(run, "行动")
        self.assertIn("乙的记录", res_b)
        self.assertNotIn("甲的记录", res_b)

    def _force_shared_event(self, uids, event_id):
        run = self.plugin.save_manager.load_save(uids[0])
        run.node_type = "event"
        explore = self.plugin.engine.map_engine.explore_engine
        event = next(e for e in ALL_EVENTS if e.id == event_id)
        with patch("game.core.explore_engine.random.choice", return_value=event):
            explore._init_event_node(run)
        self.plugin.save_manager.save_coop_save(uids[0], run)
        return run

    def test_coop_event_is_shared(self):
        uids = ["event_a", "event_b"]
        self.start_coop(uids)
        run = self._force_shared_event(uids, "altar")
        self.assertEqual(run.node_type, "event")
        self.assertEqual(run.node_data.get("player_views"), {})
        loaded = [self.plugin.save_manager.load_save(uid) for uid in uids]
        self.assertEqual(len({item.node_data.get("event_id") for item in loaded}), 1)
        self.assertEqual(loaded[0].node_data.get("options"), loaded[1].node_data.get("options"))
        self.assertTrue(loaded[0].node_data.get("options"))

    def test_coop_event_effects_all_players(self):
        uids = ["effect_a", "effect_b", "effect_c"]
        self.start_coop(uids)
        before = {uid: self.plugin.save_manager.load_save(uid).player.gold for uid in uids}
        names = {uid: self.plugin.save_manager.load_save(uid).player.name for uid in uids}
        self._force_shared_event(uids, "altar")
        result = self.run_cmd("c 2", uids[0])
        self.assertIn("全队共同应对事件", result)
        for uid in uids:
            self.assertIn(names[uid], result)
        after = {uid: self.plugin.save_manager.load_save(uid).player.gold for uid in uids}
        for uid in uids:
            self.assertGreater(after[uid], before[uid])
        self.assertEqual(self.plugin.save_manager.load_save(uids[0]).node_type, "map_select")

    def test_coop_event_vote_half_threshold(self):
        uids = ["evvote_a", "evvote_b", "evvote_c", "evvote_d"]
        self.start_coop(uids)
        self._force_shared_event(uids, "lost_maze")
        first = self.run_cmd("c 1", uids[1])
        self.assertIn("事件意向已记录", first)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.node_type, "event")
        self.assertEqual(run.node_data.get("event_id"), "lost_maze")
        second = self.run_cmd("c 1", uids[2])
        self.assertNotIn("事件意向已记录", second)
        self.assertIn("全队共同应对事件", second)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.node_type, "event")
        self.assertEqual(run.node_data.get("event_id"), "maze_guard")

    def test_coop_event_battle_enters_whole_party(self):
        uids = ["bt_a", "bt_b", "bt_c"]
        self.start_coop(uids)
        self._force_shared_event(uids, "lost_maze")
        self.run_cmd("c 1", uids[0])
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.node_data.get("event_id"), "maze_guard")
        fight_idx = next(
            index + 1
            for index, option in enumerate(run.node_data.get("options", []))
            if option.get("action") == "fight_guard"
        )
        result = self.run_cmd(f"c {fight_idx}", uids[0])
        self.assertIn("全队共同应对事件", result)
        final = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(final.node_type, "battle")
        self.assertEqual(len(final.players), len(uids))
        self.assertIn("coop_hp_mult", final.node_data)
        for uid in uids:
            member = self.plugin.save_manager.load_save(uid)
            self.assertEqual(member.node_type, "battle")
            self.assertFalse(member.player.downed)

    def test_coop_projection_sends_one_message_per_command(self):
        uids = ["projection_a", "projection_b"]
        self.start_coop(uids)
        service = self.plugin.cli_router.projection_service
        for uid in uids:
            service.consume(uid)
        self.run_cmd("team", uids[1])
        first = service.consume(uids[0])
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["command"], "team")
        self.assertTrue(first[0]["result"])
        self.assertIn("[队员1]", first[0]["text"])
        self.assertEqual(service.consume(uids[1]), [])
        self.run_cmd("team", uids[1])
        second = service.consume(uids[0])
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["command"], "team")
        self.assertNotEqual(first[0]["text"], "")
        self.run_cmd("projection 关闭", uids[0])
        self.assertEqual(service.consume(uids[1]), [])
        self.run_cmd("team", uids[1])
        self.assertEqual(service.consume(uids[0]), [])
        toggled = self.run_cmd("projection", uids[0])
        self.assertIn("开启", toggled)
        self.run_cmd("team", uids[1])
        self.assertEqual(len(service.consume(uids[0])), 1)

    def test_coop_logc_shows_all_party_logs(self):
        uids = ["logc_a", "logc_b"]
        self.start_coop(uids)
        team_result = self.run_cmd("logc 10", uids[0])
        self.assertIn("队伍最近", team_result)
        self.assertIn("队员1", team_result)
        self.assertIn("c 1", team_result)
        personal_result = self.run_cmd("logs 10", uids[0])
        self.assertIn("最近", personal_result)
        self.assertNotIn("队伍最近", personal_result)
        self.assertIn("c 1", personal_result)

    def test_coop_reward_card_select_reuses_relic_hooks(self):
        uids = ["card_reward_a", "card_reward_b"]
        run = self.start_coop(uids)
        cards = ["fireball", "magic_shield"]
        views = {
            uid: {
                "node_type": "reward",
                "data": {
                    "items": [{"type": "card_reward", "cards": list(cards), "taken": False, "force": True}],
                    "coop_done": False,
                },
            }
            for uid in uids
        }
        run.node_type = "reward"
        run.node_data = {
            "coop_node_type": "reward",
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        }
        if "trash_mountain" not in run.players[uids[0]].relics:
            run.players[uids[0]].relics.append("trash_mountain")
        from game.models.coop_view import apply_view
        apply_view(run, uids[0])
        self.plugin.save_manager.save_coop_save(uids[0], run)

        opened = self.run_cmd("c 1", uids[0])
        owner = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(owner.node_type, "card_select")
        self.assertFalse(owner.node_data.get("can_skip"))
        self.assertTrue(owner.node_data.get("force_upgraded"))
        self.assertIn(ALL_CARDS[CardState(id="fireball", upgraded=True)].desc, opened)
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(teammate.node_type, "reward")

        refused = self.run_cmd("c 3", uids[0])
        self.assertIn("无法跳过", refused)
        owner = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(owner.node_type, "card_select")

        self.run_cmd("c 1", uids[0])
        owner = self.plugin.save_manager.load_save(uids[0])
        obtained = [card for card in owner.player.deck if getattr(card, "id", "") == "fireball"]
        self.assertTrue(obtained)
        self.assertTrue(obtained[-1].upgraded)

    def test_coop_rest_card_select_reuses_standard_renderer(self):
        uids = ["rest_card_a", "rest_card_b"]
        run = self.start_coop(uids)
        items = [
            {"type": "rest_heal", "taken": False},
            {"type": "rest_meditate", "taken": False},
            {"type": "rest_upgrade", "taken": False},
            {"type": "rest_mend", "taken": False},
        ]
        views = {
            uid: {"node_type": "rest", "data": {"items": list(items), "coop_done": False}}
            for uid in uids
        }
        run.node_type = "rest"
        run.node_data = {
            "coop_node_type": "rest",
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        }
        from game.models.coop_view import apply_view
        apply_view(run, uids[0])
        self.plugin.save_manager.save_coop_save(uids[0], run)
        before = len(self.plugin.save_manager.load_save(uids[0]).player.deck)

        opened = self.run_cmd("c 2", uids[0])
        owner = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(owner.node_type, "card_select")
        self.assertTrue(owner.node_data.get("can_skip"))
        cards = owner.node_data.get("cards", [])
        self.assertTrue(cards)
        self.assertIn(ALL_CARDS[CardState(id=cards[0])].desc, opened)

        self.run_cmd("c 1", uids[0])
        owner = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(owner.node_type, "rest")
        self.assertTrue(owner.node_data.get("coop_done"))
        self.assertEqual(len(owner.player.deck), before + 1)

    def test_coop_gem_flow_preserves_teammate_view(self):
        uids = ["gem_a", "gem_b"]
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        shop_index = next(index + 1 for index, option in enumerate(options) if option.get("node_type") == "shop")
        self.run_cmd(f"c {shop_index}", uids[0])
        run = self.plugin.save_manager.load_save(uids[0])
        items = list(run.node_data.get("items", []))
        gem_id = next(iter(GEM_CONFIG))
        explore = self.plugin.engine.map_engine.explore_engine
        explore.start_gem_insert_flow(run, gem_id, "shop", {"items": items})
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "gem_insert")
        self.assertEqual(teammate.node_type, "shop")
        self.assertTrue(teammate.node_data.get("items"))
        explore.gem_insert_cancel(owner)
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "shop")
        self.assertEqual(teammate.node_type, "shop")
        self.assertTrue(owner.node_data.get("items"))
        self.assertTrue(teammate.node_data.get("items"))

    def test_coop_treasure_card_select_is_private(self):
        uids = ["treasure_a", "treasure_b"]
        run = self.start_coop(uids)
        items = [
            {"type": "card_reward", "cards": ["fireball"], "taken": False},
            {"type": "gem", "gem_id": next(iter(GEM_CONFIG)), "taken": False},
        ]
        views = {
            uid: {"node_type": "treasure", "data": {"state": "opened", "items": list(items)}}
            for uid in uids
        }
        run.node_type = "treasure"
        run.node_data = {
            "coop_node_type": "treasure",
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        }
        from game.models.coop_view import apply_view
        apply_view(run, uids[0])
        self.plugin.save_manager.save_coop_save(uids[0], run)
        owner = self.plugin.save_manager.load_save(uids[0])
        self.plugin.engine.map_engine.choose_option(owner, 1)
        self.plugin.save_manager.save_save(uids[0], owner)
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "card_select")
        self.assertIn("fireball", owner.node_data.get("cards", []))
        self.assertEqual(teammate.node_type, "treasure")
        self.assertEqual(
            [item["type"] for item in teammate.node_data.get("items", [])],
            ["card_reward", "gem"],
        )
        self.plugin.engine.map_engine.choose_option(owner, 1)
        self.plugin.save_manager.save_save(uids[0], owner)
        owner = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(owner.node_type, "treasure")
        self.plugin.engine.map_engine.choose_option(owner, 1)
        self.plugin.save_manager.save_save(uids[0], owner)
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "gem_insert")
        self.assertEqual(teammate.node_type, "treasure")
        self.assertEqual(
            [item["type"] for item in teammate.node_data.get("items", [])],
            ["card_reward", "gem"],
        )
        self.plugin.engine.map_engine.explore_engine.gem_insert_cancel(owner)
        self.plugin.save_manager.save_save(uids[0], owner)
        owner = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(owner.node_type, "treasure")

    def test_coop_reward_completion_advances_once(self):
        uids = ["once_reward_leader", "once_reward_member"]
        run = self.start_coop(uids)
        stage = run.players[uids[0]].stage
        options = run.node_data.get("options", [])
        battle_index = next(
            index + 1
            for index, option in enumerate(options)
            if option.get("node_type") in ("battle", "elite")
        )
        self.run_cmd(f"c {battle_index}", uids[0])
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.node_type, "battle")
        for enemy in run.enemies:
            enemy.hp = 0
        self.plugin.engine.battle_engine._handle_battle_win(run)
        reward = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(reward.node_type, "reward")
        self.assertTrue(reward.node_data.get("items"))
        self.assertEqual(reward.players[uids[0]].stage, stage)

        waiting = self.run_cmd("c 取消", uids[0])
        self.assertIn("等待队友", waiting)
        mid = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(mid.node_type, "reward")
        self.assertTrue(mid.node_data.get("stage_ready", {}).get(uids[0]))
        self.assertFalse(mid.node_data.get("stage_ready", {}).get(uids[1]))
        self.assertEqual(mid.players[uids[0]].stage, stage)
        self.assertEqual(mid.players[uids[1]].stage, stage)

        completed = self.run_cmd("c 取消", uids[1])
        self.assertIn("继续前进", completed)
        for uid in uids:
            advanced = self.plugin.save_manager.load_save(uid)
            self.assertEqual(advanced.node_type, "map_select")
            self.assertEqual(advanced.players[uids[0]].stage, stage + 1)
            self.assertEqual(advanced.players[uids[1]].stage, stage + 1)
        self.run_cmd("c 取消", uids[0])
        unchanged = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(unchanged.node_type, "map_select")
        self.assertEqual(unchanged.players[uids[0]].stage, stage + 1)

    def test_coop_rest_completion_advances_once(self):
        uids = ["once_rest_leader", "once_rest_member"]
        run = self.start_coop(uids)
        stage = run.players[uids[0]].stage
        options = run.node_data.get("options", [])
        rest_index = next(
            index + 1
            for index, option in enumerate(options)
            if option.get("node_type") == "rest"
        )
        self.run_cmd(f"c {rest_index}", uids[0])
        rest = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(rest.node_type, "rest")
        self.assertEqual(rest.players[uids[0]].stage, stage)

        waiting = self.run_cmd("c 4", uids[0])
        self.assertIn("救治", waiting)
        mid = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(mid.node_type, "rest")
        self.assertTrue(mid.node_data.get("stage_ready", {}).get(uids[0]))
        self.assertFalse(mid.node_data.get("stage_ready", {}).get(uids[1]))
        self.assertEqual(mid.players[uids[0]].stage, stage)

        completed = self.run_cmd("c 4", uids[1])
        self.assertIn("继续前进", completed)
        for uid in uids:
            advanced = self.plugin.save_manager.load_save(uid)
            self.assertEqual(advanced.node_type, "map_select")
            self.assertEqual(advanced.players[uids[0]].stage, stage + 1)
            self.assertEqual(advanced.players[uids[1]].stage, stage + 1)
        self.run_cmd("c 取消", uids[0])
        unchanged = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(unchanged.node_type, "map_select")
        self.assertEqual(unchanged.players[uids[0]].stage, stage + 1)

    def test_coop_gem_completion_advances_once(self):
        uids = ["once_gem_leader", "once_gem_member"]
        run = self.start_coop(uids)
        stage = run.players[uids[0]].stage
        gem_id = next(iter(GEM_CONFIG))
        views = {
            uid: {
                "node_type": "treasure",
                "data": {
                    "state": "opened",
                    "items": [{"type": "gem", "gem_id": gem_id, "taken": False}],
                },
            }
            for uid in uids
        }
        run.node_type = "treasure"
        run.node_data = {
            "coop_node_type": "treasure",
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        }
        from game.models.coop_view import apply_view
        apply_view(run, uids[0])
        self.plugin.save_manager.save_coop_save(uids[0], run)

        opened = self.run_cmd("c 1", uids[0])
        self.assertIn("强制镶嵌", opened)
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "gem_insert")
        self.assertEqual(teammate.node_type, "treasure")
        self.assertFalse(teammate.node_data["items"][0]["taken"])

        inserted = self.run_cmd("c 1", uids[0])
        self.assertIn("镶嵌成功", inserted)
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "treasure")
        self.assertTrue(owner.node_data["items"][0]["taken"])
        self.assertTrue(any(gem_id in card.gems for card in owner.player.deck))
        self.assertEqual(teammate.node_type, "treasure")
        self.assertFalse(teammate.node_data["items"][0]["taken"])
        self.assertFalse(any(gem_id in card.gems for card in teammate.player.deck))

        waiting = self.run_cmd("c 取消", uids[0])
        self.assertIn("等待队友", waiting)
        mid = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(mid.node_type, "treasure")
        self.assertEqual(mid.players[uids[0]].stage, stage)
        self.assertTrue(mid.node_data.get("stage_ready", {}).get(uids[0]))
        self.assertFalse(mid.node_data["items"][0]["taken"])

        opened_b = self.run_cmd("c 1", uids[1])
        self.assertIn("强制镶嵌", opened_b)
        member = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(member.node_type, "gem_insert")
        member_inserted = self.run_cmd("c 1", uids[1])
        self.assertIn("镶嵌成功", member_inserted)
        member = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(member.node_type, "treasure")
        self.assertTrue(member.node_data["items"][0]["taken"])
        self.assertTrue(any(gem_id in card.gems for card in member.player.deck))
        leader = self.plugin.save_manager.load_save(uids[0])
        self.assertTrue(any(gem_id in card.gems for card in leader.player.deck))

        completed = self.run_cmd("c 取消", uids[1])
        self.assertIn("继续前进", completed)
        for uid in uids:
            advanced = self.plugin.save_manager.load_save(uid)
            self.assertEqual(advanced.node_type, "map_select")
            self.assertEqual(advanced.players[uids[0]].stage, stage + 1)
            self.assertEqual(advanced.players[uids[1]].stage, stage + 1)
        self.run_cmd("c 取消", uids[0])
        unchanged = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(unchanged.node_type, "map_select")
        self.assertEqual(unchanged.players[uids[0]].stage, stage + 1)

    def enter_coop_battle(self, uids):
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        battle_index = next(
            index + 1 for index, option in enumerate(options) if option.get("node_type") in ("battle", "elite")
        )
        self.run_cmd(f"c {battle_index}", uids[0])
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.node_type, "battle")
        return run

    def set_hand(self, uid, states):
        run = self.plugin.save_manager.load_save(uid)
        run.player = run.players[uid]
        run.players[uid].hand = list(states)
        self.plugin.save_manager.save_coop_save(uid, run)
        return run

    def test_coop_battle_logs_not_replayed(self):
        uids = ["log_leader", "log_member"]
        self.enter_coop_battle(uids)
        uid = uids[0]
        self.set_hand(uid, [CardState(id="mercenary"), CardState(id="mercenary")])
        first = self.run_cmd("p 1", uid)
        self.assertIn("✨ [消耗] 【雇佣兵】进入战场。", first)
        second = self.run_cmd("p 1", uid)
        self.assertEqual(second.count("✨ [消耗] 【雇佣兵】进入战场。"), 1)
        run = self.plugin.save_manager.load_save(uid)
        self.assertFalse(run.node_data.get("battle_logs"))

    def test_coop_last_ender_clears_single_turn_buff(self):
        uids = ["focus_leader", "focus_member"]
        self.enter_coop_battle(uids)
        from game.models.state import BuffState
        waiting = self.run_cmd("e", uids[0])
        self.assertIn("等待队友", waiting)
        run = self.plugin.save_manager.load_save(uids[1])
        run.player = run.players[uids[1]]
        run.players[uids[1]].buffs.append(BuffState("tactical_focus", "无法抽牌", 1, None, ""))
        self.plugin.save_manager.save_coop_save(uids[1], run)
        self.run_cmd("e", uids[1])
        run = self.plugin.save_manager.load_save(uids[1])
        self.assertFalse(any(b.id == "tactical_focus" for b in run.players[uids[1]].buffs))
        self.assertEqual(len(run.players[uids[1]].hand), 6)

    def test_coop_echo_form_uses_per_player_play_count(self):
        uids = ["echo_leader", "echo_member"]
        self.enter_coop_battle(uids)
        from game.models.state import BuffState
        self.set_hand(uids[0], [CardState(id="quick_strike")] * 3)
        self.run_cmd("p 1", uids[0])
        self.run_cmd("p 1", uids[0])
        run = self.plugin.save_manager.load_save(uids[1])
        run.player = run.players[uids[1]]
        run.players[uids[1]].buffs.append(BuffState("echo_form", "回响形态", 1, None, ""))
        run.players[uids[1]].hand = [CardState(id="arcane_spark")]
        run.players[uids[1]].actions = 2
        run.players[uids[1]].bonus_actions = 1
        self.plugin.save_manager.save_coop_save(uids[1], run)
        res = self.run_cmd("p 1", uids[1])
        self.assertIn("[回响触发]", res)

    def test_coop_minion_card_leaves_hand_and_stays(self):
        uids = ["minion_leader", "minion_member"]
        self.enter_coop_battle(uids)
        uid = uids[0]
        self.set_hand(uid, [CardState(id="mercenary", upgraded=True)])
        self.run_cmd("p 1", uid)
        run = self.plugin.save_manager.load_save(uid)
        player = run.players[uid]
        self.assertEqual(player.minions["1"].id, "mercenary+")
        self.assertFalse([c for c in player.hand if c.id == "mercenary"])
        self.assertFalse([c for c in player.discard_pile if c.id == "mercenary"])
        self.assertFalse([c for c in player.exhaust_pile if c.id == "mercenary"])
        self.run_cmd("e", uid)
        self.run_cmd("e", uids[1])
        run = self.plugin.save_manager.load_save(uid)
        player = run.players[uid]
        self.assertIn("1", player.minions)
        self.assertEqual(player.minions["1"].id, "mercenary+")
        self.assertEqual(player.minions["1"].atk, 5)
        self.assertFalse([c for c in player.hand if c.id == "mercenary"])

    def test_coop_cafe_and_ancient_wait_for_all_players(self):
        uids = ["cafe_wait_leader", "cafe_wait_member"]
        run = self.start_coop(uids)
        from game.data.map_config import MapConfig
        cafe_stage = MapConfig.CAFE_STAGES[0]
        for uid in uids:
            run.players[uid].stage = cafe_stage - 1
        self.plugin.save_manager.save_coop_save(uids[0], run)
        self.plugin.engine.map_engine.enter_next_stage(self.plugin.save_manager.load_save(uids[0]))
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
            ancient = self.plugin.save_manager.load_save(uid)
            self.assertEqual(ancient.node_type, "ancient")
            self.assertEqual(ancient.players[uid].stage, cafe_stage)

        waiting = self.run_cmd("c 1", uids[0])
        self.assertIn("等待队友", waiting)
        member = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(member.node_type, "ancient")

        completed = self.run_cmd("c 1", uids[1])
        self.assertIn("继续前进", completed)
        for uid in uids:
            advanced = self.plugin.save_manager.load_save(uid)
            self.assertEqual(advanced.node_type, "map_select")
            self.assertEqual(advanced.players[uid].stage, cafe_stage + 1)

    def test_coop_ally_card_defaults_to_first_teammate(self):
        uids = ["ally_default_leader", "ally_default_member", "ally_default_third"]
        self.enter_coop_battle(uids)
        uid = uids[0]
        self.set_hand(uid, [CardState(id="coop_tactical_command")])
        before = self.plugin.save_manager.load_save(uids[1]).players[uids[1]].actions
        result = self.run_cmd("p 1", uid)
        self.assertNotIn("请指定", result)
        self.assertIn("战术指挥", result)
        after = self.plugin.save_manager.load_save(uids[1]).players[uids[1]].actions
        self.assertEqual(after, before + 1)


if __name__ == "__main__":
    unittest.main()
