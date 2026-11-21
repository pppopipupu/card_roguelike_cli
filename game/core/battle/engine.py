import random
import re
from typing import Optional
from ...models.state import GameRun, PlayerState, EnemyState, Card, UserStats
from ...data.map_config import MapConfig
from ...data.enemy_data import ENEMY_CONFIG
from ...data.enemy_data_normal import ENEMY_ENCOUNTER_CONFIG
from ...data.enemy_data_boss import BOSS_POOLS
from ...data.corpse_config import CorpseConfig
from ...data.locale_data import get_locale_text
from .base import BaseBattleEngine
from .combat_resolver import CombatResolver
from .card_player import CardPlayer
from .enemy_controller import EnemyTurnController
from .observers import RelicTriggerHandler, BuffTriggerHandler, AmuletTriggerHandler, RallyTriggerHandler, MinionTriggerHandler, EnemyTriggerHandler, CardTriggerHandler, StatTrackingHandler
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


class BattleEngine(BaseBattleEngine):
    def __init__(self, save_manager):
        super().__init__(save_manager)
        self.current_run = None
        self.combat_resolver = CombatResolver(self)
        self.card_player = CardPlayer(self)
        self.enemy_controller = EnemyTurnController(self)
        self.relic_handler = RelicTriggerHandler(self.event_bus, self)
        self.buff_handler = BuffTriggerHandler(self.event_bus, self)
        self.amulet_handler = AmuletTriggerHandler(self.event_bus, self)
        self.rally_handler = RallyTriggerHandler(self.event_bus, self)
        self.minion_handler = MinionTriggerHandler(self.event_bus, self)
        self.enemy_handler = EnemyTriggerHandler(self.event_bus, self)
        self.card_handler = CardTriggerHandler(self.event_bus, self)
        self.stat_tracking_handler = StatTrackingHandler(self.event_bus, self.save_manager)
        self.instant_summon_handler = InstantSummonHandler(self.event_bus, self)
        self.daily_blessing_handler = DailyBlessingHandler(self.event_bus, self)
        from ..party.mercenary import MercenaryVoiceHandler
        self.mercenary_voice_handler = MercenaryVoiceHandler(self.event_bus, self)
        self.exhaustion_observer = ExhaustionObserver(self.event_bus, self)
        self.anna_handler = AnnaCardHandler(self.event_bus, self)
        self.millika_handler = MillikaCardHandler(self.event_bus, self)
        self.ultimate_prism_handler = UltimatePrismHandler(self.event_bus, self)
        from ...models.events import CardExhaustEvent, LexKelaChangedEvent
        from .ninja_runtime import handle_lex_kela_changed, handle_ninja_card_exhaust
        self.event_bus.subscribe(LexKelaChangedEvent, lambda evt: handle_lex_kela_changed(self, evt))
        self.event_bus.subscribe(CardExhaustEvent, lambda evt: handle_ninja_card_exhaust(self, evt))

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
        if self.current_run is not None and buff_id == "fusion_overcharge" and not getattr(entity, "is_mercenary", False):
            uid = self.current_run.uid_for(entity)
            if uid and (uid == getattr(self.current_run, "user_id", "") or uid in self.current_run.human_uids()):
                total = sum(b.stacks for b in getattr(entity, "buffs", []) if b.id == "fusion_overcharge")
                if total >= 8:
                    from ..progress.achievement_service import AchievementService

                    AchievementService(self.save_manager).record_stat(
                        uid,
                        "max_fusion_overcharge",
                        total,
                        mode="max",
                        run=self.current_run,
                        battle_engine=self,
                    )

    def _get_free_grid(self, p: PlayerState) -> Optional[str]:
        return self.combat_resolver.get_free_grid(p)

    def _register_card_played(self, run: GameRun) -> int:
        key = run.turn_key("cards_played_this_turn")
        count = run.node_data.get(key, 0) + 1
        run.node_data[key] = count
        from ...models.events import CardPlayedCountEvent
        self.event_bus.dispatch(CardPlayedCountEvent(run, count))
        return count

    def _draw_cards(self, p: PlayerState, count: int, run: Optional[GameRun] = None, ignore_focus: bool = False):
        self.card_player.draw_cards(p, count, run, ignore_focus)

    def _init_battle_node(self, run: GameRun, difficulty: str = "normal"):
        self.current_run = run
        from .party_battle import assign_enemy_targets, scale_party_enemies
        caller = run.user_id
        viewer = run.player
        if run.node_data.get("temp_minus_1a"):
            run.node_data["drain_a"] = True
            run.node_data.pop("temp_minus_1a", None)
        run.node_data.pop("enemy_targets", None)
        run.node_data.pop("coop_aggro_cursor", None)
        run.node_data.pop("coop_hp_mult", None)
        run.node_data.pop("break_limits_ignore_cap", None)
        run.node_data["turn_count"] = 1
        run.node_data["difficulty"] = difficulty
        turn_ready = {}
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            run.player = player
            run.user_id = uid
            self._init_player_battle(run, player, difficulty)
            turn_ready[uid] = player.downed or getattr(player, "is_mercenary", False)
        run.node_data["turn_ready"] = turn_ready
        run.player = viewer
        run.user_id = caller
        self._generate_battle_enemies(run, difficulty)
        scale_party_enemies(run)
        assign_enemy_targets(run)
        from ...models.events import BattleStartEvent, TurnStartEvent
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None or player.downed or player.hp <= 0:
                continue
            run.player = player
            run.user_id = uid
            self.event_bus.dispatch(BattleStartEvent(run))
        run.player = viewer
        run.user_id = caller
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None or player.downed or player.hp <= 0:
                continue
            run.player = player
            run.user_id = uid
            self.event_bus.dispatch(TurnStartEvent(run, is_player=True))
        run.player = viewer
        run.user_id = caller
        self._roll_enemy_intent(run)
        assign_enemy_targets(run)
        from ..party.mercenary import run_mercenaries_for_timing
        from ...data.mercenary_data import MERCENARY_TIMING_BEFORE
        merc_logs = run_mercenaries_for_timing(self, run, MERCENARY_TIMING_BEFORE)
        if merc_logs:
            self._log_event(run, merc_logs)
        if self.is_battle_won(run):
            from .party_battle import is_all_downed
            if not is_all_downed(run):
                self.card_player.handle_battle_win(run)

    init_battle = _init_battle_node

    def join_battle(self, run: GameRun, uid: str):
        player = run.players.get(uid)
        if player is None or player.downed or player.hp <= 0:
            return
        caller = run.user_id
        viewer = run.player
        difficulty = str(run.node_data.get("difficulty") or "normal")
        is_mercenary = bool(getattr(player, "is_mercenary", False))
        run.player = player
        run.user_id = uid
        self._init_player_battle(run, player, difficulty)
        run.node_data.setdefault("turn_ready", {})[uid] = is_mercenary
        if not is_mercenary:
            from ...models.events import BattleStartEvent, TurnStartEvent
            self.event_bus.dispatch(BattleStartEvent(run))
            self.event_bus.dispatch(TurnStartEvent(run, is_player=True))
        run.player = viewer
        run.user_id = caller
        from .party_battle import assign_enemy_targets
        assign_enemy_targets(run)

    def _init_player_battle(self, run: GameRun, p, difficulty: str):
        player_uid = run.uid_for(p)
        if player_uid and not getattr(p, "is_mercenary", False) and hasattr(self.save_manager, "load_stats"):
            stats = self.save_manager.load_stats(player_uid)
            stats_class = getattr(stats, "selected_class", "")
            if stats_class:
                p.selected_class = stats_class
                if stats_class in ("战士", "蕾忍"):
                    p.subclass = ""
                else:
                    p.subclass = getattr(stats, "selected_subclass", "") or p.subclass
        if run.node_data.get("temp_minus_1a"):
            run.node_data["drain_a"] = True
            run.node_data.pop("temp_minus_1a", None)
        p.hand.clear()
        p.draw_pile = []
        for c in p.deck:
            cloned = DeckService.clone_state(c)
            cloned.exhaust_used = 0
            cloned.temp_cost_a = None
            cloned.battle_cost_delta_a = 0
            p.draw_pile.append(cloned)
        import random
        random.shuffle(p.draw_pile)
        p.discard_pile.clear()
        from .enchantment_runtime import apply_grave_enchantments_at_battle_start
        apply_grave_enchantments_at_battle_start(self, run, p)
        p.exhaust_pile.clear()
        p.minion_graveyard.clear()
        p.enemy_graveyard.clear()
        p.minions.clear()
        p.amulets.clear()
        p.buffs.clear()
        from ..world.persistent_buffs import break_map_invisibility, sync_persistent_buffs_to_battle
        broken_msg = break_map_invisibility(run, reason="battle", player=p)
        if broken_msg:
            self._log_event(run, broken_msg)
        sync_persistent_buffs_to_battle(p)
        if getattr(p, "selected_class", "法师") == "蕾忍":
            p.actions = 3
            p.bonus_actions = 0
        else:
            p.actions = 2
            p.bonus_actions = 1
        p.shield = 0
        p.lex_kela = 0
        run.node_data[run.turn_key("lex_kela_spent_this_turn", p)] = False
        run.node_data[run.turn_key("cards_played_this_turn", p)] = 0
        selected_class = getattr(p, "selected_class", "法师")
        if selected_class == "战士":
            run.node_data[run.turn_key("action_surge_uses", p)] = 2
            run.node_data[run.turn_key("action_surge_turn_used", p)] = False
        if getattr(p, "subclass", "") == "时序法师":
            if random.random() < 0.25:
                p.bonus_actions += 1
                self._log_event(run, locale_text(key="i18n_battle_core.time_shift_initial_log"))
        if getattr(p, "subclass", "") == "秘钥学者":
            self._add_buff_to(p, "key_scholar_passive", get_locale_text("i18n_battle_core.key_scholar_buff_name"), get_locale_text("i18n_battle_core.key_scholar_buff_desc"))
        init_draw = 6
        for r in p.relics:
            from ...entities.relics import get_relic_impl
            impl = get_relic_impl(r)
            if impl:
                init_draw = impl.modify_initial_draw(run, init_draw, self)
        init_draw = self.exhaustion_observer.modify_initial_draw(p, init_draw)
        self._draw_cards(p, init_draw, run, ignore_focus=True)
        run.node_data["difficulty"] = difficulty
        if getattr(run, "enemies", None):
            from ..world.encounter_lore import record_encounter_for_run

            record_encounter_for_run(self.save_manager, run, *(e.name for e in run.enemies if getattr(e, "name", "")))

    def _enemy_config_stats(self, name: str):
        cfg = ENEMY_CONFIG[name]
        hp_match = re.match(r"^(\d+)", str(cfg["hp"]))
        actions_str = str(cfg["actions"])
        actions_match = re.search(r"(\d+)A", actions_str)
        bonus_match = re.search(r"(\d+)BA", actions_str)
        if hp_match is None or actions_match is None or bonus_match is None:
            raise ValueError(f"invalid enemy config: {name}")
        return int(hp_match.group(1)), int(actions_match.group(1)), int(bonus_match.group(1))

    def _build_enemy_state(self, name: str, hp: int, actions: int, bonus_actions: int, size: str = "") -> EnemyState:
        from ...data.size_data import resolve_enemy_size
        return EnemyState(
            name=name,
            hp=hp,
            max_hp=hp,
            shield=0,
            actions=actions,
            bonus_actions=bonus_actions,
            max_actions=actions,
            max_bonus_actions=bonus_actions,
            size=resolve_enemy_size(name, size or None),
        )

    def _stage_enemy_pool(self, pools, stage):
        for entry in pools:
            if entry.get("max_stage") is None or stage <= entry["max_stage"]:
                return entry["names"]
        return pools[-1]["names"]

    def _create_boss_enemy(self, name: str) -> EnemyState:
        hp, actions, bonus_actions = self._enemy_config_stats(name)
        return self._build_enemy_state(name, hp, actions, bonus_actions)

    def _generate_battle_enemies(self, run: GameRun, difficulty: str):
        p = run.player
        if difficulty == "boss":
            preset_boss = str((run.node_data or {}).get("preset_boss_name") or "")
            if preset_boss:
                boss_name = preset_boss
            elif p.stage == MapConfig.GATE_BOSS_STAGE:
                boss_name = random.choice(BOSS_POOLS["gate"])
            elif p.stage == MapConfig.AVERGOMON_STAGE:
                boss_name = BOSS_POOLS["aforgomon"][0]
            elif p.stage == MapConfig.FINAL_BOSS_STAGE:
                boss_name = BOSS_POOLS["final"][0]
            else:
                boss_name = random.choice(BOSS_POOLS["early"])
            run.enemies = [self._create_boss_enemy(boss_name)]
            if boss_name == "腐化之心":
                self._add_buff_to(run.enemies[0], "beat_of_death", get_locale_text("i18n_battle_core.beat_of_death_name"), get_locale_text("i18n_battle_core.beat_of_death_desc"))
                self._add_buff_to(run.enemies[0], "unyielding", get_locale_text("i18n_battle_core.unyielding_name"), get_locale_text("i18n_battle_core.unyielding_desc"), 40)
                run.node_data["boss_name"] = boss_name
            elif boss_name == "雷霆领主":
                run.node_data["boss_name"] = boss_name
                run.node_data["thunder_lord_turn"] = 1
            elif boss_name == "Icerainboww":
                run.node_data["boss_name"] = boss_name
                run.node_data["icerainboww_turn"] = 1
            elif boss_name == "虚空之门·尤格-索托斯":
                self._add_buff_to(run.enemies[0], "ancient_protection", get_locale_text("i18n_battle_core.ancient_protection_name"), get_locale_text("i18n_battle_core.ancient_protection_desc"))
                run.node_data["boss_name"] = boss_name
                run.node_data["yog_sothoth_phase"] = 1
                run.node_data["yog_sothoth_turn"] = 1
                stats = self.save_manager.load_stats(run.user_id)
                if stats:
                    stats.yog_sothoth_challenge_count = getattr(stats, "yog_sothoth_challenge_count", 0) + 1
                    from ..progress.achievement_service import AchievementService
                    AchievementService(self.save_manager).reconcile(run.user_id, stats=stats, save=False, run=run, battle_engine=self)
                    self.save_manager.save_stats(run.user_id, stats)
                    challenge_count = stats.yog_sothoth_challenge_count
                else:
                    challenge_count = 1
                if challenge_count == 1:
                    self._log_event(run, locale_text(key="i18n_battle_core.yog_sothoth_intro_first"))
                else:
                    self._log_event(run, locale_text(key="i18n_battle_core.yog_sothoth_intro_repeat", params={"name": run.player.name}))
            else:
                run.node_data["boss_name"] = boss_name
        elif difficulty == "secret_boss":
            boss_name = run.node_data.get("secret_boss_name") or random.choice(BOSS_POOLS["secret"])
            run.enemies = [self._create_boss_enemy(boss_name)]
            run.node_data["boss_name"] = boss_name
            run.node_data["is_secret_boss"] = True
        elif difficulty == "elite":
            encounter = ENEMY_ENCOUNTER_CONFIG["elite"]
            elite_pool = self._stage_enemy_pool(encounter["pools"], p.stage)
            run.enemies = []
            base_name = random.choice(elite_pool)
            run.node_data["elite_name"] = base_name
            base_hp, actions, bonus_actions = self._enemy_config_stats(base_name)
            hp_final = base_hp + p.stage * encounter["hp_per_stage"]
            run.enemies.append(self._build_enemy_state(base_name, hp_final, actions, bonus_actions))
        elif difficulty == "ghost":
            ghost_name = str(run.node_data.get("ghost_name", get_locale_text("i18n_battle_core.ghost_default_name")))
            ghost_hp = max(1, int(run.node_data.get("ghost_max_hp", 60) or 60))
            ghost_actions = max(1, int(CorpseConfig.GHOST_ACTIONS))
            ghost_bonus_actions = max(0, int(CorpseConfig.GHOST_BONUS_ACTIONS))
            run.enemies = [EnemyState(
                name=ghost_name,
                hp=ghost_hp,
                max_hp=ghost_hp,
                shield=0,
                actions=ghost_actions,
                bonus_actions=ghost_bonus_actions,
                max_actions=ghost_actions,
                max_bonus_actions=ghost_bonus_actions
            )]
        elif difficulty == "npc_combat":
            npc_info = run.node_data.get("npc_combat") or {}
            enemy_name = str(npc_info.get("enemy_name", get_locale_text("i18n_battle_core.ghost_default_name")))
            hp = max(1, int(npc_info.get("hp", 60) or 60))
            actions = max(1, int(npc_info.get("actions", 1) or 1))
            bonus_actions = max(0, int(npc_info.get("bonus_actions", 1) or 0))
            run.enemies = [self._build_enemy_state(enemy_name, hp, actions, bonus_actions)]
        else:
            encounter = ENEMY_ENCOUNTER_CONFIG["normal"]
            normal_pool = self._stage_enemy_pool(encounter["pools"], p.stage)
            run.enemies = []
            count_min, count_max = encounter["count_range"]
            num_enemies = random.randint(count_min, count_max)
            selected_names = [random.choice(normal_pool) for _ in range(num_enemies)]
            for i, base_name in enumerate(selected_names):
                base_hp, actions, bonus_actions = self._enemy_config_stats(base_name)
                hp_final = base_hp + p.stage * encounter["hp_per_stage"]
                name = f"{base_name} {chr(65 + i)}" if num_enemies > 1 else base_name
                run.enemies.append(self._build_enemy_state(name, hp_final, actions, bonus_actions))
        from ...entities import get_enemy_template
        for enemy in list(run.enemies):
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_battle_start") and not getattr(enemy, "_battle_init_done", False):
                enemy._battle_init_done = True
                template.on_battle_start(run, enemy, self)

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
        return self.combat_resolver.get_modified_spell_damage(run, card, damage)

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

    def _reindex_minions(self, p: PlayerState):
        active = [p.minions[k] for k in sorted(p.minions.keys(), key=int)]
        available = [str(i) for i in range(1, 7) if str(i) not in p.amulets]
        new_minions = {}
        for idx, m in enumerate(active):
            if idx < len(available):
                new_minions[available[idx]] = m
        p.minions = new_minions

    def execute_emperor_eye_resolve(self, run: GameRun, keep_idx: int, upgraded: bool) -> str:
        self.current_run = run
        p = run.player
        exhausted_count = 0
        retained_cid = None
        if 0 <= keep_idx < len(p.hand):
            retained_cid = p.hand[keep_idx]
        cards_to_exhaust = []
        for i, cid in enumerate(p.hand):
            if i != keep_idx:
                cards_to_exhaust.append(cid)
        p.hand.clear()
        if retained_cid:
            DeckService.add_card_to_hand(p, retained_cid)
        from ...models.events import CardExhaustEvent
        from ...entities.cards.base import ALL_CARDS
        for cid in cards_to_exhaust:
            DeckService.add_card_to_exhaust(p, cid)
            card_obj = ALL_CARDS.get(cid)
            cname = card_obj.name if card_obj else cid
            self._log_event(run, locale_text(key="i18n_battle_core.exhaust_to_pile_log", params={"name": cname}))
            self.event_bus.dispatch(CardExhaustEvent(run, cid, "emperor_eye"))
            exhausted_count += 1
        from ...entities.cards.market import is_card_available
        stat_uid = getattr(p, "mercenary_owner", "") if getattr(p, "is_mercenary", False) else run.user_id
        stats = self.save_manager.load_stats(stat_uid) if stat_uid and hasattr(self.save_manager, "load_stats") else None
        card_pool = []
        for cid, card_obj in ALL_CARDS.items():
            if not cid.startswith("duel_") and not cid.startswith("curse_") and not cid.endswith("+"):
                if not getattr(card_obj, "unplayable", False) and not getattr(card_obj, "coop_only", False) and not getattr(card_obj, "token", False) and not getattr(card_obj, "event_only", False) and not getattr(card_obj, "life_merchant_only", False) and getattr(card_obj, "color", "") != "mercenary" and is_card_available(cid, stats):
                    card_pool.append(cid)
        drawn = []
        if card_pool and exhausted_count > 0:
            import random
            max_hand = 9 if "mask_of_void" in p.relics else 12
            for _ in range(exhausted_count):
                if len(p.hand) < max_hand:
                    new_cid = random.choice(card_pool)
                    DeckService.add_card_to_hand(p, new_cid)
                    card_obj = ALL_CARDS.get(new_cid)
                    drawn.append(card_obj.name if card_obj else new_cid)
        dmg_msg = ""
        if upgraded:
            alive_enemies = [e for e in run.enemies if e.hp > 0]
            if alive_enemies:
                import random
                target_enemy = random.choice(alive_enemies)
                target_idx = run.enemies.index(target_enemy) + 1
                self.combat_resolver.damage_target(run, f"e{target_idx}", 49, source="p0", damage_type="force")
                dmg_msg = get_locale_text("i18n_battle_core.emperor_eye_damage_log", name=target_enemy.name)
        self.resolve_suspended_card(run)

        retained_name = ALL_CARDS[retained_cid].name if retained_cid else get_locale_text("i18n_battle_core.none_label")
        drawn_str = "，".join(drawn) if drawn else get_locale_text("i18n_battle_core.none_label")
        res_str = get_locale_text("i18n_battle_core.emperor_eye_success_log", retained_name=retained_name, count=exhausted_count, drawn=drawn_str, damage_msg=dmg_msg)
        self.save_manager.save_save(run.user_id, run)
        return self._append_logs_to_res(run, res_str)

    def resolve_suspended_card(self, run: GameRun, target: Optional[str] = None):
        self.current_run = run
        suspended_state = run.node_data.pop("suspended_card_cid", None)
        if not suspended_state:
            suspended_state = run.node_data.pop("emperor_eye_cid", None)
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
            suspended_state = run.node_data.pop("emperor_eye_cid", None)
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
