import random
from typing import Optional, List, Dict
from .models.state import GameRun, PlayerState, EnemyState, MinionState, AmuletState, Card
from .entities import ALL_CARDS
from .entities.cards.market import is_card_available
from .models.manager import SaveManager
from .core.battle_engine import BattleEngine
from .core.map_engine import MapEngine

class GameEngine:
    def __init__(self, save_manager: SaveManager):
        self.save_manager = save_manager
        self.battle_engine = BattleEngine(save_manager)
        self.map_engine = MapEngine(save_manager, self.battle_engine)
        self.battle_engine.map_engine = self.map_engine
        from .core.battle.potion_resolver import PotionResolver
        self.potion_resolver = PotionResolver(self)

    def start_new_game(self, user_id: str) -> GameRun:
        stats = self.save_manager.load_stats(user_id)
        stats.town_flags.pop("market_shelf", None)
        selected_class = getattr(stats, "selected_class", "法师")
        selected_subclass = getattr(stats, "selected_subclass", "")
        if selected_class == "战士":
            selected_subclass = ""
            allowed_colors = ("warrior", "neutral")
            hp = 80
            max_hp = 80
        else:
            allowed_colors = ("wizard", "neutral")
            hp = 45
            max_hp = 45
        hp_bonus = getattr(stats, "town_health_bonus", 0)
        hp += hp_bonus
        max_hp += hp_bonus
        commons = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "common" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and is_card_available(cid, stats)]
        rares = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "rare" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and is_card_available(cid, stats)]
        epics = [cid for cid, c in ALL_CARDS.items() if getattr(c, "rarity", "common") == "epic" and getattr(c, "color", "") in allowed_colors and not cid.startswith("curse_") and not cid.startswith("duel_") and cid != "time_stop" and is_card_available(cid, stats)]
        locked_cards = list(getattr(stats, "locked_cards", []) or [])
        g_card = getattr(stats, "guaranteed_card", None)
        if g_card:
            if g_card not in locked_cards:
                locked_cards.append(g_card)
            stats.guaranteed_card = None
        p_pool = getattr(stats, "purchased_pool", [])
        if p_pool:
            locked_cards.extend(p_pool)
            stats.purchased_pool = []
        stats.locked_cards = locked_cards
        target_counts = {"common": 5, "rare": 2, "epic": 1}
        for cid in locked_cards:
            c_obj = ALL_CARDS.get(cid)
            r = getattr(c_obj, "rarity", "common") if c_obj else "common"
            if r not in target_counts:
                r = "common"
            if target_counts[r] > 0:
                target_counts[r] -= 1
            else:
                if target_counts["common"] > 0:
                    target_counts["common"] -= 1
                elif target_counts["rare"] > 0:
                    target_counts["rare"] -= 1
                elif target_counts["epic"] > 0:
                    target_counts["epic"] -= 1
        initial_deck = list(locked_cards)
        for _ in range(target_counts["common"]):
            initial_deck.append(random.choice(commons))
        for _ in range(target_counts["rare"]):
            initial_deck.append(random.choice(rares))
        for _ in range(target_counts["epic"]):
            initial_deck.append(random.choice(epics))
        if selected_class == "法师" and selected_subclass == "时序法师":
            initial_deck.append("time_stop")
        player = PlayerState(
            hp=hp,
            max_hp=max_hp,
            shield=0,
            gold=20,
            stage=0,
            name=getattr(stats, "player_name", "玩家"),
            deck=initial_deck,
            draw_pile=[],
            discard_pile=[],
            hand=[],
            actions=1,
            bonus_actions=1,
            minions={},
            amulets={},
            abilities=[],
            subclass=selected_subclass,
            selected_class=selected_class
        )
        run = GameRun(
            user_id=user_id,
            node_type="start",
            player=player,
            enemies=[],
            node_data={}
        )
        from .core.daily_blessing import apply_pending_blessing
        apply_pending_blessing(run, stats)
        self.save_manager.save_stats(user_id, stats)
        self.enter_next_stage(run)
        self.save_manager.save_save(user_id, run)
        return run

    def enter_next_stage(self, run: GameRun):
        self.map_engine.enter_next_stage(run)

    def is_battle_won(self, run: GameRun) -> bool:
        return self.battle_engine.is_battle_won(run)

    def play_card(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        return self.battle_engine.play_card(run, hand_idx, target)

    def play_special_action(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        return self.battle_engine.play_special_action(run, hand_idx, target)

    def minion_attack(self, run: GameRun, my_grid: str, opp_grid: Optional[str] = None) -> str:
        return self.battle_engine.minion_attack(run, my_grid, opp_grid)

    def minion_skill(self, run: GameRun, my_grid: str, skill_idx: int = 1, target: Optional[str] = None) -> str:
        return self.battle_engine.minion_skill(run, my_grid, skill_idx, target)

    def end_turn(self, run: GameRun) -> str:
        return self.battle_engine.end_turn(run)

    def choose_option(self, run: GameRun, option_idx: int) -> str:
        return self.map_engine.choose_option(run, option_idx)

    def choose_map_node(self, run: GameRun, option_idx: int) -> str:
        return self.map_engine.choose_map_node(run, option_idx)

    def remove_card_from_deck(self, run: GameRun, deck_idx: int) -> str:
        return self.map_engine.remove_card_from_deck(run, deck_idx)

    def _handle_battle_win(self, run: GameRun):
        self.battle_engine._handle_battle_win(run)

    def _discard_card(self, run: GameRun, cid: str) -> str:
        return self.battle_engine._discard_card(run, cid)

    def execute_emperor_eye_resolve(self, run: GameRun, keep_idx: int, upgraded: bool) -> str:
        return self.battle_engine.execute_emperor_eye_resolve(run, keep_idx, upgraded)

    def upgrade_card_in_deck(self, run: GameRun, deck_idx: int) -> str:
        return self.map_engine.upgrade_card_in_deck(run, deck_idx)

    def gem_insert_choose(self, run: GameRun, deck_idx: int) -> str:
        return self.map_engine.gem_insert_choose(run, deck_idx)

    def gem_insert_cancel(self, run: GameRun) -> str:
        return self.map_engine.gem_insert_cancel(run)

    def jump_to_stage(self, run: GameRun, target_stage: int) -> str:
        p = run.player
        p.stage = target_stage - 1
        if 2 <= target_stage <= 10:
            self.map_engine._generate_map_network(run, 2, 10)
            run.map_data["current_node_id"] = None
        elif 12 <= target_stage <= 19:
            self.map_engine._generate_map_network(run, 12, 20)
            run.map_data["current_node_id"] = None
        elif 21 <= target_stage <= 24:
            self.map_engine._generate_map_network(run, 21, 25)
            run.map_data["current_node_id"] = None
        self.map_engine.enter_next_stage(run)
        self.save_manager.save_save(run.user_id, run)
        return f"成功跳转到第 {target_stage} 层。"
