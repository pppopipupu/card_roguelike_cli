from typing import Dict, Any, List
from ....models.state import UserStats
from ....data.outer_plane_config import OUTER_PLANE_FLAGS_KEY
from ....data.temple_config import TEMPLE_FLAGS_KEY, TEMPLE_INFO_FLAG, TEMPLE_QUEST_FLAG, TEMPLE_VISITED_KEY
from ....data.locale_data import get_locale_text


def _objective_line(text: str) -> str:
    return f"     • {text}"


def _tour_quest(stats: UserStats) -> Dict[str, Any]:
    state = stats.town_flags.get("quest_town_tour_state", "unstarted")
    if state == "unstarted":
        return {}
    visited = stats.town_flags.get("quest_town_tour_visited", [])
    visited_cnt = len(visited)
    if state == "completed":
        return {
            "state": state,
            "title": get_locale_text("i18n_town.quest_tour_title"),
            "intro": get_locale_text("i18n_town.quest_tour_done_intro"),
            "objectives": [],
        }
    if visited_cnt >= 11:
        return {
            "state": state,
            "title": get_locale_text("i18n_town.quest_tour_title"),
            "intro": get_locale_text("i18n_town.quest_tour_ready_intro"),
            "objectives": [get_locale_text("i18n_town.quest_tour_goal_report")],
        }
    return {
        "state": state,
        "title": get_locale_text("i18n_town.quest_tour_title"),
        "intro": get_locale_text("i18n_town.quest_tour_intro"),
        "objectives": [get_locale_text("i18n_town.quest_tour_goal", visited_cnt=visited_cnt)],
    }


def _brew_quest(stats: UserStats) -> Dict[str, Any]:
    state = stats.town_flags.get("quest_brew_state", "unstarted")
    if state == "unstarted":
        return {}
    title = get_locale_text("i18n_town.quest_brew_title")
    if state == "completed":
        outcome = stats.town_flags.get("quest_brew_outcome")
        if outcome == "bartender":
            intro = get_locale_text("i18n_town.quest_brew_done_bartender")
        elif outcome == "shopkeeper":
            intro = get_locale_text("i18n_town.quest_brew_done_shopkeeper")
        else:
            intro = get_locale_text("i18n_town.quest_brew_done_default")
        return {"state": state, "title": title, "intro": intro, "objectives": []}

    inv = stats.town_inventory
    if "wishing_dew" in inv:
        intro = get_locale_text("i18n_town.quest_brew_intro_dew")
        goal = get_locale_text("i18n_town.quest_brew_goal_deliver")
    elif "void_herb" in inv:
        if stats.town_flags.get("reported_whale"):
            intro = get_locale_text("i18n_town.quest_brew_intro_herb_reported")
        else:
            intro = get_locale_text("i18n_town.quest_brew_intro_herb")
        goal = get_locale_text("i18n_town.quest_brew_goal_wash")
    elif "promotional_agreement" in inv:
        intro = get_locale_text("i18n_town.quest_brew_intro_agreement")
        goal = get_locale_text("i18n_town.quest_brew_goal_trade")
    elif stats.town_flags.get("jack_riddle_step"):
        intro = get_locale_text("i18n_town.quest_brew_intro_riddle")
        goal = get_locale_text("i18n_town.quest_brew_goal_agreement")
    else:
        intro = get_locale_text("i18n_town.quest_brew_intro")
        goal = get_locale_text("i18n_town.quest_brew_goal_void")
    return {"state": state, "title": title, "intro": intro, "objectives": [goal]}


def _hammer_quest(stats: UserStats) -> Dict[str, Any]:
    state = stats.town_flags.get("quest_hammer_state", "unstarted")
    if state == "unstarted":
        return {}
    title = get_locale_text("i18n_town.quest_hammer_title")
    if state == "completed":
        outcome = stats.town_flags.get("quest_hammer_outcome")
        if outcome == "real":
            intro = get_locale_text("i18n_town.quest_hammer_done_real")
        elif outcome == "fake":
            intro = get_locale_text("i18n_town.quest_hammer_done_fake")
        elif outcome == "force":
            intro = get_locale_text("i18n_town.quest_hammer_done_force")
        else:
            intro = get_locale_text("i18n_town.quest_hammer_done_default")
        return {"state": state, "title": title, "intro": intro, "objectives": []}

    inv = stats.town_inventory
    if stats.town_flags.get("noob_coerced_hammer"):
        intro = get_locale_text("i18n_town.quest_hammer_intro_coerced")
        goal = get_locale_text("i18n_town.quest_hammer_goal_return_coerced")
    elif "smith_hammer" in inv:
        intro = get_locale_text("i18n_town.quest_hammer_intro_real")
        goal = get_locale_text("i18n_town.quest_hammer_goal_return")
    elif "fake_hammer" in inv:
        intro = get_locale_text("i18n_town.quest_hammer_intro_fake")
        goal = get_locale_text("i18n_town.quest_hammer_goal_get")
    elif stats.town_flags.get("hammer_asked_bard"):
        intro = get_locale_text("i18n_town.quest_hammer_intro_bard")
        goal = get_locale_text("i18n_town.quest_hammer_goal_bard")
    else:
        intro = get_locale_text("i18n_town.quest_hammer_intro")
        goal = get_locale_text("i18n_town.quest_hammer_goal_clue")
    return {"state": state, "title": title, "intro": intro, "objectives": [goal]}


