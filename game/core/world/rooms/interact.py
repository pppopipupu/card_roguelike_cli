import random
from typing import List, Optional
from ....data.text.locale_data import get_locale_text
from ....data.entities.potion_data import get_potion_name, roll_potion
from ....data.world.room_interact_data import ROOM_NPCS, ROOM_PROPS
from ...inventory.bag_service import add_bag_item, get_item_display_name, resolve_item_query
from ..persistent_buffs import break_map_invisibility
from ..sp_system import reduce_exhaustion, restore_sp
from .big_room import (
    add_effective_item,
    get_effective_alive_npcs,
    get_effective_interacted_props,
    get_effective_items,
    get_effective_props,
    mark_effective_prop_interacted,
    remove_effective_item,
)
from .hostile_npc import ensure_room_hostile_npcs, ensure_treasure_chest_prop

PROP_HANDLERS = {}


def register_prop_handler(*prop_ids):
    def decorator(handler):
        for prop_id in prop_ids:
            PROP_HANDLERS[prop_id] = handler
        return handler
    return decorator


def get_current_room(run):
    fm = getattr(run, "floor_map", None)
    if fm is None:
        return None, ""
    coord = fm.player_coords.get(run.user_id, "")
    return fm.rooms.get(coord), coord


def _reveal_any_special(fm, count: int = 1) -> List[str]:
    candidates = [
        c for c, r in fm.rooms.items()
        if r.room_type not in ("wall", "obstacle", "empty", "spawn", "secret_boss")
        and not r.explored
        and c not in fm.revealed_coords
    ]
    if not candidates:
        candidates = [
            c for c, r in fm.rooms.items()
            if r.room_type not in ("wall", "secret_boss")
            and not r.explored
            and c not in fm.revealed_coords
        ]
    random.shuffle(candidates)
    chosen = candidates[:count]
    for c in chosen:
        if c not in fm.revealed_coords:
            fm.revealed_coords.append(c)
    return chosen


def resolve_npc_in_room(room, query: str, fm=None, include_hostile: bool = True) -> Optional[str]:
    if room is None:
        return None
    ensure_room_hostile_npcs(fm, room)
    alive = get_effective_alive_npcs(fm, room)
    if not include_hostile:
        alive = [nid for nid in alive if not ROOM_NPCS.get(nid, {}).get("hostile")]
    if not alive:
        return None
    q = (query or "").strip()
    if not q:
        return alive[0] if len(alive) == 1 else None
    ql = q.lower()
    entries = []
    for nid in alive:
        if nid.lower() == ql:
            return nid
        cfg = ROOM_NPCS.get(nid, {})
        name = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else nid
        if name.lower() == ql or ql in name.lower():
            return nid
        entries.append((nid, name))
        for alias in cfg.get("aliases", []):
            if alias.lower() == ql:
                return nid
            entries.append((nid, alias))
    from ...cli.base.pinyin_match import find_entry_by_query
    return find_entry_by_query(entries, q)


def resolve_prop_in_room(room, query: str, fm=None) -> Optional[str]:
    if room is None:
        return None
    ensure_treasure_chest_prop(room)
    props = get_effective_props(fm, room)
    if not props:
        return None
    q = (query or "").strip()
    if not q:
        return None
    ql = q.lower()
    entries = []
    for pid in props:
        if pid.lower() == ql:
            return pid
        cfg = ROOM_PROPS.get(pid, {})
        name = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else pid
        if name.lower() == ql or ql in name.lower():
            return pid
        entries.append((pid, name))
        for alias in cfg.get("aliases", []):
            if alias.lower() == ql:
                return pid
            entries.append((pid, alias))
    from ...cli.base.pinyin_match import find_entry_by_query
    return find_entry_by_query(entries, q)


