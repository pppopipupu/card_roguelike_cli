import asyncio
import random
import tempfile
import unittest

from game.models.state import (
    BuffState,
    CardState,
    EnemyIntentState,
    EnemyState,
    GameRun,
    MinionState,
    PlayerState,
)
from game.test.core.base import CorePlugin, load_run, run_command


class TestBuffHooksAndModifiers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.random_state = random.getstate()
        random.seed(11)
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, command: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, command, uid))

    def _build_battle(
        self,
        uid: str,
        hand,
        enemies=None,
        actions: int = 10,
        bonus_actions: int = 5,
        buffs=None,
        minions=None,
        draw_pile=None,
        lex_kela: int = 0,
    ) -> GameRun:
        p = PlayerState(
            hp=100,
            max_hp=100,
            shield=0,
            gold=100,
            stage=1,
            deck=list(hand),
            hand=list(hand),
            draw_pile=list(draw_pile) if draw_pile is not None else [CardState(id="warrior_defend")] * 5,
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            actions=actions,
            bonus_actions=bonus_actions,
            buffs=list(buffs or []),
            minions=dict(minions or {}),
            lex_kela=lex_kela,
        )
        en = list(enemies) if enemies is not None else [EnemyState("测试训练假人", 500, 500, 0)]
        run = GameRun(user_id=uid, node_type="battle", player=p, enemies=en, node_data={})
        self.plugin.save_manager.save_save(uid, run)
        return run

    def test_strength_and_negative_strength_player_minion_enemy_and_render(self):
        uid = "str_mod_user"
        self._build_battle(
            uid,
            hand=[
                CardState(id="warrior_strike"),
                CardState(id="warrior_shield_bash"),
                CardState(id="strike_of_all"),
            ],
            buffs=[BuffState(id="strength", name="力量", stacks=5, desc="造成的伤害增加")],
        )
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 11)

        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 11 - 13)

        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 11 - 13 - 17)

        self._build_battle(
            uid,
            hand=[
                CardState(id="warrior_strike"),
                CardState(id="warrior_shield_bash"),
            ],
            buffs=[BuffState(id="strength", name="力量", stacks=-3, desc="造成的伤害增加")],
        )
        status_out = self.run_cmd("status", uid)
        self.assertIn("力量 -3", status_out)
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 3)
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 3 - 5)

        self._build_battle(
            uid,
            hand=[CardState(id="warrior_strike")],
            buffs=[BuffState(id="strength", name="力量", stacks=-10, desc="造成的伤害增加")],
        )
        zero_out = self.run_cmd("p 1 e1", uid)
        self.assertNotIn("-4", zero_out)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500)

        self._build_battle(
            uid,
            hand=[],
            minions={
                "1": MinionState(
                    id="m_pos",
                    name="强力步兵",
                    hp=10,
                    max_hp=10,
                    atk=5,
                    actions=1,
                    bonus_actions=0,
                    attack_actions=1,
                    buffs=[BuffState(id="strength", name="力量", stacks=4, desc="造成的伤害增加")],
                ),
                "2": MinionState(
                    id="m_neg",
                    name="虚弱步兵",
                    hp=10,
                    max_hp=10,
                    atk=5,
                    actions=1,
                    bonus_actions=0,
                    attack_actions=1,
                    buffs=[BuffState(id="strength", name="力量", stacks=-2, desc="造成的伤害增加")],
                ),
            },
        )
        self.run_cmd("m 1 a e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 9)
        self.run_cmd("m 2 a e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 9 - 3)

        goblin = EnemyState(
            name="地精突袭者",
            hp=100,
            max_hp=100,
            shield=0,
            actions=1,
            bonus_actions=0,
            max_actions=1,
            max_bonus_actions=0,
            intents=[EnemyIntentState(type="raid_stab", val=6, desc="造成 6 点穿刺伤害", cost_a=1, cost_ba=0)],
            buffs=[BuffState(id="strength", name="力量", stacks=5, desc="造成的伤害增加")],
        )
        self._build_battle(uid, hand=[], enemies=[goblin])
        self.run_cmd("e", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.player.hp, 100 - 11 - 2)

        goblin_neg = EnemyState(
            name="地精突袭者",
            hp=100,
            max_hp=100,
            shield=0,
            actions=1,
            bonus_actions=0,
            max_actions=1,
            max_bonus_actions=0,
            intents=[EnemyIntentState(type="raid_stab", val=6, desc="造成 6 点穿刺伤害", cost_a=1, cost_ba=0)],
            buffs=[],
        )
        self._build_battle(
            uid,
            hand=[CardState(id="ninja_beast_shout")],
            enemies=[goblin_neg],
            lex_kela=2,
        )
        self.run_cmd("p 1", uid)
        run = load_run(self.plugin, uid)
        str_buff = next((b for b in run.enemies[0].buffs if b.id == "strength"), None)
        self.assertIsNotNone(str_buff)
        assert str_buff is not None
        self.assertEqual(str_buff.stacks, -2)
        self.run_cmd("e", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.player.hp, 100 - 4 - 2)

    def test_strength_and_weak_apply_to_true_and_force_damage(self):
        uid = "all_type_mod_user"
        self._build_battle(
            uid,
            hand=[CardState(id="arcane_torrent")],
            actions=2,
            bonus_actions=0,
            buffs=[BuffState(id="strength", name="力量", stacks=3, desc="造成的伤害增加")],
        )
        out = self.run_cmd("p 1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 36)
        self.assertIn("4 点真实伤害", out)
        self.assertIn("5 点力场伤害", out)

        self._build_battle(
            uid,
            hand=[CardState(id="arcane_torrent")],
            actions=2,
            bonus_actions=0,
            buffs=[
                BuffState(id="strength", name="力量", stacks=2, desc="造成的伤害增加"),
                BuffState(id="weak", name="虚弱", stacks=1, desc="造成的伤害减少 25%"),
            ],
        )
        out = self.run_cmd("p 1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 20)
        self.assertIn("2 点真实伤害", out)
        self.assertIn("3 点力场伤害", out)

        self._build_battle(
            uid,
            hand=[CardState(id="arcane_torrent")],
            actions=2,
            bonus_actions=0,
            buffs=[BuffState(id="strength", name="力量", stacks=-1, desc="造成的伤害增加")],
        )
        out = self.run_cmd("p 1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 4)
        self.assertIn("1 点力场伤害", out)

    def test_weak_and_severe_weak_multipliers_and_turn_decay(self):
        uid = "weak_mod_user"
        self._build_battle(
            uid,
            hand=[CardState(id="bludgeon")],
            buffs=[BuffState(id="weak", name="虚弱", stacks=2, desc="造成的伤害减少 25%")],
        )
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 24)

        self._build_battle(
            uid,
            hand=[CardState(id="bludgeon")],
            buffs=[BuffState(id="severe_weak", name="重度虚弱", stacks=2, desc="造成的伤害减少 50%")],
        )
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 16)

        self._build_battle(
            uid,
            hand=[CardState(id="bludgeon")],
            buffs=[
                BuffState(id="weak", name="虚弱", stacks=2, desc="造成的伤害减少 25%"),
                BuffState(id="severe_weak", name="重度虚弱", stacks=2, desc="造成的伤害减少 50%"),
            ],
        )
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 12)

        self._build_battle(
            uid,
            hand=[CardState(id="bludgeon")],
            buffs=[
                BuffState(id="severe_weak", name="重度虚弱", stacks=2, desc="造成的伤害减少 50%"),
                BuffState(id="weak", name="虚弱", stacks=2, desc="造成的伤害减少 25%"),
                BuffState(id="strength", name="力量", stacks=8, desc="造成的伤害增加"),
            ],
        )
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 15)

        goblin = EnemyState(
            name="地精突袭者",
            hp=100,
            max_hp=100,
            shield=0,
            actions=1,
            bonus_actions=0,
            max_actions=1,
            max_bonus_actions=0,
            intents=[EnemyIntentState(type="raid_stab", val=16, desc="造成 16 点穿刺伤害", cost_a=1, cost_ba=0)],
            buffs=[
                BuffState(id="weak", name="虚弱", stacks=2, desc="造成的伤害减少 25%"),
                BuffState(id="severe_weak", name="重度虚弱", stacks=1, desc="造成的伤害减少 50%"),
            ],
        )
        self._build_battle(
            uid,
            hand=[],
            enemies=[goblin],
            buffs=[
                BuffState(id="weak", name="虚弱", stacks=2, desc="造成的伤害减少 25%"),
                BuffState(id="severe_weak", name="重度虚弱", stacks=1, desc="造成的伤害减少 50%"),
            ],
        )
        status_out = self.run_cmd("status", uid)
        self.assertIn("造成 6 点穿刺伤害", status_out)
        self.run_cmd("e", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.player.hp, 100 - 6 - 2)
        player_buff_map = {b.id: b.stacks for b in run.player.buffs}
        enemy_buff_map = {b.id: b.stacks for b in run.enemies[0].buffs}
        self.assertEqual(player_buff_map.get("weak"), 1)
        self.assertNotIn("severe_weak", player_buff_map)
        self.assertEqual(enemy_buff_map.get("weak"), 1)
        self.assertNotIn("severe_weak", enemy_buff_map)

    def test_split_to_ten_single_stack_gem_fallback_and_merged_debuffs(self):
        uid = "hook_fix_user"
        self._build_battle(
            uid,
            hand=[CardState(id="warrior_strike")],
            actions=0,
            bonus_actions=0,
            buffs=[BuffState(id="split_to_ten", name="一分为十", stacks=1, desc="一分为十")],
        )
        fail_out = self.run_cmd("p 1 e1", uid)
        self.assertIn("❌", fail_out)
        run = load_run(self.plugin, uid)
        self.assertTrue(any(b.id == "split_to_ten" and b.stacks == 1 for b in run.player.buffs))

        self._build_battle(
            uid,
            hand=[CardState(id="warrior_strike")],
            actions=2,
            bonus_actions=0,
            buffs=[BuffState(id="split_to_ten", name="一分为十", stacks=1, desc="一分为十")],
        )
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.enemies[0].hp, 500 - 66)
        self.assertFalse(any(b.id == "split_to_ten" for b in run.player.buffs))

        self._build_battle(
            uid,
            hand=[
                CardState(id="warrior_defend", gems=["gem_dmg_add_2"]),
                CardState(id="warrior_strike", gems=["gem_shield_add_3"]),
            ],
            actions=3,
            bonus_actions=3,
        )
        self.run_cmd("p 1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.player.shield, 5)
        self.assertEqual(run.enemies[0].hp, 500 - 2)
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.player.shield, 8)

        self._build_battle(
            uid,
            hand=[CardState(id="shrug_it_off")],
            actions=2,
            bonus_actions=2,
            buffs=[BuffState(id="tactical_focus", name="无法抽牌", stacks=1, desc="本回合无法再抽牌")],
            draw_pile=[CardState(id="warrior_strike"), CardState(id="warrior_strike")],
        )
        self.run_cmd("p 1", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(len(run.player.hand), 0)

        self._build_battle(
            uid,
            hand=[CardState(id="warrior_strike")],
            actions=2,
            bonus_actions=0,
            buffs=[BuffState(id="void_exhaustion", name="虚空耗竭", stacks=1, desc="强制消耗")],
        )
        self.run_cmd("p 1 e1", uid)
        run = load_run(self.plugin, uid)
        self.assertTrue(any(c.id == "warrior_strike" for c in run.player.exhaust_pile))
        self.assertFalse(any(c.id == "warrior_strike" for c in run.player.discard_pile))

        goblin = EnemyState(
            name="地精突袭者",
            hp=100,
            max_hp=100,
            shield=0,
            actions=1,
            bonus_actions=0,
            max_actions=1,
            max_bonus_actions=0,
            intents=[EnemyIntentState(type="raid_stab", val=12, desc="造成 12 点穿刺伤害", cost_a=1, cost_ba=0)],
            buffs=[BuffState(id="stun", name="眩晕", stacks=1, desc="无法行动")],
        )
        self._build_battle(uid, hand=[], enemies=[goblin])
        self.run_cmd("e", uid)
        run = load_run(self.plugin, uid)
        self.assertEqual(run.player.hp, 100)
        self.assertFalse(any(b.id == "stun" for b in run.enemies[0].buffs))


if __name__ == "__main__":
    unittest.main()
