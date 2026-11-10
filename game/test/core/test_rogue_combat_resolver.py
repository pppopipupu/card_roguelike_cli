import unittest
from game.test.core.base import *

class TestRogueCombatResolver(unittest.TestCase):
    def test_damage_system_and_real_damage(self):
        class DummySaveManager:
            def __init__(self):
                self.dir = "data_test"
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        save_mgr = DummySaveManager()
        engine = BattleEngine(save_mgr)
        player = PlayerState(
            hp=50,
            max_hp=100,
            shield=0,
            gold=100,
            stage=1,
            deck=["mass_healing_word", "chain_lightning", "magic_missile"],
            hand=["mass_healing_word", "chain_lightning", "magic_missile"],
            minions={
                "1": MinionState("mercenary", "雇佣兵", 5, 10, 4, 1, 0)
            }
        )
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            player=player,
            enemies=[
                EnemyState("哥布林掠夺者 A", 20, 20, 0),
                EnemyState("哥布林掠夺者 B", 20, 20, 0),
                EnemyState("地底史莱姆", 15, 15, 0)
            ]
        )
        run.player.actions = 10
        run.player.bonus_actions = 10
        card_heal = ALL_CARDS["mass_healing_word"]
        card_heal.execute(run, "p0", engine)
        self.assertEqual(run.player.hp, 58)
        self.assertEqual(run.player.minions["1"].hp, 10)
        card_chain = ALL_CARDS["chain_lightning"]
        card_chain.execute(run, "e1", engine)
        self.assertEqual(len(run.enemies), 3)
        self.assertEqual(run.enemies[0].hp, 8)
        self.assertEqual(run.enemies[1].hp, 8)
        self.assertEqual(run.enemies[2].hp, 15)
        enemy_mm = run.enemies[2]
        enemy_mm.shield = 20
        card_mm = ALL_CARDS["magic_missile"]
        card_mm.execute(run, "e3", engine)
        self.assertEqual(enemy_mm.shield, 20)
        self.assertEqual(enemy_mm.hp, 6)
        self.assertTrue(len(run.node_data.get("battle_logs", [])) > 0)
        last_log = run.node_data["battle_logs"][-1]
        self.assertNotIn("对护盾造成", last_log)
        self.assertIn("对生命造成", last_log)
        self.assertNotIn("（", last_log)

        from game.entities.enemies.elite.shadow_fiend import ShadowFiendTemplate
        fiend_template = ShadowFiendTemplate("暗影影魔")
        fiend_enemy = EnemyState("暗影影魔测试", 30, 30, 0, intent_type="shadow_strike", intent_val=6)
        fiend_logs = []
        run.player.hp = 50
        run.player.shield = 10
        fiend_template.execute_intent(run, engine, fiend_enemy, fiend_logs)
        self.assertEqual(run.player.shield, 10)
        self.assertEqual(run.player.hp, 44)
        self.assertEqual(len(fiend_logs), 1)
        self.assertIn("对【玩家】造成 6 点真实伤害，对生命造成 6 伤害", fiend_logs[0])

        from game.entities.buffs.debuffs import BeatOfDeathBuff
        beat_buff = BeatOfDeathBuff(2)
        class FakeEvent:
            def __init__(self, run, engine):
                self.run = run
                self.engine = engine
        evt = FakeEvent(run, engine)
        run.player.hp = 50
        run.player.shield = 0
        run.node_data["battle_logs"] = []
        beat_buff.on_card_played(evt, None, None)
        self.assertEqual(run.player.hp, 48)
        self.assertEqual(len(run.node_data["battle_logs"]), 2)
        self.assertIn("造成 2 点力场伤害", run.node_data["battle_logs"][-1])

        run.node_data["battle_logs"] = []
        engine._damage_target(run, "e3", 0, damage_type="cold")
        self.assertEqual(len(run.node_data["battle_logs"]), 1)
        self.assertIn("对【地底史莱姆】造成 0 点寒冷伤害（但地底史莱姆免疫了这次攻击！）", run.node_data["battle_logs"][-1])

    def test_enemy_action_sync_and_stun(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
        mgr = DummySaveManager()
        engine = BattleEngine(mgr)
        enemy = EnemyState(
            name="奥术巨魔",
            hp=50,
            max_hp=50,
            shield=0,
            actions=1,
            bonus_actions=1,
            max_actions=1,
            max_bonus_actions=1,
            intent_a_type="attack",
            intent_a_val=10,
            intent_a_desc="攻击 (造成 10 伤害)",
            intent_ba_type="defend",
            intent_ba_val=5,
            intent_ba_desc="防御 (获得 5 护盾)"
        )
        player = PlayerState(hp=45, max_hp=45, shield=0, gold=10, stage=1)
        run = GameRun(user_id="test_user", node_type="battle", player=player, enemies=[enemy])
        engine._sync_enemy_intents(enemy)
        self.assertEqual(enemy.intent_a_type, "attack")
        self.assertEqual(enemy.intent_ba_type, "defend")
        enemy.actions = 0
        engine._sync_enemy_intents(enemy)
        self.assertEqual(enemy.intent_a_type, "")
        self.assertIn("已取消", enemy.intent_a_desc)
        self.assertEqual(enemy.intent_ba_type, "defend")
        enemy.bonus_actions = 0
        engine._sync_enemy_intents(enemy)
        self.assertEqual(enemy.intent_ba_type, "")
        self.assertIn("已取消", enemy.intent_ba_desc)
        enemy.actions = 1
        enemy.bonus_actions = 1
        enemy.intent_a_type = "attack"
        enemy.intent_a_desc = "攻击 (造成 10 伤害)"
        enemy.intent_ba_type = "defend"
        enemy.intent_ba_desc = "防御 (获得 5 护盾)"
        engine._add_buff_to(enemy, "stun", "眩晕", "无法行动", 1)
        self.assertEqual(enemy.actions, 0)
        self.assertEqual(enemy.bonus_actions, 0)
        self.assertEqual(enemy.intent_a_type, "")
        self.assertIn("眩晕", enemy.intent_a_desc)
        self.assertEqual(enemy.intent_ba_type, "")
        enemy.buffs.clear()
        enemy.actions = 1
        enemy.bonus_actions = 1
        enemy.intent_a_type = "attack"
        enemy.intent_a_val = 10
        enemy.intent_a_desc = "攻击 (造成 10 伤害)"
        enemy.intent_ba_type = "defend"
        enemy.intent_ba_val=5
        enemy.intent_ba_desc = "防御 (获得 5 护盾)"
        enemy.intent_type = "old_temp_type"
        enemy.intent_val = 999
        engine._enemy_turn(run)
        self.assertEqual(enemy.intent_type, "old_temp_type")
        self.assertEqual(enemy.intent_val, 999)

    def test_echo_replay_message_compression(self):
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
            stage=2,
            deck=["fire_bolt"],
            hand=["fire_bolt"],
            actions=2,
            bonus_actions=1
        )
        enemy = EnemyState("测试敌人", 500, 500, 0)
        run = GameRun(
            user_id="test_compression_user",
            node_type="battle",
            player=player,
            enemies=[enemy]
        )
        card = ALL_CARDS["fire_bolt"]
        old_replay = getattr(card, "replay", 0)
        card.replay = 12
        try:
            res = engine.play_card(run, 1)
            self.assertIn("x 12次", res)
            self.assertNotIn("[重放触发]", res)
            self.assertEqual(enemy.hp, 500 - 3 * 13)
        finally:
            card.replay = old_replay

    def test_unyielding_buff(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return None
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(hp=100, max_hp=100, shield=0, gold=100, stage=25)
        run = GameRun(user_id="test_user", node_type="battle", player=player)
        engine._init_battle_node(run, "boss")
        
        corrupted_heart = None
        for enemy in run.enemies:
            if enemy.name == "腐化之心":
                corrupted_heart = enemy
                break
        
        if corrupted_heart:
            self.assertEqual(corrupted_heart.max_hp, 200)
            self.assertEqual(corrupted_heart.hp, 200)
            unyielding_buff = next((b for b in corrupted_heart.buffs if b.id == "unyielding"), None)
            self.assertIsNotNone(unyielding_buff)
            self.assertEqual(unyielding_buff.stacks, 40)

        enemy = EnemyState("测试敌人", 200, 200, 0)
        from game.models.state import BuffState
        enemy.buffs.append(BuffState("unyielding", "坚不可摧", 40))
        run.enemies = [enemy]

        engine._damage_target(run, "e1", 30, damage_type="fire")
        self.assertEqual(enemy.hp, 170)
        
        engine._damage_target(run, "e1", 20, damage_type="fire")
        self.assertEqual(enemy.hp, 160)
        
        engine._damage_target(run, "e1", 15, damage_type="fire")
        self.assertEqual(enemy.hp, 160)

        engine._damage_target(run, "e1", 10, damage_type="true")
        self.assertEqual(enemy.hp, 150)

        from game.models.events import TurnEndEvent
        evt = TurnEndEvent(run=run, is_player=False)
        engine.event_bus.dispatch(evt)

        engine._damage_target(run, "e1", 30, damage_type="fire")
        self.assertEqual(enemy.hp, 120)

    def test_time_ravage_vulnerable_mechanism(self):
        class DummySaveManager:
            def save_save(self, user_id, run): pass
            def load_stats(self, user_id): return None
        engine = BattleEngine(DummySaveManager())
        player = PlayerState(hp=80, max_hp=80, shield=0, gold=100, stage=1)
        enemy = EnemyState("测试地精", 50, 50, 0)
        run = GameRun(user_id="test_time_ravage", node_type="battle", player=player, enemies=[enemy])
        engine._add_buff_to(enemy, "vulnerable", "易伤", "受到的所有类型伤害翻倍", 2)
        self.assertTrue(any(b.id == "vulnerable" for b in enemy.buffs))
        engine.combat_resolver.damage_target(run, "e1", 10, source="p0", damage_type="fire")
        self.assertEqual(enemy.hp, 30)
        from game.models.events import TurnEndEvent
        evt_end = TurnEndEvent(run, is_player=False)
        engine.event_bus.dispatch(evt_end)
        buff = next(b for b in enemy.buffs if b.id == "vulnerable")
        self.assertEqual(buff.stacks, 1)
        engine.event_bus.dispatch(evt_end)
        self.assertFalse(any(b.id == "vulnerable" for b in enemy.buffs))

    def test_monster_weak_and_queue_deck(self):
        class DummySaveManager:
            def __init__(self):
                self.saves = {}
                self.stats = {}
            def save_save(self, user_id, run):
                self.saves[user_id] = run
            def load_save(self, user_id):
                return self.saves.get(user_id)
            def load_stats(self, user_id):
                return self.stats.get(user_id)
        dummy_save = DummySaveManager()
        engine = BattleEngine(dummy_save)
        player = PlayerState(hp=80, max_hp=80, shield=0, gold=100, stage=1)
        player.deck = ["strike", "strike"]
        enemy = EnemyState("测试地精", 50, 50, 0)
        run = GameRun(user_id="test_weak", node_type="battle", player=player, enemies=[enemy])
        engine._add_buff_to(enemy, "weak", "虚弱", "造成的伤害减少 50%", 1)
        run.node_data["current_acting_enemy_idx"] = 0
        engine.combat_resolver.damage_target(run, "p0", 10, source="enemy:测试地精", damage_type="bludgeoning")
        self.assertEqual(player.hp, 75)
        enemy.buffs = []
        engine._add_buff_to(enemy, "strength", "力量", "物理伤害增加 3 点", 3)
        engine.combat_resolver.damage_target(run, "p0", 10, source="enemy:测试地精", damage_type="bludgeoning")
        self.assertEqual(player.hp, 62)
        if "current_acting_enemy_idx" in run.node_data:
            del run.node_data["current_acting_enemy_idx"]
        from game.core.cli_router import CLIRouter
        router = CLIRouter(dummy_save, engine)
        router.save_manager.save_save("test_weak", run)
        results = []
        router._execute_queue("test_weak", run, "[deck]", results)
        self.assertTrue(any("当前拥有的卡组" in r for r in results))

    def test_weak_changes_intent_display(self):
        from game.models.state import EnemyIntentState
        from game.renderer.battle import render_battle
        player = PlayerState(hp=80, max_hp=80, shield=0, gold=100, stage=1)
        enemy = EnemyState("测试地精", 50, 50, 0)
        enemy.buffs = []
        enemy.intents = [EnemyIntentState(type="attack", val=10, desc="攻击 (造成 10 点伤害)")]
        run = GameRun(user_id="test_display", node_type="battle", player=player, enemies=[enemy])
        res1 = render_battle(run)
        self.assertIn("造成 10 点伤害", res1)
        from game.core.battle_engine import BattleEngine
        class DummySaveManager:
            def save_save(self, user_id, run): pass
            def load_stats(self, user_id): return None
        engine = BattleEngine(DummySaveManager())
        engine._add_buff_to(enemy, "weak", "虚弱", "造成的伤害减少 50%", 1)
        res2 = render_battle(run)
        self.assertIn("造成 5 点伤害", res2)

    def test_p_comma_rendering_flow(self):
        class DummySaveManager:
            def __init__(self):
                self.saves = {}
                self.stats = {}
            def save_save(self, user_id, run):
                self.saves[user_id] = run
            def delete_save(self, user_id):
                self.saves.pop(user_id, None)
            def load_save(self, user_id):
                return self.saves.get(user_id)
            def load_stats(self, user_id):
                class DummyStats:
                    selected_class = "战士"
                return DummyStats()
        dummy_save = DummySaveManager()
        engine = BattleEngine(dummy_save)
        player = PlayerState(hp=80, max_hp=80, shield=0, gold=100, stage=1)
        player.deck = ["strike", "strike"]
        from game.models.state import ensure_card_state
        player.hand = [ensure_card_state("adrenaline"), ensure_card_state("get_ready")]
        player.actions = 2
        player.bonus_actions = 2
        enemy = EnemyState("邪教徒咔咔 A", 50, 50, 0)
        run = GameRun(user_id="test_render_p_comma", node_type="battle", player=player, enemies=[enemy])
        dummy_save.save_save("test_render_p_comma", run)
        from game.core.cli_router import CLIRouter
        router = CLIRouter(dummy_save, engine)
        res_list = list(router.handle_command("test_render_p_comma", ["p", "1, 2"]))
        res_combined = "\n".join(res_list)
        self.assertEqual(res_combined.count("⚔️ 【第 1 关"), 1)
