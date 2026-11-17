from dataclasses import asdict
import random
import time
from typing import Optional

from ...data.pvp_config import (
    PVP_MATCH_KEY,
    PVP_ROPE_WARNING_SECONDS,
    PVP_TURN_TIMEOUT_SECONDS,
    PVP_WIN_GP_REWARD,
)
from ...data.open_world_config import (
    OPEN_WORLD_COMBAT_FLAG,
    OPEN_WORLD_COORD_KEY,
    OPEN_WORLD_ORIGIN_KEY,
    OPEN_WORLD_SETTLED_MSG_KEY,
    OPEN_WORLD_WORLD_KEY,
    WORLD_YOG_TEMPLE,
)
from ...data.world_social_config import (
    WORLD_OUTER_PLANE,
    WORLD_SNOWFIELD,
    WORLD_TOWN,
)
from ...models.events import BattleStartEvent
from ...models.state import EnemyIntentState, EnemyState, GameRun, PlayerState
from ..inventory.deck_service import DeckService
from ..text.events import LocaleText
from ..text.pipeline import render_text_node
from ..world.open_world.death_service import OpenWorldDeathService
from ..world.open_world.loadout_service import OpenWorldLoadoutService


def _t(key: str, **params) -> str:
    return render_text_node(LocaleText(key=key, params=params))


def is_pvp_run(run: Optional[GameRun]) -> bool:
    return bool(run is not None and run.node_data.get(PVP_MATCH_KEY))


def _world_origin(world: str) -> str:
    if world in (WORLD_SNOWFIELD, WORLD_YOG_TEMPLE):
        return "grid_map"
    if world == WORLD_OUTER_PLANE:
        return "outer_plane"
    return "town"


def _init_pvp_player(battle_engine, p_state: PlayerState, is_first: bool, user_id: str) -> dict:
    p_state.hand.clear()
    p_state.draw_pile = DeckService.clone_cards(p_state.deck)
    random.shuffle(p_state.draw_pile)
    p_state.discard_pile.clear()
    p_state.exhaust_pile.clear()
    p_state.minion_graveyard.clear()
    p_state.enemy_graveyard.clear()
    p_state.minions.clear()
    p_state.amulets.clear()
    p_state.buffs.clear()
    p_state.shield = 0
    p_state.actions = 2 if is_first else 0
    p_state.bonus_actions = 1 if is_first else 0
    stub = GameRun(user_id=user_id, node_type="battle", player=p_state, node_data={})
    battle_engine.card_player.draw_cards(p_state, 6, stub, ignore_focus=True)
    battle_engine.event_bus.dispatch(BattleStartEvent(stub))
    return dict(stub.node_data)


