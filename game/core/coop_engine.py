import copy
import random
import uuid
from math import ceil

from ..models.state import CardState, EnemyState, GameRun, PlayerState


VIEW_KEYS = {
    "items",
    "options",
    "cards",
    "title",
    "desc",
    "text",
    "can_skip",
    "force_upgraded",
    "next_node_type",
    "next_node_data",
    "state",
    "pending_remove",
    "remove_source",
    "pending_upgrade",
    "upgrade_source",
    "upgrade_price",
    "pending_gem",
    "style",
    "event_id",
    "description",
    "base_options",
    "pending_cards",
    "pending_card_can_skip",
    "pending_card_upgraded",
    "quest_bonus",
    "no_reward",
    "coop_done",
    "coop_downed",
    "coop_pending_upgrade",
}

SHARED_PERSIST_KEYS = {
    "coop_node_type",
    "player_views",
    "player_rewards",
    "player_shops",
    "player_rests",
    "stage_ready",
    "turn_ready",
    "votes",
    "shared_relics",
    "relic_claims",
    "coop_notices",
    "coop_battle_log_history",
    "enemy_targets",
    "coop_aggro_cursor",
    "coop_node_round",
    "coop_shared_relic",
    "gem_prev_coop_type",
}

TREASURE_RELIC_POOL = [
    "lucky_coin", "red_bottle", "leather_armor", "whetstone", "ready_pack",
    "arcane_rune", "ancient_eye", "gold_compass", "dragon_blood",
    "energy_core", "heavy_armor",
]

VIEW_NODES = {
    "start_ancient",
    "ancient",
    "reward",
    "shop",
    "rest",
    "card_select",
    "treasure",
    "boss_chest",
    "gem_insert",
}

AOE_INTENT_TYPES = {
    "attack_all",
    "aoe_attack",
    "all_attack",
    "aoe_damage",
}

ELITE_RELIC_MAP = {
    "地精百夫长": "centurion_mail",
    "石像鬼祭司": "priest_charm",
    "狂暴兽王": "beastmaster_claw",
    "黑曜石巨灵": "djinn_shard",
    "幽灵大魔法师": "archmage_robe",
    "暗影影魔": "shadow_tentacle",
    "夺心魔": "mindflayer_brain",
    "末日守卫": "doomsday_core",
    "亡灵巫师": "necromancer_skull",
    "夺心魔奥术师": "arcanist_hand",
    "吉斯洋基至高指挥官": "commander_medal",
    "虚空潜伏者": "stalker_eye",
    "冷蛛": "leng_spider_venom",
    "米·戈": "migo_lightning_gun",
    "修格斯": "shoggoth_slime",
    "星之精": "star_vampire_proboscis",
    "克苏鲁之星之眷族": "starspawn_core",
}

NORMAL_POOLS = {
    "early": ["地精突袭者", "石像鬼守卫", "堕落学徒", "狂暴野兽", "邪教徒咔咔", "深潜者", "食尸鬼"],
    "mid": ["幽灵法师", "冰霜史莱姆", "骷髅弓箭手", "剧毒蜘蛛", "邪教徒咔咔", "夜魇", "夏塔克鸟"],
    "late": ["黑曜石巨人", "暗影刺客", "吉斯洋基海盗", "虚空行者", "空鬼"],
}


def _base_enemy_name(name: str) -> str:
    parts = name.rsplit(" ", 1)
    if len(parts) == 2 and len(parts[1]) == 1 and parts[1].isalpha():
        return parts[0]
    return name


