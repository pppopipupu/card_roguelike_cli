import random
from typing import Optional, List, Dict
from ..models.state import GameRun, PlayerState, EnemyState, MinionState, AmuletState, Card
from ..data.map_config import MapConfig
from ..data.corpse_config import CorpseConfig
from .explore_engine import ExploreEngine

class MapEngine:
    def __init__(self, save_manager, battle_engine):
        self.save_manager = save_manager
        self.battle_engine = battle_engine
        self.explore_engine = ExploreEngine(save_manager, self)

    def enter_next_stage(self, run: GameRun):
        if getattr(run, "coop_id", ""):
            from .coop_engine import CoopEngine
            CoopEngine(self.save_manager, self.battle_engine).enter_next_stage(run)
            return
        self._enter_next_stage_solo(run)

    def _enter_next_stage_solo(self, run: GameRun):
        p = run.player
        p.stage += 1
        if "espresso_relic" in p.relics:
            p.relics.remove("espresso_relic")
        if hasattr(self.save_manager, "load_admin_config"):
            admin_cfg = self.save_manager.load_admin_config()
        else:
            admin_cfg = {}
        icerainboww_enabled = admin_cfg.get("icerainboww_enabled", True)
        if p.stage > 1:
            self.save_manager.record_stage_passed(run.user_id)
        p.shield = 0
        p.minions.clear()
        p.amulets.clear()
        p.abilities.clear()
        run.enemies.clear()
        run.node_data.clear()

        if "lucky_coin" in p.relics:
            p.gold += 5
        if "tax_contract" in p.relics:
            p.gold = max(0, p.gold - 6)

        if p.stage == 1:
            run.node_type = "start_ancient"
            stats = self.save_manager.load_stats(run.user_id)
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
                        {"type": "double", "relic": "ancient_page"}
                    ]
                    cards_pool = [
                        {"type": "contract", "relic": "rust_shackle", "card": "demon_form"},
                        {"type": "contract", "relic": "fool_oath", "card": "impervious"},
                        {"type": "contract", "relic": "blind_spot", "card": "demon_form"},
                        {"type": "contract", "relic": "tax_contract", "card": "impervious"}
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
                        {"type": "double", "relic": "abyss_contract"}
                    ]
                    cards_pool = [
                        {"type": "contract", "relic": "shadow_curse", "card": "abyss_collapse"},
                        {"type": "contract", "relic": "shadow_curse", "card": "demon_contract"},
                        {"type": "contract", "relic": "shadow_curse", "card": "abyss_erosion"},
                        {"type": "contract", "relic": "shadow_curse", "card": "abyss_altar"}
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
                        {"type": "double", "relic": "ancient_page"}
                    ]
                    cards_pool = [
                        {"type": "contract", "relic": "rust_shackle", "card": "doomsday_judgment"},
                        {"type": "contract", "relic": "fool_oath", "card": "time_warp"},
                        {"type": "contract", "relic": "wither_seed", "card": "magic_network"},
                        {"type": "contract", "relic": "blind_spot", "card": "meteor_swarm"},
                        {"type": "contract", "relic": "tax_contract", "card": "archmage_wish"}
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
                        {"type": "double", "relic": "abyss_contract"}
                    ]
                    cards_pool = [
                        {"type": "contract", "relic": "shadow_curse", "card": "abyss_collapse"},
                        {"type": "contract", "relic": "shadow_curse", "card": "demon_contract"},
                        {"type": "contract", "relic": "shadow_curse", "card": "abyss_erosion"},
                        {"type": "contract", "relic": "shadow_curse", "card": "abyss_altar"}
                    ]
                    cards_pool.append({"type": "contract", "relic": "shadow_curse", "card": "break_limits"})
                    cards_pool.append({"type": "contract", "relic": "shadow_curse", "card": "unmined_gem"})
                    if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
                        cards_pool.append({"type": "contract", "relic": "shadow_curse", "card": "minion_icerainboww"})
                else:
                    relics_pool = [
                        {"type": "double", "relic": "glacier_armor"},
                        {"type": "double", "relic": "unstable_crystal"},
                        {"type": "double", "relic": "vampiric_touch"},
                        {"type": "double", "relic": "glacier_core"}
                    ]
                    cards_pool = [
                        {"type": "contract", "relic": "glacier_chill", "card": "frost_nova"},
                        {"type": "contract", "relic": "glacier_chill", "card": "glacier_fortress"},
                        {"type": "contract", "relic": "glacier_chill", "card": "glacier_tempest"}
                    ]
                    cards_pool.append({"type": "contract", "relic": "glacier_chill", "card": "break_limits"})
                    cards_pool.append({"type": "contract", "relic": "glacier_chill", "card": "unmined_gem"})
                    if getattr(stats, "killed_icerainboww", False) and icerainboww_enabled:
                        cards_pool.append({"type": "contract", "relic": "glacier_chill", "card": "minion_icerainboww"})
            
            num_relics = random.choice([1, 2])
            selected_relics = random.sample(relics_pool, min(len(relics_pool), num_relics))
            selected_cards = random.sample(cards_pool, min(len(cards_pool), 3 - len(selected_relics)))
            from ..models.state import check_and_replace_fireball
            for item in selected_cards:
                if "card" in item:
                    item["card"] = check_and_replace_fireball(run, item["card"])
            options = selected_relics + selected_cards
            random.shuffle(options)
            options.append({"type": "double", "relic": "trash_mountain"})
            run.node_data = {"options": options, "style": style}
        elif p.stage in MapConfig.CAFE_STAGES:
            from .cafe_engine import CafeEngine
            cafe = CafeEngine(self.save_manager, self)
            cafe.init_cafe(run)
        elif p.stage in MapConfig.BOSS_STAGES:
            run.node_type = "battle"
            self.battle_engine._init_battle_node(run, "boss")
        else:
            if p.stage in MapConfig.STAGE_NETWORKS:
                s_start, s_end = MapConfig.STAGE_NETWORKS[p.stage]
                self._generate_map_network(run, s_start, s_end)
            run.node_type = "map_select"
            self._build_map_options(run)

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
        if getattr(run, "coop_id", ""):
            desc_map = {
                "battle": "遭遇战 (遇到双倍数量的普通敌人)",
                "elite": "精英战 (遭遇双倍数量的强力敌人，获胜金币更多)",
                "event": "神秘事件 (可能获得宝物或遭遇危险)",
                "shop": "奇妙商店 (各自独立货架，购买强力卡牌、遗物或移除卡牌)",
                "rest": "篝火营地 (恢复生命值、冥想领悟或救治队友)",
                "treasure": "古老宝箱 (献祭卡牌以获取稀有遗物及宝藏)",
                "boss": "首领战 (击败双倍数量的守关首领)"
            }
        else:
            desc_map = {
                "battle": "遭遇战 (遇到 1~3 个普通的敌人)",
                "elite": "精英战 (遭遇强力敌人，获胜金币更多)",
                "event": "神秘事件 (可能获得宝物或遭遇危险)",
                "shop": "奇妙商店 (购买强力卡牌、遗物或移除卡牌)",
                "rest": "篝火营地 (恢复生命值或冥想领悟卡牌)",
                "treasure": "古老宝箱 (献祭卡牌以获取稀有遗物及宝藏)",
                "boss": "首领战 (击败守关的首领)"
            }
        emoji_map = {
            "battle": "遭遇战",
            "elite": "精英战",
            "event": "神秘事件",
            "shop": "奇妙商店",
            "rest": "篝火营地",
            "treasure": "古老宝箱",
            "boss": "首领战"
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
        if getattr(run, "coop_id", ""):
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
                "desc": (
                    f"尸体：{corpse.get('player_name', '玩家')}"
                    f"（{corpse.get('cause', '死因不明')}）"
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
            run.map_data["total_treasures"] = random.choice([4, 5])
        
        tot = run.map_data["total_treasures"]
        treasure_layers = []
        if start_s in MapConfig.TREASURE_LAYERS_CONFIG:
            t_start, t_end = MapConfig.TREASURE_LAYERS_CONFIG[start_s]
            num_t = 2 if (start_s == 2 and tot == 5) or start_s == 14 else 1
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
                width = random.choices([2, 3, 4], weights=[0.1, 0.5, 0.4])[0]
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
                    allowed = []
                    for offset in (-1, 0, 1):
                        idx = i + offset
                        if 0 <= idx < len(next_layer):
                            allowed.append(next_layer[idx]["id"])
                    cn["next"] = random.sample(allowed, min(len(allowed), random.randint(1, 2)))
                
                for nn in next_layer:
                    nn_id = nn["id"]
                    has_pre = False
                    for cn in curr_layer:
                        if nn_id in cn["next"]:
                            has_pre = True
                            break
                    if not has_pre:
                        best_i = min(len(curr_layer)-1, int(nn_id.split("_")[1]))
                        curr_layer[best_i]["next"].append(nn_id)
                        curr_layer[best_i]["next"] = list(set(curr_layer[best_i]["next"]))
                        
        run.map_data["nodes"] = nodes
        run.map_data["current_node_id"] = None

    def choose_map_node(self, run: GameRun, option_idx: int) -> str:
        options = run.node_data.get("options", [])
        if option_idx < 1 or option_idx > len(options):
            return "❌ 无效的分支序号。"
        if getattr(run, "coop_id", ""):
            from .coop_engine import CoopEngine
            coop = CoopEngine(self.save_manager, self.battle_engine)
            vote_result = coop.vote_map_node(run, run.user_id, option_idx)
            if vote_result is not None:
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
                return "❌ 这具尸体已经被其他玩家搜刮，尸体节点消失了。"
            dead_name = str(corpse.get("player_name", "玩家"))
            cause = str(corpse.get("cause", "死因不明"))
            run.node_type = "battle"
            run.node_data = {
                "corpse_battle": True,
                "corpse_id": corpse.get("id"),
                "corpse_stage": int(corpse.get("stage", run.player.stage)),
                "corpse_dead_name": dead_name,
                "corpse_cause": cause,
                "ghost_name": f"冤魂·{dead_name}",
                "ghost_max_hp": max(CorpseConfig.GHOST_MIN_HP, int(corpse.get("max_hp", 60) or 60)),
                "ghost_deck": list(corpse.get("deck", [])),
            }
            self.battle_engine._init_battle_node(run, "ghost")
            self.save_manager.save_save(run.user_id, run)
            return self.battle_engine._append_logs_to_res(
                run,
                f"你踏入【尸体：{dead_name}】的阴影。死因：{cause}。\n"
                f"冤魂从遗体中站起，手中浮现着死者生前的卡组。进入冤魂战！"
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
            name = run.enemies[0].name if run.enemies else "未知"
            num_enemies = len(run.enemies)
            self.save_manager.save_save(run.user_id, run)
            return self.battle_engine._append_logs_to_res(run, f"你选择前往【{chosen['desc']}】。前方出现了 {num_enemies} 个敌人，领头的是【{name}】！进入战斗。")
        elif node_type == "elite":
            self.battle_engine._init_battle_node(run, "elite")
            name = run.enemies[0].name if run.enemies else "未知"
            num_enemies = len(run.enemies)
            self.save_manager.save_save(run.user_id, run)
            return self.battle_engine._append_logs_to_res(run, f"你选择前往【{chosen['desc']}】。前方出现了 {num_enemies} 个强力精英，领头的是【{name}】！进入战斗。")
        elif node_type == "event":
            self.explore_engine._init_event_node(run)
            self.save_manager.save_save(run.user_id, run)
            return f"你选择前往【{chosen['desc']}】。你遇到了一个神秘事件..."
        elif node_type == "shop":
            self.explore_engine._init_shop_node(run)
            self.save_manager.save_save(run.user_id, run)
            return f"你选择前往【{chosen['desc']}】。你来到了奇妙商店，店主热情地向你招手。"
        elif node_type == "rest":
            self.explore_engine._init_rest_node(run)
            self.save_manager.save_save(run.user_id, run)
            return f"你选择前往【{chosen['desc']}】。篝火在噼啪作响，你可以在此整顿休息。"
        elif node_type == "treasure":
            self.explore_engine._init_treasure_node(run)
            self.save_manager.save_save(run.user_id, run)
            return f"你选择前往【{chosen['desc']}】。你来到了古老宝箱前。"
        return "❌ 未知节点类型。"

    def _init_event_node(self, run: GameRun):
        self.explore_engine._init_event_node(run)

    def _init_shop_node(self, run: GameRun):
        self.explore_engine._init_shop_node(run)

    def _init_treasure_node(self, run: GameRun):
        self.explore_engine._init_treasure_node(run)

    def choose_option(self, run: GameRun, option_idx: int, target: Optional[str] = None) -> str:
        if run.node_type == "battle":
            return "❌ 战斗中无法使用选择命令。"
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
        stats = self.save_manager.load_stats(run.user_id)
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
        for i in range(3):
            options.append({
                "type": "blessing",
                "card": check_and_replace_fireball(run, legends_pool[i % len(legends_pool)]),
                "relic": available_relics[i % len(available_relics)]
            })
        options.append({"type": "double", "relic": "trash_mountain"})
        run.node_data = {"options": options, "style": style}
