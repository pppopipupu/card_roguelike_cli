from typing import Optional

from ....data.corpse_config import CorpseConfig
from ....data.open_world_config import (
    OPEN_WORLD_COMBAT_FLAG,
    OPEN_WORLD_COORD_KEY,
    OPEN_WORLD_GHOST_ID_KEY,
    OPEN_WORLD_GHOST_OTHER_GP_REWARD,
    OPEN_WORLD_ORIGIN_KEY,
    OPEN_WORLD_SETTLED_MSG_KEY,
    OPEN_WORLD_WORLD_KEY,
    WORLD_YOG_TEMPLE,
)
from ....data.outer_plane_config import OUTER_PLANE_COMBAT_FLAG, OUTER_PLANE_ROOMS
from ....models.state import GameRun, UserStats
from ...text.events import LocaleText
from ...text.pipeline import render_text_node
from ..presence import WORLD_OUTER_PLANE, WORLD_SNOWFIELD, WORLD_TOWN
from .loadout_service import OpenWorldLoadoutService


class OpenWorldGhostService:
    @staticmethod
    def ghost_name_node(owner_name: str) -> LocaleText:
        return LocaleText(key="i18n_open_world.ghost_npc_name", params={"name": owner_name})

    @staticmethod
    def location_node(world: str, coord: str) -> LocaleText:
        if world == WORLD_TOWN:
            return LocaleText(
                key="i18n_open_world.world_town",
                params={"coord": LocaleText(key=f"rooms.{coord}.name")},
            )
        if world == WORLD_SNOWFIELD:
            return LocaleText(key="i18n_open_world.world_snowfield", params={"coord": coord})
        if world == WORLD_YOG_TEMPLE:
            return LocaleText(key="i18n_open_world.world_yog_temple", params={"coord": coord})
        if world == WORLD_OUTER_PLANE:
            room_name = LocaleText(key=f"i18n_outer_plane.room.{coord}.name") if coord in OUTER_PLANE_ROOMS else coord
            return LocaleText(key="i18n_open_world.world_outer_plane", params={"coord": room_name})
        return LocaleText(key="i18n_open_world.world_snowfield", params={"coord": coord})

    @staticmethod
    def list_at(save_manager, world: str, coord: str) -> list[dict]:
        registry = getattr(save_manager, "open_world_ghosts", None)
        if registry is None:
            return []
        return registry.list_at(world, coord)

    @staticmethod
    def display_names_at(save_manager, world: str, coord: str) -> list[str]:
        return [
            render_text_node(OpenWorldGhostService.ghost_name_node(str(g.get("owner_name", g.get("owner_uid", "")))))
            for g in OpenWorldGhostService.list_at(save_manager, world, coord)
        ]

    @staticmethod
    def resolve_at(
        save_manager,
        world: str,
        coord: str,
        query: str = "",
    ) -> tuple[Optional[dict], Optional[LocaleText]]:
        ghosts = OpenWorldGhostService.list_at(save_manager, world, coord)
        if not ghosts:
            return None, None
        clean = (query or "").strip().lower()
        if not clean:
            if len(ghosts) == 1:
                return ghosts[0], None
            names = [
                render_text_node(OpenWorldGhostService.ghost_name_node(str(g.get("owner_name", ""))))
                for g in ghosts
            ]
            return None, LocaleText(
                key="i18n_open_world.ghost_ambiguous",
                params={"names": "、".join(names), "example": names[0]},
            )
        exact = []
        partial = []
        for g in ghosts:
            owner_name = str(g.get("owner_name", ""))
            gname = render_text_node(OpenWorldGhostService.ghost_name_node(owner_name))
            candidates = (gname.lower(), owner_name.lower(), str(g.get("owner_uid", "")).lower())
            if clean in candidates:
                exact.append(g)
            elif any(clean in cand for cand in candidates):
                partial.append(g)
        matches = exact or partial
        if not matches:
            return None, LocaleText(key="i18n_open_world.ghost_not_found", params={"query": query})
        if len(matches) > 1:
            names = [
                render_text_node(OpenWorldGhostService.ghost_name_node(str(g.get("owner_name", ""))))
                for g in matches
            ]
            return None, LocaleText(
                key="i18n_open_world.ghost_ambiguous",
                params={"names": "、".join(names), "example": names[0]},
            )
        return matches[0], None

    @staticmethod
    def inspect_ghost_node(ghost: dict) -> LocaleText:
        owner_name = str(ghost.get("owner_name", ghost.get("owner_uid", "")))
        return LocaleText(
            key="i18n_open_world.ghost_talk_flavor",
            params={
                "ghost_name": OpenWorldGhostService.ghost_name_node(owner_name),
                "owner_name": owner_name,
                "cause": str(ghost.get("cause", "")),
                "cards": len(ghost.get("deck") or []),
                "relics": len(ghost.get("relics") or []),
            },
        )

    @staticmethod
    def touch_ghost_node(ghost: dict) -> LocaleText:
        owner_name = str(ghost.get("owner_name", ghost.get("owner_uid", "")))
        return LocaleText(
            key="i18n_open_world.ghost_corpse_touch",
            params={
                "ghost_name": OpenWorldGhostService.ghost_name_node(owner_name),
                "owner_name": owner_name,
                "cause": str(ghost.get("cause", "")),
                "cards": len(ghost.get("deck") or []),
                "relics": len(ghost.get("relics") or []),
            },
        )

    @staticmethod
    def try_inspect_ghost(
        save_manager,
        world: str,
        coord: str,
        query: str,
        *,
        is_touch: bool = False,
    ) -> Optional[str]:
        from ....data.locale_data import get_locale_raw
        clean = (query or "").strip()
        if not clean:
            return None
        ghost_q = clean
        if is_touch:
            aliases = [str(a).lower() for a in (get_locale_raw("i18n_open_world.corpse_aliases", []) or [])]
            if clean.lower() in aliases:
                ghost_q = ""
        ghost, ghost_err = OpenWorldGhostService.resolve_at(save_manager, world, coord, ghost_q)
        if ghost is not None:
            node = OpenWorldGhostService.touch_ghost_node(ghost) if is_touch else OpenWorldGhostService.inspect_ghost_node(ghost)
            return render_text_node(node)
        if ghost_err is not None and OpenWorldGhostService.list_at(save_manager, world, coord):
            return render_text_node(ghost_err)
        return None

    @staticmethod
    def try_attack_ghost(
        save_manager,
        battle_engine,
        user_id: str,
        stats: UserStats,
        world: str,
        coord: str,
        query: str,
        origin: str,
        active_run: Optional[GameRun] = None,
    ) -> tuple[bool, Optional[str]]:
        ghost, ghost_err = OpenWorldGhostService.resolve_at(save_manager, world, coord, query)
        if ghost is None:
            if ghost_err is not None:
                return False, render_text_node(ghost_err)
            return False, None
        ok, msg_node, run = OpenWorldGhostService.start_ghost_battle(
            save_manager,
            battle_engine,
            user_id,
            stats,
            ghost,
            world,
            coord,
            origin,
            active_run=active_run,
        )
        if not ok or run is None:
            return False, render_text_node(msg_node)
        from ....renderer import GameRenderer
        return True, render_text_node(msg_node) + "\n" + GameRenderer.render_game(run)

    @staticmethod
    def spawn_from_death(
        save_manager,
        user_id: str,
        stats: UserStats,
        world: str,
        coord: str,
        cause: str,
        snapshot: dict,
    ) -> Optional[dict]:
        registry = getattr(save_manager, "open_world_ghosts", None)
        if registry is None:
            return None
        owner_name = str(getattr(stats, "player_name", user_id) or user_id)
        max_hp = max(CorpseConfig.GHOST_MIN_HP, int(snapshot.get("max_hp", 0) or CorpseConfig.GHOST_MIN_HP))
        return registry.add(
            owner_uid=user_id,
            owner_name=owner_name,
            world=world,
            coord=coord,
            cause=cause,
            max_hp=max_hp,
            deck=list(snapshot.get("deck") or []),
            relics=list(snapshot.get("relics") or []),
            relic_counters=dict(snapshot.get("relic_counters") or {}),
            bag_items=list(snapshot.get("bag_items") or []),
        )

    @staticmethod
    def start_ghost_battle(
        save_manager,
        battle_engine,
        user_id: str,
        stats: UserStats,
        ghost: dict,
        world: str,
        coord: str,
        origin: str,
        active_run: Optional[GameRun] = None,
    ) -> tuple[bool, LocaleText, Optional[GameRun]]:
        owner_name = str(ghost.get("owner_name", ghost.get("owner_uid", "")))
        ghost_name_node = OpenWorldGhostService.ghost_name_node(owner_name)
        if str(user_id) != str(ghost.get("owner_uid", "")):
            attacked = list(ghost.get("attacked_by") or [])
            if str(user_id) in attacked:
                return False, LocaleText(
                    key="i18n_open_world.ghost_already_attacked",
                    params={"ghost_name": ghost_name_node},
                ), active_run
            registry = getattr(save_manager, "open_world_ghosts", None)
            if registry is not None:
                registry.mark_attacked(ghost["id"], user_id)

        ghost_name = render_text_node(ghost_name_node)
        ghost_max_hp = max(CorpseConfig.GHOST_MIN_HP, int(ghost.get("max_hp", CorpseConfig.GHOST_MIN_HP)))
        ghost_node_data = {
            "difficulty": "ghost",
            "ghost_name": ghost_name,
            "ghost_max_hp": ghost_max_hp,
            "ghost_deck": list(ghost.get("deck") or []),
            OPEN_WORLD_COMBAT_FLAG: True,
            OPEN_WORLD_GHOST_ID_KEY: ghost["id"],
            OPEN_WORLD_WORLD_KEY: world,
            OPEN_WORLD_COORD_KEY: coord,
            OPEN_WORLD_ORIGIN_KEY: origin,
        }
        if world == WORLD_OUTER_PLANE and origin == "outer_plane":
            ghost_node_data[OUTER_PLANE_COMBAT_FLAG] = f"ghost:{ghost['id']}"

        if active_run is not None:
            run = active_run
            floor_map = run.floor_map
            if floor_map is not None:
                from ...party.session import SessionContextScoper
                ghost_node_data["yog_quest"] = bool(floor_map.floor_flags.get("yog_quest"))
                coord_key = str(floor_map.player_coords.get(user_id, coord) or coord)
                SessionContextScoper.create_session(run, coord_key, "battle", [user_id], node_data=ghost_node_data)
            else:
                run.node_type = "battle"
                run.node_data.update(ghost_node_data)
            OpenWorldLoadoutService.apply_loadout_to_player(stats, run.player)
        else:
            p_state = OpenWorldLoadoutService.build_player_state(user_id, stats)
            run = GameRun(
                user_id=user_id,
                node_type="battle",
                player=p_state,
                node_data=ghost_node_data,
            )

        save_manager.save_stats(user_id, stats)
        battle_engine._init_battle_node(run, "ghost")
        save_manager.save_save(user_id, run)
        return True, LocaleText(
            key="i18n_open_world.ghost_start_battle",
            params={"ghost_name": ghost_name_node},
        ), run

    @staticmethod
    def handle_ghost_win(save_manager, battle_engine, run: GameRun) -> LocaleText:
        uid = run.user_id
        stats = save_manager.load_stats(uid)
        OpenWorldLoadoutService.sync_player_to_stats(stats, run.player)
        ghost_id = run.node_data.get(OPEN_WORLD_GHOST_ID_KEY)
        registry = getattr(save_manager, "open_world_ghosts", None)
        ghost = registry.get(ghost_id) if registry is not None else None
        ghost_name_str = str(run.node_data.get("ghost_name", ""))

        if registry is not None and ghost is not None and str(uid) == str(ghost.get("owner_uid", "")):
            card_cnt, relic_cnt = OpenWorldLoadoutService.reclaim_ghost_loadout(stats, ghost, player=run.player)
            registry.remove(ghost_id)
            notice = LocaleText(
                key="i18n_open_world.ghost_owner_reclaimed",
                params={
                    "ghost_name": ghost_name_str,
                    "cards": card_cnt,
                    "relics": relic_cnt,
                },
            )
        else:
            if registry is not None and ghost is not None:
                registry.mark_attacked(ghost_id, uid)
            stats.gp += OPEN_WORLD_GHOST_OTHER_GP_REWARD
            notice = LocaleText(
                key="i18n_open_world.ghost_other_reward",
                params={
                    "ghost_name": ghost_name_str,
                    "gp": OPEN_WORLD_GHOST_OTHER_GP_REWARD,
                },
            )

        save_manager.save_stats(uid, stats)
        origin = run.node_data.get(OPEN_WORLD_ORIGIN_KEY, "grid_map")
        rendered_notice = render_text_node(notice)
        floor_map = run.floor_map
        if origin == "grid_map" and floor_map is not None:
            map_engine = getattr(battle_engine, "map_engine", None)
            if map_engine is not None and hasattr(map_engine, "complete_session"):
                map_engine.complete_session(run, mark_cleared=False)
            elif map_engine is not None:
                map_engine.return_to_grid_map(run)
            else:
                run.node_type = "grid_map"
                run.node_data = {"yog_quest": True} if floor_map.floor_flags.get("yog_quest") else {}
            run.enemies.clear()
            run.node_data["notice"] = rendered_notice
            save_manager.save_save(uid, run)
        else:
            run.node_data[OPEN_WORLD_SETTLED_MSG_KEY] = rendered_notice
            save_manager.delete_save(uid)
        return notice