class CoopEngine:
    def __init__(self, save_manager, engine=None):
        self.save_manager = save_manager
        self.engine = engine
        self.map_engine = getattr(engine, "map_engine", None)
        self.battle_engine = getattr(engine, "battle_engine", engine)

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
        if not run or not getattr(run, "coop_id", ""):
            return run
        node_data = run.node_data if run.node_data is not None else {}
        run._coop_shared = {
            key: node_data.get(key)
            for key in SHARED_PERSIST_KEYS
            if key in node_data
        }
        base_type = node_data.get("coop_node_type", run.node_type)
        if base_type not in VIEW_NODES:
            return run
        views = node_data.setdefault("player_views", {})
        view = views.get(uid)
        if not view:
            view = {
                "node_type": run.node_type,
                "data": {key: value for key, value in node_data.items() if key in VIEW_KEYS},
            }
            views[uid] = view
        for key in VIEW_KEYS:
            node_data.pop(key, None)
        for key, value in view.get("data", {}).items():
            node_data[key] = value
        run.node_type = view.get("node_type", run.node_type)
        return run

    def persist_view(self, run, uid):
        if not run or not getattr(run, "coop_id", ""):
            return
        node_data = run.node_data if run.node_data is not None else {}
        base_type = node_data.get("coop_node_type", "")
        shared = {}
        for key in SHARED_PERSIST_KEYS:
            if key in node_data:
                shared[key] = node_data[key]
        for key, value in getattr(run, "_coop_shared", {}).items():
            if key not in shared:
                shared[key] = value
                node_data[key] = value
        if base_type not in VIEW_NODES:
            if run.node_type in VIEW_NODES:
                base_type = run.node_type
            else:
                return
        node_data["coop_node_type"] = base_type
        shared["coop_node_type"] = base_type
        views = node_data.setdefault("player_views", shared.get("player_views", {}))
        views[uid] = {
            "node_type": run.node_type,
            "data": {key: value for key, value in node_data.items() if key in VIEW_KEYS},
        }
        node_data["player_views"] = views
        shared["player_views"] = views
        for key, value in shared.items():
            node_data[key] = value
        run._coop_shared = shared

    def list_enemy_hp_multiplier(self, count):
        if count <= 2:
            return 1.0
        if count == 3:
            return 1.5
        return 2.0

    def scale_coop_enemies(self, run):
        count = len(run.party_order)
        originals = list(run.enemies)
        if count < 2 or not originals:
            return
        multiplier = self.list_enemy_hp_multiplier(count)
        expanded = []
        sequence = 0
        for enemy in originals:
            base_name = _base_enemy_name(enemy.name)
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
        self.battle_engine._log_event(run, f"💀 【{player.name}】倒下了！队友仍可继续战斗，进入下一层时将以其 1 HP 复活。")
        if not self._alive_uids(run):
            run.node_data["coop_wipe"] = True

    def revive_downed_players(self, run):
        notices = []
        for player in self._party(run):
            if player.downed or player.hp <= 0:
                player.downed = False
                player.hp = 1
                player.shield = 0
                notices.append(f"✨ 【{player.name}】在层间以 1 HP 复活。")
        if notices:
            run.node_data["coop_notices"] = notices
        return notices

    def is_all_downed(self, run):
        players = self._party(run)
        return bool(players) and all(player.downed or player.hp <= 0 for player in players)

    def enter_next_stage(self, run):
        caller = run.user_id
        leader = run.leader_id or (run.party_order[0] if run.party_order else caller)
        leader_player = run.players.get(leader)
        if leader_player is None:
            return
        revives = self.revive_downed_players(run)
        target_stage = max(player.stage for player in self._party(run)) + 1
        run.enemies.clear()
        run.node_data = {}
        if target_stage == 1:
            views = {}
            for uid in run.party_order:
                player = run.players[uid]
                previous, previous_user = self._swap(run, player)
                player.stage = 0
                self.map_engine._enter_next_stage_solo(run)
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
                "coop_notices": revives,
            }
            run.node_type = "start_ancient"
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
                player.gold += 5
            if "tax_contract" in player.relics:
                player.gold = max(0, player.gold - 6)
        previous, previous_user = self._swap(run, leader_player)
        from ..data.map_config import MapConfig
        if target_stage in MapConfig.CAFE_STAGES:
            from .cafe_engine import CafeEngine
            CafeEngine(self.save_manager, self.map_engine).init_cafe(run)
            run.node_data["coop_node_type"] = run.node_type
        elif target_stage in MapConfig.BOSS_STAGES:
            run.node_type = "battle"
            self.battle_engine._init_battle_node(run, "boss")
            run.node_data["coop_node_type"] = "battle"
        else:
            if target_stage in MapConfig.STAGE_NETWORKS:
                start_stage, end_stage = MapConfig.STAGE_NETWORKS[target_stage]
                self.map_engine._generate_map_network(run, start_stage, end_stage)
            run.node_type = "map_select"
            self.map_engine._build_map_options(run)
            run.node_data["coop_node_type"] = "map_select"
        self._restore(run, previous, previous_user)
        if revives:
            run.node_data.setdefault("coop_notices", []).extend(revives)
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
            run.node_data = {}
            apply_pending_blessing(run, stats)
            self.save_manager.save_stats(uid, stats)
        run.player = run.players[leader_id]
        run.user_id = leader_id
        run.node_data = {}
        self.enter_next_stage(run)
        self.save_manager.save_coop_save(leader_id, run)
        return run

    def _finish_notice(self, run, uid, prefix=""):
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
            player_names = "、".join(run.players[u].name for u in alive)
            self.enter_next_stage(run)
            run.node_data.setdefault("coop_notices", []).extend(notices)
            self.save_manager.save_coop_save(run.user_id, run)
            notice_text = "\n".join(notices)
            extra = f"\n{notice_text}" if notice_text else ""
            return f"{prefix}\n✅ 全队（{player_names}）均已完成，队伍继续前进。{extra}".strip()
        waiting = [
            run.players[u].name
            for u in alive
            if not ready.get(u, False) and not run.players[u].downed
        ]
        self.save_manager.save_coop_save(uid, run)
        return f"{prefix}\n⏳ 你已完成本节点行动，正在等待队友：{'、'.join(waiting) if waiting else '无'}。"

    def finish_player_node(self, run, uid, prefix=""):
        return self._finish_notice(run, uid, prefix)

    def resolve_relic_claims(self, run):
        claims = run.node_data.get("relic_claims", {})
        notices = []
        for relic_id, claimants in list(claims.items()):
            unique = []
            for uid in claimants:
                if uid in run.players and uid not in unique:
                    unique.append(uid)
            if not unique:
                continue
            if len(unique) == 1:
                winner = run.players[unique[0]]
                if relic_id not in winner.relics:
                    winner.relics.append(relic_id)
                from ..entities import get_relic_name
                notices.append(f"🎒 【{winner.name}】获得共享遗物【{get_relic_name(relic_id)}】。")
                continue
            picks = {}
            hands = ["石头", "剪刀", "布"]
            beats = {"石头": "剪刀", "剪刀": "布", "布": "石头"}
            winner_uid = None
            for _ in range(100):
                for uid in unique:
                    picks[uid] = random.choice(hands)
                survivors = [
                    uid
                    for uid in unique
                    if not any(
                        beats[picks[other]] == picks[uid]
                        for other in unique
                        if other != uid
                    )
                ]
                if len(survivors) == 1 and len(set(picks.values())) > 1:
                    winner_uid = survivors[0]
                    break
            if winner_uid is None:
                winner_uid = random.choice(unique)
            from ..entities import get_relic_name
            detail = "，".join(f"{run.players[uid].name}（{picks[uid]}）" for uid in unique)
            winner = run.players[winner_uid]
            if relic_id not in winner.relics:
                winner.relics.append(relic_id)
            losers = [uid for uid in unique if uid != winner_uid]
            for uid in losers:
                run.players[uid].gold += 25
            notice = (
                f"✊✌️✋ [遗物争夺] {detail}。"
                f"【{winner.name}】夺得【{get_relic_name(relic_id)}】！"
            )
            if losers:
                notice += "；".join(f"【{run.players[uid].name}】获得 25 金币补偿" for uid in losers) + "。"
            notices.append(notice)
        run.node_data["relic_claims"] = {}
        return notices

    def gain_shared_relic(self, run, uid, relic_id):
        claims = run.node_data.setdefault("relic_claims", {})
        claims.setdefault(relic_id, []).append(uid)
        return len(claims[relic_id])

    def vote_map_node(self, run, uid, option_idx):
        if uid == run.leader_id:
            run.node_data["votes"] = {}
            return None
        votes = run.node_data.setdefault("votes", {})
        votes[uid] = option_idx
        alive = self._alive_uids(run)
        if alive and all(votes.get(member) == option_idx for member in alive):
            return None
        summary = "、".join(
            f"{run.players[member].name}→{index}"
            for member, index in votes.items()
            if member in run.players
        )
        return f"🗳️ 路线意向已记录（{summary}）。全体队员选择一致后，或由队长直接选择时出发。"

    def _reward_card_pool(self, run, player, stats):
        from ..entities import ALL_CARDS
        from ..entities.cards.market import is_card_available, is_coop_only
        target_color = "warrior" if getattr(player, "selected_class", "法师") == "战士" else "wizard"
        pool = []
        for cid, card in ALL_CARDS.items():
            if cid.endswith("+"):
                continue
            if card.rarity in ("legendary", "mythic", "artifact"):
                continue
            if cid.startswith("curse_") or cid.startswith("duel_"):
                continue
            if card.color not in (target_color, "neutral"):
                continue
            if getattr(card, "coop_only", False):
                continue
            if not is_card_available(cid, stats):
                continue
            pool.append(cid)
        coop_pool = [
            cid
            for cid, card in ALL_CARDS.items()
            if getattr(card, "coop_only", False)
            and getattr(card, "rarity", "common") in ("common", "rare", "epic")
            and is_card_available(cid, stats)
        ]
        if coop_pool:
            pool.extend(coop_pool)
        return pool

    def _make_reward_items(self, run, uid, difficulty):
        from ..entities import ALL_CARDS, get_relic_name
        from ..models.events import RewardGenerateEvent
        from ..data.potion_data import roll_potion
        player = run.players[uid]
        stats = self.save_manager.load_stats(uid)
        if player.downed:
            return [], "你处于倒地状态，无法领取本次战利品；进入下一层时将以 1 HP 复活。"
        previous, previous_user = self._swap(run, player)
        items = []
        gold = 10 + random.randint(5, 15)
        if difficulty == "elite":
            gold = 25 + random.randint(10, 20)
        items.append({"type": "gold", "amount": gold, "taken": False})
        pool = self._reward_card_pool(run, player, stats)
        cards = random.sample(pool, min(3, len(pool))) if pool else []
        from ..models.state import check_and_replace_fireball
        cards = [check_and_replace_fireball(run, cid) for cid in cards]
        items.append({
            "type": "card_reward",
            "cards": cards,
            "taken": False,
            "force": False,
        })
        potion_chance = 0.66 if difficulty == "elite" else 0.33
        if random.random() < potion_chance:
            pid = roll_potion(getattr(player, "selected_class", "法师"))
            items.append({"type": "potion", "potion_id": pid, "taken": False})
        if difficulty == "elite":
            elite_name = _base_enemy_name(str(run.node_data.get("elite_name", "")))
            rid = ELITE_RELIC_MAP.get(elite_name)
            if rid and rid not in player.relics:
                items.append({"type": "shared_relic", "relic_id": rid, "taken": False})
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
        mythic_relics = ["infinite_hourglass"]
        available_relics = [r for r in mythic_relics if r not in player.relics]
        if available_relics:
            options.append({"type": "relic", "id": random.choice(available_relics)})
        class_mythic_cards = ["neutral_plane_shift", "neutral_omega"]
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
            "title": "🏆 BOSS 战利品：神话宝箱",
            "desc": "你击败了第二阶段的守护者！一尊散发着七彩神圣微光的【神话宝箱】缓缓升起。请选择你要继承的一件神话秘宝：",
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
                data = {"items": [], "coop_done": True, "coop_downed": True, "title": "神话宝箱", "desc": "你处于倒地状态。"}
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
                "boss_name": run.node_data.get("boss_name", "虚空之门·尤格-索托斯"),
                "coop_notices": ["🎉 全队击败了先古的超最终BOSS【虚空之门·尤格-索托斯】！"],
            }
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
                    "coop_notices": ["🎉 全队击败了守关BOSS，取得了胜利！"],
                }
                return
            self.init_coop_boss_chest(run)
            return
        self.init_coop_rewards(run, difficulty)

    def handle_battle_turn_end(self, run):
        if not run.player or run.player.downed:
            if self.is_all_downed(run):
                run.coop_end_reason = "全队阵亡，联机牌局结束。"
                settle_msg = self.save_manager.settle_coop_game_and_delete(run.user_id, run, is_victory=False)
                return f"💀 全队阵亡，当前联机牌局结束。\n{settle_msg}"
            return "💀 你已倒地，只能观战。等待队友行动或结束回合。"
        uid = run.uid_for(run.player)
        logs = [self.battle_engine.card_player._end_player_phase(run, run.player)]
        ready = run.node_data.setdefault("turn_ready", {})
        ready[uid] = True
        alive = self._alive_uids(run)
        waiting = [u for u in alive if not ready.get(u, False)]
        if waiting:
            names = "、".join(run.players[u].name for u in waiting)
            count = len(alive) - len(waiting)
            self.save_manager.save_save(uid, run)
            return (
                f"{self.battle_engine._append_logs_to_res(run, '\n'.join(filter(None, logs)))}\n"
                f"⏳ 你已结束本回合行动，正在等待队友完成回合（当前已就绪：{count}/{len(alive)}：{names}）。"
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
                run.coop_end_reason = "全队阵亡，联机牌局结束。"
                settle_msg = self.save_manager.settle_coop_game_and_delete(viewer_uid, run, is_victory=False)
                return f"{enemy_logs}\n💀 全队阵亡，当前联机牌局结束。\n{settle_msg}"
            self.handle_coop_battle_win(run)
            self.save_manager.save_save(viewer_uid, run)
            return self.battle_engine._append_logs_to_res(run, f"{enemy_logs}\n🎉 战斗胜利！敌方单位已被全部击败。")
        if self.is_all_downed(run):
            run.coop_end_reason = "全队阵亡，联机牌局结束。"
            settle_msg = self.save_manager.settle_coop_game_and_delete(viewer_uid, run, is_victory=False)
            return f"{enemy_logs}\n💀 全队阵亡，当前联机牌局结束。\n{settle_msg}"
        run.node_data.pop("coop_wipe", None)
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
            run.coop_end_reason = "全队阵亡，联机牌局结束。"
            settle_msg = self.save_manager.settle_coop_game_and_delete(viewer_uid, run, is_victory=False)
            return f"{enemy_logs}\n{joined}\n💀 全队阵亡，当前联机牌局结束。\n{settle_msg}"
        self.battle_engine._roll_enemy_intent(run)
        self.assign_enemy_targets(run)
        run.node_data["cards_played_this_turn"] = 0
        self.save_manager.save_save(viewer_uid, run)
        result = f"{enemy_logs}\n{joined}\n🔄 全体存活队员已结束回合，进入第 {run.node_data['turn_count']} 回合。"
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

    def enemy_turn(self, run, controller):
        logs = []
        pending = run.node_data.get("pending_transitions", {})
        if pending:
            for enemy in list(run.enemies):
                if enemy.name in pending:
                    target_phase = pending.pop(enemy.name)
                    from ..entities import get_enemy_template
                    template = get_enemy_template(enemy.name)
                    if hasattr(template, "apply_phase_transition"):
                        template.apply_phase_transition(run, enemy, target_phase, self.battle_engine, logs)
            run.node_data["pending_transitions"] = pending
        decay_enemies = []
        for index, enemy in enumerate(run.enemies):
            if enemy.hp > 0 and enemy.shield > 0:
                lost = enemy.shield - (enemy.shield // 2)
                enemy.shield = enemy.shield // 2
                if lost > 0:
                    decay_enemies.append(f"【{enemy.name}】失去 {lost} 点护盾")
                    from ..models.events import ShieldDecayEvent
                    self.battle_engine.event_bus.dispatch(ShieldDecayEvent(run, f"e{index + 1}", lost))
            else:
                enemy.shield = 0
        if decay_enemies:
            logs.append("🛡️ 护盾流失：" + "，".join(decay_enemies))
        from ..models.events import TurnStartEvent, TurnEndEvent
        self.battle_engine.event_bus.dispatch(TurnStartEvent(run, is_player=False))
        viewer = run.player
        viewer_uid = run.user_id
        from ..entities import get_enemy_template
        for index, enemy in enumerate(list(run.enemies), 1):
            if enemy.hp <= 0:
                continue
            if enemy.actions == 0 and enemy.bonus_actions == 0:
                continue
            template = get_enemy_template(enemy.name)
            for intent in list(enemy.intents):
                if enemy.hp <= 0:
                    break
                if intent.cancelled:
                    continue
                if intent.cost_a > 0 and enemy.actions < intent.cost_a:
                    logs.append(f"⚠️ 【{enemy.name}】因动作点（A）不足，取消了意图【{intent.desc}】。")
                    intent.cancelled = True
                    intent.cancelled_desc = "已取消 (动作点不足)"
                    continue
                if intent.cost_ba > 0 and enemy.bonus_actions < intent.cost_ba:
                    logs.append(f"⚠️ 【{enemy.name}】因附赠动作点（BA）不足，取消了意图【{intent.desc}】。")
                    intent.cancelled = True
                    intent.cancelled_desc = "已取消 (动作点不足)"
                    continue
                enemy.actions = max(0, enemy.actions - intent.cost_a)
                enemy.bonus_actions = max(0, enemy.bonus_actions - intent.cost_ba)
                if intent.type == "phase_transition":
                    logs.append(f"⏳ 【{enemy.name}】正在进行【{intent.desc.split(' (')[0]}】！此回合免疫所有伤害。")
                    continue
                target = self._pick_enemy_target(run, index, intent, viewer_uid)
                target_uids = self._alive_uids(run) if target == "ALL" else [target]
                for uid in target_uids:
                    player = run.players.get(uid)
                    if player is None or player.downed or player.hp <= 0:
                        continue
                    run.player = player
                    run.user_id = uid
                    run.node_data["coop_damage_target_uid"] = uid
                    run.node_data["coop_damage_aoe"] = target == "ALL"
                    run.node_data["current_acting_enemy_idx"] = run.enemies.index(enemy) if enemy in run.enemies else index - 1
                    try:
                        template.execute_intent(run, self.battle_engine, enemy, intent, logs)
                    finally:
                        run.node_data.pop("current_acting_enemy_idx", None)
                        run.player = viewer
                        run.user_id = viewer_uid
                if self.is_all_downed(run):
                    logs.append("💀 全队均已倒地！")
                    break
            if self.is_all_downed(run):
                break
        self.battle_engine.event_bus.dispatch(TurnEndEvent(run, is_player=False))
        run.node_data.pop("coop_damage_aoe", None)
        run.node_data.pop("coop_damage_target_uid", None)
        for player in run.players.values():
            player.buffs[:] = [buff for buff in player.buffs if buff.id != "coop_aegis"]
        for enemy in run.enemies:
            enemy.actions = enemy.max_actions
            enemy.bonus_actions = enemy.max_bonus_actions
        return "\n".join(logs)
