import asyncio
import random
import tempfile
import unittest

from game.core.inventory.relic_service import grant_relic
from game.models.state import CardState, EnemyState
from game.test.core.base import CorePlugin, move_to_room, run_command
from server.snapshot import build_snapshot


class TestCountingRelics(unittest.TestCase):
    def setUp(self):
        random.seed(2026)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, cmd, uid="relic_tester"):
        return asyncio.run(run_command(self.plugin, cmd, sender_id=uid))

    def _start_warrior(self, uid="relic_tester"):
        self.run_cmd("class warrior", uid)
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        return self.plugin.save_manager.load_save(uid)

    def test_pen_nib_counting_double_damage_and_cross_battle_persistence(self):
        uid = "pen_nib_user"
        self._start_warrior(uid)
        _, run = move_to_room(self.plugin, uid, ("battle", "normal"))
        grant_relic(run.player, "pen_nib")
        run.player.relics = ["pen_nib"]
        run.player.hand = [
            CardState(id="warrior_defend"),
            CardState(id="warrior_strike"),
            CardState(id="warrior_strike"),
            CardState(id="warrior_strike"),
            CardState(id="warrior_strike"),
            CardState(id="warrior_strike"),
        ]
        run.player.actions = 10
        run.player.buffs = []
        run.player.persistent_buffs = []
        run.player.hp = 100
        run.enemies = [EnemyState(name="测试训练假人", hp=999, max_hp=999, shield=0, actions=1, bonus_actions=0, max_actions=1, max_bonus_actions=0)]
        self.plugin.engine.battle_engine.enemy_controller.roll_enemy_intent(run)
        self.plugin.save_manager.save_save(uid, run)

        battle_view = self.run_cmd("r", uid)
        self.assertIn("铅笔尖(0/5)", battle_view)
        snap = build_snapshot(run, self.plugin.save_manager.load_stats(uid))
        self.assertEqual(snap["player"]["relics"][0]["counter"], 0)
        self.assertEqual(snap["player"]["relics"][0]["counter_max"], 5)

        self.run_cmd("p 1", uid)
        after_skill = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after_skill.player.relic_counters["pen_nib"], 0)

        for step in range(1, 6):
            before_hp = self.plugin.save_manager.load_save(uid).enemies[0].hp
            self.run_cmd("p 1 e1", uid)
            after_atk = self.plugin.save_manager.load_save(uid)
            self.assertEqual(before_hp - after_atk.enemies[0].hp, 6)
            self.assertEqual(after_atk.player.relic_counters["pen_nib"], step)

        armed_view = self.run_cmd("r", uid)
        self.assertIn("铅笔尖(5/5)", armed_view)

        _, win_run = move_to_room(self.plugin, uid, ("battle", "normal"))
        self.assertEqual(win_run.player.relic_counters["pen_nib"], 5)
        win_run.enemies = [EnemyState(name="测试训练假人", hp=5, max_hp=5, shield=0, actions=1, bonus_actions=0, max_actions=1, max_bonus_actions=0)]
        win_run.player.hand = [CardState(id="warrior_strike")]
        win_run.player.actions = 2
        self.plugin.save_manager.save_save(uid, win_run)

        win_res = self.run_cmd("p 1 e1", uid)
        self.assertIn("铅笔尖", win_res)
        self.assertIn("胜利", win_res)
        after_win = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after_win.player.relic_counters["pen_nib"], 0)
        after_win.node_data["items"] = []
        self.plugin.save_manager.save_save(uid, after_win)
        self.run_cmd("leave", uid)

        map_view = self.run_cmd("map", uid)
        self.assertIn("铅笔尖(0/5)", map_view)

        _, run2 = move_to_room(self.plugin, uid, ("battle", "elite"))
        run2.player.relic_counters["pen_nib"] = 5
        run2.player.buffs = []
        run2.player.persistent_buffs = []
        run2.player.hand = [
            CardState(id="warrior_strike"),
            CardState(id="warrior_strike"),
        ]
        run2.player.actions = 5
        run2.enemies = [EnemyState(name="测试训练假人", hp=500, max_hp=500, shield=0, actions=1, bonus_actions=0, max_actions=1, max_bonus_actions=0)]
        self.plugin.save_manager.save_save(uid, run2)

        res_double = self.run_cmd("p 1 e1", uid)
        self.assertIn("铅笔尖", res_double)
        after_double = self.plugin.save_manager.load_save(uid)
        self.assertEqual(500 - after_double.enemies[0].hp, 12)
        self.assertEqual(after_double.player.relic_counters["pen_nib"], 0)

        self.run_cmd("p 1 e1", uid)
        after_normal = self.plugin.save_manager.load_save(uid)
        self.assertEqual(500 - after_normal.enemies[0].hp, 18)
        self.assertEqual(after_normal.player.relic_counters["pen_nib"], 1)

    def test_prayer_wheel_turn_counter_and_action_bonus(self):
        uid = "prayer_wheel_user"
        self._start_warrior(uid)
        _, run = move_to_room(self.plugin, uid, ("battle", "normal"))
        grant_relic(run.player, "prayer_wheel")
        run.player.relics = ["prayer_wheel"]
        run.player.hp = 200
        run.player.max_hp = 200
        run.enemies = [EnemyState(name="测试训练假人", hp=999, max_hp=999, shield=0, actions=1, bonus_actions=0, max_actions=1, max_bonus_actions=0)]
        self.plugin.engine.battle_engine.enemy_controller.roll_enemy_intent(run)
        self.plugin.save_manager.save_save(uid, run)

        view1 = self.run_cmd("r", uid)
        self.assertIn("转经轮(0/3)", view1)
        self.assertEqual(run.player.actions, 2)

        self.run_cmd("e", uid)
        t2 = self.plugin.save_manager.load_save(uid)
        self.assertEqual(t2.player.relic_counters["prayer_wheel"], 1)
        self.assertEqual(t2.player.actions, 2)

        self.run_cmd("e", uid)
        t3 = self.plugin.save_manager.load_save(uid)
        self.assertEqual(t3.player.relic_counters["prayer_wheel"], 2)
        self.assertEqual(t3.player.actions, 2)

        res_t4 = self.run_cmd("e", uid)
        self.assertIn("转经轮", res_t4)
        t4 = self.plugin.save_manager.load_save(uid)
        self.assertEqual(t4.player.actions, 3)
        self.assertEqual(t4.player.relic_counters["prayer_wheel"], 0)

        for _ in range(3):
            cur = self.plugin.save_manager.load_save(uid)
            cur.player.hp = 200
            self.plugin.save_manager.save_save(uid, cur)
            self.run_cmd("e", uid)
        t7 = self.plugin.save_manager.load_save(uid)
        self.assertEqual(t7.player.actions, 3)
        self.assertEqual(t7.player.relic_counters["prayer_wheel"], 0)

    def test_nail_of_heaven_counter_negation_confusion_and_tremor(self):
        uid = "nail_user"
        self._start_warrior(uid)
        _, run = move_to_room(self.plugin, uid, ("battle", "normal"))
        grant_relic(run.player, "nail_of_heaven")
        run.player.relics = ["nail_of_heaven"]
        run.player.buffs = []
        run.player.persistent_buffs = []
        run.player.hp = 200
        run.player.max_hp = 200
        run.enemies = [EnemyState(name="测试训练假人", hp=99999, max_hp=99999, shield=0, actions=1, bonus_actions=0, max_actions=1, max_bonus_actions=0)]
        run.node_data["test_dummy_turn"] = 1
        self.plugin.engine.battle_engine.enemy_controller.roll_enemy_intent(run)
        self.plugin.save_manager.save_save(uid, run)

        view = self.run_cmd("r", uid)
        self.assertIn("天之钉(5/5)", view)

        self.run_cmd("e", uid)
        after_t1 = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after_t1.player.relic_counters["nail_of_heaven"], 4)

        self.run_cmd("e", uid)
        after_t2 = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after_t2.player.relic_counters["nail_of_heaven"], 4)

        for _ in range(7):
            cur = self.plugin.save_manager.load_save(uid)
            cur.player.hp = 200
            self.plugin.save_manager.save_save(uid, cur)
            self.run_cmd("e", uid)

        armed = self.plugin.save_manager.load_save(uid)
        self.assertEqual(armed.player.relic_counters["nail_of_heaven"], 0)
        armed_view = self.run_cmd("r", uid)
        self.assertIn("天之钉(0/5)", armed_view)

        armed.player.hp = 150
        armed.player.shield = 5
        self.run_cmd("e", uid)
        armed_t11 = self.plugin.save_manager.load_save(uid)
        armed_t11.player.hp = 150
        armed_t11.player.shield = 5
        self.plugin.save_manager.save_save(uid, armed_t11)

        trigger_res = self.run_cmd("e", uid)
        self.assertIn("天之钉", trigger_res)
        self.assertIn("混乱", trigger_res)
        self.assertIn("震颤", trigger_res)

        after_trig = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after_trig.player.hp, 150)
        self.assertEqual(after_trig.player.shield, 2)
        self.assertEqual(after_trig.player.relic_counters["nail_of_heaven"], 5)
        enemy = after_trig.enemies[0]
        self.assertTrue(any(b.id == "confusion" and b.stacks == 1 for b in enemy.buffs))
        self.assertTrue(any(b.id == "tremor" and b.stacks == 1 for b in enemy.buffs))

        after_trig.player.hand = [CardState(id="warrior_strike")]
        after_trig.player.actions = 2
        enemy_hp_before = enemy.hp
        enemy_shield_before = enemy.shield
        self.plugin.save_manager.save_save(uid, after_trig)

        atk_res = self.run_cmd("p 1 e1", uid)
        self.assertIn("震颤", atk_res)
        after_atk = self.plugin.save_manager.load_save(uid)
        total_dmg = (enemy_hp_before - after_atk.enemies[0].hp) + (enemy_shield_before - after_atk.enemies[0].shield)
        self.assertEqual(total_dmg, 10)
        self.run_cmd("e", uid)
        after_defend = self.plugin.save_manager.load_save(uid)
        self.assertEqual(after_defend.enemies[0].shield, 5)
        self.assertFalse(any(b.id == "confusion" for b in after_defend.enemies[0].buffs))
        self.assertFalse(any(b.id == "tremor" for b in after_defend.enemies[0].buffs))

    def test_nail_of_heaven_ignores_small_hits_caps_one_per_turn_and_confusion_recoil(self):
        uid_small = "nail_small_user"
        self.run_cmd("class warrior", uid_small)
        self.run_cmd("主城", uid_small)
        self.run_cmd("home", uid_small)
        self.run_cmd("up", uid_small)
        self.run_cmd("talk NoobSlayer99", uid_small)
        self.run_cmd("2", uid_small)
        run_small = self.plugin.save_manager.load_save(uid_small)
        grant_relic(run_small.player, "nail_of_heaven")
        run_small.player.relics = ["nail_of_heaven"]
        run_small.player.hp = 200
        run_small.player.max_hp = 200
        self.plugin.save_manager.save_save(uid_small, run_small)

        self.run_cmd("e", uid_small)
        after_small = self.plugin.save_manager.load_save(uid_small)
        self.assertEqual(after_small.player.relic_counters["nail_of_heaven"], 5)

        uid_cap = "nail_cap_user"
        self._start_warrior(uid_cap)
        _, run_cap = move_to_room(self.plugin, uid_cap, ("battle", "normal"))
        grant_relic(run_cap.player, "nail_of_heaven")
        run_cap.player.relics = ["nail_of_heaven"]
        run_cap.player.hp = 200
        run_cap.player.max_hp = 200
        e1 = EnemyState(name="测试训练假人", hp=99999, max_hp=99999, shield=0, actions=1, bonus_actions=0, max_actions=1, max_bonus_actions=0)
        e2 = EnemyState(name="测试训练假人", hp=99999, max_hp=99999, shield=0, actions=1, bonus_actions=0, max_actions=1, max_bonus_actions=0)
        run_cap.enemies = [e1, e2]
        run_cap.node_data["test_dummy_turn"] = 1
        self.plugin.engine.battle_engine.enemy_controller.roll_enemy_intent(run_cap)
        self.plugin.save_manager.save_save(uid_cap, run_cap)

        self.run_cmd("e", uid_cap)
        after_two_hits = self.plugin.save_manager.load_save(uid_cap)
        self.assertEqual(after_two_hits.player.relic_counters["nail_of_heaven"], 4)

        run_conf = self.plugin.save_manager.load_save(uid_cap)
        run_conf.player.relic_counters["nail_of_heaven"] = 1
        run_conf.enemies = [run_conf.enemies[0]]
        run_conf.node_data["test_dummy_turn"] = 1
        self.plugin.engine.battle_engine.enemy_controller.roll_enemy_intent(run_conf)
        self.plugin.save_manager.save_save(uid_cap, run_conf)

        self.run_cmd("e", uid_cap)
        run_armed = self.plugin.save_manager.load_save(uid_cap)
        self.assertEqual(run_armed.player.relic_counters["nail_of_heaven"], 0)
        run_armed.node_data["test_dummy_turn"] = 1
        self.plugin.engine.battle_engine.enemy_controller.roll_enemy_intent(run_armed)
        self.plugin.save_manager.save_save(uid_cap, run_armed)

        self.run_cmd("e", uid_cap)
        run_after_negate = self.plugin.save_manager.load_save(uid_cap)
        self.assertTrue(any(b.id == "confusion" for b in run_after_negate.enemies[0].buffs))
        run_after_negate.node_data["test_dummy_turn"] = 1
        self.plugin.engine.battle_engine.enemy_controller.roll_enemy_intent(run_after_negate)
        self.plugin.save_manager.save_save(uid_cap, run_after_negate)

        before_conf_hit = self.plugin.save_manager.load_save(uid_cap)
        hp_p_before = before_conf_hit.player.hp
        hp_e_before = before_conf_hit.enemies[0].hp
        shield_p_before = before_conf_hit.player.shield
        conf_res = self.run_cmd("e", uid_cap)
        self.assertIn("混乱", conf_res)
        after_conf_hit = self.plugin.save_manager.load_save(uid_cap)
        effective_dmg_taken = (hp_p_before - after_conf_hit.player.hp) + (shield_p_before // 2 - after_conf_hit.player.shield)
        self.assertEqual(effective_dmg_taken, 7)
        self.assertEqual(hp_e_before - after_conf_hit.enemies[0].hp, 5)
