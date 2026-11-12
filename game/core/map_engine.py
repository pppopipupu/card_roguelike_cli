import random
from typing import Optional, List, Dict
from ..models.state import GameRun, PlayerState, EnemyState, MinionState, AmuletState, Card
from ..data.map_config import MapConfig
from ..data.corpse_config import CorpseConfig
from ..data.balance_config import (
    LIFE_MERCHANT_MAX_PER_RUN,
    LIFE_MERCHANT_STAGE_CONFIG,
    MAP_ANCIENT_OPTION_SLOTS,
    MAP_ANCIENT_RELIC_CHOICES,
    MAP_BRANCH_MAX,
    MAP_BRANCH_MIN,
    MAP_GHOST_DEFAULT_MAX_HP,
    MAP_LUCKY_COIN_GOLD,
    MAP_TAX_CONTRACT_GOLD,
    MAP_TREASURE_ALWAYS_EXTRA_STAGE,
    MAP_TREASURE_EXTRA_LAYER_COUNT,
    MAP_TREASURE_EXTRA_LAYER_STAGE,
    MAP_TREASURE_EXTRA_LAYER_TOTAL,
    MAP_TREASURE_LAYER_COUNT,
    MAP_TREASURE_TOTAL_CHOICES,
    MAP_WIDTH_CHOICES,
    MAP_WIDTH_WEIGHTS,
)
from ..data.locale_data import get_locale_text
from .explore_engine import ExploreEngine

