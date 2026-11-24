from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Type

from ...data.text.locale_data import get_locale_text
from ...models.state import set_user_id


@dataclass
class AdminContext:
    server: Any
    caller_user_id: str
    target_user_id: str
    command: str
    args: list[str]

    @property
    def save_manager(self):
        return self.server.save_manager

    @property
    def engine(self):
        return self.server.engine

    def lock(self, user_id: Optional[str] = None):
        return self.server._get_user_lock(user_id or self.target_user_id)


class AdminCommandHandler:
    aliases: Tuple[str, ...] = ()
    category: str = "general"
    help_key: str = ""
    detail_key: str = ""
    registry: dict[str, Type["AdminCommandHandler"]] = {}
    ordered_handlers: list[Type["AdminCommandHandler"]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.aliases:
            return
        if cls not in AdminCommandHandler.ordered_handlers:
            AdminCommandHandler.ordered_handlers.append(cls)
        for alias in cls.aliases:
            AdminCommandHandler.registry[alias.lower()] = cls

    async def execute(self, ctx: AdminContext) -> str:
        raise NotImplementedError


def register_admin_command(
    aliases: Tuple[str, ...],
    category: str = "general",
    help_key: str = "",
    detail_key: str = "",
) -> Callable[[Type[AdminCommandHandler]], Type[AdminCommandHandler]]:
    def decorator(cls: Type[AdminCommandHandler]) -> Type[AdminCommandHandler]:
        cls.aliases = aliases
        cls.category = category
        cls.help_key = help_key
        cls.detail_key = detail_key
        if cls not in AdminCommandHandler.ordered_handlers:
            AdminCommandHandler.ordered_handlers.append(cls)
        for alias in aliases:
            AdminCommandHandler.registry[alias.lower()] = cls
        return cls

    return decorator


def extract_target_option(parts: list[str]) -> Tuple[Optional[str], list[str]]:
    target: Optional[str] = None
    remaining: list[str] = []
    idx = 0
    while idx < len(parts):
        token = parts[idx]
        low = token.lower()
        if low in ("-u", "--user", "--player") and idx + 1 < len(parts):
            target = parts[idx + 1]
            idx += 2
            continue
        if low.startswith("--user="):
            target = token.split("=", 1)[1]
            idx += 1
            continue
        if low.startswith("-u="):
            target = token.split("=", 1)[1]
            idx += 1
            continue
        remaining.append(token)
        idx += 1
    return target, remaining


class AdminCommandRouter:
    def __init__(self, server: Any):
        self.server = server

    async def dispatch(self, user_id: str, message: str) -> str:
        set_user_id(user_id)
        parts = message.strip().split()
        if parts and parts[0].lower() in ("rogueadmin", "/rogueadmin", ".rogueadmin", "admin", "/admin"):
            parts = parts[1:]

        target_override, parts = extract_target_option(parts)
        if not parts:
            return render_admin_help()

        cmd = parts[0].lower()
        handler_cls = AdminCommandHandler.registry.get(cmd)
        if handler_cls is None:
            return get_locale_text("i18n_cli_core.err_admin_unknown")

        from .resolvers import resolve_target_user

        target_user_id = user_id
        if target_override:
            resolved_uid = resolve_target_user(self.server.save_manager, target_override)
            if resolved_uid is None:
                return get_locale_text("i18n_admin.err_user_not_found", user=target_override)
            target_user_id = resolved_uid

        ctx = AdminContext(
            server=self.server,
            caller_user_id=user_id,
            target_user_id=target_user_id,
            command=cmd,
            args=parts[1:],
        )
        handler = handler_cls()
        return await handler.execute(ctx)


CATEGORY_ORDER = ("config", "entity", "battle", "world", "save")


def render_admin_help(topic: str = "") -> str:
    if topic:
        cls = AdminCommandHandler.registry.get(topic.lower())
        if cls is None:
            return get_locale_text("i18n_admin.err_help_topic_not_found", topic=topic)
        key = cls.detail_key or cls.help_key
        if not key:
            return get_locale_text("i18n_admin.err_help_topic_not_found", topic=topic)
        aliases_str = ", ".join(cls.aliases)
        return get_locale_text(
            "i18n_admin.help_detail_wrap",
            cmd=cls.aliases[0],
            aliases=aliases_str,
            body=get_locale_text(key),
        )

    lines = [get_locale_text("i18n_admin.help_header")]
    grouped: dict[str, list[Type[AdminCommandHandler]]] = {}
    for cls in AdminCommandHandler.ordered_handlers:
        if not cls.help_key:
            continue
        grouped.setdefault(cls.category, []).append(cls)

    for cat in CATEGORY_ORDER:
        items = grouped.get(cat)
        if not items:
            continue
        lines.append("")
        lines.append(get_locale_text(f"i18n_admin.cat_{cat}"))
        for cls in items:
            lines.append(get_locale_text(cls.help_key))

    lines.append("")
    lines.append(get_locale_text("i18n_admin.help_footer"))
    return "\n".join(lines)
