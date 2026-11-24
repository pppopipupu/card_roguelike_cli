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


class TestCoopEventsAndViews(CoopTestBase):
    def test_team_event_effects_all_players(self):
        uids = ["effect_a", "effect_b", "effect_c"]
        self.start_coop(uids)
        before = {uid: load_run(self.plugin, uid).player.gold for uid in uids}
        names = {uid: load_run(self.plugin, uid).player.name for uid in uids}
        run = self._force_event(uids, "void_contract")
        idx = self._event_option_index(run, "absorb_void")
        result = ""
        for uid in uids:
            result = self.run_cmd(f"c {idx}", uid)
        self.assertIn("全队投票完成", result)
        self.assertIn("全队共同应对事件", result)
        for uid in uids:
            self.assertIn(names[uid], result)
        after = {uid: load_run(self.plugin, uid).player.gold for uid in uids}
        for uid in uids:
            self.assertGreater(after[uid], before[uid])
        self.assertEqual(load_run(self.plugin, uids[0]).node_type, "grid_map")

    def test_team_event_requires_all_votes(self):
        uids = ["evvote_a", "evvote_b", "evvote_c", "evvote_d"]
        self.start_coop(uids)
        run = self._force_event(uids, "void_contract")
        idx = self._event_option_index(run, "absorb_void")
        for uid in uids[:3]:
            pending = self.run_cmd(f"c {idx}", uid)
            self.assertIn("等待全队投票", pending)
            self.assertEqual(load_run(self.plugin, uids[0]).node_type, "event")
        final = self.run_cmd(f"c {idx}", uids[3])
        self.assertIn("全队投票完成", final)
        final_run = load_run(self.plugin, uids[0])
        self.assertEqual(final_run.node_type, "grid_map")

    def test_team_event_tie_rolls_dice(self):
        uids = ["tie_a", "tie_b"]
        self.start_coop(uids)
        run = self._force_event(uids, "void_contract")
        first = self._event_option_index(run, "contract_relic")
        second = self._event_option_index(run, "contract_legend")
        self.run_cmd(f"c {first}", uids[0])
        final = self.run_cmd(f"c {second}", uids[1])
        self.assertIn("平票", final)
        self.assertIn("掷骰决定", final)
        self.assertEqual(load_run(self.plugin, uids[0]).node_type, "grid_map")

    def test_solo_event_affects_only_trigger(self):
        uids = ["solo_a", "solo_b", "solo_c"]
        self.start_coop(uids)
        before = {uid: load_run(self.plugin, uid).player.gold for uid in uids}
        run = self._force_event([uids[0]], "altar")
        idx = self._event_option_index(run, "break_altar")
        result = self.run_cmd(f"c {idx}", uids[0])
        self.assertNotIn("全队共同应对事件", result)
        after = {uid: load_run(self.plugin, uid).player.gold for uid in uids}
        self.assertGreater(after[uids[0]], before[uids[0]])
        for uid in uids[1:]:
            self.assertEqual(after[uid], before[uid])
            self.assertEqual(load_run(self.plugin, uid).node_type, "grid_map")

    def test_solo_event_battle_uses_trigger_session(self):
        uids = ["bt_a", "bt_b", "bt_c"]
        self.start_coop(uids)
        self._force_event([uids[0]], "lost_maze")
        self.run_cmd("c 1", uids[0])
        run = load_run(self.plugin, uids[0])
        self.assertEqual(run.node_data.get("event_id"), "maze_guard")
        fight_idx = self._event_option_index(run, "fight_guard")
        result = self.run_cmd(f"c {fight_idx}", uids[0])
        self.assertNotIn("全队共同应对事件", result)
        final = load_run(self.plugin, uids[0])
        self.assertEqual(final.node_type, "battle")
        self.assertEqual(final.node_data.get("battle_mode"), "forced_solo")
        self.assertEqual(list(final.party_order), [uids[0]])
        self.assertFalse(final.player.downed)
        for uid in uids[1:]:
            self.assertEqual(load_run(self.plugin, uid).node_type, "grid_map")

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
        SessionContextScoper.create_session(run, "A1", "reward", uids, node_data={
            "coop_node_type": "reward",
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        })
        if "trash_mountain" not in run.players[uids[0]].relics:
            run.players[uids[0]].relics.append("trash_mountain")
        from game.models.coop_view import apply_view
        apply_view(run, uids[0])
        self.plugin.save_manager.save_save(uids[0], run)

        opened = self.run_cmd("c 1", uids[0])
        owner = load_run(self.plugin, uids[0])
        self.assertEqual(owner.node_type, "card_select")
        self.assertFalse(owner.node_data.get("can_skip"))
        self.assertTrue(owner.node_data.get("force_upgraded"))
        self.assertIn(ALL_CARDS[CardState(id="fireball", upgraded=True)].desc, opened)
        teammate = load_run(self.plugin, uids[1])
        self.assertEqual(teammate.node_type, "reward")

        refused = self.run_cmd("c 3", uids[0])
        self.assertIn("无法跳过", refused)
        owner = load_run(self.plugin, uids[0])
        self.assertEqual(owner.node_type, "card_select")

        self.run_cmd("c 1", uids[0])
        owner = load_run(self.plugin, uids[0])
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
        SessionContextScoper.create_session(run, "A1", "rest", uids, node_data={
            "coop_node_type": "rest",
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        })
        from game.models.coop_view import apply_view
        apply_view(run, uids[0])
        self.plugin.save_manager.save_save(uids[0], run)
        before = len(load_run(self.plugin, uids[0]).player.deck)

        opened = self.run_cmd("c 2", uids[0])
        owner = load_run(self.plugin, uids[0])
        self.assertEqual(owner.node_type, "card_select")
        self.assertTrue(owner.node_data.get("can_skip"))
        cards = owner.node_data.get("cards", [])
        self.assertTrue(cards)
        self.assertIn(ALL_CARDS[CardState(id=cards[0])].desc, opened)

        self.run_cmd("c 1", uids[0])
        owner = load_run(self.plugin, uids[0])
        self.assertEqual(owner.node_type, "grid_map")
        self.assertEqual(len(owner.player.deck), before + 1)
        teammate = load_run(self.plugin, uids[1])
        self.assertEqual(teammate.node_type, "rest")

    def test_coop_gem_flow_preserves_teammate_view(self):
        uids = ["gem_a", "gem_b"]
        run = self.start_coop(uids)
        SessionContextScoper.create_session(run, "A1", "shop", uids)
        self.plugin.engine.map_engine.explore_engine._init_shop_node(run)
        self.plugin.save_manager.save_save(uids[0], run)
        run = load_run(self.plugin, uids[0])
        items = list(run.node_data.get("items", []))
        gem_id = next(iter(GEM_CONFIG))
        explore = self.plugin.engine.map_engine.explore_engine
        explore.start_gem_insert_flow(run, gem_id, "shop", {"items": items})
        owner = load_run(self.plugin, uids[0])
        teammate = load_run(self.plugin, uids[1])
        self.assertEqual(owner.node_type, "gem_insert")
        self.assertEqual(teammate.node_type, "shop")
        self.assertTrue(teammate.node_data.get("items"))
        explore.gem_insert_cancel(owner)
        owner = load_run(self.plugin, uids[0])
        teammate = load_run(self.plugin, uids[1])
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
        SessionContextScoper.create_session(run, "A1", "treasure", uids, node_data={
            "coop_node_type": "treasure",
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        })
        from game.models.coop_view import apply_view
        apply_view(run, uids[0])
        self.plugin.save_manager.save_save(uids[0], run)
        owner = load_run(self.plugin, uids[0])
        self.plugin.engine.map_engine.choose_option(owner, 1)
        self.plugin.save_manager.save_save(uids[0], owner)
        owner = load_run(self.plugin, uids[0])
        teammate = load_run(self.plugin, uids[1])
        self.assertEqual(owner.node_type, "card_select")
        self.assertIn("fireball", owner.node_data.get("cards", []))
        self.assertEqual(teammate.node_type, "treasure")
        self.assertEqual(
            [item["type"] for item in teammate.node_data.get("items", [])],
            ["card_reward", "gem"],
        )
        self.plugin.engine.map_engine.choose_option(owner, 1)
        self.plugin.save_manager.save_save(uids[0], owner)
        owner = load_run(self.plugin, uids[0])
        self.assertEqual(owner.node_type, "treasure")
        self.plugin.engine.map_engine.choose_option(owner, 1)
        self.plugin.save_manager.save_save(uids[0], owner)
        owner = load_run(self.plugin, uids[0])
        teammate = load_run(self.plugin, uids[1])
        self.assertEqual(owner.node_type, "gem_insert")
        self.assertEqual(teammate.node_type, "treasure")
        self.assertEqual(
            [item["type"] for item in teammate.node_data.get("items", [])],
            ["card_reward", "gem"],
        )
        self.plugin.engine.map_engine.explore_engine.gem_insert_cancel(owner)
        self.plugin.save_manager.save_save(uids[0], owner)
        owner = load_run(self.plugin, uids[0])
        self.assertEqual(owner.node_type, "treasure")

    def test_coop_reward_completion_advances_once(self):
        uids = ["once_reward_leader", "once_reward_member"]
        run = self.start_coop(uids)
        _, run = move_to_room(self.plugin, uids[0], ("battle", "elite"), rally=True)
        floor_idx = floor_of(run).floor_index
        self.assertEqual(run.node_type, "battle")
        for enemy in run.enemies:
            enemy.hp = 0
        self.plugin.engine.battle_engine._handle_battle_win(run)
        reward = load_run(self.plugin, uids[0])
        self.assertEqual(reward.node_type, "reward")
        self.assertTrue(reward.node_data.get("items"))
        self.assertEqual(floor_of(reward).floor_index, floor_idx)

        waiting = self.run_cmd("c 取消", uids[0])
        self.assertIn("回到迷宫", waiting)
        leader = load_run(self.plugin, uids[0])
        self.assertEqual(leader.node_type, "grid_map")
        mid = load_run(self.plugin, uids[1])
        self.assertEqual(mid.node_type, "reward")
        self.assertTrue(mid.node_data.get("stage_ready", {}).get(uids[0]))
        self.assertFalse(mid.node_data.get("stage_ready", {}).get(uids[1]))
        self.assertEqual(floor_of(mid).floor_index, floor_idx)

        completed = self.run_cmd("c 取消", uids[1])
        self.assertIn("回到迷宫", completed)
        for uid in uids:
            advanced = load_run(self.plugin, uid)
            self.assertEqual(advanced.node_type, "grid_map")
            self.assertEqual(floor_of(advanced).floor_index, floor_idx)
        self.run_cmd("c 取消", uids[0])
        unchanged = load_run(self.plugin, uids[0])
        self.assertEqual(unchanged.node_type, "grid_map")
        self.assertEqual(floor_of(unchanged).floor_index, floor_idx)

    def test_coop_rest_completion_advances_once(self):
        uids = ["once_rest_leader", "once_rest_member"]
        run = self.start_coop(uids)
        floor_idx = floor_of(run).floor_index
        SessionContextScoper.create_session(run, "A1", "rest", uids)
        self.plugin.engine.map_engine.explore_engine._init_rest_node(run)
        self.plugin.save_manager.save_save(uids[0], run)
        rest = load_run(self.plugin, uids[0])
        self.assertEqual(rest.node_type, "rest")
        self.assertEqual(floor_of(rest).floor_index, floor_idx)

        waiting = self.run_cmd("c 4", uids[0])
        self.assertIn("救治", waiting)
        self.assertIn("回到迷宫", waiting)
        leader = load_run(self.plugin, uids[0])
        self.assertEqual(leader.node_type, "grid_map")
        mid = load_run(self.plugin, uids[1])
        self.assertEqual(mid.node_type, "rest")
        self.assertTrue(mid.node_data.get("stage_ready", {}).get(uids[0]))
        self.assertFalse(mid.node_data.get("stage_ready", {}).get(uids[1]))
        self.assertEqual(floor_of(mid).floor_index, floor_idx)

        completed = self.run_cmd("c 4", uids[1])
        self.assertIn("回到迷宫", completed)
        for uid in uids:
            advanced = load_run(self.plugin, uid)
            self.assertEqual(advanced.node_type, "grid_map")
            self.assertEqual(floor_of(advanced).floor_index, floor_idx)
        self.run_cmd("c 取消", uids[0])
        unchanged = load_run(self.plugin, uids[0])
        self.assertEqual(unchanged.node_type, "grid_map")
        self.assertEqual(floor_of(unchanged).floor_index, floor_idx)

    def test_coop_gem_completion_advances_once(self):
        uids = ["once_gem_leader", "once_gem_member"]
        run = self.start_coop(uids)
        floor_idx = floor_of(run).floor_index
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
        SessionContextScoper.create_session(run, "A1", "treasure", uids, node_data={
            "coop_node_type": "treasure",
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        })
        from game.models.coop_view import apply_view
        apply_view(run, uids[0])
        self.plugin.save_manager.save_save(uids[0], run)

        opened = self.run_cmd("c 1", uids[0])
        self.assertIn("强制镶嵌", opened)
        owner = load_run(self.plugin, uids[0])
        teammate = load_run(self.plugin, uids[1])
        self.assertEqual(owner.node_type, "gem_insert")
        self.assertEqual(teammate.node_type, "treasure")
        self.assertFalse(teammate.node_data["items"][0]["taken"])

        inserted = self.run_cmd("c 1", uids[0])
        self.assertIn("镶嵌成功", inserted)
        owner = load_run(self.plugin, uids[0])
        teammate = load_run(self.plugin, uids[1])
        self.assertEqual(owner.node_type, "treasure")
        self.assertTrue(owner.node_data["items"][0]["taken"])
        self.assertTrue(any(gem_id in card.gems for card in owner.player.deck))
        self.assertEqual(teammate.node_type, "treasure")
        self.assertFalse(teammate.node_data["items"][0]["taken"])
        self.assertFalse(any(gem_id in card.gems for card in teammate.player.deck))

        waiting = self.run_cmd("c 取消", uids[0])
        self.assertIn("回到迷宫", waiting)
        leader = load_run(self.plugin, uids[0])
        self.assertEqual(leader.node_type, "grid_map")
        mid = load_run(self.plugin, uids[1])
        self.assertEqual(mid.node_type, "treasure")
        self.assertEqual(floor_of(mid).floor_index, floor_idx)
        self.assertTrue(mid.node_data.get("stage_ready", {}).get(uids[0]))
        self.assertFalse(mid.node_data["items"][0]["taken"])

        opened_b = self.run_cmd("c 1", uids[1])
        self.assertIn("强制镶嵌", opened_b)
        member = load_run(self.plugin, uids[1])
        self.assertEqual(member.node_type, "gem_insert")
        member_inserted = self.run_cmd("c 1", uids[1])
        self.assertIn("镶嵌成功", member_inserted)
        member = load_run(self.plugin, uids[1])
        self.assertEqual(member.node_type, "treasure")
        self.assertTrue(member.node_data["items"][0]["taken"])
        self.assertTrue(any(gem_id in card.gems for card in member.player.deck))
        leader = load_run(self.plugin, uids[0])
        self.assertTrue(any(gem_id in card.gems for card in leader.player.deck))

        completed = self.run_cmd("c 取消", uids[1])
        self.assertIn("回到迷宫", completed)
        for uid in uids:
            advanced = load_run(self.plugin, uid)
            self.assertEqual(advanced.node_type, "grid_map")
            self.assertEqual(floor_of(advanced).floor_index, floor_idx)
        self.run_cmd("c 取消", uids[0])
        unchanged = load_run(self.plugin, uids[0])
        self.assertEqual(unchanged.node_type, "grid_map")
        self.assertEqual(floor_of(unchanged).floor_index, floor_idx)


if __name__ == "__main__":
    unittest.main()
