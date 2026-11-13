import asyncio
import unittest
from tempfile import TemporaryDirectory

from game.test.core.base import MyPlugin, DummyContext, run_command
from game.models.state import GameRun, PlayerState, CardState, EnemyState


class TestRogueCorpse(unittest.TestCase):
    def test_corpse_node_injected_and_claimed_globally(self):
        with TemporaryDirectory() as tmp:
            plugin = MyPlugin(DummyContext(), data_dir=tmp)
            user_id = "test_corpse_node_user"

            async def go():
                corpse_seed = GameRun(
                    user_id="dead_corpse_user",
                    node_type="battle",
                    player=PlayerState(
                        hp=0,
                        max_hp=50,
                        shield=0,
                        gold=100,
                        stage=3,
                        name="尸体测试",
                        deck=[CardState(id="magic_missile")],
                    ),
                )
                corpse = plugin.save_manager.corpses.create_from_run(
                    corpse_seed, "被【测试敌人】击败"
                )
                self.assertEqual(corpse["gp_pool"], 0)
                await run_command(plugin, ".rogue 开启", sender_id=user_id)
                await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
                run = plugin.save_manager.load_save(user_id)
                corpse_coords = [
                    c for c, r in run.floor_map.rooms.items()
                    if r.room_type == "corpse" and r.shared_payload.get("corpse_id") == corpse["id"]
                ]
                self.assertEqual(len(corpse_coords), 1)
                plugin.save_manager.corpses.claim(corpse["id"], "other_user")
                target = corpse_coords[0]
                run.floor_map.rooms[target].explored = True
                run.floor_map.revealed_coords.append(target)
                plugin.save_manager.save_save(user_id, run)
                tp_out = await run_command(plugin, f".rogue tp {target}", sender_id=user_id)
                self.assertIn("已空旷", tp_out)
                run = plugin.save_manager.load_save(user_id)
                self.assertEqual(run.floor_map.rooms[target].room_type, "empty")
            asyncio.run(go())


if __name__ == "__main__":
    unittest.main()
