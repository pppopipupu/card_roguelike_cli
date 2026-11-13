import unittest

from game.core.battle.engine import BattleEngine
from game.models.state import BuffState, CardState, EnemyState, GameRun, PlayerState


class TestSpecialActionGemAffixes(unittest.TestCase):

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