class PvpService:
    @staticmethod
    def match_invite_action(parts: list[str]) -> Optional[str]:
        if not parts:
            return None
        joined = " ".join(str(part) for part in parts).strip().lower()
        head = str(parts[0]).strip().lower()
        if head in ("接受", "accept") or joined in ("接受", "accept"):
            return "accept"
        if head in ("不接受", "拒绝", "decline", "reject") or joined in ("不接受", "拒绝", "decline", "reject"):
            return "decline"
        if joined in ("关闭pvp", "关闭 pvp", "pvp off"):
            return "disable"
        if len(parts) == 1 and head in ("1", "2", "3"):
            return {"1": "accept", "2": "decline", "3": "disable"}[head]
        return None

    @staticmethod
    def toggle_pvp(save_manager, uid: str, raw_arg: str = "") -> str:
        stats = save_manager.load_stats(uid)
        arg = str(raw_arg or "").strip().lower()
        if arg in ("status", "stat", "s", "状态"):
            return _t("i18n_pvp.toggle.status_on" if getattr(stats, "pvp_enabled", True) else "i18n_pvp.toggle.status_off")
        if arg in ("on", "enable", "1", "true", "开启", "开"):
            stats.pvp_enabled = True
        elif arg in ("off", "disable", "0", "false", "关闭", "关"):
            stats.pvp_enabled = False
        else:
            stats.pvp_enabled = not bool(getattr(stats, "pvp_enabled", True))
        save_manager.save_stats(uid, stats)
        return _t("i18n_pvp.toggle.enabled" if stats.pvp_enabled else "i18n_pvp.toggle.disabled")

    @staticmethod
    def _is_in_battle(save_manager, uid: str) -> bool:
        if save_manager.pvp.find_match_for_user(uid) is not None:
            return True
        run = save_manager.load_save(uid)
        return bool(run is not None and run.node_type == "battle")

    @staticmethod
    def send_challenge(
        save_manager,
        world_social,
        challenger_uid: str,
        target_entry: dict,
        world: str,
        coord: str,
    ) -> str:
        target_uid = str(target_entry.get("user_id", ""))
        target_stats = save_manager.load_stats(target_uid)
        target_name = str(target_entry.get("name") or getattr(target_stats, "player_name", target_uid))
        if PvpService._is_in_battle(save_manager, challenger_uid):
            return _t("i18n_pvp.invite.self_busy")
        if not bool(getattr(target_stats, "pvp_enabled", True)):
            return _t("i18n_pvp.invite.target_disabled", name=target_name)
        if PvpService._is_in_battle(save_manager, target_uid):
            return _t("i18n_pvp.invite.target_busy", name=target_name)

        challenger_stats = save_manager.load_stats(challenger_uid)
        challenger_name = str(getattr(challenger_stats, "player_name", challenger_uid))
        save_manager.pvp.set_invite(
            challenger_uid=challenger_uid,
            challenger_name=challenger_name,
            target_uid=target_uid,
            target_name=target_name,
            world=world,
            coord=coord,
            challenger_origin=_world_origin(world),
            target_origin=_world_origin(world),
        )
        world_social.push_log(
            target_uid,
            _t("i18n_pvp.invite.push_to_target", name=challenger_name),
            command="pvp_invite",
            player_name=challenger_name,
        )
        return _t("i18n_pvp.invite.sent", name=target_name)

    @staticmethod
    def render_invite_popup(save_manager, uid: str) -> str:
        pvp = getattr(save_manager, "pvp", None)
        if pvp is None:
            return ""
        invite = pvp.get_invite(uid)
        if not invite:
            return ""
        name = str(invite.get("challenger_name", invite.get("challenger_uid", "")))
        return "\n".join([
            _t("i18n_pvp.invite.popup_header", name=name),
            _t("i18n_pvp.invite.popup_opts"),
        ])

    @staticmethod
    def respond_invite(
        save_manager,
        battle_engine,
        world_social,
        target_uid: str,
        action: str,
    ) -> tuple[bool, str]:
        invite = save_manager.pvp.get_invite(target_uid)
        if not invite:
            return False, _t("i18n_pvp.invite.none_pending")
        save_manager.pvp.pop_invite(target_uid)

        challenger_uid = str(invite.get("challenger_uid", ""))
        challenger_name = str(invite.get("challenger_name", challenger_uid))
        target_stats = save_manager.load_stats(target_uid)
        target_name = str(getattr(target_stats, "player_name", target_uid))

        if action == "decline":
            world_social.push_log(
                challenger_uid,
                _t("i18n_pvp.invite.declined_notify", name=target_name),
                command="pvp_decline",
                player_name=target_name,
            )
            return True, _t("i18n_pvp.invite.declined_self", name=challenger_name)

        if action == "disable":
            target_stats.pvp_enabled = False
            save_manager.save_stats(target_uid, target_stats)
            world_social.push_log(
                challenger_uid,
                _t("i18n_pvp.invite.disabled_notify", name=target_name),
                command="pvp_disable",
                player_name=target_name,
            )
            return True, _t("i18n_pvp.invite.disabled_self")

        if PvpService._is_in_battle(save_manager, challenger_uid) or PvpService._is_in_battle(save_manager, target_uid):
            return False, _t("i18n_pvp.invite.target_busy", name=challenger_name)

        c_loc = world_social.presence.resolve_location(challenger_uid)
        t_loc = world_social.presence.resolve_location(target_uid)
        world = str(invite.get("world", WORLD_TOWN))
        coord = str(invite.get("coord", ""))
        if c_loc != (world, coord) or t_loc != (world, coord):
            return False, _t("i18n_pvp.invite.expired")

        challenger_stats = save_manager.load_stats(challenger_uid)
        p1_state = OpenWorldLoadoutService.build_player_state(challenger_uid, challenger_stats)
        p2_state = OpenWorldLoadoutService.build_player_state(target_uid, target_stats)
        p1_battle_data = _init_pvp_player(battle_engine, p1_state, True, challenger_uid)
        p2_battle_data = _init_pvp_player(battle_engine, p2_state, False, target_uid)

        match = save_manager.pvp.create_match({
            "p1_uid": challenger_uid,
            "p2_uid": target_uid,
            "p1_name": challenger_name,
            "p2_name": target_name,
            "p1_state": asdict(p1_state),
            "p2_state": asdict(p2_state),
            "p1_origin": str(invite.get("challenger_origin", _world_origin(world))),
            "p2_origin": str(invite.get("target_origin", _world_origin(world))),
            "world": world,
            "coord": coord,
            "current_turn_uid": challenger_uid,
            "turn_count": 1,
            "turn_started_at": time.time(),
            "status": "active",
        })

        PvpService._attach_run_for_player(
            save_manager, challenger_uid, match, p1_state, p2_state, world, coord, p1_battle_data
        )
        PvpService._attach_run_for_player(
            save_manager, target_uid, match, p2_state, p1_state, world, coord, p2_battle_data
        )

        world_social.push_log(
            challenger_uid,
            _t("i18n_pvp.invite.accepted_notify", name=target_name),
            command="pvp_start",
            player_name=target_name,
        )
        from ...renderer import GameRenderer
        target_run = save_manager.load_save(target_uid)
        rendered = GameRenderer.render_game(target_run) if target_run is not None else ""
        return True, (_t("i18n_pvp.invite.accepted_self", name=challenger_name) + ("\n" + rendered if rendered else ""))

    @staticmethod
    def _attach_run_for_player(
        save_manager,
        uid: str,
        match: dict,
        own_state: PlayerState,
        opp_state: PlayerState,
        world: str,
        coord: str,
        battle_data: Optional[dict] = None,
    ) -> None:
        origin = str(match.get("p1_origin" if uid == match["p1_uid"] else "p2_origin", _world_origin(world)))
        node_data = dict(battle_data or {})
        node_data.update({
            PVP_MATCH_KEY: match["id"],
            OPEN_WORLD_COMBAT_FLAG: True,
            OPEN_WORLD_WORLD_KEY: world,
            OPEN_WORLD_COORD_KEY: coord,
            OPEN_WORLD_ORIGIN_KEY: origin,
            "turn_count": int(match.get("turn_count", 1)),
        })
        existing = save_manager.load_save(uid)
        if existing is not None and getattr(existing, "floor_map", None) is not None and origin == "grid_map":
            from ..party.session import SessionContextScoper
            node_data["yog_quest"] = bool(existing.floor_map.floor_flags.get("yog_quest"))
            coord_key = str(existing.floor_map.player_coords.get(uid, coord) or coord)
            SessionContextScoper.create_session(existing, coord_key, "battle", [uid], node_data=node_data)
            existing.player = own_state
            existing.players[uid] = own_state
            existing.player2 = opp_state
            PvpService.sync_enemies_from_opponent(existing)
            save_manager.save_save(uid, existing)
            return

        run = GameRun(
            user_id=uid,
            node_type="battle",
            player=own_state,
            player2=opp_state,
            node_data=node_data,
        )
        PvpService.sync_enemies_from_opponent(run)
        save_manager.save_save(uid, run)

    @staticmethod
    def sync_enemies_from_opponent(run: GameRun) -> None:
        opp = getattr(run, "player2", None)
        if opp is None:
            return
        enemies: list[EnemyState] = [
            EnemyState(
                name=opp.name,
                hp=int(opp.hp),
                max_hp=int(opp.max_hp),
                shield=int(opp.shield),
                actions=int(opp.actions),
                bonus_actions=int(opp.bonus_actions),
                buffs=list(getattr(opp, "buffs", []) or []),
                max_actions=2,
                max_bonus_actions=1,
                intents=[
                    EnemyIntentState(
                        type="buff",
                        val=0,
                        desc=_t("i18n_pvp.battle.opp_intent"),
                        cost_a=0,
                        cost_ba=0,
                    )
                ],
            )
        ]
        for key in sorted((getattr(opp, "minions", {}) or {}).keys()):
            m = opp.minions[key]
            enemies.append(
                EnemyState(
                    name=m.name,
                    hp=int(m.hp),
                    max_hp=int(m.max_hp),
                    shield=0,
                    actions=int(m.actions),
                    bonus_actions=int(m.bonus_actions),
                    buffs=list(getattr(m, "buffs", []) or []),
                    is_summon=True,
                    size=getattr(m, "size", ""),
                )
            )
        run.enemies = enemies

    @staticmethod
    def sync_opponent_from_enemies(run: GameRun) -> None:
        opp = getattr(run, "player2", None)
        if opp is None:
            return
        if not run.enemies:
            opp.hp = 0
            return
        main = run.enemies[0]
        opp.hp = max(0, int(main.hp))
        opp.shield = max(0, int(main.shield))
        opp.buffs = list(getattr(main, "buffs", []) or [])
        minion_keys = sorted((getattr(opp, "minions", {}) or {}).keys())
        for idx, key in enumerate(minion_keys, start=1):
            if idx >= len(run.enemies):
                break
            e = run.enemies[idx]
            m = opp.minions[key]
            if e.hp <= 0:
                opp.minions.pop(key, None)
                opp.minion_graveyard.append(m.id)
            else:
                m.hp = int(e.hp)
                m.buffs = list(getattr(e, "buffs", []) or [])

    @staticmethod
    def bind_run_from_match(save_manager, run: GameRun, uid: str) -> None:
        match_id = str(run.node_data.get(PVP_MATCH_KEY) or "")
        match = save_manager.pvp.get_match(match_id)
        if not match:
            return
        is_p1 = str(uid) == str(match.get("p1_uid", ""))
        own_dict = match["p1_state"] if is_p1 else match["p2_state"]
        opp_dict = match["p2_state"] if is_p1 else match["p1_state"]
        own_state = save_manager._parse_player_state(own_dict)
        opp_state = save_manager._parse_player_state(opp_dict)
        if own_state is not None:
            run.player = own_state
            if uid in run.players:
                run.players[uid] = own_state
        run.player2 = opp_state
        run.node_data["turn_count"] = int(match.get("turn_count", 1))
        run.node_data["pvp_turn_uid"] = str(match.get("current_turn_uid", ""))
        run.node_data["pvp_turn_started_at"] = float(match.get("turn_started_at", time.time()))
        run.node_data["pvp_opp_name"] = str(match["p2_name"] if is_p1 else match["p1_name"])
        PvpService.sync_enemies_from_opponent(run)

    @staticmethod
    def sync_match_from_run(save_manager, run: GameRun, uid: str) -> None:
        match_id = str(run.node_data.get(PVP_MATCH_KEY) or "")
        match = save_manager.pvp.get_match(match_id)
        if not match:
            return
        is_p1 = str(uid) == str(match.get("p1_uid", ""))
        if run.player is not None:
            match["p1_state" if is_p1 else "p2_state"] = asdict(run.player)
        if run.player2 is not None:
            match["p2_state" if is_p1 else "p1_state"] = asdict(run.player2)
        save_manager.pvp.save_match(match)

    @staticmethod
    def remaining_rope_seconds(match: dict, now: Optional[float] = None) -> int:
        ts = time.time() if now is None else float(now)
        started = float(match.get("turn_started_at", ts))
        return max(0, int(PVP_TURN_TIMEOUT_SECONDS - (ts - started)))

    @staticmethod
    def format_rope_status(save_manager, run: GameRun, uid: str, now: Optional[float] = None) -> list[str]:
        match = save_manager.pvp.get_match(run.node_data.get(PVP_MATCH_KEY))
        if not match:
            return []
        active_uid = str(match.get("current_turn_uid", ""))
        turn = int(match.get("turn_count", 1))
        rem = PvpService.remaining_rope_seconds(match, now=now)
        if active_uid == str(uid):
            turn_line = _t("i18n_pvp.battle.turn_yours", turn=turn)
            rope_key = "i18n_pvp.battle.rope_warning" if rem <= PVP_ROPE_WARNING_SECONDS else "i18n_pvp.battle.rope_normal"
        else:
            opp_name = str(match["p2_name"] if str(uid) == str(match["p1_uid"]) else match["p1_name"])
            turn_line = _t("i18n_pvp.battle.turn_waiting", opp=opp_name, turn=turn)
            rope_key = "i18n_pvp.battle.rope_opp_warning" if rem <= PVP_ROPE_WARNING_SECONDS else "i18n_pvp.battle.rope_opp_normal"
        return [turn_line, _t(rope_key, seconds=rem)]

    @staticmethod
    def check_turn_owner(save_manager, uid: str, run: GameRun) -> tuple[bool, str]:
        match = save_manager.pvp.get_match(run.node_data.get(PVP_MATCH_KEY))
        if not match:
            return True, ""
        active_uid = str(match.get("current_turn_uid", ""))
        if active_uid == str(uid):
            return True, ""
        opp_name = str(match["p2_name"] if str(uid) == str(match["p1_uid"]) else match["p1_name"])
        rem = PvpService.remaining_rope_seconds(match)
        return False, _t("i18n_pvp.battle.wait_action_blocked", opp=opp_name, seconds=rem)

    @staticmethod
    def check_and_advance_rope(
        save_manager,
        battle_engine,
        town_engine,
        world_social,
        uid: str,
        now: Optional[float] = None,
    ) -> str:
        pvp = getattr(save_manager, "pvp", None)
        if pvp is None:
            return ""
        match = pvp.find_match_for_user(uid)
        if not match:
            return ""
        ts = time.time() if now is None else float(now)
        if ts < float(match.get("turn_started_at", ts)) + PVP_TURN_TIMEOUT_SECONDS:
            return ""
        active_uid = str(match.get("current_turn_uid", ""))
        active_name = str(match["p1_name"] if active_uid == str(match["p1_uid"]) else match["p2_name"])
        active_run = save_manager.load_save(active_uid)
        if active_run is not None:
            PvpService.advance_pvp_turn(
                save_manager,
                battle_engine,
                town_engine,
                world_social,
                active_run,
                active_uid,
                now=ts,
            )
        return _t("i18n_pvp.battle.rope_auto_end", name=active_name)

    @staticmethod
    def consume_extra_turn(
        save_manager,
        battle_engine,
        run: GameRun,
        uid: str,
        *,
        run_end_phase: bool,
        now: Optional[float] = None,
    ) -> str:
        match_id = str(run.node_data.get(PVP_MATCH_KEY) or "")
        if run_end_phase:
            battle_engine.card_player._end_player_phase_events(run, run.player)
            PvpService.sync_opponent_from_enemies(run)
        remaining = max(0, int(run.node_data.get("extra_turns_left", 0) or 0) - 1)
        run.node_data["extra_turns_left"] = remaining
        battle_engine.card_player._begin_player_phase_events(run, run.player, advance_global=False)
        PvpService.sync_enemies_from_opponent(run)
        save_manager.save_save(uid, run)
        match = save_manager.pvp.get_match(match_id)
        if match is not None:
            match["turn_started_at"] = time.time() if now is None else float(now)
            save_manager.pvp.save_match(match)
        return _t("i18n_battle_core.time_stop_extra_turn", count=remaining)

    @staticmethod
    def advance_pvp_turn(
        save_manager,
        battle_engine,
        town_engine,
        world_social,
        run: GameRun,
        uid: str,
        *,
        now: Optional[float] = None,
    ) -> str:
        match_id = str(run.node_data.get(PVP_MATCH_KEY) or "")
        match = save_manager.pvp.get_match(match_id)
        if not match:
            return ""
        p1_uid = str(match["p1_uid"])
        p2_uid = str(match["p2_uid"])
        opp_uid = p2_uid if str(uid) == p1_uid else p1_uid
        opp_name = str(match["p2_name"] if str(uid) == p1_uid else match["p1_name"])
        my_name = str(match["p1_name"] if str(uid) == p1_uid else match["p2_name"])

        PvpService.sync_enemies_from_opponent(run)
        battle_engine.card_player._end_player_phase_events(run, run.player)
        PvpService.sync_opponent_from_enemies(run)
        save_manager.save_save(uid, run)

        if run.player.hp <= 0:
            _, lose_msg = PvpService.settle_pvp_match(
                save_manager, town_engine, world_social, match_id, opp_uid, str(uid), actor_uid=str(uid)
            )
            return lose_msg
        if run.player2 is not None and run.player2.hp <= 0:
            win_msg, _ = PvpService.settle_pvp_match(
                save_manager, town_engine, world_social, match_id, str(uid), opp_uid, actor_uid=str(uid)
            )
            return win_msg

        match = save_manager.pvp.get_match(match_id) or match
        if int(run.node_data.get("extra_turns_left", 0) or 0) > 0:
            return PvpService.consume_extra_turn(
                save_manager,
                battle_engine,
                run,
                uid,
                run_end_phase=False,
                now=now,
            )
        match["current_turn_uid"] = opp_uid
        if opp_uid == p1_uid:
            match["turn_count"] = int(match.get("turn_count", 1)) + 1
        match["turn_started_at"] = time.time() if now is None else float(now)
        save_manager.pvp.save_match(match)

        opp_run = save_manager.load_save(opp_uid)
        if opp_run is not None:
            opp_run.node_data["turn_count"] = int(match["turn_count"])
            battle_engine.card_player._begin_player_phase_events(opp_run, opp_run.player, advance_global=False)
            PvpService.sync_opponent_from_enemies(opp_run)
            save_manager.save_save(opp_uid, opp_run)
            if opp_run.player.hp <= 0:
                win_msg, _ = PvpService.settle_pvp_match(
                    save_manager, town_engine, world_social, match_id, str(uid), opp_uid, actor_uid=str(uid)
                )
                return win_msg

        world_social.push_log(
            opp_uid,
            _t("i18n_pvp.battle.your_turn_notify", opp=my_name, turn=int(match["turn_count"])),
            command="pvp_turn",
            player_name=my_name,
        )
        return _t("i18n_pvp.battle.turn_ended_wait", turn=int(match["turn_count"]), opp=opp_name)

    @staticmethod
    def settle_pvp_match(
        save_manager,
        town_engine,
        world_social,
        match_id: str,
        winner_uid: str,
        loser_uid: str,
        reason: str = "defeat",
        actor_uid: str = "",
    ) -> tuple[str, str]:
        match = save_manager.pvp.remove_match(match_id) or {}
        p1_uid = str(match.get("p1_uid", winner_uid))
        is_w_p1 = str(winner_uid) == p1_uid
        winner_name = str(match.get("p1_name" if is_w_p1 else "p2_name", winner_uid))
        loser_name = str(match.get("p2_name" if is_w_p1 else "p1_name", loser_uid))
        world = str(match.get("world", WORLD_TOWN))
        coord = str(match.get("coord", "square"))

        winner_run = save_manager.load_save(winner_uid)
        winner_stats = save_manager.load_stats(winner_uid)
        if winner_run is not None and winner_run.player is not None:
            OpenWorldLoadoutService.sync_player_to_stats(winner_stats, winner_run.player)
        winner_stats.gp += PVP_WIN_GP_REWARD
        save_manager.save_stats(winner_uid, winner_stats)

        if reason == "abandon":
            win_msg = _t("i18n_pvp.battle.opp_forfeit_notify", loser=loser_name, gp=PVP_WIN_GP_REWARD)
        elif reason == "escape":
            win_msg = _t("i18n_pvp.battle.opp_escape_notify", loser=loser_name, gp=PVP_WIN_GP_REWARD)
        else:
            win_msg = _t("i18n_pvp.battle.win_banner", loser=loser_name, gp=PVP_WIN_GP_REWARD)

        if winner_run is not None and getattr(winner_run, "floor_map", None) is not None:
            map_engine = getattr(getattr(town_engine, "engine", None), "map_engine", None)
            if map_engine is not None and hasattr(map_engine, "complete_session"):
                map_engine.complete_session(winner_run, mark_cleared=False)
            else:
                winner_run.node_type = "grid_map"
                winner_run.enemies.clear()
                winner_run.node_data = {}
                if winner_run.floor_map.floor_flags.get("yog_quest"):
                    winner_run.node_data["yog_quest"] = True
            winner_run.player2 = None
            winner_run.node_data["notice"] = win_msg
            save_manager.save_save(winner_uid, winner_run)
        else:
            save_manager.delete_save(winner_uid)

        loser_run = save_manager.load_save(loser_uid)
        loser_stats = save_manager.load_stats(loser_uid)
        loser_player = loser_run.player if loser_run is not None else None
        if reason == "escape":
            if loser_player is not None:
                OpenWorldLoadoutService.sync_player_to_stats(loser_stats, loser_player)
            OpenWorldDeathService._clear_outer_plane_flags(loser_stats)
            OpenWorldDeathService._clear_transient_dialog_flags(loser_stats)
            loser_stats.in_town = True
            loser_stats.town_pos = "square"
            save_manager.save_stats(loser_uid, loser_stats)
            save_manager.delete_save(loser_uid)
            lose_msg = _t("i18n_pvp.battle.escape_banner", winner=winner_name)
        else:
            ghost_coord = str(getattr(loser_stats, "town_pos", "square") or "square") if world == WORLD_TOWN else coord
            OpenWorldDeathService.handle_state_death(
                save_manager,
                town_engine,
                loser_uid,
                loser_stats,
                world,
                ghost_coord,
                player=loser_player,
                is_abandon=(reason == "abandon"),
            )
            save_manager.delete_save(loser_uid)
            lose_msg = _t("i18n_pvp.battle.lose_banner", winner=winner_name)

        if str(actor_uid) != str(winner_uid):
            world_social.push_log(winner_uid, win_msg, command="pvp_win", player_name=loser_name)
        if str(actor_uid) != str(loser_uid):
            world_social.push_log(loser_uid, lose_msg, command="pvp_lose", player_name=winner_name)
        return win_msg, lose_msg
