import random
import re
from typing import Optional
from ...models.state import GameRun, PlayerState, EnemyState, Card, UserStats
from ...models.events import DamageCalculateEvent
from ...data.world.map_config import MapConfig
from ...data.enemies.enemy_data import ENEMY_CONFIG
from ...data.enemies.enemy_data_normal import ENEMY_ENCOUNTER_CONFIG
from ...data.enemies.enemy_data_boss import BOSS_POOLS
from ...data.entities.corpse_config import CorpseConfig
from ...data.text.locale_data import get_locale_text
from .base import BaseBattleEngine
from .battle_setup import BattleSetupMixin
from .combat_resolver import CombatResolver
from .card_player import CardPlayer
from .enemy_controller import EnemyTurnController
from .handlers import register_default_battle_handlers
from .instant_summon import InstantSummonHandler
from .exhaustion_observer import ExhaustionObserver
from .daily_blessing import DailyBlessingHandler
from .anna_handler import AnnaCardHandler
from .millika_handler import MillikaCardHandler
from .ultimate_prism_handler import UltimatePrismHandler
from ..inventory.deck_service import DeckService
from ...models.stats_tracker import StatsTracker
from ..text.events import RenderedText, TextDocument, TextNode, coerce_text_node, locale_text
from ..text.pipeline import render_text_node


