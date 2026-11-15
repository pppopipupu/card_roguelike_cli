import asyncio
import os
import tempfile
import unittest

from game.core.battle.daily_blessing import _pick_random_card
from game.core.inventory.deck_service import DeckService
from game.test.core.base import CorePlugin, run_command
from game.entities import ALL_CARDS
from game.models.state import CardState, EnemyState, GameRun, PlayerState, UserStats


class DummyContext:
    def __init__(self):
        self.data_dir = tempfile.mkdtemp()


class MyPlugin(CorePlugin):
    pass


class TestTempleAndTokens(unittest.TestCase):
    def setUp(self):
        self.plugin = MyPlugin(DummyContext())
        self.sm = self.plugin.save_manager

    def _cleanup(self, uid):
        self.sm.delete_save(uid)
        sp = self.sm.get_stats_path(uid)
        if os.path.exists(sp):
            os.remove(sp)

    def _run(self, cmd, uid):
        return asyncio.run(run_command(self.plugin, cmd, uid))

    def test_temple_quest_causality_and_no_early_spoilers(self):
        uid = "test_temple_causality_user"
        self._cleanup(uid)
        try:
            self._run(".rogue 主城", uid)
            stats = self.sm.load_stats(uid)
            stats.yog_sothoth_kill_count = 1
            self.sm.save_stats(uid, stats)

            pre_quest = self._run(".rogue 任务", uid)
            self.assertIn("前往中心广场，向向导长老报告你击败了尤格-索托斯", pre_quest)
            self.assertNotIn("西大门", pre_quest)
            self.assertNotIn("死灵之书", pre_quest)
            self.assertNotIn("欧吕尔", pre_quest)
            self.assertNotIn("\u0336", pre_quest)
            self.assertNotIn("✔", pre_quest)

            talk_res = self._run(".rogue talk 向导长老", uid)
            self.assertIn("告诉向导长老：我击败了尤格-索托斯", talk_res)
            self.assertNotIn("欧吕尔", talk_res)
            self.assertNotIn("冰封少女", talk_res)

            report_num = None
            for line in talk_res.splitlines():
                if "告诉向导长老：我击败了尤格-索托斯" in line:
                    report_num = line.split(".", 1)[0].strip()
                    break
            self.assertIsNotNone(report_num)

            reply_res = self._run(f".rogue {report_num}", uid)
            self.assertIn("西大门外一直藏着一座隐秘的尤格-索托斯神殿", reply_res)
            self.assertIn("符印", reply_res)
            self.assertNotIn("欧吕尔", reply_res)
            self.assertNotIn("冰封少女", reply_res)
            stats = self.sm.load_stats(uid)
            self.assertIn("star_sigil", stats.town_inventory)
            bag_res = self._run(".rogue bag t", uid)
            self.assertIn("星辉符印", bag_res)

            leave_num = None
            for line in reply_res.splitlines():
                if "离开" in line and "." in line:
                    leave_num = line.split(".", 1)[0].strip()
                    break
            self.assertIsNotNone(leave_num)
            self._run(f".rogue {leave_num}", uid)
            quest_res = self._run(".rogue 任务", uid)
            self.assertIn("尤格索托斯之死？", quest_res)
            self.assertIn("在西大门使用【星辉符印】出城，进入尤格索托斯神殿", quest_res)
            self.assertNotIn("前往中心广场，向向导长老报告", quest_res)
            self.assertNotIn("死灵之书", quest_res)
            self.assertNotIn("欧吕尔", quest_res)
            self.assertNotIn("冰封少女", quest_res)
            self.assertNotIn("\u0336", quest_res)
            self._run(".rogue a", uid)
            self._run(".rogue a", uid)
            gate_talk = self._run(".rogue talk 西大门", uid)
            self.assertIn("出示星辉符印", gate_talk)
            enter_res = self._run(".rogue use 星辉符印", uid)
            self.assertIn("尤格索托斯神殿", enter_res)
            self.assertNotIn("欧吕尔", enter_res)

            sigil_res = self._run(".rogue 1", uid)
            self.assertIn("长老派你来的", sigil_res)
            self.assertNotIn("欧吕尔", sigil_res)
            self.assertNotIn("姑娘", sigil_res)
            self.assertNotIn("『", sigil_res)

            steps = [
                ("2", "左侧回廊"),
                ("3", "地下墓道"),
                ("2", "镜廊"),
                ("2", "教徒营房"),
                ("2", "仪式厅"),
                ("2", "关押室"),
                ("1", "旧祭坛"),
                ("2", "下行石阶"),
                ("3", "星门礼拜堂"),
                ("1", "裂隙石桥"),
                ("1", "守卫厅"),
            ]
            for cmd, expected_room in steps:
                step_res = self._run(f".rogue {cmd}", uid)
                self.assertIn(expected_room, step_res)
                self.assertNotIn("欧吕尔", step_res)
                self.assertNotIn("『", step_res)
                self.assertNotIn("』", step_res)
                if expected_room == "镜廊":
                    mid_quest = self._run(".rogue 任务", uid)
                    self.assertIn("从左侧回廊潜入了神殿内部", mid_quest)
                    self.assertIn("带着骨钥匙穿过神殿内殿", mid_quest)
                    self.assertNotIn("欧吕尔", mid_quest)
                    self.assertNotIn("\u0336", mid_quest)

            throne_res = self._run(".rogue 2", uid)
            self.assertIn("主殿王座厅", throne_res)
            self.assertIn("冰封少女·欧吕尔的化身", throne_res)
            self.assertIn("这里不归星辉教团管了", throne_res)
            self.assertNotIn("『", throne_res)

            throne_quest = self._run(".rogue 任务", uid)
            self.assertIn("冰封少女·欧吕尔的化身强行闯进了这座神殿", throne_quest)
            self.assertIn("击退强行闯入王座厅的冰封少女·欧吕尔化身", throne_quest)
            self.assertNotIn("\u0336", throne_quest)

            leave_res = self._run(".rogue 撤离", uid)
            self.assertIn("先古主城", leave_res)
        finally:
            self._cleanup(uid)

    def test_legacy_temple_info_grants_sigil(self):
        uid = "test_legacy_temple_sigil_user"
        self._cleanup(uid)
        try:
            self._run(".rogue 主城", uid)
            stats = self.sm.load_stats(uid)
            stats.yog_sothoth_kill_count = 1
            stats.town_flags["temple_info_received"] = True
            stats.town_pos = "west_gate"
            stats.town_inventory = []
            self.sm.save_stats(uid, stats)
            res = self._run(".rogue use 星辉符印", uid)
            self.assertIn("尤格索托斯神殿", res)
            stats = self.sm.load_stats(uid)
            self.assertIn("star_sigil", stats.town_inventory)
        finally:
            self._cleanup(uid)

    def test_token_tagging_and_pool_isolation(self):
        uid = "test_token_isolation_user"
        self._cleanup(uid)
        try:
            q_crit = self._run(".rogue i 卓越暴击", uid)
            self.assertIn("衍生物/token", q_crit)
            q_spirit = self._run(".rogue i 安的巨大英灵", uid)
            self.assertIn("衍生物/token", q_spirit)
            q_soldier = self._run(".rogue i 步兵轻卒", uid)
            self.assertIn("衍生物/token", q_soldier)
            q_altar = self._run(".rogue i 苏醒的深渊祭坛", uid)
            self.assertIn("衍生物/token", q_altar)
            q_kw = self._run(".rogue i 衍生物", uid)
            self.assertIn("衍生物/token", q_kw)

            stats = UserStats()
            stats.unlocked_new_cards = ["manaeria_queen_anne", "holy_celestial_millika", "elf_archer_xiaomei"]
            stats.yog_sothoth_kill_count = 1
            tokens = {
                "excellent_crit",
                "abyss_altar_awaken",
                "abyss_altar_converge",
                "abyss_altar_burst",
                "abyss_altar_end",
                "special_rlyeh_astrolabe",
                "dream_shard",
            }
            for cls_name in ("法师", "战士"):
                p = PlayerState(hp=50, max_hp=50, shield=0, gold=0, stage=1, selected_class=cls_name)
                run = GameRun(user_id=uid, node_type="battle", player=p, enemies=[])
                all_pools = (
                    set(DeckService.eligible_card_ids(stats, allow_coop=True))
                    | set(DeckService.get_reward_card_pool(run, p, stats, include_coop=True))
                    | set(DeckService.get_shop_card_pool(run, p, stats, include_coop=True))
                    | set(DeckService.get_epic_card_pool(run, p, stats))
                    | set(DeckService.get_class_spell_pool(p, stats, include_coop=True))
                )
                self.assertTrue(tokens.isdisjoint(all_pools))

            for flt in ("rare_minion", "rare", "zero_cost"):
                for _ in range(40):
                    picked = _pick_random_card(flt, stats)
                    self.assertNotIn(picked, tokens)

            self._run(".rogue 主城", uid)
            stats = self.sm.load_stats(uid)
            stats.gp = 1000
            self.sm.save_stats(uid, stats)
            lock_crit = self._run(".rogue lock 卓越暴击", uid)
            self.assertIn("无法锁定衍生物或特殊限定卡牌", lock_crit)
            lock_dream = self._run(".rogue lock 碎梦者", uid)
            self.assertIn("无法锁定", lock_dream)
            self.assertNotIn("excellent_crit", self.sm.load_stats(uid).locked_cards)
            self.assertNotIn("dream_shard", self.sm.load_stats(uid).locked_cards)

            self._run(".rogue start confirm", uid)
            run = self.sm.load_save(uid)
            deck_ids = {c.id for c in run.player.deck}
            self.assertTrue(tokens.isdisjoint(deck_ids))

            p = PlayerState(
                hp=50,
                max_hp=50,
                shield=0,
                gold=0,
                stage=1,
                deck=[CardState(id="manaeria_queen_anne"), CardState(id="fire_bolt")],
                hand=[CardState(id="manaeria_queen_anne")],
                draw_pile=[CardState(id="fire_bolt")],
                discard_pile=[],
                actions=2,
                bonus_actions=1,
            )
            battle_run = GameRun(user_id=uid, node_type="battle", player=p, enemies=[EnemyState("木桩", 100, 100, 0)])
            self.sm.save_save(uid, battle_run)
            play_res = self._run(".rogue p 1", uid)
            self.assertIn("安的巨大英灵", play_res)
            self.assertIn("卓越暴击", play_res)
            self.assertIn("衍生物/token", play_res)
        finally:
            self._cleanup(uid)
    def test_crpg_quest_branch_progression(self):
        uid = "test_crpg_quest_branch_user"
        self._cleanup(uid)
        try:
            self._run(".rogue 主城", uid)
            self._run(".rogue d", uid)
            self._run(".rogue d", uid)
            self._run(".rogue w", uid)
            self._run(".rogue talk Bartender_Jack", uid)
            self._run(".rogue 3", uid)
            self._run(".rogue exit", uid)

            q1 = self._run(".rogue 任务", uid)
            self.assertIn("在主城内打听并设法获取虚空草药", q1)
            self.assertNotIn("许愿喷泉", q1)
            self.assertNotIn("\u0336", q1)

            self._run(".rogue s", uid)
            self._run(".rogue a", uid)
            self._run(".rogue a", uid)
            self._run(".rogue a", uid)
            from game.data.locale_data import get_locale_text
            stats = self.sm.load_stats(uid)
            guard_room = stats.town_flags.get("pos_Town_Guard", "square")
            guard_room_name = get_locale_text(f"rooms.{guard_room}.name")
            self._run(f".rogue tp {guard_room_name}", uid)
            self._run(".rogue talk 巡逻卫兵", uid)
            self._run(".rogue 2", uid)
            self._run(".rogue exit", uid)

            q2 = self._run(".rogue 任务", uid)
            self.assertIn("向卫兵举报了非法倒卖草药的推销员", q2)
            self.assertIn("前往许愿喷泉，用泉水清洗虚空草药", q2)
            self.assertNotIn("在主城内打听并设法获取虚空草药", q2)
            self.assertNotIn("\u0336", q2)

            self._run(".rogue tp 许愿喷泉", uid)
            self._run(".rogue talk Fountain", uid)
            self._run(".rogue 1", uid)
            self._run(".rogue exit", uid)

            q3 = self._run(".rogue 任务", uid)
            self.assertIn("天外甘露草正散发着微光", q3)
            self.assertIn("将天外甘露草带回酒馆交给酒保杰克", q3)
            self.assertNotIn("\u0336", q3)

            self._run(".rogue d", uid)
            self._run(".rogue talk 神秘店主", uid)
            self._run(".rogue 3", uid)
            self._run(".rogue exit", uid)

            q4 = self._run(".rogue 任务", uid)
            self.assertIn("已完成", q4)
            self.assertIn("高价卖给了主城商店的神秘店主", q4)
            self.assertNotIn("当前目标：", q4)
            self.assertNotIn("\u0336", q4)
            self.assertNotIn("✔", q4)
        finally:
            self._cleanup(uid)


if __name__ == "__main__":
    unittest.main()
