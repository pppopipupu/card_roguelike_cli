from typing import Tuple
from ...models.state import set_user_id
from ..cli.base import ActionHandler
from .base.aliases import normalize_node_alias
from ...data.text.locale_data import get_locale_text

class ActionRouter:
    def __init__(self, save_manager, engine):
        self.save_manager = save_manager
        self.engine = engine
        self._action_handlers = ActionHandler.registry

    def execute_action(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        set_user_id(user_id)
        if not parts:
            return "", False, False
        state_stack = run.node_data.setdefault("state_stack", [])
        if parts[0].lower() in ("折叠", "f", "fold"):
            handler = self._action_handlers.get(parts[0].lower())
            if handler:
                return handler.execute(router, user_id, run, parts)
        if state_stack:
            top_state = state_stack[-1]
            stype = top_state.get("type")
            if stype in ("interaction_session", "card_selection"):
                from ..battle.selection import handle_selection_input
                return handle_selection_input(self, router, user_id, run, parts)
        parts = normalize_node_alias(run, parts)
        sub = parts[0]
        handler = self._action_handlers.get(sub)
        if handler:
            return handler.execute(router, user_id, run, parts)
        return get_locale_text("i18n_cli_core.unknown_action", parts=parts), False, False
