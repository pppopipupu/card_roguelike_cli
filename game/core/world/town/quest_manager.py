from typing import Dict, Any, List
from ....models.state import UserStats
from ....data.temple_config import TEMPLE_FLAGS_KEY, TEMPLE_INFO_FLAG, TEMPLE_QUEST_FLAG, TEMPLE_VISITED_KEY

from ....data.locale_data import get_locale_text


def _goal_line(text: str, done: bool) -> str:
    if done:
        return "     ✔ " + QuestManager.apply_strikethrough(text)
    return f"     • {text}"


def _tour_quest(stats: UserStats) -> Dict[str, Any]:
    state = stats.town_flags.get("quest_town_tour_state", "unstarted")
    if state == "unstarted":
        return {}
    visited = stats.town_flags.get("quest_town_tour_visited", [])
    visited_cnt = len(visited)
    return {
        "state": state,
        "title": get_locale_text("i18n_town.quest_tour_title"),
        "intro": get_locale_text("i18n_town.quest_tour_intro"),
        "goals": [
            {
                "text": get_locale_text("i18n_town.quest_tour_goal", visited_cnt=visited_cnt),
                "done": state == "completed" or visited_cnt >= 11,
            }
        ],
    }


def _brew_quest(stats: UserStats) -> Dict[str, Any]:
    state = stats.town_flags.get("quest_brew_state", "unstarted")
    if state == "unstarted":
        return {}
    has_void = "void_herb" in stats.town_inventory
    has_dew = "wishing_dew" in stats.town_inventory
    is_comp = state == "completed"
    return {
        "state": state,
        "title": get_locale_text("i18n_town.quest_brew_title"),
        "intro": get_locale_text("i18n_town.quest_brew_intro"),
        "goals": [
            {"text": get_locale_text("i18n_town.quest_brew_goal_void"), "done": has_void or has_dew or is_comp},
            {"text": get_locale_text("i18n_town.quest_brew_goal_wash"), "done": has_dew or is_comp},
            {"text": get_locale_text("i18n_town.quest_brew_goal_deliver"), "done": is_comp},
        ],
    }


def _hammer_quest(stats: UserStats) -> Dict[str, Any]:
    state = stats.town_flags.get("quest_hammer_state", "unstarted")
    if state == "unstarted":
        return {}
    has_real = "smith_hammer" in stats.town_inventory
    has_fake = "fake_hammer" in stats.town_inventory
    coerced = stats.town_flags.get("noob_coerced_hammer")
    taken_bard = stats.town_flags.get("taken_smith_hammer")
    is_comp = state == "completed"
    return {
        "state": state,
        "title": get_locale_text("i18n_town.quest_hammer_title"),
        "intro": get_locale_text("i18n_town.quest_hammer_intro"),
        "goals": [
            {"text": get_locale_text("i18n_town.quest_hammer_goal_clue"), "done": has_real or has_fake or coerced or taken_bard or is_comp},
            {"text": get_locale_text("i18n_town.quest_hammer_goal_get"), "done": has_real or has_fake or coerced or is_comp},
            {"text": get_locale_text("i18n_town.quest_hammer_goal_return"), "done": is_comp},
        ],
    }


def _yog_death_quest(stats: UserStats) -> Dict[str, Any]:
    if int(getattr(stats, "yog_sothoth_kill_count", 0) or 0) <= 0:
        return {}
    flags = stats.town_flags
    inner = flags.get(TEMPLE_FLAGS_KEY) or {}
    state = flags.get(TEMPLE_QUEST_FLAG, "unstarted")
    goals = [
        {"text": get_locale_text("i18n_temple.quest.goal_1"), "done": bool(flags.get(TEMPLE_INFO_FLAG))},
        {"text": get_locale_text("i18n_temple.quest.goal_2"), "done": bool(flags.get(TEMPLE_VISITED_KEY))},
        {"text": get_locale_text("i18n_temple.quest.goal_3"), "done": bool(inner.get("cultists_defeated") or inner.get("temple_boss_defeated"))},
        {"text": get_locale_text("i18n_temple.quest.goal_4"), "done": bool(inner.get("temple_boss_defeated"))},
        {"text": get_locale_text("i18n_temple.quest.goal_5"), "done": state in ("outer_plane", "completed")},
        {"text": get_locale_text("i18n_temple.quest.goal_6"), "done": state == "completed"},
    ]
    return {
        "state": state,
        "title": get_locale_text("i18n_temple.quest.title"),
        "intro": get_locale_text("i18n_temple.quest.intro"),
        "goals": goals,
    }


def _active_quests(stats: UserStats) -> List[Dict[str, Any]]:
    quests = []
    for builder in (_tour_quest, _brew_quest, _hammer_quest, _yog_death_quest):
        quest = builder(stats)
        if quest:
            quests.append(quest)
    return quests


class QuestManager:
    @staticmethod
    def apply_strikethrough(text: str) -> str:
        return "".join(c + "\u0336" for c in text)

    @classmethod
    def render_quests(cls, stats: UserStats) -> str:
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("i18n_town.quest_log_header"),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]

        has_any_quest = False
        for quest in _active_quests(stats):
            has_any_quest = True
            status_text = get_locale_text("i18n_town.quest_status_completed") if quest["state"] == "completed" else get_locale_text("i18n_town.quest_status_in_progress")
            lines.append(quest["title"].format(status=status_text))
            lines.append(quest["intro"])
            lines.append(get_locale_text("i18n_town.quest_goals_title"))
            for goal in quest["goals"]:
                lines.append(_goal_line(goal["text"], goal["done"]))
            lines.append("")

        if not has_any_quest:
            lines.append(get_locale_text("i18n_town.quest_empty"))
            lines.append(get_locale_text("i18n_town.quest_empty_hint"))
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(get_locale_text("i18n_town.quest_help_tip"))
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return "\n".join(lines)
