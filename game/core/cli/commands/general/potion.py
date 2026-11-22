from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.entities.potion_data import POTION_CONFIG, get_potion_name
from .....data.text.command_data import POTION_LIST_ALIASES, POTION_DRINK_ALIASES, POTION_THROW_ALIASES, POTION_DROP_ALIASES, POTION_CONTAINER_ALIASES
from .....data.text.locale_data import get_locale_text
from ....inventory.bag_service import drop_bag_item, format_weight, get_bag_max_weight, get_bag_weight, get_player_potions, resolve_item_query

class PotionCommand(CommandHandler, names=["药水", "喝药水", "potion", "drink", "use_potion", "丢弃药水", "discard_potion", "drop_potion", "drop", "丢药", "dp", "dr", "pot", "投掷", "投", "throw", "t"], allowed_states=["battle", "grid_map", "explore", "cafe", "town", "menu"], help_key="potion"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        action, args = self._parse(parts)
        if not run:
            if action == "list":
                stats = router.save_manager.load_stats(user_id)
                yield GameRenderer.render_bag(stats)
                return
            yield get_locale_text("i18n_cli_general_a.potion.no_run")
            return
        p = run.player
        if not hasattr(p, "bag_items") or p.bag_items is None:
            p.bag_items = []
        potions = get_player_potions(p)

        if action == "list":
            yield GameRenderer.render_potion_list(run)
            return
        if action == "drop" and not args:
            yield get_locale_text("i18n_cli_general_a.potion.drop_need_slot")
            return
        if action == "throw" and not args:
            yield get_locale_text("i18n_cli_general_a.potion.throw_need_slot")
            return
        if not args:
            yield get_locale_text("i18n_cli_general_a.potion.drink_need_slot")
            return
        if action != "drop" and p.downed:
            yield get_locale_text("i18n_cli_general_a.potion.downed")
            return

        bag_idx = -1
        potion_id = ""
        try:
            idx = int(args[0]) - 1
        except ValueError:
            matched = resolve_item_query(args[0], [f"potion:{pid}" for _, pid in potions])
            if matched:
                for b_idx, pid in potions:
                    if f"potion:{pid}" == matched:
                        bag_idx = b_idx
                        potion_id = pid
                        break
            elif action == "drop":
                msg = drop_bag_item(run, " ".join(args))
                router.save_manager.save_save(user_id, run)
                yield msg
                return
            else:
                yield get_locale_text("i18n_cli_general_a.potion.invalid_slot")
                return
        else:
            if idx < 0 or idx >= len(potions):
                yield get_locale_text("i18n_cli_general_a.potion.invalid_slot_count", count=len(potions))
                return
            bag_idx, potion_id = potions[idx]

        if bag_idx < 0:
            yield get_locale_text("i18n_cli_general_a.potion.invalid_slot")
            return
        potion_name = get_potion_name(potion_id)

        if action == "drop":
            p.bag_items.pop(bag_idx)
            router.save_manager.save_save(user_id, run)
            yield get_locale_text("i18n_cli_general_a.potion.discarded", name=potion_name) + GameRenderer.render_game(run)
            return

        is_throw = action == "throw"
        target = "p0"
        if is_throw:
            if len(args) >= 2:
                target = args[1]
            elif run.node_type != "battle":
                yield get_locale_text("i18n_cli_general_a.potion.throw_battle_only")
                return
            elif not run.enemies:
                yield get_locale_text("i18n_cli_general_a.potion.no_enemy", target="e1")
                return
            else:
                target = "e1"
        elif len(args) >= 2:
            target = args[1]
            is_throw = True

        if target != "p0":
            if run.node_type != "battle":
                yield get_locale_text("i18n_cli_general_a.potion.throw_battle_only")
                return
            if isinstance(target, str) and target.isdigit():
                target = f"e{target}"
            if target == "0" or target == "e0":
                target = "e1"
            elif target == "p":
                target = "p0"
                is_throw = False

            if target.startswith("e"):
                try:
                    grid = int(target[1:]) - 1
                except ValueError:
                    grid = 0
                if grid < 0 or grid >= len(run.enemies):
                    yield get_locale_text("i18n_cli_general_a.potion.no_enemy", target=target)
                    return
            elif target.startswith("p"):
                grid = target[1:]
                if grid != "0" and grid not in p.minions:
                    yield get_locale_text("i18n_cli_general_a.potion.no_minion", grid=grid)
                    return
            elif (ally_resolved := router.engine.battle_engine.combat_resolver.resolve_ally(run, target)):
                _, ally_player, ally_grid = ally_resolved
                if ally_player.downed or ally_player.hp <= 0:
                    yield get_locale_text("i18n_battle_misc.coop_ally_downed", name=ally_player.name)
                    return
                if ally_grid is not None and ally_grid not in ally_player.minions:
                    yield get_locale_text("i18n_battle_misc.coop_ally_minion_empty", name=ally_player.name, grid=ally_grid)
                    return
                is_throw = False
            else:
                yield get_locale_text("i18n_cli_general_a.potion.invalid_target")
                return

        if run.node_type != "battle" and not POTION_CONFIG.get(potion_id, {}).get("usable_out_of_battle", False):
            yield get_locale_text("i18n_cli_general_a.potion.battle_only")
            return

        p.bag_items.pop(bag_idx)
        res_msg = router.engine.potion_resolver.use_potion(run, potion_id, target, is_throw)
        if run.node_type == "battle":
            res_msg = router.engine.battle_engine._append_logs_to_res(run, res_msg)
            if router.engine.battle_engine.is_battle_won(run):
                router.engine.battle_engine._handle_battle_win(run)
        router.save_manager.save_save(user_id, run)
        yield res_msg + "\n" + GameRenderer.render_game(run)

    def _parse(self, parts: list[str]):
        head = parts[0].lower()
        args = parts[1:]
        if head in POTION_CONTAINER_ALIASES:
            if not args:
                return "list", args
            sub = args[0].lower()
            if sub in POTION_LIST_ALIASES:
                return "list", args[1:]
            if sub in POTION_DROP_ALIASES:
                return "drop", args[1:]
            if sub in POTION_THROW_ALIASES:
                return "throw", args[1:]
            if sub in POTION_DRINK_ALIASES:
                return "drink", args[1:]
            return "drink", args
        if head in POTION_DROP_ALIASES:
            return "drop", args
        if head in POTION_THROW_ALIASES:
            return "throw", args
        if head in POTION_DRINK_ALIASES:
            return "drink", args
        return "drink", args
