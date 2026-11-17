import asyncio
import random
import tempfile
import time
import unittest
from unittest.mock import patch

from game.data.pvp_config import PVP_TURN_TIMEOUT_SECONDS, PVP_WIN_GP_REWARD
from game.data.town_card_shop_data import TOWN_CARD_SHOP_CATALOG
from game.data.world_social_config import WORLD_TOWN
from game.models.state import CardState
from game.test.core.base import CorePlugin, require_run, run_command


class TestTownCardShopAndPvp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.random_state = random.getstate()
        random.seed(20261116)
        self.plugin = CorePlugin(data_dir=self.tmp.name)
        self.alice = "pvp_alice"
        self.bob = "pvp_bob"

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def cmd(self, text: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, text, uid))

    def im_cmd(self, text: str, uid: str) -> str | None:
        return asyncio.run(
            self.plugin.server.handle_rogue_message(
                uid,
                uid,
                text,
                shortcut_prefix=[".rogue"],
                enable_shortcut=True,
                force_execute=False,
            )
        )

    def _prepare_player(self, uid: str, name: str, *, gp: int = 500, bag=None, relics=None, deck=None):
        stats = self.plugin.save_manager.load_stats(uid)
        stats.player_name = name
        stats.player_handle = name
        stats.selected_class = "法师"
        stats.gp = gp
        if bag is not None:
            stats.open_world_bag = list(bag)
        if relics is not None:
            stats.open_world_relics = list(relics)
        if deck is not None:
            stats.open_world_deck = [CardState(c) if isinstance(c, str) else c for c in deck]
        self.plugin.save_manager.save_stats(uid, stats)
        self.cmd("主城", uid)

    def test_town_card_merchant_sells_restrained_cards_into_open_world_deck(self):
        self._prepare_player(self.alice, "Alice", gp=1000)
        catalog_ids = {entry["id"] for entry in TOWN_CARD_SHOP_CATALOG}
        for banned in ("time_stop", "meteor_swarm", "wizard_split_to_ten", "warrior_hematopoiesis", "archmage_wish"):
            self.assertNotIn(banned, catalog_ids)

        self.cmd("deck", self.alice)
        self.cmd("s", self.alice)
        shop_view = self.cmd("talk 主城牌商", self.alice)
        self.assertIn("主城牌商", shop_view)
        self.assertIn("匕首投掷", shop_view)

        before_stats = self.plugin.save_manager.load_stats(self.alice)
        before_count = len(before_stats.open_world_deck)
        buy_out = self.cmd("1", self.alice)
        self.assertIn("购买成功", buy_out)
        self.assertIn("匕首投掷", buy_out)

        after_stats = self.plugin.save_manager.load_stats(self.alice)
        self.assertEqual(after_stats.gp, 1000 - TOWN_CARD_SHOP_CATALOG[0]["price"])
        self.assertEqual(len(after_stats.open_world_deck), before_count + 1)
        self.assertEqual(after_stats.open_world_deck[-1].id, "dagger_throw")

        self.cmd("0", self.alice)
        deck_view = self.cmd("deck", self.alice)
        self.assertIn("匕首投掷", deck_view)

    def test_pvp_toggle_and_invite_popup_accept_decline_disable(self):
        self._prepare_player(self.alice, "Alice")
        self._prepare_player(self.bob, "Bob")

        sent = self.cmd("atk Bob", self.alice)
        self.assertIn("PVP 切磋请求", sent)

        bob_screen = self.cmd("r", self.bob)
        self.assertIn("PVP 切磋请求", bob_screen)
        self.assertNotIn("先古主城", bob_screen)
        self.assertIn("[1] 接受", bob_screen)
        self.assertIn("[2] 不接受", bob_screen)
        self.assertIn("[3] 关闭PVP", bob_screen)

        decline_res = self.cmd("2", self.bob)
        self.assertIn("拒绝了", decline_res)
        self.assertIsNone(self.plugin.save_manager.load_save(self.bob))

        self.cmd("atk Bob", self.alice)
        disable_res = self.cmd("3", self.bob)
        self.assertIn("关闭 PVP 开关", disable_res)
        self.assertFalse(self.plugin.save_manager.load_stats(self.bob).pvp_enabled)

        blocked = self.cmd("atk Bob", self.alice)
        self.assertIn("已关闭 PVP", blocked)

        toggle_on = self.cmd("pvp", self.bob)
        self.assertIn("已开启 PVP", toggle_on)
        self.assertTrue(self.plugin.save_manager.load_stats(self.bob).pvp_enabled)

        toggle_status = self.cmd("pvp status", self.bob)
        self.assertIn("已开启", toggle_status)

    def test_pvp_invite_reply_accepts_without_command_prefix(self):
        self._prepare_player(self.alice, "Alice", deck=["fire_bolt", "shield", "dagger_throw"] * 3)
        self._prepare_player(self.bob, "Bob", deck=["fire_bolt", "shield", "dagger_throw"] * 3)
        for uid in (self.alice, self.bob):
            stats = self.plugin.save_manager.load_stats(uid)
            stats.rogue_mode = True
            self.plugin.save_manager.save_stats(uid, stats)

        sent = self.im_cmd(".rogue atk Bob", self.alice) or ""
        self.assertIn("PVP 切磋请求", sent)

        status_view = self.im_cmd("status", self.bob) or ""
        self.assertIn("PVP 切磋请求", status_view)
        self.assertNotIn("先古主城", status_view)

        accepted = self.im_cmd("1", self.bob) or ""
        self.assertIn("战斗开始", accepted)
        self.assertIn("等待【Alice】行动", accepted)
        self.assertEqual(require_run(self.plugin.save_manager.load_save(self.bob)).node_type, "battle")
        self.assertEqual(require_run(self.plugin.save_manager.load_save(self.alice)).node_type, "battle")

    def test_pvp_battle_turn_wait_rope_and_death_reward_settlement(self):
        self._prepare_player(
            self.alice,
            "Alice",
            gp=100,
            deck=["fire_bolt", "magic_missile", "shield", "dagger_throw"] * 3,
        )
        self._prepare_player(
            self.bob,
            "Bob",
            gp=100,
            bag=["espresso_beans"],
            relics=["ancient_compass"],
            deck=["fire_bolt", "shield", "dagger_throw"] * 3,
        )

        self.cmd("atk Bob", self.alice)
        accept_out = self.cmd("1", self.bob)
        self.assertIn("战斗开始", accept_out)
        self.assertIn("等待【Alice】行动", accept_out)
        self.assertIn("对手回合时限", accept_out)

        bob_blocked = self.cmd("p 1 e1", self.bob)
        self.assertIn("现在是【Alice】的回合", bob_blocked)

        alice_view = self.cmd("r", self.alice)
        self.assertIn("你的回合", alice_view)
        self.assertIn("回合时限", alice_view)

        play_out = self.cmd("p 1 e1", self.alice)
        self.assertNotIn("❌", play_out)

        end_out = self.cmd("e", self.alice)
        self.assertIn("等待【Bob】行动", end_out)

        alice_blocked = self.cmd("e", self.alice)
        self.assertIn("现在是【Bob】的回合", alice_blocked)

        future = time.time() + PVP_TURN_TIMEOUT_SECONDS + 5
        with patch("game.core.battle.pvp_service.time.time", return_value=future):
            rope_out = self.cmd("r", self.alice)
        self.assertIn("烧绳超时", rope_out)
        self.assertIn("你的回合", rope_out)

        abandon_out = self.cmd("abandon confirm", self.bob)
        self.assertIn("PVP 切磋战败", abandon_out)
        self.assertIn("Bob的冤魂", abandon_out)

        alice_stats = self.plugin.save_manager.load_stats(self.alice)
        bob_stats = self.plugin.save_manager.load_stats(self.bob)
        self.assertEqual(alice_stats.gp, 100 + PVP_WIN_GP_REWARD)
        self.assertEqual(bob_stats.open_world_bag, [])
        self.assertEqual(bob_stats.open_world_relics, [])
        self.assertEqual(bob_stats.open_world_deck, [])
        self.assertIsNone(self.plugin.save_manager.load_save(self.alice))
        self.assertIsNone(self.plugin.save_manager.load_save(self.bob))
        ghosts = self.plugin.save_manager.open_world_ghosts.list_at(WORLD_TOWN, "square")
        self.assertEqual(len(ghosts), 1)
        self.assertEqual(ghosts[0]["owner_uid"], self.bob)

    def test_pvp_time_stop_grants_extra_turns_and_breaks_on_damage(self):
        self._prepare_player(self.alice, "Alice", deck=["time_stop"] + ["fire_bolt"] * 5)
        self._prepare_player(self.bob, "Bob", deck=["fire_bolt"] * 12)

        self.cmd("atk Bob", self.alice)
        self.cmd("1", self.bob)

        cast = self.cmd("p sjt", self.alice)
        self.assertIn("时间停止", cast)
        self.assertNotIn("❌", cast)

        first_extra = self.cmd("e", self.alice)
        self.assertIn("额外回合进行中（剩余 2 个额外回合）", first_extra)

        bob_blocked = self.cmd("e", self.bob)
        self.assertIn("现在是【Alice】的回合", bob_blocked)

        damaged = self.cmd("p 1 e1", self.alice)
        self.assertIn("当前额外回合提前结束", damaged)
        self.assertIn("额外回合进行中（剩余 1 个额外回合）", damaged)

        second_extra = self.cmd("e", self.alice)
        self.assertIn("额外回合进行中（剩余 0 个额外回合）", second_extra)

        pass_turn = self.cmd("e", self.alice)
        self.assertIn("等待【Bob】行动", pass_turn)

        bob_turn = self.cmd("e", self.bob)
        self.assertIn("等待【Alice】行动", bob_turn)

    def test_pvp_hourglass_relic_grants_battle_start_extra_turn(self):
        self._prepare_player(self.alice, "Alice", deck=["fire_bolt"] * 12, relics=["infinite_hourglass"])
        self._prepare_player(self.bob, "Bob", deck=["fire_bolt"] * 12)

        self.cmd("atk Bob", self.alice)
        self.cmd("1", self.bob)

        extra = self.cmd("e", self.alice)
        self.assertIn("额外回合进行中（剩余 0 个额外回合）", extra)

        bob_blocked = self.cmd("e", self.bob)
        self.assertIn("现在是【Alice】的回合", bob_blocked)

        pass_turn = self.cmd("e", self.alice)
        self.assertIn("等待【Bob】行动", pass_turn)

    def test_pvp_plane_shift_escapes_to_center_square(self):
        self._prepare_player(
            self.alice,
            "Alice",
            deck=["neutral_plane_shift"] + ["fire_bolt"] * 5,
            bag=["espresso_beans"],
            relics=["ancient_compass"],
        )
        self._prepare_player(self.bob, "Bob", deck=["fire_bolt"] * 6)

        self.cmd("atk Bob", self.alice)
        self.cmd("1", self.bob)

        escape_out = self.cmd("p yjcs", self.alice)
        self.assertIn("中心广场", escape_out)
        self.assertIn("视为战败", escape_out)
        self.assertNotIn("【敌方战场】", escape_out)
        self.assertNotIn("❌", escape_out)

        alice_stats = self.plugin.save_manager.load_stats(self.alice)
        self.assertTrue(alice_stats.in_town)
        self.assertEqual(alice_stats.town_pos, "square")
        self.assertEqual(alice_stats.open_world_bag, ["espresso_beans"])
        self.assertIn("ancient_compass", alice_stats.open_world_relics)
        self.assertNotIn("neutral_plane_shift", [card.id for card in alice_stats.open_world_deck])
        self.assertIsNone(self.plugin.save_manager.load_save(self.alice))
        self.assertEqual(self.plugin.save_manager.open_world_ghosts.list_at(WORLD_TOWN, "square"), [])

        bob_stats = self.plugin.save_manager.load_stats(self.bob)
        self.assertEqual(bob_stats.gp, 500 + PVP_WIN_GP_REWARD)
        self.assertIsNone(self.plugin.save_manager.load_save(self.bob))
        bob_view = self.cmd("r", self.bob)
        self.assertEqual(bob_view.count("赢得胜利"), 1)

    def test_pvp_rope_only_ends_turn_without_forfeit(self):
        self._prepare_player(self.alice, "Alice", deck=["fire_bolt"] * 6, gp=500)
        self._prepare_player(self.bob, "Bob", deck=["fire_bolt"] * 6, gp=500)

        self.cmd("atk Bob", self.alice)
        self.cmd("1", self.bob)
        self.cmd("e", self.alice)

        first_future = time.time() + PVP_TURN_TIMEOUT_SECONDS + 5
        with patch("game.core.battle.pvp_service.time.time", return_value=first_future):
            first_rope = self.cmd("r", self.alice)
        self.assertIn("烧绳超时", first_rope)
        self.assertNotIn("判为战败", first_rope)

        second_future = first_future + PVP_TURN_TIMEOUT_SECONDS + 5
        with patch("game.core.battle.pvp_service.time.time", return_value=second_future):
            second_rope = self.cmd("r", self.bob)
        self.assertIn("烧绳超时", second_rope)
        self.assertNotIn("判为战败", second_rope)

        self.assertIsNotNone(self.plugin.save_manager.pvp.find_match_for_user(self.alice))
        self.assertIsNotNone(self.plugin.save_manager.pvp.find_match_for_user(self.bob))
        self.assertEqual(self.plugin.save_manager.load_stats(self.alice).gp, 500)
        self.assertEqual(self.plugin.save_manager.load_stats(self.bob).gp, 500)
        self.assertEqual(self.plugin.save_manager.open_world_ghosts.list_at(WORLD_TOWN, "square"), [])

    def test_pvp_victory_message_is_not_duplicated(self):
        self._prepare_player(self.alice, "Alice", deck=["neutral_astral_strike"] * 5)
        self._prepare_player(self.bob, "Bob", deck=["fire_bolt"] * 6, gp=500)

        self.cmd("atk Bob", self.alice)
        self.cmd("1", self.bob)

        self.cmd("p 1 e1", self.alice)
        win_out = self.cmd("p 1 e1", self.alice)
        self.assertEqual(win_out.count("PVP 切磋胜利"), 1)
        self.assertIsNone(self.plugin.save_manager.load_save(self.alice))
        self.assertEqual(self.plugin.save_manager.load_stats(self.alice).gp, 500 + PVP_WIN_GP_REWARD)
