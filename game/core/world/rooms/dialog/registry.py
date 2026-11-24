from typing import Any, Callable, List, Optional, Tuple


class NpcDialogProvider:
    """地城房间 NPC 对话提供者接口，统一隔离不同剧情线的会话渲染与选择流转。"""

    def can_handle(self, run, npc_id: str) -> bool:
        return False

    def open_dialog(self, save_manager, run, room, coord: str, npc_id: str) -> Optional[dict]:
        return None

    def render_content(self, run, save_manager=None) -> Optional[Tuple[str, str, List[str]]]:
        return None

    def handle_choice(self, map_engine, run, idx: int) -> Optional[str]:
        return None


DIALOG_PROVIDERS: List[Tuple[int, str, NpcDialogProvider]] = []


def register_npc_provider(name: str, priority: int = 100):
    def decorator(cls):
        instance = cls()
        DIALOG_PROVIDERS.append((priority, name, instance))
        DIALOG_PROVIDERS.sort(key=lambda item: item[0])
        return cls

    return decorator


def resolve_provider_for_open(run, npc_id: str) -> Optional[Tuple[str, NpcDialogProvider]]:
    for _, name, provider in DIALOG_PROVIDERS:
        if provider.can_handle(run, npc_id):
            return name, provider
    return None


def resolve_provider_by_name(name: str) -> Optional[NpcDialogProvider]:
    for _, reg_name, provider in DIALOG_PROVIDERS:
        if reg_name == name:
            return provider
    return None


@register_npc_provider("bleak_falls", priority=10)
class BleakFallsNpcProvider(NpcDialogProvider):
    BLEAK_NPCS = frozenset({"farengar_court_mage", "arvel_trapped", "map_surveyor", "brazier_keeper"})

    def can_handle(self, run, npc_id: str) -> bool:
        return npc_id in self.BLEAK_NPCS

    def open_dialog(self, save_manager, run, room, coord: str, npc_id: str) -> Optional[dict]:
        from ...bleak_falls import build_bleak_npc_dialog

        bleak_dlg = build_bleak_npc_dialog(save_manager, run, room, npc_id)
        if bleak_dlg is None:
            return None
        return {
            "npc_id": npc_id,
            "dialog_state": "start",
            "coord": coord,
            "provider": "bleak_falls",
            "bleak_dialog": bleak_dlg,
        }

    def render_content(self, run, save_manager=None) -> Optional[Tuple[str, str, List[str]]]:
        bleak_dlg = run.node_data.get("bleak_dialog")
        if not isinstance(bleak_dlg, dict):
            return None
        opts = [o.get("text", "") for o in (bleak_dlg.get("options") or [])]
        return bleak_dlg.get("name", ""), bleak_dlg.get("greeting", ""), opts

    def handle_choice(self, map_engine, run, idx: int) -> Optional[str]:
        bleak_dlg = run.node_data.get("bleak_dialog")
        if not isinstance(bleak_dlg, dict):
            return None
        from ...bleak_falls import handle_bleak_npc_choice

        chosen_opt = (bleak_dlg.get("options") or [])[idx - 1]
        return handle_bleak_npc_choice(map_engine, run, bleak_dlg, chosen_opt)


@register_npc_provider("chireiden", priority=20)
class ChireidenNpcProvider(NpcDialogProvider):
    def can_handle(self, run, npc_id: str) -> bool:
        return npc_id == "kaenbyou_rin"

    def open_dialog(self, save_manager, run, room, coord: str, npc_id: str) -> Optional[dict]:
        from ...chireiden import build_rin_npc_dialog

        rin_dlg = build_rin_npc_dialog(save_manager, run, room, npc_id)
        if rin_dlg is None:
            return None
        return {
            "npc_id": npc_id,
            "dialog_state": "start",
            "coord": coord,
            "provider": "chireiden",
            "chireiden_dialog": rin_dlg,
        }

    def render_content(self, run, save_manager=None) -> Optional[Tuple[str, str, List[str]]]:
        chireiden_dlg = run.node_data.get("chireiden_dialog")
        if not isinstance(chireiden_dlg, dict):
            return None
        opts = [o.get("text", "") for o in (chireiden_dlg.get("options") or [])]
        return chireiden_dlg.get("name", ""), chireiden_dlg.get("greeting", ""), opts

    def handle_choice(self, map_engine, run, idx: int) -> Optional[str]:
        chireiden_dlg = run.node_data.get("chireiden_dialog")
        if not isinstance(chireiden_dlg, dict):
            return None
        from ...chireiden import handle_rin_npc_choice

        chosen_opt = (chireiden_dlg.get("options") or [])[idx - 1]
        return handle_rin_npc_choice(map_engine, run, chireiden_dlg, chosen_opt)


@register_npc_provider("tutorial", priority=30)
class TutorialNpcProvider(NpcDialogProvider):
    def can_handle(self, run, npc_id: str) -> bool:
        return npc_id == "tutorial_elder"

    def open_dialog(self, save_manager, run, room, coord: str, npc_id: str) -> Optional[dict]:
        from ...tutorial import build_tutorial_elder_dialog

        tut_dlg = build_tutorial_elder_dialog(run)
        return {
            "npc_id": npc_id,
            "dialog_state": "start",
            "coord": coord,
            "provider": "tutorial",
            "tutorial_dialog": tut_dlg,
        }

    def render_content(self, run, save_manager=None) -> Optional[Tuple[str, str, List[str]]]:
        tut_dlg = run.node_data.get("tutorial_dialog")
        if not isinstance(tut_dlg, dict):
            return None
        opts = [o.get("text", "") for o in (tut_dlg.get("options") or [])]
        return tut_dlg.get("name", ""), tut_dlg.get("greeting", ""), opts

    def handle_choice(self, map_engine, run, idx: int) -> Optional[str]:
        tut_dlg = run.node_data.get("tutorial_dialog")
        if not isinstance(tut_dlg, dict):
            return None
        from ...tutorial import handle_tutorial_elder_choice

        chosen_opt = (tut_dlg.get("options") or [])[idx - 1]
        return handle_tutorial_elder_choice(map_engine, run, chosen_opt)


