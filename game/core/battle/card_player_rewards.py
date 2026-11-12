import random
from ...models.state import GameRun, PlayerState
from ...data.map_config import MapConfig
from .corpse_reward import handle_corpse_win as handle_corpse_reward
from ..reward_builder import build_reward_items, roll_battle_gold, roll_potion
from ...data.locale_data import get_locale_text
from ...entities import get_relic_name
from ...models.events import BattleWinEvent
from ..achievement_service import AchievementService


class CardPlayerRewardsMixin:
    def handle_battle_win(self, run: GameRun):
        if getattr(run, "coop_id", ""):
            from ..coop_engine import CoopEngine
            CoopEngine(self.engine.save_manager, self.engine).handle_coop_battle_win(run)
            self.engine.save_manager.save_save(run.user_id, run)
            return
        p = run.player
        p.buffs.clear()
        p.hp = min(p.max_hp, p.hp)
        evt_win = BattleWinEvent(run)
        self.engine.event_bus.dispatch(evt_win)
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
        quest = run.node_data.get("quest")
        quest_bonus = ""
        items = []
        if quest == "knight_cave":
            items.append({
                "type": "quest_card",
                "card_id": "shield_guard",
                "taken": False,
                "bind_group": "quest_knight_cave"
            })
            items.append({
                "type": "quest_relic",
                "relic_id": "heavy_armor",
                "taken": False,
                "bind_group": "quest_knight_cave"
            })
            quest_bonus = get_locale_text("i18n_battle_core.quest_knight_cave_bonus")
        elif quest == "maze_fight":
            got_relic = random.choice(["whetstone", "ready_pack", "arcane_rune"])
            items.append({
                "type": "relic",
                "relic_id": got_relic,
                "taken": False
            })
            quest_bonus = get_locale_text("i18n_battle_core.quest_maze_fight_bonus", relic=get_relic_name(got_relic))
        
        stats = self.engine.save_manager.load_stats(run.user_id)
        if difficulty == "boss" and stats is not None:
            ach = AchievementService(self.engine.save_manager)
            if p.max_hp <= 1:
                ach.record_stat(run.user_id, "one_hp_boss_kills", 1, stats=stats, save=False)
            if p.stage == 12:
                ach.record_stat(run.user_id, "act1_boss_kills", 1, stats=stats, save=False)
            elif p.stage == MapConfig.AVERGOMON_STAGE:
                ach.record_stat(run.user_id, "avergomon_kills", 1, stats=stats, save=False)
        if p.stage in (MapConfig.FINAL_BOSS_STAGE, MapConfig.GATE_BOSS_STAGE):
            roll_battle_gold(difficulty)
            roll_potion(stats, difficulty)
            reward_items = []
        else:
            reward_items = build_reward_items(
                self.engine.save_manager,
                run,
                p,
                difficulty,
            )
        has_gatekey = getattr(stats, "unlocked_gatekey", False)
        if p.stage == MapConfig.FINAL_BOSS_STAGE:
            run.node_type = "victory"
            stats.yog_sothoth_kill_count = getattr(stats, "yog_sothoth_kill_count", 0) + 1
            AchievementService(self.engine.save_manager).reconcile(run.user_id, stats=stats, save=True)
            self.engine.save_manager.save_stats(run.user_id, stats)
        elif p.stage == MapConfig.GATE_BOSS_STAGE and not has_gatekey:
            run.node_type = "victory"
            if run.node_data.get("boss_name") == "Icerainboww":
                stats.killed_icerainboww = True
            AchievementService(self.engine.save_manager).record_stat(run.user_id, "wins", 1, stats=stats, save=True)
            self.engine.save_manager.save_stats(run.user_id, stats)
        elif p.stage == MapConfig.GATE_BOSS_STAGE and has_gatekey:
            if run.node_data.get("boss_name") == "Icerainboww":
                stats.killed_icerainboww = True
            AchievementService(self.engine.save_manager).reconcile(run.user_id, stats=stats, save=True)
            self.engine.save_manager.save_stats(run.user_id, stats)
            run.node_type = "boss_chest"
            p_class = getattr(stats, "selected_class", "法师")
            class_mythic_cards = ["neutral_plane_shift", "neutral_omega"]
            if getattr(stats, "yog_sothoth_kill_count", 0) > 0:
                class_mythic_cards.append("neutral_button_magic")
            if p_class == "战士":
                class_mythic_cards.append("warrior_hematopoiesis")
            else:
                class_mythic_cards.append("wizard_split_to_ten")
            
            mythic_relics = ["infinite_hourglass"]
            available_relics = [r for r in mythic_relics if r not in p.relics]
            
            options = []
            if available_relics:
                relic_choice = random.choice(available_relics)
                options.append({"type": "relic", "id": relic_choice})
            
            needed = 3 - len(options)
            chosen_cards = random.sample(class_mythic_cards, min(needed, len(class_mythic_cards)))
            for c in chosen_cards:
                options.append({"type": "card", "id": c})
                
            items = []
            for opt in options:
                items.append({
                    "type": "boss_relic" if opt["type"] == "relic" else "boss_card",
                    "id": opt["id"],
                    "taken": False,
                    "group_id": "boss_chest_group"
                })
            from ...models.events import RewardGenerateEvent
            evt = RewardGenerateEvent(run, items)
            self.engine.event_bus.dispatch(evt)
            run.node_data = {
                "title": get_locale_text("i18n_battle_core.boss_chest_title"),
                "desc": get_locale_text("i18n_battle_core.boss_chest_desc"),
                "options": options,
                "items": items
            }
            self.engine.save_manager.save_save(run.user_id, run)
        else:
            run.node_type = "reward"
            items.extend(reward_items)
            if difficulty == "elite":
                relic_item = next((it for it in reward_items if it.get("type") == "relic"), None)
                if relic_item:
                    elite_name = run.node_data.get("elite_name", "")
                    quest_bonus += get_locale_text("i18n_battle_core.elite_defeat_bonus", elite=elite_name, relic=get_relic_name(relic_item['relic_id']))
            
            pending_gems = run.node_data.get("pending_gems", [])
            if pending_gems:
                for gid in pending_gems:
                    items.append({
                        "type": "gem",
                        "gem_id": gid,
                        "taken": False
                    })
            
            from ...models.events import RewardGenerateEvent
            evt = RewardGenerateEvent(run, items)
            self.engine.event_bus.dispatch(evt)
            
            is_town = run.node_data.get("is_town_combat", False)
            npc_n = run.node_data.get("npc_name", "")
            run.node_data = {"items": items, "quest_bonus": quest_bonus}
            if is_town:
                run.node_data["is_town_combat"] = True
                run.node_data["npc_name"] = npc_n
            if difficulty == "boss":
                AchievementService(self.engine.save_manager).reconcile(run.user_id, stats=stats, save=True)
                self.engine.save_manager.save_stats(run.user_id, stats)
            self.engine.save_manager.save_save(run.user_id, run)

    def handle_corpse_win(self, run: GameRun):
        handle_corpse_reward(self, run)

    def _reindex_minions(self, p: PlayerState):
        self.engine._reindex_minions(p)
