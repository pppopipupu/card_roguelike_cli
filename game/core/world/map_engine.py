import random
from typing import Optional, TYPE_CHECKING
from ...models.state import GameRun
from ...data.progression.balance_config import (
    MAP_ANCIENT_OPTION_SLOTS,
    MAP_ANCIENT_RELIC_CHOICES,
    MAP_LUCKY_COIN_GOLD,
    MAP_TAX_CONTRACT_GOLD,
)
from ...data.world.grid_map_config import FLOOR_CONFIGS
from ...data.text.locale_data import get_locale_text
from .explore_engine import ExploreEngine
from .grid_map_generator import generate_floor_map, xy_to_coord
from .grid_map_service import GridMapService
from .landmark_system import execute_downstairs_option, execute_landmark_option
from ..party.session import SessionContextScoper
from .sp_system import reduce_exhaustion

if TYPE_CHECKING:
    from ...engine import GameEngine


class MapEngine:
    game_engine: "GameEngine"
    def __init__(self, save_manager, battle_engine):
        self.save_manager = save_manager
        self.battle_engine = battle_engine
        self.explore_engine = ExploreEngine(save_manager, self)
        self.grid_map_service = GridMapService(save_manager, self)

    def _build_start_ancient_data(self, run: GameRun, icerainboww_enabled: bool) -> dict:
        from .ancient_reward import build_start_ancient_options
        return build_start_ancient_options(run, self.save_manager, icerainboww_enabled)

    def init_new_run_map(self, run: GameRun):
        run.floor_map = generate_floor_map(run, 1, save_manager=self.save_manager)
        stats = self.save_manager.load_stats(run.user_id) if self.save_manager is not None else None
        from .map_quest_service import init_run_quests, populate_floor_quests
        init_run_quests(run, stats)
        populate_floor_quests(run, run.floor_map, stats)
        SessionContextScoper.ensure_full_party_order(run)
        spawn_coord = xy_to_coord(0, run.floor_map.height // 2)
        SessionContextScoper.create_session(run, spawn_coord, "start_ancient", list(run.all_human_uids()))
        self._populate_start_ancient(run)

    def _populate_start_ancient(self, run: GameRun):
        from ..party.coordinator import apply_and_scope, restore_player, swap_player
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
        from ..party.mercenary import cleanup_temporary_mercenaries
        cleanup_temporary_mercenaries(run)
        fm = getattr(run, "floor_map", None)
        if fm is not None:
            sid = fm.player_session_map.get(run.user_id)
            if sid:
                SessionContextScoper.close_session(run, sid, mark_cleared=False)
                return
        run.node_type = "grid_map"
        run.enemies.clear()
        run.node_data = {}

    def _settle_player_node(self, run: GameRun, uid: str, was_start_ancient: bool, mark_cleared: bool) -> str:
        player = run.players.get(uid)
        if player is None:
            return ""
        notice = ""
        if player.downed or player.hp <= 0:
            player.downed = False
            player.hp = 1
            player.shield = 0
            notice = get_locale_text("i18n_explore_core.revive_log", player_name=player.name)
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
        return notice

    def complete_session(self, run: GameRun, mark_cleared: bool = True):
        from ..party.coordinator import attach_notices, collect_notices
        caller = run.user_id
        carried = collect_notices(run)
        was_start_ancient = (run.node_type == "start_ancient")
        fm = getattr(run, "floor_map", None)
        sid = fm.player_session_map.get(caller, "") if fm is not None else ""
        active = None
        if fm is not None and sid:
            active = {uid for uid, mapped in fm.player_session_map.items() if mapped == sid}
        for uid in run.party_order:
            if active is not None and uid not in active:
                continue
            notice = self._settle_player_node(run, uid, was_start_ancient, mark_cleared)
            if notice:
                carried.setdefault(uid, []).append(notice)
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

    def leave_node_for_free_roam(self, run: GameRun, uid: str) -> dict[str, str]:
        from ..party.session import SessionContextScoper
        fm = getattr(run, "floor_map", None)
        was_start_ancient = run.node_type == "start_ancient"
        sid = fm.player_session_map.get(uid, "") if fm is not None else ""
        session = None
        if fm is not None and sid:
            session = fm.active_sessions.get(sid)
        leaves = [uid]
        for member_uid, member in run.players.items():
            if member_uid != uid and getattr(member, "mercenary_owner", "") == uid:
                leaves.append(member_uid)
        node_data = run.node_data if isinstance(run.node_data, dict) else {}
        views = node_data.get("player_views")
        if session is not None:
            for member_uid in list(session.participants):
                member = run.players.get(member_uid)
                if member is None or member_uid in leaves:
                    continue
                if getattr(member, "is_mercenary", False):
                    continue
                if member.downed or member.hp <= 0:
                    view = views.get(member_uid) if isinstance(views, dict) else None
                    data = view.get("data") if isinstance(view, dict) else None
                    if not isinstance(data, dict) or data.get("coop_done", True):
                        leaves.append(member_uid)
        revived = {}
        for member_uid in leaves:
            notice = self._settle_player_node(run, member_uid, was_start_ancient, True)
            if notice:
                revived[member_uid] = notice
        ready = node_data.get("stage_ready")
        for member_uid in leaves:
            if isinstance(ready, dict):
                ready[member_uid] = True
            view = views.get(member_uid) if isinstance(views, dict) else None
            if isinstance(view, dict):
                view.setdefault("data", {})["coop_done"] = True
        if fm is not None and session is not None:
            SessionContextScoper.leave_session(run, leaves, mark_cleared=True)
        else:
            run.party_order = list(SessionContextScoper.ensure_full_party_order(run))
            run.node_type = "grid_map"
            run.enemies = []
            run.node_data = {}
        return revived

    def enter_next_stage(self, run: GameRun):
        if run.floor_map is not None:
            if run.node_type == "start_ancient" and run.user_id not in run.floor_map.player_session_map:
                spawn_coord = xy_to_coord(0, run.floor_map.height // 2)
                SessionContextScoper.create_session(run, spawn_coord, "start_ancient", list(run.all_human_uids()))
                self._populate_start_ancient(run)
                return
            self.complete_session(run, mark_cleared=True)
            return
        from ..battle.party_battle import revive_downed_players
        from ..party.coordinator import apply_and_scope, attach_notices, collect_notices
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

    def _finalize_next_floor(self, run: GameRun, actor_uid: str, cfg: dict, *, yog_quest: bool = False) -> str:
        from .presence import sync_active
        from .world_social import WorldSocialService
        from ...data.world.grid_map_config import get_display_floor
        from ...renderer.world_grid import format_floor_number
        from ...data.world.yog_quest_config import YOG_QUEST_ZONE_KEY

        next_floor = run.floor_map.floor_index if run.floor_map is not None else 1
        display_floor = format_floor_number(get_display_floor(next_floor))
        SessionContextScoper.ensure_full_party_order(run)
        humans = run.all_human_uids()
        for uid in humans:
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
        social = WorldSocialService(self.save_manager) if len(humans) > 1 else None
        actor = run.players.get(actor_uid)
        actor_name = actor.name if actor is not None else actor_uid
        notice = (
            get_locale_text("i18n_grid_map.downstairs.all_descended_notice", actor=actor_name, floor=display_floor, name=floor_name)
            if social is not None
            else ""
        )
        for uid in humans:
            stats = self.save_manager.load_stats(uid)
            if yog_quest:
                stats.town_flags[YOG_QUEST_ZONE_KEY] = 1
                self.save_manager.save_stats(uid, stats)
            sync_active(uid, stats=stats, run=run)
            if social is not None and uid != actor_uid:
                social.push_log(
                    uid,
                    notice,
                    command="downstairs",
                    player_name=actor_name,
                    coop_id=str(getattr(run, "coop_id", "") or ""),
                )
        self.open_floor_arrival_ancient(run)
        msg_key = "i18n_yog_quest.gate.arrived" if yog_quest else "i18n_grid_map.downstairs.arrived_floor"
        return get_locale_text(msg_key, floor=display_floor, name=floor_name)

    def open_floor_arrival_ancient(self, run: GameRun) -> None:
        fm = getattr(run, "floor_map", None)
        humans = list(run.all_human_uids())
        if fm is not None and humans:
            spawn_coord = fm.player_coords.get(run.user_id) or next(iter(fm.player_coords.values()), "A1")
            SessionContextScoper.create_session(run, spawn_coord, "ancient", humans)
        self.enter_ancient_node(run)

    def advance_to_next_floor(self, run: GameRun) -> str:
        actor_uid = run.user_id
        cur_floor = run.floor_map.floor_index if run.floor_map else 1
        if run.floor_map is not None and run.floor_map.floor_flags.get("yog_quest"):
            from .yog_quest.floor import generate_yog_quest_floor
            from ...data.world.yog_quest_config import YOG_FLOOR_TEMPLE
            if cur_floor >= YOG_FLOOR_TEMPLE:
                return get_locale_text("i18n_yog_quest.gate.no_further")
            next_floor = YOG_FLOOR_TEMPLE
            cfg = FLOOR_CONFIGS[next_floor]
            run.floor_map = generate_yog_quest_floor(run, next_floor)
            return self._finalize_next_floor(run, actor_uid, cfg, yog_quest=True)
        next_floor = min(4, int(cur_floor) + 1)
        cfg = FLOOR_CONFIGS.get(next_floor, FLOOR_CONFIGS[4])
        run.floor_map = generate_floor_map(run, next_floor, save_manager=self.save_manager)
        stats = self.save_manager.load_stats(actor_uid) if self.save_manager is not None else None
        from .map_quest_service import populate_floor_quests
        populate_floor_quests(run, run.floor_map, stats)
        return self._finalize_next_floor(run, actor_uid, cfg, yog_quest=False)

    def enter_ancient_node(self, run: GameRun):
        from ..party.coordinator import apply_and_scope, attach_notices, collect_notices, restore_player, swap_player
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
                for key in ("options", "style", "deity")
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

    def dig(self, run: GameRun, direction: str) -> str:
        return self.grid_map_service.move_player(run, direction, dig=True)

    def teleport(self, run: GameRun, target: str) -> str:
        return self.grid_map_service.teleport_player(run, target)

    def _init_event_node(self, run: GameRun, event_id: str = ""):
        self.explore_engine._init_event_node(run, event_id=event_id)

    def _init_shop_node(self, run: GameRun):
        self.explore_engine._init_shop_node(run)

    def _init_treasure_node(self, run: GameRun):
        self.explore_engine._init_treasure_node(run)

    def choose_option(self, run: GameRun, option_idx: int, target: Optional[str] = None) -> str | None:
        if run.node_type == "battle":
            return get_locale_text("i18n_map_cafe.err_cannot_choose_in_battle")
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

    def enchant_choose(self, run: GameRun, option_idx: int) -> str:
        return self.explore_engine.enchant_choose(run, option_idx)

    def enchant_cancel(self, run: GameRun) -> str:
        return self.explore_engine.enchant_cancel(run)

    def _init_ancient_node(self, run: GameRun):
        from .ancient_reward import build_ancient_options
        run.node_type = "ancient"
        run.node_data = build_ancient_options(run, self.save_manager)