@register_npc_provider("cafe", priority=25)
class CafeNpcProvider(NpcDialogProvider):
    def can_handle(self, run, npc_id: str) -> bool:
        return npc_id == "cafe_barista" or npc_id.startswith("cafe_guest:")

    def open_dialog(self, save_manager, run, room, coord: str, npc_id: str) -> Optional[dict]:
        from .....data.text.locale_data import get_locale_text
        from .....data.world.cafe_data import NPC_SHOW_NAMES
        from ...cafe.engine import CafeEngine

        cafe = CafeEngine(save_manager, None)
        state = cafe.ensure_cafe_room(run, room)
        if npc_id == "cafe_barista":
            if room.shared_payload.get("barista_defeated"):
                return {
                    "_error": get_locale_text(
                        "i18n_room_interact.combat.attack_already_defeated",
                        name=get_locale_text("i18n_room_interact.npcs.cafe_barista.name"),
                    )
                }
            return {
                "npc_id": "cafe_barista",
                "cafe_npc": "Barista_Bruno",
                "active_npc": "Barista_Bruno",
                "dialog_state": "start",
                "coord": coord,
                "provider": "cafe",
            }
        guest_key = npc_id.split(":", 1)[1]
        active_by_npc = state.setdefault("active_by_npc", {})
        holder = active_by_npc.get(guest_key)
        players = getattr(run, "players", {}) or {}
        fm = getattr(run, "floor_map", None)
        holder_still_talking = False
        if holder and holder != run.user_id and holder in players and fm is not None:
            hsid = fm.player_session_map.get(holder)
            if hsid and hsid in fm.active_sessions:
                hsess = fm.active_sessions[hsid]
                if hsess.node_type == "room_dialog" and (hsess.node_data or {}).get("cafe_npc") == guest_key:
                    holder_still_talking = True
        if holder_still_talking:
            return {
                "_error": get_locale_text(
                    "i18n_map_cafe.cafe_err_npc_busy",
                    npc_name=NPC_SHOW_NAMES.get(guest_key, guest_key),
                    player_name=players[holder].name,
                )
            }
        if holder and holder != run.user_id and not holder_still_talking:
            active_by_npc.pop(guest_key, None)
        if guest_key not in state.get("talked_npcs", []):
            active_by_npc[guest_key] = run.user_id
        return {
            "npc_id": npc_id,
            "cafe_npc": guest_key,
            "active_npc": guest_key,
            "dialog_state": "start",
            "coord": coord,
            "provider": "cafe",
        }

    def render_content(self, run, save_manager=None) -> Optional[Tuple[str, str, List[str]]]:
        nd = run.node_data or {}
        cafe_npc = str(nd.get("cafe_npc") or "")
        if not cafe_npc:
            return None
        from .....data.text.locale_data import get_locale_text
        from .....data.world.cafe_data import NPC_SHOW_NAMES
        from ...cafe.engine import CafeEngine

        cafe = CafeEngine(save_manager, None)
        shared_cafe = cafe._shared_cafe(run)
        talked = False if cafe_npc == "Barista_Bruno" else cafe_npc in shared_cafe.get("talked_npcs", [])
        text, opts = cafe._get_dialog_content(run, cafe_npc, nd.get("dialog_state"), talked)
        if cafe_npc == "Barista_Bruno":
            name = get_locale_text("i18n_room_interact.npcs.cafe_barista.name")
        else:
            name = str(NPC_SHOW_NAMES.get(cafe_npc, cafe_npc))
        return name, text, opts

    def handle_choice(self, map_engine, run, idx: int) -> Optional[str]:
        nd = run.node_data or {}
        cafe_npc = str(nd.get("cafe_npc") or "")
        if not cafe_npc:
            return None
        from ...cafe.engine import CafeEngine
        from ..npc_dialog import close_room_dialog

        cafe = CafeEngine(map_engine.save_manager, map_engine)
        shared_cafe = cafe._shared_cafe(run)
        talked_before = cafe_npc in shared_cafe.get("talked_npcs", [])
        talked_flag = False if cafe_npc == "Barista_Bruno" else talked_before
        res = cafe._execute_dialog_logic(run, cafe_npc, nd.get("dialog_state"), idx, talked_flag)
        if res == "UPGRADE_FLOW":
            map_engine.save_manager.save_save(run.user_id, run)
            return "UPGRADE_FLOW"
        if run.node_type == "gem_insert":
            cafe._release_npc_lock(shared_cafe, run.user_id, cafe_npc)
            if cafe_npc in shared_cafe.get("talked_npcs", []) and not talked_before:
                shared_cafe.setdefault("talked_by", {})[cafe_npc] = run.user_id
            map_engine.save_manager.save_save(run.user_id, run)
            return res
        if nd.get("active_npc") is None:
            cafe._release_npc_lock(shared_cafe, run.user_id, cafe_npc)
            if cafe_npc in shared_cafe.get("talked_npcs", []) and not talked_before:
                shared_cafe.setdefault("talked_by", {})[cafe_npc] = run.user_id
            close_room_dialog(map_engine.save_manager, run, mark_solo_talked=False)
            return res
        map_engine.save_manager.save_save(run.user_id, run)
        return res
