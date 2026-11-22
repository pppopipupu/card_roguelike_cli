from typing import TYPE_CHECKING, Optional

from ...models.state import GameRun
from ...data.text.locale_data import get_locale_text
from ...data.entities.minions.minion_data import MINION_CONFIG
from ...entities import ALL_MINIONS
from ...models.events import MinionSkillUsedEvent
from .card_player_turn import CardPlayerEngineMixin
from .selection import TargetSelectorParser


class CardPlayerMinionMixin(CardPlayerEngineMixin):
    """随从攻击与技能指令，保持 CardPlayer 门面职责单一。"""

    if TYPE_CHECKING:
        def _post_battle_action_check(self, run, initial_status, res, p) -> str: ...

    def minion_attack(self, run: GameRun, my_grid: str, opp_grid: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return get_locale_text("i18n_battle_core.not_in_battle_minion_attack")
        if p.downed:
            return get_locale_text("i18n_battle_core.downed_cannot_command")
        if my_grid not in p.minions:
            return get_locale_text("i18n_battle_core.own_grid_empty", grid=my_grid)
        m = p.minions[my_grid]
        if m.attack_actions < 1:
            return get_locale_text("i18n_battle_core.minion_no_attack_actions")
        if opp_grid is None:
            opp_grid = self.engine._get_first_alive_enemy(run)
        else:
            resolved_opp, opp_err = TargetSelectorParser.resolve_simple_target(run, opp_grid, engine=self.engine)
            if opp_err or not resolved_opp or not resolved_opp.startswith("e"):
                return get_locale_text("i18n_battle_core.enemy_grid_invalid", target=opp_grid)
            opp_grid = resolved_opp
        m.attack_actions -= 1
        try:
            opp_idx = int(opp_grid.replace("e", "")) - 1
            if opp_idx < 0:
                opp_idx = 0
        except ValueError:
            opp_idx = 0
        if opp_idx < 0 or opp_idx >= len(run.enemies):
            return get_locale_text("i18n_battle_core.enemy_grid_invalid", target=opp_grid)
        enemy = run.enemies[opp_idx]
        opp_grid = f"e{opp_idx+1}"
        dtype = MINION_CONFIG.get(m.id, {}).get("attack_damage_type", "bludgeoning")
        self.engine._damage_target(run, opp_grid, m.atk, source=f"p{my_grid}", damage_type=dtype, is_attack=True)
        res = get_locale_text("i18n_battle_core.minion_attack_log", minion=m.name, enemy=enemy.name)
        self.engine.save_manager.save_save(run.user_id, run)
        res = self._post_battle_action_check(run, initial_status, res, p)
        return self.engine._append_logs_to_res(run, res)

    def minion_skill(self, run: GameRun, my_grid: str, skill_idx: int = 1, target: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return get_locale_text("i18n_battle_core.not_in_battle_minion_skill")
        if p.downed:
            return get_locale_text("i18n_battle_core.downed_cannot_skill")
        if my_grid not in p.minions:
            return get_locale_text("i18n_battle_core.own_grid_empty", grid=my_grid)
        m = p.minions[my_grid]
        if m.id not in ALL_MINIONS:
            return get_locale_text("i18n_battle_core.minion_no_skills", name=m.name)
        template = ALL_MINIONS[m.id]
        skills_list = template.skills
        if skill_idx < 1 or skill_idx > len(skills_list):
            skills_desc = "\n".join([f" [{idx}] {s.name}: {s.desc}" for idx, s in enumerate(skills_list, 1)])
            return get_locale_text("i18n_battle_core.invalid_skill_index", name=m.name, skills=skills_desc)
        skill = skills_list[skill_idx - 1]
        cost_a = skill.cost_a
        cost_ba = skill.cost_ba
        if m.actions < cost_a or m.bonus_actions < cost_ba:
            return get_locale_text("i18n_battle_core.minion_insufficient_resources", cost_a=cost_a, cost_ba=cost_ba, actions=m.actions, bonus_actions=m.bonus_actions)
        needs_target = getattr(skill, "target_type", None) == "enemy"
        if needs_target:
            if target is None:
                target = self.engine._get_first_alive_enemy(run)
            else:
                resolved_target, target_err = TargetSelectorParser.resolve_simple_target(run, target, engine=self.engine)
                if target_err:
                    return get_locale_text("i18n_battle_core.invalid_target_enemy_only")
                target = resolved_target
            if target is None:
                return get_locale_text("i18n_battle_core.enemy_target_missing", target="")
            if isinstance(target, str) and target.isdigit():
                target = f"e{target}"
            if target == "0" or target == "e0":
                target = "e1"
            if target.startswith("e"):
                try:
                    idx = int(target[1:]) - 1
                except ValueError:
                    idx = 0
                if idx < 0 or idx >= len(run.enemies):
                    return get_locale_text("i18n_battle_core.enemy_target_missing", target=target)
            else:
                return get_locale_text("i18n_battle_core.invalid_target_enemy_only")
        m.actions -= cost_a
        m.bonus_actions -= cost_ba
        msg = get_locale_text("i18n_battle_core.minion_skill_log", minion=m.name, skill=skill.name)
        run.node_data["current_acting_minion_grid"] = my_grid
        try:
            effect_msg = skill.execute(run, my_grid, target, self.engine)
        finally:
            run.node_data.pop("current_acting_minion_grid", None)
        msg += effect_msg
        from ...models.events import MinionSkillUsedEvent
        self.engine.event_bus.dispatch(MinionSkillUsedEvent(run, p, m, my_grid, skill, target))
        self.engine.save_manager.save_save(run.user_id, run)
        msg = self._post_battle_action_check(run, initial_status, msg, p)
        return self.engine._append_logs_to_res(run, msg)
