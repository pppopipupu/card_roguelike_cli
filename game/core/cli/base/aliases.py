NODE_EXIT_ALIASES = ("exit", "quit", "leave", "lv", "离开", "退出")
NODE_CANCEL_ALIASES = ("取消", "cancel", "返回")
STATE_STACK_CANCEL_ALIASES = ("取消", "cancel", "abandon", "放弃", "exit", "quit", "退出")


def has_pending_node_cancel(run) -> bool:
    if run is None or getattr(run, "node_type", "") == "battle":
        return False
    if run.node_data.get("pending_remove") or run.node_data.get("pending_upgrade"):
        return True
    return run.node_type == "gem_insert"


def normalize_node_alias(run, parts: list[str]) -> list[str]:
    if not parts:
        return parts
    head = parts[0].lower()
    if head.isdigit() or head in NODE_EXIT_ALIASES:
        return ["选择"] + parts
    if head in NODE_CANCEL_ALIASES and has_pending_node_cancel(run):
        return ["选择"] + parts
    return parts
