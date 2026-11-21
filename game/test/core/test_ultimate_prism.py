import asyncio
import random
import tempfile
import unittest

from game.core.inventory.card_distribution import CardDistributor
from game.data.ultimate_prism_data import (
    CHIREIDEN_QUEST_COMPLETED_FLAG,
    GLASS_SHARD_ITEM_ID,
    ULTIMATE_PRISM_ACHIEVEMENT_ID,
    ULTIMATE_PRISM_CARD_ID,
    ULTIMATE_PRISM_CONFIG,
    ULTIMATE_PRISM_FLAG_DEPARTED,
    ULTIMATE_PRISM_FLAG_IDLE_BATTLES,
    ULTIMATE_PRISM_FLAG_UNLOCKED,
    ULTIMATE_PRISM_MERC_ID,
)
from game.entities import ALL_CARDS
from game.entities.cards.ninja_base import resolve_card_effective_cost_a
from game.models.state import BuffState, CardState, EnemyState, GameRun, PlayerState
from game.test.core.base import CorePlugin, load_run, run_command


class TestUltimatePrism(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.random_state = random.getstate()
        random.seed(7)
        self.plugin = CorePlugin(data_dir=self.tmp.name)

    def tearDown(self):
        random.setstate(self.random_state)
        self.tmp.cleanup()

    def run_cmd(self, command: str, uid: str) -> str:
        return asyncio.run(run_command(self.plugin, command, uid))

    def _build_battle(self, uid: str, hand, deck=None, enemies=None, actions=3, bonus_actions=3, buffs=None):
        p = PlayerState(
            hp=100,
            max_hp=100,
            shield=0,
            gold=200,
            stage=1,
            deck=list(deck) if deck is not None else list(hand),
            hand=list(hand),
            draw_pile=[CardState(id="shield")] * 5,
            discard_pile=[],
            exhaust_pile=[],
            graveyard=[],
            actions=actions,
            bonus_actions=bonus_actions,
            buffs=list(buffs or []),
        )
        en = list(enemies) if enemies is not None else [EnemyState("训练假人", 2000, 2000, 0)]
        run = GameRun(user_id=uid, node_type="battle", player=p, enemies=en, node_data={})
        self.plugin.save_manager.save_save(uid, run)
        return run

    def test_market_unlock_lock_and_not_in_normal_pool(self):
        uid = "prism_market_user"
        stats = self.plugin.save_manager.load_stats(uid)
        stats.gp = 10000
        self.plugin.save_manager.save_stats(uid, stats)

        deny_lock = self.run_cmd("lock 终极棱镜", uid)
        self.assertIn("7891", deny_lock)

        self.run_cmd("主城", uid)
        self.run_cmd("s", uid)
        before_dlg = self.run_cmd("talk 卡牌商人", uid)
        self.assertNotIn("7891", before_dlg)
        self.run_cmd("离开", uid)

        stats = self.plugin.save_manager.load_stats(uid)
        stats.town_flags[CHIREIDEN_QUEST_COMPLETED_FLAG] = True
        self.plugin.save_manager.save_stats(uid, stats)

        dlg = self.run_cmd("talk 卡牌商人", uid)
        self.assertIn("终极棱镜", dlg)
        self.assertIn("7891", dlg)
        buy_opt = ""
        for line in dlg.splitlines():
            if "终极棱镜" in line and "." in line:
                buy_opt = line.strip().split(".", 1)[0]
                break
        self.assertTrue(buy_opt.isdigit())
        buy_res = self.run_cmd(buy_opt, uid)
        self.assertIn("7891", buy_res)
        self.assertIn("终极棱镜", buy_res)

        after_stats = self.plugin.save_manager.load_stats(uid)
        from game.data.achievement_data import ACHIEVEMENTS_CONFIG
        bonus_gp = ACHIEVEMENTS_CONFIG["collection_complete"]["gp_reward"] if "collection_complete" in after_stats.unlocked_achievements else 0
        self.assertEqual(after_stats.gp, 10000 - 7891 + bonus_gp)
        self.assertTrue(after_stats.town_flags.get(ULTIMATE_PRISM_FLAG_UNLOCKED))
        self.assertIn(ULTIMATE_PRISM_CARD_ID, after_stats.locked_cards)

        self.run_cmd("离开", uid)
        self.run_cmd("退出", uid)
        self.run_cmd("start confirm", uid)
        run = load_run(self.plugin, uid)
        self.assertIn(ULTIMATE_PRISM_CARD_ID, [c.id for c in run.player.deck])

        for channel in ("battle_normal", "battle_elite", "shop", "treasure"):
            rolled = CardDistributor.roll(channel, run, run.player, after_stats, count=30)
            self.assertNotIn(ULTIMATE_PRISM_CARD_ID, rolled)

    def test_passive_refract_and_cost_reductions(self):
        uid = "prism_passive_user"
        prism_state = CardState(id=ULTIMATE_PRISM_CARD_ID)
        replay_card = CardState(id="fire_bolt", replay=1)
        hand = [
            CardState(id="fire_bolt"),
            prism_state,
            CardState(id="shield"),
            replay_card,
            CardState(id="magic_missile"),
        ]
        self._build_battle(
            uid,
            hand=hand,
            actions=5,
            bonus_actions=5,
            buffs=[BuffState("echo_form", "回响形态", 1, None, "")],
        )

        res1 = self.run_cmd("p 1 e1", uid)
        self.assertIn("终极棱镜", res1)
        self.assertIn("5 次", res1)
        after1 = load_run(self.plugin, uid)
        self.assertIn("shield", [c.id for c in after1.player.exhaust_pile])
        self.assertGreaterEqual(after1.player.shield, 25)
        prism_in_hand = next(c for c in after1.player.hand if c.id == ULTIMATE_PRISM_CARD_ID)
        prism_obj = ALL_CARDS[prism_in_hand]
        cost_after_first = resolve_card_effective_cost_a(prism_obj, prism_in_hand, after1.player)
        self.assertEqual(cost_after_first, 999 - 20 - 10)

        replay_idx = next(i for i, c in enumerate(after1.player.hand, 1) if c.id == "fire_bolt" and c.replay == 1)
        res2 = self.run_cmd(f"p {replay_idx} e1", uid)
        self.assertIn("重放", res2)
        after2 = load_run(self.plugin, uid)
        prism_in_hand2 = next(c for c in after2.player.hand if c.id == ULTIMATE_PRISM_CARD_ID)
        cost_after_second = resolve_card_effective_cost_a(ALL_CARDS[prism_in_hand2], prism_in_hand2, after2.player)
        self.assertEqual(cost_after_second, 999 - 20 - 10 - 15)

        uid_right = "prism_right_adj_user"
        self._build_battle(
            uid_right,
            hand=[CardState(id="shield"), CardState(id=ULTIMATE_PRISM_CARD_ID), CardState(id="fire_bolt")],
            actions=3,
            bonus_actions=3,
        )
        res_right = self.run_cmd("p 3 e1", uid_right)
        self.assertIn("5 次", res_right)
        after_right = load_run(self.plugin, uid_right)
        self.assertIn("shield", [c.id for c in after_right.player.exhaust_pile])
        self.assertGreaterEqual(after_right.player.shield, 25)

    def test_play_effect_stun_strip_damage_blind_yog_and_achievement(self):
        uid = "prism_play_user"
        prism_free = CardState(id=ULTIMATE_PRISM_CARD_ID, battle_cost_delta_a=-999)
        e1 = EnemyState("训练假人 A", 2000, 2000, 0)
        e1.buffs.append(BuffState("strength", "力量", 5, None, ""))
        e1.buffs.append(BuffState("weak", "虚弱", 1, None, ""))
        e2 = EnemyState("训练假人 B", 2000, 2000, 0)
        e2.buffs.append(BuffState("buffer", "缓冲", 2, None, ""))
        self._build_battle(
            uid,
            hand=[prism_free, CardState(id="fire_bolt"), CardState(id="magic_missile")],
            enemies=[e1, e2],
            actions=1,
            bonus_actions=1,
        )

        res = self.run_cmd("p 1", uid)
        self.assertIn("盲目", res)
        self.assertIn("万象折射的意志", res)
        after = load_run(self.plugin, uid)
        self.assertEqual(after.enemies[0].hp, 2000 - 666)
        self.assertEqual(after.enemies[1].hp, 2000 - 666)
        self.assertNotIn("strength", [b.id for b in after.enemies[0].buffs])
        self.assertIn("weak", [b.id for b in after.enemies[0].buffs])
        self.assertNotIn("buffer", [b.id for b in after.enemies[1].buffs])
        for en in after.enemies:
            stun_b = next((b for b in en.buffs if b.id == "stun"), None)
            assert stun_b is not None
            self.assertEqual(stun_b.stacks, 2)
        self.assertIn(ULTIMATE_PRISM_CARD_ID, [c.id for c in after.player.exhaust_pile])
        self.assertIn("blind", [b.id for b in after.player.buffs])

        blind_view = self.run_cmd("r", uid)
        self.assertNotIn("火焰弹", blind_view)
        self.assertNotIn("魔法飞弹", blind_view)

        self.run_cmd("e", uid)
        after_turn = load_run(self.plugin, uid)
        self.assertNotIn("blind", [b.id for b in after_turn.player.buffs])
        stats = self.plugin.save_manager.load_stats(uid)
        self.assertIn(ULTIMATE_PRISM_ACHIEVEMENT_ID, stats.unlocked_achievements)

        uid_yog = "prism_yog_user"
        yog_hp = 20000000000000000
        yog = EnemyState("虚空之门·尤格-索托斯", yog_hp, yog_hp, 0)
        self._build_battle(
            uid_yog,
            hand=[CardState(id=ULTIMATE_PRISM_CARD_ID, battle_cost_delta_a=-999)],
            enemies=[yog],
            actions=1,
            bonus_actions=0,
        )
        yog_res = self.run_cmd("p 1", uid_yog)
        self.assertIn("光耀裁决", yog_res)
        after_yog = load_run(self.plugin, uid_yog)
        self.assertEqual(after_yog.enemies[0].hp, yog_hp - ULTIMATE_PRISM_CONFIG["yog_radiant_damage"])

    def test_eternal_cannot_be_removed_in_shop_or_treasure(self):
        uid = "prism_eternal_user"
        p = PlayerState(
            hp=80,
            max_hp=80,
            shield=0,
            gold=500,
            stage=1,
            deck=[CardState(id=ULTIMATE_PRISM_CARD_ID), CardState(id="fire_bolt")],
        )
        shop_run = GameRun(
            user_id=uid,
            node_type="shop",
            player=p,
            enemies=[],
            node_data={
                "items": [{"type": "remove", "price": 75, "sold": False}],
                "pending_remove": True,
                "remove_source": "shop",
            },
        )
        self.plugin.save_manager.save_save(uid, shop_run)
        counts_sorted = sorted(
            {c: 1 for c in p.deck}.items(),
            key=lambda item: (item[0].id, 1 if item[0].upgraded else 0, tuple(item[0].gems or [])),
        )
        prism_idx = next(i for i, (st, _) in enumerate(counts_sorted, 1) if st.id == ULTIMATE_PRISM_CARD_ID)
        rem_res = self.run_cmd(str(prism_idx), uid)
        self.assertIn("永恒", rem_res)
        after = load_run(self.plugin, uid)
        self.assertIn(ULTIMATE_PRISM_CARD_ID, [c.id for c in after.player.deck])
        self.assertEqual(after.player.gold, 500)

    def test_lore_card_talk_and_mercenary_recruitment(self):
        uid = "prism_talk_user"
        query_res = self.run_cmd("i 终极棱镜", uid)
        self.assertIn("背景：", query_res)
        self.assertIn("自主晶体", query_res)

        no_resp = self.run_cmd("talk 火焰弹", uid)
        self.assertIn("没有任何反应", no_resp)

        self._build_battle(
            uid,
            hand=[CardState(id=ULTIMATE_PRISM_CARD_ID, battle_cost_delta_a=-999), CardState(id="fire_bolt")],
            enemies=[EnemyState("训练假人", 2000, 2000, 0)],
            actions=2,
            bonus_actions=1,
        )
        talk_before = self.run_cmd("talk 终极棱镜", uid)
        self.assertIn("卡牌低语", talk_before)
        self.assertNotIn("雇佣兵", talk_before)
        lore_reply = self.run_cmd("2", uid)
        self.assertIn("自主晶体", lore_reply)
        self.run_cmd("0", uid)

        self.run_cmd("p 1", uid)
        talk_after = self.run_cmd("talk 终极棱镜", uid)
        self.assertIn("雇佣兵", talk_after)
        recruit_res = self.run_cmd("3", uid)
        self.assertIn("雇佣兵", recruit_res)
        self.run_cmd("0", uid)

        run_after = load_run(self.plugin, uid)
        merc_players = [
            p for p in run_after.players.values()
            if getattr(p, "is_mercenary", False) and getattr(p, "mercenary_id", "") == ULTIMATE_PRISM_MERC_ID
        ]
        self.assertEqual(len(merc_players), 1)

        uid_town = "prism_talk_town"
        stats = self.plugin.save_manager.load_stats(uid_town)
        stats.achievement_stats["ultimate_prism_played"] = 1
        stats.unlocked_achievements.append(ULTIMATE_PRISM_ACHIEVEMENT_ID)
        stats.town_flags[ULTIMATE_PRISM_FLAG_UNLOCKED] = True
        self.plugin.save_manager.save_stats(uid_town, stats)
        self.run_cmd("主城", uid_town)
        self.run_cmd("talk 终极棱镜", uid_town)
        town_rec = self.run_cmd("3", uid_town)
        self.assertIn("雇佣兵", town_rec)
        self.run_cmd("0", uid_town)
        st_hired = self.plugin.save_manager.load_stats(uid_town)
        self.assertIn(ULTIMATE_PRISM_MERC_ID, st_hired.hired_mercenaries)

    def test_five_idle_battles_departure_glass_shard_and_666_relock(self):
        uid = "prism_depart_user"
        stats = self.plugin.save_manager.load_stats(uid)
        stats.gp = 1000
        stats.town_flags[CHIREIDEN_QUEST_COMPLETED_FLAG] = True
        stats.town_flags[ULTIMATE_PRISM_FLAG_UNLOCKED] = True
        stats.locked_cards = [ULTIMATE_PRISM_CARD_ID]
        self.plugin.save_manager.save_stats(uid, stats)

        for battle_num in range(1, 3):
            self._build_battle(
                uid,
                hand=[CardState(id="fire_bolt")],
                deck=[CardState(id=ULTIMATE_PRISM_CARD_ID), CardState(id="fire_bolt")],
                enemies=[EnemyState("软泥怪", 1, 1, 0)],
                actions=1,
                bonus_actions=1,
            )
            self.run_cmd("p 1 e1", uid)
        self.assertEqual(self.plugin.save_manager.load_stats(uid).town_flags.get(ULTIMATE_PRISM_FLAG_IDLE_BATTLES), 2)

        self._build_battle(
            uid,
            hand=[CardState(id="shield"), CardState(id=ULTIMATE_PRISM_CARD_ID), CardState(id="fire_bolt")],
            deck=[CardState(id=ULTIMATE_PRISM_CARD_ID), CardState(id="shield"), CardState(id="fire_bolt")],
            enemies=[EnemyState("软泥怪", 1, 1, 0)],
            actions=2,
            bonus_actions=2,
        )
        self.run_cmd("p 1", uid)
        self.assertEqual(self.plugin.save_manager.load_stats(uid).town_flags.get(ULTIMATE_PRISM_FLAG_IDLE_BATTLES), 0)

        for battle_num in range(1, 6):
            self._build_battle(
                uid,
                hand=[CardState(id="fire_bolt")],
                deck=[CardState(id=ULTIMATE_PRISM_CARD_ID), CardState(id="fire_bolt")],
                enemies=[EnemyState("软泥怪", 1, 1, 0)],
                actions=1,
                bonus_actions=1,
            )
            res = self.run_cmd("p 1 e1", uid)
            if battle_num < 5:
                st = self.plugin.save_manager.load_stats(uid)
                self.assertEqual(st.town_flags.get(ULTIMATE_PRISM_FLAG_IDLE_BATTLES), battle_num)
                self.assertFalse(st.town_flags.get(ULTIMATE_PRISM_FLAG_DEPARTED))
            else:
                self.assertIn("玻璃碎块", res)

        run_post = load_run(self.plugin, uid)
        self.assertNotIn(ULTIMATE_PRISM_CARD_ID, [c.id for c in run_post.player.deck])
        self.assertIn(GLASS_SHARD_ITEM_ID, run_post.player.bag_items)
        bag_view = self.run_cmd("bag", uid)
        self.assertIn("玻璃碎块", bag_view)

        st_departed = self.plugin.save_manager.load_stats(uid)
        self.assertTrue(st_departed.town_flags.get(ULTIMATE_PRISM_FLAG_DEPARTED))
        self.assertNotIn(ULTIMATE_PRISM_CARD_ID, st_departed.locked_cards)

        lock_blocked = self.run_cmd("lock 终极棱镜", uid)
        self.assertIn("666", lock_blocked)

        self.plugin.save_manager.delete_save(uid)
        self.run_cmd("主城", uid)
        self.run_cmd("s", uid)
        market_dlg = self.run_cmd("talk 卡牌商人", uid)
        self.assertIn("666", market_dlg)
        relock_opt = ""
        for line in market_dlg.splitlines():
            if "666" in line and "." in line:
                relock_opt = line.strip().split(".", 1)[0]
                break
        self.assertTrue(relock_opt.isdigit())
        relock_res = self.run_cmd(relock_opt, uid)
        self.assertIn("666", relock_res)
        st_relocked = self.plugin.save_manager.load_stats(uid)
        self.assertEqual(st_relocked.gp, 1000 - 666)
        self.assertFalse(st_relocked.town_flags.get(ULTIMATE_PRISM_FLAG_DEPARTED))
        self.assertIn(ULTIMATE_PRISM_CARD_ID, st_relocked.locked_cards)


if __name__ == "__main__":
    unittest.main()