@register_prop_handler("ancient_brazier")
def _touch_ancient_brazier(run, room, cfg, p, fm, coord):
    sp = restore_sp(p, cfg["sp_gain"])
    return get_locale_text("i18n_room_interact.touch.ancient_brazier", sp=sp)


@register_prop_handler("cracked_statue")
def _touch_cracked_statue(run, room, cfg, p, fm, coord):
    if random.random() < cfg["trap_chance"]:
        dmg = cfg["trap_dmg"]
        p.hp = max(1, p.hp - dmg)
        p.gold += cfg["gold_gain"]
        return get_locale_text("i18n_room_interact.touch.cracked_statue_trap", dmg=dmg, gold=cfg["gold_gain"])
    p.gold += cfg["gold_gain"]
    return get_locale_text("i18n_room_interact.touch.cracked_statue_gold", gold=cfg["gold_gain"])


@register_prop_handler("alchemy_desk")
def _touch_alchemy_desk(run, room, cfg, p, fm, coord):
    pid = roll_potion(getattr(p, "selected_class", "法师"))
    ok, _ = add_bag_item(p, f"potion:{pid}")
    if ok:
        return get_locale_text("i18n_room_interact.touch.alchemy_desk_potion", potion=get_potion_name(pid))
    ok2, _ = add_bag_item(p, cfg["fallback_item"])
    if ok2:
        return get_locale_text("i18n_room_interact.touch.alchemy_desk_item", item=get_item_display_name(cfg["fallback_item"]))
    room.items.append(f"potion:{pid}")
    return get_locale_text("i18n_room_interact.touch.alchemy_desk_full", potion=get_potion_name(pid))


@register_prop_handler("bloodied_pack")
def _touch_bloodied_pack(run, room, cfg, p, fm, coord):
    p.gold += cfg["gold_gain"]
    ok, _ = add_bag_item(p, cfg["item"])
    if not ok:
        add_effective_item(fm, room, cfg["item"])
    return get_locale_text("i18n_room_interact.touch.bloodied_pack", gold=cfg["gold_gain"])


@register_prop_handler("runic_wall")
def _touch_runic_wall(run, room, cfg, p, fm, coord):
    revealed = _reveal_any_special(fm, cfg["reveal_count"]) if fm is not None else []
    if revealed:
        return get_locale_text("i18n_room_interact.touch.runic_wall_reveal", coord=revealed[0])
    restore_sp(p, cfg["sp_fallback"])
    return get_locale_text("i18n_room_interact.touch.runic_wall_sp")


@register_prop_handler("crystal_cluster")
def _touch_crystal_cluster(run, room, cfg, p, fm, coord):
    before = p.hp
    p.hp = min(p.max_hp, p.hp + cfg["heal"])
    sp = restore_sp(p, cfg["sp_gain"])
    return get_locale_text("i18n_room_interact.touch.crystal_cluster", hp=p.hp - before, sp=sp)


@register_prop_handler("shop_scale")
def _touch_shop_gold(run, room, cfg, p, fm, coord):
    p.gold += cfg["gold_gain"]
    return get_locale_text("i18n_room_interact.touch.shop_scale", gold=cfg["gold_gain"])


@register_prop_handler("shop_display")
def _touch_shop_display(run, room, cfg, p, fm, coord):
    p.gold += cfg["gold_gain"]
    return get_locale_text("i18n_room_interact.touch.shop_display", gold=cfg["gold_gain"])


@register_prop_handler("cafe_espresso_machine")
def _touch_cafe_espresso_machine(run, room, cfg, p, fm, coord):
    sp = restore_sp(p, cfg["sp_gain"])
    return get_locale_text("i18n_room_interact.touch.cafe_espresso_machine", sp=sp)


@register_prop_handler("cafe_gramophone")
def _touch_cafe_gramophone(run, room, cfg, p, fm, coord):
    from ..persistent_buffs import cure_persistent_debuffs
    old_ex = getattr(p, "exhaustion", 0)
    new_ex = reduce_exhaustion(p, cfg["exhaustion_cure"])
    cure_persistent_debuffs(p, 1)
    return get_locale_text("i18n_room_interact.touch.cafe_gramophone", cured=max(0, old_ex - new_ex))


