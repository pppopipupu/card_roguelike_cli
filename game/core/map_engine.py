import random
from typing import Optional
from ..models.state import GameRun
from ..data.balance_config import (
    MAP_ANCIENT_OPTION_SLOTS,
    MAP_ANCIENT_RELIC_CHOICES,
    MAP_LUCKY_COIN_GOLD,
    MAP_TAX_CONTRACT_GOLD,
)
from ..data.grid_map_config import FLOOR_CONFIGS
from ..data.locale_data import get_locale_text
from .explore_engine import ExploreEngine
from .grid_map_generator import generate_floor_map, xy_to_coord
from .grid_map_service import GridMapService
from .landmark_system import execute_downstairs_option, execute_landmark_option
from .session_manager import SessionContextScoper
from .sp_system import reduce_exhaustion


class MapEngine:
    def __init__(self, save_manager, battle_engine):
        self.save_manager = save_manager
        self.battle_engine = battle_engine
        self.explore_engine = ExploreEngine(save_manager, self)
        self.grid_map_service = GridMapService(save_manager, self)

    def _build_start_ancient_data(self, run: GameRun, icerainboww_enabled: bool) -> dict:
        stats = self.save_manager.load_stats(run.user_id) if hasattr(self.save_manager, "load_stats") else None
        p_class = getattr(stats, "selected_class", "法师")
        if p_class == "战士":
            style = random.choice(["default", "abyss"])
        else:
            style = random.choice(["default", "abyss", "glacier"])
        if p_class == "战士":
            if style == "default":
                relics_pool = [
                    {"type": "double", "relic": "mark_of_fury"},
                    {"type": "double", "relic": "greedy_contract"},
                    {"type": "double", "relic": "mask_of_void"},
                    {"type": "double", "relic": "unstable_crystal"},
                    {"type": "double", "relic": "vampiric_touch"},
                    {"type": "double", "relic": "ancient_page"},
                ]
                cards_pool = [
                    {"type": "contract", "relic": "rust_shackle", "card": "demon_form"},
                    {"type": "contract", "relic": "fool_oath", "card": "impervious"},
                    {"type": "contract", "relic": "blind_spot", "card": "demon_form"},
                    {"type": "contract", "relic": "tax_contract", "card": "impervious"},
                    {"type": "contract", "relic": "blind_spot", "card": "break_limits"},
                    {"type": "contract", "relic": "blind_spot", "card": "unmined_gem"},
                ]
                if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
                    cards_pool.append({"type": "contract", "relic": "wither_seed", "card": "minion_icerainboww"})
            else:
                relics_pool = [
                    {"type": "double", "relic": "abyss_gaze"},
                    {"type": "double", "relic": "mark_of_fury"},
                    {"type": "double", "relic": "greedy_contract"},
                    {"type": "double", "relic": "abyss_contract"},
                ]
                cards_pool = [
                    {"type": "contract", "relic": "shadow_curse", "card": "abyss_collapse"},
                    {"type": "contract", "relic": "shadow_curse", "card": "demon_contract"},
                    {"type": "contract", "relic": "shadow_curse", "card": "abyss_erosion"},
                    {"type": "contract", "relic": "shadow_curse", "card": "abyss_altar"},
                    {"type": "contract", "relic": "shadow_curse", "card": "break_limits"},
                    {"type": "contract", "relic": "shadow_curse", "card": "unmined_gem"},
                ]
                if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
                    cards_pool.append({"type": "contract", "relic": "shadow_curse", "card": "minion_icerainboww"})
        else:
            if style == "default":
                relics_pool = [
                    {"type": "double", "relic": "mark_of_fury"},
                    {"type": "double", "relic": "greedy_contract"},
                    {"type": "double", "relic": "mask_of_void"},
                    {"type": "double", "relic": "unstable_crystal"},
                    {"type": "double", "relic": "vampiric_touch"},
                    {"type": "double", "relic": "ancient_page"},
                ]
                cards_pool = [
                    {"type": "contract", "relic": "rust_shackle", "card": "doomsday_judgment"},
                    {"type": "contract", "relic": "fool_oath", "card": "time_warp"},
                    {"type": "contract", "relic": "wither_seed", "card": "magic_network"},
                    {"type": "contract", "relic": "blind_spot", "card": "meteor_swarm"},
                    {"type": "contract", "relic": "tax_contract", "card": "archmage_wish"},
                    {"type": "contract", "relic": "blind_spot", "card": "break_limits"},
                    {"type": "contract", "relic": "blind_spot", "card": "unmined_gem"},
                ]
                if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
                    cards_pool.append({"type": "contract", "relic": "wither_seed", "card": "minion_icerainboww"})
            elif style == "abyss":
                relics_pool = [
                    {"type": "double", "relic": "abyss_gaze"},
                    {"type": "double", "relic": "mark_of_fury"},
                    {"type": "double", "relic": "greedy_contract"},
                    {"type": "double", "relic": "abyss_contract"},
                ]
                cards_pool = [
                    {"type": "contract", "relic": "shadow_curse", "card": "abyss_collapse"},
                    {"type": "contract", "relic": "shadow_curse", "card": "demon_contract"},
                    {"type": "contract", "relic": "shadow_curse", "card": "abyss_erosion"},
                    {"type": "contract", "relic": "shadow_curse", "card": "abyss_altar"},
                    {"type": "contract", "relic": "shadow_curse", "card": "break_limits"},
                    {"type": "contract", "relic": "shadow_curse", "card": "unmined_gem"},
                ]
                if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
                    cards_pool.append({"type": "contract", "relic": "shadow_curse", "card": "minion_icerainboww"})
            else:
                relics_pool = [
                    {"type": "double", "relic": "glacier_armor"},
                    {"type": "double", "relic": "frost_blade"},
                    {"type": "double", "relic": "glacier_core"},
                    {"type": "double", "relic": "mark_of_fury"},
                ]
                cards_pool = [
                    {"type": "contract", "relic": "glacier_chill", "card": "frost_nova"},
                    {"type": "contract", "relic": "glacier_chill", "card": "glacier_fortress"},
                    {"type": "contract", "relic": "glacier_chill", "card": "glacier_tempest"},
                    {"type": "contract", "relic": "glacier_chill", "card": "break_limits"},
                    {"type": "contract", "relic": "glacier_chill", "card": "unmined_gem"},
                ]
                if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
                    cards_pool.append({"type": "contract", "relic": "glacier_chill", "card": "minion_icerainboww"})
        relics_pool.append({"type": "double", "relic": "trash_mountain"})
        num_relics = random.choice(MAP_ANCIENT_RELIC_CHOICES)
        selected_relics = random.sample(relics_pool, min(len(relics_pool), num_relics))
        selected_cards = random.sample(cards_pool, min(len(cards_pool), MAP_ANCIENT_OPTION_SLOTS - len(selected_relics)))
        from ..models.state import check_and_replace_fireball
        for item in selected_cards:
            if "card" in item:
                item["card"] = check_and_replace_fireball(run, item["card"])
        options = selected_relics + selected_cards
        random.shuffle(options)
        return {"options": options, "style": style}

    def init_new_run_map(self, run: GameRun):
        run.floor_map = generate_floor_map(run, 1, save_manager=self.save_manager)
        SessionContextScoper.ensure_full_party_order(run)
        spawn_coord = xy_to_coord(0, run.floor_map.height // 2)
        SessionContextScoper.create_session(run, spawn_coord, "start_ancient", list(run.all_human_uids()))
        self._populate_start_ancient(run)

    def _populate_start_ancient(self, run: GameRun):
        from .party_coordinator import apply_and_scope, restore_player, swap_player
        caller = run.user_id
        admin_cfg = self.save_manager.load_admin_config() if hasattr(self.save_manager, "load_admin_config") else {}
        icerainboww_enabled = admin_cfg.get("icerainboww_enabled", True)
        views = {}
        ready = {}
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            player.stage = 1
            if getattr(player, "is_mercenary", False):
                views[uid] = {"node_type": "start_ancient", "data": {"options": [], "coop_done": True}}
                ready[uid] = True
                continue
            previous, previous_user = swap_player(run, player)
            views[uid] = {"node_type": "start_ancient", "data": self._build_start_ancient_data(run, icerainboww_enabled)}
            ready[uid] = player.downed
            restore_player(run, previous, previous_user)
        run.node_type = "start_ancient"
        run.node_data = {
            "coop_node_type": "start_ancient",
            "player_views": views,
            "stage_ready": ready,
            "votes": {},
        }
        apply_and_scope(run, caller)

    def return_to_grid_map(self, run: GameRun):
        fm = getattr(run, "floor_map", None)
        if fm is not None:
            sid = fm.player_session_map.get(run.user_id)
            if sid:
                SessionContextScoper.close_session(run, sid, mark_cleared=False)
                return
        run.node_type = "grid_map"
        run.enemies.clear()
        run.node_data = {}

    def complete_session(self, run: GameRun, mark_cleared: bool = True):
        from .battle.party_battle import revive_downed_players
        from .party_coordinator import attach_notices, collect_notices
        caller = run.user_id
        carried = collect_notices(run)
        revived = revive_downed_players(run)
        for uid, text in revived.items():
            carried.setdefault(uid, []).append(text)
        was_start_ancient = (run.node_type == "start_ancient")
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            player.shield = 0
            player.minions.clear()
            player.amulets.clear()
            player.abilities.clear()
            player.actions = 1
            player.bonus_actions = 1
            if was_start_ancient and player.stage < 2:
                player.stage = 2
            if not was_start_ancient and mark_cleared:
                if not getattr(player, "is_mercenary", False) and hasattr(self.save_manager, "record_stage_passed"):
                    self.save_manager.record_stage_passed(uid)
                if "espresso_relic" in player.relics:
                    player.relics.remove("espresso_relic")
                if "lucky_coin" in player.relics:
                    player.gold += MAP_LUCKY_COIN_GOLD
                if "tax_contract" in player.relics:
                    player.gold = max(0, player.gold - MAP_TAX_CONTRACT_GOLD)
        fm = getattr(run, "floor_map", None)
        if fm is not None:
            sid = fm.player_session_map.get(caller, "")
            if sid:
                SessionContextScoper.close_session(run, sid, mark_cleared=mark_cleared)
            else:
                run.node_type = "grid_map"
                run.enemies.clear()
                run.node_data = {}
        else:
            run.node_type = "grid_map"
            run.enemies.clear()
            run.node_data = {}
        attach_notices(run, carried, caller)

    def enter_next_stage(self, run: GameRun):
        if run.floor_map is not None:
            if run.node_type == "start_ancient" and run.user_id not in run.floor_map.player_session_map:
                spawn_coord = xy_to_coord(0, run.floor_map.height // 2)
                SessionContextScoper.create_session(run, spawn_coord, "start_ancient", list(run.all_human_uids()))
                self._populate_start_ancient(run)
                return
            self.complete_session(run, mark_cleared=True)
            return
        from .battle.party_battle import revive_downed_players
        from .party_coordinator import apply_and_scope, attach_notices, collect_notices
        caller = run.user_id
        carried = collect_notices(run)
        revive_downed_players(run)
        target_stage = max((run.players[u].stage for u in run.party_order if u in run.players), default=run.player.stage) + 1
        run.enemies.clear()
        run.node_data = {}
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            player.stage = target_stage
            player.shield = 0
            player.minions.clear()
            player.amulets.clear()
            player.abilities.clear()
            player.actions = 1
            player.bonus_actions = 1
            if "espresso_relic" in player.relics:
                player.relics.remove("espresso_relic")
            if "lucky_coin" in player.relics:
                player.gold += MAP_LUCKY_COIN_GOLD
            if "tax_contract" in player.relics:
                player.gold = max(0, player.gold - MAP_TAX_CONTRACT_GOLD)
        if target_stage == 1:
            self._populate_start_ancient(run)
            attach_notices(run, carried, caller)
            return
        run.node_type = "grid_map"
        attach_notices(run, carried, caller)
        apply_and_scope(run, caller)

    def advance_to_next_floor(self, run: GameRun) -> str:
        cur_floor = run.floor_map.floor_index if run.floor_map else 1
        next_floor = min(4, cur_floor + 1)
        cfg = FLOOR_CONFIGS.get(next_floor, FLOOR_CONFIGS[4])
        run.floor_map = generate_floor_map(run, next_floor, save_manager=self.save_manager)
        SessionContextScoper.ensure_full_party_order(run)
        for uid in run.all_human_uids():
            p = run.players.get(uid)
            if p is None:
                continue
            p.sp = p.max_sp
            reduce_exhaustion(p, 1)
            p.stage = int(cfg["stage_min"])
        run.node_type = "grid_map"
        run.enemies.clear()
        run.node_data = {}
        floor_name = get_locale_text(cfg["name_key"])
        return get_locale_text("i18n_grid_map.downstairs.arrived_floor", floor=next_floor, name=floor_name)

    def enter_ancient_node(self, run: GameRun):
        from .party_coordinator import apply_and_scope, attach_notices, collect_notices, restore_player, swap_player
        caller = run.user_id
        carried = collect_notices(run)
        run.enemies.clear()
        views = {}
        ready = {}
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            if getattr(player, "is_mercenary", False):
                views[uid] = {"node_type": "ancient", "data": {"options": [], "coop_done": True}}
                ready[uid] = True
                continue
            previous, previous_user = swap_player(run, player)
            self._init_ancient_node(run)
            data = {
                key: run.node_data[key]
                for key in ("options", "style")
                if key in run.node_data
            }
            data["coop_done"] = player.downed
            views[uid] = {"node_type": "ancient", "data": data}
            ready[uid] = player.downed
            restore_player(run, previous, previous_user)
        run.node_type = "ancient"
        run.node_data = {
            "coop_node_type": "ancient",
            "player_views": views,
            "stage_ready": ready,
        }
        attach_notices(run, carried, caller)
        apply_and_scope(run, caller)
        self.save_manager.save_save(caller, run)

    def move(self, run: GameRun, direction: str) -> str:
        return self.grid_map_service.move_player(run, direction)

    def teleport(self, run: GameRun, target: str) -> str:
        return self.grid_map_service.teleport_player(run, target)

    def _init_event_node(self, run: GameRun, event_id: str = ""):
        self.explore_engine._init_event_node(run, event_id=event_id)

    def _init_shop_node(self, run: GameRun):
        self.explore_engine._init_shop_node(run)

    def _init_treasure_node(self, run: GameRun):
        self.explore_engine._init_treasure_node(run)

    def choose_option(self, run: GameRun, option_idx: int, target: Optional[str] = None) -> str:
        if run.node_type == "battle":
            return get_locale_text("i18n_map_cafe.err_cannot_choose_in_battle")
        if run.node_type == "battle_prompt":
            return self.grid_map_service.handle_battle_prompt(run, option_idx)
        if run.node_type == "landmark":
            return execute_landmark_option(self.save_manager, self, run, option_idx - 1)
        if run.node_type == "downstairs":
            return execute_downstairs_option(self.save_manager, self, run, option_idx - 1)
        return self.explore_engine.choose_option(run, option_idx, target)

    def remove_card_from_deck(self, run: GameRun, deck_idx: int) -> str:
        return self.explore_engine.remove_card_from_deck(run, deck_idx)

    def upgrade_card_in_deck(self, run: GameRun, deck_idx: int) -> str:
        return self.explore_engine.upgrade_card_in_deck(run, deck_idx)

    def gem_insert_choose(self, run: GameRun, deck_idx: int) -> str:
        return self.explore_engine.gem_insert_choose(run, deck_idx)

    def gem_insert_cancel(self, run: GameRun) -> str:
        return self.explore_engine.gem_insert_cancel(run)

    def _init_ancient_node(self, run: GameRun):
        p = run.player
        run.node_type = "ancient"
        stats = self.save_manager.load_stats(run.user_id) if hasattr(self.save_manager, "load_stats") else None
        p_class = getattr(stats, "selected_class", "法师")
        admin_cfg = self.save_manager.load_admin_config() if hasattr(self.save_manager, "load_admin_config") else {}
        icerainboww_enabled = admin_cfg.get("icerainboww_enabled", True)
        if p_class == "战士":
            style = random.choice(["default", "abyss"])
        else:
            style = random.choice(["default", "abyss", "glacier"])
        if p_class == "战士":
            if style == "default":
                legends_pool = ["demon_form", "impervious"]
                relics_pool = ["ancient_eye", "gold_compass", "dragon_blood", "energy_core", "heavy_armor"]
            else:
                legends_pool = ["abyss_collapse", "demon_contract", "abyss_erosion", "abyss_altar"]
                relics_pool = ["abyss_whisper", "gold_compass", "dragon_blood", "abyss_contract"]
        else:
            if style == "default":
                legends_pool = ["doomsday_judgment", "time_warp", "magic_network", "meteor_swarm", "archmage_wish"]
                relics_pool = ["ancient_eye", "gold_compass", "dragon_blood", "energy_core", "heavy_armor"]
            elif style == "abyss":
                legends_pool = ["abyss_collapse", "demon_contract", "abyss_erosion", "abyss_altar"]
                relics_pool = ["abyss_whisper", "gold_compass", "dragon_blood", "abyss_contract"]
            else:
                legends_pool = ["frost_nova", "glacier_fortress", "glacier_tempest"]
                relics_pool = ["frost_blade", "energy_core", "heavy_armor", "glacier_core"]
        legends_pool.append("break_limits")
        legends_pool.append("unmined_gem")
        if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
            legends_pool.append("minion_icerainboww")
        available_relics = [r for r in relics_pool if r not in p.relics]
        if not available_relics:
            available_relics = relics_pool.copy()
        random.shuffle(legends_pool)
        random.shuffle(available_relics)
        options = []
        from ..models.state import check_and_replace_fireball
        for i in range(MAP_ANCIENT_OPTION_SLOTS):
            options.append({
                "type": "blessing",
                "card": check_and_replace_fireball(run, legends_pool[i % len(legends_pool)]),
                "relic": available_relics[i % len(available_relics)],
            })
        run.node_data = {"options": options, "style": style}