class MapEngine:
    def __init__(self, save_manager, battle_engine):
        self.save_manager = save_manager
        self.battle_engine = battle_engine
        self.explore_engine = ExploreEngine(save_manager, self)

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
                ]
                cards_pool.append({"type": "contract", "relic": "blind_spot", "card": "break_limits"})
                cards_pool.append({"type": "contract", "relic": "blind_spot", "card": "unmined_gem"})
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
                ]
                cards_pool.append({"type": "contract", "relic": "shadow_curse", "card": "break_limits"})
                cards_pool.append({"type": "contract", "relic": "shadow_curse", "card": "unmined_gem"})
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
                ]
                cards_pool.append({"type": "contract", "relic": "blind_spot", "card": "break_limits"})
                cards_pool.append({"type": "contract", "relic": "blind_spot", "card": "unmined_gem"})
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
                ]
                cards_pool.append({"type": "contract", "relic": "shadow_curse", "card": "break_limits"})
                cards_pool.append({"type": "contract", "relic": "shadow_curse", "card": "unmined_gem"})
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
                ]
                cards_pool.append({"type": "contract", "relic": "glacier_chill", "card": "break_limits"})
                cards_pool.append({"type": "contract", "relic": "glacier_chill", "card": "unmined_gem"})
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

    def enter_next_stage(self, run: GameRun):
        from .battle.party_battle import revive_downed_players
        from .party_coordinator import apply_and_scope, attach_notices, collect_notices, restore_player, swap_player
        caller = run.user_id
        leader = run.leader_id or (run.party_order[0] if run.party_order else caller)
        leader_player = run.players.get(leader) or run.player
        carried = collect_notices(run)
        revived = revive_downed_players(run)
        for uid, text in revived.items():
            carried.setdefault(uid, []).append(text)
        target_stage = max((run.players[u].stage for u in run.party_order if u in run.players), default=run.player.stage) + 1
        admin_cfg = self.save_manager.load_admin_config() if hasattr(self.save_manager, "load_admin_config") else {}
        icerainboww_enabled = admin_cfg.get("icerainboww_enabled", True)
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
            if target_stage > 1 and not getattr(player, "is_mercenary", False) and hasattr(self.save_manager, "record_stage_passed"):
                self.save_manager.record_stage_passed(uid)
            if "espresso_relic" in player.relics:
                player.relics.remove("espresso_relic")
            if "lucky_coin" in player.relics:
                player.gold += MAP_LUCKY_COIN_GOLD
            if "tax_contract" in player.relics:
                player.gold = max(0, player.gold - MAP_TAX_CONTRACT_GOLD)
        if target_stage == 1:
            views = {}
            ready = {}
            for uid in run.party_order:
                player = run.players.get(uid)
                if player is None:
                    continue
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
            attach_notices(run, carried, caller)
            apply_and_scope(run, caller)
            return
        previous, previous_user = swap_player(run, leader_player)
        if target_stage in MapConfig.CAFE_STAGES:
            from .cafe_engine import CafeEngine
            CafeEngine(self.save_manager, self).init_cafe(run, persist=False)
        elif target_stage in MapConfig.BOSS_STAGES:
            run.node_type = "battle"
            self.battle_engine._init_battle_node(run, "boss")
            run.node_data["coop_node_type"] = "battle"
        else:
            if target_stage in MapConfig.STAGE_NETWORKS:
                s_start, s_end = MapConfig.STAGE_NETWORKS[target_stage]
                self._generate_map_network(run, s_start, s_end)
            run.node_type = "map_select"
            self._build_map_options(run)
            run.node_data["coop_node_type"] = "map_select"
        restore_player(run, previous, previous_user)
        attach_notices(run, carried, caller)
        run.node_data["votes"] = {}
        apply_and_scope(run, caller)

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
    def _build_map_options(self, run: GameRun):
        p = run.player
        nodes_layer = run.map_data.get("nodes", {}).get(str(p.stage), [])
        curr_id = run.map_data.get("current_node_id")
        opts = []
        if not curr_id:
            opts = nodes_layer
        else:
            nodes_dict = {}
            for layer in run.map_data.get("nodes", {}).values():
                for node in layer:
                    nodes_dict[node["id"]] = node
            curr_node = nodes_dict.get(curr_id)
            if curr_node:
                next_ids = curr_node.get("next", [])
                opts = [nodes_dict[nid] for nid in next_ids if nid in nodes_dict]
        if not opts and nodes_layer:
            opts = nodes_layer
        options_data = []
        if run.player_count() > 1:
            desc_map = {
                "battle": get_locale_text("i18n_map_cafe.node_desc_coop_battle"),
                "elite": get_locale_text("i18n_map_cafe.node_desc_coop_elite"),
                "event": get_locale_text("i18n_map_cafe.node_desc_coop_event"),
                "shop": get_locale_text("i18n_map_cafe.node_desc_coop_shop"),
                "rest": get_locale_text("i18n_map_cafe.node_desc_coop_rest"),
                "treasure": get_locale_text("i18n_map_cafe.node_desc_coop_treasure"),
                "life_merchant": get_locale_text("i18n_map_cafe.node_desc_coop_life_merchant"),
                "boss": get_locale_text("i18n_map_cafe.node_desc_coop_boss")
            }
        else:
            desc_map = {
                "battle": get_locale_text("i18n_map_cafe.node_desc_battle"),
                "elite": get_locale_text("i18n_map_cafe.node_desc_elite"),
                "event": get_locale_text("i18n_map_cafe.node_desc_event"),
                "shop": get_locale_text("i18n_map_cafe.node_desc_shop"),
                "rest": get_locale_text("i18n_map_cafe.node_desc_rest"),
                "treasure": get_locale_text("i18n_map_cafe.node_desc_treasure"),
                "life_merchant": get_locale_text("i18n_map_cafe.node_desc_life_merchant"),
                "boss": get_locale_text("i18n_map_cafe.node_desc_boss")
            }
        emoji_map = {
            "battle": get_locale_text("i18n_map_cafe.node_name_battle"),
            "elite": get_locale_text("i18n_map_cafe.node_name_elite"),
            "event": get_locale_text("i18n_map_cafe.node_name_event"),
            "shop": get_locale_text("i18n_map_cafe.node_name_shop"),
            "rest": get_locale_text("i18n_map_cafe.node_name_rest"),
            "treasure": get_locale_text("i18n_map_cafe.node_name_treasure"),
            "life_merchant": get_locale_text("i18n_map_cafe.node_name_life_merchant"),
            "boss": get_locale_text("i18n_map_cafe.node_name_boss")
        }
        for o in opts:
            options_data.append({
                "node_id": o["id"],
                "node_type": o["type"],
                "desc": f"{emoji_map.get(o['type'], o['type'])} ({desc_map.get(o['type'], o['type'])})"
            })
        run.node_data = {
            "options": list(options_data),
            "base_options": list(options_data),
        }
        self.sync_corpse_options(run)

    def sync_corpse_options(self, run: GameRun) -> bool:
        if run is None or run.node_type != "map_select":
            return False
        if run.player_count() > 1:
            return False
        data = run.node_data if run.node_data is not None else {}
        base = data.get("base_options")
        if base is None:
            base = [
                option for option in data.get("options", [])
                if option.get("node_type") != "corpse"
            ]
            data["base_options"] = list(base)
        options = list(base)
        registry = getattr(self.save_manager, "corpses", None)
        corpses = registry.list_at_stage(
            run.player.stage, exclude_user=run.user_id
        ) if registry is not None else []
        for corpse in corpses:
            options.append({
                "node_id": f"corpse_{corpse.get('id')}",
                "node_type": "corpse",
                "corpse_id": corpse.get("id"),
                "desc": get_locale_text(
                    "i18n_map_cafe.corpse_option_desc",
                    player_name=corpse.get("player_name", get_locale_text("i18n_map_cafe.default_player_name")),
                    cause=corpse.get("cause", get_locale_text("i18n_map_cafe.default_cause")),
                ),
            })
        changed = options != data.get("options")
        data["options"] = options
        run.node_data = data
        return changed

    def return_to_map_select(self, run: GameRun):
        run.node_type = "map_select"
        run.enemies.clear()
        run.node_data = {}
        self._build_map_options(run)

    def _generate_map_network(self, run: GameRun, start_s: int, end_s: int):
        nodes = {}
        for s in range(start_s, end_s + 1):
            nodes[str(s)] = []
        
        if "total_treasures" not in run.map_data:
            run.map_data["total_treasures"] = random.choice(MAP_TREASURE_TOTAL_CHOICES)
        
        tot = run.map_data["total_treasures"]
        treasure_layers = []
        if start_s in MapConfig.TREASURE_LAYERS_CONFIG:
            t_start, t_end = MapConfig.TREASURE_LAYERS_CONFIG[start_s]
            num_t = MAP_TREASURE_LAYER_COUNT
            if (start_s == MAP_TREASURE_EXTRA_LAYER_STAGE and tot == MAP_TREASURE_EXTRA_LAYER_TOTAL) or start_s == MAP_TREASURE_ALWAYS_EXTRA_STAGE:
                num_t = MAP_TREASURE_EXTRA_LAYER_COUNT
            treasure_layers = random.sample(range(t_start, t_end), num_t)

        types_pool = ["battle", "event", "shop", "elite", "rest"]
        for s in range(start_s, end_s + 1):
            s_str = str(s)
            if s in MapConfig.BOSS_STAGES:
                nodes[s_str].append({
                    "id": f"{s}_0",
                    "type": "boss",
                    "next": []
                })
            else:
                width = random.choices(MAP_WIDTH_CHOICES, weights=MAP_WIDTH_WEIGHTS)[0]
                treasure_idx = random.randint(0, width - 1) if s in treasure_layers else -1
                for i in range(width):
                    if i == treasure_idx:
                        ntype = "treasure"
                    else:
                        ntype = random.choice(types_pool)
                    nodes[s_str].append({
                        "id": f"{s}_{i}",
                        "type": ntype,
                        "next": []
                    })
        
        for s in range(start_s, end_s):
            curr_layer = nodes[str(s)]
            next_layer = nodes[str(s+1)]
            
            if len(next_layer) == 1:
                for cn in curr_layer:
                    cn["next"] = [next_layer[0]["id"]]
            elif len(curr_layer) == 1:
                curr_layer[0]["next"] = [nn["id"] for nn in next_layer]
            else:
                for i, cn in enumerate(curr_layer):
                    center = round(i * (len(next_layer) - 1) / max(1, len(curr_layer) - 1))
                    allowed = []
                    for offset in (-1, 0, 1, -2, 2):
                        idx = center + offset
                        if 0 <= idx < len(next_layer):
                            nid = next_layer[idx]["id"]
                            if nid not in allowed:
                                allowed.append(nid)
                        if len(allowed) >= 3 and abs(offset) >= 1:
                            break
                    branch_count = min(len(allowed), random.randint(MAP_BRANCH_MIN, MAP_BRANCH_MAX))
                    cn["next"] = random.sample(allowed, branch_count)
                
                for nn in next_layer:
                    nn_id = nn["id"]
                    has_pre = False
                    for cn in curr_layer:
                        if nn_id in cn["next"]:
                            has_pre = True
                            break
                    if not has_pre:
                        nn_idx = int(nn_id.split("_")[1])
                        best_i = round(nn_idx * (len(curr_layer) - 1) / max(1, len(next_layer) - 1))
                        best_i = max(0, min(len(curr_layer) - 1, best_i))
                        curr_layer[best_i]["next"].append(nn_id)
                        curr_layer[best_i]["next"] = list(set(curr_layer[best_i]["next"]))

        self._place_life_merchant(run, nodes, start_s)
        run.map_data["nodes"] = nodes
        run.map_data["current_node_id"] = None

    def _place_life_merchant(self, run: GameRun, nodes: dict, start_s: int):
        cfg = LIFE_MERCHANT_STAGE_CONFIG.get(start_s)
        if not cfg:
            return
        placed = int(run.map_data.get("life_merchant_count", 0) or 0)
        if placed >= LIFE_MERCHANT_MAX_PER_RUN:
            return
        s_start, s_end, chance = cfg
        if start_s == 27 and placed == 0:
            chance = 1.0
        if random.random() >= chance:
            return
        candidate_layers = []
        for s in range(s_start, s_end):
            layer = nodes.get(str(s), [])
            non_treasure = [nd for nd in layer if nd.get("type") not in ("treasure", "boss")]
            if non_treasure:
                candidate_layers.append(non_treasure)
        if not candidate_layers:
            return
        chosen_pool = random.choice(candidate_layers)
        chosen_node = random.choice(chosen_pool)
        chosen_node["type"] = "life_merchant"
        run.map_data["life_merchant_count"] = placed + 1

    def choose_map_node(self, run: GameRun, option_idx: int) -> str:
        options = run.node_data.get("options", [])
        if option_idx < 1 or option_idx > len(options):
            return get_locale_text("i18n_map_cafe.err_invalid_branch_idx")
        from .party_coordinator import vote_option
        vote_result = vote_option(run, run.user_id, option_idx, "i18n_explore_core.vote_recorded")
        if vote_result is not None:
            self.save_manager.save_save(run.user_id, run)
            return vote_result
        run.node_data["votes"] = {}
        chosen = options[option_idx - 1]
        node_type = chosen["node_type"]
        node_id = chosen["node_id"]

        if node_type == "corpse":
            corpse_id = chosen.get("corpse_id")
            corpse = self.save_manager.corpses.get(corpse_id)
            if not corpse or corpse.get("claimed_by"):
                self.sync_corpse_options(run)
                self.save_manager.save_save(run.user_id, run)
                return get_locale_text("i18n_map_cafe.err_corpse_claimed")
            dead_name = str(corpse.get("player_name", get_locale_text("i18n_map_cafe.default_player_name")))
            cause = str(corpse.get("cause", get_locale_text("i18n_map_cafe.default_cause")))
            run.node_type = "battle"
            run.node_data = {
                "corpse_battle": True,
                "corpse_id": corpse.get("id"),
                "corpse_stage": int(corpse.get("stage", run.player.stage)),
                "corpse_dead_name": dead_name,
                "corpse_cause": cause,
                "ghost_name": get_locale_text("i18n_map_cafe.ghost_name", dead_name=dead_name),
                "ghost_max_hp": max(CorpseConfig.GHOST_MIN_HP, int(corpse.get("max_hp", MAP_GHOST_DEFAULT_MAX_HP) or MAP_GHOST_DEFAULT_MAX_HP)),
                "ghost_deck": list(corpse.get("deck", [])),
            }
            self.battle_engine._init_battle_node(run, "ghost")
            self.save_manager.save_save(run.user_id, run)
            return self.battle_engine._append_logs_to_res(
                run,
                get_locale_text("i18n_map_cafe.corpse_battle_log", dead_name=dead_name, cause=cause)
            )

        if node_type in ("battle", "elite", "boss"):
            run.node_type = "battle"
        else:
            run.node_type = node_type
        run.map_data["current_node_id"] = node_id
        run.node_data.clear()
        
        if node_type == "battle" or node_type == "boss":
            diff = "boss" if node_type == "boss" else "normal"
            self.battle_engine._init_battle_node(run, diff)
            name = run.enemies[0].name if run.enemies else get_locale_text("i18n_map_cafe.unknown_enemy")
            num_enemies = len(run.enemies)
            self.save_manager.save_save(run.user_id, run)
            return self.battle_engine._append_logs_to_res(run, get_locale_text("i18n_map_cafe.choose_battle_log", desc=chosen['desc'], num_enemies=num_enemies, name=name))
        elif node_type == "elite":
            self.battle_engine._init_battle_node(run, "elite")
            name = run.enemies[0].name if run.enemies else get_locale_text("i18n_map_cafe.unknown_enemy")
            num_enemies = len(run.enemies)
            self.save_manager.save_save(run.user_id, run)
            return self.battle_engine._append_logs_to_res(run, get_locale_text("i18n_map_cafe.choose_elite_log", desc=chosen['desc'], num_enemies=num_enemies, name=name))
        elif node_type == "event":
            self.explore_engine._init_event_node(run)
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_map_cafe.choose_event_log", desc=chosen['desc'])
        elif node_type == "shop":
            self.explore_engine._init_shop_node(run)
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_map_cafe.choose_shop_log", desc=chosen['desc'])
        elif node_type == "rest":
            self.explore_engine._init_rest_node(run)
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_map_cafe.choose_rest_log", desc=chosen['desc'])
        elif node_type == "treasure":
            self.explore_engine._init_treasure_node(run)
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_map_cafe.choose_treasure_log", desc=chosen['desc'])
        elif node_type == "life_merchant":
            self.explore_engine._init_life_merchant_node(run)
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_map_cafe.choose_life_merchant_log", desc=chosen['desc'])
        return get_locale_text("i18n_map_cafe.err_unknown_node_type")

    def _init_event_node(self, run: GameRun):
        self.explore_engine._init_event_node(run)

    def _init_shop_node(self, run: GameRun):
        self.explore_engine._init_shop_node(run)

    def _init_treasure_node(self, run: GameRun):
        self.explore_engine._init_treasure_node(run)

    def choose_option(self, run: GameRun, option_idx: int, target: Optional[str] = None) -> str:
        if run.node_type == "battle":
            return get_locale_text("i18n_map_cafe.err_cannot_choose_in_battle")
        if run.node_type == "map_select":
            return self.choose_map_node(run, option_idx)
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
        if hasattr(self.save_manager, "load_admin_config"):
            admin_cfg = self.save_manager.load_admin_config()
        else:
            admin_cfg = {}
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
                "relic": available_relics[i % len(available_relics)]
            })
        run.node_data = {"options": options, "style": style}