class BattleEngine(BattleSetupMixin):
    def __init__(self, save_manager):
        super().__init__(save_manager)
        self.current_run = None
        self.combat_resolver = CombatResolver(self)
        self.card_player = CardPlayer(self)
        self.enemy_controller = EnemyTurnController(self)
        self.handlers = register_default_battle_handlers(self.event_bus, self, self.save_manager)
        self.relic_handler = self.handlers["relic"]
        self.buff_handler = self.handlers["buff"]
        self.amulet_handler = self.handlers["amulet"]
        self.rally_handler = self.handlers["rally"]
        self.minion_handler = self.handlers["minion"]
        self.enemy_handler = self.handlers["enemy"]
        self.card_handler = self.handlers["card"]
        self.stat_tracking_handler = self.handlers["stat_tracking"]
        self.instant_summon_handler = InstantSummonHandler(self.event_bus, self)
        self.daily_blessing_handler = DailyBlessingHandler(self.event_bus, self)
        from ..party.mercenary import MercenaryVoiceHandler
        self.mercenary_voice_handler = MercenaryVoiceHandler(self.event_bus, self)
        self.exhaustion_observer = ExhaustionObserver(self.event_bus, self)
        self.anna_handler = AnnaCardHandler(self.event_bus, self)
        self.millika_handler = MillikaCardHandler(self.event_bus, self)
        self.ultimate_prism_handler = UltimatePrismHandler(self.event_bus, self)

    def _effective_log_uid(self, run: GameRun) -> str:
        effective_uid = run.user_id
        if run.player is not None and getattr(run.player, "is_mercenary", False):
            effective_uid = getattr(run.player, "mercenary_owner", "") or effective_uid
        return effective_uid

    def _log_event(self, run: Optional[GameRun], msg: str | TextNode):
        if run is None:
            return
        owner_uid = self._effective_log_uid(run)
        logs = run.node_data.setdefault("battle_logs", [])
        owners = run.node_data.get("battle_log_owners")
        if not isinstance(owners, list):
            owners = []
            run.node_data["battle_log_owners"] = owners
        if len(owners) < len(logs):
            owners.extend([owner_uid] * (len(logs) - len(owners)))
        elif len(owners) > len(logs):
            del owners[len(logs):]
        owners.append(owner_uid)
        logs.append(msg)

    def _consume_pending_stats_logs(self, uid: str) -> TextDocument:
        if not uid or self.save_manager is None:
            return []
        stats = self.save_manager.load_stats(uid)
        pending = stats.pending_logs
        if not pending:
            return []
        nodes: TextDocument = [RenderedText(text=str(item)) for item in pending if str(item or "").strip()]
        stats.pending_logs = []
        self.save_manager.save_stats(uid, stats)
        return nodes

    def _take_battle_logs(self, run: GameRun, effective_uid: Optional[str] = None) -> TextDocument:
        target_uid = effective_uid or self._effective_log_uid(run)
        logs = run.node_data.pop("battle_logs", [])
        owners = run.node_data.pop("battle_log_owners", [])
        own_logs: TextDocument = []
        remaining = []
        remaining_owners = []
        for index, msg in enumerate(logs):
            owner = owners[index] if index < len(owners) else target_uid
            if owner == target_uid:
                node = coerce_text_node(msg)
                if isinstance(node, str):
                    own_logs.append(RenderedText(text=node))
                elif isinstance(node, TextNode):
                    own_logs.append(node)
            else:
                remaining.append(msg)
                remaining_owners.append(owner)
        if remaining:
            run.node_data["battle_logs"] = remaining
            run.node_data["battle_log_owners"] = remaining_owners
        own_logs.extend(self._consume_pending_stats_logs(target_uid))
        return own_logs

    def _append_logs_to_res(self, run: GameRun, res: str) -> str:
        effective_uid = self._effective_log_uid(run)
        nodes = self._take_battle_logs(run, effective_uid)
        if nodes:
            log_text = "\n".join(text for text in (render_text_node(node) for node in nodes) if text)
            if log_text:
                res = res.rstrip() + "\n" + log_text
        self.save_manager.save_save(effective_uid, run)
        return res
    def is_battle_won(self, run: GameRun) -> bool:
        if run.node_type != "battle":
            return False
        if not run.enemies:
            return True
        if all(e.hp <= 0 for e in run.enemies):
            return True
        alive_enemies = [e for e in run.enemies if e.hp > 0]
        if all(e.is_summon for e in alive_enemies):
            return True
        return False

    def _get_first_alive_enemy(self, run: GameRun) -> str:
        return self.combat_resolver.get_first_alive_enemy(run)

    def _get_target_name(self, run: GameRun, target: Optional[str]) -> str:
        return self.combat_resolver.get_target_name(run, target)

    def _damage_target(self, run: GameRun, target: str, dmg: int, source: str = "effect", damage_type: str = "effect", card: Optional[Card] = None, damage_ready: bool = False, is_attack: bool = False):
        self.combat_resolver.damage_target(run, target, dmg, source, damage_type, card, damage_ready, is_attack)

    def _heal_target(self, run: GameRun, target: str, heal: int):
        self.combat_resolver.heal_target(run, target, heal)

    def _summon_minion(self, run: GameRun, minion_id: str, name: str, hp: int, atk: int, ba: int) -> Optional[str]:
        return self.combat_resolver.summon_minion(run, minion_id, name, hp, atk, ba)

    def _gain_shield(self, run: GameRun, target: str, amount: int):
        self.combat_resolver.gain_shield(run, target, amount)

    def _sync_enemy_intents(self, enemy: EnemyState):
        self.enemy_controller.sync_enemy_intents(enemy)

    def _add_buff_to(self, entity, buff_id: str, buff_name: str, desc: str, count: int = 1, count2: Optional[int] = None):
        self.combat_resolver.add_buff_to(entity, buff_id, buff_name, desc, count, count2, run=self.current_run)

    def _get_free_grid(self, p: PlayerState) -> Optional[str]:
        return self.combat_resolver.get_free_grid(p)

    def _register_card_played(self, run: GameRun) -> int:
        key = run.turn_key("cards_played_this_turn")
        count = run.node_data.get(key, 0) + 1
        run.node_data[key] = count
        from ...models.events import CardPlayedCountEvent
        self.event_bus.dispatch(CardPlayedCountEvent(run, count))
        return count

    def _draw_cards(self, p: PlayerState, count: int, run: Optional[GameRun] = None, ignore_focus: bool = False, is_turn_start: bool = False):
        self.card_player.draw_cards(p, count, run, ignore_focus, is_turn_start)

    def play_card(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        self.current_run = run
        return self.card_player.play_card(run, hand_idx, target)

    def play_special_action(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        self.current_run = run
        return self.card_player.play_special_action(run, hand_idx, target)

    def minion_attack(self, run: GameRun, my_grid: str, opp_grid: Optional[str] = None) -> str:
        self.current_run = run
        return self.card_player.minion_attack(run, my_grid, opp_grid)

    def minion_skill(self, run: GameRun, my_grid: str, skill_idx: int = 1, target: Optional[str] = None) -> str:
        self.current_run = run
        return self.card_player.minion_skill(run, my_grid, skill_idx, target)

    def _execute_card_effect(self, run: GameRun, card: Card, target: Optional[str] = None) -> str:
        self.current_run = run
        res = card.execute(run, target, self)
        if run.node_data.get("split_to_ten_active"):
            for _ in range(10):
                if self.is_battle_won(run):
                    break
                extra_res = card.execute(run, target, self)
                from ...models.events import CardPlayedEvent
                played_evt = CardPlayedEvent(run, card, target, extra_res, is_extra=True)
                self.event_bus.dispatch(played_evt)
                run.node_data.setdefault("extra_play_msgs", []).append(get_locale_text("i18n_battle_core.split_to_ten_extra", feedback=played_evt.feedback))
        return res

    def get_modified_spell_damage(self, run: GameRun, card: Card, damage: int) -> int:
        """派发伤害计算事件并返回修改后的法术伤害。"""
        dtype = getattr(card, "damage_type", "spell")
        calc_evt = DamageCalculateEvent(run, card, "p0", "e1", dtype, damage, damage)
        self.event_bus.dispatch(calc_evt)
        return calc_evt.modified_damage

    def _discard_card(self, run: GameRun, cid: str) -> str:
        self.current_run = run
        return self.card_player.discard_card(run, cid)

    def end_turn(self, run: GameRun) -> str:
        self.current_run = run
        res = self.card_player.end_turn(run)
        StatsTracker.flush(self.save_manager, run)
        return res

    def _enemy_turn(self, run: GameRun) -> str:
        self.current_run = run
        return self.enemy_controller.enemy_turn(run)

    def _enemy_turn_events(self, run: GameRun) -> TextDocument:
        self.current_run = run
        return self.enemy_controller.enemy_turn_events(run)

    def _handle_battle_win(self, run: GameRun):
        self.current_run = run
        self.card_player.handle_battle_win(run)
        StatsTracker.flush(self.save_manager, run)
    def _roll_enemy_intent(self, run: GameRun):
        self.enemy_controller.roll_enemy_intent(run)

    def get_max_hand_size(self, run, player) -> int:
        from ...models.events import HandLimitCalculateEvent
        evt = HandLimitCalculateEvent(run, player, 12)
        self.event_bus.dispatch(evt)
        return evt.max_hand

    def _reindex_minions(self, p: PlayerState):
        active = [p.minions[k] for k in sorted(p.minions.keys(), key=int)]
        available = [str(i) for i in range(1, 7) if str(i) not in p.amulets]
        new_minions = {}
        for idx, m in enumerate(active):
            if idx < len(available):
                new_minions[available[idx]] = m
        p.minions = new_minions

    def resolve_suspended_card(self, run: GameRun, target: Optional[str] = None):
        self.current_run = run
        suspended_state = run.node_data.pop("suspended_card_cid", None)
        if not suspended_state:
            return
        run.node_data.pop("suspended_card_cost_a", None)
        run.node_data.pop("suspended_card_cost_ba", None)
        run.node_data.pop("suspended_card_hand_idx", None)
        p = run.player
        from ...models.state import ensure_card_state
        suspended_state = ensure_card_state(suspended_state)
        from ...entities.cards.base import ALL_CARDS
        card = ALL_CARDS.get(suspended_state)
        if not card:
            return
        
        res, _ = self.card_player._finalize_card_play(run, p, card, suspended_state, target, "", source="played", register=True)
        if res.strip():
            self._log_event(run, res.strip())

    def rollback_suspended_card(self, run: GameRun):
        self.current_run = run
        suspended_state = run.node_data.pop("suspended_card_cid", None)
        if not suspended_state:
            return
        from ...models.state import ensure_card_state
        suspended_state = ensure_card_state(suspended_state)
        cost_a = run.node_data.pop("suspended_card_cost_a", 0)
        cost_ba = run.node_data.pop("suspended_card_cost_ba", 0)
        hand_idx = run.node_data.pop("suspended_card_hand_idx", None)
        p = run.player
        p.actions += cost_a
        p.bonus_actions += cost_ba
        if hand_idx is not None and 0 <= hand_idx <= len(p.hand):
            p.hand.insert(hand_idx, suspended_state)
        else:
            p.hand.append(suspended_state)
