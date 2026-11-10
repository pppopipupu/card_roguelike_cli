from ..cli.base import split_by_comma_with_brackets, CommandHandler
from ...data.balance_config import QUEUE_MAX_COMMANDS
from ...data.locale_data import get_locale_text

QUEUE_ALIASES = ("队列", "q", "queue", "qi", "queue_interrupt", "中断队列")


def _queue_items(content: str) -> list[str]:
    content = content.strip()
    if content.startswith("[") and content.endswith("]"):
        content = content[1:-1].strip()
    return split_by_comma_with_brackets(content)


def count_queue_commands(content: str) -> int:
    total = 0
    for item in _queue_items(content):
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
        is_top_level = not run.node_data.get("in_queue", False)
        if is_top_level:
            run.node_data["in_queue"] = True
            self.save_manager.save_save(user_id, run)
        try:
            content = queue_content.strip()
            if content.startswith("[") and content.endswith("]"):
                content = content[1:-1].strip()
            items = split_by_comma_with_brackets(content)
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
                    curr_state = run.node_type if run else "menu"
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
                        res = "\n".join(res_list)
                    elif exists:
                        res = get_locale_text("i18n_cli_commands.err_command_unavailable", sub=first_sub)
                        success = False
                    else:
                        res, term, success = router.action_router.execute_action(router, user_id, run, parts_sub)
                    results.append(res)
                    if interrupt_on_fail and not success:
                        return True
                    if term:
                        return True
            return False
        finally:
            if is_top_level:
                latest_run = self.save_manager.load_save(user_id)
                if latest_run:
                    latest_run.node_data.pop("in_queue", None)
                    self.save_manager.save_save(user_id, latest_run)
