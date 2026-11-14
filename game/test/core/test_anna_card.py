import asyncio
import random
import tempfile
import unittest

from game.models.state import CardState, EnemyState, GameRun, MinionState, PlayerState
from game.test.core.base import CorePlugin, run_command


class TestAnnaCard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.random_state = random.getstate()
        random.seed(1)
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, command, uid):
        return asyncio.run(run_command(self.plugin, command, uid))

    def build_battle(self, uid, hand, draw_pile, discard_pile, deck=None, minions=None, hp=1000):
        p = PlayerState(
            hp=hp, max_hp=hp, shield=0, gold=0, stage=1,
            deck=deck or [], hand=hand, draw_pile=draw_pile, discard_pile=discard_pile,
            exhaust_pile=[], graveyard=[], actions=1, bonus_actions=1,
            minions=minions or {},
        )
        run = GameRun(
            user_id=uid, node_type="battle", player=p,
            enemies=[EnemyState("训练假人", 500, 500, 0)], node_data={},
        )
        self.plugin.save_manager.save_save(uid, run)
        return run

    def test_checkin_unlocks_anne(self):
        uid = "anna_checkin_user"
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        self.run_cmd("checkin", uid)
        res1 = self.run_cmd("checkin 2", uid)
        self.assertIn("马纳历亚女王‧安", res1)
        stats = self.plugin.save_manager.load_stats(uid)
        stats.last_checkin_date = "2000-01-01"
        self.plugin.save_manager.save_stats(uid, stats)
        self.run_cmd("checkin", uid)
        res2 = self.run_cmd("checkin 2", uid)
        self.assertIn("解锁", res2)
        stats = self.plugin.save_manager.load_stats(uid)
        self.assertIn("manaeria_queen_anne", stats.unlocked_new_cards)

    def test_fanfare_vanishes_without_exhaust_and_summons_spirit(self):
        uid = "anna_fanfare_user"
        piles = [CardState(id="fire_bolt"), CardState(id="quick_strike"), CardState(id="dagger_throw"), CardState(id="shield")]
        deck = [CardState(id="fire_bolt"), CardState(id="quick_strike"), CardState(id="dagger_throw"), CardState(id="shield"), CardState(id="manaeria_queen_anne")]
        self.build_battle(uid, [CardState(id="manaeria_queen_anne")], piles[:2], piles[2:], deck=deck)
        res = self.run_cmd("p 1", uid)
        self.assertIn("消失", res)
        after = self.plugin.save_manager.load_save(uid)
        p = after.player
        self.assertEqual(len(p.draw_pile) + len(p.discard_pile), 2)
        self.assertEqual(p.exhaust_pile, [])
        self.assertEqual([c.id for c in p.deck], [c.id for c in deck])
        self.assertIn("excellent_crit", [c.id for c in p.hand])
        spirit = next((m for m in p.minions.values() if m.id == "anna_great_spirit"), None)
        self.assertIsNotNone(spirit)
        self.assertEqual(spirit.hp, 50)
        self.assertEqual(spirit.atk, 20)
        self.assertEqual(spirit.attack_actions, 3)
        self.assertIn("ward", [b.id for b in spirit.buffs])
        self.assertIn("安的巨大英灵", res)

    def test_upgraded_threshold_is_seven(self):
        uid = "anna_upgraded_user"
        piles = [CardState(id=f"fire_bolt_{i}") for i in range(6)]
        self.build_battle(uid, [CardState(id="manaeria_queen_anne", upgraded=True)], piles[:3], piles[3:], deck=list(piles))
        self.run_cmd("p 1", uid)
        after = self.plugin.save_manager.load_save(uid)
        self.assertIn("anna_great_spirit", [m.id for m in after.player.minions.values()])

    def test_spirit_dies_on_player_turn_start(self):
        uid = "anna_spirit_death_user"
        minions = {"1": MinionState("anna_great_spirit", "安的巨大英灵", 50, 50, 20, 1, 0)}
        piles = [CardState(id="fire_bolt")] * 10
        self.build_battle(uid, [CardState(id="excellent_crit")], piles[:5], piles[5:], minions=minions)
        self.run_cmd("e", uid)
        after = self.plugin.save_manager.load_save(uid)
        self.assertNotIn("anna_great_spirit", [m.id for m in after.player.minions.values()])

    def test_skill_one_vanishes_and_distributes_fire_damage(self):
        uid = "anna_skill_user"
        minions = {"1": MinionState("manaeria_queen_anne", "马纳历亚女王‧安", 21, 21, 6, 1, 0)}
        piles = [CardState(id=f"fire_bolt_{i}") for i in range(5)]
        self.build_battle(uid, [], piles[:3], piles[3:], minions=minions)
        res = self.run_cmd("m 1 s 1", uid)
        self.assertIn("火焰", res)
        after = self.plugin.save_manager.load_save(uid)
        self.assertEqual(len(after.player.draw_pile) + len(after.player.discard_pile), 4)
        self.assertEqual(after.player.exhaust_pile, [])
        self.assertEqual(after.enemies[0].hp, 480)

    def test_minion_attack_uses_fire_damage(self):
        uid = "anna_fire_attack_user"
        minions = {"1": MinionState("manaeria_queen_anne", "马纳历亚女王‧安", 21, 21, 6, 1, 0)}
        self.build_battle(uid, [], [], [], minions=minions)
        res = self.run_cmd("m 1 a e1", uid)
        self.assertIn("火焰", res)
        after = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after.enemies[0].hp, 494)

    def test_excellent_crit_tiers_and_both_targets(self):
        cases = [
            (0, 200),
            (2, 80),
            (4, 40),
            (7, 20),
            (10, 10),
        ]
        for idx, (pile_count, expected) in enumerate(cases):
            with self.subTest(pile_count=pile_count):
                uid = f"anna_crit_user_{idx}"
                piles = [CardState(id=f"fire_bolt_{i}") for i in range(pile_count)]
                self.build_battle(uid, [CardState(id="excellent_crit")], piles, [], deck=list(piles))
                res = self.run_cmd("p 1 p0", uid)
                after = self.plugin.save_manager.load_save(uid)
                self.assertEqual(after.player.hp, 1000 - expected * 2)
                self.assertEqual(after.enemies[0].hp, 500 - expected * 2)
                self.assertIn(str(expected), res)

    def test_excellent_crit_requires_ally_target(self):
        uid = "anna_crit_target_user"
        piles = [CardState(id="fire_bolt")] * 10
        self.build_battle(uid, [CardState(id="excellent_crit")], piles, [], deck=list(piles))
        res = self.run_cmd("p 1", uid)
        self.assertIn("己方目标", res)

    def test_disappear_keyword_is_queryable(self):
        uid = "anna_keyword_user"
        self.build_battle(uid, [], [], [])
        res = self.run_cmd("i 消失", uid)
        self.assertIn("消耗堆", res)
