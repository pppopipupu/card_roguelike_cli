from ..cli.base import CommandHandler
from .state_resolver import resolve_game_state
from ...data.progression.balance_config import QUEUE_MAX_COMMANDS
from ...data.text.locale_data import get_locale_text
from ...models.state import in_queue_ctx

QUEUE_ALIASES = ("队列", "q", "queue", "qi", "queue_interrupt", "中断队列")


def split_queue_items(content: str) -> list[str]:
    content = content.strip()
    bracketed = content.startswith("[") and content.endswith("]")
    if bracketed:
        content = content[1:-1].strip()
    separators = {",", "，", ";", "；", "\n"} if bracketed else {";", "；", "\n"}
    items: list[str] = []
    current: list[str] = []
    depth = 0
    for char in content:
        if char == "[":
            depth += 1
            current.append(char)
        elif char == "]":
            depth = max(0, depth - 1)
            current.append(char)
        elif char in separators and depth == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
        else:
            current.append(char)
    item = "".join(current).strip()
    if item:
        items.append(item)
    return items


def count_queue_commands(content: str) -> int:
    total = 0
    for item in split_queue_items(content):
        parts = item.split()
        if not parts:
            continue
        if parts[0].lower() in QUEUE_ALIASES:
            total += count_queue_commands(item[len(parts[0]):].strip())
        else:
            total += 1
    return total


class QueueProcessor:
    def __init__(self, save_manager, engine):
        self.save_manager = save_manager
        self.engine = engine

    def execute_queue(self, router, user_id: str, run, queue_content: str, results: list[str], interrupt_on_fail: bool = False) -> bool:
        if count_queue_commands(queue_content) > QUEUE_MAX_COMMANDS:
            results.append(get_locale_text("i18n_cli_commands.battle_queue_limit", limit=QUEUE_MAX_COMMANDS))
            return True
        is_top_level = not in_queue_ctx.get() and not run.node_data.get("in_queue", False)
        queue_token = in_queue_ctx.set(True) if is_top_level else None
        if is_top_level:
            run.node_data["in_queue"] = True
            self.save_manager.save_save(user_id, run)
        try:
            items = split_queue_items(queue_content)
            for item in items:
                if not item:
                    continue
                parts_sub = item.split()
                if not parts_sub:
                    continue
                first_sub = parts_sub[0].lower()
                if first_sub in ("队列", "q", "queue", "qi", "queue_interrupt", "中断队列"):
                    sub_content = item[len(parts_sub[0]):].strip()
                    term = self.execute_queue(router, user_id, run, sub_content, results, interrupt_on_fail)
                    if term:
                        return True
                else:
                    latest_run = self.save_manager.load_save(user_id)
                    if latest_run is not None and not latest_run.node_data.get("in_queue"):
                        latest_run.node_data["in_queue"] = True
                        self.save_manager.save_save(user_id, latest_run)
                    curr_state = resolve_game_state(
                        latest_run,
                        self.save_manager.load_stats(user_id) if latest_run is None else None,
                    )
                    cmd_handler, exists = CommandHandler.resolve(first_sub, curr_state)
                    term = False
                    if cmd_handler:
                        gen = cmd_handler.execute(router, user_id, parts_sub)
                        res_list = []
                        success = True
                        try:
                            while True:
                                res_list.append(next(gen))
                        except StopIteration as e:
                            success = e.value if e.value is not None else True
                        res = "\n".join(r.strip() for r in res_list if r and r.strip())
                    elif exists:
                        res = get_locale_text("i18n_cli_commands.err_command_unavailable", sub=first_sub)
                        success = False
                    elif latest_run is not None:
                        res, term, success = router.action_router.execute_action(router, user_id, latest_run, parts_sub)
                    else:
                        res = get_locale_text("i18n_cli_commands.err_unknown_command", sub=first_sub)
                        success = False
                    if res and res.strip():
                        results.append(res.strip())
                    if interrupt_on_fail and not success:
                        return True
                    if term:
                        return True
            return False
        finally:
            if queue_token is not None:
                in_queue_ctx.reset(queue_token)
            if is_top_level:
                latest_run = self.save_manager.load_save(user_id)
                if latest_run:
                    latest_run.node_data.pop("in_queue", None)
                    fm = getattr(latest_run, "floor_map", None)
                    if fm is not None:
                        for sess in (getattr(fm, "active_sessions", None) or {}).values():
                            if isinstance(sess, dict):
                                (sess.get("node_data") or {}).pop("in_queue", None)
                            elif getattr(sess, "node_data", None):
                                sess.node_data.pop("in_queue", None)
                    self.save_manager.save_save(user_id, latest_run)
