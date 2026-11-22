from typing import Optional
import re
from ...data.entities.relic_data import RELIC_CONFIG
from .registry import register_relic, RELIC_CLASS_REGISTRY

class RelicImpl:
    """遗物行为基类，由 RelicTriggerHandler 将战斗事件转发到生命周期钩子。

    新增遗物只需继承并通过 ``register_relic`` 注册，覆写所需钩子即可；
    严禁在核心战斗类中按遗物 ID 写特判。钩子统一接收事件、战斗与引擎。
    """

    blocks_in_turn_draw = False

    def __init__(self, relic_id: str):
        self.relic_id = relic_id
        self.name = RELIC_CONFIG.get(relic_id, {}).get("name", relic_id)
        self.desc = RELIC_CONFIG.get(relic_id, {}).get("desc", "")
        self.rarity = RELIC_CONFIG.get(relic_id, {}).get("rarity", "common")

    def on_battle_start(self, run, engine):
        """处理 on_battle_start 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_turn_start(self, event, run, engine):
        """处理 on_turn_start 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_turn_end(self, event, run, engine):
        """处理 on_turn_end 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_play(self, event, run, engine):
        """处理 on_card_play 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_played(self, event, run, engine):
        """处理 on_card_played 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_calculate(self, event, run, engine):
        """处理 on_damage_calculate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_calculate_defend(self, event, run, engine):
        """处理 on_damage_calculate_defend 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_take(self, event, run, engine):
        """处理 on_damage_take 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_take_defend(self, event, run, engine):
        """处理 on_damage_take_defend 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass
    def on_before_damage_apply(self, event, run, engine):
        """处理 on_before_damage_apply 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass


    def on_shield_gain(self, event, run, engine):
        """处理 on_shield_gain 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_shield_decay(self, event, run, engine):
        """处理 on_shield_decay 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_heal(self, event, run, engine):
        """处理 on_heal 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_heal_calculate(self, event, run, engine):
        """处理 on_heal_calculate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_node_enter(self, run, engine):
        """处理 on_node_enter 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass
    def modify_initial_draw(self, run, draw_count: int, engine) -> int:
        return draw_count

    def modify_turn_draw(self, run, draw_count: int, engine) -> int:
        return draw_count

    def on_draw_blocked(self, run, engine):
        """处理 on_draw_blocked 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_battle_win(self, run, engine):
        """处理 on_battle_win 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_minion_summon(self, event, run, engine):
        """处理 on_minion_summon 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_minion_death(self, event, run, engine):
        """处理 on_minion_death 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_reward_generate(self, event, run, engine):
        """处理 on_reward_generate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_select_init(self, event, run, engine):
        """处理 on_card_select_init 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_obtain(self, event, run, engine):
        """处理 on_card_obtain 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_hand_limit_calculate(self, event, run, engine):
        """处理 on_hand_limit_calculate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_turn_draw_calculate(self, event, run, engine):
        """处理 on_turn_draw_calculate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_before_card_draw(self, event, run, engine):
        """处理 on_before_card_draw 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_drawn(self, event, run, engine):
        """处理 on_card_drawn 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_discard(self, event, run, engine):
        """处理 on_card_discard 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_buff_applied(self, event, run, engine):
        """处理 on_buff_applied 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_player_before_death(self, event, run, engine):
        """处理 on_player_before_death 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_minion_skill_used(self, event, run, engine):
        """处理 on_minion_skill_used 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass


def get_relic_impl(relic_id: str) -> Optional[RelicImpl]:
    """按遗物 ID 获取已注册的实现类。"""
    cls = RELIC_CLASS_REGISTRY.get(relic_id)
    if cls:
        return cls(relic_id)
    return None

def get_relic_name(relic_id: str) -> str:
    """读取遗物展示名称。"""
    return RELIC_CONFIG.get(relic_id, {}).get("name", relic_id)

def get_relic_desc(relic_id: str) -> str:
    """读取遗物描述。"""
    return RELIC_CONFIG.get(relic_id, {}).get("desc", "")

def get_relic_rarity(relic_id: str) -> str:
    """读取遗物稀有度。"""
    return RELIC_CONFIG.get(relic_id, {}).get("rarity", "common")

ALL_RELIC_IDS = list(RELIC_CONFIG.keys())
