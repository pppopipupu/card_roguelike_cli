import unittest
from scratch.rogue_tests.base import *

class TestRogueCardMech2(unittest.TestCase):
    def test_unmined_gem_and_replay_logic(self):
        card_normal = ALL_CARDS.get("unmined_gem")
        self.assertIsNotNone(card_normal)
        self.assertEqual(card_normal.cost_a, 0)
        self.assertEqual(card_normal.cost_ba, 0)
        self.assertTrue(card_normal.exhaust)
        self.assertIn("重放 3", card_normal.desc)

        card_plus = ALL_CARDS.get("unmined_gem+")
        self.assertIsNotNone(card_plus)
        self.assertEqual(card_plus.cost_a, 0)
        self.assertEqual(card_plus.cost_ba, 0)
        self.assertTrue(card_plus.exhaust)
        self.assertIn("重放 4", card_plus.desc)

        card_replay = ALL_CARDS.get("fire_bolt:replay:3")
        self.assertIsNotNone(card_replay)
        self.assertEqual(card_replay.replay, 3)
        self.assertEqual(card_replay.name, ALL_CARDS.get("fire_bolt").name)
        self.assertIn("重放 3", card_replay.desc)

        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                class DummyStats:
                    selected_class = "法师"
                    killed_icerainboww = False
                return DummyStats()
            def record_stage_passed(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=100,
            stage=1,
            deck=["fire_bolt", "unmined_gem", "unmined_gem+"],
            hand=["fire_bolt", "unmined_gem", "unmined_gem+"],
            actions=10,
            bonus_actions=10
        )
        run = GameRun(
            user_id="test_user_replay",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 100, 100, 0)]
        )

        engine.play_card(run, 2)
        self.assertTrue(any(cid.replay == 3 for cid in player.hand))
        self.assertIn("unmined_gem", player.exhaust_pile)

        engine.play_card(run, 2)
        self.assertTrue(any(cid.replay == 7 or cid.replay == 16 for cid in player.hand))
        self.assertTrue(any(cid.id == "unmined_gem" and cid.upgraded for cid in player.exhaust_pile))

        self.assertEqual(len(player.hand), 1)
        target_card_id = player.hand[0]
        self.assertTrue(target_card_id.replay > 0)

        hp_before = run.enemies[0].hp
        engine.play_card(run, 1)
        hp_after = run.enemies[0].hp
        self.assertIn(hp_before - hp_after, (24, 51))

        player.hand = ["fire_bolt:replay:3"]
        player.buffs = [BuffState(id="echo_form", name="回响形态", stacks=1, desc="")]
        run.node_data["cards_played_this_turn"] = 0
        hp_before2 = run.enemies[0].hp
        engine.play_card(run, 1)
        hp_after2 = run.enemies[0].hp
        self.assertEqual(hp_before2 - hp_after2, 24)

        player.hand = ["fire_bolt:replay:3", "unmined_gem+"]
        player.actions = 10
        player.bonus_actions = 10
        engine.play_card(run, 2)
        self.assertEqual(player.hand[0], "fire_bolt:replay:7")

        from game.core.map_engine import MapEngine
        map_eng = MapEngine(sm, engine)
        
        found_in_1 = False
        for _ in range(50):
            player1 = PlayerState(hp=50, max_hp=50, shield=0, gold=100, stage=0)
            run1 = GameRun(user_id="test_map_ancient", node_type="map_select", player=player1)
            map_eng.enter_next_stage(run1)
            options1 = run1.node_data.get("options", [])
            if any(opt.get("card") == "unmined_gem" for opt in options1 if "card" in opt):
                found_in_1 = True
                break
        self.assertTrue(found_in_1)

        found_in_11 = False
        for _ in range(50):
            player11 = PlayerState(hp=50, max_hp=50, shield=0, gold=100, stage=12)
            run11 = GameRun(user_id="test_map_ancient", node_type="map_select", player=player11)
            map_eng.enter_next_stage(run11)
            from game.core.cafe_engine import CafeEngine
            CafeEngine(sm, map_eng).leave_cafe(run11)
            options11 = run11.node_data.get("options", [])
            if any(opt.get("card") == "unmined_gem" for opt in options11 if "card" in opt):
                found_in_11 = True
                break
        self.assertTrue(found_in_11)

        player.hand = ["echo_form:replay:3"]
        player.actions = 10
        player.bonus_actions = 10
        player.buffs.clear()
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "echo_form" and b.name == "回响形态" for b in player.buffs))

        player.hand = ["echo_form+:replay:4"]
        player.actions = 10
        player.bonus_actions = 10
        player.buffs.clear()
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "echo_form" and b.name == "回响形态" for b in player.buffs))

        player.hand = ["iron_will+:replay:3"]
        player.actions = 10
        player.bonus_actions = 10
        player.buffs.clear()
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "iron_will+" and b.name == "钢铁意志+" for b in player.buffs))

        player.hand = ["quicken:replay:3"]
        player.actions = 10
        player.bonus_actions = 10
        player.buffs.clear()
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "quicken" and b.name == "超魔-瞬发" for b in player.buffs))

        player.hand = ["magic_network+:replay:2"]
        player.actions = 10
        player.bonus_actions = 10
        player.buffs.clear()
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "magic_network+" and b.name == "魔网天成+" for b in player.buffs))

    def test_shockwave_with_echo_form(self):
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
            deck=["shockwave"],
            hand=["shockwave"],
            actions=10,
            bonus_actions=10,
            buffs=[BuffState(id="echo_form", name="回响形态", stacks=1, desc="")]
        )
        run = GameRun(
            user_id="test_user_shockwave",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 100, 100, 0)]
        )
        run.node_data["cards_played_this_turn"] = 0
        res = engine.play_card(run, 1)
        self.assertIn("震荡波", res)
        self.assertTrue(any(b.id == "minor_vulnerable" for b in run.enemies[0].buffs))
        self.assertTrue(any(b.id == "weak" for b in run.enemies[0].buffs))

    def test_sunburst_effects(self):
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
            deck=["sunburst", "sunburst+"],
            hand=["sunburst", "sunburst+"],
            minions={
                "1": MinionState("mercenary", "雇佣兵", 30, 30, 4, 1, 0),
                "2": MinionState("shield_guard", "盾卫", 10, 10, 2, 1, 0)
            }
        )
        player.minions["1"].buffs.append(BuffState(id="burning", name="燃烧", desc="每回合受伤害", stacks=2))
        run = GameRun(
            user_id="test_user_sunburst",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 30, 30, 0)]
        )
        card_sunburst = ALL_CARDS["sunburst"]
        card_sunburst.execute(run, None, engine)
        self.assertEqual(run.enemies[0].hp, 14)
        self.assertEqual(player.minions["1"].hp, 14)
        self.assertEqual(len(player.minions["1"].buffs), 1)
        self.assertEqual(player.minions["1"].atk, 4)
        self.assertNotIn("2", player.minions)
        
        player_upg = PlayerState(
            hp=50,
            max_hp=100,
            shield=0,
            gold=100,
            stage=1,
            deck=["sunburst", "sunburst+"],
            hand=["sunburst", "sunburst+"],
            minions={
                "1": MinionState("mercenary", "雇佣兵", 30, 30, 4, 1, 0),
                "2": MinionState("shield_guard", "盾卫", 10, 10, 2, 1, 0)
            }
        )
        player_upg.minions["1"].buffs.append(BuffState(id="burning", name="燃烧", desc="每回合受伤害", stacks=2))
        run_upg = GameRun(
            user_id="test_user_sunburst_upg",
            node_type="battle",
            player=player_upg,
            enemies=[EnemyState("测试敌人", 30, 30, 0)]
        )
        card_sunburst_upg = ALL_CARDS["sunburst+"]
        card_sunburst_upg.execute(run_upg, None, engine)
        self.assertEqual(run_upg.enemies[0].hp, 8)
        self.assertEqual(player_upg.minions["1"].hp, 8)
        self.assertEqual(len(player_upg.minions["1"].buffs), 0)
        self.assertEqual(player_upg.minions["1"].atk, 7)
        self.assertNotIn("2", player_upg.minions)

    def test_chain_lightning_default_target(self):
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
            deck=["chain_lightning"],
            hand=["chain_lightning"],
            actions=2,
            bonus_actions=1
        )
        run = GameRun(
            user_id="test_user_chain",
            node_type="battle",
            player=player,
            enemies=[EnemyState("哥布林 A", 20, 20, 0)]
        )
        res = engine.play_card(run, 1, None)
        self.assertIn("释放【链式闪电】", res)
        self.assertEqual(run.enemies[0].hp, 8)

    def test_blacklist_spell_targeting(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=20,
            max_hp=50,
            shield=0,
            gold=100,
            stage=1,
            deck=["first_aid", "magic_missile"],
            hand=["first_aid", "magic_missile"],
            actions=5,
            bonus_actions=5
        )
        run = GameRun(
            user_id="test_user_blacklist_targeting",
            node_type="battle",
            player=player,
            enemies=[EnemyState("哥布林 A", 20, 20, 0)]
        )
        engine.play_card(run, 1, None)
        self.assertEqual(player.hp, 24)
        engine.play_card(run, 1, None)
        self.assertEqual(run.enemies[0].hp, 11)

    def test_arcane_barrier_and_buffer_buff(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=1,
            deck=["arcane_barrier", "arcane_barrier+"],
            hand=["arcane_barrier", "arcane_barrier+"],
            actions=3,
            bonus_actions=3
        )
        enemy = EnemyState("测试敌人", 50, 50, 0)
        run = GameRun(
            user_id="test_buffer_user",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        
        run.node_data["last_x_cost_ba"] = 1
        card_barrier = ALL_CARDS["arcane_barrier"]
        card_barrier.execute(run, None, engine)
        self.assertEqual(player.shield, 6)
        self.assertFalse(any(b.id == "buffer" for b in player.buffs))
        
        player.shield = 0
        run.node_data["last_x_cost_ba"] = 2
        card_barrier.execute(run, None, engine)
        self.assertEqual(player.shield, 12)
        self.assertTrue(any(b.id == "buffer" for b in player.buffs))
        buffer_buff = next(b for b in player.buffs if b.id == "buffer")
        self.assertEqual(buffer_buff.stacks, 1)
        
        engine.combat_resolver.damage_target(run, "p0", 15, damage_type="bludgeoning")
        self.assertEqual(player.hp, 30)
        self.assertEqual(player.shield, 12)
        self.assertFalse(any(b.id == "buffer" for b in player.buffs))
        
        player.shield = 0
        run.node_data["last_x_cost_ba"] = 1
        card_barrier_plus = ALL_CARDS["arcane_barrier+"]
        card_barrier_plus.execute(run, None, engine)
        self.assertEqual(player.shield, 9)
        self.assertFalse(any(b.id == "buffer" for b in player.buffs))
        
        player.shield = 0
        run.node_data["last_x_cost_ba"] = 2
        card_barrier_plus.execute(run, None, engine)
        self.assertEqual(player.shield, 18)
        self.assertTrue(any(b.id == "buffer" for b in player.buffs))

    def test_arcane_torrent_aoe(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=0,
            gold=100,
            stage=1,
            deck=["arcane_torrent", "arcane_torrent+"],
            hand=["arcane_torrent", "arcane_torrent+"],
            actions=3,
            bonus_actions=3
        )
        enemies = [
            EnemyState("测试敌人A", 50, 50, 0),
            EnemyState("测试敌人B", 50, 50, 0)
        ]
        run = GameRun(
            user_id="test_torrent_user",
            node_type="battle",
            player=player,
            enemies=enemies
        )
        
        run.node_data["last_x_cost_a"] = 1
        card_torrent = ALL_CARDS["arcane_torrent"]
        card_torrent.execute(run, None, engine)
        self.assertEqual(enemies[0].hp, 44)
        self.assertEqual(enemies[1].hp, 44)
        
        enemies[0].hp = 50
        enemies[1].hp = 50
        run.node_data["last_x_cost_a"] = 3
        card_torrent.execute(run, None, engine)
        self.assertEqual(enemies[0].hp, 14)
        self.assertEqual(enemies[1].hp, 14)
        
        enemies[0].hp = 50
        enemies[1].hp = 50
        run.node_data["last_x_cost_a"] = 1
        engine._add_buff_to(player, "wish_power", "祈愿奥术", "本场战斗法术伤害 +4", 1)
        res_buffed = card_torrent.execute(run, None, engine)
        self.assertEqual(enemies[0].hp, 36)
        self.assertEqual(enemies[1].hp, 36)
        self.assertIn("2 次 7 点真实伤害", res_buffed)

    def test_master_key_chant_reduction_feedback(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        card_key = ALL_CARDS["master_key"]
        for upgraded, reduction in ((False, 2), (True, 3)):
            player = PlayerState(
                hp=30,
                max_hp=30,
                shield=0,
                gold=10,
                stage=1,
                deck=["master_key"],
                hand=["master_key"],
                draw_pile=["thorns_necklace"],
                actions=3,
                bonus_actions=3
            )
            run = GameRun(
                user_id="test_master_key_reduction_user",
                node_type="battle",
                player=player,
                enemies=[EnemyState("测试敌人A", 50, 50, 0)]
            )
            from game.models.state import AmuletState
            player.amulets["1"] = AmuletState(id="some_amulet", name="测试护符", countdown=6, desc="测试描述")
            card_key.upgraded = upgraded
            res = card_key.execute(run, None, engine)
            self.assertEqual(player.amulets["1"].countdown, 6 - reduction)
            self.assertIn(f"吟唱时间减少 {reduction}", res)
        card_key.upgraded = False

    def test_multiple_thorns_amulet_reflect_does_not_reenter(self):
        from game.models.state import AmuletState

        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass

        engine = BattleEngine(DummySaveManager())
        player = PlayerState(50, 50, 0, 0, 1, name="测试")
        for grid in "123456":
            player.amulets[grid] = AmuletState("thorns_necklace", "荆棘项链", 1, "")
        enemy = EnemyState(
            "终焉测试",
            100,
            100,
            0,
            buffs=[BuffState("doomsday_gate_passive", "终焉庇护")],
        )
        run = GameRun("test_thorns_user", "battle", player, [enemy], {}, {})
        engine._damage_target(run, "e1", 5, source="relic:djinn_shard", damage_type="force")
        self.assertEqual(player.amulets, {})
        self.assertEqual(player.minion_graveyard.count("thorns_necklace"), 6)
        self.assertFalse(getattr(run, "_amulet_damage_trigger_active", False))

    def test_end_turn_amulet_trigger_deletion_is_safe(self):
        from game.models.state import AmuletState

        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass

        engine = BattleEngine(DummySaveManager())
        player = PlayerState(500, 500, 0, 0, 1, name="测试")
        player.amulets["1"] = AmuletState("void_beacon", "虚空信标", 3, "")
        for grid in "234567":
            player.amulets[grid] = AmuletState("thorns_necklace", "荆棘项链", 1, "")
        enemy = EnemyState(
            "终焉测试",
            1000,
            1000,
            0,
            buffs=[BuffState("end_gate_passive", "终焉之门")],
        )
        run = GameRun("test_amulet_end_turn_user", "battle", player, [enemy], {}, {})
        engine.card_player._end_player_phase(run, player)
        self.assertEqual(list(player.amulets), ["1"])
        self.assertEqual(player.minion_graveyard.count("thorns_necklace"), 6)

    def test_flow_more_special_cards_and_buffs(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=30,
            max_hp=100,
            shield=15,
            actions=10,
            bonus_actions=10,
            deck=["barricade"],
            hand=["barricade"],
            draw_pile=["arcane_spark", "arcane_spark"],
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            amulets={},
            minions={},
            buffs=[],
            gold=100,
            stage=1
        )
        run = GameRun(
            user_id="test_user_sp",
            node_type="battle",
            node_data={"cards_played_this_turn": 0},
            player=player,
            enemies=[EnemyState(name="地精", hp=9999, max_hp=9999, shield=0, actions=0, bonus_actions=0, max_actions=0, max_bonus_actions=0)]
        )
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "buffer" for b in player.buffs))
        self.assertTrue(any(b.id == "barricade" for b in player.buffs))
        engine._damage_target(run, "p0", 10, damage_type="slash")
        self.assertEqual(player.hp, 30)
        self.assertEqual(player.shield, 5)
        self.assertTrue(any(b.id == "buffer" for b in player.buffs))
        engine._damage_target(run, "p0", 10, damage_type="slash")
        self.assertEqual(player.hp, 30)
        self.assertEqual(player.shield, 5)
        self.assertFalse(any(b.id == "buffer" for b in player.buffs))
        player.shield = 15
        engine.end_turn(run)
        self.assertEqual(player.shield, 15)
        
        player.hand = ["glacier_fortress"]
        player.actions = 2
        engine.play_card(run, 1)
        self.assertEqual(player.shield, 35)
        self.assertTrue(any(b.id == "glacier_fortress_buff" for b in player.buffs))
        engine.end_turn(run)
        self.assertEqual(player.shield, 39)
        
        player.hand = ["archmage_wish", "fire_bolt"]
        player.actions = 4
        player.bonus_actions = 4
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "wish_power" for b in player.buffs))
        enemy = run.enemies[0]
        engine.play_card(run, 1, "e1")
        self.assertEqual(enemy.hp, 9992)
        
        player.hand = ["demon_form"]
        player.actions = 2
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "demon_form" for b in player.buffs))
        self.assertEqual(next(b for b in player.buffs if b.id == "demon_form").stacks, 3)
        from game.models.events import TurnStartEvent
        engine.event_bus.dispatch(TurnStartEvent(run, is_player=True))
        self.assertTrue(any(b.id == "strength" for b in player.buffs))
        self.assertEqual(next(b for b in player.buffs if b.id == "strength").stacks, 3)
        
        player.hand = ["time_warp", "arcane_spark"]
        player.discard_pile = ["arcane_spark"]
        player.actions = 2
        engine.play_card(run, 1)
        self.assertEqual(len(player.discard_pile), 0)
        self.assertEqual(len(player.hand), 2)
        
        player.buffs = [BuffState(id="strength", name="力量", desc="", stacks=2)]
        player.hand = ["break_limits"]
        player.actions = 2
        player.bonus_actions = 1
        engine.play_card(run, 1)
        self.assertEqual(next(b for b in player.buffs if b.id == "strength").stacks, 4)
        
        player.buffs = [BuffState(id="strength", name="力量", desc="", stacks=2000)]
        player.hand = ["break_limits"]
        player.actions = 2
        player.bonus_actions = 1
        engine.play_card(run, 1)
        self.assertEqual(next(b for b in player.buffs if b.id == "strength").stacks, 4000)

        player.buffs = [BuffState(id="strength", name="力量", desc="", stacks=2001)]
        player.hand = ["break_limits"]
        player.actions = 2
        player.bonus_actions = 1
        engine.play_card(run, 1)
        self.assertEqual(next(b for b in player.buffs if b.id == "strength").stacks, 2001)
        
        enemy.buffs = []
        player.hand = ["abyss_collapse"]
        player.actions = 2
        engine.play_card(run, 1, "e1")
        self.assertEqual(enemy.hp, 9968)
        
        engine._add_buff_to(enemy, "stun", "眩晕", "无法行动", 1)
        player.hand = ["abyss_collapse"]
        player.actions = 2
        engine.play_card(run, 1, "e1")
        self.assertEqual(enemy.hp, 9920)
        
        player.hand = ["demon_contract"]
        player.actions = 2
        player.bonus_actions = 1
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "demon_contract_buff" for b in player.buffs))
        self.assertEqual(player.bonus_actions, 3)
        
        enemy.buffs = []
        player.hand = ["frost_nova"]
        player.actions = 2
        engine.play_card(run, 1)
        self.assertTrue(any(b.id == "stun" for b in enemy.buffs))
        self.assertTrue(any(b.id == "minor_vulnerable_cold" for b in enemy.buffs))
        
        enemy.buffs = []
        player.hand = ["abyss_erosion"]
        player.actions = 2
        engine.play_card(run, 1, "e1")
        self.assertTrue(any(b.id == "void_weakness" for b in enemy.buffs))
        
        player.minions = {"1": MinionState(id="mercenary", name="雇佣兵", hp=10, max_hp=10, atk=4, actions=1, bonus_actions=0)}
        player.shield = 0
        player.hand = ["glacier_tempest"]
        player.actions = 4
        engine.play_card(run, 1)
        self.assertEqual(player.shield, 6)
        
        player.hand = ["time_stop"]
        player.actions = 2
        engine.play_card(run, 1)
        self.assertEqual(run.node_data["extra_turns_left"], 3)

    def test_buffer_buff_mechanics(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=30,
            max_hp=30,
            shield=10,
            actions=3,
            bonus_actions=3,
            gold=100,
            stage=1
        )
        enemy = EnemyState("测试敌人", 50, 50, 0)
        run = GameRun(
            user_id="test_buffer_mechanics_user",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        engine._add_buff_to(player, "buffer", "缓冲", "免疫下一次伤害", 1)
        self.assertTrue(any(b.id == "buffer" for b in player.buffs))
        engine.combat_resolver.damage_target(run, "p0", 5, damage_type="bludgeoning")
        self.assertEqual(player.hp, 30)
        self.assertEqual(player.shield, 5)
        self.assertTrue(any(b.id == "buffer" for b in player.buffs))
        engine.combat_resolver.damage_target(run, "p0", 2, damage_type="true")
        self.assertEqual(player.hp, 30)
        self.assertEqual(player.shield, 5)
        self.assertFalse(any(b.id == "buffer" for b in player.buffs))
        engine._add_buff_to(player, "buffer", "缓冲", "免疫下一次伤害", 1)
        engine.combat_resolver.damage_target(run, "p0", 10, damage_type="bludgeoning")
        self.assertEqual(player.hp, 30)
        self.assertEqual(player.shield, 5)
        self.assertFalse(any(b.id == "buffer" for b in player.buffs))

    def test_market_cards_upgraded(self):
        class DummySaveManager:
            def __init__(self):
                from game.models.state import UserStats
                self.stats = UserStats()
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return self.stats
            def save_stats(self, user_id, stats):
                self.stats = stats
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(
            hp=50,
            max_hp=100,
            shield=10,
            actions=5,
            bonus_actions=5,
            gold=100,
            stage=25
        )
        enemy = EnemyState("测试敌人", 200, 200, 0)
        run = GameRun(
            user_id="test_market_upgraded_user",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        
        from game.models.state import CardState, BuffState
        
        card_fury = CardState("warrior_blood_fury", upgraded=True)
        fury_obj = ALL_CARDS.get(card_fury)
        player.hp = 50
        player.hand = []
        player.draw_pile = ["warrior_strike", "warrior_defend", "warrior_strike"]
        fury_obj.execute(run, None, engine)
        self.assertEqual(player.hp, 47)
        self.assertEqual(next(b for b in player.buffs if b.id == "strength").stacks, 3)
        self.assertEqual(len(player.hand), 3)
        
        player.buffs = []
        player.hand = []
        player.draw_pile = ["wizard_prismatic_wall+"]
        card_hell = CardState("warrior_hell_raider", upgraded=True)
        hell_obj = ALL_CARDS.get(card_hell)
        hell_obj.execute(run, None, engine)
        self.assertTrue(any(b.id == "hell_raider_upgraded" for b in player.buffs))
        engine.card_player.draw_cards(player, 1, run)
        self.assertTrue(any(b.id == "prismatic_barrier_upgraded" for b in player.buffs))
        self.assertEqual(player.shield, 160)
        
        enemy.hp = 200
        engine.combat_resolver.damage_target(run, "p0", 5, source="e1", damage_type="bludgeoning")
        self.assertEqual(enemy.hp, 180)
        
        player.buffs = [
            BuffState(id="weak", name="虚弱", desc="", stacks=2),
            BuffState(id="strength", name="力量", desc="", stacks=3)
        ]
        enemy.buffs = [
            BuffState(id="weak", name="虚弱", desc="", stacks=1),
            BuffState(id="strength", name="力量", desc="", stacks=2)
        ]
        from game.models.state import AmuletState
        player.amulets = {"1": AmuletState(id="some_amulet", name="测试护符", countdown=3, desc="测试描述")}
        card_anti = CardState("wizard_antimagic_field", upgraded=True)
        anti_obj = ALL_CARDS.get(card_anti)
        anti_obj.execute(run, None, engine)
        self.assertEqual(len(player.buffs), 0)
        self.assertEqual(len(enemy.buffs), 0)
        self.assertEqual(len(player.amulets), 0)
        
        player.buffs = [BuffState(id="strength", name="力量", desc="", stacks=3)]
        enemy.buffs = [BuffState(id="weak", name="虚弱", desc="", stacks=1)]
        from game.models.state import MinionState
        player.minions = {"1": MinionState(id="royal_guard", name="皇家卫兵", hp=10, max_hp=10, atk=3, buffs=[BuffState(id="ward", name="守护", desc="", stacks=1)], actions=1, bonus_actions=0)}
        player.amulets = {"1": AmuletState(id="some_amulet", name="测试护符", countdown=3, desc="测试描述")}
        card_anti_normal = CardState("wizard_antimagic_field", upgraded=False)
        anti_obj_normal = ALL_CARDS.get(card_anti_normal)
        anti_obj_normal.execute(run, None, engine)
        self.assertEqual(len(player.buffs), 0)
        self.assertEqual(len(enemy.buffs), 0)
        self.assertEqual(len(player.minions["1"].buffs), 0)
        self.assertEqual(len(player.amulets), 0)
        
        enemy.hp = 200
        enemy.buffs = []
        player.action_a = 3
        card_time = CardState("wizard_time_ravage", upgraded=True)
        time_obj = ALL_CARDS.get(card_time)
        time_obj.execute(run, "e1", engine)
        self.assertEqual(enemy.hp, 175)
        self.assertEqual(next(b for b in enemy.buffs if b.id == "weak").stacks, 3)
        self.assertEqual(next(b for b in enemy.buffs if b.id == "vulnerable").stacks, 3)
        self.assertEqual(player.action_a, 4)
        
        enemy.hp = 120
        enemy.buffs = []
        card_kill = CardState("neutral_power_word_kill", upgraded=True)
        kill_obj = ALL_CARDS.get(card_kill)
        res = kill_obj.execute(run, "e1", engine)
        self.assertEqual(enemy.hp, 80)
        self.assertIn("40", res)
        kill_obj.execute(run, "e1", engine)
        self.assertEqual(enemy.hp, 0)
        # 7. 律令震慑升级版
        run.enemies = [enemy]
        enemy.hp = 180
        enemy.actions = 2
        card_stun = CardState("neutral_power_word_stun", upgraded=True)
        stun_obj = ALL_CARDS.get(card_stun)
        res = stun_obj.execute(run, "e1", engine)
        self.assertEqual(enemy.hp, 165)
        self.assertEqual(enemy.actions, 1)
        enemy.hp = 140
        stun_obj.execute(run, "e1", engine)
        self.assertTrue(any(b.id == "stun" for b in enemy.buffs))
        
        # 8. 律令痛苦升级版
        run.enemies = [enemy]
        enemy.hp = 200
        enemy.buffs = []
        card_pain = CardState("neutral_power_word_pain", upgraded=True)
        pain_obj = ALL_CARDS.get(card_pain)
        pain_obj.execute(run, "e1", engine)
        self.assertEqual(enemy.hp, 188)
        enemy.hp = 170
        pain_obj.execute(run, "e1", engine)
        self.assertEqual(next(b for b in enemy.buffs if b.id == "bleed").stacks, 4)
        self.assertEqual(next(b for b in enemy.buffs if b.id == "weak").stacks, 3)
        
        player.stage = 25
        player.gp = 100
        card_shift = CardState("neutral_plane_shift", upgraded=True)
        shift_obj = ALL_CARDS.get(card_shift)
        res = shift_obj.execute(run, None, engine)
        self.assertNotIn("❌", res)
        self.assertEqual(player.gp, 140)
        
        player.stage = 32
        res2 = shift_obj.execute(run, None, engine)
        self.assertIn("❌", res2)

        # 9. 神话卡牌: Omega
        player.hand = ["fire_bolt", "shield"]
        player.actions = 2
        run.enemies = [EnemyState(name="小木人", hp=100, max_hp=100, shield=0, actions=1, bonus_actions=1)]
        card_omega = CardState("neutral_omega", upgraded=True)
        omega_obj = ALL_CARDS.get(card_omega)
        omega_obj.execute(run, None, engine)
        self.assertLess(run.enemies[0].hp, 100)
        self.assertGreater(player.shield, 0)

        # 10. 一分为十 Buff 与乘算复制
        run.enemies = [EnemyState(name="小木人", hp=9999, max_hp=9999, shield=0, actions=1, bonus_actions=1)]
        player.buffs = [BuffState(id="split_to_ten", name="一分为十", desc="", stacks=1)]
        player.hand = [CardState("fire_bolt")]
        player.actions = 2
        engine.play_card(run, 1, "e1")
        self.assertEqual(run.enemies[0].hp, 9966)

        # 11. 神话卡牌: 造血
        player.shield = 20
        player.hp = 10
        player.max_hp = 40
        card_hem = CardState("warrior_hematopoiesis")
        hem_obj = ALL_CARDS.get(card_hem)
        hem_obj.execute(run, None, engine)
        self.assertEqual(player.shield, 0)
        self.assertEqual(player.hp, 30)

        player.shield = 20
        player.hp = 10
        card_hem_up = CardState("warrior_hematopoiesis", upgraded=True)
        hem_up_obj = ALL_CARDS.get(card_hem_up)
        hem_up_obj.execute(run, None, engine)
        self.assertEqual(player.shield, 0)
        self.assertEqual(player.hp, 40)

        # 12. 击败第二阶段 BOSS 神话宝箱
        player.stage = 25
        run.node_data = {"boss_name": "Icerainboww"}
        run.enemies = []
        stats = sm.load_stats("test_market_upgraded_user")
        stats.unlocked_gatekey = True
        sm.save_stats("test_market_upgraded_user", stats)

        engine.card_player.handle_battle_win(run)
        self.assertEqual(run.node_type, "boss_chest")
        self.assertTrue(any(opt["id"] == "infinite_hourglass" for opt in run.node_data["options"]))

        # 13. 神话遗物: 无限沙漏
        player.relics = ["infinite_hourglass"]
        run.node_data = {}
        engine._init_battle_node(run)
        self.assertEqual(run.node_data.get("extra_turns_left"), 1)
        player.bonus_actions = 1
        from game.models.events import TurnStartEvent
        engine.event_bus.dispatch(TurnStartEvent(run, is_player=True))
        self.assertEqual(player.bonus_actions, 2)

        card_echo = CardState("echo_form", upgraded=False)
        echo_obj = ALL_CARDS.get(card_echo)
        self.assertTrue(echo_obj.ethereal)
        card_echo_up = CardState("echo_form", upgraded=True)
        echo_up_obj = ALL_CARDS.get(card_echo_up)
        self.assertTrue(echo_up_obj.ethereal)

    def test_astral_strike_logic(self):
        from game.models.state import CardState
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
            hp=50,
            max_hp=50,
            shield=0,
            gold=100,
            stage=1,
            deck=["neutral_astral_strike"],
            hand=["neutral_astral_strike"],
            actions=10,
            bonus_actions=10
        )
        run = GameRun(
            user_id="test_astral_strike",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试敌人", 100, 100, 0)]
        )
        engine.play_card(run, 1)
        self.assertEqual(run.enemies[0].hp, 64)
        run.enemies = [EnemyState("测试敌人", 100, 100, 0)]
        player.hand = ["neutral_astral_strike"]
        engine._add_buff_to(player, "strength", "力量", "", 2)
        engine.play_card(run, 1)
        self.assertEqual(run.enemies[0].hp, 56)
        player.buffs = []
        run.enemies = [EnemyState("测试敌人", 100, 100, 0)]
        player.hand = [CardState("neutral_astral_strike", upgraded=True)]
        engine.play_card(run, 1)
        self.assertEqual(run.enemies[0].hp, 52)
        self.assertEqual(len(run.node_data.get("pending_gems", [])), 0)
        run.enemies = [EnemyState("测试敌人", 100, 100, 0)]
        player.hand = [CardState("neutral_astral_strike", upgraded=True)]
        engine._add_buff_to(player, "strength", "力量", "", 2)
        engine.play_card(run, 1)
        self.assertEqual(run.enemies[0].hp, 42)

    def test_meteor_strike_and_strike_of_all(self):
        from game.models.state import CardState
        self.assertEqual(ALL_CARDS.get("discover").color, "warrior")
        self.assertEqual(ALL_CARDS.get("meteor_strike").color, "wizard")
        self.assertEqual(ALL_CARDS.get("strike_of_all").color, "warrior")

        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                class DummyStats:
                    selected_class = "战士"
                    killed_icerainboww = False
                return DummyStats()
            def record_stage_passed(self, user_id):
                pass

        sm = DummySaveManager()
        engine = BattleEngine(sm)

        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=100,
            stage=1,
            deck=["warrior_strike", "strike_of_all", "meteor_strike", "warrior_defend"],
            hand=["meteor_strike"],
            actions=10,
            bonus_actions=10,
            draw_pile=["warrior_strike"],
            discard_pile=["discover"],
            exhaust_pile=[]
        )
        run = GameRun(
            user_id="test_user_meteor",
            node_type="battle",
            player=player,
            enemies=[EnemyState("测试怪物A", 9999, 9999, 0), EnemyState("测试怪物B", 9999, 9999, 0)]
        )

        res = engine.play_card(run, 1)
        self.assertNotIn("❌", res)
        self.assertNotIn("⚠️", res)

        total_hp = sum(e.hp for e in run.enemies)
        self.assertEqual(total_hp, 19878)
        self.assertTrue(any(a.id == "energy_core" for a in player.amulets.values()))

        grid = [g for g, a in player.amulets.items() if a.id == "energy_core"][0]
        amulet = player.amulets[grid]
        self.assertEqual(amulet.countdown, 1)

        player.hand = [CardState("meteor_strike", upgraded=True)]
        player.amulets.clear()
        engine.play_card(run, 1)
        self.assertEqual(len(run.enemies), 2)
        total_hp_upg = sum(e.hp for e in run.enemies)
        self.assertEqual(total_hp_upg, 19718)
        self.assertTrue(any(a.id == "energy_core+" for a in player.amulets.values()))

        grid_upg = [g for g, a in player.amulets.items() if a.id == "energy_core+"][0]
        amulet_upg = player.amulets[grid_upg]
        self.assertEqual(amulet_upg.countdown, 1)

        from game.entities.amulets.amulets import ALL_AMULETS
        player.actions = 0
        player.bonus_actions = 0
        lw_msg = ALL_AMULETS["energy_core"].on_death(run, grid_upg, True, engine)
        self.assertEqual(lw_msg, "你获得 2A 1BA。")
        self.assertEqual(player.actions, 2)
        self.assertEqual(player.bonus_actions, 1)

        player.deck = ["warrior_strike", "warrior_strike", "strike_of_all"]
        player.draw_pile = ["warrior_strike"]
        player.discard_pile = ["warrior_strike"]
        player.exhaust_pile = ["warrior_strike"]
        player.hand = ["strike_of_all"]
        player.actions = 10
        player.bonus_actions = 10
        run.enemies = [EnemyState("测试怪物A", 9999, 9999, 0)]

        engine.play_card(run, 1)
        self.assertEqual(run.enemies[0].hp, 9981)
        self.assertEqual(player.hand.count("warrior_strike"), 3)


        from game.renderer.query import render_query_info
        query_res = render_query_info("能量核心")
        self.assertIn("能量核心", query_res)
        self.assertIn("energy_core", query_res)

    def test_help_and_menu_guides(self):
        from game.renderer import GameRenderer
        help_text = GameRenderer.render_help()
        self.assertIn("bag", help_text)
        self.assertIn("quest", help_text)
        self.assertIn("lock", help_text)
        self.assertIn("map", help_text)
        self.assertIn("qi", help_text)
        self.assertIn("draw", help_text)
        self.assertIn("mg (eg)", help_text)
        self.assertIn("exit (quit/取消)", help_text)
        self.assertIn("talk", help_text)
        
        menu_text = GameRenderer.render_menu()
        self.assertIn("💡 提示：输入 /rogue help 或 help 可查看指令用法帮助。", menu_text)

        class DummyPlayer:
            def __init__(self):
                self.stage = 1
                self.hp = 100
                self.max_hp = 100
                self.gold = 100
                self.relics = []
                self.name = "测试玩家"
                self.fold_guide = False
        class DummyGameRun:
            def __init__(self):
                self.player = DummyPlayer()
                self.node_data = {"options": [{"desc": "前往分支1"}]}
                self.map_data = {"nodes": {}}
        
        run = DummyGameRun()
        from game.renderer.map import render_map_select
        map_text = render_map_select(run)
        self.assertIn("💡 提示：输入 /rogue help 或 help 可查看指令用法帮助。", map_text)

