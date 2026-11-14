import asyncio
import random
import tempfile
import unittest

from game.data.millika_card_config import MILLIKA_TURN_FLAG_KEY
from game.models.state import CardState, EnemyState, GameRun, MinionState, PlayerState
from game.test.core.base import CorePlugin, run_command

MILLIKA_ID = "holy_celestial_millika"
ANNE_ID = "manaeria_queen_anne"


class TestMillikaCard(unittest.TestCase):
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

    def build_battle(self, uid, hand, draw_pile, discard_pile, deck=None, minions=None, hp=1000, node_data=None):
        p = PlayerState(
            hp=hp, max_hp=hp, shield=0, gold=0, stage=1,
            deck=deck or [], hand=hand, draw_pile=draw_pile, discard_pile=discard_pile,
            exhaust_pile=[], graveyard=[], actions=1, bonus_actions=1,
            minions=minions or {},
        )
        run = GameRun(
            user_id=uid, node_type="battle", player=p,
            enemies=[EnemyState("训练假人", 500, 500, 0)],
            node_data=node_data or {},
        )
        self.plugin.save_manager.save_save(uid, run)
        return run

    def pile_total(self, run):
        return len(run.player.draw_pile) + len(run.player.discard_pile)

    def test_checkin_unlocks_millika(self):
        uid = "millika_checkin_user"
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        self.run_cmd("checkin", uid)
        res1 = self.run_cmd("checkin 3", uid)
        self.assertIn("神圣天体‧弥莉卡", res1)
        stats = self.plugin.save_manager.load_stats(uid)
        stats.last_checkin_date = "2000-01-01"
        self.plugin.save_manager.save_stats(uid, stats)
        self.run_cmd("checkin", uid)
        res2 = self.run_cmd("checkin 3", uid)
        self.assertIn("解锁", res2)
        stats = self.plugin.save_manager.load_stats(uid)
        self.assertIn(MILLIKA_ID, stats.unlocked_new_cards)

    def test_fanfare_vanish_branch_and_replenish(self):
        uid = "millika_vanish_user"
        piles = [CardState(id=MILLIKA_ID) for _ in range(11)]
        self.build_battle(uid, [CardState(id=MILLIKA_ID)], piles, [], deck=list(piles))
        res = self.run_cmd("p 1", uid)
        self.assertIn("加入手牌", res)
        self.assertIn("入场曲", res)
        after = self.plugin.save_manager.load_save(uid)
        p = after.player
        self.assertEqual([c.id for c in p.hand], [MILLIKA_ID, MILLIKA_ID])
        self.assertEqual(self.pile_total(after), 9)
        self.assertEqual(p.exhaust_pile, [])
        millika = next(m for m in p.minions.values() if m.id == MILLIKA_ID)
        self.assertEqual(millika.hp, 20)
        self.assertEqual(millika.atk, 5)
        self.assertIn("ward", [b.id for b in millika.buffs])

    def test_fanfare_buff_branch(self):
        uid = "millika_buff_user"
        piles = [CardState(id=f"fire_bolt_{i}") for i in range(5)]
        self.build_battle(uid, [CardState(id=MILLIKA_ID)], piles, [], deck=list(piles))
        res = self.run_cmd("p 1", uid)
        self.assertIn("入场曲", res)
        after = self.plugin.save_manager.load_save(uid)
        p = after.player
        self.assertEqual(self.pile_total(after), 5)
        self.assertEqual(p.hand, [])
        millika = next(m for m in p.minions.values() if m.id == MILLIKA_ID)
        self.assertEqual(millika.hp, 40)
        self.assertEqual(millika.max_hp, 40)
        self.assertEqual(millika.atk, 15)
        self.assertIn("ward", [b.id for b in millika.buffs])

    def test_replenish_from_anna_skill(self):
        uid = "millika_replenish_user"
        minions = {"1": MinionState(ANNE_ID, "马纳历亚女王‧安", 21, 21, 6, 1, 0)}
        self.build_battle(uid, [], [CardState(id=MILLIKA_ID)], [], minions=minions)
        res = self.run_cmd("m 1 s 1", uid)
        self.assertIn("加入手牌", res)
        after = self.plugin.save_manager.load_save(uid)
        self.assertEqual([c.id for c in after.player.hand], [MILLIKA_ID])
        self.assertEqual(self.pile_total(after), 0)
        self.assertEqual(after.enemies[0].hp, 480)

    def test_no_replenish_for_other_vanished_cards(self):
        uid = "millika_other_vanish_user"
        minions = {"1": MinionState(ANNE_ID, "马纳历亚女王‧安", 21, 21, 6, 1, 0)}
        self.build_battle(uid, [], [CardState(id="fire_bolt")], [], minions=minions)
        res = self.run_cmd("m 1 s 1", uid)
        self.assertNotIn("加入手牌", res)
        after = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after.player.hand, [])

    def test_no_replenish_outside_own_turn(self):
        uid = "millika_enemy_turn_user"
        minions = {"1": MinionState(ANNE_ID, "马纳历亚女王‧安", 21, 21, 6, 1, 0)}
        self.build_battle(uid, [], [CardState(id=MILLIKA_ID)], [], minions=minions, node_data={MILLIKA_TURN_FLAG_KEY: {}})
        res = self.run_cmd("m 1 s 1", uid)
        self.assertNotIn("加入手牌", res)
        after = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after.player.hand, [])

    def test_minion_attack_uses_radiant_damage(self):
        uid = "millika_radiant_user"
        minions = {"1": MinionState(MILLIKA_ID, "神圣天体‧弥莉卡", 20, 20, 5, 1, 0)}
        self.build_battle(uid, [], [], [], minions=minions)
        res = self.run_cmd("m 1 a e1", uid)
        self.assertIn("光耀", res)
        after = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after.enemies[0].hp, 495)

    def test_query_card_is_available(self):
        uid = "millika_query_user"
        self.build_battle(uid, [], [], [])
        res = self.run_cmd("i 神圣天体‧弥莉卡", uid)
        self.assertIn("神圣天体‧弥莉卡", res)
        self.assertIn("稀有", res)
