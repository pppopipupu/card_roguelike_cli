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
                await run_command(plugin, ".rogue 开启", sender_id=user_id)
                await run_command(plugin, ".rogue 选择 1", sender_id=user_id)
                run = plugin.save_manager.load_save(user_id)
                dead = GameRun(
                    user_id="dead_corpse_user",
                    node_type="battle",
                    player=PlayerState(
                        hp=0,
                        max_hp=50,
                        shield=0,
                        gold=100,
                        stage=run.player.stage,
                        name="尸体测试",
                        deck=[CardState(id="magic_missile")],
                    ),
                )
                corpse = plugin.save_manager.corpses.create_from_run(
                    dead, "被【测试敌人】击败"
                )
                self.assertEqual(corpse["gp_pool"], 0)
                output = await run_command(plugin, ".rogue 状态", sender_id=user_id)
                self.assertIn("尸体：尸体测试", output)
                run = plugin.save_manager.load_save(user_id)
                corpse_options = [
                    option for option in run.node_data.get("options", [])
                    if option.get("node_type") == "corpse"
                ]
                self.assertEqual(len(corpse_options), 1)
                self.assertEqual(corpse_options[0].get("corpse_id"), corpse["id"])
                plugin.save_manager.corpses.claim(corpse["id"], "other_user")
                await run_command(plugin, ".rogue 状态", sender_id=user_id)
                run = plugin.save_manager.load_save(user_id)
                self.assertFalse(
                    any(
                        option.get("node_type") == "corpse"
                        for option in run.node_data.get("options", [])
                    )
                )

            asyncio.run(go())

    def test_corpse_gp_pool_starts_at_stage_five(self):
        with TemporaryDirectory() as tmp:
            plugin = MyPlugin(DummyContext(), data_dir=tmp)
            dead = GameRun(
                user_id="dead_corpse_gp_user",
                node_type="battle",
                player=PlayerState(
                    hp=0,
                    max_hp=50,
                    shield=0,
                    gold=100,
                    stage=5,
                    name="金币尸体",
                    deck=[CardState(id="magic_missile")],
                ),
            )
            corpse = plugin.save_manager.corpses.create_from_run(
                dead, "被【测试敌人】击败"
            )
            self.assertEqual(corpse["gp_pool"], 1000)


if __name__ == "__main__":
    unittest.main()