@register_prop_handler("cafe_guestbook")
def _touch_cafe_guestbook(run, room, cfg, p, fm, coord):
    revealed = _reveal_any_special(fm, cfg["reveal_count"]) if fm is not None else []
    target_c = revealed[0] if revealed else (fm.boss_coord if fm is not None and fm.boss_coord else coord)
    return get_locale_text("i18n_room_interact.touch.cafe_guestbook", coord=target_c)


@register_prop_handler("forgotten_shrine")
def _touch_forgotten_shrine(run, room, cfg, p, fm, coord):
    from ..persistent_buffs import add_persistent_buff
    before = p.hp
    p.hp = min(p.max_hp, p.hp + cfg["heal"])
    buff_id, stacks = cfg["buff"]
    add_persistent_buff(p, buff_id, stacks)
    return get_locale_text("i18n_room_interact.touch.forgotten_shrine", heal=p.hp - before)


@register_prop_handler("arcane_mirror")
def _touch_arcane_mirror(run, room, cfg, p, fm, coord):
    revealed = _reveal_any_special(fm, cfg["reveal_count"]) if fm is not None else []
    if revealed:
        return get_locale_text("i18n_room_interact.touch.arcane_mirror_reveal", coords="、".join(revealed))
    sp = restore_sp(p, cfg["sp_gain"])
    p.gold += cfg["gold_gain"]
    return get_locale_text("i18n_room_interact.touch.arcane_mirror_fallback", sp=sp, gold=cfg["gold_gain"])


@register_prop_handler("smuggler_cache")
def _touch_smuggler_cache(run, room, cfg, p, fm, coord):
    loot = random.choice(cfg["loot"])
    ok, _ = add_bag_item(p, loot)
    if ok:
        return get_locale_text("i18n_room_interact.touch.smuggler_cache_item", item=get_item_display_name(loot))
    p.gold += cfg["gold_gain"]
    return get_locale_text("i18n_room_interact.touch.smuggler_cache_gold", gold=cfg["gold_gain"])


@register_prop_handler("dusty_bookshelf")
def _touch_dusty_bookshelf(run, room, cfg, p, fm, coord):
    from ..persistent_buffs import add_persistent_buff
    buff_id, stacks = cfg["buff"]
    add_persistent_buff(p, buff_id, stacks)
    ok, _ = add_bag_item(p, cfg["item"])
    if not ok:
        add_effective_item(fm, room, cfg["item"])
    return get_locale_text("i18n_room_interact.touch.dusty_bookshelf")


@register_prop_handler("nordic_urn")
def _touch_nordic_urn(run, room, cfg, p, fm, coord):
    from ....data.world.map_quest_config import BLEAK_FALLS_REWARDS
    gold = BLEAK_FALLS_REWARDS["urn_gold"]
    p.gold += gold
    return get_locale_text("i18n_bleak_falls.props.nordic_urn_res", gold=gold)


@register_prop_handler("bleak_clue_tablet")
def _touch_bleak_clue_tablet(run, room, cfg, p, fm, coord):
    return get_locale_text("i18n_bleak_falls.props.bleak_clue_res")


@register_prop_handler("nordic_brazier")
def _touch_nordic_brazier(run, room, cfg, p, fm, coord):
    from ....data.world.map_quest_config import BLEAK_FALLS_REWARDS
    from ..map_quest_service import record_brazier_lit
    heal = BLEAK_FALLS_REWARDS["brazier_heal"]
    p.hp = min(p.max_hp, p.hp + heal)
    record_brazier_lit(run)
    return get_locale_text("i18n_bleak_falls.props.nordic_brazier_res")


