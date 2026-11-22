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
