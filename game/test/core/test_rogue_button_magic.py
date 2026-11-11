import os
import unittest
import asyncio
import random
from game.test.core.base import *
from game.renderer.menu import get_rogue_card_library_items

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