def _open_treasure_chest(save_manager, run, room, coord: str, map_engine=None) -> str:
    from ....renderer import GameRenderer
    from ...party.session import SessionContextScoper
    fm = getattr(run, "floor_map", None)
    uid = run.user_id
    bonus_item = room.shared_payload.pop("bonus_item", "")
    if bonus_item:
        ok, _ = add_bag_item(run.player, bonus_item)
        if not ok:
            add_effective_item(fm, room, bonus_item)
    SessionContextScoper.create_session(run, coord, "treasure", [uid])
    if map_engine is not None and hasattr(map_engine, "explore_engine"):
        map_engine.explore_engine._init_treasure_node(run)
    else:
        from ...battle.engine import BattleEngine
        from ..explore_engine import ExploreEngine
        from ..map_engine import MapEngine
        me = MapEngine(save_manager, BattleEngine(save_manager))
        ExploreEngine(save_manager, me)._init_treasure_node(run)
    save_manager.save_save(uid, run)
    return GameRenderer.render_game(run)


def touch_in_room(save_manager, run, query: str, map_engine=None) -> str:
    q = (query or "").strip()
    if not q:
        return get_locale_text("i18n_room_interact.touch.need_arg")
    from ...social.player_inspect import touch_player_status
    player_status = touch_player_status(save_manager, run.user_id, q, run=run)
    if player_status is not None:
        return player_status
    room, coord = get_current_room(run)
    if room is None:
        return get_locale_text("i18n_grid_map.err_no_floor_map")
    fm = getattr(run, "floor_map", None)
    if room.room_type == "downstairs":
        from ..landmark_system import ensure_descent_tunnel
        ensure_descent_tunnel(room)
    prop_id = resolve_prop_in_room(room, q, fm=fm)
    if not prop_id:
        from ....data.world.open_world_config import WORLD_YOG_TEMPLE
        from ....data.world.world_social_config import WORLD_SNOWFIELD
        from ....data.world.yog_quest_config import YOG_FLOOR_TEMPLE
        from ..open_world.ghost_service import OpenWorldGhostService
        from ..open_world.loadout_service import is_open_world_run

        if is_open_world_run(run):
            floor_idx = getattr(fm, "floor_index", 0) if fm is not None else 0
            world = WORLD_YOG_TEMPLE if floor_idx == YOG_FLOOR_TEMPLE else WORLD_SNOWFIELD
            ghost_msg = OpenWorldGhostService.try_inspect_ghost(save_manager, world, coord, q, is_touch=True)
            if ghost_msg is not None:
                broken_msg = break_map_invisibility(run, reason="interact")
                if broken_msg:
                    save_manager.save_save(run.user_id, run)
                    return f"{broken_msg}\n{ghost_msg}"
                return ghost_msg
        return get_locale_text("i18n_room_interact.touch.not_found", target=q)
    cfg = ROOM_PROPS.get(prop_id, {})
    pname = get_locale_text(cfg["name_key"]) if cfg.get("name_key") else prop_id
    broken_msg = break_map_invisibility(run, reason="interact")
    if prop_id in ("descent_tunnel", "temple_gate"):
        from ..landmark_system import open_room_talk
        from ....renderer import GameRenderer
        err = open_room_talk(save_manager, run, run.user_id)
        if err:
            if broken_msg:
                save_manager.save_save(run.user_id, run)
            return err
        save_manager.save_save(run.user_id, run)
        rendered = GameRenderer.render_game(run)
        return f"{broken_msg}\n\n{rendered}" if broken_msg else rendered
    done = get_effective_interacted_props(fm, room)
    if prop_id in done:
        if broken_msg:
            save_manager.save_save(run.user_id, run)
        already_msg = get_locale_text("i18n_room_interact.touch.already_done", name=pname)
        return f"{broken_msg}\n{already_msg}" if broken_msg else already_msg
    mark_effective_prop_interacted(fm, room, prop_id)
    if prop_id == "treasure_chest":
        res = _open_treasure_chest(save_manager, run, room, coord, map_engine=map_engine)
        return f"{broken_msg}\n\n{res}" if broken_msg else res
    if fm is not None and fm.floor_flags.get("chireiden_zone"):
        from .. import chireiden as _chireiden_mod
    handler = PROP_HANDLERS.get(prop_id)
    if handler:
        msg = handler(run, room, cfg, run.player, fm, coord)
    else:
        msg = get_locale_text("i18n_room_interact.touch.already_done", name=pname)
    from .forced_triggers import run_forced_triggers

    trigger_logs = run_forced_triggers(run, fm, room, "on_interact")
    from ....data.content.chireiden_data import CHIREIDEN_PROPS

    if prop_id in CHIREIDEN_PROPS:
        from ...progress.achievement_service import record_run_achievement_stat

        record_run_achievement_stat(save_manager, run, "chireiden_facilities_used", 1)
    save_manager.save_save(run.user_id, run)
    parts = [x for x in (broken_msg, *trigger_logs, msg) if x]
    return "\n".join(parts)


