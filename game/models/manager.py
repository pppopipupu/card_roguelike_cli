import os
import json
import tempfile
from dataclasses import asdict
from typing import Optional, Tuple, Dict, List
from .state import GameRun, PlayerState, EnemyState, MinionState, AmuletState, BuffState, UserStats, current_user_id, register_stat_recorder, get_user_id
from ..data.map_config import MapConfig

def _atomic_write_json(path: str, data, indent: int = 2) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".rogue-", suffix=".tmp", dir=directory or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

class SaveManager:
    _default_data_dir = None

    def __init__(self, data_dir: str = None):
        if data_dir is not None:
            SaveManager._default_data_dir = data_dir
            self.data_dir = data_dir
        else:
            if SaveManager._default_data_dir is not None:
                self.data_dir = SaveManager._default_data_dir
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                self.data_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "data")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_save_path(self, user_id: str) -> str:
        safe_id = "".join([c for c in user_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"user_{safe_id}.json")

    def get_stats_path(self, user_id: str) -> str:
        safe_id = "".join([c for c in user_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"stats_{safe_id}.json")

    def load_stats(self, user_id: str) -> UserStats:
        path = self.get_stats_path(user_id)
        if not os.path.exists(path):
            return UserStats()
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return UserStats(
                total_damage=d.get("total_damage", 0),
                total_kills=d.get("total_kills", 0),
                total_stages=d.get("total_stages", 0),
                rogue_mode=True,
                duel_mode=False,
                gp=d.get("gp", 0),
                unlocked_subclasses=d.get("unlocked_subclasses", []),
                selected_class=d.get("selected_class", "法师"),
                selected_subclass=d.get("selected_subclass", ""),
                killed_icerainboww=d.get("killed_icerainboww", False),
                unlocked_gatekey=d.get("unlocked_gatekey", False),
                yog_sothoth_kill_count=d.get("yog_sothoth_kill_count", 0),
                yog_sothoth_challenge_count=d.get("yog_sothoth_challenge_count", 0),
                reader_active=d.get("reader_active", False),
                reader_page=d.get("reader_page", 1),
                reader_title=d.get("reader_title", ""),
                reader_items=d.get("reader_items", []),
                reader_mode=d.get("reader_mode", "rogue"),
                in_town=d.get("in_town", False),
                town_pos=d.get("town_pos", "square"),
                guaranteed_card=d.get("guaranteed_card", None),
                locked_cards=d.get("locked_cards", []),
                purchased_pool=d.get("purchased_pool", []),
                defeated_town_npcs=d.get("defeated_town_npcs", []),
                town_inventory=d.get("town_inventory", []),
                town_flags=d.get("town_flags", {}),
                town_health_bonus=d.get("town_health_bonus", 0),
                player_name=d.get("player_name", "玩家"),
                unlocked_new_cards=d.get("unlocked_new_cards", [])
            )
        except:
            return UserStats()

    def save_stats(self, user_id: str, stats: UserStats) -> bool:
        path = self.get_stats_path(user_id)
        try:
            d = asdict(stats)
            _atomic_write_json(path, d)
            return True
        except:
            return False

    def record_damage(self, user_id: str, amount: int):
        if not user_id or amount <= 0:
            return
        stats = self.load_stats(user_id)
        stats.total_damage += amount
        self.save_stats(user_id, stats)

    def record_kill(self, user_id: str):
        if not user_id:
            return
        stats = self.load_stats(user_id)
        stats.total_kills += 1
        self.save_stats(user_id, stats)

    def record_stage_passed(self, user_id: str):
        if not user_id:
            return
        stats = self.load_stats(user_id)
        stats.total_stages += 1
        self.save_stats(user_id, stats)

    def get_duel_registry_path(self) -> str:
        return os.path.join(self.data_dir, "duel_registry.json")

    def get_duel_registry(self) -> dict:
        path = self.get_duel_registry_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_duel_registry(self, reg: dict) -> bool:
        path = self.get_duel_registry_path()
        try:
            _atomic_write_json(path, reg)
            return True
        except:
            return False

    def get_duel_game_id(self, user_id: str) -> Optional[str]:
        return self.get_duel_registry().get(user_id)

    def bind_duel_game(self, user_id1: str, user_id2: str, game_id: str):
        reg = self.get_duel_registry()
        reg[user_id1] = game_id
        reg[user_id2] = game_id
        self.save_duel_registry(reg)

    def unbind_duel_game(self, game_id: str):
        reg = self.get_duel_registry()
        keys_to_del = [k for k, v in reg.items() if v == game_id]
        for k in keys_to_del:
            del reg[k]
        self.save_duel_registry(reg)

    def get_duel_deck_path(self, user_id: str) -> str:
        safe_id = "".join([c for c in user_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"duel_decks_{safe_id}.json")

    def load_duel_decks(self, user_id: str) -> dict:
        path = self.get_duel_deck_path(user_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_duel_decks(self, user_id: str, decks: dict) -> bool:
        path = self.get_duel_deck_path(user_id)
        try:
            _atomic_write_json(path, decks)
            return True
        except:
            return False

    def load_save(self, user_id: str) -> GameRun:
        path = self.get_save_path(user_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return self.from_dict(d)
        except:
            return None

    def save_save(self, user_id: str, run: GameRun) -> bool:
        path = self.get_save_path(user_id)
        try:
            d = self.to_dict(run)
            _atomic_write_json(path, d)
            return True
        except:
            return False

    def delete_save(self, user_id: str) -> bool:
        path = self.get_save_path(user_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except:
                return False
        return False

    def load_duel_save(self, user_id: str) -> GameRun:
        game_id = self.get_duel_game_id(user_id)
        if not game_id:
            return None
        path = os.path.join(self.data_dir, f"duel_{game_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            run = self.from_dict(d)
            if run:
                p2_id = run.node_data.get("player2_id")
                if p2_id == user_id:
                    run.player, run.player2 = run.player2, run.player
                    run.user_id = user_id
            return run
        except:
            return None

    def save_duel_save(self, user_id: str, run: GameRun) -> bool:
        game_id = self.get_duel_game_id(user_id)
        if not game_id:
            return False
        path = os.path.join(self.data_dir, f"duel_{game_id}.json")
        p2_id = run.node_data.get("player2_id")
        if p2_id == user_id:
            run.player, run.player2 = run.player2, run.player
            run.user_id = run.node_data.get("player1_id", run.user_id)
        try:
            d = self.to_dict(run)
            if p2_id == user_id:
                run.player, run.player2 = run.player2, run.player
                run.user_id = user_id
            _atomic_write_json(path, d)
            return True
        except:
            if p2_id == user_id:
                run.player, run.player2 = run.player2, run.player
                run.user_id = user_id
            return False

    def delete_duel_save(self, user_id: str) -> bool:
        game_id = self.get_duel_game_id(user_id)
        if not game_id:
            return False
        path = os.path.join(self.data_dir, f"duel_{game_id}.json")
        self.unbind_duel_game(game_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except:
                return False
        return False

    def to_dict(self, run: GameRun) -> dict:
        if not run:
            return {}
        logs = None
        if run.node_data is not None:
            logs = run.node_data.pop("battle_logs", None)
        try:
            res = asdict(run)
        finally:
            if logs is not None and run.node_data is not None:
                run.node_data["battle_logs"] = logs
        return res

    def _parse_player_state(self, p_data: dict) -> PlayerState:
        if not p_data:
            return None
        p_minions = {}
        for k, v in p_data.get("minions", {}).items():
            m_buffs = []
            for b in v.get("buffs", []):
                if b.get("id") == "summon_sickness":
                    continue
                m_buffs.append(BuffState(
                    id=b["id"],
                    name=b["name"],
                    stacks=b.get("stacks", 1),
                    stacks2=b.get("stacks2", None),
                    desc=b.get("desc", "")
                ))
            p_minions[k] = MinionState(
                id=v["id"],
                name=v["name"],
                hp=v["hp"],
                max_hp=v["max_hp"],
                atk=v["atk"],
                actions=v.get("actions", 1),
                bonus_actions=v.get("bonus_actions", 1),
                attack_actions=v.get("attack_actions", 1),
                buffs=m_buffs
            )
        p_amulets = {k: AmuletState(**v) for k, v in p_data.get("amulets", {}).items()}
        p_buffs = []
        for b in p_data.get("buffs", []):
            if b.get("id") == "summon_sickness":
                continue
            p_buffs.append(BuffState(
                id=b["id"],
                name=b["name"],
                stacks=b.get("stacks", 1),
                stacks2=b.get("stacks2", None),
                desc=b.get("desc", "")
            ))
        minion_gy = list(p_data.get("minion_graveyard", []))
        enemy_gy = list(p_data.get("enemy_graveyard", []))
        if not minion_gy and not enemy_gy and "graveyard" in p_data:
            for item in p_data["graveyard"]:
                if item.startswith("minion:"):
                    minion_gy.append(item[len("minion:"):])
                elif item.startswith("enemy:"):
                    enemy_gy.append(item[len("enemy:"):])
                else:
                    enemy_gy.append(item)
        return PlayerState(
            hp=p_data["hp"],
            max_hp=p_data["max_hp"],
            shield=p_data["shield"],
            gold=p_data["gold"],
            stage=p_data["stage"],
            name=p_data.get("name", "玩家"),
            deck=p_data.get("deck", []),
            draw_pile=p_data.get("draw_pile", []),
            discard_pile=p_data.get("discard_pile", []),
            exhaust_pile=p_data.get("exhaust_pile", []),
            graveyard=p_data.get("graveyard", []),
            minion_graveyard=minion_gy,
            enemy_graveyard=enemy_gy,
            hand=p_data.get("hand", []),
            actions=p_data.get("actions", 1),
            bonus_actions=p_data.get("bonus_actions", 1),
            minions=p_minions,
            amulets=p_amulets,
            abilities=p_data.get("abilities", []),
            fold_guide=p_data.get("fold_guide", False),
            buffs=p_buffs,
            relics=p_data.get("relics", []),
            subclass=p_data.get("subclass", ""),
            selected_class=p_data.get("selected_class", "法师"),
            potions=p_data.get("potions", [])
        )

    def from_dict(self, d: dict) -> GameRun:
        if not d:
            return None
        player = self._parse_player_state(d["player"])
        player2 = self._parse_player_state(d.get("player2"))
        enemies = []
        if "enemies" in d:
            from .state import EnemyIntentState
            for ed in d["enemies"]:
                e_buffs = []
                for b in ed.get("buffs", []):
                    if b.get("id") == "summon_sickness":
                        continue
                    e_buffs.append(BuffState(
                        id=b["id"],
                        name=b["name"],
                        stacks=b.get("stacks", 1),
                        stacks2=b.get("stacks2", None),
                        desc=b.get("desc", "")
                    ))
                intent_list = []
                if "intents" in ed:
                    for it in ed["intents"]:
                        intent_list.append(EnemyIntentState(
                            type=it.get("type", ""),
                            val=it.get("val", 0),
                            desc=it.get("desc", ""),
                            cost_a=it.get("cost_a", 1),
                            cost_ba=it.get("cost_ba", 0),
                            cancelled=it.get("cancelled", False),
                            cancelled_desc=it.get("cancelled_desc", "")
                        ))
                enemies.append(EnemyState(
                    name=ed["name"],
                    hp=ed["hp"],
                    max_hp=ed["max_hp"],
                    shield=ed["shield"],
                    actions=ed.get("actions", 1),
                    bonus_actions=ed.get("bonus_actions", 1),
                    buffs=e_buffs,
                    is_summon=ed.get("is_summon", False),
                    max_actions=ed.get("max_actions", 1),
                    max_bonus_actions=ed.get("max_bonus_actions", 0),
                    intents=intent_list,
                    intent_type=ed.get("intent_type", ""),
                    intent_val=ed.get("intent_val", 0),
                    intent_desc=ed.get("intent_desc", ""),
                    intent_a_type=ed.get("intent_a_type", ""),
                    intent_a_val=ed.get("intent_a_val", 0),
                    intent_a_desc=ed.get("intent_a_desc", ""),
                    intent_a2_type=ed.get("intent_a2_type", ""),
                    intent_a2_val=ed.get("intent_a2_val", 0),
                    intent_a2_desc=ed.get("intent_a2_desc", ""),
                    intent_ba_type=ed.get("intent_ba_type", ""),
                    intent_ba_val=ed.get("intent_ba_val", 0),
                    intent_ba_desc=ed.get("intent_ba_desc", ""),
                    intent_ba2_type=ed.get("intent_ba2_type", ""),
                    intent_ba2_val=ed.get("intent_ba2_val", 0),
                    intent_ba2_desc=ed.get("intent_ba2_desc", "")
                ))
        return GameRun(
            user_id=d["user_id"],
            node_type=d["node_type"],
            player=player,
            enemies=enemies,
            node_data=d.get("node_data", {}),
            map_data=d.get("map_data", {}),
            player2=player2
        )

    def settle_game_and_delete(self, user_id: str, run: GameRun, is_victory: bool = False) -> str:
        if not run or not run.player:
            self.delete_save(user_id)
            return "本局结算：未找到有效的角色进度，未获得 GP。"
        stage = run.player.stage
        gold = run.player.gold
        if stage < 5:
            self.delete_save(user_id)
            return f"本局结算：由于在第 {stage} 层结束，未获得 GP。"
        gp_gained = gold * 10
        victory_bonus = ""
        unlock_msg = ""
        stats = self.load_stats(user_id)
        if is_victory:
            if stage == MapConfig.FINAL_BOSS_STAGE:
                gp_gained += 3000
                victory_bonus = "（含超最终通关奖励 3000 GP）"
                unlock_msg = "\n\n🎉 特别提示：你成功击败了先古的超最终BOSS【虚空之门·尤格-索托斯】！你已完成了最伟大的先古救赎！"

            else:
                gp_gained += 1000
                victory_bonus = "（含通关奖励 1000 GP）"
                if run.node_data.get("boss_name") == "Icerainboww":
                    stats.killed_icerainboww = True
                    unlock_msg = "\n\n🎉 特别提示：你成功击败了最终BOSS【Icerainboww】！在先古祭坛和先古赐福石碑中已永久解锁传奇随从卡【Icerainboww】！"
        stats.town_flags.pop("market_shelf", None)
        stats.gp += gp_gained
        self.save_stats(user_id, stats)
        self.delete_save(user_id)
        return f"本局结算：剩余金币 {gold}，折算获得 {gp_gained} GP{victory_bonus}！当前总 GP：{stats.gp}。{unlock_msg}"

    def get_admin_config_path(self) -> str:
        return os.path.join(self.data_dir, "admin_config.json")

    def load_admin_config(self) -> dict:
        path = self.get_admin_config_path()
        if not os.path.exists(path):
            return {"final_boss": "random"}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"final_boss": "random"}

    def save_admin_config(self, cfg: dict) -> bool:
        path = self.get_admin_config_path()
        try:
            _atomic_write_json(path, cfg)
            return True
        except:
            return False

def stat_recorder_callback(enemy_name: str, amount: int, is_defeat: bool):
    user_id = get_user_id()
    if not user_id:
        return
    mgr = SaveManager()
    if amount > 0:
        mgr.record_damage(user_id, amount)
    if is_defeat:
        mgr.record_kill(user_id)

register_stat_recorder(stat_recorder_callback)
