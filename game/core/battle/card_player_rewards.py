import random

from ...data.locale_data import get_locale_text
from ...data.map_config import MapConfig
from ...data.relic_data import RELIC_CONFIG
from ...data.reward_config import (
    BOSS_MYTHIC_CARDS,
    BOSS_MYTHIC_RELICS,
    COOP_ELITE_RANDOM_RELIC_RARITIES,
    COOP_ELITE_RANDOM_RELICS_PER_PLAYER,
)
from ...entities import get_relic_name
from ...models.events import BattleWinEvent, RewardGenerateEvent
from ...models.state import GameRun, PlayerState
from ..achievement_service import AchievementService
from ..party_coordinator import apply_and_scope, restore_player, swap_player, team_notice
from ..reward_builder import build_reward_items, elite_relic_id, roll_battle_gold, roll_potion
from .corpse_reward import handle_corpse_win as handle_corpse_reward


class CardPlayerRewardsMixin:
    def build_elite_relic_pool(self, run: GameRun, difficulty: str) -> list:
        if difficulty != "elite" or run.player_count() <= 1:
            return []
        alive = [
            uid
            for uid in run.party_order
            if uid in run.players and not run.players[uid].downed and run.players[uid].hp > 0
        ]
        if not alive:
            return []
        elite_name = str(run.node_data.get("elite_name", ""))
        pool = []
        for uid in alive:
            rid = elite_relic_id(elite_name, run.players[uid], exact=False)
            if rid:
                pool.append(rid)
                break
        target = len(alive) * COOP_ELITE_RANDOM_RELICS_PER_PLAYER + 1
        owned = set()
        for uid in run.party_order:
            if uid in run.players:
                owned.update(run.players[uid].relics)
        eligible = [
            rid
            for rid, cfg in RELIC_CONFIG.items()
            if cfg.get("rarity") in COOP_ELITE_RANDOM_RELIC_RARITIES
            and cfg.get("price", 0) > 0
            and rid not in pool
        ]
        candidates = [rid for rid in eligible if rid not in owned]
        random.shuffle(candidates)
        pool.extend(candidates[: target - len(pool)])
        if len(pool) < target:
            fallback = [
                rid
                for rid in eligible
                if rid not in pool
                and not all(rid in run.players[uid].relics for uid in alive)
            ]
            random.shuffle(fallback)
            pool.extend(fallback[: target - len(pool)])
        return [{"relic_id": rid, "claimed_by": ""} for rid in pool[:target]]

    def _make_boss_chest_view(self, run: GameRun, uid: str) -> dict:
        player = run.players[uid]
        stats = self.engine.save_manager.load_stats(uid)
        options = []
        available_relics = [r for r in BOSS_MYTHIC_RELICS if r not in player.relics]
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
        items = [
            {
                "type": "boss_relic" if opt["type"] == "relic" else "boss_card",
                "id": opt["id"],
                "taken": False,
                "group_id": "boss_chest_group",
            }
            for opt in options
        ]
        previous, previous_user = swap_player(run, player)
        self.engine.event_bus.dispatch(RewardGenerateEvent(run, items))
        restore_player(run, previous, previous_user)
        return {
            "title": get_locale_text("i18n_battle_core.boss_chest_title"),
            "desc": get_locale_text("i18n_battle_core.boss_chest_desc"),
            "options": options,
            "items": items,
        }

    def init_boss_chest(self, run: GameRun):
        caller = run.user_id
        views = {}
        stage_ready = {}
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            if getattr(player, "is_mercenary", False):
                views[uid] = {"node_type": "boss_chest", "data": {"items": [], "coop_done": True}}
                stage_ready[uid] = True
                continue
            if player.downed:
                data = {
                    "items": [],
                    "coop_done": True,
                    "coop_downed": True,
                    "title": get_locale_text("i18n_explore_core.boss_chest_downed_title"),
                    "desc": get_locale_text("i18n_explore_core.boss_chest_downed_desc"),
                }
            else:
                data = self._make_boss_chest_view(run, uid)
            views[uid] = {"node_type": "boss_chest", "data": data}
            stage_ready[uid] = player.downed
        run.node_type = "boss_chest"
        run.node_data = {
            "coop_node_type": "boss_chest",
            "player_views": views,
            "stage_ready": stage_ready,
        }
        apply_and_scope(run, caller)
        self.engine.save_manager.save_save(caller, run)

    def _make_player_reward_items(self, run: GameRun, uid: str, difficulty: str, quest: str, pending_gems: list, elite_name: str):
        player = run.players[uid]
        if player.downed:
            return [], get_locale_text("i18n_explore_core.downed_no_loot")
        items = []
        quest_bonus = ""
        if quest == "knight_cave":
            items.append({"type": "quest_card", "card_id": "shield_guard", "taken": False, "bind_group": "quest_knight_cave"})
            items.append({"type": "quest_relic", "relic_id": "heavy_armor", "taken": False, "bind_group": "quest_knight_cave"})
            quest_bonus = get_locale_text("i18n_battle_core.quest_knight_cave_bonus")
        elif quest == "maze_fight":
            got_relic = random.choice(["whetstone", "ready_pack", "arcane_rune"])
            items.append({"type": "relic", "relic_id": got_relic, "taken": False})
            quest_bonus = get_locale_text("i18n_battle_core.quest_maze_fight_bonus", relic=get_relic_name(got_relic))
        previous, previous_user = swap_player(run, player)
        reward_items = build_reward_items(self.engine.save_manager, run, player, difficulty)
        items.extend(reward_items)
        if run.player_count() <= 1 and difficulty == "elite":
            relic_item = next((it for it in reward_items if it.get("type") == "relic"), None)
            if relic_item:
                quest_bonus += get_locale_text("i18n_battle_core.elite_defeat_bonus", elite=elite_name, relic=get_relic_name(relic_item["relic_id"]))
        for gid in pending_gems:
            items.append({"type": "gem", "gem_id": gid, "taken": False})
        self.engine.event_bus.dispatch(RewardGenerateEvent(run, items))
        restore_player(run, previous, previous_user)
        return items, quest_bonus

    def init_rewards(self, run: GameRun, difficulty: str):
        caller = run.user_id
        quest = run.node_data.get("quest")
        pending_gems = list(run.node_data.get("pending_gems", []))
        elite_name = str(run.node_data.get("elite_name", ""))
        relic_pool = self.build_elite_relic_pool(run, difficulty)
        views = {}
        rewards = {}
        stage_ready = {}
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            if getattr(player, "is_mercenary", False):
                rewards[uid] = []
                views[uid] = {
                    "node_type": "reward",
                    "data": {
                        "items": [],
                        "quest_bonus": "",
                        "coop_done": True,
                        "coop_downed": player.downed,
                    },
                }
                stage_ready[uid] = True
                continue
            items, note = self._make_player_reward_items(run, uid, difficulty, quest, pending_gems, elite_name)
            rewards[uid] = items
            views[uid] = {
                "node_type": "reward",
                "data": {
                    "items": items,
                    "quest_bonus": note,
                    "coop_done": player.downed,
                    "coop_downed": player.downed,
                },
            }
            stage_ready[uid] = player.downed
        run.node_data = {
            "coop_node_type": "reward",
            "player_views": views,
            "player_rewards": rewards,
            "coop_relic_pool": relic_pool,
            "stage_ready": stage_ready,
        }
        apply_and_scope(run, caller)
        self.engine.save_manager.save_save(caller, run)

    def handle_battle_win(self, run: GameRun):
        multi = run.player_count() > 1
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            player.buffs.clear()
            player.hp = min(max(player.hp, 0), player.max_hp)
            if multi and player.hp <= 0:
                player.downed = True
            previous, previous_user = swap_player(run, player)
            self.engine.event_bus.dispatch(BattleWinEvent(run))
            restore_player(run, previous, previous_user)
        if run.node_data.get("corpse_battle"):
            self.handle_corpse_win(run)
            return
        if run.node_data.get("is_town_combat"):
            self.engine.save_manager.save_save(run.user_id, run)
            return
        if run.node_data.get("no_reward"):
            run.node_type = "reward"
            run.node_data = {"cards": [], "no_reward": True}
            self.engine.save_manager.save_save(run.user_id, run)
            return
        difficulty = run.node_data.get("difficulty", "normal")
        stage = max((run.players[u].stage for u in run.party_order if u in run.players), default=run.player.stage)
        if run.node_data.get("is_secret_boss"):
            run.enemies.clear()
            self.engine.map_engine.enter_ancient_node(run)
            self.engine._reindex_minions(run.player)
            return
        run.enemies.clear()
        ach = AchievementService(self.engine.save_manager)
        if stage in (MapConfig.FINAL_BOSS_STAGE, MapConfig.GATE_BOSS_STAGE):
            roll_battle_gold(difficulty)
            roll_potion(self.engine.save_manager.load_stats(run.user_id), difficulty)
        if stage == MapConfig.FINAL_BOSS_STAGE:
            boss_name = run.node_data.get("boss_name", get_locale_text("i18n_explore_core.final_boss_name"))
            run.node_type = "victory"
            run.node_data = {"coop_node_type": "victory", "boss_name": boss_name}
            if multi:
                team_notice(run, get_locale_text("i18n_explore_core.final_boss_notice", boss_name=get_locale_text("i18n_explore_core.final_boss_name")))
            for uid in run.human_uids():
                stats = self.engine.save_manager.load_stats(uid)
                stats.yog_sothoth_kill_count = getattr(stats, "yog_sothoth_kill_count", 0) + 1
                player = run.players.get(uid)
                if player and player.max_hp <= 1:
                    ach.record_stat(uid, "one_hp_boss_kills", 1, stats=stats, save=False)
                ach.reconcile(uid, stats=stats, save=False)
                self.engine.save_manager.save_stats(uid, stats)
            self.engine.save_manager.save_save(run.user_id, run)
            return
        if stage == MapConfig.GATE_BOSS_STAGE:
            has_gatekey = all(
                getattr(self.engine.save_manager.load_stats(uid), "unlocked_gatekey", False)
                for uid in run.all_human_uids()
                if uid in run.players
            )
            boss_name = run.node_data.get("boss_name", "")
            for uid in run.human_uids():
                stats = self.engine.save_manager.load_stats(uid)
                player = run.players.get(uid)
                if boss_name == "Icerainboww":
                    stats.killed_icerainboww = True
                if player and player.max_hp <= 1:
                    ach.record_stat(uid, "one_hp_boss_kills", 1, stats=stats, save=False)
                if not has_gatekey:
                    ach.record_stat(uid, "wins", 1, stats=stats, save=False)
                else:
                    ach.reconcile(uid, stats=stats, save=False)
                self.engine.save_manager.save_stats(uid, stats)
            if not has_gatekey:
                run.node_type = "victory"
                run.node_data = {"coop_node_type": "victory", "boss_name": boss_name}
                if multi:
                    team_notice(run, get_locale_text("i18n_explore_core.gate_boss_victory_notice"))
                self.engine.save_manager.save_save(run.user_id, run)
                return
            self.init_boss_chest(run)
            return
        if difficulty == "boss":
            for uid in run.human_uids():
                stats = self.engine.save_manager.load_stats(uid)
                player = run.players.get(uid)
                if player and player.max_hp <= 1:
                    ach.record_stat(uid, "one_hp_boss_kills", 1, stats=stats, save=False)
                if stage == 12:
                    ach.record_stat(uid, "act1_boss_kills", 1, stats=stats, save=False)
                elif stage == MapConfig.AVERGOMON_STAGE:
                    ach.record_stat(uid, "avergomon_kills", 1, stats=stats, save=False)
                ach.reconcile(uid, stats=stats, save=False)
                self.engine.save_manager.save_stats(uid, stats)
        self.init_rewards(run, difficulty)
        self.engine._reindex_minions(run.player)

    def handle_corpse_win(self, run: GameRun):
        handle_corpse_reward(self, run)

    def _reindex_minions(self, p: PlayerState):
        self.engine._reindex_minions(p)