def _yog_death_quest(stats: UserStats) -> Dict[str, Any]:
    if int(getattr(stats, "yog_sothoth_kill_count", 0) or 0) <= 0:
        return {}
    flags = stats.town_flags
    inner = flags.get(TEMPLE_FLAGS_KEY) or {}
    outer = flags.get(OUTER_PLANE_FLAGS_KEY) or {}
    visited = flags.get(TEMPLE_VISITED_KEY) or []
    state = flags.get(TEMPLE_QUEST_FLAG, "unstarted")
    title = get_locale_text("i18n_temple.quest.title")

    if state == "completed":
        if inner.get("butcher_path") or outer.get("butcher_path"):
            intro = get_locale_text("i18n_temple.quest.done_butcher")
        else:
            intro = get_locale_text("i18n_temple.quest.done_standard")
        return {"state": state, "title": title, "intro": intro, "objectives": []}

    if state == "outer_plane":
        has_shift = bool(outer.get("has_plane_shift"))
        has_calm = bool(outer.get("has_calm_mind"))
        if outer.get("butcher_path"):
            intro = get_locale_text("i18n_temple.quest.intro_outer_butcher")
            goal = get_locale_text("i18n_temple.quest.goal_6_butcher")
        else:
            intro = get_locale_text("i18n_temple.quest.intro_outer_default")
            if has_shift and has_calm:
                goal = get_locale_text("i18n_temple.quest.goal_6_forge")
            elif has_shift:
                goal = get_locale_text("i18n_temple.quest.goal_6_need_calm")
            elif has_calm:
                goal = get_locale_text("i18n_temple.quest.goal_6_need_shift")
            else:
                goal = get_locale_text("i18n_temple.quest.goal_6")
        return {"state": state, "title": title, "intro": intro, "objectives": [goal]}

    if not flags.get(TEMPLE_INFO_FLAG):
        return {
            "state": state,
            "title": title,
            "intro": get_locale_text("i18n_temple.quest.intro"),
            "objectives": [get_locale_text("i18n_temple.quest.goal_1")],
        }

    if not visited:
        return {
            "state": state,
            "title": title,
            "intro": get_locale_text("i18n_temple.quest.intro_info"),
            "objectives": [get_locale_text("i18n_temple.quest.goal_2")],
        }

    if inner.get("temple_boss_defeated") or "necronomicon_chamber" in visited:
        return {
            "state": state,
            "title": title,
            "intro": get_locale_text("i18n_temple.quest.intro_book"),
            "objectives": [get_locale_text("i18n_temple.quest.goal_5")],
        }

    if "frozen_throne" in visited:
        return {
            "state": state,
            "title": title,
            "intro": get_locale_text("i18n_temple.quest.intro_throne"),
            "objectives": [get_locale_text("i18n_temple.quest.goal_4")],
        }

    deep_rooms = ("cage_of_scholars", "altar_of_frost", "frozen_stair", "auril_shrine", "blizzard_bridge", "sentinel_hall")
    if inner.get("cultists_defeated") or inner.get("side_door_used") or any(r in visited for r in deep_rooms):
        if inner.get("butcher_path"):
            intro = get_locale_text("i18n_temple.quest.intro_deep_butcher")
        elif inner.get("side_door_used"):
            intro = get_locale_text("i18n_temple.quest.intro_deep_stealth")
        else:
            intro = get_locale_text("i18n_temple.quest.intro_deep_combat")
        return {
            "state": state,
            "title": title,
            "intro": intro,
            "objectives": [get_locale_text("i18n_temple.quest.goal_3_deep")],
        }

    if inner.get("butcher_path"):
        intro = get_locale_text("i18n_temple.quest.intro_temple_butcher")
    elif inner.get("forced_entry"):
        intro = get_locale_text("i18n_temple.quest.intro_temple_forced")
    elif inner.get("path_sneak"):
        intro = get_locale_text("i18n_temple.quest.intro_temple_sneak")
    else:
        intro = get_locale_text("i18n_temple.quest.intro_temple_default")

    if inner.get("spy_intel"):
        goal = get_locale_text("i18n_temple.quest.goal_3_spy")
    elif inner.get("bone_key"):
        goal = get_locale_text("i18n_temple.quest.goal_3_key")
    else:
        goal = get_locale_text("i18n_temple.quest.goal_3")
    return {"state": state, "title": title, "intro": intro, "objectives": [goal]}


def _active_quests(stats: UserStats) -> List[Dict[str, Any]]:
    quests = []
    for builder in (_tour_quest, _brew_quest, _hammer_quest, _yog_death_quest):
        quest = builder(stats)
        if quest:
            quests.append(quest)
    return quests


class QuestManager:
    @classmethod
    def render_quests(cls, stats: UserStats) -> str:
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("i18n_town.quest_log_header"),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        has_any_quest = False
        for quest in _active_quests(stats):
            has_any_quest = True
            status_text = (
                get_locale_text("i18n_town.quest_status_completed")
                if quest["state"] == "completed"
                else get_locale_text("i18n_town.quest_status_in_progress")
            )
            lines.append(quest["title"].format(status=status_text))
            lines.append(quest["intro"])
            if quest["objectives"]:
                lines.append(get_locale_text("i18n_town.quest_goals_title"))
                for obj in quest["objectives"]:
                    lines.append(_objective_line(obj))
            lines.append("")

        if not has_any_quest:
            lines.append(get_locale_text("i18n_town.quest_empty"))
            lines.append(get_locale_text("i18n_town.quest_empty_hint"))
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(get_locale_text("i18n_town.quest_help_tip"))
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return "\n".join(lines)
