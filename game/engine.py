import random
from typing import Optional, List, Dict
from .models.state import GameRun, PlayerState, EnemyState, MinionState, AmuletState, Card
from .entities import ALL_CARDS
from .entities.cards.market import is_card_available, is_coop_only
from .models.manager import SaveManager
from .core.battle.engine import BattleEngine
from .core.world.map_engine import MapEngine
from .data.progression.starting_deck_config import CLASS_BASE_HP, CLASS_STARTING_CARDS, DEFAULT_BASE_HP, LOCK_SLOT_LIMIT, STARTING_ROLL_COUNTS

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
        if selected_class in ("战士", "蕾忍"):
            selected_subclass = ""
        base_hp = CLASS_BASE_HP.get(selected_class, DEFAULT_BASE_HP)
        hp = base_hp
        max_hp = base_hp
        hp_bonus = getattr(stats, "town_health_bonus", 0)
        hp += hp_bonus
        max_hp += hp_bonus
        from .core.inventory.deck_service import DeckService
        initial_deck = DeckService.assemble_starting_deck(
            stats,
            include_random_rolls=True,
            consume_pending=True,
        )
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
        if selected_class == "蕾忍" and "lotus_box" not in player.relics:
            from .core.inventory.relic_service import grant_relic
            grant_relic(player, "lotus_box")
        from .core.inventory.bag_service import carryin_from_stats
        carryin_from_stats(player, stats)
        self.save_manager.save_stats(user_id, stats)
        return player

    def start_party_game(self, member_ids: List[str], leader_id: Optional[str] = None, shared_save: bool = False) -> Optional[GameRun]:
        import uuid
        from .data.progression.balance_config import COOP_MAX_PLAYERS
        from .core.battle.daily_blessing import apply_pending_blessing
        from .core.party.mercenary import build_mercenary_player
        if not member_ids:
            return None
        if len(member_ids) > COOP_MAX_PLAYERS:
            raise ValueError(f"Coop party exceeds COOP_MAX_PLAYERS ({COOP_MAX_PLAYERS})")
        leader = leader_id or member_ids[0]
        coop_id = uuid.uuid4().hex[:8] if (shared_save or len(member_ids) > 1) else ""
        players = {uid: self._build_player_state(uid) for uid in member_ids}
        run = GameRun(
            user_id=leader,
            node_type="start",
            player=players[leader],
            enemies=[],
            node_data={},
            coop_id=coop_id,
            leader_id=leader,
            party_order=list(member_ids),
            players=players,
        )
        pending_mercs = []
        for uid in member_ids:
            run.player = players[uid]
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
        from .core.world.presence import sync_active
        for uid in run.human_uids():
            sync_active(uid, run=run)
        return run
    def start_new_game(self, user_id: str) -> Optional[GameRun]:
        stats = self.save_manager.load_stats(user_id)
        if getattr(stats, "active_coop_id", "") or getattr(stats, "active_lobby_id", ""):
            return None
        return self.start_party_game([user_id], user_id, shared_save=False)

    def build_player_state(self, user_id: str) -> PlayerState:
        return self._build_player_state(user_id)

    def start_quest_run(self, user_id: str) -> Optional[str]:
        from .core.world.yog_quest.service import start_quest_run
        return start_quest_run(self.save_manager, self, user_id)

    def start_tutorial_run(self, user_id: str, return_to_town: bool = False):
        from .core.world.tutorial import start_tutorial_run
        return start_tutorial_run(self.save_manager, self, user_id, return_to_town=return_to_town)

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

    def choose_option(self, run: GameRun, option_idx: int, target: Optional[str] = None) -> str | None:
        return self.map_engine.choose_option(run, option_idx, target)


    def remove_card_from_deck(self, run: GameRun, deck_idx: int) -> str:
        return self.map_engine.remove_card_from_deck(run, deck_idx)

    def _handle_battle_win(self, run: GameRun):
        self.battle_engine._handle_battle_win(run)

    def _discard_card(self, run: GameRun, cid: str) -> str:
        return self.battle_engine._discard_card(run, cid)


    def upgrade_card_in_deck(self, run: GameRun, deck_idx: int) -> str:
        return self.map_engine.upgrade_card_in_deck(run, deck_idx)

    def gem_insert_choose(self, run: GameRun, deck_idx: int) -> str:
        return self.map_engine.gem_insert_choose(run, deck_idx)

    def gem_insert_cancel(self, run: GameRun) -> str:
        return self.map_engine.gem_insert_cancel(run)

    def enchant_choose(self, run: GameRun, option_idx: int) -> str:
        return self.map_engine.enchant_choose(run, option_idx)

    def enchant_cancel(self, run: GameRun) -> str:
        return self.map_engine.enchant_cancel(run)

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
