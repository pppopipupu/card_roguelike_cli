import copy
import random
import uuid
from math import ceil

from ..models import coop_view
from ..models.coop_view import SHARED_PERSIST_KEYS, VIEW_KEYS, VIEW_NODES
from ..models.state import CardState, EnemyState, GameRun, PlayerState
from ..data.balance_config import (
    COOP_HP_MULTIPLIER_DEFAULT,
    COOP_HP_MULTIPLIERS,
    COOP_VOTE_RATIO,
    MAP_LUCKY_COIN_GOLD,
    MAP_TAX_CONTRACT_GOLD,
)
from ..data.reward_config import BOSS_MYTHIC_CARDS, BOSS_MYTHIC_RELICS
from ..data.locale_data import get_locale_text
from .deck_service import DeckService
from .reward_builder import base_enemy_name, build_reward_items


AOE_INTENT_TYPES = {
    "attack_all",
    "aoe_attack",
    "all_attack",
    "aoe_damage",
    "hellfire",
    "electrodynamics",
    "soul_daggers",
    "focus_bloom",
    "sunken_tsunami",
    "mist_condense_1",
    "tail_sweep",
    "inferno_breath",
}


def coop_for_map_engine(save_manager, map_engine):
    battle_engine = map_engine.battle_engine
    root = getattr(battle_engine, "game_engine", None) or battle_engine
    return CoopEngine(save_manager, root)


