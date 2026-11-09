import unittest
from scratch.rogue_tests.base import *

class TestRogueEnemyStage(unittest.TestCase):
    def test_dynamic_boss_victory_message(self):
        class DummySaveManager:
            def __init__(self):
                self.stats = UserStats()
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return self.stats
            def save_stats(self, user_id, stats):
                self.stats = stats
                return True
            def settle_game_and_delete(self, user_id, run, is_victory=True):
                return "游戏已成功结算并清理。"
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        router = CLIRouter(sm, engine)
        player = PlayerState(
            hp=50,
            max_hp=50,
            shield=0,
            gold=100,
            stage=25,
            deck=["fire_bolt"],
            hand=["fire_bolt"],
            actions=2,
            bonus_actions=1
        )
        enemy = EnemyState("Icerainboww", 1, 160, 0)
        run = GameRun(
            user_id="test_victory_user",
            node_type="battle",
            player=player,
            enemies=[enemy],
            node_data={"boss_name": "Icerainboww"}
        )
        res, term, success = router._execute_sub_action("test_victory_user", run, ["使用", "1", "e1"])
        self.assertTrue(term)
        self.assertIn("恭喜你击败了Icerainboww，通关成功！", res)
        self.assertNotIn("腐化之心", res)

    def test_expanded_monsters_and_mechanics(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        sm = DummySaveManager()
        engine = BattleEngine(sm)

        cultist = EnemyState("邪教徒咔咔", 15, 15, 0)
        p_state = PlayerState(hp=50, max_hp=50, shield=0, gold=10, stage=1)
        run = GameRun(user_id="test_exp", node_type="battle", player=p_state, enemies=[cultist])

        from game.entities.enemies.normal.cultist_kaka import CultistKakaTemplate
        c_temp = CultistKakaTemplate("邪教徒咔咔")

        intents_1 = c_temp.roll_intents(run, engine, cultist)
        self.assertEqual(len(intents_1), 1)
        self.assertEqual(intents_1[0].type, "caw")

        c_logs_1 = []
        c_temp.execute_intent(run, engine, cultist, intents_1[0], c_logs_1)
        self.assertTrue(any(b.id == "ritual" for b in cultist.buffs))
        self.assertIn("咔咔", "".join(c_logs_1))

        from game.models.events import TurnStartEvent
        evt_start = TurnStartEvent(run, is_player=False)
        engine.event_bus.dispatch(evt_start)
        self.assertTrue(any(b.id == "strength" and b.stacks == 1 for b in cultist.buffs))

        intents_2 = c_temp.roll_intents(run, engine, cultist)
        self.assertEqual(intents_2[0].type, "peck")

        run.player.hp = 50
        c_logs_2 = []
        c_temp.execute_intent(run, engine, cultist, intents_2[0], c_logs_2)
        self.assertEqual(run.player.hp, 43)

        flayer = EnemyState("夺心魔", 48, 48, 0, max_actions=1, max_bonus_actions=1)
        run.enemies = [flayer]

        from game.entities.enemies.elite.mind_flayer import MindFlayerTemplate
        f_temp = MindFlayerTemplate("夺心魔")

        run.player.buffs.clear()
        intents_f1 = f_temp.roll_intents(run, engine, flayer)
        self.assertEqual(len(intents_f1), 2)

        tentacles_intent = next((it for it in intents_f1 if it.type == "tentacles"), None)
        if not tentacles_intent:
            from game.models.state import EnemyIntentState
            tentacles_intent = EnemyIntentState(type="tentacles", val=8, desc="触须袭击")
        f_logs_1 = []
        f_temp.execute_intent(run, engine, flayer, tentacles_intent, f_logs_1)
        self.assertTrue(any(b.id == "grappled" for b in run.player.buffs))

        import random
        old_random = random.random
        random.random = lambda: 0.0
        try:
            intents_f2 = f_temp.roll_intents(run, engine, flayer)
        finally:
            random.random = old_random
        self.assertTrue(any(it.type == "extract_brain" for it in intents_f2))

        eb_intent = next(it for it in intents_f2 if it.type == "extract_brain")
        run.player.hp = 50
        f_logs_2 = []
        f_temp.execute_intent(run, engine, flayer, eb_intent, f_logs_2)
        self.assertEqual(run.player.hp, 25)

        blast_intent = next((it for it in intents_f1 if it.type == "mind_blast"), None)
        if not blast_intent:
            from game.models.state import EnemyIntentState
            blast_intent = EnemyIntentState(type="mind_blast", val=8, desc="心灵震爆")
        f_logs_3 = []
        f_temp.execute_intent(run, engine, flayer, blast_intent, f_logs_3)
        self.assertTrue(any(b.id == "stun" for b in run.player.buffs))

        run.player.actions = 2
        run.player.bonus_actions = 1
        evt_p_start = TurnStartEvent(run, is_player=True)
        engine.event_bus.dispatch(evt_p_start)
        self.assertEqual(run.player.actions, 0)
        self.assertEqual(run.player.bonus_actions, 0)
        self.assertFalse(any(b.id == "stun" for b in run.player.buffs))

        pirate = EnemyState("吉斯洋基海盗", 18, 18, 0, max_actions=1, max_bonus_actions=0)
        run.enemies = [pirate]

        from game.entities.enemies.normal.githyanki_pirate import GithyankiPirateTemplate
        p_temp = GithyankiPirateTemplate("吉斯洋基海盗")

        run.player.shield = 10
        run.player.hp = 50
        slash_intent = next((it for it in p_temp.roll_intents(run, engine, pirate) if it.type == "silver_sword"), None)
        if not slash_intent:
            from game.models.state import EnemyIntentState
            slash_intent = EnemyIntentState(type="silver_sword", val=7, desc="银剑")
        p_logs_1 = []
        p_temp.execute_intent(run, engine, pirate, slash_intent, p_logs_1)
        self.assertEqual(run.player.shield, 0)
        self.assertEqual(run.player.hp, 49)

        step_intent = next((it for it in p_temp.roll_intents(run, engine, pirate) if it.type == "astral_step"), None)
        if not step_intent:
            from game.models.state import EnemyIntentState
            step_intent = EnemyIntentState(type="astral_step", val=6, desc="跃迁")
        p_logs_2 = []
        p_temp.execute_intent(run, engine, pirate, step_intent, p_logs_2)
        self.assertTrue(any(b.id == "astral_speed" for b in pirate.buffs))

        intents_p3 = p_temp.roll_intents(run, engine, pirate)
        self.assertEqual(len(intents_p3), 2)
        self.assertFalse(any(b.id == "astral_speed" for b in pirate.buffs))

        commander = EnemyState("吉斯洋基至高指挥官", 55, 55, 0, max_actions=1, max_bonus_actions=1)
        run.enemies = [commander]

        from game.entities.enemies.elite.githyanki_supreme_commander import GithyankiSupremeCommanderTemplate
        cmd_temp = GithyankiSupremeCommanderTemplate("吉斯洋基至高指挥官")

        cmd_logs_1 = []
        sh_intent = next((it for it in cmd_temp.roll_intents(run, engine, commander) if it.type == "summon_hound"), None)
        if not sh_intent:
            from game.models.state import EnemyIntentState
            sh_intent = EnemyIntentState(type="summon_hound", val=0, desc="星界呼唤")
        cmd_temp.execute_intent(run, engine, commander, sh_intent, cmd_logs_1)
        self.assertEqual(len(run.enemies), 2)
        self.assertEqual(run.enemies[1].name, "星界幼犬")

        cmd_logs_2 = []
        cp_intent = next((it for it in cmd_temp.roll_intents(run, engine, commander) if it.type == "commanding_presence"), None)
        if not cp_intent:
            from game.models.state import EnemyIntentState
            cp_intent = EnemyIntentState(type="commanding_presence", val=2, desc="指挥")
        cmd_temp.execute_intent(run, engine, commander, cp_intent, cmd_logs_2)
        self.assertTrue(any(b.id == "strength" and b.stacks == 2 for b in commander.buffs))
        self.assertTrue(any(b.id == "strength" and b.stacks == 2 for b in run.enemies[1].buffs))

    def test_yog_reflect_requires_shield_and_query(self):
        from game.renderer import render_query_info

        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return UserStats()

        engine = BattleEngine(DummySaveManager())
        cases = (
            ("ancient_protection", "先古庇护", 98),
            ("end_gate_passive", "终焉之门", 99),
            ("doomsday_gate_passive", "终焉庇护", 97),
        )
        for buff_id, buff_name, shielded_hp in cases:
            for shield in (10, 0):
                player = PlayerState(100, 100, 0, 0, 1, name="测试")
                enemy = EnemyState(
                    "测试尤格",
                    500,
                    500,
                    shield,
                    buffs=[BuffState(buff_id, buff_name)],
                )
                run = GameRun("test_yog_reflect", "battle", player, [enemy], {}, {})
                engine._damage_target(run, "e1", 10, damage_type="force")
                if shield > 0:
                    self.assertEqual(player.hp, shielded_hp)
                else:
                    self.assertEqual(player.hp, 100)

        q_gate = render_query_info("终焉之门")
        self.assertIn("拥有护盾时", q_gate)
        self.assertIn("反弹", q_gate)
        q_awaken = render_query_info("【觉醒】虚空之门·尤格-索托斯")
        self.assertIn("拥有护盾时", q_awaken)
        self.assertIn("反弹", q_awaken)
        q_end = render_query_info("【终焉】虚空之门·尤格-索托斯")
        self.assertIn("拥有护盾时", q_end)
        self.assertIn("反弹", q_end)

    def test_enemy_trash_talk(self):
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
            deck=["fire_bolt"],
            hand=["fire_bolt"],
            actions=1,
            bonus_actions=1
        )
        run = GameRun(
            user_id="test_trash",
            node_type="battle",
            player=player,
            enemies=[]
        )
        run.node_data["turn"] = 1

        from game.entities.enemies.summon.astral_puppy import AstralPuppyTemplate
        puppy_enemy = EnemyState("星界幼犬", 15, 15, 0)
        puppy_temp = AstralPuppyTemplate("星界幼犬")
        puppy_intents = puppy_temp.roll_intents(run, engine, puppy_enemy)
        logs = []
        puppy_temp.execute_intent(run, engine, puppy_enemy, puppy_intents[0], logs)
        self.assertFalse(any("【" in log and "】说" in log for log in logs))

        from game.entities.enemies.town_enemies import NoobSlayer99Template
        noob_enemy = EnemyState("NoobSlayer99", 50, 50, 0)
        noob_temp = NoobSlayer99Template("NoobSlayer99")
        noob_intents = noob_temp.roll_intents(run, engine, noob_enemy)
        
        logs_noob = []
        noob_temp.execute_intent(run, engine, noob_enemy, noob_intents[0], logs_noob)
        self.assertEqual(len(logs_noob), 2)
        
        logs_noob_2 = []
        noob_temp.execute_intent(run, engine, noob_enemy, noob_intents[0], logs_noob_2)
        self.assertEqual(len(logs_noob_2), 1)

        run.node_data["turn"] = 2
        player.hp = 20
        player.max_hp = 100
        noob_intents_2 = noob_temp.roll_intents(run, engine, noob_enemy)
        logs_noob_3 = []
        noob_temp.execute_intent(run, engine, noob_enemy, noob_intents_2[0], logs_noob_3)
        self.assertTrue(any("单手" in log or "送你一程" in log or "双手离开" in log for log in logs_noob_3))

        run.node_data["turn"] = 3
        player.hp = 80
        player.shield = 20
        noob_intents_3 = noob_temp.roll_intents(run, engine, noob_enemy)
        logs_noob_4 = []
        noob_temp.execute_intent(run, engine, noob_enemy, noob_intents_3[0], logs_noob_4)
        self.assertTrue(any("乌龟壳" in log or "最厚的甲" in log or "属乌龟" in log for log in logs_noob_4))

        run.node_data["turn"] = 4
        player.shield = 0
        player.hand = ["fire_bolt"] * 12
        noob_intents_4 = noob_temp.roll_intents(run, engine, noob_enemy)
        logs_noob_5 = []
        noob_temp.execute_intent(run, engine, noob_enemy, noob_intents_4[0], logs_noob_5)
        self.assertTrue(any("斗地主" in log or "废纸" in log for log in logs_noob_5))

        run.node_data["turn"] = 5
        player.hand = ["fire_bolt"]
        noob_intents_5 = noob_temp.roll_intents(run, engine, noob_enemy)
        logs_noob_6 = []
        noob_temp.execute_intent(run, engine, noob_enemy, noob_intents_5[0], logs_noob_6)
        self.assertTrue(any("没牌" in log or "空手" in log or "个人秀" in log or "血虐" in log for log in logs_noob_6))

    def test_boss_selection_by_stage(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return None
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        
        stages_12_bosses = set()
        for _ in range(50):
            player = PlayerState(hp=100, max_hp=100, shield=0, gold=100, stage=12)
            run = GameRun(user_id="test_boss", node_type="battle", player=player)
            engine._init_battle_node(run, "boss")
            stages_12_bosses.add(run.enemies[0].name)
        self.assertEqual(stages_12_bosses, {"远古红龙", "雷霆领主"})
        
        stages_25_bosses = set()
        for _ in range(50):
            player = PlayerState(hp=100, max_hp=100, shield=0, gold=100, stage=25)
            run = GameRun(user_id="test_boss", node_type="battle", player=player)
            engine._init_battle_node(run, "boss")
            stages_25_bosses.add(run.enemies[0].name)
        self.assertEqual(stages_25_bosses, {"腐化之心", "Icerainboww"})
        
        player31 = PlayerState(hp=100, max_hp=100, shield=0, gold=100, stage=31)
        run31 = GameRun(user_id="test_boss", node_type="battle", player=player31)
        engine._init_battle_node(run31, "boss")
        self.assertEqual(run31.enemies[0].name, "亚弗戈蒙")
        
        player32 = PlayerState(hp=100, max_hp=100, shield=0, gold=100, stage=32)
        run32 = GameRun(user_id="test_boss", node_type="battle", player=player32)
        engine._init_battle_node(run32, "boss")
        self.assertEqual(run32.enemies[0].name, "虚空之门·尤格-索托斯")

    def test_aforgomon_boss_mechanisms(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return None
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(hp=100, max_hp=100, shield=0, gold=100, stage=31, name="测试玩家")
        run = GameRun(user_id="test_user", node_type="battle", player=player)
        engine._init_battle_node(run, "boss")
        
        boss = run.enemies[0]
        self.assertEqual(boss.name, "亚弗戈蒙")
        self.assertEqual(boss.hp, 180)
        
        from game.renderer import render_query_info
        res_afor = render_query_info("【时空主宰】亚弗戈蒙")
        self.assertFalse("未找到" in res_afor)
        res_yog = render_query_info("【终焉】虚空之门·尤格-索托斯")
        self.assertFalse("未找到" in res_yog)
        
        intents_p1 = engine.enemy_controller.roll_enemy_intent(run)
        self.assertTrue(len(boss.intents) >= 2)
        
        engine._damage_target(run, "e1", 180, damage_type="true")
        self.assertEqual(boss.name, "亚弗戈蒙")
        self.assertEqual(boss.hp, 1)
        engine._enemy_turn(run)
        self.assertEqual(boss.name, "【时空主宰】亚弗戈蒙")
        self.assertEqual(boss.hp, 220)
        self.assertEqual(boss.max_hp, 220)
        
        has_res = any(b.id == "pendulum_resonance" for b in player.buffs)
        self.assertTrue(has_res)
        
        intents_p2 = engine.enemy_controller.roll_enemy_intent(run)
        self.assertTrue(len(boss.intents) >= 3)
        
        from game.entities.enemies.boss import BossAforgomonTemplate
        from game.models.state import EnemyIntentState, CardState
        aforgomon_temp = BossAforgomonTemplate("亚弗戈蒙")
        
        player.hand = [CardState("strike"), CardState("defend"), CardState("strike")]
        intent_tf = EnemyIntentState(type="time_fracture", val=12, desc="", cost_a=1, cost_ba=0)
        logs_tf = []
        aforgomon_temp.execute_intent(run, engine, boss, intent_tf, logs_tf)
        self.assertEqual(player.hand[0].fragile, 0)
        self.assertEqual(player.hand[1].fragile, 1)
        self.assertEqual(player.hand[2].fragile, 1)
        
        player.buffs = [b for b in player.buffs if b.id != "pendulum_resonance"]
        intent_sbc = EnemyIntentState(type="silver_bell_clang", val=15, desc="", cost_a=1, cost_ba=0)
        logs_sbc = []
        aforgomon_temp.execute_intent(run, engine, boss, intent_sbc, logs_sbc)
        has_res2 = any(b.id == "pendulum_resonance" for b in player.buffs)
        self.assertTrue(has_res2)
        
        player.hp = 100
        logs_sbc2 = []
        aforgomon_temp.execute_intent(run, engine, boss, intent_sbc, logs_sbc2)
        self.assertEqual(player.hp, 80)
        
        boss.hp = 100
        boss.shield = 0
        intent_tr = EnemyIntentState(type="time_reflux", val=0, desc="", cost_a=1, cost_ba=0)
        logs_tr = []
        aforgomon_temp.execute_intent(run, engine, boss, intent_tr, logs_tr)
        self.assertEqual(boss.hp, 125)
        self.assertEqual(boss.shield, 20)
        
        player.hand = [CardState("strike")]
        intent_tl = EnemyIntentState(type="temporal_lock", val=5, desc="", cost_a=0, cost_ba=1)
        logs_tl = []
        aforgomon_temp.execute_intent(run, engine, boss, intent_tl, logs_tl)
        self.assertTrue(any(b.id == "discard_next_turn" for b in player.buffs))
        
        import unittest.mock as mock
        with mock.patch("random.random", return_value=0.1):
            from game.models.events import TurnStartEvent
            evt = TurnStartEvent(run=run, is_player=False)
            engine.event_bus.dispatch(evt)
            
        self.assertTrue(any(e.name == "时空残影" for e in run.enemies))
        
        echo_enemy = next(e for e in run.enemies if e.name == "时空残影")
        self.assertEqual(echo_enemy.hp, 15)
        
        player.hp = 100
        boss.hp = 220
        boss.shield = 0
        boss.buffs = [b for b in boss.buffs if b.id != "phase_transition_immune"]
        engine._damage_target(run, "e1", 20, damage_type="slashing")
        self.assertEqual(boss.hp, 210)
        self.assertEqual(echo_enemy.hp, 5)
        self.assertEqual(player.hp, 100)
        
        player.actions = 0
        player.bonus_actions = 1
        run.node_data["cards_played_this_turn"] = 3
        player.hp = 100
        from game.models.events import TurnEndEvent
        evt_end = TurnEndEvent(run=run, is_player=True)
        engine.event_bus.dispatch(evt_end)
        self.assertEqual(player.hp, 94)
        
        player.actions = 1
        player.bonus_actions = 1
        run.node_data["cards_played_this_turn"] = 3
        player.hp = 100
        evt_end2 = TurnEndEvent(run=run, is_player=True)
        engine.event_bus.dispatch(evt_end2)
        self.assertEqual(player.hp, 100)
        self.assertEqual(run.node_data.get("draw_penalty_next_turn"), -2)

    def test_coc_creatures_and_relics(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return None
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(hp=80, max_hp=80, shield=10, gold=100, stage=1, relics=["leng_spider_venom", "migo_lightning_gun", "shoggoth_slime", "star_vampire_proboscis", "starspawn_core"])
        
        from game.entities.enemies.normal.coc_creatures import DeepOneTemplate, GhoulTemplate, ShantakTemplate
        from game.entities.enemies.elite.coc_elites import MigoTemplate, StarspawnOfCthulhuTemplate
        from game.models.state import EnemyIntentState, CardState
        
        deep_one = EnemyState("深潜者", 20, 20, 0)
        run = GameRun(user_id="test_coc", node_type="battle", player=player, enemies=[deep_one])
        deep_temp = DeepOneTemplate("深潜者")
        logs_deep = []
        intent_deep = EnemyIntentState(type="tsunami_strike", val=5, desc="")
        deep_temp.execute_intent(run, engine, deep_one, intent_deep, logs_deep)
        self.assertTrue(player.shield < 10)
        
        migo = EnemyState("米·戈", 30, 30, 0)
        run_migo = GameRun(user_id="test_coc_migo", node_type="battle", player=player, enemies=[migo])
        migo_temp = MigoTemplate("米·戈")
        logs_migo = []
        intent_migo = EnemyIntentState(type="bio_shield", val=10, desc="")
        engine._add_buff_to(migo, "stun", "眩晕", "", 1)
        migo_temp.execute_intent(run_migo, engine, migo, intent_migo, logs_migo)
        self.assertFalse(any(b.id == "stun" for b in migo.buffs))
        
        migo.shield = 0
        from game.models.events import BattleStartEvent
        evt_start = BattleStartEvent(run=run_migo)
        engine.event_bus.dispatch(evt_start)
        self.assertEqual(migo.hp, 25)
        
        engine._damage_target(run_migo, "p0", 10, damage_type="slashing")
        self.assertEqual(player.shield, 4)
        
        from game.models.events import CardPlayedEvent, Card
        card_dummy = Card(id="test_card", name="测试牌", cost_a=1, cost_ba=0, type="spell", rarity="common", desc="", color="neutral")
        setattr(card_dummy, "exhaust", True)
        evt_played = CardPlayedEvent(run=run, card=card_dummy, target="e1")
        engine.event_bus.dispatch(evt_played)
        self.assertTrue(player.hp > 70)
        
        player.bonus_actions = 1
        from game.models.events import TurnEndEvent
        evt_end = TurnEndEvent(run=run_migo, is_player=True)
        engine.event_bus.dispatch(evt_end)
        self.assertEqual(migo.hp, 15)

    def test_mindflayer_brain_modification(self):
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
            def load_stats(self, user_id):
                return None
        sm = DummySaveManager()
        engine = BattleEngine(sm)
        player = PlayerState(hp=80, max_hp=80, shield=10, gold=100, stage=1, relics=["mindflayer_brain"])
        enemy = EnemyState("测试敌人", 50, 50, 0)
        run = GameRun(user_id="test_mindflayer", node_type="battle", player=player, enemies=[enemy])
        
        from game.models.state import CardState
        player.hand = [CardState("strike")]
        engine.card_player.discard_card(run, player.hand[0])
        self.assertEqual(enemy.hp, 47)
        
        enemy.hp = 50
        player.hand = [CardState("strike")]
        engine.card_player.end_turn(run)
        self.assertEqual(enemy.hp, 50)

    def test_phase_transition_immune_damage_blocks(self):
        class DummySaveManager:
            def save_save(self, user_id, run): pass
        engine = BattleEngine(DummySaveManager())
        player = PlayerState(hp=80, max_hp=80, shield=10, gold=100, stage=1)
        enemy = EnemyState("测试敌人", 50, 50, 0)
        run = GameRun(user_id="test_pt", node_type="battle", player=player, enemies=[enemy])
        from game.models.state import BuffState
        enemy.buffs.append(BuffState(id="phase_transition_immune", name="转换阶段", stacks=1, desc="处于转换阶段状态，免疫所有伤害"))
        engine._damage_target(run, "e1", 10, damage_type="slashing")
        self.assertEqual(enemy.hp, 50)
        engine._damage_target(run, "e1", 15, damage_type="true")
        self.assertEqual(enemy.hp, 50)

    def test_monster_intent_buffs_and_deductions(self):
        class DummySaveManager:
            def save_save(self, user_id, run): pass
            def load_stats(self, user_id): return None
        engine = BattleEngine(DummySaveManager())
        player = PlayerState(hp=80, max_hp=80, shield=10, gold=100, stage=1)
        enemy = EnemyState("测试敌人", 50, 50, 0)
        run = GameRun(user_id="test_intents", node_type="battle", player=player, enemies=[enemy])
        engine._add_buff_to(player, "drain_a", "时间纠缠", "在下一回合开始时，你将失去等同于此状态层数的动作点 (A)", 1)
        engine._add_buff_to(player, "drain_ba", "虚空纠缠", "在下一回合开始时，你将失去等同于此状态层数的附赠动作点 (BA)", 1)
        engine._add_buff_to(player, "discard_next_turn", "下回合弃牌", "在下一回合开始时，你将随机丢弃等同于此状态层数的手牌", 2)
        self.assertTrue(any(b.id == "drain_a" for b in player.buffs))
        self.assertTrue(any(b.id == "drain_ba" for b in player.buffs))
        self.assertTrue(any(b.id == "discard_next_turn" for b in player.buffs))
        from game.models.state import CardState
        player.deck = ["strike", "strike", "strike", "strike", "strike", "strike", "strike", "strike"]
        player.hand = []
        player.draw_pile = player.deck.copy()
        engine.card_player.end_turn(run)
        self.assertEqual(player.actions, 1)
        self.assertEqual(player.bonus_actions, 0)
        self.assertFalse(any(b.id == "drain_a" for b in player.buffs))
        self.assertFalse(any(b.id == "drain_ba" for b in player.buffs))
        self.assertEqual(len(player.hand), 4)
        self.assertFalse(any(b.id == "discard_next_turn" for b in player.buffs))

    def test_ready_pack_relic(self):
        class DummySaveManager:
            def save_save(self, user_id, run): pass
            def load_stats(self, user_id): return None
        engine = BattleEngine(DummySaveManager())
        player = PlayerState(hp=80, max_hp=80, shield=10, gold=100, stage=1, relics=["ready_pack"])
        player.deck = ["strike", "strike", "strike", "strike", "strike", "strike", "strike", "strike"]
        run = GameRun(user_id="test_relic_pack", node_type="battle", player=player, enemies=[])
        engine._init_battle_node(run)
        self.assertEqual(len(player.hand), 7)
        self.assertEqual(player.bonus_actions, 2)

    def test_queue_rendering_flow(self):
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
        run = GameRun(user_id="test_render_q", node_type="battle", player=player, enemies=[enemy])
        dummy_save.save_save("test_render_q", run)
        from game.core.cli_router import CLIRouter
        router = CLIRouter(dummy_save, engine)
        res_list = list(router.handle_command("test_render_q", ["q", "[p 1, p 2]"]))
        res_combined = "\n".join(res_list)
        self.assertEqual(res_combined.count("⚔️ 【第 1 关"), 1)

    def test_yog_sothoth_phase_transitions(self):
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
                    yog_sothoth_challenge_count = 1
                return DummyStats()
        dummy_save = DummySaveManager()
        from game.core.battle_engine import BattleEngine
        engine = BattleEngine(dummy_save)
        from game.models.state import PlayerState, EnemyState, GameRun
        player = PlayerState(hp=100, max_hp=100, shield=0, gold=100, stage=32)
        enemy = EnemyState("虚空之门·尤格-索托斯", 200, 200, 0)
        run = GameRun(user_id="test_yog_trans", node_type="battle", player=player, enemies=[enemy])
        dummy_save.save_save("test_yog_trans", run)
        from game.models.events import EnemyBeforeDeathEvent
        from game.entities.enemies.boss import BossYogSothothTemplate
        template = BossYogSothothTemplate("虚空之门·尤格-索托斯")
        evt = EnemyBeforeDeathEvent(run, enemy)
        template.on_enemy_before_death(run, enemy, evt, engine)
        self.assertTrue(evt.cancelled)
        self.assertEqual(enemy.hp, 1)
        self.assertEqual(run.node_data["pending_transitions"][enemy.name], 2)
        logs = []
        template.apply_phase_transition(run, enemy, 2, engine, logs)
        self.assertEqual(enemy.name, "【觉醒】虚空之门·尤格-索托斯")
        self.assertEqual(enemy.hp, 260)
        enemy.name = "【觉醒】虚空之门·尤格-索托斯"
        evt2 = EnemyBeforeDeathEvent(run, enemy)
        template.on_enemy_before_death(run, enemy, evt2, engine)
        self.assertTrue(evt2.cancelled)
        self.assertEqual(enemy.hp, 1)
        self.assertEqual(run.node_data["pending_transitions"][enemy.name], 3)
        template.apply_phase_transition(run, enemy, 3, engine, logs)
        self.assertEqual(enemy.name, "【终焉】虚空之门·尤格-索托斯")
        self.assertEqual(enemy.hp, 300)
        enemy.name = "【终焉】虚空之门·尤格-索托斯"
        evt3 = EnemyBeforeDeathEvent(run, enemy)
        template.on_enemy_before_death(run, enemy, evt3, engine)
        self.assertTrue(evt3.cancelled)
        self.assertEqual(enemy.hp, 1)
        self.assertEqual(run.node_data["pending_transitions"][enemy.name], 4)
        template.apply_phase_transition(run, enemy, 4, engine, logs)
        self.assertEqual(enemy.name, "【万物归一】虚空之门·尤格-索托斯")
        self.assertEqual(enemy.hp, 2147483647)

    def test_test_dummy_creation_and_intents(self):
        from game.entities import get_enemy_template
        from game.data.enemy_data import ENEMY_CONFIG
        
        self.assertIn("测试训练假人", ENEMY_CONFIG)
        cfg = ENEMY_CONFIG["测试训练假人"]
        self.assertEqual(cfg["hp"], "999999")
        
        template = get_enemy_template("测试训练假人")
        self.assertIsNotNone(template)
        
        class DummySaveManager:
            def save_save(self, user_id, run):
                pass
            def delete_save(self, user_id):
                pass
        save_mgr = DummySaveManager()
        engine = BattleEngine(save_mgr)
        
        player = PlayerState(hp=100, max_hp=100, shield=0, gold=100, stage=1, deck=[], hand=[])
        test_dummy = EnemyState(name="测试训练假人", hp=999999, max_hp=999999, shield=0)
        run = GameRun(
            user_id="test_user",
            node_type="battle",
            player=player,
            enemies=[test_dummy]
        )
        
        self.assertEqual(test_dummy.hp, 999999)
        self.assertEqual(test_dummy.max_hp, 999999)
        
        intents_1 = template.roll_intents(run, engine, test_dummy)
        self.assertEqual(len(intents_1), 1)
        self.assertEqual(intents_1[0].type, "attack")
        self.assertEqual(intents_1[0].val, 10)
        
        intents_2 = template.roll_intents(run, engine, test_dummy)
        self.assertEqual(len(intents_2), 1)
        self.assertEqual(intents_2[0].type, "defend")
        self.assertEqual(intents_2[0].val, 10)
        
        run.player.hp = 100
        run.player.shield = 0
        logs = []
        template.execute_intent(run, engine, test_dummy, intents_1[0], logs)
        self.assertEqual(run.player.hp, 90)
        
        test_dummy.shield = 0
        logs = []
        template.execute_intent(run, engine, test_dummy, intents_2[0], logs)
        self.assertEqual(test_dummy.shield, 10)
