import asyncio
import random
import tempfile
import unittest

from game.core.world.grid_map_generator import coord_to_xy, xy_to_coord
from game.core.party.session import SessionContextScoper
from game.data.grid_map_config import FLOOR_CONFIGS
from game.entities import ALL_CARDS
from game.entities.cards.base import card_matches_color, get_card_color_icon
from game.models.state import CardState, EnemyState
from game.test.core.base import CorePlugin, move_to_room, run_command


class TestGridMapAndBladesong(unittest.TestCase):
    def setUp(self):
        random.seed(2026)
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, cmd, uid="grid_solo"):
        return asyncio.run(run_command(self.plugin, cmd, sender_id=uid))

    def _start_solo(self, uid="grid_solo"):
        self.run_cmd("start confirm", uid)
        self.run_cmd("c 1", uid)
        return self.plugin.save_manager.load_save(uid)

    def test_grid_generation_fog_movement_and_tp(self):
        random.seed(42)
        run = self._start_solo("gm_nav")
        self.assertEqual(run.node_type, "grid_map")
        fm = run.floor_map
        self.assertIsNotNone(fm)
        self.assertEqual(fm.floor_index, 1)
        passable = [r for r in fm.rooms.values() if r.room_type != "wall"]
        ratio = len(passable) / (fm.width * fm.height)
        self.assertGreaterEqual(ratio, 0.35)
        self.assertLessEqual(ratio, 0.65)
        room_types = {r.room_type for r in passable}
        self.assertIn("spawn", room_types)
        self.assertIn("boss", room_types)
        self.assertIn("cafe", room_types)
        self.assertIn("landmark", room_types)

        map_out = self.run_cmd("map", "gm_nav")
        self.assertIn("表层迷城", map_out)
        self.assertIn("📍", map_out)
        self.assertIn("🌫️", map_out)

        spawn_coord = fm.player_coords["gm_nav"]
        tp_list = self.run_cmd("tp", "gm_nav")
        self.assertIn("可传送节点", tp_list)
        self.assertIn(spawn_coord, tp_list)

        cafe_coord = next(c for c, r in fm.rooms.items() if r.room_type == "cafe")
        fm.rooms[cafe_coord].explored = True
        if cafe_coord not in fm.revealed_coords:
            fm.revealed_coords.append(cafe_coord)
        self.plugin.save_manager.save_save("gm_nav", run)

        tp_pinyin = self.run_cmd("tp kfg", "gm_nav")
        after_tp = self.plugin.save_manager.load_save("gm_nav")
        self.assertEqual(after_tp.floor_map.player_coords["gm_nav"], cafe_coord)
        self.assertEqual(after_tp.node_type, "cafe")
        self.assertIn("咖啡", tp_pinyin)

        self.run_cmd("离开", "gm_nav")
        back_to_spawn = self.run_cmd(f"tp {spawn_coord}", "gm_nav")
        self.assertIn(spawn_coord, back_to_spawn)
        after_spawn = self.plugin.save_manager.load_save("gm_nav")
        self.assertEqual(after_spawn.player.sp, after_spawn.player.max_sp)

    def test_obstacle_sp_and_forced_exhaustion_overdraft(self):
        run = self._start_solo("gm_obs")
        fm = run.floor_map
        sx, sy = coord_to_xy(fm.player_coords["gm_obs"])
        adj_coord = None
        adj_dir = None
        for dkey, (dx, dy) in (("d", (1, 0)), ("w", (0, -1)), ("s", (0, 1)), ("a", (-1, 0))):
            nx, ny = sx + dx, sy + dy
            if 0 <= nx < fm.width and 0 <= ny < fm.height:
                adj_coord = xy_to_coord(nx, ny)
                adj_dir = dkey
                break
        self.assertIsNotNone(adj_coord)
        fm.rooms[adj_coord].room_type = "obstacle"
        fm.rooms[adj_coord].cleared = False
        fm.rooms[adj_coord].obstacle_sp = 2
        run.player.sp = 0
        run.player.exhaustion = 0
        self.plugin.save_manager.save_save("gm_obs", run)

        warn = self.run_cmd(adj_dir, "gm_obs")
        self.assertIn("体力透支", warn)
        self.assertEqual(self.plugin.save_manager.load_save("gm_obs").player.exhaustion, 0)
        warn2 = self.run_cmd(adj_dir, "gm_obs")
        self.assertIn("2/2", warn2)
        self.assertEqual(self.plugin.save_manager.load_save("gm_obs").player.exhaustion, 0)

        forced = self.run_cmd(adj_dir, "gm_obs")
        self.assertIn("强行突破", forced)
        after = self.plugin.save_manager.load_save("gm_obs")
        self.assertEqual(after.player.exhaustion, 1)
        self.assertEqual(after.floor_map.player_coords["gm_obs"], adj_coord)
        self.assertLess(after.player.hp, after.player.max_hp)

    def test_five_level_exhaustion_effects_and_death(self):
        run = self._start_solo("gm_exh")
        run.player.exhaustion = 4
        run.player.max_hp = 80
        run.player.hp = 80
        run.player.deck = [CardState(id="fireball") for _ in range(10)]
        run.player.relics = []
        self.plugin.save_manager.save_save("gm_exh", run)

        _, battle = move_to_room(self.plugin, "gm_exh", ("battle", "elite"))
        self.assertEqual(battle.node_type, "battle")
        p = battle.player
        self.assertEqual(p.hp, 40)
        self.assertEqual(len(p.hand), 4)
        self.assertEqual(p.bonus_actions, 0)

        p.hand = [CardState(id="ghostly_armor"), CardState(id="fireball"), CardState(id="haste_sp")]
        p.relics = []
        p.actions = 4
        p.bonus_actions = 0
        p.shield = 0
        p.sp = 0
        battle.enemies = [EnemyState(name="测试假人", hp=999, max_hp=999, shield=0, intent_type="attack", intent_val=1, intent_desc="攻击", intent_a_type="attack")]
        self.plugin.save_manager.save_save("gm_exh", battle)

        self.run_cmd("p 1", "gm_exh")
        after_shield = self.plugin.save_manager.load_save("gm_exh")
        self.assertEqual(after_shield.player.shield, int(10 * 0.75))

        self.run_cmd("p 1 e1", "gm_exh")
        after_dmg = self.plugin.save_manager.load_save("gm_exh")
        self.assertEqual(999 - after_dmg.enemies[0].hp, int(18 * 0.80))

        death_res = self.run_cmd("p 1", "gm_exh")
        self.assertTrue("力竭" in death_res or "阵亡" in death_res or "GP" in death_res)
        self.assertIsNone(self.plugin.save_manager.load_save("gm_exh"))

    def test_sp_cards_and_ghostification_mechanics(self):
        run = self._start_solo("gm_sp")
        run.player.relics = []
        run.player.max_hp = 80
        run.player.hp = 80
        self.plugin.save_manager.save_save("gm_sp", run)

        SessionContextScoper.create_session(run, "A1", "event", ["gm_sp"])
        self.plugin.engine.map_engine.explore_engine._init_event_node(run, event_id="ghostification")
        self.plugin.save_manager.save_save("gm_sp", run)
        ghost_res = self.run_cmd("c 1", "gm_sp")
        self.assertIn("幽灵之躯", ghost_res)

        after_ghost = self.plugin.save_manager.load_save("gm_sp")
        self.assertEqual(after_ghost.node_type, "grid_map")
        self.assertEqual(after_ghost.player.max_hp, 40)
        self.assertIn("ghost_body", after_ghost.player.relics)
        self.assertEqual(sum(1 for c in after_ghost.player.deck if c.id == "intangible"), 2)

        _, battle = move_to_room(self.plugin, "gm_sp", ("battle", "elite"))
        p = battle.player
        p.sp = 5
        p.hand = [
            CardState(id="calm_mind"),
            CardState(id="desperate_strike"),
            CardState(id="intangible"),
        ]
        p.actions = 3
        p.bonus_actions = 1
        battle.enemies = [EnemyState(name="测试假人", hp=999, max_hp=999, shield=0, intent_type="attack", intent_val=20, intent_desc="攻击", intent_a_type="attack")]
        self.plugin.save_manager.save_save("gm_sp", battle)

        self.run_cmd("p 1", "gm_sp")
        after_calm = self.plugin.save_manager.load_save("gm_sp")
        self.assertEqual(after_calm.player.sp, 9)
        self.assertTrue(any(b.id == "psychic_resistance" for b in after_calm.player.buffs))

        after_calm.player.sp = 4
        after_calm.player.exhaustion = 2
        self.plugin.save_manager.save_save("gm_sp", after_calm)
        self.run_cmd("p 1 e1", "gm_sp")
        after_desp = self.plugin.save_manager.load_save("gm_sp")
        dealt = 999 - after_desp.enemies[0].hp
        expected = int((6 + 6 * 2) * (1 + 2 * 0.25))
        self.assertEqual(dealt, expected)

        self.run_cmd("p 1", "gm_sp")
        after_intang = self.plugin.save_manager.load_save("gm_sp")
        self.assertTrue(any(b.id == "intangible" for b in after_intang.player.buffs))
        hp_before_enemy = after_intang.player.hp
        self.run_cmd("e", "gm_sp")
        after_enemy = self.plugin.save_manager.load_save("gm_sp")
        self.assertEqual(hp_before_enemy - after_enemy.player.hp, 1)

    def test_bladesong_dual_color_event_and_combat_resonance(self):
        card_obj = ALL_CARDS["bladesong"]
        self.assertEqual(card_obj.color, "wizard_warrior")
        self.assertEqual(get_card_color_icon(card_obj), "🔵🔴")
        self.assertTrue(card_matches_color(card_obj, "wizard"))
        self.assertTrue(card_matches_color(card_obj, "warrior"))
        self.assertFalse(card_matches_color(card_obj, "neutral"))

        run = self._start_solo("gm_bs")
        SessionContextScoper.create_session(run, "A1", "event", ["gm_bs"])
        self.plugin.engine.map_engine.explore_engine._init_event_node(run, event_id="bladesinger_echo")
        self.plugin.save_manager.save_save("gm_bs", run)

        ev_res = self.run_cmd("c 1", "gm_bs")
        self.assertIn("剑歌", ev_res)
        after_ev = self.plugin.save_manager.load_save("gm_bs")
        self.assertEqual(after_ev.node_type, "grid_map")
        self.assertTrue(any(c.id == "bladesong" for c in after_ev.player.deck))

        deck_out = self.run_cmd("deck", "gm_bs")
        self.assertIn("🔵🔴", deck_out)
        self.assertIn("剑歌", deck_out)

        _, battle = move_to_room(self.plugin, "gm_bs", ("battle", "elite"))
        p = battle.player
        p.hand = [
            CardState(id="bladesong"),
            CardState(id="fireball"),
            CardState(id="warrior_strike"),
            CardState(id="quick_strike"),
        ]
        p.relics = []
        p.buffs = []
        p.actions = 4
        p.bonus_actions = 1
        p.shield = 0
        battle.enemies = [EnemyState(name="测试假人", hp=999, max_hp=999, shield=0, intent_type="attack", intent_val=1, intent_desc="攻击", intent_a_type="attack")]
        self.plugin.save_manager.save_save("gm_bs", battle)

        bs_res = self.run_cmd("p 1", "gm_bs")
        self.assertIn("剑歌", bs_res)
        after_bs = self.plugin.save_manager.load_save("gm_bs")
        self.assertEqual(after_bs.player.shield, 11)
        self.assertEqual(999 - after_bs.enemies[0].hp, 3)
        self.assertTrue(any(b.id == "bladesong" for b in after_bs.player.buffs))

        self.run_cmd("p 1 e1", "gm_bs")
        after_blue = self.plugin.save_manager.load_save("gm_bs")
        self.assertEqual(after_blue.player.shield, 14)
        self.assertEqual(999 - after_blue.enemies[0].hp, 3 + 18 + 3)

        self.run_cmd("p 1 e1", "gm_bs")
        after_red = self.plugin.save_manager.load_save("gm_bs")
        self.assertEqual(after_red.player.shield, 17)
        self.assertEqual(999 - after_red.enemies[0].hp, 3 + 18 + 3 + 6 + 3)

        self.run_cmd("p 1 e1", "gm_bs")
        after_neutral = self.plugin.save_manager.load_save("gm_bs")
        self.assertEqual(after_neutral.player.shield, 17)

        self.run_cmd("e", "gm_bs")
        next_turn = self.plugin.save_manager.load_save("gm_bs")
        self.assertEqual(next_turn.player.bonus_actions, 2)

    def test_landmark_secret_boss_and_downstairs_floor_advance(self):
        random.seed(7)
        run = self._start_solo("gm_lm")
        fm = run.floor_map
        obs_coord = next((c for c, r in fm.rooms.items() if r.room_type == "landmark" and r.landmark_id == "observatory"), None)
        if obs_coord is None:
            obs_coord = fm.player_coords["gm_lm"]
            fm.rooms[obs_coord].room_type = "landmark"
            fm.rooms[obs_coord].landmark_id = "observatory"
            fm.rooms[obs_coord].cleared = False
        fm.player_coords["gm_lm"] = obs_coord
        fm.rooms[obs_coord].explored = True
        self.plugin.save_manager.save_save("gm_lm", run)

        talk_res = self.run_cmd("talk", "gm_lm")
        self.assertIn("观星台", talk_res)
        clue_res = self.run_cmd("c 3", "gm_lm")
        self.assertIn("秘密祭坛", clue_res)
        after_clue = self.plugin.save_manager.load_save("gm_lm")
        self.assertTrue(after_clue.floor_map.secret_clue_found)

        ritual_coord = after_clue.floor_map.ritual_coord
        proto = after_clue.floor_map.ritual_protocol
        if proto == "exhaustion_or_curse":
            after_clue.player.exhaustion = 1
        elif proto == "camp_ember":
            after_clue.player.quest_relics.append("camp_ember")
        elif proto == "awakened_compass":
            after_clue.player.quest_relics.append("awakened_rift_compass")
        after_clue.floor_map.player_coords["gm_lm"] = ritual_coord
        after_clue.floor_map.rooms[ritual_coord].explored = True
        self.plugin.save_manager.save_save("gm_lm", after_clue)

        self.run_cmd("talk", "gm_lm")
        ritual_state = self.plugin.save_manager.load_save("gm_lm")
        ritual_idx = next(i + 1 for i, o in enumerate(ritual_state.node_data["options"]) if o.get("action", "").startswith("ritual_"))
        ritual_res = self.run_cmd(f"c {ritual_idx}", "gm_lm")
        self.assertIn("隐秘首领房间", ritual_res)
        unlocked = self.plugin.save_manager.load_save("gm_lm")
        self.assertTrue(unlocked.floor_map.secret_unlocked)

        unlocked.player.sp = 3
        unlocked.player.exhaustion = 2
        ds_coord = unlocked.floor_map.boss_coord
        unlocked.floor_map.rooms[ds_coord].room_type = "downstairs"
        unlocked.floor_map.rooms[ds_coord].cleared = True
        unlocked.floor_map.rooms[ds_coord].explored = True
        unlocked.floor_map.player_coords["gm_lm"] = ds_coord
        self.plugin.save_manager.save_save("gm_lm", unlocked)

        ds_open = self.run_cmd("talk", "gm_lm")
        self.assertIn("下楼回廊", ds_open)
        ds_res = self.run_cmd("c 1", "gm_lm")
        self.assertIn("第 2 层", ds_res)
        floor2 = self.plugin.save_manager.load_save("gm_lm")
        self.assertEqual(floor2.floor_map.floor_index, 2)
        self.assertEqual(floor2.player.sp, floor2.player.max_sp)
        self.assertEqual(floor2.player.exhaustion, 1)
        self.assertEqual(floor2.player.stage, FLOOR_CONFIGS[2]["stage_min"])


if __name__ == "__main__":
    unittest.main()
