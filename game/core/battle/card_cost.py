def _has_ninja_tag(card, tag: str) -> bool:
    if tag in (getattr(card, "ninja_tags", ()) or ()):
        return True
    return any(getattr(item, "name", "") == tag for item in (getattr(card, "tags", ()) or ()))


def resolve_card_effective_cost_a(card, card_state, player) -> int:
    """计算卡牌的当前主动作费用，不修改卡牌状态。

    参数 ``card`` 为 ``ALL_CARDS`` 中的卡牌实例，``card_state`` 为携带
    临时费用与战斗内费用偏移的 ``CardState``，``player`` 用于读取蕾克拉。
    ``temp_cost_a`` 优先于 ``battle_cost_delta_a``；科学忍具在费用大于 0
    时按蕾克拉扣减，忍术牌在拥有 ``plasma_arrow`` 时直接降为 0。
    返回非负费用；X 费用卡牌返回 ``-1``，由调用方展开为当前资源。
    """
    base_a = int(getattr(card, "cost_a", 0) or 0)
    if base_a == -1:
        return -1
    temp_a = getattr(card_state, "temp_cost_a", None) if card_state is not None else None
    if temp_a is not None:
        effective = max(0, int(temp_a))
    else:
        delta = int(getattr(card_state, "battle_cost_delta_a", 0) or 0) if card_state is not None else 0
        effective = max(0, base_a + delta)
    if getattr(card, "science", False) and effective > 0 and player is not None:
        lex = max(0, int(getattr(player, "lex_kela", 0) or 0))
        effective = max(0, effective - lex)
    if player is not None and _has_ninja_tag(card, "ninjutsu"):
        if any(b.id == "plasma_arrow" and b.stacks > 0 for b in player.buffs):
            return 0
    return effective


def resolve_card_effective_cost_ba(card, card_state, player=None) -> int:
    """计算卡牌的当前附赠动作费用，不修改卡牌状态。

    ``temp_cost_ba`` 覆盖基础费用；X 费用卡牌返回 ``-1``。当前实现不读取
    玩家资源，``player`` 参数保留给未来附赠动作修正。
    """
    base_ba = int(getattr(card, "cost_ba", 0) or 0)
    if base_ba == -1:
        return -1
    temp_ba = getattr(card_state, "temp_cost_ba", None) if card_state is not None else None
    if temp_ba is not None:
        return max(0, int(temp_ba))
    return max(0, base_ba)
