import random
from typing import Any, Dict, List, Optional, Tuple
from .....data.world.npc_dialog import NPC_DIALOG_GRAPHS
from .....data.world.room_interact_data import ROOM_NPCS
from ....text.events import LocaleText, RenderedText, TextNode, locale_text
from ....text.pipeline import render_text_node
from .checks import DiceCheckEngine
from .conditions import eval_condition
from .effects import apply_effects
from .quest_hooks import get_quest_entry, has_active_quest_for_npc
from .registry import NpcDialogProvider, register_npc_provider
from .renderer import get_npc_display_name, serialize_outcome_nodes
from .state import NpcMemoryStore

NON_EXHAUSTING_CATEGORIES = frozenset({"recap", "leave"})
SPAR_INTERNAL_NODES = frozenset({"spar_npc_yield", "spar_execute_confirm", "spar_player_lost"})


@register_npc_provider("crpg_graph", priority=90)
class CrpgDialogProvider(NpcDialogProvider):
    def can_handle(self, run, npc_id: str) -> bool:
        return npc_id in NPC_DIALOG_GRAPHS

    def open_dialog(self, save_manager, run, room, coord: str, npc_id: str) -> Optional[dict]:
        graph = NPC_DIALOG_GRAPHS.get(npc_id)
        if graph is None:
            return None
        uid = run.user_id
        stats = NpcMemoryStore.load_stats(save_manager, uid)
        run_npc = NpcMemoryStore.ensure_initialized_run_npc(run, stats, uid, npc_id, graph)
        fm = getattr(run, "floor_map", None)
        cur_floor = getattr(fm, "floor_index", 1) if fm is not None else 1
        p_enc = NpcMemoryStore.ensure_player_encounter(run, npc_id, uid, room=room, coord=coord)
        if p_enc["talk_turns"] == 0:
            run_npc["met_count"] = int(run_npc.get("met_count", 0)) + 1
            run_npc["last_floor"] = cur_floor
            run_npc["last_coord"] = coord
            greetings = list(graph.get("greetings") or ())
            if greetings:
                p_enc["greeting_idx"] = random.randrange(len(greetings))
        entry_node = CrpgDialogEngine.resolve_entry_node(run, stats, uid, npc_id, graph, room=room, coord=coord)
        return {
            "npc_id": npc_id,
            "dialog_state": "start",
            "coord": coord,
            "provider": "crpg_graph",
            "node_id": entry_node,
            "last_outcome_nodes": [],
            "pending_return_node": "",
        }

    def render_content(self, run, save_manager=None) -> Optional[Tuple[str, str, List[str]]]:
        return CrpgDialogEngine.get_dialog_view(run, save_manager=save_manager)

    def handle_choice(self, map_engine, run, idx: int) -> Optional[str]:
        return CrpgDialogEngine.handle_choice(map_engine, run, idx)


