import asyncio
import re
import tempfile
import unittest
from collections import Counter

from game.cards import ALL_CARDS
from game.test.core.base import CorePlugin, load_run, run_command


class PlayerTradeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.a = "trade_a"
        self.b = "trade_b"
        for uid, name in ((self.a, "Alice"), (self.b, "Bob")):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.player_name = name
            stats.player_handle = name
            stats.name_customized = True
            self.plugin.save_manager.save_stats(uid, stats)

    def tearDown(self):
        self.tmp.cleanup()

    def cmd(self, text: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, text, uid))

    def enter_town(self):
        self.cmd("主城", self.a)
        self.cmd("主城", self.b)

    def befriend(self):
        self.cmd("好友 add Bob", self.a)
        self.cmd("好友 accept Alice", self.b)

    def start_coop(self):
        self.enter_town()
        self.befriend()
        created = self.cmd("组队 创建", self.a)
        match = re.search(r"队伍 ([A-Z0-9]{6})", created)
        assert match is not None
        lobby_id = match.group(1)
        self.cmd("组队 邀请 Bob", self.a)
        self.cmd("组队 加入 " + lobby_id, self.b)
        self.cmd("组队 准备", self.b)
        self.cmd("team start", self.a)
        self.cmd("c 1", self.a)
        self.cmd("c 1", self.b)

    def card_name(self, uid: str, index: int = 0, exclude: set[str] | None = None) -> str:
        deck = load_run(self.plugin, uid).player.deck
        exclude = exclude or set()
        for offset in range(len(deck)):
            state = deck[(index + offset) % len(deck)]
            card = ALL_CARDS.get(state)
            assert card is not None
            if card.name not in exclude:
                return card.name
        self.fail("no distinct card name found")

    def deck_names(self, uid: str) -> list[str]:
        names = []
        for state in load_run(self.plugin, uid).player.deck:
            card = ALL_CARDS.get(state)
            assert card is not None
            names.append(card.name)
        return names

    def test_coop_gift_and_exchange_require_both_sides(self):
        self.start_coop()
        gift_card = self.card_name(self.a)
        before_a = len(self.deck_names(self.a))
        before_b = len(self.deck_names(self.b))

        gift = self.cmd(f"trade gift Bob card:{gift_card}", self.a)
        self.assertIn("赠送提议", gift)
        self.assertEqual(len(self.deck_names(self.a)), before_a)
        self.assertEqual(len(self.deck_names(self.b)), before_b)

        popup = self.cmd("r", self.b)
        self.assertIn("发来了交易提议", popup)
        accepted = self.cmd("1", self.b)
        self.assertIn("赠送", accepted)
        self.assertIn("你获得", accepted)
        self.assertEqual(len(self.deck_names(self.a)), before_a - 1)
        self.assertEqual(len(self.deck_names(self.b)), before_b + 1)
        self.assertIn(gift_card, self.deck_names(self.b))
        self.assertIn("没有待处理", self.cmd("trade list", self.a))

        give_name = self.card_name(self.a)
        want_name = self.card_name(self.b, index=-1, exclude={give_name})
        offer = self.cmd(f"trade offer Bob card:{give_name} for card:{want_name}", self.a)
        self.assertIn("交换提议", offer)
        self.assertIn(give_name, self.deck_names(self.a))
        self.assertIn(want_name, self.deck_names(self.b))

        declined = self.cmd("2", self.b)
        self.assertIn("拒绝", declined)
        self.assertIn(give_name, self.deck_names(self.a))
        self.assertIn(want_name, self.deck_names(self.b))

        before_offer_a = Counter(self.deck_names(self.a))
        before_offer_b = Counter(self.deck_names(self.b))
        self.cmd(f"trade offer Bob card:{give_name} for card:{want_name}", self.a)
        done = self.cmd("trade accept", self.b)
        self.assertIn("交易完成", done)
        after_offer_a = Counter(self.deck_names(self.a))
        after_offer_b = Counter(self.deck_names(self.b))
        self.assertEqual(after_offer_a[give_name], before_offer_a[give_name] - 1)
        self.assertEqual(after_offer_b[give_name], before_offer_b[give_name] + 1)
        self.assertEqual(after_offer_b[want_name], before_offer_b[want_name] - 1)
        self.assertEqual(after_offer_a[want_name], before_offer_a[want_name] + 1)

        status = self.cmd("touch Bob", self.a)
        self.assertIn("【Bob】的状态", status)
        self.assertIn("生命", status)
        self.assertIn("SP", status)
        self.assertIn("持久状态", status)

        view = self.cmd("trade view Bob", self.a)
        self.assertIn("的卡组", view)
        self.assertIn("的背包", view)
        self.assertIn("的遗物", view)
        relic_view = self.cmd("trade view Bob relic", self.a)
        self.assertIn("的遗物", relic_view)
        self.assertNotIn("的卡组", relic_view)

    def test_town_trade_relics_items_and_consent(self):
        stats_a = self.plugin.save_manager.load_stats(self.a)
        stats_a.open_world_relics = ["ancient_eye", "gold_compass"]
        stats_a.open_world_relic_counters = {"ancient_eye": 0, "gold_compass": 0}
        stats_a.open_world_bag = ["potion:healing_potion"]
        self.plugin.save_manager.save_stats(self.a, stats_a)
        stats_b = self.plugin.save_manager.load_stats(self.b)
        stats_b.open_world_relics = ["heavy_armor", "dragon_blood"]
        stats_b.open_world_relic_counters = {"heavy_armor": 0, "dragon_blood": 0}
        stats_b.open_world_bag = ["potion:shield_potion"]
        self.plugin.save_manager.save_stats(self.b, stats_b)
        self.enter_town()

        self.cmd("trade offer Bob relic:先古之眼 for relic:重装甲片", self.a)
        self.assertEqual(self.plugin.save_manager.load_stats(self.a).open_world_relics, ["ancient_eye", "gold_compass"])
        self.assertEqual(self.plugin.save_manager.load_stats(self.b).open_world_relics, ["heavy_armor", "dragon_blood"])
        self.assertIn("交易完成", self.cmd("trade accept", self.b))
        self.assertEqual(self.plugin.save_manager.load_stats(self.a).open_world_relics, ["gold_compass", "heavy_armor"])
        self.assertEqual(self.plugin.save_manager.load_stats(self.b).open_world_relics, ["dragon_blood", "ancient_eye"])

        self.cmd("trade offer Bob item:治疗药水 for item:护盾药水", self.a)
        self.cmd("trade accept", self.b)
        self.assertEqual(self.plugin.save_manager.load_stats(self.a).open_world_bag, ["potion:shield_potion"])
        self.assertEqual(self.plugin.save_manager.load_stats(self.b).open_world_bag, ["potion:healing_potion"])

        self.cmd("trade gift Bob relic:黄金罗盘", self.a)
        self.assertIn("gold_compass", self.plugin.save_manager.load_stats(self.a).open_world_relics)
        self.assertIn("拒绝", self.cmd("trade decline", self.b))
        self.assertIn("gold_compass", self.plugin.save_manager.load_stats(self.a).open_world_relics)
        self.assertNotIn("gold_compass", self.plugin.save_manager.load_stats(self.b).open_world_relics)

        self.cmd("trade gift Bob relic:黄金罗盘", self.a)
        self.assertIn("赠送", self.cmd("1", self.b))
        self.assertNotIn("gold_compass", self.plugin.save_manager.load_stats(self.a).open_world_relics)
        self.assertIn("gold_compass", self.plugin.save_manager.load_stats(self.b).open_world_relics)


if __name__ == "__main__":
    unittest.main()
