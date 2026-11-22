import asyncio
import os
import random
import tempfile
import unittest

from game.data.world.outer_plane_config import NECRONOMICON_ITEM, OUTER_PLANE_ACTIVE_FLAG
from game.data.progression.starting_deck_config import CLASS_STARTING_CARDS
from game.data.world.world_social_config import WORLD_OUTER_PLANE, WORLD_SNOWFIELD, WORLD_TOWN
from game.data.world.yog_quest_config import YOG_INFO_FLAG, YOG_QUEST_FLAG, YOG_SIGIL_ITEM
from game.models.state import CardState
from game.test.core.base import CorePlugin, floor_of, load_run, run_command


class TestOpenWorldGhostAndChest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.random_state = random.getstate()
        random.seed(20261116)
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.alice = "ow_alice"
        self.bob = "ow_bob"

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def cmd(self, text: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, text, uid))

    def _prepare_open_world_player(
        self,
        uid: str,
        name: str,
        *,
        locked=None,
        bag=None,
        relics=None,
        deck=None,
    ):
        stats = self.plugin.save_manager.load_stats(uid)
        stats.player_name = name
        stats.player_handle = name
        stats.selected_class = "法师"
        stats.yog_sothoth_kill_count = 1
        stats.locked_cards = list(locked or [])
        stats.town_flags[YOG_INFO_FLAG] = True
        stats.town_flags[YOG_QUEST_FLAG] = "started"
        for item in (YOG_SIGIL_ITEM, NECRONOMICON_ITEM):
            if item not in stats.town_inventory:
                stats.town_inventory.append(item)
        if bag is not None:
            stats.open_world_bag = list(bag)
        if relics is not None:
            stats.open_world_relics = list(relics)
        if deck is not None:
            stats.open_world_deck = [CardState(c) if isinstance(c, str) else c for c in deck]
        self.plugin.save_manager.save_stats(uid, stats)
        self.cmd("主城", uid)

    def _win_active_battle(self, uid: str, max_turns: int = 30) -> str:
        last_out = ""
        for _ in range(max_turns):
            run = self.plugin.save_manager.load_save(uid)
            if run is None or run.node_type != "battle":
                return last_out
            played = False
            for idx in range(1, len(run.player.hand) + 1):
                res = self.cmd(f"p {idx} e1", uid)
                last_out = res
                run = self.plugin.save_manager.load_save(uid)
                if run is None or run.node_type != "battle":
                    return res
                if "❌" not in res:
                    played = True
                    break
            if not played:
                last_out = self.cmd("e", uid)
                run = self.plugin.save_manager.load_save(uid)
                if run is None or run.node_type != "battle":
                    return last_out
        self.fail(f"battle did not finish within turns: {last_out}")

    def test_shared_loadout_no_random_deck_and_private_center_chest(self):
        self._prepare_open_world_player(
            self.alice,
            "Alice",
            locked=["fireball"],
            bag=["espresso_beans", "field_bandage"],
            relics=["ancient_compass"],
        )
        self._prepare_open_world_player(
            self.bob,
            "Bob",
            locked=["fireball"],
            bag=["sugar_cube_pack"],
        )

        deck_view = self.cmd("deck", self.alice)
        expected_count = len(CLASS_STARTING_CARDS["法师"]) + 1
        self.assertIn(f"共 {expected_count} 张", deck_view)
        self.assertIn("火球术", deck_view)

        stats_a = self.plugin.save_manager.load_stats(self.alice)
        self.assertEqual(
            [c.id for c in stats_a.open_world_deck],
            CLASS_STARTING_CARDS["法师"] + ["fireball"],
        )

        chest_a = self.cmd("talk 储物箱", self.alice)
        self.assertIn("储物箱里空空如也", chest_a)
        stored = self.cmd("2", self.alice)
        self.assertIn("全部存入", stored)
        self.assertIn("浓缩咖啡豆", stored)
        self.assertIn("战地绷带", stored)

        store_relic_menu = self.cmd("2", self.alice)
        self.assertIn("古老罗盘", store_relic_menu)
        stored_relic = self.cmd("1", self.alice)
        self.assertIn("古老罗盘", stored_relic)
        self.cmd("0", self.alice)

        chest_b = self.cmd("touch 箱子", self.bob)
        self.assertIn("储物箱里空空如也", chest_b)
        self.assertNotIn("浓缩咖啡豆", chest_b)
        self.assertNotIn("古老罗盘", chest_b)
        self.cmd("0", self.bob)

        take_menu = self.cmd("talk 箱子", self.alice)
        self.assertIn("浓缩咖啡豆", take_menu)
        self.cmd("1", self.alice)
        took_item = self.cmd("1", self.alice)
        self.assertIn("取出", took_item)
        self.cmd("0", self.alice)
        take_relic_menu = self.cmd("4", self.alice)
        self.assertIn("古老罗盘", take_relic_menu)
        self.cmd("1", self.alice)
        self.cmd("0", self.alice)

        stats_a = self.plugin.save_manager.load_stats(self.alice)
        self.assertEqual(len(stats_a.open_world_bag), 1)
        self.assertEqual(len(stats_a.town_chest), 1)
        self.assertIn("ancient_compass", stats_a.open_world_relics)
        self.assertEqual(stats_a.town_chest_relics, [])

        bag_t_view = self.cmd("bag t", self.alice)
        self.assertIn("储物箱", bag_t_view)
        self.assertIn("开放世界共享行囊", bag_t_view)

        self.plugin.cli_router.town_engine.outer_plane_engine.enter_quest(self.alice, self.plugin.save_manager.load_stats(self.alice))
        self.cmd("atk", self.alice)
        outer_atk = self.cmd("atk", self.alice)
        run_op = load_run(self.plugin, self.alice)
        self.assertIsNotNone(run_op)
        self.assertFalse(run_op.node_data.get("is_town_combat"))
        self.assertTrue(run_op.node_data.get("is_open_world_combat"))
        self.assertIn("ancient_compass", run_op.player.relics)
        self.assertEqual(run_op.player.bag_items, list(stats_a.open_world_bag))
        self.assertGreater(len(run_op.player.hand), 0)
        self.assertIn("fireball", [c.id for c in run_op.player.deck])
        self.assertNotIn("（空空如也）", outer_atk)

    def test_open_world_death_and_abandon_strip_gear_while_keeping_town_spar(self):
        self._prepare_open_world_player(
            self.alice,
            "Alice",
            bag=["espresso_beans"],
            relics=["ancient_compass"],
        )

        self.cmd("talk 储物箱", self.alice)
        self.cmd("1", self.alice)
        self.cmd("1", self.alice)
        self.cmd("0", self.alice)
        self.cmd("0", self.alice)
        stats_before_spar = self.plugin.save_manager.load_stats(self.alice)
        stats_before_spar.open_world_bag = ["sugar_cube_pack"]
        self.plugin.save_manager.save_stats(self.alice, stats_before_spar)

        self.cmd("w", self.alice)
        self.cmd("atk 训练假人", self.alice)
        spar_run = load_run(self.plugin, self.alice)
        self.assertTrue(spar_run.node_data.get("is_town_combat"))
        spar_quit = self.cmd("abandon confirm", self.alice)
        self.assertIn("靶场", spar_quit)
        stats_after_spar = self.plugin.save_manager.load_stats(self.alice)
        self.assertEqual(stats_after_spar.open_world_bag, ["sugar_cube_pack"])
        self.assertEqual(stats_after_spar.open_world_relics, ["ancient_compass"])
        self.assertEqual(self.plugin.save_manager.open_world_ghosts.list_all(), [])

        self.cmd("home", self.alice)
        self.cmd("a", self.alice)
        self.cmd("a", self.alice)
        self.cmd("use 星辉符印", self.alice)
        self.cmd("d", self.alice)
        run_sf = load_run(self.plugin, self.alice)
        abandon_coord = floor_of(run_sf).player_coords[self.alice]
        abandon_out = self.cmd("abandon confirm", self.alice)
        self.assertIn("Alice的冤魂", abandon_out)
        self.assertIn("中心广场", abandon_out)
        self.assertNotIn("存档已被清除", abandon_out)

        stats_after_abandon = self.plugin.save_manager.load_stats(self.alice)
        self.assertTrue(stats_after_abandon.in_town)
        self.assertEqual(stats_after_abandon.town_pos, "square")
        self.assertEqual(stats_after_abandon.open_world_bag, [])
        self.assertEqual(stats_after_abandon.open_world_relics, [])
        self.assertEqual(stats_after_abandon.open_world_deck, [])
        self.assertEqual(len(stats_after_abandon.town_chest), 1)
        ghosts_sf = self.plugin.save_manager.open_world_ghosts.list_at(WORLD_SNOWFIELD, abandon_coord)
        self.assertEqual(len(ghosts_sf), 1)

        rebuilt_deck_view = self.cmd("deck", self.alice)
        self.assertIn(f"共 {len(CLASS_STARTING_CARDS['法师'])} 张", rebuilt_deck_view)

        stats_a = self.plugin.save_manager.load_stats(self.alice)
        stats_a.open_world_bag = ["espresso_beans"]
        stats_a.open_world_relics = ["ghost_body"]
        self.plugin.save_manager.save_stats(self.alice, stats_a)
        self.plugin.cli_router.town_engine.outer_plane_engine.enter_quest(self.alice, stats_a)
        self.cmd("atk", self.alice)
        self.cmd("atk", self.alice)
        op_run = load_run(self.plugin, self.alice)
        op_room = op_run.node_data["outer_plane_room"]
        lose_out = ""
        for _ in range(30):
            if self.plugin.save_manager.load_save(self.alice) is None:
                break
            lose_out = self.cmd("e", self.alice)
        self.assertIsNone(self.plugin.save_manager.load_save(self.alice))
        self.assertIn("Alice的冤魂", lose_out)
        self.assertIn("中心广场", lose_out)
        self.assertNotIn("存档已被清除", lose_out)
        stats_after_op_death = self.plugin.save_manager.load_stats(self.alice)
        self.assertFalse(stats_after_op_death.town_flags.get(OUTER_PLANE_ACTIVE_FLAG))
        self.assertEqual(stats_after_op_death.open_world_bag, [])
        self.assertEqual(stats_after_op_death.open_world_relics, [])
        ghosts_op = self.plugin.save_manager.open_world_ghosts.list_at(WORLD_OUTER_PLANE, op_room)
        self.assertEqual(len(ghosts_op), 1)

    def test_ghost_npc_manual_attack_random_cards_once_limit_and_owner_reclaim(self):
        self._prepare_open_world_player(
            self.alice,
            "Alice",
            locked=["fire_bolt"],
            bag=["espresso_beans"],
            relics=["ancient_compass", "migo_lightning_gun"],
            deck=["fire_bolt", "shield", "magic_missile", "warrior_defend", "elder_guidance"],
        )
        self._prepare_open_world_player(
            self.bob,
            "Bob",
            locked=["meteor_strike", "fireball"],
        )
        bob_stats = self.plugin.save_manager.load_stats(self.bob)
        bob_stats.open_world_max_hp = 200
        bob_stats.open_world_hp = 200
        self.plugin.save_manager.save_stats(self.bob, bob_stats)

        self.cmd("home", self.alice)
        self.cmd("a", self.alice)
        self.cmd("a", self.alice)
        self.cmd("use 星辉符印", self.alice)
        self.cmd("d", self.alice)
        ghost_coord = floor_of(load_run(self.plugin, self.alice)).player_coords[self.alice]
        self.cmd("abandon confirm", self.alice)

        self.cmd("a", self.bob)
        self.cmd("a", self.bob)
        self.cmd("use 星辉符印", self.bob)
        bob_move = self.cmd("d", self.bob)
        bob_run = load_run(self.plugin, self.bob)
        self.assertEqual(bob_run.node_type, "grid_map")
        self.assertIn("Alice的冤魂", bob_move)

        talk_res = self.cmd("talk Alice的冤魂", self.bob)
        self.assertIn("Alice", talk_res)
        self.assertEqual(load_run(self.plugin, self.bob).node_type, "grid_map")
        touch_res = self.cmd("touch 尸体", self.bob)
        self.assertIn("遗骸", touch_res)
        self.assertEqual(load_run(self.plugin, self.bob).node_type, "grid_map")

        atk_bob = self.cmd("atk Alice的冤魂", self.bob)
        self.assertIn("主动向", atk_bob)
        battle_run = load_run(self.plugin, self.bob)
        self.assertEqual(battle_run.node_type, "battle")
        self.assertEqual(battle_run.enemies[0].name, "Alice的冤魂")
        self.assertEqual(battle_run.enemies[0].max_actions, 2)
        self.assertEqual(battle_run.enemies[0].max_bonus_actions, 1)
        self.assertGreaterEqual(len(battle_run.enemies[0].intents), 2)

        intent_lines = set()
        for line in atk_bob.splitlines():
            if "意图" in line or "准备打出" in line:
                intent_lines.add(line.strip())
        first_turn = ""
        for turn_index in range(5):
            turn_out = self.cmd("e", self.bob)
            if turn_index == 0:
                first_turn = turn_out
            bob_check = self.plugin.save_manager.load_save(self.bob)
            if bob_check is None or bob_check.node_type != "battle":
                break
            for line in turn_out.splitlines():
                if "意图" in line or "准备打出" in line:
                    intent_lines.add(line.strip())
        self.assertGreater(len(intent_lines), 1)
        self.assertIn("魔法飞弹", first_turn)
        self.assertIn("造成", first_turn)
        self.assertGreaterEqual(first_turn.count("💀 【Alice的冤魂】打出"), 2)
        ghost_after = load_run(self.plugin, self.bob)
        self.assertTrue(any(buff.id == "all_resonance" for buff in ghost_after.enemies[0].buffs))

        bob_gp_before = self.plugin.save_manager.load_stats(self.bob).gp
        win_bob = self._win_active_battle(self.bob)
        self.assertIn("25 GP", win_bob)
        bob_gp_after = self.plugin.save_manager.load_stats(self.bob).gp
        self.assertEqual(bob_gp_after, bob_gp_before + 25)
        self.assertEqual(len(self.plugin.save_manager.open_world_ghosts.list_at(WORLD_SNOWFIELD, ghost_coord)), 1)

        reattack_bob = self.cmd("atk Alice的冤魂", self.bob)
        self.assertIn("只能攻击同一具冤魂一次", reattack_bob)

        stats_a = self.plugin.save_manager.load_stats(self.alice)
        stats_a.locked_cards = ["meteor_strike", "fireball"]
        stats_a.open_world_deck = []
        self.plugin.save_manager.save_stats(self.alice, stats_a)

        self.cmd("home", self.alice)
        self.cmd("a", self.alice)
        self.cmd("a", self.alice)
        self.cmd("use 星辉符印", self.alice)
        alice_enter = self.cmd("d", self.alice)
        self.assertIn("Alice的冤魂", alice_enter)
        self.assertEqual(load_run(self.plugin, self.alice).node_type, "grid_map")

        self.cmd("atk Alice的冤魂", self.alice)
        win_alice = self._win_active_battle(self.alice)
        self.assertIn("找回了旧卡牌（5 张）与旧遗物（2 件）", win_alice)
        self.assertEqual(self.plugin.save_manager.open_world_ghosts.list_at(WORLD_SNOWFIELD, ghost_coord), [])

        stats_a_reclaimed = self.plugin.save_manager.load_stats(self.alice)
        self.assertEqual(
            [c.id for c in stats_a_reclaimed.open_world_deck],
            ["fire_bolt", "shield", "magic_missile", "warrior_defend", "elder_guidance"],
        )
        self.assertIn("ancient_compass", stats_a_reclaimed.open_world_relics)
        self.assertIn("migo_lightning_gun", stats_a_reclaimed.open_world_relics)

    def test_talk_logs_render_in_upper_layer_across_open_worlds(self):
        self._prepare_open_world_player(
            self.alice,
            "Alice",
            locked=["meteor_strike", "fireball"],
            bag=["field_bandage"],
        )
        self._prepare_open_world_player(self.bob, "Bob")

        town_status = self.cmd("r", self.alice)
        self.assertIn("❤️ HP 50/50", town_status)
        self.assertIn("行囊负重：", town_status)
        self.assertIn("/100 KG", town_status)

        self.plugin.cli_router.town_engine.outer_plane_engine.enter_quest(self.bob, self.plugin.save_manager.load_stats(self.bob))
        self.cmd("abandon confirm", self.bob)
        self.cmd("use 死灵之书", self.alice)
        self.cmd("c 3", self.alice)
        stats_b_town = self.plugin.save_manager.load_stats(self.bob)
        stats_b_town.open_world_deck = [CardState("fire_bolt"), CardState("magic_missile")]
        self.plugin.save_manager.save_stats(self.bob, stats_b_town)
        self.cmd("主城", self.bob)
        ghost_in_town = self.plugin.save_manager.open_world_ghosts.add(
            self.bob,
            "Bob",
            WORLD_TOWN,
            "square",
            "主城试炼阵亡",
            45,
            [{"id": "fire_bolt", "upgraded": False, "gems": []}],
            [],
            {},
            [],
        )
        self.assertIsNotNone(ghost_in_town)
        self.cmd("atk Bob的冤魂", self.alice)
        self.cmd("e", self.alice)
        after_ghost_hit = load_run(self.plugin, self.alice)
        self.assertIsNotNone(after_ghost_hit)
        self.assertLess(after_ghost_hit.player.hp, after_ghost_hit.player.max_hp)
        self._win_active_battle(self.alice)
        damaged_hp = self.plugin.save_manager.load_stats(self.alice).open_world_hp
        town_damaged = self.cmd("r", self.alice)
        self.assertIn(f"❤️ HP {damaged_hp}/50", town_damaged)
        heal_res = self.cmd("use 战地绷带", self.alice)
        self.assertIn("战地绷带", heal_res)
        self.cmd("home", self.alice)
        self.cmd("a", self.alice)
        self.cmd("a", self.alice)
        snow_after_heal = self.cmd("use 星辉符印", self.alice)
        healed_hp = self.plugin.save_manager.load_stats(self.alice).open_world_hp
        self.assertGreater(healed_hp, damaged_hp)
        self.assertIn(f"❤️ HP {healed_hp}/50", snow_after_heal)
        self.cmd("abandon confirm", self.alice)

        self.cmd("talk Alice 统一上层对话", self.bob)
        town_r = self.cmd("r", self.alice)
        self.assertIn("💬 【Bob】对你说：统一上层对话", town_r)
        self.assertLess(town_r.index("💬 【Bob】对你说：统一上层对话"), town_r.index("先古主城"))

        self.cmd("home", self.alice)
        self.cmd("a", self.alice)
        self.cmd("a", self.alice)
        self.cmd("use 星辉符印", self.alice)
        self.cmd("a", self.bob)
        self.cmd("a", self.bob)
        self.cmd("use 星辉符印", self.bob)

        self.cmd("talk Alice 统一上层对话", self.bob)
        snow_view = self.cmd("r", self.alice)
        self.assertIn("💬 【Bob】对你说：统一上层对话", snow_view)
        self.assertLess(snow_view.index("💬 【Bob】对你说：统一上层对话"), snow_view.index("雾隐雪原"))
        self.assertLess(snow_view.index("💬 【Bob】对你说：统一上层对话"), snow_view.index("----------------------------------------"))

        self.cmd("abandon confirm", self.alice)
        self.cmd("abandon confirm", self.bob)
        self.cmd("use 死灵之书", self.alice)
        self.cmd("use 死灵之书", self.bob)

        self.cmd("talk Alice 统一上层对话", self.bob)
        op_view = self.cmd("look", self.alice)
        self.assertIn("💬 【Bob】对你说：统一上层对话", op_view)
        self.assertLess(op_view.index("💬 【Bob】对你说：统一上层对话"), op_view.index("外层位面"))
