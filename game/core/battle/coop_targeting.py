from ...data.locale_data import get_locale_text

COOP_ALLY_CARDS = {
    "coop_tactical_command",
    "coop_phalanx_bulwark",
    "coop_resonance_hymn",
    "coop_soul_link",
}


def validate_coop_target(engine, run, card, base_id, target):
    if base_id in COOP_ALLY_CARDS and not (isinstance(target, str) and target.lower().startswith("a")):
        return get_locale_text("i18n_battle_misc.coop_need_ally_target")
    if isinstance(target, str) and target.lower().startswith("a"):
        resolved = engine.combat_resolver.resolve_ally(run, target)
        if not resolved:
            return get_locale_text("i18n_battle_misc.coop_ally_not_found", target=target)
        ally_uid, ally_player, ally_grid = resolved
        if ally_player.downed or ally_player.hp <= 0:
            return get_locale_text("i18n_battle_misc.coop_ally_downed", name=ally_player.name)
        if ally_grid is not None and ally_grid not in ally_player.minions:
            return get_locale_text("i18n_battle_misc.coop_ally_minion_empty", name=ally_player.name, grid=ally_grid)
        if ally_grid is not None and base_id in ("coop_phalanx_bulwark", "coop_soul_link"):
            return get_locale_text("i18n_battle_misc.coop_ally_must_person")
        current_uid = run.uid_for(run.player)
        if ally_uid == current_uid and base_id in ("coop_tactical_command", "coop_soul_link"):
            return get_locale_text("i18n_battle_misc.coop_cannot_self")
        if ally_uid == current_uid and base_id == "coop_resonance_hymn" and not card.upgraded:
            return get_locale_text("i18n_battle_misc.coop_hymn_unupgraded_self")
        if ally_uid == current_uid and base_id == "coop_phalanx_bulwark" and not card.upgraded:
            return get_locale_text("i18n_battle_misc.coop_bulwark_unupgraded_self")
    return None


def normalize_coop_target(run, card, base_id, target):
    if base_id not in COOP_ALLY_CARDS:
        return target
    if isinstance(target, str) and target.strip():
        return target
    current = run.uid_for(run.player)
    allow_self = bool(getattr(card, "upgraded", False)) and base_id in (
        "coop_resonance_hymn",
        "coop_phalanx_bulwark",
    )
    for index, uid in enumerate(run.party_order, 1):
        player = run.players.get(uid)
        if player is None or player.downed or player.hp <= 0:
            continue
        if uid == current and not allow_self:
            continue
        return f"a{index}"
    return target
