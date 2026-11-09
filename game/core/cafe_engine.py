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
    CAFE_TOTAL_NPCS,
    NPC_ALIASES,
    NPC_SHOW_NAMES,
)
from ..data.locale_data import get_locale_text
from .cafe_dialog import CafeDialogMixin

class CafeEngine(CafeDialogMixin):
    def __init__(self, save_manager, map_engine):
        self.save_manager = save_manager
        self.map_engine = map_engine

    def init_cafe(self, run: GameRun):
        p = run.player

        num_guests = random.randint(CAFE_GUEST_COUNT_MIN, CAFE_GUEST_COUNT_MAX)
        selected_guests = random.sample(CAFE_GUESTS, num_guests)
        selected_normals = random.sample(CAFE_NORMALS, CAFE_TOTAL_NPCS - num_guests)
        selected_npcs = selected_guests + selected_normals
        random.shuffle(selected_npcs)

        cafe_data = {
            "npcs": selected_npcs, "active_npc": None, "dialog_state": None,
            "talked_npcs": [], "card_master_stock": [], "gemcutter_stock": [],
            "hunter_stock": None
        }

        stats = self.save_manager.load_stats(run.user_id)
        p_class = getattr(stats, "selected_class", "法师")

        if "杰斯" in selected_npcs:
            if p_class == "战士":
                from ..data.wizard_card_data import WIZARD_CARD_CONFIG
                pool = [k for k, v in WIZARD_CARD_CONFIG.items() if v.get("rarity") not in ("legendary", "mythic", "artifact")]
            else:
                from ..data.warrior_card_data import WARRIOR_CARD_CONFIG
                pool = [k for k, v in WARRIOR_CARD_CONFIG.items() if v.get("rarity") not in ("legendary", "mythic", "artifact")]
            cafe_data["card_master_stock"] = random.sample(pool, min(len(pool), CAFE_CARD_MASTER_STOCK))

        if "艾琳" in selected_npcs:
            rare_gems = [k for k, v in GEM_CONFIG.items() if v.get("rarity") == "rare"]
            if rare_gems:
                cafe_data["gemcutter_stock"] = random.sample(rare_gems, min(len(rare_gems), CAFE_GEMCUTTER_STOCK))

        if "凯尔" in selected_npcs:
            relic_keys = [k for k, v in RELIC_CONFIG.items() if v.get("rarity") == "epic" and k not in p.relics]
            if not relic_keys:
                relic_keys = [k for k in RELIC_CONFIG.keys() if k not in p.relics]
            if relic_keys:
                cafe_data["hunter_stock"] = random.choice(relic_keys)

        run.node_type = "cafe"
        run.node_data["cafe_data"] = cafe_data
        self.save_manager.save_save(run.user_id, run)

    def render_cafe(self, run: GameRun) -> str:
        p = run.player
        cafe_data = run.node_data.get("cafe_data", {})
        active_npc = cafe_data.get("active_npc")

        if active_npc is None:
            npcs_str = ""
            for npc in cafe_data.get("npcs", []):
                status = get_locale_text("i18n_map_cafe.cafe_status_talked") if npc in cafe_data.get("talked_npcs", []) else ""
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
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ]
            return "\n".join(lines)

        else:
            dialog_state = cafe_data.get("dialog_state")
            npc_name = NPC_SHOW_NAMES.get(active_npc, active_npc)

            lines = [
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                get_locale_text("i18n_map_cafe.cafe_dialog_title", npc_name=npc_name),
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ]

            talked = active_npc in cafe_data.get("talked_npcs", [])
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
        cafe_data = run.node_data.setdefault("cafe_data", {})
        npcs = cafe_data.get("npcs", [])

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

        cafe_data["active_npc"] = found
        cafe_data["dialog_state"] = "start"
        self.save_manager.save_save(run.user_id, run)

        return self.render_cafe(run)

    def leave_npc(self, run: GameRun) -> str:
        cafe_data = run.node_data.setdefault("cafe_data", {})
        active_npc = cafe_data.get("active_npc")
        if active_npc is not None:
            talked_npcs = cafe_data.setdefault("talked_npcs", [])
            if active_npc not in talked_npcs:
                talked_npcs.append(active_npc)
            cafe_data["active_npc"] = None
            cafe_data["dialog_state"] = None
            self.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_map_cafe.cafe_msg_left_npc") + "\n\n" + self.render_cafe(run)
        return get_locale_text("i18n_map_cafe.cafe_err_already_lobby")

    def leave_cafe(self, run: GameRun) -> str:
        run.node_type = "ancient"
        self.map_engine._init_ancient_node(run)
        self.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_map_cafe.cafe_msg_leave_cafe")

    def choose_option(self, run: GameRun, idx: int) -> str:
        cafe_data = run.node_data.setdefault("cafe_data", {})
        active_npc = cafe_data.get("active_npc")
        dialog_state = cafe_data.get("dialog_state")
        talked = active_npc in cafe_data.get("talked_npcs", [])

        if active_npc is None:
            return get_locale_text("i18n_map_cafe.cafe_err_not_in_dialog")

        _, options = self._get_dialog_content(run, active_npc, dialog_state, talked)
        if idx < 1 or idx > len(options):
            return get_locale_text("i18n_map_cafe.cafe_err_invalid_option")

        res_msg = self._execute_dialog_logic(run, active_npc, dialog_state, idx, talked)
        self.save_manager.save_save(run.user_id, run)

        return res_msg
