from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.potion_data import get_potion_name
from .....data.locale_data import get_locale_text

class PotionCommand(CommandHandler, names=["药水", "喝药水", "potion", "drink", "use_potion", "丢弃药水", "discard_potion", "drop_potion", "丢药", "dp", "dr", "pot", "投掷", "投", "throw", "t"], allowed_states=["battle", "explore", "town", "menu"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_a.potion.no_run")
            return
        
        p = run.player
        if not hasattr(p, "potions"):
            p.potions = []
            
        cmd = parts[0].lower()
        is_discard = cmd in ("丢弃药水", "discard_potion", "drop_potion", "丢药", "dp")
        if getattr(run, "coop_id", "") and p.downed and not is_discard:
            yield get_locale_text("i18n_cli_general_a.potion.downed")
            return
        
        if len(parts) < 2:
            if is_discard:
                yield get_locale_text("i18n_cli_general_a.potion.discard_need_slot")
            else:
                yield get_locale_text("i18n_cli_general_a.potion.use_need_slot")
            return
            
        try:
            idx = int(parts[1]) - 1
        except ValueError:
            yield get_locale_text("i18n_cli_general_a.potion.invalid_slot")
            return
            
        if idx < 0 or idx >= len(p.potions):
            yield get_locale_text("i18n_cli_general_a.potion.invalid_slot_count", count=len(p.potions))
            return
            
        potion_id = p.potions[idx]
        potion_name = get_potion_name(potion_id)
        
        if is_discard:
            p.potions.pop(idx)
            router.save_manager.save_save(user_id, run)
            yield get_locale_text("i18n_cli_general_a.potion.discarded", name=potion_name) + GameRenderer.render_game(run)
            return

        is_throw = cmd in ("投掷", "投", "throw", "t")
        target = None
        if is_throw:
            if len(parts) < 3:
                yield get_locale_text("i18n_cli_general_a.potion.throw_need_target")
                return
            target = parts[2]
        else:
            if len(parts) >= 3:
                target = parts[2]
                is_throw = True
            else:
                target = "p0"
                
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
            elif getattr(run, "coop_id", "") and router.engine.battle_engine.combat_resolver.resolve_ally(run, target):
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
