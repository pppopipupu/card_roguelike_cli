from ..data.locale_data import t
from ..models.state import GameRun
from .formatters import format_relic_bar


def render_party_status(run: GameRun) -> str:
    lines = [t("renderer_town.party_title")]
    reason = getattr(run, "coop_end_reason", "")
    if reason:
        lines.append(f"⏳ {reason}")
        return "\n".join(lines)
    for idx, uid in enumerate(getattr(run, "party_order", []) or [], 1):
        member = (getattr(run, "players", {}) or {}).get(uid)
        if member is None:
            continue
        marker = t("renderer_town.party_you_marker") if uid == run.user_id else (t("renderer_town.party_mercenary_marker") if getattr(member, "is_mercenary", False) else "")
        if member.downed or member.hp <= 0:
            hp_text = t("renderer_town.party_downed")
        else:
            hp_text = f"{member.hp}/{member.max_hp}"
        grid_text = t("renderer_town.party_grid", idx=idx)
        relics_text = format_relic_bar(getattr(member, "relics", []))
        lines.append(t(
            "renderer_town.party_member_line",
            idx=idx,
            name=member.name,
            marker=marker,
            hp=hp_text,
            grid=grid_text,
            relics=relics_text
        ))
    return "\n".join(lines)


def render_waiting(run: GameRun) -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{render_party_status(run)}\n\n"
        + t("renderer_town.party_waiting")
    )
