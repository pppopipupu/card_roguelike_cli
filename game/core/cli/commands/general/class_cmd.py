from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class ClassCommand(CommandHandler, names=["职业", "class"], allowed_states=["menu", "town"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        selected_class = getattr(stats, "selected_class", "法师")
        selected_subclass = getattr(stats, "selected_subclass", "") or get_locale_text("i18n_cli_general_a.class.none")
        if len(parts) == 1:
            from .....data.shop_data import SHOP_ITEMS
            gp = getattr(stats, "gp", 0)
            unlocked = getattr(stats, "unlocked_subclasses", [])
            status_time = get_locale_text("i18n_cli_general_a.class.status_unlocked") if "时序法师" in unlocked else get_locale_text("i18n_cli_general_a.class.status_locked", price=SHOP_ITEMS['时序法师']['price'])
            status_element = get_locale_text("i18n_cli_general_a.class.status_unlocked") if "塑能法师" in unlocked else get_locale_text("i18n_cli_general_a.class.status_locked", price=SHOP_ITEMS['塑能法师']['price'])
            status_key = get_locale_text("i18n_cli_general_a.class.status_unlocked") if "秘钥学者" in unlocked else get_locale_text("i18n_cli_general_a.class.status_locked", price=SHOP_ITEMS['秘钥学者']['price'])
            lines = [
                get_locale_text("i18n_cli_general_a.class.separator"),
                get_locale_text("i18n_cli_general_a.class.title"),
                "",
                get_locale_text("i18n_cli_general_a.class.gp", gp=gp),
                get_locale_text("i18n_cli_general_a.class.current", class_name=selected_class, subclass=selected_subclass),
                "",
                get_locale_text("i18n_cli_general_a.class.main_title"),
                get_locale_text("i18n_cli_general_a.class.main_wizard"),
                get_locale_text("i18n_cli_general_a.class.main_wizard_desc"),
                get_locale_text("i18n_cli_general_a.class.main_warrior"),
                get_locale_text("i18n_cli_general_a.class.main_warrior_desc"),
                "",
                get_locale_text("i18n_cli_general_a.class.sub_title"),
                get_locale_text("i18n_cli_general_a.class.sub_time", status=status_time),
                get_locale_text("i18n_cli_general_a.class.sub_time_desc"),
                get_locale_text("i18n_cli_general_a.class.sub_element", status=status_element),
                get_locale_text("i18n_cli_general_a.class.sub_element_desc"),
                get_locale_text("i18n_cli_general_a.class.sub_key", status=status_key),
                get_locale_text("i18n_cli_general_a.class.sub_key_desc"),
                "",
                get_locale_text("i18n_cli_general_a.class.commands_title"),
                get_locale_text("i18n_cli_general_a.class.cmd_wizard"),
                get_locale_text("i18n_cli_general_a.class.cmd_warrior"),
                get_locale_text("i18n_cli_general_a.class.cmd_sub_time"),
                get_locale_text("i18n_cli_general_a.class.cmd_sub_element"),
                get_locale_text("i18n_cli_general_a.class.cmd_sub_key"),
                get_locale_text("i18n_cli_general_a.class.cmd_sub_none"),
                get_locale_text("i18n_cli_general_a.class.cmd_buy_hint"),
                get_locale_text("i18n_cli_general_a.class.separator")
            ]
            yield "\n".join(lines)
        else:
            action = None
            subclass_arg = None
            if len(parts) == 2:
                action = "选择"
                subclass_arg = parts[1]
            elif len(parts) >= 3:
                action = parts[1]
                subclass_arg = parts[2]
            if action in ("购买", "buy"):
                yield get_locale_text("i18n_cli_general_a.class.buy_hint")
            elif action in ("选择", "c", "choose", "select"):
                if subclass_arg in ("战士", "warrior", "war"):
                    stats.selected_class = "战士"
                    stats.selected_subclass = ""
                    router.save_manager.save_stats(user_id, stats)
                    yield get_locale_text("i18n_cli_general_a.class.switched_warrior")
                    return
                elif subclass_arg in ("法师", "wizard", "wiz"):
                    stats.selected_class = "法师"
                    router.save_manager.save_stats(user_id, stats)
                    yield get_locale_text("i18n_cli_general_a.class.switched_wizard")
                    return
                if selected_class == "战士":
                    yield get_locale_text("i18n_cli_general_a.class.warrior_no_sub")
                    return
                if subclass_arg in ("1", "时序法师", "chronomancer", "time"):
                    subclass_name = "时序法师"
                elif subclass_arg in ("2", "塑能法师", "evoker", "elemental"):
                    subclass_name = "塑能法师"
                elif subclass_arg in ("3", "秘钥学者", "arcanist", "key"):
                    subclass_name = "秘钥学者"
                elif subclass_arg in ("0", "无", "取消", "none"):
                    subclass_name = ""
                else:
                    yield get_locale_text("i18n_cli_general_a.class.invalid_sub")
                    return
                if subclass_name == "":
                    stats.selected_subclass = ""
                    router.save_manager.save_stats(user_id, stats)
                    yield get_locale_text("i18n_cli_general_a.class.sub_cancelled")
                    return
                unlocked = getattr(stats, "unlocked_subclasses", [])
                if subclass_name not in unlocked:
                    from .....data.shop_data import SHOP_ITEMS
                    price = SHOP_ITEMS.get(subclass_name, {}).get("price", 2888)
                    yield get_locale_text("i18n_cli_general_a.class.sub_locked", subclass_name=subclass_name, price=price)
                    return
                stats.selected_subclass = subclass_name
                router.save_manager.save_stats(user_id, stats)
                yield get_locale_text("i18n_cli_general_a.class.sub_selected", subclass_name=subclass_name)
            else:
                yield get_locale_text("i18n_cli_general_a.class.invalid_format")
