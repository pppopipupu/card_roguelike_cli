COOP_ALLY_CARDS = {
    "coop_tactical_command",
    "coop_phalanx_bulwark",
    "coop_resonance_hymn",
    "coop_soul_link",
}


def validate_coop_target(engine, run, card, base_id, target):
    if base_id in COOP_ALLY_CARDS and not (isinstance(target, str) and target.lower().startswith(("a", "t"))):
        return "❌ 请指定一名队友目标，例如：使用 1 a2。"
    if isinstance(target, str) and target.lower().startswith(("a", "t")):
        resolved = engine.combat_resolver.resolve_ally(run, target)
        if not resolved:
            return f"❌ 队友目标 [{target}] 不存在。"
        ally_uid, ally_player, ally_grid = resolved
        if ally_player.downed or ally_player.hp <= 0:
            return f"❌ 队友【{ally_player.name}】已倒地，无法作为目标。"
        if ally_grid is not None and ally_grid not in ally_player.minions:
            return f"❌ 队友【{ally_player.name}】的随从格子 [{ally_grid}] 为空。"
        if ally_grid is not None and base_id in ("coop_phalanx_bulwark", "coop_soul_link"):
            return "❌ 该卡牌只能指定队友本人，不能指定随从。"
        current_uid = run.uid_for(run.player)
        if ally_uid == current_uid and base_id in ("coop_tactical_command", "coop_soul_link"):
            return "❌ 该卡牌不能以自己为目标，请指定一名队友。"
        if ally_uid == current_uid and base_id == "coop_resonance_hymn" and not card.upgraded:
            return "❌ 未升级的【共鸣圣歌】不能以自己为目标，请指定一名队友。"
        if ally_uid == current_uid and base_id == "coop_phalanx_bulwark" and not card.upgraded:
            return "❌ 未升级的【方阵掩护】不能以自己为目标，请指定一名队友。"
    return None
