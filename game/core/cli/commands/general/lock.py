from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....entities import ALL_CARDS
from .....data.locale_data import get_locale_text
from .....data.starting_deck_config import LOCK_PRICE_GP, LOCK_SLOT_LIMIT

class LockCommand(CommandHandler, names=["锁定", "lock", "锁定管理", "解锁", "unlock"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        if not hasattr(stats, "locked_cards") or stats.locked_cards is None:
            stats.locked_cards = []
        locked_list = stats.locked_cards
        cmd = parts[0].lower()

        rarity_map = {
            "common": get_locale_text("i18n_cli_general_a.lock.rarity_common"),
            "rare": get_locale_text("i18n_cli_general_a.lock.rarity_rare"),
            "epic": get_locale_text("i18n_cli_general_a.lock.rarity_epic"),
            "legendary": get_locale_text("i18n_cli_general_a.lock.rarity_legendary"),
            "mythic": get_locale_text("i18n_cli_general_a.lock.rarity_mythic"),
            "artifact": get_locale_text("i18n_cli_general_a.lock.rarity_artifact"),
            "curse": get_locale_text("i18n_cli_general_a.lock.rarity_curse")
        }

        if len(parts) == 1:
            if cmd in ("解锁", "unlock"):
                yield get_locale_text("i18n_cli_general_a.lock.unlock_need_name")
                return

            gp = getattr(stats, "gp", 0)
            lines = [
                get_locale_text("i18n_cli_general_a.lock.separator"),
                get_locale_text("i18n_cli_general_a.lock.title"),
                get_locale_text("i18n_cli_general_a.lock.separator"),
                get_locale_text("i18n_cli_general_a.lock.gp", gp=gp),
                get_locale_text("i18n_cli_general_a.lock.locked_count", count=len(locked_list), limit=LOCK_SLOT_LIMIT),
            ]
            if locked_list:
                for idx, cid in enumerate(locked_list):
                    c_obj = ALL_CARDS.get(cid)
                    cname = c_obj.name if c_obj else cid
                    crarity_ch = rarity_map.get(getattr(c_obj, "rarity", "common"), get_locale_text("i18n_cli_general_a.lock.rarity_common"))
                    lines.append(get_locale_text("i18n_cli_general_a.lock.locked_entry", idx=idx+1, name=cname, rarity=crarity_ch))
            else:
                lines.append(get_locale_text("i18n_cli_general_a.lock.locked_empty"))

            lines.extend([
                "",
                get_locale_text("i18n_cli_general_a.lock.rules_title"),
                get_locale_text("i18n_cli_general_a.lock.rule_1"),
                get_locale_text("i18n_cli_general_a.lock.rule_2", limit=LOCK_SLOT_LIMIT),
                get_locale_text("i18n_cli_general_a.lock.rule_3"),
                get_locale_text("i18n_cli_general_a.lock.rule_4", price=LOCK_PRICE_GP),
                get_locale_text("i18n_cli_general_a.lock.rule_5"),
                "",
                get_locale_text("i18n_cli_general_a.lock.commands_title"),
                get_locale_text("i18n_cli_general_a.lock.cmd_lock", price=LOCK_PRICE_GP),
                get_locale_text("i18n_cli_general_a.lock.cmd_unlock"),
                get_locale_text("i18n_cli_general_a.lock.cmd_clear"),
                get_locale_text("i18n_cli_general_a.lock.separator")
            ])
            yield "\n".join(lines)
            return

        arg1 = parts[1].strip()
        if arg1.lower() in ("clear", "清空", "重置", "reset") and cmd in ("锁定", "lock", "锁定管理"):
            stats.locked_cards.clear()
            router.save_manager.save_stats(user_id, stats)
            yield get_locale_text("i18n_cli_general_a.lock.clear_success")
            return

        is_unlock = (cmd in ("解锁", "unlock")) or (arg1.lower() in ("unlock", "解锁", "remove", "移除"))
        if is_unlock:
            card_name = parts[2].strip() if arg1.lower() in ("unlock", "解锁", "remove", "移除") and len(parts) >= 3 else arg1
            target_cid = None
            for cid, c_obj in ALL_CARDS.items():
                if c_obj.name == card_name or cid.lower() == card_name.lower():
                    target_cid = cid
                    break
            
            if not target_cid and card_name.endswith("+"):
                base_name = card_name[:-1]
                for cid, c_obj in ALL_CARDS.items():
                    if c_obj.name == base_name or cid.lower() == base_name.lower():
                        target_cid = cid
                        break

            if not target_cid:
                target_cid = card_name

            if target_cid in stats.locked_cards:
                stats.locked_cards.remove(target_cid)
                router.save_manager.save_stats(user_id, stats)
                c_obj = ALL_CARDS.get(target_cid)
                cname = c_obj.name if c_obj else target_cid
                yield get_locale_text("i18n_cli_general_a.lock.unlock_success", name=cname)
            else:
                yield get_locale_text("i18n_cli_general_a.lock.unlock_missing", name=card_name)
            return

        card_name = arg1
        target_cid = None
        for cid, c_obj in ALL_CARDS.items():
            if c_obj.name == card_name or cid.lower() == card_name.lower():
                target_cid = cid
                break

        if not target_cid:
            yield get_locale_text("i18n_cli_general_a.lock.card_not_found", name=card_name)
            return

        if target_cid.endswith("+"):
            target_cid = target_cid[:-1]

        c_obj = ALL_CARDS[target_cid]
        r = getattr(c_obj, "rarity", "common")
        if r in ("legendary", "mythic", "artifact", "curse"):
            yield get_locale_text("i18n_cli_general_a.lock.lock_rarity_denied", rarity=rarity_map.get(r, r))
            return

        if target_cid in stats.locked_cards:
            yield get_locale_text("i18n_cli_general_a.lock.lock_already", name=c_obj.name)
            return

        if len(stats.locked_cards) >= LOCK_SLOT_LIMIT:
            yield get_locale_text("i18n_cli_general_a.lock.lock_limit", limit=LOCK_SLOT_LIMIT)
            return

        if stats.gp < LOCK_PRICE_GP:
            yield get_locale_text("i18n_cli_general_a.lock.lock_no_gp", gp=stats.gp, price=LOCK_PRICE_GP)
            return

        stats.gp -= LOCK_PRICE_GP
        stats.locked_cards.append(target_cid)
        router.save_manager.save_stats(user_id, stats)
        yield get_locale_text("i18n_cli_general_a.lock.lock_success", name=c_obj.name, price=LOCK_PRICE_GP)
