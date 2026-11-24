import copy
import tempfile
import unittest

from game.core.battle.selection import SelectionStepSpec
from game.entities import ALL_CARDS
from game.models.state import Card, CardState, EnemyState, GameRun, MinionState, PlayerState
from game.test.core.base import CorePlugin, load_run, run_command


class TestUnifiedSelectionSystem(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmpdir.name)
        self.sm = self.plugin.save_manager
        self.uid = "test_unified_sel_user"
        self.temp_card_ids: list[str] = []

    def tearDown(self):
        for cid in self.temp_card_ids:
            ALL_CARDS.pop(cid, None)
        self.tmpdir.cleanup()

    async def test_discover_partial_param_back_exit_and_pinyin(self):
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=100,
            actions=3,
            bonus_actions=0,
            deck=[CardState(id="discover", upgraded=True)],
            hand=[CardState(id="discover", upgraded=True)],
            exhaust_pile=[
                CardState(id="discover"),
                CardState(id="fire_bolt"),
                CardState(id="dagger_throw"),
                CardState(id="first_aid"),
                CardState(id="discover", upgraded=True),
            ],
        )
        run = GameRun(
            user_id=self.uid,
            player=player,
            enemies=[EnemyState(name="测试木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
        )
        self.sm.save_save(self.uid, run)

        res_partial = await run_command(self.plugin, "p 1 ex:hyd", sender_id=self.uid)
        self.assertIn("火焰弹", res_partial)
        self.assertIn("1. 匕首投掷", res_partial)
        self.assertIn("2. 绷带包扎", res_partial)
        mid = load_run(self.plugin, self.uid)
        self.assertEqual(len(mid.node_data.get("state_stack", [])), 1)

        res_back = await run_command(self.plugin, "back", sender_id=self.uid)
        self.assertIn("退回上一轮", res_back)
        self.assertIn("1. 火焰弹", res_back)
        self.assertIn("2. 匕首投掷", res_back)
        self.assertIn("3. 绷带包扎", res_back)

        res_back_root = await run_command(self.plugin, "bk", sender_id=self.uid)
        self.assertIn("第一轮", res_back_root)

        res_step1 = await run_command(self.plugin, "2", sender_id=self.uid)
        self.assertIn("匕首投掷", res_step1)
        self.assertIn("2. 绷带包扎", res_step1)

        res_step2 = await run_command(self.plugin, "c 1", sender_id=self.uid)
        self.assertIn("发掘", res_step2)
        after = load_run(self.plugin, self.uid)
        hand_ids = [c.id for c in after.player.hand]
        self.assertIn("dagger_throw", hand_ids)
        self.assertIn("fire_bolt", hand_ids)
        self.assertEqual(len(after.node_data.get("state_stack", [])), 0)

        after.player.hand = [CardState(id="discover", upgraded=True)]
        after.player.exhaust_pile = [CardState(id="fire_bolt"), CardState(id="dagger_throw"), CardState(id="first_aid")]
        actions_before_bad = after.player.actions
        self.sm.save_save(self.uid, after)
        res_bad = await run_command(self.plugin, "p 1 ex:notfound", sender_id=self.uid)
        self.assertIn("无效", res_bad)
        self.assertIn("1. 火焰弹", res_bad)
        res_exit = await run_command(self.plugin, "exit", sender_id=self.uid)
        self.assertIn("取消", res_exit)
        after_exit = load_run(self.plugin, self.uid)
        self.assertEqual(after_exit.player.actions, actions_before_bad)
        self.assertEqual(after_exit.player.hand[0].id, "discover")

    async def test_single_valid_candidate_auto_selects(self):
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=100,
            actions=3,
            bonus_actions=0,
            deck=[CardState(id="discover"), CardState(id="moyai_trio"), CardState(id="demon_form")],
            hand=[CardState(id="discover"), CardState(id="moyai_trio"), CardState(id="demon_form")],
            exhaust_pile=[
                CardState(id="discover"),
                CardState(id="dagger_throw"),
                CardState(id="discover", upgraded=True),
            ],
        )
        run = GameRun(
            user_id=self.uid,
            player=player,
            enemies=[EnemyState(name="测试木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
        )
        self.sm.save_save(self.uid, run)

        res_disc = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertIn("匕首投掷", res_disc)
        run_mid = load_run(self.plugin, self.uid)
        self.assertEqual(len(run_mid.node_data.get("state_stack", [])), 0)
        self.assertIn("dagger_throw", [c.id for c in run_mid.player.hand])

        run_mid.player.hand = [CardState(id="moyai_trio"), CardState(id="demon_form")]
        self.sm.save_save(self.uid, run_mid)

        res_moyai = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertIn("诡秘", res_moyai)
        run_end = load_run(self.plugin, self.uid)
        self.assertEqual(run_end.player.shield, 10)
        self.assertTrue(any(b.id == "demon_form" for b in run_end.player.buffs))
        self.assertEqual(len(run_end.node_data.get("state_stack", [])), 0)

    async def test_emperor_eye_h_selector_and_pinyin(self):
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=100,
            actions=3,
            bonus_actions=0,
            deck=[CardState(id="neutral_emperor_eye"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
            hand=[CardState(id="neutral_emperor_eye"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
        )
        run = GameRun(
            user_id=self.uid,
            player=player,
            enemies=[EnemyState(name="测试木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
        )
        self.sm.save_save(self.uid, run)

        res = await run_command(self.plugin, "p 1 h:fy", sender_id=self.uid)
        self.assertIn("保留了手牌中的【防御】", res)
        after = load_run(self.plugin, self.uid)
        self.assertEqual(after.player.hand[0].id, "warrior_defend")
        self.assertIn("fire_bolt", [c.id for c in after.player.exhaust_pile])

    async def test_fleeting_spark_two_step_pinyin_and_partial(self):
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=100,
            actions=3,
            bonus_actions=0,
            deck=[CardState(id="fleeting_spark"), CardState(id="dagger_throw"), CardState(id="demon_form")],
            hand=[CardState(id="fleeting_spark"), CardState(id="dagger_throw")],
            draw_pile=[CardState(id="warrior_defend"), CardState(id="demon_form")],
        )
        enemies = [
            EnemyState(name="史莱姆", hp=50, max_hp=50, shield=0, intent_desc="待机"),
            EnemyState(name="哥布林", hp=50, max_hp=50, shield=0, intent_desc="待机"),
        ]
        run = GameRun(user_id=self.uid, player=player, enemies=enemies, node_type="battle")
        self.sm.save_save(self.uid, run)

        res_full = await run_command(self.plugin, "p 1 e:gbl h:emxt", sender_id=self.uid)
        self.assertIn("哥布林", res_full)
        self.assertIn("诡秘", res_full)
        after = load_run(self.plugin, self.uid)
        self.assertEqual(after.enemies[0].hp, 50)
        self.assertEqual(after.enemies[1].hp, 44)
        self.assertTrue(any(b.id == "demon_form" for b in after.player.buffs))
        self.assertEqual(len(after.node_data.get("state_stack", [])), 0)

    async def test_rlyeh_astrolabe_standard_choose_one_flow(self):
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=0,
            actions=5,
            bonus_actions=0,
            deck=[CardState(id="special_rlyeh_astrolabe")],
            hand=[CardState(id="special_rlyeh_astrolabe")],
        )
        run = GameRun(
            user_id=self.uid,
            player=player,
            enemies=[EnemyState(name="伟大的克苏鲁", hp=500, max_hp=500, shield=0, intent_desc="待机")],
            node_type="battle",
            node_data={"cthulhu_seal_stage": 1},
        )
        self.sm.save_save(self.uid, run)
        prompt = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertIn("1.", prompt)
        self.assertIn("2.", prompt)
        self.assertIn("3.", prompt)
        mid = load_run(self.plugin, self.uid)
        self.assertEqual(len(mid.node_data.get("state_stack", [])), 1)
        result = await run_command(self.plugin, "c 1", sender_id=self.uid)
        self.assertIn("星轨闭合", result)
        after = load_run(self.plugin, self.uid)
        self.assertEqual(after.node_data.get("cthulhu_seal_stage"), 2)
        self.assertEqual(after.player.shield, 12)
        self.assertEqual(len(after.node_data.get("state_stack", [])), 0)

    async def test_draw_pile_shuffling_fairness_and_dr_selector(self):
        soldiers = [
            CardState(id="officer_recruit_vanguard"),
            CardState(id="officer_banner_bearer"),
            CardState(id="officer_royal_guard"),
            CardState(id="officer_squad_skirmisher"),
            CardState(id="officer_blade_dancer"),
        ]
        player = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=100,
            actions=5,
            bonus_actions=5,
            deck=[CardState(id="commander_valiant_herald")] + copy.deepcopy(soldiers),
            hand=[CardState(id="commander_valiant_herald")],
            draw_pile=[CardState(id="fire_bolt"), CardState(id="warrior_defend")] + copy.deepcopy(soldiers),
        )
        run = GameRun(
            user_id=self.uid,
            player=player,
            enemies=[EnemyState(name="木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
        )
        self.sm.save_save(self.uid, run)

        observed_orders = set()
        for _ in range(10):
            res_prompt = await run_command(self.plugin, "p 1", sender_id=self.uid)
            self.assertNotIn("火焰弹", res_prompt)
            self.assertNotIn("防御", res_prompt)
            lines = [ln.strip() for ln in res_prompt.splitlines() if ln.strip()[:2] in ("1.", "2.", "3.", "4.", "5.")]
            observed_orders.add(tuple(lines))
            res_exit = await run_command(self.plugin, "exit", sender_id=self.uid)
            self.assertIn("取消", res_exit)
        self.assertGreater(len(observed_orders), 1)

        res_dr = await run_command(self.plugin, "p 1 dr:jw", sender_id=self.uid)
        self.assertIn("近卫铁骑", res_dr)
        after = load_run(self.plugin, self.uid)
        self.assertIn("officer_royal_guard", [c.id for c in after.player.hand])

    async def test_graveyard_discard_optional_multi_and_revalidation(self):
        class ProbeMultiSelectCard(Card):
            def get_selection_spec(self, run, engine):
                return {
                    "phase": "pre_play",
                    "can_cancel": True,
                    "steps": [
                        SelectionStepSpec(step_id="dc_pick", kind="discard", min_count=0, max_count=2, required=False, auto_single=True),
                        SelectionStepSpec(step_id="mg_pick", kind="minion_graveyard", min_count=1, max_count=1, required=True, auto_single=True),
                        SelectionStepSpec(step_id="eg_pick", kind="enemy_graveyard", min_count=1, max_count=1, required=True, auto_single=True),
                        SelectionStepSpec(step_id="amg_pick", kind="ally_minion_graveyard", min_count=1, max_count=1, required=True, auto_single=True),
                    ],
                }

            def execute_with_selections(self, run, selections, engine) -> str:
                parts = []
                for key in ("dc_pick", "mg_pick", "eg_pick", "amg_pick"):
                    parts.append(f"{key}=" + ",".join(item["match_name"] for item in selections.get(key, [])))
                return "PROBE|" + "|".join(parts)

        probe_id = "test_probe_multi_select"
        self.temp_card_ids.append(probe_id)
        ALL_CARDS[probe_id] = ProbeMultiSelectCard(
            id=probe_id,
            name="探针多选",
            color="neutral",
            type="spell",
            cost_a=1,
            cost_ba=0,
            desc="测试",
        )

        p1 = PlayerState(
            name="队长",
            hp=80,
            max_hp=80,
            shield=0,
            gold=0,
            actions=3,
            bonus_actions=0,
            deck=[CardState(id=probe_id)],
            hand=[CardState(id=probe_id)],
            discard_pile=[CardState(id="fire_bolt"), CardState(id="warrior_defend"), CardState(id="dagger_throw")],
            minion_graveyard=["mercenary", "shield_guard"],
            enemy_graveyard=["哥布林", "史莱姆"],
        )
        p2 = PlayerState(
            name="队友甲",
            hp=80,
            max_hp=80,
            shield=0,
            gold=0,
            minion_graveyard=["gate_guard", "water_elemental"],
        )
        run = GameRun(
            user_id=self.uid,
            player=p1,
            enemies=[EnemyState(name="木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
            party_order=[self.uid, "ally_u2"],
            players={self.uid: p1, "ally_u2": p2},
        )
        self.sm.save_save(self.uid, run)

        res1 = await run_command(self.plugin, "p 1 dc:hyd", sender_id=self.uid)
        self.assertIn("可选至多 2 项", res1)
        res_done = await run_command(self.plugin, "done", sender_id=self.uid)
        self.assertIn("盾卫", res_done)
        res_mg = await run_command(self.plugin, "mg:dw", sender_id=self.uid)
        self.assertIn("史莱姆", res_mg)
        res_eg = await run_command(self.plugin, "eg:slm", sender_id=self.uid)
        self.assertIn("寒冰元素", res_eg)
        res_amg = await run_command(self.plugin, "a2mg:hbys", sender_id=self.uid)
        self.assertIn("PROBE|dc_pick=火焰弹|mg_pick=盾卫|eg_pick=史莱姆|amg_pick=寒冰元素", res_amg)

        run2 = load_run(self.plugin, self.uid)
        run2.player.hand = [CardState(id=probe_id)]
        run2.player.actions = 2
        self.sm.save_save(self.uid, run2)
        await run_command(self.plugin, "p 1 dc1", sender_id=self.uid)
        await run_command(self.plugin, "done", sender_id=self.uid)
        await run_command(self.plugin, "mg1", sender_id=self.uid)
        run_tampered = load_run(self.plugin, self.uid)
        run_tampered.player.minion_graveyard.clear()
        self.sm.save_save(self.uid, run_tampered)
        await run_command(self.plugin, "eg1", sender_id=self.uid)
        res_reval = await run_command(self.plugin, "a2mg1", sender_id=self.uid)
        self.assertIn("已选目标已失效", res_reval)
        run_rolled = load_run(self.plugin, self.uid)
        self.assertEqual(run_rolled.player.actions, 2)
        self.assertEqual(len(run_rolled.node_data.get("state_stack", [])), 0)

    async def test_simple_cards_stay_auto_and_support_pinyin(self):
        p1 = PlayerState(
            name="队长",
            hp=60,
            max_hp=80,
            shield=0,
            gold=0,
            actions=4,
            bonus_actions=4,
            deck=[CardState(id="fire_bolt"), CardState(id="fire_bolt"), CardState(id="first_aid")],
            hand=[CardState(id="fire_bolt"), CardState(id="fire_bolt"), CardState(id="first_aid")],
            minions={"1": MinionState("mercenary", "雇佣兵", 5, 10, 4, 1, 0)},
        )
        enemies = [
            EnemyState(name="史莱姆", hp=50, max_hp=50, shield=0, intent_desc="待机"),
            EnemyState(name="哥布林", hp=50, max_hp=50, shield=0, intent_desc="待机"),
        ]
        run = GameRun(user_id=self.uid, player=p1, enemies=enemies, node_type="battle")
        self.sm.save_save(self.uid, run)

        res_auto = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertNotIn("请选择", res_auto)
        mid = load_run(self.plugin, self.uid)
        self.assertEqual(mid.enemies[0].hp, 47)
        self.assertEqual(len(mid.node_data.get("state_stack", [])), 0)

        res_e_pinyin = await run_command(self.plugin, "p 1 e:gbl", sender_id=self.uid)
        self.assertIn("哥布林", res_e_pinyin)
        mid2 = load_run(self.plugin, self.uid)
        self.assertEqual(mid2.enemies[1].hp, 47)

        res_m_pinyin = await run_command(self.plugin, "p 1 m:yb", sender_id=self.uid)
        self.assertIn("雇佣兵", res_m_pinyin)
        end = load_run(self.plugin, self.uid)
        self.assertEqual(end.player.minions["1"].hp, 10)

        res_back_idle = await run_command(self.plugin, "back", sender_id=self.uid)
        self.assertIn("没有可退回的交互选择", res_back_idle)

    async def test_ninja_frog_frog_go_select_exhaust_flow(self):
        p1 = PlayerState(
            name="忍者",
            hp=60,
            max_hp=80,
            shield=0,
            gold=0,
            actions=1,
            bonus_actions=0,
            lex_kela=2,
            deck=[CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
            hand=[CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
        )
        run = GameRun(
            user_id=self.uid,
            player=p1,
            enemies=[EnemyState(name="木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
        )
        self.sm.save_save(self.uid, run)

        prompt = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertIn("蛤蟆蛤蟆go", prompt)
        self.assertIn("火焰弹", prompt)
        self.assertIn("防御", prompt)
        mid = load_run(self.plugin, self.uid)
        self.assertEqual(len(mid.node_data.get("state_stack", [])), 1)

        res = await run_command(self.plugin, "c 2", sender_id=self.uid)
        self.assertIn("蛤蟆蛤蟆go", res)
        self.assertIn("防御", res)
        after = load_run(self.plugin, self.uid)
        self.assertEqual(len(after.node_data.get("state_stack", [])), 0)
        self.assertEqual([c.id for c in after.player.hand], ["fire_bolt"])
        exhaust_ids = [c.id for c in after.player.exhaust_pile]
        self.assertIn("warrior_defend", exhaust_ids)
        self.assertIn("ninja_frog_frog_go", exhaust_ids)
        self.assertEqual(after.player.actions, 2)
        self.assertEqual(after.player.lex_kela, 1)

        after.player.hand = [CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt"), CardState(id="warrior_defend")]
        after.player.exhaust_pile = []
        after.player.lex_kela = 2
        self.sm.save_save(self.uid, after)
        res_inline = await run_command(self.plugin, "p 1 h:fy", sender_id=self.uid)
        self.assertNotIn("请选择", res_inline)
        self.assertIn("防御", res_inline)
        after_inline = load_run(self.plugin, self.uid)
        self.assertEqual([c.id for c in after_inline.player.hand], ["fire_bolt"])
        self.assertIn("warrior_defend", [c.id for c in after_inline.player.exhaust_pile])

        after_inline.player.hand = [CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt")]
        after_inline.player.exhaust_pile = []
        after_inline.player.lex_kela = 1
        self.sm.save_save(self.uid, after_inline)
        res_auto = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertNotIn("请选择", res_auto)
        self.assertIn("火焰弹", res_auto)
        after_auto = load_run(self.plugin, self.uid)
        self.assertEqual(after_auto.player.hand, [])
        self.assertIn("fire_bolt", [c.id for c in after_auto.player.exhaust_pile])

    async def test_r_and_status_render_screen_and_prompt_during_selection(self):
        p1 = PlayerState(
            name="忍者",
            hp=60,
            max_hp=80,
            shield=0,
            gold=0,
            actions=2,
            bonus_actions=0,
            lex_kela=2,
            deck=[CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
            hand=[CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
        )
        run = GameRun(
            user_id=self.uid,
            player=p1,
            enemies=[EnemyState(name="木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
        )
        self.sm.save_save(self.uid, run)

        await run_command(self.plugin, "p 1", sender_id=self.uid)
        for cmd in ("r", "status"):
            out = await run_command(self.plugin, cmd, sender_id=self.uid)
            self.assertNotIn("❌", out)
            self.assertIn("木桩", out)
            self.assertIn("蛤蟆蛤蟆go", out)
            self.assertIn("火焰弹", out)
        self.assertEqual(len(load_run(self.plugin, self.uid).node_data.get("state_stack", [])), 1)
        done = await run_command(self.plugin, "c 1", sender_id=self.uid)
        self.assertIn("火焰弹", done)
        self.assertEqual(len(load_run(self.plugin, self.uid).node_data.get("state_stack", [])), 0)

    async def test_mercenary_auto_resolves_selection_cards(self):
        merc_uid = f"merc_{self.uid}_1"
        p1 = PlayerState(
            name="队长",
            hp=70,
            max_hp=80,
            shield=0,
            gold=0,
            actions=1,
            bonus_actions=0,
            deck=[CardState(id="fire_bolt")],
            hand=[CardState(id="fire_bolt")],
        )
        merc = PlayerState(
            name="忍者佣兵",
            hp=60,
            max_hp=60,
            shield=0,
            gold=0,
            actions=2,
            bonus_actions=0,
            lex_kela=2,
            is_mercenary=True,
            mercenary_owner=self.uid,
            mercenary_timing="after",
            deck=[CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
            hand=[CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
        )
        run = GameRun(
            user_id=self.uid,
            player=p1,
            enemies=[EnemyState(name="木桩", hp=200, max_hp=200, shield=0, intent_desc="待机")],
            node_type="battle",
            node_data={"turn_ready": {self.uid: False, merc_uid: True}},
            party_order=[self.uid, merc_uid],
            players={self.uid: p1, merc_uid: merc},
        )
        self.sm.save_save(self.uid, run)

        end_out = await run_command(self.plugin, "e", sender_id=self.uid)
        self.assertIn("蛤蟆蛤蟆go", end_out)
        self.assertNotIn("请选择 1 张要消耗的手牌", end_out)
        after = load_run(self.plugin, self.uid)
        self.assertEqual(len(after.node_data.get("state_stack", [])), 0)
        self.assertIn("ninja_frog_frog_go", [c.id for c in after.players[merc_uid].exhaust_pile])
        self.assertGreaterEqual(len(after.players[merc_uid].exhaust_pile), 2)

    async def test_coop_selection_state_does_not_leak_to_teammate(self):
        ally_uid = "coop_sel_ally"
        run_id = "run_sel_iso_1"
        p1 = PlayerState(
            name="队友甲",
            hp=70,
            max_hp=80,
            shield=0,
            gold=0,
            actions=2,
            bonus_actions=0,
            lex_kela=2,
            deck=[CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
            hand=[CardState(id="ninja_frog_frog_go"), CardState(id="fire_bolt"), CardState(id="warrior_defend")],
        )
        p2 = PlayerState(
            name="队友乙",
            hp=70,
            max_hp=80,
            shield=0,
            gold=0,
            actions=2,
            bonus_actions=2,
            deck=[CardState(id="fire_bolt")],
            hand=[CardState(id="fire_bolt")],
        )
        run = GameRun(
            user_id=self.uid,
            run_id=run_id,
            player=p1,
            enemies=[EnemyState(name="木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
            party_order=[self.uid, ally_uid],
            players={self.uid: p1, ally_uid: p2},
        )
        for uid in (self.uid, ally_uid):
            st = self.sm.load_stats(uid)
            st.rogue_mode = True
            st.active_run_id = run_id
            self.sm.save_stats(uid, st)
        self.sm.save_save(self.uid, run)

        p1_prompt = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertIn("蛤蟆蛤蟆go", p1_prompt)
        self.assertEqual(len(load_run(self.plugin, self.uid).node_data.get("state_stack", [])), 1)

        p2_run = load_run(self.plugin, ally_uid)
        self.assertEqual(len(p2_run.node_data.get("state_stack", [])), 0)
        p2_status = await run_command(self.plugin, "r", sender_id=ally_uid)
        self.assertNotIn("请选择 1 张要消耗的手牌", p2_status)

        p2_play = await run_command(self.plugin, "p 1", sender_id=ally_uid)
        self.assertIn("火焰弹", p2_play)
        self.assertEqual(load_run(self.plugin, ally_uid).enemies[0].hp, 97)

        p1_finish = await run_command(self.plugin, "c 2", sender_id=self.uid)
        self.assertIn("防御", p1_finish)
        p1_after = load_run(self.plugin, self.uid)
        self.assertEqual(len(p1_after.node_data.get("state_stack", [])), 0)
        self.assertIn("warrior_defend", [c.id for c in p1_after.players[self.uid].exhaust_pile])

    async def test_ninja_frog_frog_go_prompt_lists_options_and_echo_replay_triggers_multiple_selections(self):
        from game.models.state import BuffState
        p1 = PlayerState(
            name="忍者",
            hp=60,
            max_hp=80,
            shield=0,
            gold=0,
            actions=1,
            bonus_actions=0,
            lex_kela=3,
            buffs=[BuffState(id="echo_form", name="回响形态", desc="回响", stacks=1)],
            deck=[
                CardState(id="ninja_frog_frog_go", replay=1),
                CardState(id="fire_bolt"),
                CardState(id="warrior_defend"),
                CardState(id="warrior_strike"),
                CardState(id="first_aid"),
            ],
            hand=[
                CardState(id="ninja_frog_frog_go", replay=1),
                CardState(id="fire_bolt"),
                CardState(id="warrior_defend"),
                CardState(id="warrior_strike"),
                CardState(id="first_aid"),
            ],
        )
        run = GameRun(
            user_id=self.uid,
            player=p1,
            enemies=[EnemyState(name="木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
        )
        self.sm.save_save(self.uid, run)

        prompt1 = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertIn("1. 火焰弹", prompt1)
        self.assertIn("2. 防御", prompt1)
        self.assertIn("3. 打击", prompt1)
        self.assertIn("4. 绷带包扎", prompt1)

        prompt2 = await run_command(self.plugin, "c 1", sender_id=self.uid)
        self.assertIn("火焰弹", prompt2)
        self.assertIn("1. 防御", prompt2)
        self.assertIn("2. 打击", prompt2)
        self.assertIn("3. 绷带包扎", prompt2)
        mid1 = load_run(self.plugin, self.uid)
        self.assertEqual(len(mid1.node_data.get("state_stack", [])), 1)
        self.assertEqual(mid1.node_data["state_stack"][-1].get("phase"), "extra_play")

        prompt3 = await run_command(self.plugin, "c 2", sender_id=self.uid)
        self.assertIn("打击", prompt3)
        self.assertIn("1. 防御", prompt3)
        self.assertIn("2. 绷带包扎", prompt3)
        mid2 = load_run(self.plugin, self.uid)
        self.assertEqual(len(mid2.node_data.get("state_stack", [])), 1)
        self.assertEqual(mid2.node_data["state_stack"][-1].get("phase"), "extra_play")

        done = await run_command(self.plugin, "c 1", sender_id=self.uid)
        self.assertIn("防御", done)
        after = load_run(self.plugin, self.uid)
        self.assertEqual(len(after.node_data.get("state_stack", [])), 0)
        self.assertEqual([c.id for c in after.player.hand], ["first_aid"])
        exhaust_ids = [c.id for c in after.player.exhaust_pile]
        self.assertIn("fire_bolt", exhaust_ids)
        self.assertIn("warrior_strike", exhaust_ids)
        self.assertIn("warrior_defend", exhaust_ids)
        self.assertIn("ninja_frog_frog_go", exhaust_ids)
        self.assertEqual(after.player.actions, 4)
        self.assertEqual(after.player.lex_kela, 0)

    async def test_ninja_back_fourth_hand_select_retrieve_and_discard_with_echo(self):
        from game.models.state import BuffState
        p1 = PlayerState(
            name="忍者",
            hp=60,
            max_hp=80,
            shield=0,
            gold=0,
            actions=2,
            bonus_actions=0,
            buffs=[BuffState(id="echo_form", name="回响形态", desc="回响", stacks=1)],
            deck=[
                CardState(id="ninja_back_fourth_hand"),
                CardState(id="dagger_throw"),
                CardState(id="first_aid"),
                CardState(id="fire_bolt"),
                CardState(id="warrior_defend"),
                CardState(id="warrior_strike"),
            ],
            hand=[
                CardState(id="ninja_back_fourth_hand"),
                CardState(id="dagger_throw"),
                CardState(id="first_aid"),
            ],
            discard_pile=[
                CardState(id="fire_bolt"),
                CardState(id="warrior_defend"),
                CardState(id="warrior_strike"),
            ],
        )
        run = GameRun(
            user_id=self.uid,
            player=p1,
            enemies=[EnemyState(name="木桩", hp=100, max_hp=100, shield=0, intent_desc="待机")],
            node_type="battle",
        )
        self.sm.save_save(self.uid, run)

        retrieve_prompt = await run_command(self.plugin, "p 1", sender_id=self.uid)
        self.assertIn("1. 火焰弹", retrieve_prompt)
        self.assertIn("2. 防御", retrieve_prompt)
        self.assertIn("3. 打击", retrieve_prompt)

        discard_prompt = await run_command(self.plugin, "c 1 3", sender_id=self.uid)
        self.assertIn("哈回米内四又反手", discard_prompt)
        self.assertIn("1. 匕首投掷", discard_prompt)
        self.assertIn("2. 绷带包扎", discard_prompt)
        self.assertIn("3. 火焰弹", discard_prompt)
        self.assertIn("4. 打击", discard_prompt)
        mid = load_run(self.plugin, self.uid)
        self.assertEqual(mid.player.shield, 8)
        self.assertEqual(mid.node_data["state_stack"][-1].get("phase"), "post_play")

        echo_retrieve_prompt = await run_command(self.plugin, "c 2 3", sender_id=self.uid)
        self.assertIn("绷带包扎", echo_retrieve_prompt)
        self.assertIn("火焰弹", echo_retrieve_prompt)
        self.assertIn("1. 防御", echo_retrieve_prompt)
        mid_echo = load_run(self.plugin, self.uid)
        self.assertEqual(mid_echo.node_data["state_stack"][-1].get("phase"), "extra_play")

        echo_discard_prompt = await run_command(self.plugin, "c 1 2", sender_id=self.uid)
        self.assertIn("请选择 2 张要丢弃的手牌", echo_discard_prompt)
        mid_echo2 = load_run(self.plugin, self.uid)
        self.assertEqual(mid_echo2.player.shield, 16)
        self.assertEqual(mid_echo2.node_data["state_stack"][-1].get("phase"), "post_play")

        done = await run_command(self.plugin, "c 1 2", sender_id=self.uid)
        self.assertIn("丢弃了手牌", done)
        after = load_run(self.plugin, self.uid)
        self.assertEqual(len(after.node_data.get("state_stack", [])), 0)
        self.assertEqual(len(after.player.hand), 2)
        self.assertEqual(after.player.shield, 16)
