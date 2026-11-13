import random
from ..models.state import GameRun
from ..entities import get_relic_name
from ..data.relic_data import RELIC_CONFIG
from ..data.gem_data import GEM_CONFIG
from ..data.cafe_data import (
    CAFE_CARD_MASTER_STOCK,
    CAFE_GEMCUTTER_STOCK,
    CAFE_GUEST_COUNT_MAX,
    CAFE_GUEST_COUNT_MIN,
    CAFE_GUESTS,
    CAFE_NORMALS,
    CAFE_NPCS_PER_EXTRA_PLAYER,
    CAFE_TOTAL_NPCS,
    NPC_ALIASES,
    NPC_SHOW_NAMES,
)
from ..data.locale_data import get_locale_text
from .cafe_dialog import CafeDialogMixin
from .deck_service import DeckService
from ..data.reward_config import NORMAL_CARD_RARITIES
class CafeEngine(CafeDialogMixin):
    def __init__(self, save_manager, map_engine):
        self.save_manager = save_manager
        self.map_engine = map_engine

    def _waiting(self, run):
        if run.node_data.get("coop_done"):
            return get_locale_text("i18n_coop_explore.coop_done_waiting")
        return ""

    def _view_cafe(self, run: GameRun) -> dict:
        return run.node_data.setdefault("cafe_data", {})

    def _shared_cafe(self, run: GameRun) -> dict:
        shared = run.node_data.get("coop_cafe")
        if isinstance(shared, dict):
            return shared
        return self._view_cafe(run)
    def _release_npc_lock(self, shared_cafe: dict, uid: str, npc: str = None):
        active_by_npc = shared_cafe.get("active_by_npc")
        if not isinstance(active_by_npc, dict):
            return
        if npc is not None:
            if active_by_npc.get(npc) == uid:
                active_by_npc.pop(npc, None)
            return
        for key, holder in list(active_by_npc.items()):
            if holder == uid:
                active_by_npc.pop(key, None)

    def _npc_bounds_for_count(self, player_count: int) -> tuple[int, int, int]:
        count = max(1, int(player_count or 1))
        max_pool = len(CAFE_GUESTS) + len(CAFE_NORMALS)
        total_npcs = min(max_pool, CAFE_TOTAL_NPCS + max(0, count - 1) * CAFE_NPCS_PER_EXTRA_PLAYER)
        guest_min = max(CAFE_GUEST_COUNT_MIN, total_npcs - len(CAFE_NORMALS))
        guest_max = min(len(CAFE_GUESTS), total_npcs, CAFE_GUEST_COUNT_MAX + max(0, count - 1))
        guest_min = min(guest_min, guest_max)
        return total_npcs, guest_min, guest_max

    def build_cafe_state(self, run: GameRun, player_count: int = None) -> dict:
        if player_count is None:
            player_count = run.player_count() if run else 1
        total_npcs, guest_min, guest_max = self._npc_bounds_for_count(player_count)
        num_guests = random.randint(guest_min, guest_max)
        selected_guests = random.sample(CAFE_GUESTS, num_guests)
        selected_normals = random.sample(CAFE_NORMALS, total_npcs - num_guests)
        selected_npcs = selected_guests + selected_normals
        random.shuffle(selected_npcs)

        cafe_data = {
            "npcs": selected_npcs, "active_npc": None, "dialog_state": None,
            "talked_npcs": [], "card_master_stock": [], "gemcutter_stock": [],
            "hunter_stock": None
        }

        if "杰斯" in selected_npcs:
            pool = []
            seen = set()
            for uid in (run.human_uids() or [run.user_id]):
                member_stats = self.save_manager.load_stats(uid)
                member_class = getattr(member_stats, "selected_class", "法师")
                other_color = "wizard" if member_class == "战士" else "warrior"
                for cid in DeckService.eligible_card_ids(member_stats, colors=(other_color,), rarities=NORMAL_CARD_RARITIES):
                    if cid not in seen:
                        seen.add(cid)
                        pool.append(cid)
            cafe_data["card_master_stock"] = random.sample(pool, min(len(pool), CAFE_CARD_MASTER_STOCK))

        if "艾琳" in selected_npcs:
            rare_gems = [k for k, v in GEM_CONFIG.items() if v.get("rarity") == "rare"]
            if rare_gems:
                cafe_data["gemcutter_stock"] = random.sample(rare_gems, min(len(rare_gems), CAFE_GEMCUTTER_STOCK))

        if "凯尔" in selected_npcs:
            owned_relics = {rid for member in run.players.values() for rid in member.relics}
            relic_keys = [k for k, v in RELIC_CONFIG.items() if v.get("rarity") == "epic" and k not in owned_relics]
            if not relic_keys:
                relic_keys = [k for k in RELIC_CONFIG.keys() if k not in owned_relics]
            if relic_keys:
                cafe_data["hunter_stock"] = random.choice(relic_keys)

        return cafe_data

    def init_cafe(self, run: GameRun, persist: bool = True, player_count: int = None):
        from .party_coordinator import apply_and_scope
        if player_count is None:
            player_count = run.player_count()
        shared_cafe = self.build_cafe_state(run, player_count=player_count)
        shared_cafe["talked_by"] = {}
        shared_cafe["active_by_npc"] = {}
        views = {}
        ready = {}
        for uid in run.party_order:
            player = run.players.get(uid)
            if player is None:
                continue
            data = {
                "cafe_data": {
                    "npcs": list(shared_cafe["npcs"]),
                    "active_npc": None,
                    "dialog_state": None,
                },
                "coop_done": player.downed,
            }
            views[uid] = {"node_type": "cafe", "data": data}
            ready[uid] = player.downed or getattr(player, "is_mercenary", False)
        run.node_type = "cafe"
        run.node_data = {
            "coop_node_type": "cafe",
            "coop_cafe": shared_cafe,
            "player_views": views,
            "stage_ready": ready,
        }
        apply_and_scope(run, run.user_id)
        if persist:
            self.save_manager.save_save(run.user_id, run)

    def render_cafe(self, run: GameRun) -> str:
        if run.node_data.get("coop_done"):
            from ..renderer.party import render_waiting
            return render_waiting(run)
        p = run.player
        view_cafe = run.node_data.get("cafe_data", {})
        shared_cafe = self._shared_cafe(run)
        active_npc = view_cafe.get("active_npc")
        if active_npc is None:
            npcs_str = ""
            talked_npcs = shared_cafe.get("talked_npcs", [])
            talked_by = shared_cafe.get("talked_by", {})
            active_by_npc = shared_cafe.get("active_by_npc", {})
            stage_ready = run.node_data.get("stage_ready", {})
            players = getattr(run, "players", {}) or {}
            multi = run.player_count() > 1
            for npc in shared_cafe.get("npcs", []):
                if npc in talked_npcs:
                    actor_uid = talked_by.get(npc)
                    if multi and actor_uid in players:
                        status = get_locale_text("i18n_map_cafe.cafe_status_talked_by", name=players[actor_uid].name)
                    else:
                        status = get_locale_text("i18n_map_cafe.cafe_status_talked")
                elif multi and active_by_npc.get(npc) in players and not stage_ready.get(active_by_npc.get(npc), False):
                    busy_uid = active_by_npc.get(npc)
                    status = get_locale_text("i18n_map_cafe.cafe_status_busy", name=players[busy_uid].name)
                else:
                    status = ""
                npcs_str += f"\n  - {NPC_SHOW_NAMES.get(npc, npc)}{status}"
            lines = [
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                get_locale_text("i18n_map_cafe.cafe_title"),
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                get_locale_text("i18n_map_cafe.cafe_header_stage", stage=p.stage, name=run.player.name),
                get_locale_text("i18n_map_cafe.cafe_header_stats", hp=p.hp, max_hp=p.max_hp, gold=p.gold),
                "" if not p.relics else get_locale_text("i18n_map_cafe.cafe_relics_prefix") + " ".join(f"【{get_relic_name(r)}】" for r in p.relics),
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                get_locale_text("i18n_map_cafe.cafe_environment"),
                get_locale_text("i18n_map_cafe.cafe_guests_header") + npcs_str,
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                get_locale_text("i18n_map_cafe.cafe_hint_talk"),
                get_locale_text("i18n_map_cafe.cafe_hint_leave"),
                *([] if getattr(run, "floor_map", None) is None else [get_locale_text("i18n_grid_map.cafe_counter_hint", price=25, sp=5)]),
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ]
            return "\n".join(lines)

        else:
            dialog_state = view_cafe.get("dialog_state")
            npc_name = NPC_SHOW_NAMES.get(active_npc, active_npc)

            lines = [
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                get_locale_text("i18n_map_cafe.cafe_dialog_title", npc_name=npc_name),
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ]

            talked = active_npc in shared_cafe.get("talked_npcs", [])
            dialog_text, options = self._get_dialog_content(run, active_npc, dialog_state, talked)

            lines.append(dialog_text)
            lines.append("")

            for idx, opt in enumerate(options, 1):
                lines.append(f"  [{idx}] {opt}")

            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append(get_locale_text("i18n_map_cafe.cafe_hint_choice"))
            lines.append(get_locale_text("i18n_map_cafe.cafe_hint_exit_dialog"))
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return "\n".join(lines)

    def talk_npc(self, run: GameRun, target: str) -> str:
        waiting = self._waiting(run)
        if waiting:
            return waiting
        view_cafe = self._view_cafe(run)
        shared_cafe = self._shared_cafe(run)
        npcs = shared_cafe.get("npcs", [])
        target_lower = target.lower().strip()
        found = None

        mapped = NPC_ALIASES.get(target_lower)
        if mapped and mapped in npcs:
            found = mapped

        if not found:
            def clean_text(text: str) -> str:
                res_chars = []
                for char in text.lower():
                    if char.isalnum() or (ord(char) >= 0x4e00 and ord(char) <= 0x9fff):
                        res_chars.append(char)
                return "".join(res_chars)

            cleaned_target = clean_text(target_lower)
            if cleaned_target:
                for npc in npcs:
                    if cleaned_target in clean_text(npc):
                        found = npc
                        break
                    show_name = NPC_SHOW_NAMES.get(npc, "")
                    if show_name and cleaned_target in clean_text(show_name):
                        found = npc
                        break

        if not found:
            return get_locale_text("i18n_map_cafe.cafe_err_npc_not_found", target=target)

        active_by_npc = shared_cafe.setdefault("active_by_npc", {})
        holder = active_by_npc.get(found)
        stage_ready = run.node_data.get("stage_ready", {})
        players = getattr(run, "players", {}) or {}
        if holder and holder != run.user_id and holder in players and not stage_ready.get(holder, False):
            return get_locale_text(
                "i18n_map_cafe.cafe_err_npc_busy",
                npc_name=NPC_SHOW_NAMES.get(found, found),
                player_name=players[holder].name,
            )
        prev_npc = view_cafe.get("active_npc")
        if prev_npc and prev_npc != found:
            self._release_npc_lock(shared_cafe, run.user_id, prev_npc)
        if found not in shared_cafe.get("talked_npcs", []):
            active_by_npc[found] = run.user_id

        view_cafe["active_npc"] = found
        view_cafe["dialog_state"] = "start"
        self.save_manager.save_save(run.user_id, run)

        return self.render_cafe(run)

    def leave_npc(self, run: GameRun) -> str:
        view_cafe = self._view_cafe(run)
        shared_cafe = self._shared_cafe(run)
        active_npc = view_cafe.get("active_npc")
        if active_npc is not None:
            if run.player_count() > 1:
                self._release_npc_lock(shared_cafe, run.user_id, active_npc)
            else:
                self._release_npc_lock(shared_cafe, run.user_id, active_npc)
                talked_npcs = shared_cafe.setdefault("talked_npcs", [])
                if active_npc not in talked_npcs:
                    talked_npcs.append(active_npc)
            view_cafe["active_npc"] = None
            view_cafe["dialog_state"] = None
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_map_cafe.cafe_msg_left_npc") + "\n\n" + self.render_cafe(run)
        return get_locale_text("i18n_map_cafe.cafe_err_already_lobby")

    def leave_cafe(self, run: GameRun) -> str:
        from .party_coordinator import finish_player_node
        waiting = self._waiting(run)
        if waiting:
            return waiting
        msg = get_locale_text("i18n_map_cafe.cafe_msg_leave_cafe")
        self._release_npc_lock(self._shared_cafe(run), run.user_id)
        return finish_player_node(
            self.save_manager,
            self.map_engine,
            run,
            run.user_id,
            msg,
            on_all_ready=(None if getattr(run, "floor_map", None) is not None else self.map_engine.enter_ancient_node),
        )

    def choose_option(self, run: GameRun, idx: int) -> str:
        waiting = self._waiting(run)
        if waiting:
            return waiting
        view_cafe = self._view_cafe(run)
        shared_cafe = self._shared_cafe(run)
        active_npc = view_cafe.get("active_npc")
        dialog_state = view_cafe.get("dialog_state")
        talked = active_npc in shared_cafe.get("talked_npcs", [])

        if active_npc is None:
            if getattr(run, "floor_map", None) is not None and idx == 1:
                from ..data.grid_map_config import SP_CONFIG
                from .sp_system import reduce_exhaustion, restore_sp
                p = run.player
                price = SP_CONFIG["cafe_drink_price"]
                if p.gold < price:
                    return get_locale_text("i18n_map_cafe.cafe_err_gold_insufficient", cost=price)
                p.gold -= price
                gained = restore_sp(p, SP_CONFIG["cafe_drink_sp_gain"])
                old_ex = getattr(p, "exhaustion", 0)
                new_ex = reduce_exhaustion(p, SP_CONFIG["cafe_drink_exhaustion_cure"])
                self.save_manager.save_save(run.user_id, run)
                return get_locale_text("i18n_grid_map.cafe_drink_bought", cost=price, sp=gained, exhaustion_cured=max(0, old_ex - new_ex))
            return get_locale_text("i18n_map_cafe.cafe_err_not_in_dialog")

        _, options = self._get_dialog_content(run, active_npc, dialog_state, talked)
        if idx < 1 or idx > len(options):
            return get_locale_text("i18n_map_cafe.cafe_err_invalid_option")

        res_msg = self._execute_dialog_logic(run, active_npc, dialog_state, idx, talked)
        if view_cafe.get("active_npc") is None:
            self._release_npc_lock(shared_cafe, run.user_id, active_npc)
            if active_npc in shared_cafe.get("talked_npcs", []) and not talked:
                shared_cafe.setdefault("talked_by", {})[active_npc] = run.user_id
        self.save_manager.save_save(run.user_id, run)

        return res_msg
