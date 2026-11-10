import asyncio
import copy
import random
import re
import tempfile
import unittest

from game.test.core.base import CorePlugin, run_command
from game.core.battle_engine import BattleEngine
from game.data.gem_data import GEM_CONFIG
from game.models.coop_view import apply_view
from game.models.state import (
    BuffState,
    CardState,
    EnemyState,
    GameRun,
    PlayerState,
    public_player_id,
)


class TestRefactorRegressions(unittest.TestCase):
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
        self.run_cmd("friend name 队长", leader)
        for index, uid in enumerate(others, 1):
            self.run_cmd(f"friend name 队员{index}", uid)
            self.run_cmd(f"friend add {public_player_id(uid)}", leader)
            self.run_cmd(f"friend accept {public_player_id(leader)}", uid)

    def create_team(self, leader, others):
        result = self.run_cmd("team create", leader)
        self.assertIn("已创建队伍", result)
        lobby_id = re.search(r"队伍 ([A-Z0-9]{6})", result).group(1)
        for uid in others:
            invited = self.run_cmd(f"friend invite {public_player_id(uid)}", leader)
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
        return run

    def test_coop_treasure_card_then_gem_keeps_views_isolated(self):
        uids = ["refactor_treasure_a", "refactor_treasure_b"]
        run = self.start_coop(uids)
        stage = run.players[uids[0]].stage
        gem_id = next(iter(GEM_CONFIG))
        base_items = [
            {"type": "card_reward", "cards": ["neutral_omega"], "taken": False, "force": False},
            {"type": "gem", "gem_id": gem_id, "taken": False},
        ]
        views = {
            uid: {"node_type": "treasure", "data": {"state": "opened", "items": copy.deepcopy(base_items)}}
            for uid in uids
        }
        run.node_type = "treasure"
        run.node_data = {
            "coop_node_type": "treasure",
            "player_views": views,
            "stage_ready": {uid: False for uid in uids},
        }
        apply_view(run, uids[0])
        self.plugin.save_manager.save_coop_save(uids[0], run)

        select = self.run_cmd("c 1", uids[0])
        self.assertIn("三选一", select)
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "card_select")
        self.assertIn("neutral_omega", owner.node_data.get("cards", []))
        self.assertEqual(teammate.node_type, "treasure")
        self.assertEqual(
            [item["type"] for item in teammate.node_data.get("items", [])],
            ["card_reward", "gem"],
        )
        self.assertFalse(any(item.get("taken") for item in teammate.node_data.get("items", [])))

        self.run_cmd("c 1", uids[0])
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "treasure")
        self.assertIn("neutral_omega", {card.id for card in owner.player.deck})
        self.assertNotIn("neutral_omega", {card.id for card in teammate.player.deck})
        self.assertFalse(any(item.get("taken") for item in teammate.node_data.get("items", [])))

        gem_open = self.run_cmd("c 1", uids[0])
        self.assertIn("强制镶嵌", gem_open)
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "gem_insert")
        self.assertEqual(teammate.node_type, "treasure")
        self.assertEqual(
            [item["type"] for item in teammate.node_data.get("items", [])],
            ["card_reward", "gem"],
        )
        self.assertFalse(any(item.get("taken") for item in teammate.node_data.get("items", [])))

        inserted = self.run_cmd("c 1", uids[0])
        self.assertIn("镶嵌成功", inserted)
        owner = self.plugin.save_manager.load_save(uids[0])
        teammate = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(owner.node_type, "treasure")
        owner_items = owner.node_data.get("items", [])
        self.assertTrue(owner_items[1]["taken"])
        self.assertTrue(any(gem_id in card.gems for card in owner.player.deck))
        self.assertEqual(teammate.node_type, "treasure")
        teammate_items = teammate.node_data.get("items", [])
        self.assertFalse(teammate_items[1]["taken"])
        self.assertFalse(any(gem_id in card.gems for card in teammate.player.deck))

        waiting = self.run_cmd("c 取消", uids[0])
        self.assertIn("等待队友", waiting)
        waiting_view = self.plugin.save_manager.load_save(uids[1])
        self.assertEqual(waiting_view.node_type, "treasure")
        self.assertEqual(waiting_view.players[uids[0]].stage, stage)
        self.assertTrue(waiting_view.node_data.get("stage_ready", {}).get(uids[0]))
        waiting_items = waiting_view.node_data.get("items", [])
        self.assertEqual([item["type"] for item in waiting_items], ["card_reward", "gem"])
        self.assertFalse(any(item.get("taken") for item in waiting_items))

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

    def test_special_action_dispatches_events_and_keeps_gem_affixes(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass

            def delete_save(self, user_id):
                pass

        engine = BattleEngine(DummySaveManager())
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=0,
            stage=1,
            deck=[],
            hand=[CardState("fireball", gems=["gem_return_5", "gem_copy_1"])],
            draw_pile=[],
            discard_pile=[],
            exhaust_pile=[],
            actions=10,
            bonus_actions=10,
            relics=["djinn_shard"],
            buffs=[BuffState(id="magic_network", name="魔网天成", stacks=1, desc="")],
        )
        enemy = EnemyState("靶子", 100, 100, 0)
        run = GameRun(
            user_id="special_action_regression",
            node_type="battle",
            player=player,
            enemies=[enemy],
            node_data={"cards_played_this_turn": 0},
        )

        result = engine.play_special_action(run, 1, "e1")
        self.assertNotIn("❌", result)
        self.assertIn("特殊行动", result)
        self.assertIn("返回", result)
        self.assertIn("复制", result)
        self.assertEqual(enemy.hp, 92)
        self.assertEqual(player.shield, 3)
        self.assertEqual(run.node_data.get("cards_played_this_turn"), 1)
        self.assertTrue(run.node_data.get("djinn_shard_fired"))
        self.assertEqual(len(player.hand), 2)
        self.assertTrue(all(isinstance(card, CardState) for card in player.hand))

        returned = [card for card in player.hand if card.return_left == 4]
        self.assertEqual(len(returned), 1)
        self.assertEqual(returned[0].id, "fireball")
        self.assertEqual(returned[0].gems, ["gem_return_5", "gem_copy_1"])
        copied = [card for card in player.hand if card.no_copy]
        self.assertEqual(len(copied), 1)
        self.assertEqual(copied[0].id, "fireball")
        self.assertNotIn("gem_copy_1", copied[0].gems)
        self.assertEqual(player.discard_pile, [])
        self.assertEqual(player.exhaust_pile, [])


if __name__ == "__main__":
    unittest.main()
