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
            stage=1,
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
            stage=1,
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
            stage=1,
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
            stage=1,
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
            stage=1,
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
            stage=1,
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
            stage=1,
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
            stage=1,
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
            stage=1,
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