def take_in_room(save_manager, run, query: str) -> str:
    q = (query or "").strip()
    if not q:
        return get_locale_text("i18n_room_interact.bag.take_need_arg")
    room, _ = get_current_room(run)
    if room is None:
        return get_locale_text("i18n_grid_map.err_no_floor_map")
    fm = getattr(run, "floor_map", None)
    items = get_effective_items(fm, room)
    item_id = resolve_item_query(q, items)
    if not item_id:
        return get_locale_text("i18n_room_interact.bag.take_not_found", target=q)
    ok, msg = add_bag_item(run.player, item_id)
    if ok:
        remove_effective_item(fm, room, item_id)
        save_manager.save_save(run.user_id, run)
    return msg


def format_room_env_with_props(room, include_cleared_suffix: bool = True, fm=None) -> str:
    ensure_treasure_chest_prop(room)
    env_id = getattr(room, "env_id", "") or "dungeon_corridor"
    env_text = get_locale_text(f"i18n_room_interact.env.{env_id}")
    if include_cleared_suffix and room.cleared and room.room_type not in ("spawn", "empty", "shop", "cafe", "landmark", "downstairs"):
        env_text += get_locale_text("i18n_room_interact.env.cleared_suffix")
    done_props = set(get_effective_interacted_props(fm, room))
    for pid in get_effective_props(fm, room):
        if pid not in ROOM_PROPS:
            continue
        skey = f"i18n_room_interact.props.{pid}.done_scene" if pid in done_props else f"i18n_room_interact.props.{pid}.scene"
        env_text += get_locale_text(skey)
    return env_text


def format_room_extras(run, include_env: bool = True) -> List[str]:
    from ....renderer.formatters import format_npcs_and_players_line
    from ..presence import render_players_for
    room, _ = get_current_room(run)
    if room is None:
        return []
    fm = getattr(run, "floor_map", None)
    ensure_room_hostile_npcs(fm, room)
    lines = []
    if include_env:
        lines.append(format_room_env_with_props(room, include_cleared_suffix=True, fm=fm))
    alive_npcs = [nid for nid in get_effective_alive_npcs(fm, room) if nid in ROOM_NPCS]
    nnames = [f"【{get_locale_text(ROOM_NPCS[nid]['name_key'])}】" for nid in alive_npcs]
    world_here = render_players_for(getattr(run, "user_id", ""), run=run)
    npc_line = format_npcs_and_players_line(nnames, world_here)
    if npc_line:
        lines.append(npc_line)
    items = get_effective_items(fm, room)
    if items:
        inames = [f"【{get_item_display_name(it)}】" for it in items]
        lines.append(get_locale_text("i18n_room_interact.room_ui.items_line", items="、".join(inames)))
    return lines


from . import chaos_props
