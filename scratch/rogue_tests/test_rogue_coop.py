import asyncio
import random
import re
import tempfile
import unittest
from collections import Counter

from scratch.rogue_tests.base import CorePlugin, run_command
from game.data.gem_data import GEM_CONFIG


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

    def make_friends(self, leader, others):
        self.run_cmd(f"friend name 队长", leader)
        for index, uid in enumerate(others, 1):
            self.run_cmd(f"friend name 队员{index}", uid)
            self.run_cmd(f"friend add {uid}", leader)
            self.run_cmd(f"friend accept {leader}", uid)

    def create_team(self, leader, others):
        result = self.run_cmd("team create", leader)
        self.assertIn("已创建队伍", result)
        lobby_id = re.search(r"队伍 ([A-Z0-9]{6})", result).group(1)
        for uid in others:
            invited = self.run_cmd(f"friend invite {uid}", leader)
            self.assertIn("已邀请", invited)
            joined = self.run_cmd(f"team join {lobby_id}", uid)
            self.assertIn("已加入队伍", joined)
        return lobby_id

    def start_coop(self, uids):
        leader = uids[0]
        self.make_friends(leader, uids[1:])
        self.create_team(leader, uids[1:])
        for uid in uids[1:]:
            ready = self.run_cmd("team ready", uid)
            self.assertIn("已准备就绪", ready)
        random.seed(0)
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
        self.run_cmd("friend name 队长", leader)
        self.run_cmd("friend name 路人", stranger)
        for index, uid in enumerate(friends, 1):
            self.run_cmd(f"friend name 好友{index}", uid)
            self.run_cmd(f"friend add {uid}", leader)
            self.run_cmd(f"friend accept {leader}", uid)
        result = self.run_cmd("friend list", leader)
        self.assertIn("好友列表（5 人）", result)
        self.run_cmd("friend bind qq_rule_test", friends[0])
        searched = self.run_cmd("friend search qq_rule_test", leader)
        self.assertIn(friends[0], searched)
        self.assertIn("好友1", searched)
        named = self.run_cmd("friend search 好友2", leader)
        self.assertIn(friends[1], named)
        result = self.run_cmd("team create", leader)
        lobby_id = re.search(r"队伍 ([A-Z0-9]{6})", result).group(1)
        rejected = self.run_cmd(f"team invite {stranger}", leader)
        self.assertIn("还不是你的好友", rejected)
        for uid in friends[:3]:
            invited = self.run_cmd(f"team invite {uid}", leader)
            self.assertIn("已邀请", invited)
        overflow = self.run_cmd(f"team invite {friends[3]}", leader)
        self.assertIn("最多 4 人", overflow)
        joined = self.run_cmd(f"team join {lobby_id}", friends[0])
        self.assertIn("已加入队伍", joined)
        not_ready = self.run_cmd("team start", leader)
        self.assertIn("尚未准备", not_ready)
        left = self.run_cmd("team disband", leader)
        self.assertIn("已解散", left)
        mutual_a = "mutual_a"
        mutual_b = "mutual_b"
        self.run_cmd("friend name 互加甲", mutual_a)
        self.run_cmd("friend name 互加乙", mutual_b)
        self.run_cmd(f"friend add {mutual_b}", mutual_a)
        mutual = self.run_cmd(f"friend add {mutual_a}", mutual_b)
        self.assertIn("已成为好友", mutual)
        self.assertIn(mutual_b, self.run_cmd("friend list", mutual_a))

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
        self.assertEqual(len(winners), 1)
        loser = next(uid for uid in uids if uid != winners[0])
        self.assertEqual(run.players[loser].gold, before_gold[loser] + 25)
        self.assertIn(get_relic_name(relic_id), "\n".join(notices))
        self.assertEqual(run.node_data.get("relic_claims"), {})

    def test_map_vote_and_coop_abandon(self):
        uids = ["vote_a", "vote_b"]
        run = self.start_coop(uids)
        options = run.node_data.get("options", [])
        self.assertGreaterEqual(len(options), 2)
        vote = self.run_cmd("c 1", uids[1])
        self.assertIn("路线意向", vote)
        run = self.plugin.save_manager.load_save(uids[0])
        self.assertEqual(run.node_data.get("votes", {}).get(uids[1]), 1)
        started = self.run_cmd("c 2", uids[0])
        self.assertNotIn("无效", started)
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


if __name__ == "__main__":
    unittest.main()
