from typing import Dict, Any, List
from ....models.state import UserStats
from ....data.world.yog_quest_config import YOG_INFO_FLAG, YOG_QUEST_FLAG, YOG_QUEST_ROUTE_KEY, YOG_QUEST_ZONE_KEY
from ....data.text.locale_data import get_locale_text


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
    state = flags.get(YOG_QUEST_FLAG, "unstarted")
    title = get_locale_text("i18n_yog_quest.quest.title")
    if state == "completed":
        if flags.get(YOG_QUEST_ROUTE_KEY) == "butcher":
            intro = get_locale_text("i18n_yog_quest.quest.done_butcher")
        else:
            intro = get_locale_text("i18n_yog_quest.quest.done_standard")
        return {"state": state, "title": title, "intro": intro, "objectives": []}
    if not flags.get(YOG_INFO_FLAG):
        return {
            "state": state,
            "title": title,
            "intro": get_locale_text("i18n_yog_quest.quest.intro"),
            "objectives": [get_locale_text("i18n_yog_quest.quest.goal_1")],
        }
    if state == "unstarted":
        return {
            "state": state,
            "title": title,
            "intro": get_locale_text("i18n_yog_quest.quest.intro_info"),
            "objectives": [get_locale_text("i18n_yog_quest.quest.goal_gate")],
        }
    zone = int(flags.get(YOG_QUEST_ZONE_KEY, 0) or 0)
    zone = max(0, min(zone, 3))
    goal_keys = ("goal_2", "goal_3", "goal_4", "goal_5")
    intro = get_locale_text(f"i18n_yog_quest.quest.intro_zone_{zone}")
    goal = get_locale_text(f"i18n_yog_quest.quest.{goal_keys[zone]}")
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
    def render_quests(cls, stats: UserStats, run=None) -> str:
        from ..map_quest_service import render_map_quests
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("i18n_town.quest_log_header"),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        has_any_quest = False
        map_section = render_map_quests(stats, run=run)
        if map_section:
            has_any_quest = True
            lines.append(map_section)
            lines.append("")

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