class CoopEngine:
    def __init__(self, save_manager, engine=None):
        self.save_manager = save_manager
        root = getattr(engine, "game_engine", None) or engine
        self.map_engine = getattr(root, "map_engine", None)
        self.battle_engine = getattr(root, "battle_engine", None) or getattr(engine, "battle_engine", None) or engine
        self.engine = root

    def _require_map_engine(self):
        if self.map_engine is None:
            raise RuntimeError("CoopEngine requires a GameEngine with map_engine")
        return self.map_engine

    def _party(self, run):
        return [run.players[uid] for uid in run.party_order if uid in run.players]

    def _alive_uids(self, run):
        return [
            uid
            for uid in run.party_order
            if uid in run.players and run.players[uid].hp > 0 and not run.players[uid].downed
        ]

    def _swap(self, run, player):
        previous = run.player
        previous_user = run.user_id
        run.player = player
        uid = run.uid_for(player)
        if uid:
            run.user_id = uid
        return previous, previous_user

    def _restore(self, run, previous, previous_user):
        run.player = previous
        run.user_id = previous_user

    def apply_view(self, run, uid):
        coop_view.apply_view(run, uid)
        return coop_view.scope_view(run, uid)

    def persist_view(self, run, uid):
        coop_view.persist_view(run, uid)

    def _notice(self, run, uid, text):
        per = run.node_data.setdefault("coop_notices_by_uid", {})
        bucket = per.setdefault(uid, [])
        bucket.append(text)
        if uid == run.user_id:
            run.node_data["coop_notices"] = bucket

    def _team_notice(self, run, text):
        for uid in run.party_order:
            if uid in run.players:
                self._notice(run, uid, text)

    def _attach_notices(self, run, notices_by_uid, uid):
        if not notices_by_uid:
            return
        run.node_data["coop_notices_by_uid"] = notices_by_uid
        own = notices_by_uid.get(uid, [])
        if own:
            run.node_data["coop_notices"] = list(own)
        else:
            run.node_data.pop("coop_notices", None)

    def _collect_notices(self, run):
        carried = {}
        per = run.node_data.get("coop_notices_by_uid")
        if isinstance(per, dict):
            for uid, items in per.items():
                if isinstance(items, list) and items:
                    carried[uid] = list(items)
        return carried

    def list_enemy_hp_multiplier(self, count):
        if count <= 2:
            return COOP_HP_MULTIPLIERS[2]
        return COOP_HP_MULTIPLIERS.get(count, COOP_HP_MULTIPLIER_DEFAULT)

    def scale_coop_enemies(self, run):
        count = len(run.party_order)
        originals = list(run.enemies)
        if count < 2 or not originals:
            return
        from ..data.enemy_data import ENEMY_CONFIG
        multiplier = self.list_enemy_hp_multiplier(count)
        expanded = []
        sequence = 0
        for enemy in originals:
            base_name = base_enemy_name(enemy.name)
            if ENEMY_CONFIG.get(base_name, {}).get("type") == "boss":
                clone = copy.deepcopy(enemy)
                clone.name = base_name
                expanded.append(clone)
                continue
            for _ in range(2):
                clone = copy.deepcopy(enemy)
                clone.name = f"{base_name} {chr(65 + sequence)}" if sequence < 26 else f"{base_name} {sequence + 1}"
                expanded.append(clone)
                sequence += 1
        for enemy in expanded:
            enemy.max_hp = max(1, ceil(enemy.max_hp * multiplier))
            enemy.hp = max(1, ceil(enemy.hp * multiplier))
            enemy.shield = max(0, ceil(enemy.shield * multiplier))
            for buff in enemy.buffs:
                if buff.id in ("unyielding", "strength"):
                    buff.stacks = max(1, ceil(buff.stacks * multiplier))
        run.enemies = expanded
        run.node_data["coop_hp_mult"] = multiplier

    def assign_enemy_targets(self, run):
        alive = self._alive_uids(run)
        targets = {}
        cursor = int(run.node_data.get("coop_aggro_cursor", 0))
        for index, enemy in enumerate(run.enemies, 1):
            if enemy.hp <= 0:
                continue
            intents = list(getattr(enemy, "intents", []) or [])
            is_aoe = any(intent.type in AOE_INTENT_TYPES for intent in intents)
            if is_aoe:
                targets[str(index)] = "ALL"
                continue
            if not alive:
                targets[str(index)] = ""
                continue
            taunt_uids = [
                uid
                for uid in alive
                if any(buff.id == "coop_aegis" for buff in run.players[uid].buffs)
            ]
            pool = taunt_uids or alive
            chosen = pool[cursor % len(pool)]
            cursor += 1
            targets[str(index)] = chosen
        run.node_data["enemy_targets"] = targets
        run.node_data["coop_aggro_cursor"] = cursor

    def mark_downed(self, run, player):
        if not run or not getattr(run, "coop_id", ""):
            return
        uid = run.uid_for(player)
        if not uid or player.downed:
            return
        player.downed = True
        player.hp = 0
        player.shield = 0
        player.hand.clear()
        player.minions.clear()
        player.amulets.clear()
        player.abilities.clear()
        ready = run.node_data.setdefault("turn_ready", {})
        ready[uid] = True
        self.battle_engine._log_event(run, get_locale_text("i18n_explore_core.downed_log", player_name=player.name))
        if not self._alive_uids(run):
            run.node_data["coop_wipe"] = True

    def _revive_downed(self, run):
        revived = {}
        for player in self._party(run):
            if player.downed or player.hp <= 0:
                player.downed = False
                player.hp = 1
                player.shield = 0
                revived[run.uid_for(player)] = get_locale_text("i18n_explore_core.revive_log", player_name=player.name)
        return revived

    def revive_downed_players(self, run):
        revived = self._revive_downed(run)
        notices = list(revived.values())
        for uid, text in revived.items():
            self._notice(run, uid, text)
        return notices

    def is_all_downed(self, run):
        players = self._party(run)
        return bool(players) and all(player.downed or player.hp <= 0 for player in players)

    def enter_next_stage(self, run):
        map_engine = self._require_map_engine()
        caller = run.user_id
        leader = run.leader_id or (run.party_order[0] if run.party_order else caller)
        leader_player = run.players.get(leader)
        if leader_player is None:
            return
        carried = self._collect_notices(run)
        revived = self._revive_downed(run)
        for uid, text in revived.items():
            carried.setdefault(uid, []).append(text)
        target_stage = max(player.stage for player in self._party(run)) + 1
        run.enemies.clear()
        run.node_data = {}
        if target_stage == 1:
            views = {}
            for uid in run.party_order:
                player = run.players[uid]
                previous, previous_user = self._swap(run, player)
                player.stage = 0
                map_engine._enter_next_stage_solo(run)
                data = {
                    key: run.node_data[key]
                    for key in ("options", "style")
                    if key in run.node_data
                }
                views[uid] = {"node_type": "start_ancient", "data": data}
                self._restore(run, previous, previous_user)
            run.node_data = {
                "coop_node_type": "start_ancient",
                "player_views": views,
                "stage_ready": {
                    uid: run.players[uid].downed for uid in run.party_order
                },
            }
            run.node_data["votes"] = {}
            run.node_type = "start_ancient"
            self._attach_notices(run, carried, caller)
            self.apply_view(run, caller)
            self.save_manager.save_coop_save(caller, run)
            return
        for uid in run.party_order:
            player = run.players[uid]
            player.stage = target_stage
            player.shield = 0
            player.minions.clear()
            player.amulets.clear()
            player.abilities.clear()
            player.actions = 1
            player.bonus_actions = 1
            if target_stage > 1:
                self.save_manager.record_stage_passed(uid)
            if "espresso_relic" in player.relics:
                player.relics.remove("espresso_relic")
            if "lucky_coin" in player.relics:
                player.gold += MAP_LUCKY_COIN_GOLD
            if "tax_contract" in player.relics:
                player.gold = max(0, player.gold - MAP_TAX_CONTRACT_GOLD)
        previous, previous_user = self._swap(run, leader_player)
        from ..data.map_config import MapConfig
        if target_stage in MapConfig.CAFE_STAGES:
            self.init_coop_cafe(run, map_engine)
        elif target_stage in MapConfig.BOSS_STAGES:
            run.node_type = "battle"
            self.battle_engine._init_battle_node(run, "boss")
            run.node_data["coop_node_type"] = "battle"
        else:
            if target_stage in MapConfig.STAGE_NETWORKS:
                start_stage, end_stage = MapConfig.STAGE_NETWORKS[target_stage]
                map_engine._generate_map_network(run, start_stage, end_stage)
            run.node_type = "map_select"
            map_engine._build_map_options(run)
            run.node_data["coop_node_type"] = "map_select"
        self._restore(run, previous, previous_user)
        self._attach_notices(run, carried, caller)
        run.node_data["votes"] = {}
        self.apply_view(run, caller)
        self.save_manager.save_coop_save(caller, run)

    def init_coop_cafe(self, run, map_engine):
        from .cafe_engine import CafeEngine
        cafe = CafeEngine(self.save_manager, map_engine)
        views = {}
        ready = {}
        for uid in run.party_order:
            player = run.players[uid]
            previous, previous_user = self._swap(run, player)
            cafe.init_cafe(run, persist=False)
            data = {"cafe_data": run.node_data.get("cafe_data", {})}
            data["coop_done"] = player.downed
            views[uid] = {"node_type": "cafe", "data": data}
            ready[uid] = player.downed
            self._restore(run, previous, previous_user)
        run.node_type = "cafe"
        run.node_data = {
            "coop_node_type": "cafe",
            "player_views": views,
            "stage_ready": ready,
        }

    def enter_ancient_node(self, run):
        map_engine = self._require_map_engine()
        caller = run.user_id
        carried = self._collect_notices(run)
        run.enemies.clear()
        views = {}
        ready = {}
        for uid in run.party_order:
            player = run.players[uid]
            previous, previous_user = self._swap(run, player)
            map_engine._init_ancient_node(run)
            data = {
                key: run.node_data[key]
                for key in ("options", "style")
                if key in run.node_data
            }
            data["coop_done"] = player.downed
            views[uid] = {"node_type": "ancient", "data": data}
            ready[uid] = player.downed
            self._restore(run, previous, previous_user)
        run.node_type = "ancient"
        run.node_data = {
            "coop_node_type": "ancient",
            "player_views": views,
            "stage_ready": ready,
        }
        self._attach_notices(run, carried, caller)
        self.apply_view(run, caller)
        self.save_manager.save_coop_save(caller, run)

    def start_coop(self, engine, member_ids, leader_id):
        coop_id = uuid.uuid4().hex[:8]
        run = GameRun(
            user_id=leader_id,
            node_type="start",
            player=None,
            enemies=[],
            node_data={},
            coop_id=coop_id,
            leader_id=leader_id,
            party_order=list(member_ids),
            players={},
        )
        from .daily_blessing import apply_pending_blessing
        for uid in member_ids:
            player = engine._build_player_state(uid)
            run.players[uid] = player
            run.player = player
            run.user_id = uid
            stats = self.save_manager.load_stats(uid)
            stats.active_coop_id = coop_id
            stats.active_lobby_id = ""
            stats.projection_feed = []
            stats.team_log_history = []
            run.node_data = {}
            apply_pending_blessing(run, stats)
            self.save_manager.save_stats(uid, stats)
        run.player = run.players[leader_id]
        run.user_id = leader_id
        run.node_data = {}
        self.enter_next_stage(run)
        self.save_manager.save_coop_save(leader_id, run)
        return run

    def _finish_notice(self, run, uid, prefix="", on_all_ready=None):
        ready = run.node_data.setdefault("stage_ready", {})
        ready[uid] = True
        views = run.node_data.get("player_views", {})
        view = views.get(uid)
        if view:
            view["data"]["coop_done"] = True
            view["data"]["options"] = []
            view["data"]["items"] = []
            for key, value in view["data"].items():
                run.node_data[key] = value
        alive = [u for u in run.party_order if u in run.players]
        if all(ready.get(u, False) or run.players[u].downed for u in alive):
            notices = self.resolve_relic_claims(run)
            player_names = get_locale_text("i18n_explore_core.list_delimiter").join(run.players[u].name for u in alive)
            advance = on_all_ready or self.enter_next_stage
            advance(run)
            self.save_manager.save_coop_save(run.user_id, run)
            notice_text = "\n".join(notices)
            extra = f"\n{notice_text}" if notice_text else ""
            return get_locale_text("i18n_explore_core.team_all_ready", prefix=prefix, player_names=player_names, extra=extra).strip()
        waiting = [
            run.players[u].name
            for u in alive
            if not ready.get(u, False) and not run.players[u].downed
        ]
        self.save_manager.save_coop_save(uid, run)
        waiting_names = get_locale_text("i18n_explore_core.list_delimiter").join(waiting) if waiting else get_locale_text("i18n_explore_core.waiting_none")
        return get_locale_text("i18n_explore_core.team_waiting", prefix=prefix, waiting=waiting_names)

    def finish_player_node(self, run, uid, prefix=""):
        return self._finish_notice(run, uid, prefix)

    def finish_cafe_node(self, run, uid, prefix=""):
        return self._finish_notice(run, uid, prefix, on_all_ready=self.enter_ancient_node)

    def resolve_relic_claims(self, run):
        claims = run.node_data.get("relic_claims", {})
        produced = {}
        for relic_id, claimants in list(claims.items()):
            unique = []
            for uid in claimants:
                if uid in run.players and uid not in unique:
                    unique.append(uid)
            from ..entities import get_relic_name
            relic_name = get_relic_name(relic_id)
            for uid in unique:
                player = run.players[uid]
                if relic_id in player.relics:
                    continue
                player.relics.append(relic_id)
                text = get_locale_text("i18n_explore_core.shared_relic_notice", player_name=player.name, relic_name=relic_name)
                self._notice(run, uid, text)
                produced.setdefault(uid, []).append(text)
        run.node_data["relic_claims"] = {}
        return produced.get(run.user_id, [])

    def gain_shared_relic(self, run, uid, relic_id):
        claims = run.node_data.setdefault("relic_claims", {})
        claims.setdefault(relic_id, []).append(uid)
        return len(claims[relic_id])

    def _vote_threshold(self, run):
        alive = self._alive_uids(run)
        return max(1, ceil(len(alive) * COOP_VOTE_RATIO))

    def _vote(self, run, uid, option_idx, recorded_key):
        if uid == run.leader_id:
            run.node_data["votes"] = {}
            return None
        votes = run.node_data.setdefault("votes", {})
        votes[uid] = option_idx
        alive = self._alive_uids(run)
        same = sum(1 for member in alive if votes.get(member) == option_idx)
        if alive and same >= self._vote_threshold(run):
            run.node_data["votes"] = {}
            return None
        delimiter = get_locale_text("i18n_explore_core.list_delimiter")
        summary = delimiter.join(
            get_locale_text("i18n_explore_core.vote_summary_entry", name=run.players[member].name, index=index)
            for member, index in votes.items()
            if member in run.players
        )
        return get_locale_text(recorded_key, summary=summary)

    def vote_map_node(self, run, uid, option_idx):
        return self._vote(run, uid, option_idx, "i18n_explore_core.vote_recorded")

    def vote_event_option(self, run, uid, option_idx):
        return self._vote(run, uid, option_idx, "i18n_explore_core.event_vote_recorded")

    def _reward_card_pool(self, run, player, stats):
        return DeckService.get_reward_card_pool(run, player, stats, include_coop=True)

    def _make_reward_items(self, run, uid, difficulty):
        from ..models.events import RewardGenerateEvent
        player = run.players[uid]
        if player.downed:
            return [], get_locale_text("i18n_explore_core.downed_no_loot")
        previous, previous_user = self._swap(run, player)
        items = build_reward_items(
            self.save_manager,
            run,
            player,
            difficulty,
            True,
            len(run.party_order),
        )
        evt = RewardGenerateEvent(run, items)
        if self.battle_engine and hasattr(self.battle_engine, "event_bus"):
            self.battle_engine.event_bus.dispatch(evt)
        self._restore(run, previous, previous_user)
        return items, ""

    def _make_boss_chest_view(self, run, uid):
        from ..entities import ALL_CARDS, get_relic_name
        player = run.players[uid]
        stats = self.save_manager.load_stats(uid)
        options = []
        mythic_relics = BOSS_MYTHIC_RELICS
        available_relics = [r for r in mythic_relics if r not in player.relics]
        if available_relics:
            options.append({"type": "relic", "id": random.choice(available_relics)})
        class_mythic_cards = list(BOSS_MYTHIC_CARDS)
        if getattr(stats, "yog_sothoth_kill_count", 0) > 0:
            class_mythic_cards.append("neutral_button_magic")
        if getattr(player, "selected_class", "法师") == "战士":
            class_mythic_cards.append("warrior_hematopoiesis")
        else:
            class_mythic_cards.append("wizard_split_to_ten")
        needed = 3 - len(options)
        for cid in random.sample(class_mythic_cards, min(needed, len(class_mythic_cards))):
            options.append({"type": "card", "id": cid})
        items = []
        for option in options:
            items.append({
                "type": "boss_relic" if option["type"] == "relic" else "boss_card",
                "id": option["id"],
                "taken": False,
                "group_id": "boss_chest_group",
            })
        data = {
            "title": get_locale_text("render_boss_chest_title"),
            "desc": get_locale_text("i18n_explore_core.boss_chest_desc"),
            "options": options,
            "items": items,
        }
        return data

    def init_coop_rewards(self, run, difficulty):
        views = {}
        rewards = {}
        stage_ready = {}
        for uid in run.party_order:
            items, note = self._make_reward_items(run, uid, difficulty)
            rewards[uid] = items
            view_data = {
                "items": items,
                "quest_bonus": note,
                "coop_done": run.players[uid].downed,
                "coop_downed": run.players[uid].downed,
            }
            views[uid] = {"node_type": "reward", "data": view_data}
            stage_ready[uid] = run.players[uid].downed
        run.node_type = "reward"
        run.node_data = {
            "coop_node_type": "reward",
            "player_views": views,
            "player_rewards": rewards,
            "stage_ready": stage_ready,
        }
        self.apply_view(run, run.user_id)

    def init_coop_boss_chest(self, run):
        views = {}
        stage_ready = {}
        for uid in run.party_order:
            if run.players[uid].downed:
                data = {"items": [], "coop_done": True, "coop_downed": True, "title": get_locale_text("i18n_explore_core.boss_chest_downed_title"), "desc": get_locale_text("i18n_explore_core.boss_chest_downed_desc")}
            else:
                data = self._make_boss_chest_view(run, uid)
            views[uid] = {"node_type": "boss_chest", "data": data}
            stage_ready[uid] = run.players[uid].downed
        run.node_type = "boss_chest"
        run.node_data = {
            "coop_node_type": "boss_chest",
            "player_views": views,
            "stage_ready": stage_ready,
        }
        self.apply_view(run, run.user_id)

    def handle_coop_battle_win(self, run):
        from ..data.map_config import MapConfig
        from ..entities import get_relic_name
        from ..models.events import BattleWinEvent
        difficulty = run.node_data.get("difficulty", "normal")
        stage = max(player.stage for player in self._party(run))
        for uid in run.party_order:
            player = run.players[uid]
            player.buffs.clear()
            player.hp = min(max(player.hp, 0), player.max_hp)
            if player.hp <= 0:
                player.downed = True
            previous, previous_user = self._swap(run, player)
            if self.battle_engine and hasattr(self.battle_engine, "event_bus"):
                self.battle_engine.event_bus.dispatch(BattleWinEvent(run))
            self._restore(run, previous, previous_user)
        run.enemies.clear()
        if stage == MapConfig.FINAL_BOSS_STAGE:
            run.node_type = "victory"
            run.node_data = {
                "coop_node_type": "victory",
                "boss_name": run.node_data.get("boss_name", get_locale_text("i18n_explore_core.final_boss_name")),
            }
            self._team_notice(run, get_locale_text("i18n_explore_core.final_boss_notice", boss_name=get_locale_text("i18n_explore_core.final_boss_name")))
            for uid in run.party_order:
                stats = self.save_manager.load_stats(uid)
                stats.yog_sothoth_kill_count = getattr(stats, "yog_sothoth_kill_count", 0) + 1
                self.save_manager.save_stats(uid, stats)
            return
        if stage == MapConfig.GATE_BOSS_STAGE:
            has_key = all(
                getattr(self.save_manager.load_stats(uid), "unlocked_gatekey", False)
                for uid in run.party_order
            )
            if not has_key:
                run.node_type = "victory"
                run.node_data = {
                    "coop_node_type": "victory",
                    "boss_name": run.node_data.get("boss_name", ""),
                }
                self._team_notice(run, get_locale_text("i18n_explore_core.gate_boss_victory_notice"))
                return
            self.init_coop_boss_chest(run)
            return
        self.init_coop_rewards(run, difficulty)

    def handle_battle_turn_end(self, run):
        if not run.player or run.player.downed:
            if self.is_all_downed(run):
                run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.save_manager.settle_coop_game_and_delete(run.user_id, run, is_victory=False)
                return get_locale_text("i18n_explore_core.coop_wipe_simple", settle_msg=settle_msg)
            return get_locale_text("i18n_explore_core.downed_spectate")
        uid = run.uid_for(run.player)
        logs = [self.battle_engine.card_player._end_player_phase(run, run.player)]
        ready = run.node_data.setdefault("turn_ready", {})
        ready[uid] = True
        alive = self._alive_uids(run)
        waiting = [u for u in alive if not ready.get(u, False)]
        if waiting:
            ready_uids = [u for u in alive if ready.get(u, False)]
            names = get_locale_text("i18n_explore_core.list_delimiter").join(run.players[u].name for u in ready_uids)
            count = len(ready_uids)
            self.save_manager.save_save(uid, run)
            logs_text = self.battle_engine._append_logs_to_res(run, "\n".join(filter(None, logs)))
            return get_locale_text(
                "i18n_explore_core.turn_waiting_others",
                logs=logs_text,
                count=count,
                total=len(alive),
                names=names,
            )
        viewer = run.player
        viewer_uid = run.user_id
        run.node_data["turn_ready"] = {
            member: run.players[member].downed for member in run.party_order
        }
        self.assign_enemy_targets(run)
        enemy_logs = self.battle_engine._enemy_turn(run)
        if self.battle_engine.is_battle_won(run):
            if self.is_all_downed(run):
                run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
                settle_msg = self.save_manager.settle_coop_game_and_delete(viewer_uid, run, is_victory=False)
                return get_locale_text("i18n_explore_core.coop_wipe_enemy_log", enemy_logs=enemy_logs, settle_msg=settle_msg)
            self.handle_coop_battle_win(run)
            self.save_manager.save_save(viewer_uid, run)
            return self.battle_engine._append_logs_to_res(run, get_locale_text("i18n_explore_core.battle_victory_log", enemy_logs=enemy_logs))
        if self.is_all_downed(run):
            run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
            settle_msg = self.save_manager.settle_coop_game_and_delete(viewer_uid, run, is_victory=False)
            return get_locale_text("i18n_explore_core.coop_wipe_enemy_log", enemy_logs=enemy_logs, settle_msg=settle_msg)
        turn_logs = []
        first_alive = True
        for member in run.party_order:
            player = run.players[member]
            if player.downed or player.hp <= 0:
                continue
            previous, previous_user = self._swap(run, player)
            turn_logs.append(
                self.battle_engine.card_player._begin_player_phase(
                    run, player, advance_global=first_alive
                )
            )
            first_alive = False
            self._restore(run, previous, previous_user)
        joined = "\n".join(log for log in turn_logs if log)
        run.player = viewer
        run.user_id = viewer_uid
        if self.is_all_downed(run):
            run.coop_end_reason = get_locale_text("i18n_explore_core.coop_end_reason")
            settle_msg = self.save_manager.settle_coop_game_and_delete(viewer_uid, run, is_victory=False)
            return get_locale_text("i18n_explore_core.coop_wipe_joined", enemy_logs=enemy_logs, joined=joined, settle_msg=settle_msg)
        self.battle_engine._roll_enemy_intent(run)
        self.assign_enemy_targets(run)
        self.save_manager.save_save(viewer_uid, run)
        result = get_locale_text(
            "i18n_explore_core.turn_all_ready",
            enemy_logs=enemy_logs,
            joined=joined,
            turn_count=run.node_data["turn_count"],
        )
        return self.battle_engine._append_logs_to_res(run, result)

    def _pick_enemy_target(self, run, enemy_index, intent, fallback):
        targets = run.node_data.get("enemy_targets", {})
        marked = targets.get(str(enemy_index))
        if intent.type in AOE_INTENT_TYPES:
            return "ALL"
        if marked and marked in run.players:
            player = run.players[marked]
            if player.hp > 0 and not player.downed:
                return marked
        alive = self._alive_uids(run)
        return alive[0] if alive else fallback
