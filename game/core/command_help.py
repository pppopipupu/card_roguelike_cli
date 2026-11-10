from typing import Dict, List, Optional
from ..data.command_data import COMMAND_SECTIONS, COMMAND_SECTION_ORDER
from ..data.locale_data import get_locale_text
from ..renderer.help import render_help_detail, render_help_index


def _registry():
    from .cli.base import CommandHandler
    return CommandHandler


def help_entry(handler) -> Dict:
    key = handler.help_key
    return {
        "key": key,
        "name": get_locale_text(f"i18n_help.commands.{key}.name"),
        "usage": get_locale_text(f"i18n_help.commands.{key}.usage"),
        "brief": get_locale_text(f"i18n_help.commands.{key}.brief"),
        "desc": get_locale_text(f"i18n_help.commands.{key}.desc"),
        "example": get_locale_text(f"i18n_help.commands.{key}.example"),
        "aliases": list(handler.names),
        "states": list(handler.allowed_states)
    }


def _handlers_by_key() -> Dict[str, object]:
    mapping = {}
    for handler in _registry().registry.values():
        key = getattr(handler, "help_key", "")
        if key and key not in mapping:
            mapping[key] = handler
    return mapping


def _aliases_by_key() -> Dict[str, List[str]]:
    mapping = {}
    for name, handlers in _registry().registry_all.items():
        for handler in handlers:
            key = getattr(handler, "help_key", "")
            if not key:
                continue
            mapping.setdefault(key, [])
            if name not in mapping[key]:
                mapping[key].append(name)
    return mapping


def _with_aliases(handler, aliases_map: Dict[str, List[str]]) -> Dict:
    entry = help_entry(handler)
    entry["aliases"] = aliases_map.get(handler.help_key, entry["aliases"])
    return entry


def build_help_sections() -> List[tuple]:
    by_key = _handlers_by_key()
    aliases = _aliases_by_key()
    sections = []
    for section_id in COMMAND_SECTIONS:
        entries = []
        for key in COMMAND_SECTION_ORDER[section_id]:
            handler = by_key.get(key)
            if handler is None:
                continue
            entries.append(_with_aliases(handler, aliases))
        sections.append((section_id, entries))
    return sections


def help_index_text() -> str:
    return render_help_index(build_help_sections())


def find_help_handler(save_manager, user_id: str, target: str) -> Optional[object]:
    from .state_resolver import resolve_game_state
    registry = _registry()
    run = save_manager.load_save(user_id)
    stats = None if run is not None else save_manager.load_stats(user_id)
    handler, _ = registry.resolve(target, resolve_game_state(run, stats))
    if handler is not None:
        return handler
    handlers = registry.registry_all.get(target)
    return handlers[0] if handlers else None


def help_detail_text(save_manager, user_id: str, parts: List[str]) -> str:
    target = " ".join(parts[1:]).strip().lower()
    handler = find_help_handler(save_manager, user_id, target)
    if handler is None:
        return get_locale_text("i18n_help.not_found", name=target)
    return render_help_detail(_with_aliases(handler, _aliases_by_key()))
