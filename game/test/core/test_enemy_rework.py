import unittest
from unittest.mock import patch

from game.test.core.base import *
from game.models.state import EnemyIntentState
from game.entities.enemies.base import ALL_ENEMIES, EnemyTemplate


class AstralSpeedProbeTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy):
        main = [
            EnemyIntentState(type="attack", val=1, desc="probe-a", cost_a=1, cost_ba=0)
            for _ in range(enemy.actions)
        ]
        bonus = [
            EnemyIntentState(type="defend", val=1, desc="probe-ba", cost_a=0, cost_ba=1)
            for _ in range(enemy.bonus_actions)
        ]
        return main + bonus


class DummySaveManager:
    def __init__(self):
        self.stats = UserStats()

    def save_save(self, user_id, run):
        return True

    def delete_save(self, user_id):
        return True

    def load_stats(self, user_id):
        return self.stats

    def save_stats(self, user_id, stats):
        self.stats = stats
        return True

    def settle_game_and_delete(self, user_id, run, is_victory=True):
        return ""


class TestEnemyRework(unittest.TestCase):
    def _build(self, player, enemy, node_data=None):
        engine = BattleEngine(DummySaveManager())
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            player=player,
            enemies=[enemy],
            node_data=dict(node_data or {})
        )
        engine.current_run = run
        return engine, run

    def test_sync_enemy_intents_keeps_four_intents(self):
        engine = BattleEngine(DummySaveManager())
        enemy = EnemyState(
            name="四槽测试",
            hp=60,
            max_hp=60,
            shield=0,
            actions=2,
            bonus_actions=2,
            max_actions=2,
            max_bonus_actions=2,
            intents=[
                EnemyIntentState(type="attack", val=5, desc="slot-a1", cost_a=1, cost_ba=0),
                EnemyIntentState(type="attack", val=6, desc="slot-a2", cost_a=1, cost_ba=0),
                EnemyIntentState(type="defend", val=3, desc="slot-ba1", cost_a=0, cost_ba=1),
                EnemyIntentState(type="defend", val=4, desc="slot-ba2", cost_a=0, cost_ba=1),
            ],
        )
        engine._sync_enemy_intents(enemy)
        self.assertEqual(len(enemy.intents), 4)
        self.assertEqual(enemy.intent_a2_desc, "slot-a2")
        self.assertEqual(enemy.intent_a2_val, 6)
        self.assertEqual(enemy.intent_ba2_desc, "slot-ba2")
        self.assertEqual(enemy.intent_ba2_val, 4)

    def test_astral_speed_consumed_when_rolling_intents(self):
        player = PlayerState(hp=80, max_hp=80, shield=0, gold=0, stage=1)
        enemy = EnemyState(
            name="astral_speed_probe",
            hp=30,
            max_hp=30,
            shield=0,
            actions=1,
            bonus_actions=0,
            max_actions=1,
            max_bonus_actions=0,
        )
        enemy.buffs.append(BuffState(id="astral_speed", name="astral_speed", stacks=1))
        engine, run = self._build(player, enemy)
        ALL_ENEMIES["astral_speed_probe"] = AstralSpeedProbeTemplate("astral_speed_probe")
        try:
            with patch("random.choice", side_effect=lambda seq: seq[0]):
                engine._roll_enemy_intent(run)
        finally:
            ALL_ENEMIES.pop("astral_speed_probe", None)
        self.assertFalse(any(b.id == "astral_speed" for b in enemy.buffs))
        self.assertEqual(enemy.actions, 2)
        self.assertEqual(len(enemy.intents), enemy.max_actions + 1 + enemy.max_bonus_actions)

    def test_defect_robot_turn_three_rolls_four_intents(self):
        player = PlayerState(hp=120, max_hp=120, shield=0, gold=0, stage=9)
        enemy = EnemyState(
            name="故障机器人",
            hp=70,
            max_hp=70,
            shield=0,
            actions=2,
            bonus_actions=2,
            max_actions=2,
            max_bonus_actions=2,
        )
        engine, run = self._build(player, enemy, {"defect_turns": {"故障机器人": 3}})
        with patch("random.choice", side_effect=lambda seq: seq[0]):
            engine._roll_enemy_intent(run)
        self.assertEqual(len(enemy.intents), 4)
        self.assertEqual(len([it for it in enemy.intents if it.cost_ba == 1]), 2)
        self.assertEqual(len([it for it in enemy.intents if it.cost_a == 1]), 2)

    def test_banish_slash_purges_mist_cthulhu(self):
        player = PlayerState(
            hp=60,
            max_hp=60,
            shield=0,
            gold=0,
            stage=25,
            hand=["neutral_banish_slash"],
            actions=2,
            bonus_actions=1,
        )
        enemy = EnemyState(
            name="【迷雾】伟大的克苏鲁",
            hp=1,
            max_hp=1,
            shield=0,
            actions=1,
            bonus_actions=0,
            max_actions=1,
            max_bonus_actions=0,
        )
        engine, run = self._build(player, enemy)
        engine._add_buff_to(enemy, "cthulhu_mist_immune", "cthulhu_mist_immune", "cthulhu_mist_immune", 1)
        engine.card_player.play_card(run, 1, "e1")
        self.assertLessEqual(enemy.hp, 0)

    def test_banish_slash_never_banishes_boss(self):
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=0,
            stage=12,
            hand=["neutral_banish_slash"],
            actions=2,
            bonus_actions=1,
        )
        enemy = EnemyState(
            name="远古红龙",
            hp=145,
            max_hp=145,
            shield=0,
            actions=1,
            bonus_actions=2,
            max_actions=1,
            max_bonus_actions=2,
        )
        engine, run = self._build(player, enemy)
        with patch("random.random", return_value=0.0):
            engine.card_player.play_card(run, 1, "e1")
        self.assertGreater(enemy.hp, 0)
        self.assertLess(enemy.hp, enemy.max_hp)
        self.assertIn(enemy, run.enemies)

    def test_shroud_time_warp_forces_turn_end(self):
        player = PlayerState(
            hp=200,
            max_hp=200,
            shield=0,
            gold=0,
            stage=30,
            hand=["magic_missile"] * 12,
            actions=12,
            bonus_actions=0,
        )
        enemy = EnemyState(
            name="虚境之影",
            hp=220,
            max_hp=220,
            shield=0,
            actions=2,
            bonus_actions=1,
            max_actions=2,
            max_bonus_actions=1,
        )
        enemy.buffs.append(BuffState(id="shroud_time_warp", name="shroud_time_warp", stacks=0))
        engine, run = self._build(player, enemy)
        with patch("random.choice", side_effect=lambda seq: seq[0]), patch("random.shuffle", lambda seq: None):
            for _ in range(12):
                engine.card_player.play_card(run, 1, "e1")
        self.assertFalse(run.node_data.get("force_end_turn", False))
        self.assertEqual(run.node_data.get("turn_count"), 2)
        self.assertEqual(player.actions, 2)
        self.assertEqual(player.bonus_actions, 1)

    def test_baguwen_restriction_punishes_wrong_first_card(self):
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=0,
            stage=30,
            hand=["fire_bolt", "magic_missile"],
            actions=2,
            bonus_actions=1,
        )
        enemy = EnemyState(
            name="DeepSeek V4.1 Flash",
            hp=90,
            max_hp=90,
            shield=0,
            actions=1,
            bonus_actions=0,
            max_actions=1,
            max_bonus_actions=0,
        )
        engine, run = self._build(player, enemy)
        engine._add_buff_to(player, "baguwen_restriction", "baguwen_restriction", "baguwen_restriction", 1)
        with patch("random.choice", side_effect=lambda seq: seq[0]):
            engine.card_player._begin_player_phase(run, player)
        required = run.node_data.get(run.turn_key("baguwen_required_card", player))
        self.assertIsInstance(required, dict)
        self.assertTrue(required.get("id"))
        self.assertFalse(run.node_data.get(run.turn_key("baguwen_checked", player), True))
        play_idx = None
        for idx, card_state in enumerate(player.hand):
            if card_state.id != required["id"] or card_state.upgraded != required.get("upgraded", False):
                play_idx = idx + 1
                break
        self.assertIsNotNone(play_idx)
        before_hp = player.hp
        engine.card_player.play_card(run, play_idx, "e1")
        self.assertEqual(before_hp - player.hp, 10)
        self.assertTrue(run.node_data.get(run.turn_key("baguwen_checked", player), False))


if __name__ == "__main__":
    unittest.main()
