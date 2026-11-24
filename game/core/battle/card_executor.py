from typing import Optional

from ...data.text.locale_data import get_locale_text
from ...models.events import CardPlayedEvent, CardExtraTriggerEvent


def _card_has_interactive_selection(engine, run, card) -> bool:
    get_spec = getattr(card, "get_selection_spec", None)
    if callable(get_spec) and get_spec(run, engine) is not None:
        return True
    get_post = getattr(card, "get_post_selection_spec", None)
    if callable(get_post) and get_post(run, engine) is not None:
        return True
    return False


def _enqueue_extra_play(
    run,
    card,
    target,
    *,
    trigger_type: str,
    dispatch_played_event: bool,
    dispatch_extra_event: bool,
    msg_key: str,
    msg_params: Optional[dict],
) -> None:
    run.node_data.setdefault("pending_extra_plays", []).append(
        {
            "card_id": card.id,
            "upgraded": bool(getattr(card, "upgraded", False)),
            "gems": list(getattr(card, "gems", None) or []),
            "enchantments": list(getattr(card, "enchantments", None) or []),
            "target": target,
            "trigger_type": trigger_type,
            "dispatch_played_event": bool(dispatch_played_event),
            "dispatch_extra_event": bool(dispatch_extra_event),
            "msg_key": msg_key,
            "msg_params": dict(msg_params or {}),
        }
    )


def execute_extra_card_effect(
    engine,
    run,
    card,
    target,
    *,
    trigger_type,
    dispatch_played_event=True,
    msg_key: str = "",
    msg_params: Optional[dict] = None,
    dispatch_extra_event: bool = True,
):
    """执行一次不消耗费用的额外出牌并派发标准事件。

    参数：
        engine: 战斗引擎，提供 ``_execute_card_effect`` 与事件总线。
        run: 当前战斗运行状态。
        card: 要额外执行的卡牌实例。
        target: 已解析的目标引用，可为 ``None``。
        trigger_type: 额外触发来源标识，用于 ``CardExtraTriggerEvent``。
        dispatch_played_event: 是否派发 ``CardPlayedEvent``，默认 True。
        msg_key: 可选额外触发反馈本地化键名，写入 ``extra_play_msgs``。
        msg_params: 传给 ``msg_key`` 的附加格式化参数。
        dispatch_extra_event: 是否派发 ``CardExtraTriggerEvent``，默认 True。

    若卡牌需要交互选择则入队延迟执行并返回 ``None``，否则立即执行并返回反馈文本。
    """
    if _card_has_interactive_selection(engine, run, card):
        _enqueue_extra_play(
            run,
            card,
            target,
            trigger_type=trigger_type,
            dispatch_played_event=dispatch_played_event,
            dispatch_extra_event=dispatch_extra_event,
            msg_key=msg_key,
            msg_params=msg_params,
        )
        return None
    result = engine._execute_card_effect(run, card, target)
    feedback = result
    if dispatch_played_event:
        played_evt = CardPlayedEvent(run, card, target, result, is_extra=True)
        engine.event_bus.dispatch(played_evt)
        feedback = played_evt.feedback
    if dispatch_extra_event:
        engine.event_bus.dispatch(CardExtraTriggerEvent(run, card, trigger_type))
    if msg_key:
        params = dict(msg_params or {})
        params.setdefault("res", feedback)
        params.setdefault("feedback", feedback)
        params.setdefault("name", card.name)
        run.node_data.setdefault("extra_play_msgs", []).append(
            get_locale_text(msg_key, **params)
        )
    return feedback
