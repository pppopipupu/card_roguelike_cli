import asyncio
import random
import re
import tempfile
import unittest
from unittest.mock import patch
from game.entities.events import ALL_EVENTS
from game.test.core.base import CorePlugin, floor_of, load_run, move_to_room, run_command, walk_to_boss_battle
from game.core.party.session import SessionContextScoper
from game.data.account_config import RENAME_COST_GP
from game.data.gem_data import GEM_CONFIG
from game.entities.cards.base import ALL_CARDS
from game.models.state import CardState, GameRun, PlayerState
from game.test.core.coop_base import CoopTestBase


class TestCoopRewardsAndRelics(CoopTestBase):
    def test_independent_shop_and_rest_mend(self):
        uids = ["shop_a", "shop_b"]
        run = self.start_coop(uids)
        shop_coord = next((c for c, r in floor_of(run).rooms.items() if r.room_type == "shop"), "A1")
        SessionContextScoper.create_session(run, shop_coord, "shop", uids)
        self.plugin.engine.map_engine.explore_engine._init_shop_node(run)
        self.plugin.save_manager.save_save(uids[0], run)
        shop_a = load_run(self.plugin, uids[0])
        shop_b = load_run(self.plugin, uids[1])
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
        after_a = load_run(self.plugin, uids[0])
        after_b = load_run(self.plugin, uids[1])
        self.assertIn(bought_card, {state.id for state in after_a.player.deck})
        self.assertEqual(after_b.player.gold, shop_b.player.gold)
        self.assertFalse(after_b.node_data["items"][buy_index - 1].get("sold"))
        leave_index = len(items_a)
        self.run_cmd(f"c {leave_index}", uids[0])
        self.run_cmd(f"c {leave_index}", uids[1])
        advanced = load_run(self.plugin, uids[0])
        self.assertEqual(advanced.node_type, "grid_map")

        uids = ["rest_a", "rest_b"]
        run = self.start_coop(uids)
        rest_coord = next((c for c, r in floor_of(run).rooms.items() if r.room_type == "rest"), "A1")
        SessionContextScoper.create_session(run, rest_coord, "rest", uids)
        self.plugin.engine.map_engine.explore_engine._init_rest_node(run)
        self.plugin.save_manager.save_save(uids[0], run)
        status = self.run_cmd("status", uids[0])
        self.assertIn("救治队友", status)
        mend = self.run_cmd("c 4", uids[0])
        self.assertIn("救治", mend)
        mend = self.run_cmd("c 4", uids[1])
        self.assertIn("救治", mend)
        advanced = load_run(self.plugin, uids[0])
        self.assertEqual(advanced.node_type, "grid_map")

    def test_coop_relic_pool_contest(self):
        uids = ["relic_a", "relic_b"]
        run = self.start_coop(uids)
        from game.entities import get_relic_name
        from game.models.coop_view import apply_view
        relic_a, relic_b = "ancient_eye", "dragon_blood"
        pool = [
            {"relic_id": relic_a, "claimed_by": ""},
            {"relic_id": relic_b, "claimed_by": ""},
        ]
        views = {
            uid: {
                "node_type": "reward",
                "data": {
                    "items": [{"type": "gold", "amount": 1, "taken": False}],
                    "coop_done": False,
                },
            }
            for uid in uids
        }
        SessionContextScoper.create_session(run, "A1", "reward", uids, node_data={
            "coop_node_type": "reward",
            "coop_relic_pool": pool,
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        })
        apply_view(run, uids[0])
        self.plugin.save_manager.save_save(uids[0], run)

        first = self.run_cmd("c 1", uids[0])
        self.assertIn(get_relic_name(relic_a), first)
        owner = load_run(self.plugin, uids[0])
        self.assertEqual(owner.node_data["coop_relic_pool"][0]["claimed_by"], uids[0])

        unclaimed = self.run_cmd("c 1", uids[0])
        self.assertIn("取消了对遗物", unclaimed)
        owner = load_run(self.plugin, uids[0])
        self.assertEqual(owner.node_data["coop_relic_pool"][0]["claimed_by"], "")
        self.assertNotIn(relic_a, owner.players[uids[0]].relics)

        reclaimed = self.run_cmd("c 1", uids[0])
        self.assertIn(get_relic_name(relic_a), reclaimed)
        owner = load_run(self.plugin, uids[0])
        self.assertEqual(owner.node_data["coop_relic_pool"][0]["claimed_by"], uids[0])
        self.assertIn(relic_a, owner.players[uids[0]].relics)

        blocked = self.run_cmd("c 2", uids[0])
        self.assertIn("最多只能选择 1 件遗物", blocked)

        taken = self.run_cmd("c 1", uids[1])
        self.assertIn("夺走", taken)
        self.assertEqual(
            load_run(self.plugin, uids[1]).node_data["coop_relic_pool"][0]["claimed_by"],
            uids[0],
        )

        second = self.run_cmd("c 2", uids[1])
        self.assertIn(get_relic_name(relic_b), second)
        teammate = load_run(self.plugin, uids[1])
        self.assertEqual(teammate.node_data["coop_relic_pool"][1]["claimed_by"], uids[1])

        self.assertIn(relic_a, load_run(self.plugin, uids[0]).players[uids[0]].relics)
        self.assertIn(relic_b, load_run(self.plugin, uids[1]).players[uids[1]].relics)

    def test_ninja_relic_requires_ninja_class(self):
        uids = ["ninja_relic_a", "ninja_relic_b"]
        run = self.start_coop(uids)
        from game.entities import get_relic_name
        from game.models.coop_view import apply_view
        relic_id = "machine_ninja"
        pool = [{"relic_id": relic_id, "claimed_by": ""}]
        views = {
            uid: {
                "node_type": "reward",
                "data": {
                    "items": [{"type": "gold", "amount": 1, "taken": False}],
                    "coop_done": False,
                },
            }
            for uid in uids
        }
        SessionContextScoper.create_session(run, "A1", "reward", uids, node_data={
            "coop_node_type": "reward",
            "coop_relic_pool": pool,
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        })
        apply_view(run, uids[0])
        self.plugin.save_manager.save_save(uids[0], run)

        blocked = self.run_cmd("c 1", uids[0])
        self.assertIn("仅限【蕾忍】", blocked)
        self.assertNotIn(relic_id, load_run(self.plugin, uids[0]).players[uids[0]].relics)

        ninja_run = load_run(self.plugin, uids[1])
        ninja_run.players[uids[1]].selected_class = "蕾忍"
        self.plugin.save_manager.save_save(uids[1], ninja_run)
        claimed = self.run_cmd("c 1", uids[1])
        self.assertIn(get_relic_name(relic_id), claimed)
        self.assertIn(relic_id, load_run(self.plugin, uids[1]).players[uids[1]].relics)

    def test_coop_relic_pool_allows_multiple_picks(self):
        uids = ["multi_a", "multi_b"]
        run = self.start_coop(uids)
        from game.entities import get_relic_name
        from game.models.coop_view import apply_view
        relic_a, relic_b, relic_c = "ancient_eye", "dragon_blood", "gold_compass"
        pool = [
            {"relic_id": relic_a, "claimed_by": ""},
            {"relic_id": relic_b, "claimed_by": ""},
            {"relic_id": relic_c, "claimed_by": ""},
        ]
        views = {
            uid: {
                "node_type": "reward",
                "data": {
                    "items": [{"type": "gold", "amount": 1, "taken": False}],
                    "coop_done": False,
                },
            }
            for uid in uids
        }
        SessionContextScoper.create_session(run, "A1", "reward", uids, node_data={
            "coop_node_type": "reward",
            "coop_relic_pool": pool,
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        })
        apply_view(run, uids[0])
        self.plugin.save_manager.save_save(uids[0], run)

        first = self.run_cmd("c 1", uids[0])
        self.assertIn(get_relic_name(relic_a), first)
        second = self.run_cmd("c 2", uids[0])
        self.assertIn(get_relic_name(relic_b), second)

        blocked = self.run_cmd("c 3", uids[0])
        self.assertIn("最多只能选择 2 件遗物", blocked)

        third = self.run_cmd("c 3", uids[1])
        self.assertIn(get_relic_name(relic_c), third)

        owner = load_run(self.plugin, uids[0])
        self.assertIn(relic_a, owner.players[uids[0]].relics)
        self.assertIn(relic_b, owner.players[uids[0]].relics)
        self.assertIn(relic_c, owner.players[uids[1]].relics)

    def test_coop_elite_relic_pool_count_and_claim(self):
        uids = ["elite_a", "elite_b", "elite_c"]
        run = self.start_coop(uids)
        from game.data.reward_config import ELITE_RELIC_MAP
        SessionContextScoper.create_session(run, "A1", "reward", uids, node_data={"difficulty": "elite", "elite_name": "暗影影魔"})
        before = {uid: len(run.players[uid].relics) for uid in uids}
        self.plugin.engine.battle_engine.card_player.init_rewards(run, "elite")
        self.plugin.save_manager.save_save(uids[0], run)
        saved = load_run(self.plugin, uids[0])
        pool = saved.node_data["coop_relic_pool"]
        ids = [entry["relic_id"] for entry in pool]
        self.assertEqual(len(pool), len(uids) + 1)
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(ids[0], ELITE_RELIC_MAP["暗影影魔"])
        for index, uid in enumerate(uids, 1):
            claimed = self.run_cmd(f"c {index}", uid)
            self.assertIn("获得了遗物", claimed)
        after = load_run(self.plugin, uids[0])
        claims = [entry.get("claimed_by") for entry in after.node_data["coop_relic_pool"]]
        self.assertEqual(claims[: len(uids)], uids)
        self.assertEqual(claims[len(uids)], "")
        for uid in uids:
            member = load_run(self.plugin, uid)
            self.assertEqual(len(member.players[uid].relics), before[uid] + 1)

    def test_downed_teammate_keeps_battle_rewards(self):
        uids = ["downed_reward_a", "downed_reward_b"]
        run = self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        from game.core.battle.party_battle import mark_downed
        mark_downed(self.plugin.engine.battle_engine, run, run.players[uids[1]])
        self.plugin.save_manager.save_save(uids[0], run)
        self.plugin.engine.battle_engine.card_player.init_rewards(run, "normal")
        self.plugin.save_manager.save_save(uids[0], run)

        downed = load_run(self.plugin, uids[1])
        self.assertEqual(downed.node_type, "reward")
        self.assertTrue(downed.node_data.get("items"))
        self.assertFalse(downed.node_data.get("coop_done"))
        self.assertTrue(downed.players[uids[1]].downed)

        gold_before = downed.players[uids[1]].gold
        gold_amount = downed.node_data["items"][0]["amount"]
        self.run_cmd("c 离开", uids[0])
        still = load_run(self.plugin, uids[1])
        self.assertEqual(still.node_type, "reward")
        self.assertTrue(still.players[uids[1]].downed)
        self.assertTrue(still.node_data.get("items"))

        self.run_cmd("c 1", uids[1])
        claimed = load_run(self.plugin, uids[1])
        self.assertEqual(claimed.players[uids[1]].gold, gold_before + gold_amount)
        self.run_cmd("c 离开", uids[1])
        revived = load_run(self.plugin, uids[1])
        self.assertEqual(revived.node_type, "grid_map")
        self.assertEqual(revived.players[uids[1]].hp, 1)
        self.assertFalse(revived.players[uids[1]].downed)

    def test_downed_teammate_keeps_boss_chest(self):
        uids = ["downed_chest_a", "downed_chest_b"]
        run = self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        from game.core.battle.party_battle import mark_downed
        mark_downed(self.plugin.engine.battle_engine, run, run.players[uids[1]])
        self.plugin.save_manager.save_save(uids[0], run)
        self.plugin.engine.battle_engine.card_player.init_boss_chest(run)
        self.plugin.save_manager.save_save(uids[0], run)

        downed = load_run(self.plugin, uids[1])
        self.assertEqual(downed.node_type, "boss_chest")
        self.assertEqual(len([it for it in downed.node_data.get("items", []) if not it.get("taken")]), 3)
        self.assertFalse(downed.node_data.get("coop_done"))

        self.run_cmd("c 1", uids[1])
        revived = load_run(self.plugin, uids[1])
        self.assertEqual(revived.node_type, "grid_map")
        self.assertEqual(revived.players[uids[1]].hp, 1)
        self.assertFalse(revived.players[uids[1]].downed)

    def test_independent_battle_rewards(self):
        uids = ["reward_a", "reward_b"]
        run = self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        before = {uid: run.players[uid].gold for uid in uids}
        self.plugin.engine.battle_engine.card_player.init_rewards(run, "normal")
        self.plugin.save_manager.save_save(uids[0], run)
        amounts = {}
        for uid in uids:
            member_run = load_run(self.plugin, uid)
            self.assertEqual(member_run.node_type, "reward")
            self.assertTrue(member_run.node_data.get("items"))
            amounts[uid] = member_run.node_data["items"][0].get("amount", 0)
            claimed = self.run_cmd("c 1", uid)
            self.assertIn("金币", claimed)
            self.run_cmd("c 取消", uid)
        advanced = load_run(self.plugin, uids[0])
        self.assertEqual(advanced.node_type, "grid_map")
        for uid in uids:
            self.assertEqual(advanced.players[uid].gold, before[uid] + amounts[uid])


if __name__ == "__main__":
    unittest.main()
