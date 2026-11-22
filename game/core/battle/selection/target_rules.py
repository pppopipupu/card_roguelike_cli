from dataclasses import dataclass

from ....data.text.locale_data import get_locale_text


@dataclass(frozen=True)
class TargetRule:
    """联机/协作卡牌的队友目标约束，替代全局卡牌 ID 集合。"""

    requires_ally: bool = False
    allow_self: bool = False
    allow_minion: bool = True
    upgraded_allow_self: bool = False
    upgraded_allow_minion: bool = False
    self_denied_key: str = "i18n_battle_misc.coop_cannot_self"
    minion_denied_key: str = "i18n_battle_misc.coop_ally_must_person"


def is_coop_ally_card(card: object) -> bool:
    """判断卡牌是否声明了必须选择队友的目标规则。"""
    rule = getattr(card, "target_rule", None)
    return isinstance(rule, TargetRule) and rule.requires_ally



def validate_target(engine, run, card, base_id, target):
    rule = getattr(card, "target_rule", None)
    if not isinstance(rule, TargetRule) or not rule.requires_ally:
        return None
    if not (isinstance(target, str) and target.lower().startswith("a")):
        return get_locale_text("i18n_battle_misc.coop_need_ally_target")
    resolved = engine.combat_resolver.resolve_ally(run, target)
    if not resolved:
        return get_locale_text("i18n_battle_misc.coop_ally_not_found", target=target)
    ally_uid, ally_player, ally_grid = resolved
    if ally_player.downed or ally_player.hp <= 0:
        return get_locale_text("i18n_battle_misc.coop_ally_downed", name=ally_player.name)
    upgraded = bool(getattr(card, "upgraded", False))
    allow_minion = rule.allow_minion or (upgraded and rule.upgraded_allow_minion)
    if ally_grid is not None and not allow_minion:
        return get_locale_text(rule.minion_denied_key)
    current_uid = run.uid_for(run.player)
    allow_self = rule.allow_self or (upgraded and rule.upgraded_allow_self)
    if ally_uid == current_uid and not allow_self:
        return get_locale_text(rule.self_denied_key)
    return None


def normalize_default_target(run, card, base_id, target):
    rule = getattr(card, "target_rule", None)
    if not isinstance(rule, TargetRule) or not rule.requires_ally:
        return target
    if isinstance(target, str) and target.strip():
        return target
    current = run.uid_for(run.player)
    upgraded = bool(getattr(card, "upgraded", False))
    allow_self = rule.allow_self or (upgraded and rule.upgraded_allow_self)
    for index, uid in enumerate(run.party_order, 1):
        player = run.players.get(uid)
        if player is None or player.downed or player.hp <= 0:
            continue
        if uid == current and not allow_self:
            continue
        return f"a{index}"
    return target
