from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class SkillCommand(CommandHandler, names=["技能", "skill", "sk", "k"], allowed_states=["battle"], help_key="skill"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run or run.node_type != "battle":
            yield get_locale_text("i18n_cli_commands.battle_skill_not_in_battle")
            return
        stats = router.save_manager.load_stats(user_id)
        p_class = getattr(stats, "selected_class", "法师")
        if p_class != "战士":
            yield get_locale_text("i18n_cli_commands.battle_skill_wrong_class")
            return
        skill_arg = parts[1].lower() if len(parts) >= 2 else "as"
        if skill_arg not in ("as", "action_surge", "动作如潮"):
            yield get_locale_text("i18n_cli_commands.battle_skill_usage")
            return
        p = run.player
        if p.downed:
            yield get_locale_text("i18n_cli_commands.battle_skill_downed")
            return
        surge_key = run.turn_key("action_surge_uses", p)
        used_key = run.turn_key("action_surge_turn_used", p)
        uses = run.node_data.get(surge_key, 0)
        if uses <= 0:
            yield get_locale_text("i18n_cli_commands.battle_skill_exhausted")
            return
        if run.node_data.get(used_key, False):
            yield get_locale_text("i18n_cli_commands.battle_skill_turn_used")
            return
        run.node_data[surge_key] = uses - 1
        run.node_data[used_key] = True
        p.actions += 2
        p.bonus_actions += 1
        router.save_manager.save_save(user_id, run)
        yield get_locale_text("i18n_cli_commands.battle_skill_success", uses=uses - 1, actions=p.actions, bonus_actions=p.bonus_actions)
