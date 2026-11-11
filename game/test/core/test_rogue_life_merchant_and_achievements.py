import asyncio
import json
import math
import os
import tempfile
import unittest

from game.core.achievement_service import AchievementService
from game.core.battle_engine import BattleEngine
from game.core.coop_engine import CoopEngine
from game.core.life_merchant import calc_life_merchant_price
from game.data.achievement_data import ACHIEVEMENT_ALL_VIEW_PRICE, ACHIEVEMENTS_CONFIG
from game.data.map_config import MapConfig
from game.models.state import EnemyIntentState, EnemyState, GameRun, PlayerState, UserStats, ensure_card_state
from game.renderer.map import render_map_select
from game.renderer.menu import render_shop
from game.test.core.base import CorePlugin, run_command


class TestRogueLifeMerchantAndAchievements(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.sm = self.plugin.save_manager
        self.uid = "test_lm_user"

    def tearDown(self):
        self.tmp.cleanup()

    def _run_cmd(self, cmd, uid=None):
        return asyncio.run(run_command(self.plugin, cmd, uid or self.uid))

    def test_start_ancient_and_cafe_ancient_no_forced_trash_mountain(self):
        trash_appearances = 0
        for i in range(60):
            uid = f"ancient_u_{i}"
            res = self._run_cmd("start", uid=uid)
            self.assertIn("第 1 关", res)
            run = self.sm.load_save(uid)
            options = run.node_data.get("options", [])
            self.assertEqual(len(options), 3)
            if any(opt.get("relic") == "trash_mountain" for opt in options):
                trash_appearances += 1
        self.assertGreater(trash_appearances, 0)
        self.assertLess(trash_appearances, 60)

        cafe_trash = 0
        for i in range(30):
            run = GameRun(
                user_id=self.uid,
                node_type="cafe",
                player=PlayerState(hp=45, max_hp=45, shield=0, gold=50, stage=13),
                enemies=[],
            )
            self.plugin.engine.map_engine._init_ancient_node(run)
            opts = run.node_data.get("options", [])
            self.assertEqual(len(opts), 3)
            if any(opt.get("relic") == "trash_mountain" for opt in opts):
                cafe_trash += 1
        self.assertEqual(cafe_trash, 0)

    def test_map_size_expanded_and_life_merchant_generation(self):
        seen_widths = set()
        seen_merchants = []
        for _ in range(40):
            run = GameRun(
                user_id=self.uid,
                node_type="map_select",
                player=PlayerState(hp=45, max_hp=45, shield=0, gold=20, stage=2),
                enemies=[],
            )
            me = self.plugin.engine.map_engine
            count = 0
            me._generate_map_network(run, 2, 12)
            for s in range(2, 12):
                layer = run.map_data["nodes"][str(s)]
                seen_widths.add(len(layer))
                self.assertIn(len(layer), (3, 4, 5))
                for nd in layer:
                    self.assertGreaterEqual(len(nd["next"]), 1)
                    if len(run.map_data["nodes"][str(s + 1)]) >= 2:
                        self.assertGreaterEqual(len(nd["next"]), 2)
                        self.assertLessEqual(len(nd["next"]), 3)
            for s_str, layer in run.map_data["nodes"].items():
                for nd in layer:
                    if nd["type"] == "life_merchant":
                        count += 1
                        self.assertTrue(4 <= int(s_str) <= 11)
            me._generate_map_network(run, 14, 25)
            for s_str, layer in run.map_data["nodes"].items():
                for nd in layer:
                    if nd["type"] == "life_merchant":
                        count += 1
                        self.assertTrue(15 <= int(s_str) <= 24)
            me._generate_map_network(run, 27, 32)
            for s_str, layer in run.map_data["nodes"].items():
                for nd in layer:
                    if nd["type"] == "life_merchant":
                        count += 1
                        self.assertTrue(27 <= int(s_str) <= 30)
            self.assertGreaterEqual(count, 1)
            self.assertLessEqual(count, 2)
            seen_merchants.append(count)

        self.assertEqual(seen_widths, {3, 4, 5})
        self.assertTrue(any(c == 2 for c in seen_merchants))

        run_preview = GameRun(
            user_id=self.uid,
            node_type="map_select",
            player=PlayerState(hp=45, max_hp=45, shield=0, gold=20, stage=22),
            enemies=[],
        )
        self.plugin.engine.map_engine._generate_map_network(run_preview, 14, 25)
        self.plugin.engine.map_engine._build_map_options(run_preview)
        rendered = render_map_select(run_preview)
        self.assertIn("第 25 层", rendered)

    def test_life_merchant_dynamic_pricing_min_hp_one_and_shou_hui_bonus(self):
        self._run_cmd("start")
        run = self.sm.load_save(self.uid)
        run.player.stage = 6
        run.player.max_hp = 5
        run.player.hp = 5
        run.player.deck = [ensure_card_state("fire_bolt"), ensure_card_state("shield")]
        run.node_type = "map_select"
        run.map_data = {
            "nodes": {"6": [{"id": "6_0", "type": "life_merchant", "next": ["7_0"]}], "7": [{"id": "7_0", "type": "battle", "next": []}]},
            "current_node_id": None,
        }
        self.plugin.engine.map_engine._build_map_options(run)
        self.sm.save_save(self.uid, run)

        enter_res = self._run_cmd("1")
        self.assertIn("生命商人", enter_res)

        run = self.sm.load_save(self.uid)
        run.node_data["items"] = [
            {"type": "card", "card_id": "neutral_fusion", "ratio": 0.15, "sold": False},
            {"type": "relic", "relic_id": "trash_mountain", "ratio": 0.15, "sold": False},
            {"type": "relic", "relic_id": "blood_covenant", "ratio": 0.15, "sold": False},
            {"type": "relic", "relic_id": "sanguine_crown", "ratio": 0.22, "sold": False},
            {"type": "life_upgrade", "ratio": 0.12, "count": 2, "sold": False},
            {"type": "card", "card_id": "curse_shou_hui", "fixed_price": -5, "sold": False},
            {"type": "gem", "gem_id": "gem_dmg_add_2", "ratio": 0.10, "sold": False},
            {"type": "leave", "fixed_price": 0, "sold": False},
        ]
        self.sm.save_save(self.uid, run)

        res1 = self._run_cmd("1")
        self.assertIn("聚变", res1)
        run = self.sm.load_save(self.uid)
        self.assertEqual(run.player.max_hp, 4)
        self.assertTrue(any(ensure_card_state(c).id == "neutral_fusion" for c in run.player.deck))

        self._run_cmd("2")
        self._run_cmd("3")
        res4 = self._run_cmd("4")
        self.assertIn("一线生机", res4)

        run = self.sm.load_save(self.uid)
        self.assertEqual(run.player.max_hp, 1)

        res_block = self._run_cmd("5")
        self.assertIn("至少保留 1 点", res_block)

        res_bonus = self._run_cmd("6")
        self.assertIn("寿回✋😡✋", res_bonus)
        self.assertIn("血契大主顾", res_bonus)
        run = self.sm.load_save(self.uid)
        self.assertEqual(run.player.max_hp, 6)
        self.assertTrue(any(ensure_card_state(c).id == "curse_shou_hui" for c in run.player.deck))

        res_upg = self._run_cmd("5")
        self.assertIn("血肉洗礼完成", res_upg)
        run = self.sm.load_save(self.uid)
        self.assertEqual(run.player.max_hp, 5)
        self.assertGreaterEqual(sum(1 for c in run.player.deck if ensure_card_state(c).upgraded), 2)

        res_gem = self._run_cmd("7")
        self.assertIn("获得了宝石", res_gem)
        run = self.sm.load_save(self.uid)
        self.assertEqual(run.node_type, "gem_insert")
        self.assertEqual(run.player.max_hp, 4)
        res_gem_pick = self._run_cmd("c 2")
        self.assertIn("增幅红宝石", res_gem_pick)
        run = self.sm.load_save(self.uid)
        self.assertEqual(run.node_type, "life_merchant")
        self.assertTrue(any("gem_dmg_add_2" in ensure_card_state(c).gems for c in run.player.deck))

        res_leave = self._run_cmd("8")
        self.assertIn("离开了摊位", res_leave)
        run = self.sm.load_save(self.uid)
        self.assertEqual(run.player.stage, 7)

    def test_fusion_shou_lai_shou_hui_tau_and_relics_in_battle(self):
        self._run_cmd("start")
        run = self.sm.load_save(self.uid)
        run.node_type = "battle"
        run.node_data = {"difficulty": "normal", "turn_count": 1}
        run.player.max_hp = 40
        run.player.hp = 40
        run.player.actions = 5
        run.player.bonus_actions = 2
        run.player.relics = ["heavy_armor", "ancient_eye", "sanguine_crown", "immortal_pact", "blood_covenant"]
        run.player.hand = [
            ensure_card_state("neutral_fusion"),
            ensure_card_state("neutral_fusion"),
            ensure_card_state("shield_guard"),
            ensure_card_state("find_familiar"),
            ensure_card_state("neutral_tau"),
            ensure_card_state("neutral_shou_lai"),
            ensure_card_state("curse_shou_hui"),
        ]
        run.player.deck = list(run.player.hand)
        run.enemies = [EnemyState("测试训练假人", 99999, 99999, 0, max_actions=1)]
        self.sm.save_save(self.uid, run)

        res_fus1 = self._run_cmd("p 1")
        self.assertIn("核聚变过载", res_fus1)
        run = self.sm.load_save(self.uid)
        self.assertEqual(run.player.max_hp, 28)
        self.assertGreaterEqual(run.player.actions, 10)

        self._run_cmd("p 1")
        self._run_cmd("p 1")
        self._run_cmd("p 1")
        run = self.sm.load_save(self.uid)
        for m in run.player.minions.values():
            m.actions = 0
            m.bonus_actions = 0
        self.sm.save_save(self.uid, run)

        res_tau = self._run_cmd("p 1")
        self.assertIn("Tau", res_tau)
        self.assertIn("Tau 协奏曲", res_tau)
        run = self.sm.load_save(self.uid)
        tau_minion = next(m for m in run.player.minions.values() if m.id == "neutral_tau")
        self.assertEqual(tau_minion.hp, 1)
        self.assertEqual(tau_minion.atk, 0)
        self.assertEqual(tau_minion.attack_actions, 0)
        self.assertGreater(run.player.shield, 0)

        res_shou_lai_self = self._run_cmd("p 1 p0")
        self.assertIn("不能选中你自己", res_shou_lai_self)

        hp_before = run.player.max_hp
        res_sl = self._run_cmd("p 1 e1")
        self.assertIn("寿来", res_sl)
        run = self.sm.load_save(self.uid)
        self.assertEqual(run.player.max_hp, hp_before + 6)
        self.assertEqual(run.enemies[0].max_hp, 99999 - 6)

        res_sh_empty = self._run_cmd("p 1")
        self.assertIn("因果律落空", res_sh_empty)

        run = self.sm.load_save(self.uid)
        run.player.max_hp = 1
        run.player.hp = 1
        run.player.hand = [ensure_card_state("neutral_fusion")]
        self.sm.save_save(self.uid, run)
        res_fus_block = self._run_cmd("p 1")
        self.assertIn("最大生命上限已降至 1 点", res_fus_block)

        run = self.sm.load_save(self.uid)
        run.player.shield = 0
        run.player.minions.clear()
        run.node_data["immortal_pact_used:" + run.uid_for(run.player)] = False
        e1 = EnemyState("测试训练假人", 99999, 99999, 10, max_actions=1)
        e1.intents = [EnemyIntentState(type="attack", val=10, desc="重击", cost_a=1, cost_ba=0)]
        self.plugin.engine.battle_engine._sync_enemy_intents(e1)
        e2 = EnemyState("测试训练假人2", 99999, 99999, 10, max_actions=1)
        e2.intents = [EnemyIntentState(type="attack", val=10, desc="重击", cost_a=1, cost_ba=0)]
        self.plugin.engine.battle_engine._sync_enemy_intents(e2)
        run.enemies = [e1, e2]
        self.sm.save_save(self.uid, run)
        res_revive = self._run_cmd("e")
        self.assertIn("永生契约", res_revive)
        self.assertIn("30", res_revive)
        run = self.sm.load_save(self.uid)
        self.assertIsNotNone(run)
        self.assertEqual(run.node_type, "battle")
        self.assertEqual(run.player.hp, 1)
        self.assertTrue(run.node_data.get("immortal_pact_used:" + run.uid_for(run.player)))

    def test_coop_shou_lai_pulls_shou_hui_only_if_in_deck_and_kills_below_five(self):
        u1, u2, u3 = "coop_a", "coop_b", "coop_c"
        p1 = PlayerState(hp=30, max_hp=30, shield=0, gold=0, stage=5, name="甲", hand=[ensure_card_state("neutral_shou_lai")], deck=[ensure_card_state("neutral_shou_lai")], actions=2, bonus_actions=2)
        p2 = PlayerState(hp=30, max_hp=30, shield=0, gold=0, stage=5, name="乙", hand=[], draw_pile=[ensure_card_state("curse_shou_hui")], deck=[ensure_card_state("curse_shou_hui")], actions=2, bonus_actions=2)
        p3 = PlayerState(hp=30, max_hp=30, shield=0, gold=0, stage=5, name="丙", hand=[], draw_pile=[], deck=[], actions=2, bonus_actions=2)
        run = GameRun(
            user_id=u1,
            node_type="battle",
            player=p1,
            enemies=[EnemyState("假人", 200, 200, 0)],
            coop_id="coop_sl",
            leader_id=u1,
            party_order=[u1, u2, u3],
            players={u1: p1, u2: p2, u3: p3},
            node_data={"turn_count": 1, "turn_ready": {u1: False, u2: False, u3: False}},
        )
        be = self.plugin.engine.battle_engine
        res_13 = be.play_card(run, 1, "a3")
        self.assertIn("寿来", res_13)
        self.assertEqual(len(p3.hand), 0)

        p1.hand.append(ensure_card_state("neutral_shou_lai"))
        res_12 = be.play_card(run, 1, "a2")
        self.assertIn("寿来", res_12)
        self.assertEqual(len(p2.hand), 1)
        self.assertEqual(ensure_card_state(p2.hand[0]).id, "curse_shou_hui")

        p1.max_hp = 4
        p1.hp = 4
        run.player = p2
        run.user_id = u2
        res_kill = be.play_card(run, 1, "a1")
        self.assertIn("直接抹杀", res_kill)
        self.assertTrue(p1.downed)
        stats_u2 = self.sm.load_stats(u2)
        self.assertIn("shou_hui_karma", stats_u2.unlocked_achievements)

    def test_achievements_migration_hide_all_view_and_shop_cleanup(self):
        stats = self.sm.load_stats(self.uid)
        stats.killed_icerainboww = True
        stats.yog_sothoth_kill_count = 1
        stats.yog_sothoth_challenge_count = 1
        stats.unlocked_subclasses = ["神秘物品"]
        stats.defeated_town_npcs = ["Gate_Guardian", "pppopipupu"]
        stats.gp = 1000
        self.sm.save_stats(self.uid, stats)

        shop_txt = render_shop(stats)
        self.assertNotIn("Icerainboww", shop_txt)
        self.assertNotIn("尤格-索托斯", shop_txt)

        res_achi = self._run_cmd("achi")
        self.assertIn("极寒终结", res_achi)
        self.assertIn("万物归一的终结", res_achi)
        self.assertIn("钓鱼佬的末日", res_achi)
        self.assertIn("深渊的奇珍", res_achi)
        self.assertIn("初入暗影", res_achi)

        expected_gp = (
            1000
            + ACHIEVEMENTS_CONFIG["town_challenger"]["gp_reward"]
            + ACHIEVEMENTS_CONFIG["act2_victory"]["gp_reward"]
            + ACHIEVEMENTS_CONFIG["boss_icerainboww"]["gp_reward"]
            + ACHIEVEMENTS_CONFIG["face_yog_sothoth"]["gp_reward"]
            + ACHIEVEMENTS_CONFIG["town_guard_defeated"]["gp_reward"]
            + ACHIEVEMENTS_CONFIG["boss_yog_sothoth"]["gp_reward"]
            + ACHIEVEMENTS_CONFIG["town_pppopipupu"]["gp_reward"]
            + ACHIEVEMENTS_CONFIG["mystery_collector"]["gp_reward"]
        )
        stats_after = self.sm.load_stats(self.uid)
        self.assertEqual(stats_after.gp, expected_gp)

        res_page2 = self._run_cmd("n")
        self.assertIn("第 2 /", res_page2)
        self.assertIn("？？？", res_page2)
        res_quit = self._run_cmd("q")
        self.assertIn("已退出阅读器", res_quit)

        res_filter = self._run_cmd("achi 传奇")
        self.assertIn("万物归一的终结", res_filter)
        self.assertIn("？？？", res_filter)
        self._run_cmd("q")

        res_prompt = self._run_cmd("achi 全览")
        self.assertIn("50000 GP", res_prompt)

        res_poor = self._run_cmd("achi 全览 confirm")
        self.assertIn("需要 50000 GP", res_poor)

        stats_rich = self.sm.load_stats(self.uid)
        stats_rich.gp = 60000
        self.sm.save_stats(self.uid, stats_rich)

        res_unlock = self._run_cmd("achi 全览 confirm")
        self.assertIn("永久开启【成就全览模式】", res_unlock)
        stats_unlocked = self.sm.load_stats(self.uid)
        self.assertEqual(stats_unlocked.gp, 60000 - ACHIEVEMENT_ALL_VIEW_PRICE)
        self.assertTrue(stats_unlocked.achievement_all_view)

        res_revealed = self._run_cmd("achi 传奇")
        self.assertIn("以彼之道", res_revealed)
        self.assertIn("核聚变过载", res_revealed)
        self.assertNotIn("？？？", res_revealed)

    def test_one_hp_boss_slayer_achievement_and_help_entry(self):
        help_res = self._run_cmd("help achi")
        self.assertIn("成就列表", help_res)

        self._run_cmd("start")
        run = self.sm.load_save(self.uid)
        run.node_type = "battle"
        run.player.stage = 12
        run.player.max_hp = 1
        run.player.hp = 1
        run.player.actions = 2
        run.player.hand = [ensure_card_state("fireball")]
        run.node_data = {"difficulty": "boss", "boss_name": "远古红龙"}
        run.enemies = [EnemyState("远古红龙", 5, 145, 0)]
        self.sm.save_save(self.uid, run)

        res_win = self._run_cmd("p 1 e1")
        self.assertIn("跨越深渊", res_win)
        self.assertIn("薄如蝉翼的奇迹", res_win)
        stats = self.sm.load_stats(self.uid)
        self.assertIn("one_hp_boss_slayer", stats.unlocked_achievements)
        self.assertIn("first_act_clear", stats.unlocked_achievements)


if __name__ == "__main__":
    unittest.main()
