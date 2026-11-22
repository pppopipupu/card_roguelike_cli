from ...models.events import CardPlayedEvent, CardExtraTriggerEvent


def execute_extra_card_effect(engine, run, card, target, *, trigger_type, dispatch_played_event=True):
    """执行一次不消耗费用的额外出牌并派发标准事件。

    参数：
        engine: 战斗引擎，提供 ``_execute_card_effect`` 与事件总线。
        run: 当前战斗运行状态。
        card: 要额外执行的卡牌实例。
        target: 已解析的目标引用，可为 ``None``。
        trigger_type: 额外触发来源标识，用于 ``CardExtraTriggerEvent``。
        dispatch_played_event: 是否派发 ``CardPlayedEvent``，默认 True。

    返回卡牌效果产生的反馈文本。
    """
    result = engine._execute_card_effect(run, card, target)
    if dispatch_played_event:
        engine.event_bus.dispatch(CardPlayedEvent(run, card, target, result, is_extra=True))
    engine.event_bus.dispatch(CardExtraTriggerEvent(run, card, trigger_type))
    return result
