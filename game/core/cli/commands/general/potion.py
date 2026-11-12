from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.potion_data import get_potion_name
from .....data.command_data import POTION_LIST_ALIASES, POTION_DRINK_ALIASES, POTION_THROW_ALIASES, POTION_DROP_ALIASES, POTION_CONTAINER_ALIASES
from .....data.locale_data import get_locale_text

class PotionCommand(CommandHandler, names=["药水", "喝药水", "potion", "drink", "use_potion", "丢弃药水", "discard_potion", "drop_potion", "drop", "丢药", "dp", "dr", "pot", "投掷", "投", "throw", "t"], allowed_states=["battle", "explore", "town", "menu"], help_key="potion"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_a.potion.no_run")
            return

        p = run.player
        if not hasattr(p, "potions"):
            p.potions = []

        action, args = self._parse(parts)
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

        try:
            idx = int(args[0]) - 1
        except ValueError:
            yield get_locale_text("i18n_cli_general_a.potion.invalid_slot")
            return

        if idx < 0 or idx >= len(p.potions):
            yield get_locale_text("i18n_cli_general_a.potion.invalid_slot_count", count=len(p.potions))
            return

        potion_id = p.potions[idx]
        potion_name = get_potion_name(potion_id)

        if action == "drop":
            p.potions.pop(idx)
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

        if run.node_type != "battle" and potion_id != "healing_potion":
            yield get_locale_text("i18n_cli_general_a.potion.battle_only")
            return

        p.potions.pop(idx)
        res_msg = router.engine.potion_resolver.use_potion(run, potion_id, target, is_throw)
        if run.node_type == "battle":
            res_msg = router.engine.battle_engine._append_logs_to_res(run, res_msg)
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
