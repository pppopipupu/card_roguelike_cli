import random
from typing import Optional, List, Dict
from .models.state import GameRun, PlayerState, EnemyState, MinionState, AmuletState, Card
from .entities import ALL_CARDS
from .entities.cards.market import is_card_available, is_coop_only
from .models.manager import SaveManager
from .core.battle.engine import BattleEngine
from .core.world.map_engine import MapEngine
from .data.starting_deck_config import CLASS_STARTING_CARDS, LOCK_SLOT_LIMIT, STARTING_ROLL_COUNTS

class GameEngine:
    def __init__(self, save_manager: SaveManager):
        self.save_manager = save_manager
        self.battle_engine = BattleEngine(save_manager)
        self.map_engine = MapEngine(save_manager, self.battle_engine)
        self.battle_engine.game_engine = self
        self.map_engine.game_engine = self
        self.battle_engine.map_engine = self.map_engine
        from .core.battle.potion_resolver import PotionResolver
        self.potion_resolver = PotionResolver(self)

    def _build_player_state(self, user_id: str) -> PlayerState:
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
        from .core.inventory.deck_service import DeckService
        commons = [cid for cid in DeckService.eligible_card_ids(stats, colors=allowed_colors, rarities=("common",)) if cid != "time_stop"]
        rares = [cid for cid in DeckService.eligible_card_ids(stats, colors=allowed_colors, rarities=("rare",)) if cid != "time_stop"]
        epics = [cid for cid in DeckService.eligible_card_ids(stats, colors=allowed_colors, rarities=("epic",)) if cid != "time_stop"]
        locked_cards = list(getattr(stats, "locked_cards", []) or [])[:LOCK_SLOT_LIMIT]
        g_card = getattr(stats, "guaranteed_card", None)
        if g_card:
            if g_card not in locked_cards:
                locked_cards.append(g_card)
            stats.guaranteed_card = None
        p_pool = getattr(stats, "purchased_pool", [])
        if p_pool:
            locked_cards.extend(p_pool)
            stats.purchased_pool = []
        stats.locked_cards = locked_cards[:LOCK_SLOT_LIMIT]
        target_counts = dict(STARTING_ROLL_COUNTS)
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
        initial_deck = list(CLASS_STARTING_CARDS.get(selected_class, CLASS_STARTING_CARDS["法师"])) + list(locked_cards)
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
        from .core.inventory.bag_service import carryin_from_stats
        carryin_from_stats(player, stats)
        self.save_manager.save_stats(user_id, stats)
        return player

    def start_party_game(self, member_ids: List[str], leader_id: Optional[str] = None, shared_save: bool = False) -> Optional[GameRun]:
        import uuid
        from .data.balance_config import COOP_MAX_PLAYERS
        from .core.battle.daily_blessing import apply_pending_blessing
        from .core.party.mercenary import build_mercenary_player
        if not member_ids:
            return None
        if len(member_ids) > COOP_MAX_PLAYERS:
            raise ValueError(f"Coop party exceeds COOP_MAX_PLAYERS ({COOP_MAX_PLAYERS})")
        leader = leader_id or member_ids[0]
        coop_id = uuid.uuid4().hex[:8] if (shared_save or len(member_ids) > 1) else ""
        run = GameRun(
            user_id=leader,
            node_type="start",
            player=None,
            enemies=[],
            node_data={},
            coop_id=coop_id,
            leader_id=leader,
            party_order=list(member_ids),
            players={},
        )
        pending_mercs = []
        for uid in member_ids:
            player = self._build_player_state(uid)
            run.players[uid] = player
            run.player = player
            run.user_id = uid
            stats = self.save_manager.load_stats(uid)
            if coop_id:
                stats.active_coop_id = coop_id
                stats.active_lobby_id = ""
            apply_pending_blessing(run, stats)
            hired = list(getattr(stats, "hired_mercenaries", []) or [])
            if hired:
                for merc_id in hired:
                    pending_mercs.append((uid, merc_id))
                stats.hired_mercenaries = []
            self.save_manager.save_stats(uid, stats)
        for owner_uid, merc_id in pending_mercs:
            if len(run.party_order) >= COOP_MAX_PLAYERS:
                break
            merc_uid = f"merc:{merc_id}:{owner_uid}"
            suffix = 1
            while merc_uid in run.players:
                suffix += 1
                merc_uid = f"merc:{merc_id}:{owner_uid}:{suffix}"
            run.party_order.append(merc_uid)
            run.players[merc_uid] = build_mercenary_player(merc_id, owner_uid)
        run.player = run.players[leader]
        run.user_id = leader
        self.map_engine.init_new_run_map(run)
        self.save_manager.save_save(leader, run)
        return run
    def start_new_game(self, user_id: str) -> GameRun:
        stats = self.save_manager.load_stats(user_id)
        if getattr(stats, "active_coop_id", "") or getattr(stats, "active_lobby_id", ""):
            return None
        return self.start_party_game([user_id], user_id, shared_save=False)

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

    def choose_option(self, run: GameRun, option_idx: int, target: Optional[str] = None) -> str:
        return self.map_engine.choose_option(run, option_idx, target)


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
        from .core.world.grid_map_generator import generate_floor_map
        from .core.party.session import SessionContextScoper
        floor_idx = 1
        if target_stage >= 32:
            floor_idx = 4
        elif target_stage >= 27:
            floor_idx = 3
        elif target_stage >= 13:
            floor_idx = 2
        run.floor_map = generate_floor_map(run, floor_idx, save_manager=self.save_manager)
        SessionContextScoper.ensure_full_party_order(run)
        for uid in run.all_human_uids():
            pl = run.players.get(uid)
            if pl is not None:
                pl.stage = target_stage
        run.node_type = "grid_map"
        run.enemies.clear()
        run.node_data = {}
        self.save_manager.save_save(run.user_id, run)
        return f"成功跳转到第 {target_stage} 层（大层 {floor_idx}）。"
