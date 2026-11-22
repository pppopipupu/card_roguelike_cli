from typing import Optional, List


class BaseMinionSkill:
    """随从技能声明：名称、费用、描述与目标类型。"""

    def __init__(self, name: str, cost_a: int, cost_ba: int, desc: str, target_type: Optional[str] = None):
        self.name = name
        self.cost_a = cost_a
        self.cost_ba = cost_ba
        self.desc = desc
        self.target_type = target_type

    def execute(self, run, my_grid: str, target: Optional[str], engine) -> str:
        """处理 execute 生命周期扩展，具体字段与取消语义见事件定义。"""
        return ""


class MinionTemplate:
    """随从行为模板，由 MinionTriggerHandler 转发战斗事件到生命周期钩子。"""

    def __init__(self, id: str, name: str, skills: List[BaseMinionSkill]):
        self.id = id
        self.name = name
        self.skills = skills

    def on_turn_start(self, run, grid, event, engine):
        """回合开始时按数据配置重置随从攻击力。"""
        from ...data.entities.minions.minion_data import MINION_CONFIG
        state = run.player.minions.get(grid)
        if state is None:
            return
        cfg = MINION_CONFIG.get(state.id, {})
        reset_atk = cfg.get("reset_atk")
        if reset_atk is not None:
            state.atk = int(reset_atk)

    def on_minion_skill_used(self, run, grid, event, engine):
        """处理 on_minion_skill_used 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_minion_death(self, run, grid, event, engine):
        """处理 on_minion_death 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_played(self, run, grid, event, engine):
        """处理 on_card_played 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_shield_gain(self, run, grid, event, engine):
        """处理 on_shield_gain 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_take(self, run, grid, event, engine):
        """处理 on_damage_take 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_exhaust(self, run, grid, event, engine):
        """处理 on_card_exhaust 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_turn_end(self, run, grid, event, engine):
        """处理 on_turn_end 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_calculate(self, run, grid, event, engine):
        """处理 on_damage_calculate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_attack(self, run, grid, event, engine):
        """处理 on_attack 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_minion_summon(self, run, grid, event, engine):
        """处理 on_minion_summon 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass
