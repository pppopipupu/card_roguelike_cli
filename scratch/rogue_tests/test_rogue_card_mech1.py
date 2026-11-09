import unittest
from scratch.rogue_tests.base import *

class TestRogueCardMech1(unittest.TestCase):
    def test_card_retain_and_agile_bypass(self):
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=2,
            deck=["first_aid", "dagger_throw", "agile_strike"],
            draw_pile=["first_aid"] * 8,
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            hand=["first_aid", "dagger_throw", "agile_strike"],
            actions=2,
            bonus_actions=1
        )
        enemy = EnemyState(
            name="测试敌人",
            hp=20,
            max_hp=20,
            shield=0
        )
        run = GameRun(
            user_id="test_user_retain",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine.battle_engine
        engine.end_turn(run)
        self.assertIn("first_aid", player.hand)
        self.assertNotIn("dagger_throw", player.hand)
        self.assertNotIn("agile_strike", player.hand)
        self.assertIn("dagger_throw", player.discard_pile)
        self.assertIn("agile_strike", player.discard_pile)
        self.assertEqual(enemy.hp, 20)

    def test_tactical_focus_effect(self):
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=2,
            deck=["tactical_focus"],
            draw_pile=["dagger_throw", "first_aid", "lucky_coin", "thorns_necklace", "iron_will", "quick_strike", "arcane_spark"],
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            hand=["tactical_focus"],
            actions=2,
            bonus_actions=1
        )
        enemy = EnemyState(
            name="测试敌人",
            hp=20,
            max_hp=20,
            shield=0
        )
        run = GameRun(
            user_id="test_user_focus",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine.battle_engine
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        engine.save_manager = DummySaveManager()
        self.assertEqual(len(player.hand), 1)
        self.assertEqual(player.hand[0], "tactical_focus")
        engine.play_card(run, 1)
        self.assertNotIn("tactical_focus", player.hand)
        self.assertEqual(len(player.hand), 3)
        self.assertEqual(player.actions, 2)
        self.assertEqual(player.bonus_actions, 1)
        focus_buff = next(b for b in player.buffs if b.id == "tactical_focus")
        self.assertEqual(focus_buff.name, "无法抽牌")
        self.assertEqual(focus_buff.stacks, 1)
        original_hand_len = len(player.hand)
        engine._draw_cards(player, 1, run)
        self.assertEqual(len(player.hand), original_hand_len)
        engine.end_turn(run)
        self.assertFalse(any(b.id == "tactical_focus" for b in player.buffs))
        player.buffs.append(BuffState(id="tactical_focus", name="无法抽牌", desc="本回合无法再抽牌", stacks=2))
        player.draw_pile = ["dagger_throw"] * 10
        player.discard_pile = []
        player.hand = []
        engine.end_turn(run)
        self.assertEqual(len(player.hand), 6)
        self.assertTrue(any(b.id == "tactical_focus" for b in player.buffs))
        self.assertEqual(next(b for b in player.buffs if b.id == "tactical_focus").stacks, 1)
        curr_hand_len = len(player.hand)
        engine._draw_cards(player, 1, run)
        self.assertEqual(len(player.hand), curr_hand_len)
        engine._draw_cards(player, 1, run, ignore_focus=True)
        self.assertEqual(len(player.hand), curr_hand_len + 1)
        engine.end_turn(run)
        self.assertFalse(any(b.id == "tactical_focus" for b in player.buffs))

        player_upg = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=2,
            deck=["tactical_focus+"],
            draw_pile=["dagger_throw", "first_aid", "lucky_coin", "thorns_necklace", "iron_will", "quick_strike", "arcane_spark"],
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            hand=["tactical_focus+"],
            actions=2,
            bonus_actions=1
        )
        run_upg = GameRun(
            user_id="test_user_focus_upgraded",
            node_type="battle",
            player=player_upg,
            enemies=[enemy]
        )
        engine.play_card(run_upg, 1)
        self.assertNotIn("tactical_focus+", player_upg.hand)
        self.assertEqual(len(player_upg.hand), 5)
        self.assertEqual(player_upg.actions, 2)
        self.assertEqual(player_upg.bonus_actions, 1)
        focus_buff_upg = next(b for b in player_upg.buffs if b.id == "tactical_focus")
        self.assertEqual(focus_buff_upg.name, "无法抽牌")
        self.assertEqual(focus_buff_upg.stacks, 1)

    def test_echo_form_logic(self):
        def run_echo_test(stacks, num_cards_to_play):
            player = PlayerState(
                hp=30,
                max_hp=30,
                shield=0,
                gold=100,
                stage=2,
                deck=["fire_bolt"] * 10,
                draw_pile=["fire_bolt"] * 10,
                discard_pile=[],
                exhaust_pile=[],
                graveyard=[],
                hand=["fire_bolt"] * 10,
                actions=99,
                bonus_actions=99,
                buffs=[BuffState(id="echo_form", name="回响形态", stacks=stacks, desc="")]
            )
            enemy = EnemyState(
                name="测试敌人",
                hp=9999,
                max_hp=9999,
                shield=0
            )
            run = GameRun(
                user_id="test_user_echo",
                node_type="battle",
                player=player,
                enemies=[enemy]
            )
            class DummySaveManager:
                def save_save(self, user_id, run):
                    pass
                def delete_save(self, user_id):
                    pass
            engine = BattleEngine(DummySaveManager())
            results = []
            for i in range(num_cards_to_play):
                res = engine.play_card(run, 1)
                echo_count = res.count("[回响触发]")
                results.append(echo_count)
            return results

        res5 = run_echo_test(5, 3)
        self.assertEqual(res5, [5, 0, 0])
        res10 = run_echo_test(10, 3)
        self.assertEqual(res10, [5, 5, 0])
        res24 = run_echo_test(24, 4)
        self.assertEqual(res24, [5, 5, 5, 5])

        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=2,
            deck=["echo_form"],
            draw_pile=["echo_form"],
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            hand=["echo_form"],
            actions=99,
            bonus_actions=99
        )
        enemy = EnemyState(
            name="测试敌人",
            hp=100,
            max_hp=100,
            shield=0
        )
        run = GameRun(
            user_id="test_user_echo_self",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        engine = BattleEngine(DummySaveManager())
        res = engine.play_card(run, 1)
        self.assertEqual(res.count("[回响触发]"), 0)
        self.assertEqual(next(b for b in player.buffs if b.id == "echo_form").stacks, 1)

    def test_shield_decay_mechanism(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            node_data={"cards_played_this_turn": 0},
            player=PlayerState(
                hp=30,
                max_hp=30,
                shield=15,
                actions=2,
                bonus_actions=1,
                deck=[],
                hand=[],
                draw_pile=[],
                discard_pile=[],
                exhaust_pile=[],
                graveyard=[],
                amulets={},
                minions={},
                buffs=[],
                gold=100,
                stage=1
            ),
            enemies=[
                EnemyState(
                    name="地精突袭者",
                    hp=12,
                    max_hp=12,
                    shield=9,
                    actions=1,
                    bonus_actions=0,
                    max_actions=1,
                    max_bonus_actions=0,
                    intent_a_type="attack",
                    intent_a_val=0,
                    intent_a_desc="准备防守"
                )
            ]
        )
        engine.end_turn(run)
        self.assertEqual(run.player.shield, 7)
        self.assertEqual(run.enemies[0].shield, 4)

    def test_fragile_card_mechanism(self):
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=2,
            deck=["thunderwave"],
            draw_pile=["thunderwave"],
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            hand=["thunderwave"],
            actions=10,
            bonus_actions=10
        )
        enemy = EnemyState(
            name="测试敌人",
            hp=50,
            max_hp=50,
            shield=0
        )
        run = GameRun(
            user_id="test_user_fragile",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        engine = BattleEngine(DummySaveManager())
        card_wave = ALL_CARDS.get("thunderwave")
        self.assertEqual(card_wave.fragile, 3)
        self.assertEqual(card_wave.name, "雷鸣波")
        self.assertIn("易碎 3。", card_wave.desc)
        
        engine.play_card(run, 1)
        self.assertIn("thunderwave:fragile:2", player.discard_pile)
        self.assertEqual(len(player.deck), 1)
        self.assertEqual(player.deck[0], "thunderwave")
        
        player.hand = ["thunderwave:fragile:2"]
        card_fragile_2 = ALL_CARDS.get("thunderwave:fragile:2")
        self.assertEqual(card_fragile_2.fragile, 2)
        self.assertEqual(card_fragile_2.name, "雷鸣波")
        self.assertIn("易碎 2。", card_fragile_2.desc)
        
        engine.play_card(run, 1)
        self.assertIn("thunderwave:fragile:1", player.discard_pile)
        self.assertEqual(len(player.deck), 1)
        
        player.discard_pile.clear()
        player.hand = ["thunderwave:fragile:1"]
        engine.play_card(run, 1)
        self.assertNotIn("thunderwave:fragile:0", player.discard_pile)
        self.assertNotIn("thunderwave", player.discard_pile)
        self.assertNotIn("thunderwave:fragile:1", player.discard_pile)
        self.assertEqual(len(player.deck), 0)
        
        card_wave_plus = ALL_CARDS.get("thunderwave+")
        self.assertEqual(card_wave_plus.fragile, 3)
        self.assertEqual(card_wave_plus.name, "雷鸣波+")
        self.assertIn("雷鸣波+", card_wave_plus.name)
        self.assertIn("易碎 3。", card_wave_plus.desc)
        
        card_wave_plus_2 = ALL_CARDS.get("thunderwave+:fragile:2")
        self.assertEqual(card_wave_plus_2.fragile, 2)
        self.assertIn("雷鸣波+", card_wave_plus_2.name)
        self.assertEqual(card_wave_plus_2.name, "雷鸣波+")

        q_fragile = render_query_info("易碎")
        self.assertIn("易碎", q_fragile)
        self.assertIn("从牌组中永久移除", q_fragile)
        q_recall = render_query_info("死者召回")
        self.assertIn("死者召回", q_recall)
        self.assertIn("阵亡随从", q_recall)

    def test_impervious_card_upgrade_and_execution(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=100,
            stage=1,
            deck=["impervious", "impervious+"],
            hand=["impervious", "impervious+"],
            actions=10,
            bonus_actions=10
        )
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 20, 20, 0)]
        )
        card_normal = ALL_CARDS.get("impervious")
        self.assertEqual(card_normal.cost_a, 2)
        self.assertEqual(card_normal.cost_ba, 0)
        res_normal = engine.play_card(run, 1)
        self.assertEqual(player.shield, 30)
        self.assertIn("获得了 30 点护盾", res_normal)

        player.shield = 0
        card_plus = ALL_CARDS.get("impervious+")
        self.assertEqual(card_plus.cost_a, 2)
        self.assertEqual(card_plus.cost_ba, 0)
        self.assertIn("获得 50 点护盾", card_plus.desc)
        res_plus = engine.play_card(run, 1)
        self.assertEqual(player.shield, 50)
        self.assertIn("获得了 50 点护盾", res_plus)

    def test_entrench_card_upgrade_and_execution(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=10,
            gold=100,
            stage=1,
            deck=["entrench", "entrench+"],
            hand=["entrench", "entrench+"],
            actions=10,
            bonus_actions=10
        )
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 20, 20, 0)]
        )
        card_normal = ALL_CARDS.get("entrench")
        self.assertEqual(card_normal.cost_a, 0)
        self.assertEqual(card_normal.cost_ba, 1)
        res_normal = engine.play_card(run, 1)
        self.assertEqual(player.shield, 20)
        self.assertIn("获得了 10 点护盾", res_normal)
        self.assertEqual(player.bonus_actions, 9)

        player.shield = 10
        player.bonus_actions = 10
        card_plus = ALL_CARDS.get("entrench+")
        self.assertEqual(card_plus.cost_a, 0)
        self.assertEqual(card_plus.cost_ba, 1)
        self.assertIn("翻三倍", card_plus.desc)
        res_plus = engine.play_card(run, 1)
        self.assertEqual(player.shield, 30)
        self.assertIn("获得了 20 点护盾", res_plus)

    def test_barricade_card_exhaust(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=100,
            stage=1,
            deck=["barricade", "barricade+"],
            hand=["barricade", "barricade+"],
            actions=10,
            bonus_actions=10
        )
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 20, 20, 0)]
        )
        card_normal = ALL_CARDS.get("barricade")
        self.assertTrue(card_normal.exhaust)
        self.assertIn("消耗。", card_normal.desc)

        card_plus = ALL_CARDS.get("barricade+")
        self.assertTrue(card_plus.exhaust)
        self.assertIn("消耗。", card_plus.desc)

        engine.play_card(run, 1)
        self.assertIn("barricade", player.exhaust_pile)
        self.assertEqual(len(player.hand), 1)

    def test_flame_barrier_timing(self):
        from game.models.state import EnemyIntentState
        from game.core.battle_engine import BattleEngine
        from game.models.manager import SaveManager
        engine = BattleEngine(SaveManager())
        player = PlayerState(hp=30, max_hp=30, shield=0, gold=100, stage=1, deck=[], hand=[], draw_pile=[], discard_pile=[], exhaust_pile=[], graveyard=[])
        enemy = EnemyState(name="小鬼", hp=100, max_hp=100, shield=0, actions=1, max_actions=1, bonus_actions=0, max_bonus_actions=0, intent_type="attack", intent_val=10, intent_desc="攻击 10", intents=[])
        enemy.intents = [EnemyIntentState(type="attack", val=10, desc="攻击 10", cost_a=1, cost_ba=0)]
        run = GameRun(user_id="test_user", node_type="battle", player=player, enemies=[enemy], node_data={})
        engine._add_buff_to(player, "flame_barrier_buff", "火焰屏障", "受到伤害时对攻击源反弹真实伤害", 8)
        self.assertTrue(any(b.id == "flame_barrier_buff" for b in player.buffs))
        engine.end_turn(run)
        self.assertEqual(enemy.hp, 92)
        self.assertFalse(any(b.id == "flame_barrier_buff" for b in player.buffs))

    def test_echo_form_and_replay_triggers_beat_of_death(self):
        from game.models.state import BuffState
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                class DummyStats:
                    selected_class = "战士"
                return DummyStats()
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=100,
            max_hp=100,
            shield=0,
            gold=100,
            stage=1,
            deck=["fire_bolt:replay:3"],
            hand=["fire_bolt:replay:3"],
            actions=10,
            bonus_actions=10
        )
        enemy = EnemyState("测试敌人", 9999, 9999, 0)
        run = GameRun(
            user_id="test_user_beat_death",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        player.buffs = [
            BuffState(id="echo_form", name="回响形态", stacks=1, desc="")
        ]
        enemy.buffs = [
            BuffState(id="beat_of_death", name="死亡律动", stacks=2, desc="")
        ]
        run.node_data["cards_played_this_turn"] = 0
        engine.play_card(run, 1)
        self.assertEqual(player.hp, 84)

    def test_iron_will_upgrade_and_stack(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=20,
            max_hp=40,
            shield=0,
            gold=100,
            stage=1,
            deck=["iron_will+", "first_aid"],
            hand=["iron_will+", "first_aid"],
            actions=5,
            bonus_actions=5
        )
        run = GameRun(
            user_id="test_user_iron_will_upg",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 100, 100, 0, max_actions=0)]
        )
        engine.play_card(run, 1, None)
        self.assertEqual(player.shield, 8)
        self.assertEqual(player.hp, 35)
        engine.play_card(run, 1, None)
        self.assertEqual(player.hp, 43)
        engine.end_turn(run)
        player.actions = 5
        player.bonus_actions = 5
        player.hand = ["first_aid", "first_aid"]
        engine.play_card(run, 1, None)
        self.assertEqual(player.hp, 51)
        engine.end_turn(run)
        player.actions = 5
        player.bonus_actions = 5
        player.hand = ["first_aid"]
        engine.play_card(run, 1, None)
        self.assertEqual(player.hp, 55)

    def test_warrior_shield_bash(self):
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine.battle_engine
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=10,
            gold=100,
            stage=1,
            deck=["warrior_shield_bash", "warrior_shield_bash+"],
            hand=["warrior_shield_bash", "warrior_shield_bash+"],
            actions=5,
            bonus_actions=5
        )
        enemy = EnemyState("测试敌人", 100, 100, 0)
        run = GameRun(
            user_id="test_user_shield_bash",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        engine.play_card(run, 1, "e0")
        self.assertEqual(player.shield, 26)
        self.assertEqual(enemy.hp, 87)
        engine.play_card(run, 1, "e0")
        self.assertEqual(player.shield, 50)
        self.assertEqual(enemy.hp, 62)
        from game.models.events import CardExhaustEvent
        player.actions = 2
        player.bonus_actions = 1
        engine.event_bus.dispatch(CardExhaustEvent(run, "warrior_shield_bash", "test"))
        self.assertEqual(player.actions, 4)
        self.assertEqual(player.bonus_actions, 3)
        engine.event_bus.dispatch(CardExhaustEvent(run, "warrior_shield_bash+", "test"))
        self.assertEqual(player.actions, 6)
        self.assertEqual(player.bonus_actions, 5)

    def test_enemy_cleansing_buffs(self):
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine.battle_engine
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=10,
            gold=100,
            stage=1,
            deck=["warrior_strike"],
            hand=["warrior_strike"],
            actions=5,
            bonus_actions=5
        )
        enemy = EnemyState("测试敌人", 100, 100, 10)
        run = GameRun(
            user_id="test_user_cleansing",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        enemy.buffs = [
            BuffState(id="ancient_protection", name="先古庇护", desc="", stacks=1),
            BuffState(id="vulnerable", name="易伤", desc="", stacks=2)
        ]
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        engine.save_manager = DummySaveManager()
        engine.end_turn(run)
        self.assertFalse(any(b.id == "vulnerable" for b in enemy.buffs))
        self.assertTrue(any(b.id == "ancient_protection" for b in enemy.buffs))

        enemy2 = EnemyState("测试敌人2", 100, 100, 0)
        run2 = GameRun(
            user_id="test_user_cleansing2",
            node_type="battle",
            player=player,
            enemies=[enemy2]
        )
        enemy2.buffs = [
            BuffState(id="end_gate_passive", name="终焉之门", desc="", stacks=1),
            BuffState(id="vulnerable", name="易伤", desc="", stacks=2)
        ]
        engine.end_turn(run2)
        self.assertFalse(any(b.id == "vulnerable" for b in enemy2.buffs))
        self.assertTrue(any(b.id == "end_gate_passive" for b in enemy2.buffs))
        self.assertEqual(enemy2.shield, 15)

    def test_gem_desc_dynamic_modification_and_damage_fallbacks(self):
        from game.models.state import CardState
        from game.entities.cards.base import ALL_CARDS
        state = CardState(
            id="warrior_strike",
            upgraded=False,
            gems=["gem_dmg_mul_2", "gem_copy_1", "gem_retain", "gem_cost_ba_sub_1"]
        )
        card = ALL_CARDS[state]
        self.assertEqual(card.cost_ba, 0)
        self.assertIn("造成 12 点", card.desc)
        self.assertIn("复制 1", card.desc)
        self.assertIn("保留", card.desc)
        self.assertIn("BA消耗减少 1", card.desc)

        state2 = CardState(
            id="shield",
            upgraded=False,
            gems=["gem_dmg_mul_2"]
        )
        card2 = ALL_CARDS[state2]
        self.assertNotIn("造成", card2.desc)

        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=2,
            deck=[state2],
            draw_pile=[],
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            hand=[state2],
            actions=2,
            bonus_actions=1
        )
        enemy = EnemyState(
            name="测试敌人",
            hp=20,
            max_hp=20,
            shield=0
        )
        run = GameRun(
            user_id="test_user_gem_fallback",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine.battle_engine
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        engine.save_manager = DummySaveManager()
        engine.play_card(run, 1)
        self.assertEqual(enemy.hp, 20)

    def test_discover_exhaust(self):
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=2,
            deck=["discover"],
            draw_pile=["dagger_throw"],
            discard_pile=[],
            exhaust_pile=["first_aid"],
            graveyard=[],
            hand=["discover"],
            actions=2,
            bonus_actions=1
        )
        enemy = EnemyState(
            name="测试敌人",
            hp=20,
            max_hp=20,
            shield=0
        )
        run = GameRun(
            user_id="test_user_discover_exhaust",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine.battle_engine
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        engine.save_manager = DummySaveManager()
        engine.play_card(run, 1)
        run.node_data["state_stack"].pop()
        engine.resolve_suspended_card(run)
        self.assertTrue(any(c.id == "discover" for c in player.exhaust_pile))

    def test_hand_limit_draw_to_discard(self):
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=2,
            deck=[],
            draw_pile=["dagger_throw"],
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            hand=["fire_bolt"] * 12,
            actions=2,
            bonus_actions=1
        )
        enemy = EnemyState(
            name="测试敌人",
            hp=20,
            max_hp=20,
            shield=0
        )
        run = GameRun(
            user_id="test_user_hand_limit",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        plugin = MyPlugin(DummyContext())
        engine = plugin.engine.battle_engine
        engine.card_player.draw_cards(player, 1, run)
        self.assertEqual(len(player.hand), 12)
        self.assertEqual(len(player.discard_pile), 1)
        self.assertEqual(player.discard_pile[0], "dagger_throw")



