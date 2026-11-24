import random
import re
from typing import Optional

from ...models.state import GameRun, PlayerState, EnemyState
from ...data.world.grid_map_config import (
    FLOOR_CONFIGS,
    get_floor_difficulty_scale,
    get_run_floor_index,
)
from ...data.enemies.enemy_data import ENEMY_CONFIG
from ...data.enemies.enemy_data_normal import ENEMY_ENCOUNTER_CONFIG
from ...data.enemies.enemy_data_boss import BOSS_POOLS
from ...data.entities.corpse_config import CorpseConfig
from ...data.text.locale_data import get_locale_text
from ..inventory.deck_service import DeckService
from .base import BaseBattleEngine


class BattleSetupMixin(BaseBattleEngine):
    """战斗初始化与敌人生成流程，供 BattleEngine 以 Facade 方式组合。"""

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
        assign_enemy_targets(run, self)
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
        assign_enemy_targets(run, self)
        from ..party.mercenary import run_mercenaries_for_timing
        from ...data.entities.mercenary_data import MERCENARY_TIMING_BEFORE
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
        assign_enemy_targets(run, self)

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
            cloned.temp_cost_ba = None
            cloned.battle_cost_delta_a = 0
            cloned.lyric_form = 0
            cloned.temp_ethereal = False
            cloned.temp_exhaust = False
            cloned.temp_retain = False
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
        from ...models.events import TurnResourceInitEvent
        resource_evt = TurnResourceInitEvent(run, p, 2, 1, True)
        self.event_bus.dispatch(resource_evt)
        p.actions = resource_evt.actions
        p.bonus_actions = resource_evt.bonus_actions
        p.shield = 0
        p.lex_kela = 0
        run.node_data[run.turn_key("lex_kela_spent_this_turn", p)] = False
        run.node_data[run.turn_key("cards_played_this_turn", p)] = 0
        from .rainie_runtime import apply_legacy_at_battle_start, reset_lyric_progress
        reset_lyric_progress(run, p)
        legacy_msg = apply_legacy_at_battle_start(self, run, p)
        if legacy_msg:
            self._log_event(run, legacy_msg)
        from ...models.events import TurnDrawCalculateEvent
        draw_evt = TurnDrawCalculateEvent(run, p, 6, is_initial=True)
        self.event_bus.dispatch(draw_evt)
        init_draw = draw_evt.draw_count
        innate_cards = []
        from ...entities.cards.base import ALL_CARDS
        for c_state in list(p.draw_pile):
            card = ALL_CARDS.get(c_state)
            if card is not None and getattr(card, "innate", False):
                innate_cards.append(c_state)
                p.draw_pile.remove(c_state)
        max_hand = self.get_max_hand_size(run, p)
        for c_state in innate_cards:
            if len(p.hand) < max_hand:
                p.hand.append(c_state)
                init_draw = max(0, init_draw - 1)
            else:
                p.draw_pile.append(c_state)
        self._draw_cards(p, init_draw, run, ignore_focus=True, is_turn_start=True)
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
        from ...data.entities.size_data import resolve_enemy_size
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

    def _floor_enemy_pool(self, pools, floor_index):
        f_val = float(floor_index)
        for entry in pools:
            if entry.get("max_floor") is None or f_val <= float(entry["max_floor"]):
                return entry["names"]
        return pools[-1]["names"]

    def _create_boss_enemy(self, name: str) -> EnemyState:
        hp, actions, bonus_actions = self._enemy_config_stats(name)
        return self._build_enemy_state(name, hp, actions, bonus_actions)

    def _generate_battle_enemies(self, run: GameRun, difficulty: str):
        floor_index = get_run_floor_index(run)
        scale = get_floor_difficulty_scale(floor_index)
        floor_cfg = FLOOR_CONFIGS.get(floor_index, FLOOR_CONFIGS[1])
        if difficulty == "boss":
            preset_boss = str((run.node_data or {}).get("preset_boss_name") or "")
            if preset_boss:
                boss_name = preset_boss
            else:
                pool_key = str(floor_cfg.get("boss_pool") or "early")
                pool = BOSS_POOLS.get(pool_key, BOSS_POOLS["early"])
                boss_name = pool[0] if len(pool) == 1 else random.choice(pool)
            run.enemies = [self._create_boss_enemy(boss_name)]
            run.node_data["boss_name"] = boss_name
        elif difficulty == "secret_boss":
            boss_name = run.node_data.get("secret_boss_name") or random.choice(BOSS_POOLS["secret"])
            run.enemies = [self._create_boss_enemy(boss_name)]
            run.node_data["boss_name"] = boss_name
            run.node_data["is_secret_boss"] = True
        elif difficulty == "elite":
            encounter = ENEMY_ENCOUNTER_CONFIG["elite"]
            elite_pool = self._floor_enemy_pool(encounter["pools"], floor_index)
            run.enemies = []
            base_name = random.choice(elite_pool)
            run.node_data["elite_name"] = base_name
            base_hp, actions, bonus_actions = self._enemy_config_stats(base_name)
            hp_final = base_hp + scale * encounter["hp_per_stage"]
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
            normal_pool = self._floor_enemy_pool(encounter["pools"], floor_index)
            run.enemies = []
            count_min, count_max = encounter["count_range"]
            num_enemies = random.randint(count_min, count_max)
            selected_names = [random.choice(normal_pool) for _ in range(num_enemies)]
            for i, base_name in enumerate(selected_names):
                base_hp, actions, bonus_actions = self._enemy_config_stats(base_name)
                hp_final = base_hp + scale * encounter["hp_per_stage"]
                name = f"{base_name} {chr(65 + i)}" if num_enemies > 1 else base_name
                run.enemies.append(self._build_enemy_state(name, hp_final, actions, bonus_actions))
        from ...entities import get_enemy_template
        for enemy in list(run.enemies):
            template = get_enemy_template(enemy.name)
            if template and hasattr(template, "on_battle_start") and not getattr(enemy, "_battle_init_done", False):
                enemy._battle_init_done = True
                template.on_battle_start(run, enemy, self)
