from ..core.progress.progressive_unlock import (
    get_enemy_query_access,
    is_buff_visible_in_query,
    is_card_visible_in_query,
    is_relic_visible_in_query,
    is_world_entry_unlocked,
)
from ..data.chireiden_data import (
    CHIREIDEN_BIG_ROOM_TEMPLATES,
    CHIREIDEN_ENVIRONMENTS,
    CHIREIDEN_FLOOR_QUERY_ALIASES,
    CHIREIDEN_LANDMARK_IDS,
    CHIREIDEN_PROPS,
    CHIREIDEN_TRIGGER_QUERY_IDS,
)
from ..data.enemy_data_chireiden import ENEMY_CHIREIDEN_CONFIG
from ..data.locale_data import get_locale_text


def should_skip_buff_query(bid: str, stats) -> bool:
    return not is_buff_visible_in_query(bid, stats)


def should_skip_relic_query(rid: str, stats) -> bool:
    return not is_relic_visible_in_query(rid, stats)


def should_skip_card_query(cid: str, stats) -> bool:
    return not is_card_visible_in_query(cid, stats)


def is_chireiden_enemy(eid: str) -> bool:
    return eid in ENEMY_CHIREIDEN_CONFIG


def get_chireiden_enemy_access(eid: str, ename: str, stats) -> str:
    return get_enemy_query_access(eid, ename, stats)


def append_utsuho_ally_lore_if_unlocked(lines: list[str], eid: str, stats) -> None:
    if eid != get_locale_text("i18n_chireiden.enemies.utsuho_reiuji"):
        return
    if not is_world_entry_unlocked("ally", "merc_utsuho", stats):
        return
    lines.append(get_locale_text("i18n_chireiden.query.utsuho_ally_title"))
    lines.append(get_locale_text("i18n_chireiden.query.desc_line", desc=get_locale_text("i18n_chireiden.query.utsuho_ally_desc")))


def _matches(q_search: str, *candidates: str) -> bool:
    if not q_search:
        return False
    for raw in candidates:
        s = str(raw or "").strip().lower()
        if not s:
            continue
        if q_search == s or q_search in s:
            return True
    return False


def _append_unlocked_world_block(lines: list[str], title: str, desc: str) -> None:
    lines.append(title)
    lines.append(get_locale_text("i18n_chireiden.query.desc_line", desc=desc))
    lines.append("")


def append_chireiden_world_queries(lines: list[str], q_search: str, stats) -> bool:
    if not q_search:
        return False
    found = False

    floor_name = get_locale_text("i18n_chireiden.floor_3_5_name")
    if _matches(q_search, floor_name, *CHIREIDEN_FLOOR_QUERY_ALIASES):
        has_entered = is_world_entry_unlocked("floor", "full", stats)
        has_rumor = is_world_entry_unlocked("floor", "rumor", stats)
        if has_entered or has_rumor:
            found = True
            desc_key = "i18n_chireiden.query.floor_full_desc" if has_entered else "i18n_chireiden.query.floor_rumor_desc"
            _append_unlocked_world_block(
                lines,
                get_locale_text("i18n_chireiden.query.floor_title", name=floor_name),
                get_locale_text(desc_key),
            )

    for tpl_id, tpl in CHIREIDEN_BIG_ROOM_TEMPLATES.items():
        if not is_world_entry_unlocked("big_room", tpl_id, stats):
            continue
        name = get_locale_text(tpl["name_key"])
        if _matches(q_search, tpl_id, name):
            found = True
            _append_unlocked_world_block(
                lines,
                get_locale_text("i18n_chireiden.query.big_room_title", icon=tpl.get("icon", ""), name=name, id=tpl_id),
                get_locale_text(tpl["desc_key"]),
            )

    for lm_id in CHIREIDEN_LANDMARK_IDS:
        if not is_world_entry_unlocked("landmark", lm_id, stats):
            continue
        name = get_locale_text(f"i18n_chireiden.landmarks.{lm_id}.name")
        if _matches(q_search, lm_id, name):
            found = True
            _append_unlocked_world_block(
                lines,
                get_locale_text("i18n_chireiden.query.landmark_title", name=name, id=lm_id),
                get_locale_text(f"i18n_chireiden.landmarks.{lm_id}.desc"),
            )

    for pid, pcfg in CHIREIDEN_PROPS.items():
        if not is_world_entry_unlocked("prop", pid, stats):
            continue
        name = get_locale_text(pcfg["name_key"])
        if _matches(q_search, pid, name, *(pcfg.get("aliases") or ())):
            found = True
            _append_unlocked_world_block(
                lines,
                get_locale_text("i18n_chireiden.query.prop_title", name=name, id=pid),
                get_locale_text(pcfg["desc_key"]),
            )

    for env_id in CHIREIDEN_ENVIRONMENTS:
        if not is_world_entry_unlocked("env", env_id, stats):
            continue
        name = get_locale_text(f"i18n_chireiden.query.envs.{env_id}")
        if _matches(q_search, env_id, name):
            found = True
            _append_unlocked_world_block(
                lines,
                get_locale_text("i18n_chireiden.query.env_title", name=name, id=env_id),
                get_locale_text(f"i18n_room_interact.env.{env_id}"),
            )

    for tid in CHIREIDEN_TRIGGER_QUERY_IDS:
        if not is_world_entry_unlocked("trigger", tid, stats):
            continue
        name = get_locale_text(f"i18n_chireiden.query.triggers.{tid}.name")
        if _matches(q_search, tid, name):
            found = True
            _append_unlocked_world_block(
                lines,
                get_locale_text("i18n_chireiden.query.trigger_title", name=name, id=tid),
                get_locale_text(f"i18n_chireiden.query.triggers.{tid}.desc"),
            )

    return found
