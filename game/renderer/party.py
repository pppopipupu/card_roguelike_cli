from ..models.state import GameRun


def render_party_status(run: GameRun) -> str:
    lines = ["👥 队伍状态："]
    reason = getattr(run, "coop_end_reason", "")
    if reason:
        lines.append(f"⏳ {reason}")
        return "\n".join(lines)
    for idx, uid in enumerate(getattr(run, "party_order", []) or [], 1):
        member = (getattr(run, "players", {}) or {}).get(uid)
        if member is None:
            continue
        marker = "（你）" if uid == run.user_id else ""
        if member.downed or member.hp <= 0:
            hp_text = "倒地"
        else:
            hp_text = f"{member.hp}/{member.max_hp}"
        grid_text = f" 场上 a{idx}"
        lines.append(f" a{idx}. {member.name}{marker}：❤️ {hp_text}{grid_text}")
    return "\n".join(lines)


def render_waiting(run: GameRun) -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{render_party_status(run)}\n\n"
        "⏳ 你已结束本节点行动，正在等待其他队友完成。"
    )
