import unittest
from game.test.core.base import *
from game.models.state import CardState

class TestRogueMinions(unittest.TestCase):
    def test_minion_reindexing(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=50,
            max_hp=100,
            shield=0,
            gold=100,
            stage=1,
            deck=["quick_strike"],
            hand=["quick_strike"],
            actions=5,
            bonus_actions=5,
            minions={
                "1": MinionState("mercenary", "雇佣兵 1", 20, 20, 4, 1, 0),
                "2": MinionState("mercenary", "雇佣兵 2", 10, 10, 4, 1, 0),
                "3": MinionState("mercenary", "雇佣兵 3", 30, 30, 4, 1, 0)
            }
        )
        run = GameRun(
            user_id="test_user_reindexing",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 30, 30, 0)]
        )
        engine._damage_target(run, "p2", 10, damage_type="true")
        self.assertEqual(len(player.minions), 2)
        self.assertEqual(player.minions["1"].name, "雇佣兵 1")
        self.assertEqual(player.minions["2"].name, "雇佣兵 3")
        self.assertNotIn("3", player.minions)
        engine.play_card(run, 1, None)
        self.assertEqual(len(player.minions), 2)
        self.assertEqual(player.minions["1"].name, "雇佣兵 1")
        self.assertEqual(player.minions["2"].name, "雇佣兵 3")
        self.assertNotIn("3", player.minions)

    def test_minion_reindexing_with_amulet(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        from game.models.state import AmuletState
        player = PlayerState(
            hp=50,
            max_hp=100,
            shield=0,
            gold=100,
            stage=1,
            deck=["quick_strike"],
            hand=["quick_strike"],
            actions=5,
            bonus_actions=5,
            minions={
                "1": MinionState("mercenary", "雇佣兵 1", 20, 20, 4, 1, 0),
                "2": MinionState("mercenary", "雇佣兵 2", 10, 10, 4, 1, 0),
                "4": MinionState("mercenary", "雇佣兵 4", 30, 30, 4, 1, 0)
            },
            amulets={
                "3": AmuletState("white_blade_banner", "白刃军团战旗", 4, "白刃军团战旗")
            }
        )
        run = GameRun(
            user_id="test_user_reindexing_amulet",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 30, 30, 0)]
        )
        engine._damage_target(run, "p2", 10, damage_type="true")
        self.assertEqual(len(player.minions), 2)
        self.assertEqual(player.minions["1"].name, "雇佣兵 1")
        self.assertEqual(player.minions["2"].name, "雇佣兵 4")
        self.assertNotIn("3", player.minions)
        self.assertNotIn("4", player.minions)
        self.assertIn("3", player.amulets)

    def test_minion_attack_digit_target(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        mgr = DummySaveManager()
        engine = BattleEngine(mgr)
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=100,
            stage=1,
            deck=[],
            hand=[],
            minions={
                "1": MinionState("mercenary", "雇佣兵", 10, 10, 4, 1, 0)
            }
        )
        enemy = EnemyState("哥布林", 20, 20, 0)
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        res = engine.card_player.minion_attack(run, "1", "1")
        self.assertEqual(enemy.hp, 16)
        self.assertIn("造成 4 点钝击伤害", res)

    def test_minion_all_attack_with_wish_power_buff(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        mgr = DummySaveManager()
        engine = BattleEngine(mgr)
        router = CLIRouter(mgr, engine)
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=100,
            stage=1,
            hand=[CardState("archmage_wish")],
            actions=5,
            bonus_actions=5,
            minions={
                "1": MinionState("mercenary", "雇佣兵", 10, 10, 4, 1, 0)
            }
        )
        enemy = EnemyState("训练假人", 999, 999, 0)
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        engine.play_card(run, 1, None)
        self.assertIn("wish_power", [b.id for b in player.buffs])
        res, term, success = router._execute_sub_action("test_user", run, ["随从", "all", "攻击", "e1"])
        self.assertEqual(enemy.hp, 995)
        self.assertIn("造成 4 点钝击伤害", res)
        self.assertNotIn("❌", res)
        self.assertFalse(term)

    def test_minion_defeat_non_summon_and_win(self):
        class DummySaveManager:
            def __init__(self):
                self.saved_run = None
                self.stats = UserStats()
            def save_save(self, user_id, run):
                self.saved_run = run
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return self.stats
            def save_stats(self, user_id, stats):
                self.stats = stats
        mgr = DummySaveManager()
        engine = BattleEngine(mgr)
        router = CLIRouter(mgr, engine)
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=100,
            stage=1,
            deck=[],
            hand=[],
            minions={
                "1": MinionState("mercenary", "雇佣兵", 10, 10, 4, 1, 0)
            }
        )
        enemy_non_summon = EnemyState("Boss", 4, 4, 0, is_summon=False)
        enemy_summon = EnemyState("爪牙", 10, 10, 0, is_summon=True)
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            player=player,
            enemies=[enemy_non_summon, enemy_summon]
        )
        res, term, success = router._execute_sub_action("test_user", run, ["随从", "1", "攻击", "e1"])
        self.assertEqual(enemy_non_summon.hp, 0)
        self.assertTrue(term)
        self.assertEqual(run.node_type, "reward")
        self.assertIn("战斗胜利！你击败了敌方所有单位。", res)

    def test_instant_summon_uses_configured_sources(self):
        from game.models.state import CardState
        from game.models.events import CardPlayedCountEvent
        from game.data.keyword_data import KEYWORD_CONFIG

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
            gold=100,
            stage=1,
            draw_pile=[CardState("elf_archer_xiaomei")],
            discard_pile=[CardState("elf_archer_xiaomei")],
            exhaust_pile=[CardState("elf_archer_xiaomei")],
            actions=5,
            bonus_actions=5
        )
        run = GameRun(
            user_id="test_instant_summon",
            node_type="battle",
            player=player,
            enemies=[EnemyState("训练假人", 999, 999, 0)],
            node_data={"cards_played_this_turn": 4}
        )
        engine.event_bus.dispatch(CardPlayedCountEvent(run, 4))
        self.assertEqual(len(player.minions), 2)
        self.assertEqual(player.draw_pile, [])
        self.assertEqual(player.discard_pile, [])
        self.assertEqual(len(player.exhaust_pile), 1)
        logs = "\n".join(run.node_data.get("battle_logs", []))
        self.assertIn("抽牌堆", logs)
        self.assertIn("弃牌堆", logs)
        self.assertNotIn("消耗堆", logs)
        for pile_name in ("抽牌堆", "弃牌堆", "手牌", "消耗堆"):
            self.assertIn(pile_name, KEYWORD_CONFIG["instant_summon"]["desc"])

    def test_instant_summon_sources_are_card_specific(self):
        from game.models.state import Card, CardState
        from game.models.events import CardPlayedCountEvent
        from game.entities.cards.base import ALL_CARDS

        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass

        test_id = "test_instant_summon_variant"
        card = Card(test_id, "测试瞬念随从", "neutral", "minion", 0, 0)
        card.minion_hp = 5
        card.minion_atk = 1
        card.instant_summon = True
        card.instant_summon_thresholds = (4,)
        card.instant_summon_piles = ("hand", "exhaust")
        ALL_CARDS[test_id] = card
        try:
            engine = BattleEngine(DummySaveManager())
            player = PlayerState(
                hp=50,
                max_hp=50,
                shield=0,
                gold=100,
                stage=1,
                hand=[CardState(test_id)],
                exhaust_pile=[CardState(test_id)],
                draw_pile=[CardState(test_id)],
                discard_pile=[CardState(test_id)],
                actions=5,
                bonus_actions=5
            )
            run = GameRun(
                user_id="test_instant_summon_variant",
                node_type="battle",
                player=player,
                enemies=[EnemyState("训练假人", 999, 999, 0)],
                node_data={"cards_played_this_turn": 4}
            )
            engine.event_bus.dispatch(CardPlayedCountEvent(run, 4))
            self.assertEqual(len(player.minions), 2)
            self.assertEqual(player.hand, [])
            self.assertEqual(player.exhaust_pile, [])
            self.assertEqual(len(player.draw_pile), 1)
            self.assertEqual(len(player.discard_pile), 1)
        finally:
            ALL_CARDS.pop(test_id, None)