class CrpgDialogEngine:
    @staticmethod
    def _build_ctx(run, stats, save_manager, uid: str, npc_id: str, graph: dict, room=None, coord: str = "") -> dict:
        fm = getattr(run, "floor_map", None)
        target_coord = coord or (fm.player_coords.get(uid, "") if fm is not None else "")
        if room is None and fm is not None and target_coord:
            room = fm.rooms.get(target_coord)
        run_bucket = NpcMemoryStore.ensure_run_bucket(run, uid)
        run_npc = NpcMemoryStore.ensure_initialized_run_npc(run, stats, uid, npc_id, graph)
        enc = NpcMemoryStore.ensure_encounter(run, npc_id, room=room, coord=target_coord)
        p_enc = NpcMemoryStore.ensure_player_encounter(run, npc_id, uid, room=room, coord=target_coord)
        return {
            "run": run,
            "stats": stats,
            "save_manager": save_manager,
            "uid": uid,
            "player": run.player,
            "npc_id": npc_id,
            "graph": graph,
            "room": room,
            "coord": target_coord,
            "run_bucket": run_bucket,
            "run_npc": run_npc,
            "enc": enc,
            "p_enc": p_enc,
        }

    @staticmethod
    def _is_option_visible(opt: dict, ctx: dict) -> bool:
        if opt.get("once_per_encounter"):
            if str(opt.get("id", "")) in set(ctx["p_enc"].get("consumed_options") or ()):
                return False
        if opt.get("once_per_run"):
            flag = f"opt_run:{ctx['npc_id']}:{opt.get('id', '')}"
            if flag in set(ctx["run_npc"].get("known_flags") or ()):
                return False
        egroup = opt.get("exclusive_group")
        if egroup and str(egroup) in set(ctx["p_enc"].get("locked_groups") or ()):
            return False
        service_key = opt.get("service_key")
        if service_key:
            quotas = ctx["graph"].get("service_quotas") or {}
            limit = int(quotas.get(service_key, 1))
            used = int((ctx["p_enc"].get("service_uses") or {}).get(service_key, 0) or 0)
            if used >= limit:
                return False
        check_cfg = opt.get("check")
        if isinstance(check_cfg, dict):
            cid = str(check_cfg.get("check_id") or opt.get("id", ""))
            if cid and cid in (ctx["p_enc"].get("checked_nodes") or {}):
                return False
        vis = opt.get("visible_if")
        if vis and not eval_condition(vis, ctx):
            return False
        return True

    @staticmethod
    def _build_recap_options(ctx: dict) -> List[dict]:
        opts: List[dict] = []
        p_enc = ctx["p_enc"]
        for rec in list(p_enc.get("recap_entries") or ())[:2]:
            rid = str(rec.get("id", "recap"))
            lkey = str(rec.get("locale_key", ""))
            params = dict(rec.get("params") or {})
            opts.append(
                {
                    "id": f"__recap_{rid}",
                    "category": "recap",
                    "text_key": "i18n_npc_crpg_core.recap.opt_clue",
                    "tag_key": "i18n_npc_crpg_core.tags.recap",
                    "effects": [{"type": "message", "key": lkey, "params": params}],
                    "next_node": "exhausted_root",
                }
            )
        if len(opts) < 2 and has_active_quest_for_npc(ctx["run"], ctx.get("stats"), ctx["npc_id"]):
            from .....data.world.npc_dialog.quests import NPC_QUEST_CONFIG

            for qid, cfg in NPC_QUEST_CONFIG.items():
                if len(opts) >= 2:
                    break
                givers = set(cfg.get("turnin_npcs") or ()) | {cfg.get("giver_npc_id", "")}
                if ctx["npc_id"] not in givers:
                    continue
                qentry = get_quest_entry(ctx["run"], ctx.get("stats"), qid)
                if not qentry or qentry.get("status") != "active":
                    continue
                opts.append(
                    {
                        "id": f"__recap_quest_{qid}",
                        "category": "recap",
                        "text_key": "i18n_npc_crpg_core.recap.opt_quest",
                        "text_params": {"title": render_text_node(locale_text(str(cfg["title_key"])))},
                        "tag_key": "i18n_npc_crpg_core.tags.recap",
                        "effects": [
                            {
                                "type": "message",
                                "key": str(cfg.get("recap_key", "i18n_npc_crpg_core.recap.quest_progress")),
                                "params": {
                                    "progress": int(qentry.get("progress", 0)),
                                    "target": int(qentry.get("target", cfg.get("target", 1))),
                                },
                            }
                        ],
                        "next_node": "exhausted_root",
                    }
                )
        return opts

    @staticmethod
    def _has_active_content(graph: dict, node_id: str, ctx: dict, visited: Optional[set] = None) -> bool:
        if visited is None:
            visited = set()
        if node_id in visited:
            return False
        visited.add(node_id)
        node = (graph.get("nodes") or {}).get(node_id)
        if not isinstance(node, dict):
            return False
        for opt in node.get("options") or ():
            if not CrpgDialogEngine._is_option_visible(opt, ctx):
                continue
            cat = str(opt.get("category", "topic"))
            if cat not in NON_EXHAUSTING_CATEGORIES:
                nxt = str(opt.get("next_node") or "")
                if nxt and nxt in (graph.get("nodes") or {}) and opt.get("submenu_only"):
                    if CrpgDialogEngine._has_active_content(graph, nxt, ctx, visited):
                        return True
                    continue
                return True
        return False

    @staticmethod
    def resolve_entry_node(run, stats, uid: str, npc_id: str, graph: dict, room=None, coord: str = "") -> str:
        ctx = CrpgDialogEngine._build_ctx(run, stats, None, uid, npc_id, graph, room=room, coord=coord)
        enc_world = ctx["enc"].get("world") or {}
        if enc_world.get("departed") or enc_world.get("spared"):
            return "exhausted_root"
        if int(ctx["run_npc"].get("affinity", 0)) <= -4 and "hostile_root" in (graph.get("nodes") or {}):
            return "hostile_root"
        for rule in graph.get("entry_rules") or ():
            cond = rule.get("when")
            if cond and not eval_condition(cond, ctx):
                continue
            target = str(rule.get("node", "root"))
            if target in (graph.get("nodes") or {}):
                if target == "exhausted_root" or CrpgDialogEngine._has_active_content(graph, target, ctx):
                    return target
        base_root = "return_root" if int(ctx["p_enc"].get("talk_turns", 0)) > 0 and "return_root" in (graph.get("nodes") or {}) else "root"
        if CrpgDialogEngine._has_active_content(graph, base_root, ctx):
            return base_root
        return "exhausted_root"

    @staticmethod
    def _visible_options_for_node(node_id: str, graph: dict, ctx: dict) -> List[dict]:
        if node_id == "spar_npc_yield":
            return [
                {
                    "id": "__spar_spare",
                    "category": "topic",
                    "text_key": "i18n_npc_crpg_core.spar.opt_spare",
                    "effects": [{"type": "mark_spared"}, {"type": "message", "key": "i18n_npc_crpg_core.spar.spared_ok"}],
                    "next_node": "exhausted_root",
                },
                {
                    "id": "__spar_execute_ask",
                    "category": "challenge",
                    "text_key": "i18n_npc_crpg_core.spar.opt_execute_ask",
                    "next_node": "spar_execute_confirm",
                },
            ]
        if node_id == "spar_execute_confirm":
            return [
                {
                    "id": "__spar_execute_confirm",
                    "category": "challenge",
                    "text_key": "i18n_npc_crpg_core.spar.opt_execute_confirm",
                    "effects": [{"type": "execute_npc_kill"}],
                },
                {
                    "id": "__spar_execute_cancel",
                    "category": "topic",
                    "text_key": "i18n_npc_crpg_core.spar.opt_execute_cancel",
                    "effects": [{"type": "mark_spared"}, {"type": "message", "key": "i18n_npc_crpg_core.spar.spared_ok"}],
                    "next_node": "exhausted_root",
                },
            ]
        if node_id == "spar_player_lost":
            return [
                {
                    "id": "__spar_lost_leave",
                    "category": "leave",
                    "text_key": "i18n_npc_crpg_core.spar.opt_lost_leave",
                    "tag_key": "i18n_npc_crpg_core.tags.leave",
                    "effects": [{"type": "mark_spared"}, {"type": "close_dialog"}],
                }
            ]

        node = (graph.get("nodes") or {}).get(node_id) or {}
        if node_id == "exhausted_root":
            opts = CrpgDialogEngine._build_recap_options(ctx)
            for raw in node.get("options") or ():
                if CrpgDialogEngine._is_option_visible(raw, ctx):
                    opts.append(raw)
            if not any(o.get("category") == "leave" for o in opts):
                opts.append(
                    {
                        "id": "__exhausted_leave",
                        "category": "leave",
                        "text_key": "i18n_npc_crpg_core.common.opt_leave",
                        "tag_key": "i18n_npc_crpg_core.tags.leave",
                        "effects": [{"type": "close_dialog"}],
                    }
                )
            return opts

        opts = [o for o in (node.get("options") or ()) if CrpgDialogEngine._is_option_visible(o, ctx)]
        if not opts:
            return [
                {
                    "id": "__fallback_leave",
                    "category": "leave",
                    "text_key": "i18n_npc_crpg_core.common.opt_leave",
                    "tag_key": "i18n_npc_crpg_core.tags.leave",
                    "effects": [{"type": "close_dialog"}],
                }
            ]
        return opts

    @staticmethod
    def _format_option_label(opt: dict, ctx: dict) -> str:
        tkey = str(opt.get("text_key", ""))
        tparams = dict(opt.get("text_params") or {})
        base = render_text_node(locale_text(tkey, params=tparams)) if tkey else str(opt.get("text", ""))
        tags: List[str] = []
        cost = opt.get("cost") or {}
        if cost.get("gold"):
            tags.append(render_text_node(locale_text("i18n_npc_crpg_core.tags.cost_gold", params={"cost": int(cost["gold"])})))
        if cost.get("item"):
            from ....inventory.bag_service import get_item_display_name

            tags.append(render_text_node(locale_text("i18n_npc_crpg_core.tags.cost_item", params={"item": get_item_display_name(str(cost["item"]))})))
        if cost.get("hp"):
            tags.append(render_text_node(locale_text("i18n_npc_crpg_core.tags.cost_hp", params={"hp": int(cost["hp"])})))
        tag_key = opt.get("tag_key")
        if tag_key:
            tags.append(render_text_node(locale_text(str(tag_key))))
        if isinstance(opt.get("check"), dict):
            tags.append(render_text_node(DiceCheckEngine.build_option_tag(opt["check"], ctx)))
        if tags:
            return f"{base} {' '.join(tags)}"
        return base

    @staticmethod
    def _resolve_node_text_key(node_id: str, npc_id: str, graph: dict, ctx: dict) -> str:
        if node_id == "spar_npc_yield":
            return str(graph.get("spar_yield_key") or "i18n_npc_crpg_core.spar.npc_yield_default")
        if node_id == "spar_execute_confirm":
            if graph.get("cycle_aware") or graph.get("cross_run_memory"):
                return str(graph.get("spar_execute_key") or "i18n_npc_crpg_core.spar.execute_confirm_cycle")
            return str(graph.get("spar_execute_key") or "i18n_npc_crpg_core.spar.execute_confirm_default")
        if node_id == "spar_player_lost":
            return str(graph.get("spar_lost_key") or "i18n_npc_crpg_core.spar.player_lost_default")
        node = (graph.get("nodes") or {}).get(node_id) or {}
        for variant in node.get("text_variants") or ():
            cond = variant.get("when")
            if not cond or eval_condition(cond, ctx):
                return str(variant.get("key", ""))
        return str(node.get("text_key", ""))

    @staticmethod
    def get_dialog_view(run, save_manager=None) -> Optional[Tuple[str, str, List[str]]]:
        npc_id = str((run.node_data or {}).get("npc_id", ""))
        graph = NPC_DIALOG_GRAPHS.get(npc_id)
        if graph is None:
            return None
        uid = run.user_id
        stats = NpcMemoryStore.load_stats(save_manager, uid)
        coord = str((run.node_data or {}).get("coord", ""))
        ctx = CrpgDialogEngine._build_ctx(run, stats, save_manager, uid, npc_id, graph, coord=coord)
        node_id = str((run.node_data or {}).get("node_id") or "")
        if not node_id or (node_id not in (graph.get("nodes") or {}) and node_id not in SPAR_INTERNAL_NODES):
            node_id = CrpgDialogEngine.resolve_entry_node(run, stats, uid, npc_id, graph, coord=coord)
        name = get_npc_display_name(npc_id)
        text_key = CrpgDialogEngine._resolve_node_text_key(node_id, npc_id, graph, ctx)
        body = render_text_node(locale_text(text_key, params={"name": name})) if text_key else ""
        if node_id in ("root", "return_root") and not text_key:
            greetings = list(graph.get("greetings") or ())
            if greetings:
                gidx = int(ctx["p_enc"].get("greeting_idx", 0)) % len(greetings)
                body = render_text_node(locale_text(str(greetings[gidx]), params={"name": name}))
        opts = CrpgDialogEngine._visible_options_for_node(node_id, graph, ctx)
        opt_labels = [CrpgDialogEngine._format_option_label(opt, ctx) for opt in opts]
        return name, body, opt_labels

    @staticmethod
    def _validate_cost(opt: dict, ctx: dict) -> Optional[TextNode]:
        cost = opt.get("cost") or {}
        p = ctx["player"]
        if cost.get("gold") and int(getattr(p, "gold", 0) or 0) < int(cost["gold"]):
            return locale_text("i18n_room_interact.dialog.err_gold", params={"cost": int(cost["gold"])})
        if cost.get("hp") and int(getattr(p, "hp", 0) or 0) <= int(cost["hp"]):
            return locale_text("i18n_room_interact.dialog.err_hp")
        if cost.get("item"):
            item_id = str(cost["item"])
            if item_id not in (getattr(p, "bag_items", None) or ()):
                from ....inventory.bag_service import get_item_display_name

                return locale_text("i18n_npc_crpg_core.common.err_need_item", params={"item": get_item_display_name(item_id)})
        if cost.get("need_unupgraded_card"):
            from .....data.cards.card_upgrade_data import CARD_UPGRADE_CONFIG

            if not any(not c.upgraded and c.id in CARD_UPGRADE_CONFIG for c in (getattr(p, "deck", None) or ())):
                return locale_text("i18n_room_interact.dialog.smith_no_unupgraded")
        return None

    @staticmethod
    def _deduct_cost(opt: dict, ctx: dict) -> None:
        if opt.get("defer_cost"):
            return
        cost = opt.get("cost") or {}
        p = ctx["player"]
        if cost.get("gold"):
            p.gold -= int(cost["gold"])
        if cost.get("hp"):
            p.hp -= int(cost["hp"])
        if cost.get("item"):
            bag = getattr(p, "bag_items", None)
            if isinstance(bag, list) and str(cost["item"]) in bag:
                bag.remove(str(cost["item"]))

    @staticmethod
    def handle_choice(map_engine, run, idx: int) -> Optional[str]:
        npc_id = str((run.node_data or {}).get("npc_id", ""))
        graph = NPC_DIALOG_GRAPHS.get(npc_id)
        if graph is None:
            return None
        uid = run.user_id
        save_manager = map_engine.save_manager
        stats = NpcMemoryStore.load_stats(save_manager, uid)
        coord = str((run.node_data or {}).get("coord", ""))
        ctx = CrpgDialogEngine._build_ctx(run, stats, save_manager, uid, npc_id, graph, coord=coord)
        node_id = str((run.node_data or {}).get("node_id") or "")
        if not node_id or (node_id not in (graph.get("nodes") or {}) and node_id not in SPAR_INTERNAL_NODES):
            node_id = CrpgDialogEngine.resolve_entry_node(run, stats, uid, npc_id, graph, coord=coord)
        opts = CrpgDialogEngine._visible_options_for_node(node_id, graph, ctx)
        if idx < 1 or idx > len(opts):
            return render_text_node(locale_text("err_invalid_option_idx"))
        chosen = opts[idx - 1]
        err_node = CrpgDialogEngine._validate_cost(chosen, ctx)
        if err_node is not None:
            return render_text_node(err_node)

        ctx["p_enc"]["talk_turns"] = int(ctx["p_enc"].get("talk_turns", 0)) + 1
        CrpgDialogEngine._deduct_cost(chosen, ctx)

        if chosen.get("once_per_encounter"):
            oid = str(chosen.get("id", ""))
            if oid and oid not in ctx["p_enc"].setdefault("consumed_options", []):
                ctx["p_enc"]["consumed_options"].append(oid)
        if chosen.get("once_per_run"):
            flag = f"opt_run:{npc_id}:{chosen.get('id', '')}"
            if flag not in ctx["run_npc"].setdefault("known_flags", []):
                ctx["run_npc"]["known_flags"].append(flag)
        if chosen.get("exclusive_group"):
            eg = str(chosen["exclusive_group"])
            if eg not in ctx["p_enc"].setdefault("locked_groups", []):
                ctx["p_enc"]["locked_groups"].append(eg)
        if chosen.get("service_key") and not chosen.get("defer_service"):
            skey = str(chosen["service_key"])
            uses = ctx["p_enc"].setdefault("service_uses", {})
            uses[skey] = int(uses.get(skey, 0) or 0) + 1

        outcome_nodes: List[TextNode] = []
        next_node = str(chosen.get("next_node") or "")
        effects = list(chosen.get("effects") or ())

        check_cfg = chosen.get("check")
        if isinstance(check_cfg, dict):
            cid = str(check_cfg.get("check_id") or chosen.get("id", ""))
            passed, check_logs, _ = DiceCheckEngine.resolve_check(check_cfg, ctx)
            outcome_nodes.extend(check_logs)
            if cid:
                ctx["p_enc"].setdefault("checked_nodes", {})[cid] = "success" if passed else "fail"
            branch = check_cfg.get("on_success") if passed else check_cfg.get("on_fail")
            if isinstance(branch, dict):
                effects.extend(branch.get("effects") or ())
                if branch.get("next_node"):
                    next_node = str(branch["next_node"])

        ctrl = apply_effects(effects, ctx)
        outcome_nodes.extend(ctrl.get("outcomes") or ())
        flow = ctrl.get("flow")

        from ..npc_dialog import close_room_dialog, finalize_npc_kill_rewards, render_room_dialog, start_npc_combat

        if flow == "UPGRADE_FLOW":
            save_manager.save_save(uid, run)
            return "UPGRADE_FLOW"
        if flow == "GEM_FLOW":
            res = map_engine.explore_engine.start_gem_insert_flow(run, ctrl["gem_id"], "room_dialog", ctrl["next_data"])
            return res
        if flow == "COMBAT_FLOW":
            intro_key = ctrl.get("intro_key")
            intro = render_text_node(locale_text(intro_key)) if intro_key else ""
            battle_view = start_npc_combat(map_engine, run, npc_id, npc_source="grid", non_lethal=bool(ctrl.get("non_lethal", True)))
            return f"{intro}\n\n{battle_view}" if intro else battle_view
        if flow == "EXECUTE_KILL_FLOW":
            return finalize_npc_kill_rewards(map_engine.save_manager, run, npc_id, coord)
        if flow == "CLOSE_FLOW" or next_node == "__close__":
            prefix = "\n".join(render_text_node(n) for n in outcome_nodes if n is not None)
            ended = close_room_dialog(save_manager, run)
            return f"{prefix}\n{ended}" if prefix else ended

        if not next_node:
            next_node = "root"
        if next_node in ("root", "return_root") and not CrpgDialogEngine._has_active_content(graph, next_node, ctx):
            next_node = "exhausted_root"
        if next_node == "exhausted_root":
            ctx["p_enc"]["exhausted"] = True
        run.node_data["node_id"] = next_node
        run.node_data["last_outcome_nodes"] = serialize_outcome_nodes(outcome_nodes)
        save_manager.save_save(uid, run)
        return render_room_dialog(run, save_manager=save_manager)
