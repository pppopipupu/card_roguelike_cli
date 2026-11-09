from typing import Optional, List


class BaseMinionSkill:
    def __init__(self, name: str, cost_a: int, cost_ba: int, desc: str):
        self.name = name
        self.cost_a = cost_a
        self.cost_ba = cost_ba
        self.desc = desc

    def execute(self, run, my_grid: str, target: Optional[str], engine) -> str:
        return ""


class MinionTemplate:
    def __init__(self, id: str, name: str, skills: List[BaseMinionSkill]):
        self.id = id
        self.name = name
        self.skills = skills

    def on_minion_death(self, run, grid, event, engine):
        pass

    def on_card_played(self, run, grid, event, engine):
        pass

    def on_shield_gain(self, run, grid, event, engine):
        pass

    def on_damage_take(self, run, grid, event, engine):
        pass

    def on_card_exhaust(self, run, grid, event, engine):
        pass

    def on_turn_end(self, run, grid, event, engine):
        pass

    def on_damage_calculate(self, run, grid, event, engine):
        pass

    def on_attack(self, run, grid, event, engine):
        pass

    def on_minion_summon(self, run, grid, event, engine):
        pass
