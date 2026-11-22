from typing import List, Optional
import re
from .registry import register_buff, BUFF_CLASS_REGISTRY


def is_debuff(buff_id: str) -> bool:
    """判断 Buff 是否属于负面效果，统一读取 BUFF_CONFIG 元数据。"""
    clean_id = buff_id[:-1] if buff_id.endswith("+") else buff_id
    if clean_id.startswith("minor_vulnerable_") or clean_id.startswith("vulnerable_"):
        return True
    from ...data.entities.buffs.buff_data import BUFF_CONFIG
    cfg = BUFF_CONFIG.get(clean_id, {})
    return cfg.get("is_debuff", False)


def is_positive_buff(buff_id: str) -> bool:
    """判断 Buff 是否属于正面效果，负面与硬控白名单优先排除。"""
    clean_id = buff_id[:-1] if buff_id.endswith("+") else buff_id
    if is_debuff(clean_id):
        return False
    if clean_id in ("stun", "weak", "electrified", "poison", "agony", "bleed", "void_weakness", "blind"):
        return False
    if "vulnerable" in clean_id:
        return False
    return True


class BuffImpl:
    """Buff 行为实现基类，所有具名 Buff 必须继承并通过 ``register_buff`` 注册。

    战斗事件总线在生命周期节点派发标准事件，``BuffTriggerHandler`` 会自动
    查找实体身上的 Buff 并调用同名钩子。新增 Buff 只需覆写需要的钩子，
    严禁在核心战斗类中编写针对具体 buff_id 的判断。

    统一钩子签名为 ``(event, buff_state, entity)``，引擎通过 ``event.engine``
    获取。可选类属性 ``hook_priorities`` 声明钩子执行顺序，数值越大越先执行，
    建议复用 ``event_bus`` 中的 ``PRIORITY_*`` 常量。
    """

    auto_register = True
    hook_priorities: dict[str, int] = {}

    def __init__(self, stacks: int):
        self.stacks = stacks
        self.upgraded = False
        self.stacks2: Optional[int] = None

    def on_card_play(self, event, buff_state, entity):
        """处理 on_card_play 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_played(self, event, buff_state, entity):
        """处理 on_card_played 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_turn_start(self, event, buff_state, entity):
        """处理 on_turn_start 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_turn_end(self, event, buff_state, entity):
        """处理 on_turn_end 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_calculate(self, event, buff_state, entity):
        """处理 on_damage_calculate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_calculate_defend(self, event, buff_state, entity):
        """处理 on_damage_calculate_defend 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_take_defend(self, event, buff_state, entity, engine=None):
        """处理 on_damage_take_defend 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_heal(self, event, buff_state, entity):
        """处理 on_heal 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_heal_calculate(self, event, buff_state, entity):
        """处理 on_heal_calculate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_shield_gain(self, event, buff_state, entity):
        """处理 on_shield_gain 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_enemy_sync_intents(self, event, buff_state, entity):
        """处理 on_enemy_sync_intents 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_take_attack(self, event, buff_state, entity, engine=None):
        """处理 on_damage_take_attack 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_exhaust(self, event, buff_state, entity):
        """处理 on_card_exhaust 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_buff_gain(self, event, buff_state, entity):
        """处理 on_buff_gain 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_unit_death(self, event, buff_state, entity):
        """处理 on_unit_death 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_before_damage_apply(self, event, buff_state, entity, engine=None):
        """处理 on_before_damage_apply 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_battle_before_win_cleanup(self, event, buff_state, entity):
        """处理 on_battle_before_win_cleanup 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_buff_applied(self, event, buff_state, entity):
        """处理 on_buff_applied 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_shield_decay_calculate(self, event, buff_state, entity):
        """处理 on_shield_decay_calculate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_turn_start_after_draw(self, event, buff_state, entity):
        """处理 on_turn_start_after_draw 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_before_card_draw(self, event, buff_state, entity):
        """处理 on_before_card_draw 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_drawn(self, event, buff_state, entity):
        """处理 on_card_drawn 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_cost_calculate(self, event, buff_state, entity):
        """处理 on_card_cost_calculate 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_play_check(self, event, buff_state, entity):
        """处理 on_card_play_check 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_card_post_play_route(self, event, buff_state, entity):
        """处理 on_card_post_play_route 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_damage_redirect(self, event, buff_state, entity):
        """处理 on_damage_redirect 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_player_before_death(self, event, buff_state, entity):
        """处理 on_player_before_death 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_enemy_target_select(self, event, buff_state, entity):
        """处理 on_enemy_target_select 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_enemy_roll_intent(self, event, buff_state, entity):
        """处理 on_enemy_roll_intent 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass

    def on_lex_kela_changed(self, event, buff_state, entity):
        """处理 on_lex_kela_changed 生命周期扩展，具体字段与取消语义见事件定义。"""
        pass


def get_buff_impl(buff_id: str, stacks: int, stacks2: Optional[int] = None) -> Optional[BuffImpl]:
    """按 Buff ID 与层数构造实现实例。"""
    upgraded = False
    if isinstance(buff_id, str) and buff_id.endswith("+"):
        upgraded = True
        buff_id = buff_id[:-1]
    if buff_id.startswith("minor_vulnerable_"):
        from .debuffs import MinorVulnerableBuff
        dtype = buff_id[len("minor_vulnerable_"):]
        inst = MinorVulnerableBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    elif buff_id.startswith("vulnerable_"):
        from .debuffs import VulnerableBuff
        dtype = buff_id[len("vulnerable_"):]
        inst = VulnerableBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    elif buff_id.startswith("resist_"):
        from .buffs import ResistBuff
        dtype = buff_id[len("resist_"):]
        inst = ResistBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    elif buff_id.startswith("immune_"):
        from .buffs import ImmuneBuff
        dtype = buff_id[len("immune_"):]
        inst = ImmuneBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    cls = BUFF_CLASS_REGISTRY.get(buff_id)
    if not cls and isinstance(buff_id, str) and buff_id.endswith("_buff"):
        cls = BUFF_CLASS_REGISTRY.get(buff_id[:-5])
    if cls:
        inst = cls(stacks)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    return None
