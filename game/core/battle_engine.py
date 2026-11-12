import random
import re
from typing import Optional
from ..models.state import GameRun, PlayerState, EnemyState, Card
from ..data.map_config import MapConfig
from ..data.enemy_data import ENEMY_CONFIG
from ..data.enemy_data_normal import ENEMY_ENCOUNTER_CONFIG
from ..data.enemy_data_boss import BOSS_POOLS
from ..data.locale_data import get_locale_text
from .battle.base import BaseBattleEngine
from .battle.combat_resolver import CombatResolver
from .battle.card_player import CardPlayer
from .battle.enemy_controller import EnemyTurnController
from .battle.observers import RelicTriggerHandler, BuffTriggerHandler, AmuletTriggerHandler, RallyTriggerHandler, MinionTriggerHandler, EnemyTriggerHandler, CardTriggerHandler, StatTrackingHandler
from .battle.instant_summon import InstantSummonHandler
from .daily_blessing import DailyBlessingHandler
from .deck_service import DeckService
from ..models.stats_tracker import StatsTracker

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

    def _log_event(self, run: Optional[GameRun], msg: str):
        if run is None:
            return
        logs = run.node_data.setdefault("battle_logs", [])
        if getattr(run, "coop_id", ""):
            owners = run.node_data.get("battle_log_owners")
            if not isinstance(owners, list):
                owners = []
                run.node_data["battle_log_owners"] = owners
            if len(owners) < len(logs):
                owners.extend([run.user_id] * (len(logs) - len(owners)))
            elif len(owners) > len(logs):
                del owners[len(logs):]
            owners.append(run.user_id)
        logs.append(msg)

    def _append_logs_to_res(self, run: GameRun, res: str) -> str:
        if "battle_logs" in run.node_data:
            logs = run.node_data.pop("battle_logs", [])
            if getattr(run, "coop_id", ""):
                owners = run.node_data.pop("battle_log_owners", [])
                own_logs = []
                remaining = []
                remaining_owners = []
                for index, msg in enumerate(logs):
                    owner = owners[index] if index < len(owners) else run.user_id
                    if owner == run.user_id:
                        own_logs.append(msg)
                    else:
                        remaining.append(msg)
                        remaining_owners.append(owner)
                if remaining:
                    run.node_data["battle_logs"] = remaining
                    run.node_data["battle_log_owners"] = remaining_owners
                logs = own_logs
            if logs:
                res = res.rstrip() + "\n" + "\n".join(logs)
        elif getattr(run, "coop_id", ""):
            run.node_data.pop("battle_log_owners", None)
        if getattr(run, "coop_id", "") and run.user_id in run.players:
            self.save_manager.save_coop_save(run.user_id, run)
        else:
            self.save_manager.save_save(run.user_id, run)
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
        from ..models.events import CardPlayedCountEvent
        self.event_bus.dispatch(CardPlayedCountEvent(run, count))
        return count

    def _draw_cards(self, p: PlayerState, count: int, run: Optional[GameRun] = None, ignore_focus: bool = False):
        self.card_player.draw_cards(p, count, run, ignore_focus)

    def _init_battle_node(self, run: GameRun, difficulty: str = "normal"):
        self.current_run = run
        if getattr(run, "coop_id", ""):
            self._init_coop_battle(run, difficulty)
            return
        self._init_battle_node_solo(run, difficulty)

    init_battle = _init_battle_node

    def _init_battle_node_solo(self, run: GameRun, difficulty: str = "normal"):
        self.current_run = run
        self._init_player_battle(run, run.player, difficulty)
        self._generate_battle_enemies(run, difficulty)
        from ..models.events import BattleStartEvent, TurnStartEvent
        self.event_bus.dispatch(BattleStartEvent(run))
        evt_turn = TurnStartEvent(run, is_player=True)
        self.event_bus.dispatch(evt_turn)
        self._roll_enemy_intent(run)

    def _init_coop_battle(self, run: GameRun, difficulty: str = "normal"):
        self.current_run = run
        from .coop_engine import CoopEngine
        coop = CoopEngine(self.save_manager, self)
        caller = run.user_id
        viewer = run.player
        if run.node_data.get("temp_minus_1a"):
            run.node_data["drain_a"] = True
            run.node_data.pop("temp_minus_1a", None)
        run.node_data = {
            "turn_count": 1,
            "difficulty": difficulty,
            "turn_ready": {},
        }
        for uid in run.party_order:
            player = run.players[uid]
            run.player = player
            run.user_id = uid
            self._init_player_battle(run, player, difficulty)
            run.node_data["turn_ready"][uid] = player.downed
        run.player = viewer
        run.user_id = caller
        self._generate_battle_enemies(run, difficulty)
        coop.scale_coop_enemies(run)
        coop.assign_enemy_targets(run)
        from ..models.events import BattleStartEvent, TurnStartEvent
        for uid in run.party_order:
            player = run.players[uid]
            if player.downed or player.hp <= 0:
                continue
            run.player = player
            run.user_id = uid
            self.event_bus.dispatch(BattleStartEvent(run))
        run.player = viewer
        run.user_id = caller
        for uid in run.party_order:
            player = run.players[uid]
            if player.downed or player.hp <= 0:
                continue
            run.player = player
            run.user_id = uid
            self.event_bus.dispatch(TurnStartEvent(run, is_player=True))
        run.player = viewer
        run.user_id = caller
        self._roll_enemy_intent(run)
        coop.assign_enemy_targets(run)
        self.save_manager.save_coop_save(caller, run)

    def _init_player_battle(self, run: GameRun, p, difficulty: str):
        player_uid = run.uid_for(p) if getattr(run, "coop_id", "") else run.user_id
        if player_uid:
            stats = self.save_manager.load_stats(player_uid)
            stats_class = getattr(stats, "selected_class", "")
            if stats_class:
                p.selected_class = stats_class
                if stats_class == "战士":
                    p.subclass = ""
                else:
                    p.subclass = getattr(stats, "selected_subclass", "") or p.subclass
        if run.node_data.get("temp_minus_1a"):
            run.node_data["drain_a"] = True
            run.node_data.pop("temp_minus_1a", None)
        p.hand.clear()
        p.draw_pile = p.deck.copy()
        import random
        random.shuffle(p.draw_pile)
        p.discard_pile.clear()
        p.exhaust_pile.clear()
        p.minion_graveyard.clear()
        p.enemy_graveyard.clear()
        p.minions.clear()
        p.amulets.clear()
        p.buffs.clear()
        p.actions = 2
        p.bonus_actions = 1
        p.shield = 0
        run.node_data[run.turn_key("cards_played_this_turn", p)] = 0
        run.node_data["turn_count"] = 1
        selected_class = getattr(p, "selected_class", "法师")
        if selected_class == "战士":
            if getattr(run, "coop_id", ""):
                surge_uid = run.uid_for(p)
                run.node_data[f"action_surge_uses:{surge_uid}"] = 2
                run.node_data[f"action_surge_turn_used:{surge_uid}"] = False
            else:
                run.node_data["action_surge_uses"] = 2
                run.node_data["action_surge_turn_used"] = False

        if getattr(p, "subclass", "") == "时序法师":
            if random.random() < 0.25:
                p.bonus_actions += 1
                self._log_event(run, get_locale_text("i18n_battle_core.time_shift_initial_log"))
        if getattr(p, "subclass", "") == "秘钥学者":
            self._add_buff_to(p, "key_scholar_passive", get_locale_text("i18n_battle_core.key_scholar_buff_name"), get_locale_text("i18n_battle_core.key_scholar_buff_desc"))
        init_draw = 6
        for r in p.relics:
            from ..entities.relics import get_relic_impl
            impl = get_relic_impl(r)
            if impl:
                init_draw = impl.modify_initial_draw(run, init_draw, self)
        self._draw_cards(p, init_draw, run, ignore_focus=True)
        run.node_data["difficulty"] = difficulty

    def _enemy_config_stats(self, name: str):
        cfg = ENEMY_CONFIG[name]
        hp_match = re.match(r"^(\d+)", str(cfg["hp"]))
        actions_str = str(cfg["actions"])
        actions_match = re.search(r"(\d+)A", actions_str)
        bonus_match = re.search(r"(\d+)BA", actions_str)
        return int(hp_match.group(1)), int(actions_match.group(1)), int(bonus_match.group(1))

    def _build_enemy_state(self, name: str, hp: int, actions: int, bonus_actions: int) -> EnemyState:
        return EnemyState(
            name=name,
            hp=hp,
            max_hp=hp,
            shield=0,
            actions=actions,
            bonus_actions=bonus_actions,
            max_actions=actions,
            max_bonus_actions=bonus_actions
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
            if p.stage == MapConfig.GATE_BOSS_STAGE:
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
                    from .achievement_service import AchievementService
                    AchievementService(self.save_manager).reconcile(run.user_id, stats=stats, save=False, run=run, battle_engine=self)
                    self.save_manager.save_stats(run.user_id, stats)
                    challenge_count = stats.yog_sothoth_challenge_count
                else:
                    challenge_count = 1
                if challenge_count == 1:
                    self._log_event(run, get_locale_text("i18n_battle_core.yog_sothoth_intro_first"))
                else:
                    self._log_event(run, get_locale_text("i18n_battle_core.yog_sothoth_intro_repeat", name=run.player.name))
            else:
                run.node_data["boss_name"] = boss_name
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
            run.enemies = [EnemyState(
                name=ghost_name,
                hp=ghost_hp,
                max_hp=ghost_hp,
                shield=0,
                actions=1,
                bonus_actions=0,
                max_actions=1,
                max_bonus_actions=0
            )]
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
        from ..entities import get_enemy_template
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
                from ..models.events import CardPlayedEvent
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

    def _handle_battle_win(self, run: GameRun):
        self.current_run = run
        if getattr(run, "coop_id", ""):
            from .coop_engine import CoopEngine
            CoopEngine(self.save_manager, self).handle_coop_battle_win(run)
            self.save_manager.save_save(run.user_id, run)
            StatsTracker.flush(self.save_manager, run)
            return
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
        from ..models.events import CardExhaustEvent
        from ..entities.cards.base import ALL_CARDS
        for cid in cards_to_exhaust:
            DeckService.add_card_to_exhaust(p, cid)
            card_obj = ALL_CARDS.get(cid)
            cname = card_obj.name if card_obj else cid
            self._log_event(run, get_locale_text("i18n_battle_core.exhaust_to_pile_log", name=cname))
            self.event_bus.dispatch(CardExhaustEvent(run, cid, "emperor_eye"))
            exhausted_count += 1
        card_pool = []
        for cid, card_obj in ALL_CARDS.items():
            if not cid.startswith("duel_") and not cid.startswith("curse_") and not cid.endswith("+"):
                if not getattr(card_obj, "unplayable", False) and not getattr(card_obj, "coop_only", False):
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

    def resolve_suspended_card(self, run: GameRun):
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
        from ..models.state import ensure_card_state
        suspended_state = ensure_card_state(suspended_state)
        from ..entities.cards.base import ALL_CARDS
        card = ALL_CARDS.get(suspended_state)
        if not card:
            return
        
        res, _ = self.card_player._finalize_card_play(run, p, card, suspended_state, None, "", source="played", register=True)
        if res.strip():
            self._log_event(run, res.strip())

    def rollback_suspended_card(self, run: GameRun):
        self.current_run = run
        suspended_state = run.node_data.pop("suspended_card_cid", None)
        if not suspended_state:
            suspended_state = run.node_data.pop("emperor_eye_cid", None)
        if not suspended_state:
            return
        from ..models.state import ensure_card_state
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
