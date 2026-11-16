import asyncio
import os
import tempfile
import unittest

from game.core.battle.daily_blessing import _pick_random_card
from game.core.inventory.deck_service import DeckService
from game.test.core.base import CorePlugin, floor_of, require_run, run_command
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

    def test_yog_quest_starts_as_snowfield_grid_run(self):
        uid = "test_yog_quest_grid_user"
        self._cleanup(uid)
        try:
            self._run(".rogue 主城", uid)
            stats = self.sm.load_stats(uid)
            stats.yog_sothoth_kill_count = 1
            self.sm.save_stats(uid, stats)

            pre_quest = self._run(".rogue 任务", uid)
            self.assertIn("尤格索托斯死了吗？", pre_quest)
            self.assertIn("先与向导长老谈一谈", pre_quest)
            self.assertNotIn("死灵之书", pre_quest)
            self.assertNotIn("欧吕尔", pre_quest)

            talk_res = self._run(".rogue talk 向导长老", uid)
            self.assertIn("询问尤格索托斯的死讯", talk_res)
            report_num = None
            for line in talk_res.splitlines():
                if "询问尤格索托斯的死讯" in line and "." in line:
                    report_num = line.split(".", 1)[0].strip()
                    break
            self.assertIsNotNone(report_num)

            reply_res = self._run(f".rogue {report_num}", uid)
            self.assertIn("星形符印", reply_res)
            stats = self.sm.load_stats(uid)
            self.assertIn("star_sigil", stats.town_inventory)
            self._run(".rogue exit", uid)

            self._run(".rogue a", uid)
            self._run(".rogue a", uid)
            gate_talk = self._run(".rogue talk 西大门", uid)
            self.assertIn("出城前往雪原", gate_talk)
            enter_res = self._run(".rogue use 星辉符印", uid)
            self.assertIn("雾隐雪原", enter_res)
            self.assertIn("B11", enter_res)
            self.assertNotIn("尤格索托斯神殿", enter_res)
            run = require_run(self.sm.load_save(uid))
            self.assertEqual(run.node_type, "grid_map")
            self.assertEqual(floor_of(run).floor_index, 5)
            self.assertTrue(floor_of(run).floor_flags.get("yog_quest"))

            quest_res = self._run(".rogue 任务", uid)
            self.assertIn("穿过雾隐雪原，找到神殿大门", quest_res)
            move_res = self._run(".rogue d", uid)
            self.assertIn("C11", move_res)
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
            run = require_run(self.sm.load_save(uid))
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
