from .state import GameRun
from ..data.map_config import MapConfig
from ..data.locale_data import get_locale_text


class SettlementMixin:
    def settle_game_and_delete(self, user_id: str, run: GameRun, is_victory: bool = False, create_corpse: bool = True, force: bool = False) -> str:
        if run is None:
            return self._settle_single_game(user_id, None, is_victory, create_corpse, delete_personal=True)
        other_alive = [
            uid
            for uid in run.all_human_uids()
            if uid != user_id and uid in run.players and run.players[uid].hp > 0 and not run.players[uid].downed
        ]
        if not force and not is_victory and other_alive:
            downed = run.players.get(user_id)
            if downed is not None:
                downed.downed = True
            fm = getattr(run, "floor_map", None)
            if fm is not None:
                sid = fm.player_session_map.pop(user_id, None)
                if sid and sid in fm.active_sessions:
                    sess = fm.active_sessions[sid]
                    if user_id in sess.participants:
                        sess.participants.remove(user_id)
                    human_alive_in_sess = [
                        u for u in sess.participants
                        if u in run.players and not getattr(run.players[u], "is_mercenary", False) and not getattr(run.players[u], "downed", False) and run.players[u].hp > 0
                    ]
                    if not human_alive_in_sess:
                        for u in list(sess.participants):
                            fm.player_session_map.pop(u, None)
                        fm.active_sessions.pop(sid, None)
                run.node_type = "grid_map"
                run.enemies = []
                run.node_data = {}
            self.save_save(user_id, run)
            return get_locale_text("i18n_models.manager.settle_coop_downed")
        original_player = run.player
        original_user = run.user_id
        results = []
        lines = []
        for uid in run.all_party_order():
            player = run.players.get(uid)
            if player is None or getattr(player, "is_mercenary", False):
                continue
            run.player = player
            run.user_id = uid
            result = self._settle_single_game(uid, run, is_victory, create_corpse, delete_personal=False)
            results.append(result)
            lines.append(get_locale_text("i18n_models.manager.settle_coop_line", name=player.name, result=result))
            stats = self.load_stats(uid)
            stats.active_coop_id = ""
            stats.active_lobby_id = ""
            self.save_stats(uid, stats)
        run.player = original_player
        run.user_id = original_user
        if getattr(run, "coop_id", ""):
            self.delete_coop_save(run.coop_id)
            lobbies = self.load_lobbies()
            changed = False
            for lobby_id, lobby in list(lobbies.items()):
                if lobby.get("coop_id") == run.coop_id:
                    del lobbies[lobby_id]
                    changed = True
            if changed:
                self.save_lobbies(lobbies)
        self.delete_save(user_id)
        if run.player_count() <= 1 and results:
            return results[0]
        return "\n".join(lines)
    def _settle_single_game(self, user_id: str, run: GameRun, is_victory: bool = False, create_corpse: bool = True, delete_personal: bool = True) -> str:
        if not run or not run.player:
            if delete_personal:
                self.delete_save(user_id)
            return get_locale_text("i18n_models.manager.settle_no_progress")
        stage = run.player.stage
        gold = run.player.gold
        corpse_note = ""
        if create_corpse and not is_victory:
            cause = ""
            if run.node_data:
                cause = str(run.node_data.get("death_cause", "")).strip()
            if not cause:
                cause = get_locale_text("i18n_models.manager.settle_fall_at_stage", stage=stage)
            corpse = self.corpses.create_from_run(run, cause)
            if corpse:
                corpse_note = get_locale_text("i18n_models.manager.settle_corpse_note", stage=stage)
        stats = self.load_stats(user_id)
        carryover_note = ""
        if is_victory or run.player.hp > 0:
            from ..core.inventory.bag_service import carryout_to_stats
            carried = carryout_to_stats(run.player, stats)
            if carried:
                carryover_note = get_locale_text("i18n_room_interact.bag.settle_carryover", items="、".join(carried))
        if stage < 5:
            if carryover_note:
                self.save_stats(user_id, stats)
            if delete_personal:
                self.delete_save(user_id)
            return get_locale_text("i18n_models.manager.settle_too_shallow", stage=stage, corpse_note=corpse_note, carryover_note=carryover_note)
        gp_gained = gold * 10
        victory_bonus = ""
        unlock_msg = ""
        if is_victory:
            ach_stats = getattr(stats, "achievement_stats", None)
            if isinstance(ach_stats, dict):
                ach_stats["wins"] = int(ach_stats.get("wins", 0) or 0) + 1
            if stage == MapConfig.FINAL_BOSS_STAGE:
                gp_gained += 3000
                victory_bonus = get_locale_text("i18n_models.manager.settle_bonus_final")
                unlock_msg = get_locale_text("i18n_models.manager.settle_unlock_final")

            else:
                gp_gained += 1000
                victory_bonus = get_locale_text("i18n_models.manager.settle_bonus_victory")
                if run.node_data.get("boss_name") == "Icerainboww":
                    stats.killed_icerainboww = True
                    unlock_msg = get_locale_text("i18n_models.manager.settle_unlock_icerainboww")
        stats.town_flags.pop("market_shelf", None)
        stats.gp += gp_gained
        self.save_stats(user_id, stats)
        if delete_personal:
            self.delete_save(user_id)
        return get_locale_text("i18n_models.manager.settle_result", gold=gold, gp_gained=gp_gained, victory_bonus=victory_bonus, total_gp=stats.gp, unlock_msg=unlock_msg, corpse_note=corpse_note, carryover_note=carryover_note)
