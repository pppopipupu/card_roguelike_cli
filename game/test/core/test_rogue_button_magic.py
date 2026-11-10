import os
import unittest
import asyncio
import random
from game.test.core.base import *
from game.models.state import GameRun, PlayerState, EnemyState, CardState
from game.entities.cards.neutral import NeutralButtonMagicCard
from game.renderer.menu import get_rogue_card_library_items
from game.entities.cards.base import ALL_CARDS

class TestRogueButtonMagic(unittest.TestCase):
    def test_unlocked_and_locked_query(self):
        plugin = MyPlugin(DummyContext())
        save_manager = SaveManager()
        save_manager.delete_save("test_user_magic")
        
        stats = save_manager.load_stats("test_user_magic")
        stats.yog_sothoth_kill_count = 0
        save_manager.save_stats("test_user_magic", stats)
        
        async def run_locked():
            res = await run_command(plugin, "query 按钮术", "test_user_magic")
            self.assertIn("此卡牌的细节将在以后揭晓...", res)
            
            items = get_rogue_card_library_items("test_user_magic")
            has_button_magic = any("按钮术" in x for x in items)
            self.assertFalse(has_button_magic)
            
        asyncio.run(run_locked())
        
        stats = save_manager.load_stats("test_user_magic")
        stats.yog_sothoth_kill_count = 1
        save_manager.save_stats("test_user_magic", stats)
        
        async def run_unlocked():
            res = await run_command(plugin, "query 按钮术", "test_user_magic")
            self.assertNotIn("此卡牌的细节将在以后揭晓...", res)
            self.assertIn("随机触发 X 个按钮效果", res)
            
            items = get_rogue_card_library_items("test_user_magic")
            has_button_magic = any("按钮术" in x for x in items)
            self.assertTrue(has_button_magic)
            
        asyncio.run(run_unlocked())
        save_manager.delete_save("test_user_magic")

    def test_button_magic_battle_execution(self):
        sm = SaveManager()
        engine = BattleEngine(save_manager=sm)
        
        p = PlayerState(hp=100, max_hp=100, shield=50, gold=100, stage=1, deck=[], hand=[], draw_pile=[], discard_pile=[], exhaust_pile=[], graveyard=[])
        p.actions = 3
        p.bonus_actions = 2
        
        card_state = CardState(id="neutral_button_magic", upgraded=False)
        p.deck = [card_state]
        p.hand = [card_state]
        
        run = GameRun(user_id="test_user_battle", node_type="battle", player=p)
        
        e1 = EnemyState("哥布林", 30, 30, 0)
        run.enemies = [e1]
        
        run.node_data["last_x_cost_a"] = p.actions
        run.node_data["last_x_cost_ba"] = 0
        
        card_obj = ALL_CARDS.get("neutral_button_magic")
        self.assertIsNotNone(card_obj)
        
        res = engine._execute_card_effect(run, card_obj)
        self.assertIn("按下了命运的按钮，触发了以下效果", res)

    def test_button_magic_upgrade_battle_execution(self):
        sm = SaveManager()
        engine = BattleEngine(save_manager=sm)
        
        p = PlayerState(hp=100, max_hp=100, shield=20, gold=100, stage=1, deck=[], hand=[], draw_pile=[], discard_pile=[], exhaust_pile=[], graveyard=[])
        p.actions = 2
        p.bonus_actions = 1
        
        card_state = CardState(id="neutral_button_magic", upgraded=True)
        p.deck = [card_state]
        p.hand = [card_state]
        
        run = GameRun(user_id="test_user_battle_upg", node_type="battle", player=p)
        
        e1 = EnemyState("哥布林", 30, 30, 0)
        run.enemies = [e1]
        
        run.node_data["last_x_cost_a"] = p.actions
        run.node_data["last_x_cost_ba"] = 0
        
        card_obj = ALL_CARDS.get("neutral_button_magic+")
        self.assertIsNotNone(card_obj)
        
        res = engine._execute_card_effect(run, card_obj)
        self.assertIn("按下了命运的按钮，触发了以下效果", res)
