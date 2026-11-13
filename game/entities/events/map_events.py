import random
from .base import EventOption
from ...data.event_data import EVENT_CONFIG, EVENT_MIN_HP
from ...data.card_upgrade_data import CARD_UPGRADE_CONFIG
from ...data.reward_config import TREASURE_RELIC_POOL
from ...data.locale_data import get_locale_text
from ...entities import ALL_CARDS, get_relic_name
from ...models.state import ensure_card_state
from ...core.inventory.deck_service import DeckService
from ...core.world.sp_system import consume_sp, restore_sp


def _coord_to_xy(coord: str) -> tuple[int, int]:
    if not coord or len(coord) < 2:
        return 0, 0
    col = ord(coord[0].upper()) - ord("A")
    try:
        row = int(coord[1:]) - 1
    except ValueError:
        row = 0
    return col, row


def _xy_to_coord(x: int, y: int) -> str:
    return f"{chr(ord('A') + x)}{y + 1}"


class AcceptGhostificationOption(EventOption, action="accept_ghostification", text=get_locale_text("i18n_grid_map.event.ghostification.opt_accept")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("ghostification", {})
        p.max_hp = max(1, p.max_hp // 2)
        p.hp = min(p.hp, p.max_hp)
        if "ghost_body" not in p.relics:
            p.relics.append("ghost_body")
        cnt = int(cfg.get("intangible_count", 2))
        for _ in range(cnt):
            DeckService.add_card_to_deck(p, "intangible")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.ghostification.result_accept", max_hp=p.max_hp, count=cnt)


class RefuseGhostificationOption(EventOption, action="refuse_ghostification", text=get_locale_text("i18n_grid_map.event.ghostification.opt_refuse")):
    def _run_effect(self, run, engine) -> str:
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.ghostification.result_refuse")


def _break_adjacent_wall(run) -> str:
    fm = getattr(run, "floor_map", None)
    if fm is None:
        return ""
    cur = fm.player_coords.get(run.user_id, "")
    cx, cy = _coord_to_xy(cur)
    candidates = []
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = cx + dx, cy + dy
        if 0 <= nx < fm.width and 0 <= ny < fm.height:
            nc = _xy_to_coord(nx, ny)
            room = fm.rooms.get(nc)
            if room and room.room_type == "wall":
                candidates.append(nc)
    if not candidates:
        return ""
    chosen = random.choice(candidates)
    room = fm.rooms[chosen]
    room.room_type = "empty"
    room.explored = True
    room.cleared = True
    if chosen not in fm.revealed_coords:
        fm.revealed_coords.append(chosen)
    return chosen


class TunnelBreakSpOption(EventOption, action="tunnel_break_sp", text=get_locale_text("i18n_grid_map.event.collapsed_tunnel.opt_sp")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("collapsed_tunnel", {})
        sp_cost = int(cfg.get("sp_cost", 3))
        broken = _break_adjacent_wall(run)
        if not broken:
            fb = int(cfg.get("fallback_gold", 10))
            p.gold += fb
            engine.enter_next_stage(run)
            engine.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_grid_map.event.collapsed_tunnel.result_no_wall", gold=fb)
        consume_sp(p, sp_cost, allow_overdraft=True)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.collapsed_tunnel.result_sp", coord=broken, cost=sp_cost)


class TunnelBreakGoldOption(EventOption, action="tunnel_break_gold", text=get_locale_text("i18n_grid_map.event.collapsed_tunnel.opt_gold")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("collapsed_tunnel", {})
        gold_cost = int(cfg.get("gold_cost", 25))
        if p.gold < gold_cost:
            return get_locale_text("i18n_grid_map.event.collapsed_tunnel.not_enough_gold", cost=gold_cost)
        broken = _break_adjacent_wall(run)
        if not broken:
            fb = int(cfg.get("fallback_gold", 10))
            p.gold += fb
            engine.enter_next_stage(run)
            engine.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_grid_map.event.collapsed_tunnel.result_no_wall", gold=fb)
        p.gold -= gold_cost
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.collapsed_tunnel.result_gold", coord=broken, cost=gold_cost)


class TunnelLeaveOption(EventOption, action="tunnel_leave", text=get_locale_text("i18n_grid_map.event.collapsed_tunnel.opt_leave")):
    def _run_effect(self, run, engine) -> str:
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.collapsed_tunnel.result_leave")


class BeaconScanOption(EventOption, action="beacon_scan", text=get_locale_text("i18n_grid_map.event.ancient_beacon.opt_scan")):
    def _run_effect(self, run, engine) -> str:
        fm = getattr(run, "floor_map", None)
        revealed = []
        if fm is not None:
            cur = fm.player_coords.get(run.user_id, "")
            cx, cy = _coord_to_xy(cur)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < fm.width and 0 <= ny < fm.height:
                        nc = _xy_to_coord(nx, ny)
                        room = fm.rooms.get(nc)
                        if room and room.room_type != "secret_boss":
                            room.explored = True
                            if nc not in fm.revealed_coords:
                                fm.revealed_coords.append(nc)
                            revealed.append(nc)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.ancient_beacon.result_scan", count=len(revealed))


class BeaconIgniteDangerOption(EventOption, action="beacon_ignite_danger", text=get_locale_text("i18n_grid_map.event.ancient_beacon.opt_danger")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("ancient_beacon", {})
        pool = [r for r in TREASURE_RELIC_POOL if r not in p.relics]
        if not pool:
            pool = list(TREASURE_RELIC_POOL)
        got_relic = random.choice(pool)
        if got_relic not in p.relics:
            p.relics.append(got_relic)
        relic_name = get_relic_name(got_relic)
        converted = 0
        fm = getattr(run, "floor_map", None)
        if fm is not None:
            limit = int(cfg.get("danger_convert_count", 2))
            cur = fm.player_coords.get(run.user_id, "")
            cx, cy = _coord_to_xy(cur)
            candidates = []
            for coord, room in fm.rooms.items():
                if room.room_type == "battle" and not room.cleared:
                    rx, ry = _coord_to_xy(coord)
                    candidates.append((abs(rx - cx) + abs(ry - cy), coord, room))
            candidates.sort(key=lambda x: x[0])
            for _, _, room in candidates[:limit]:
                room.room_type = "high_danger"
                room.is_high_danger = True
                converted += 1
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.ancient_beacon.result_danger", relic=relic_name, count=converted)


class BeaconLeaveOption(EventOption, action="beacon_leave", text=get_locale_text("i18n_grid_map.event.ancient_beacon.opt_leave")):
    def _run_effect(self, run, engine) -> str:
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.ancient_beacon.result_leave")


class FerryToSpecialOption(EventOption, action="ferry_to_special", text=get_locale_text("i18n_grid_map.event.mist_ferryman.opt_ferry")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("mist_ferryman", {})
        gold_cost = int(cfg.get("gold_cost", 15))
        sp_cost = int(cfg.get("sp_cost", 2))
        if p.gold >= gold_cost:
            p.gold -= gold_cost
            cost_msg = get_locale_text("i18n_grid_map.event.mist_ferryman.cost_gold", cost=gold_cost)
        else:
            consume_sp(p, sp_cost, allow_overdraft=True)
            cost_msg = get_locale_text("i18n_grid_map.event.mist_ferryman.cost_sp", cost=sp_cost)
        fm = getattr(run, "floor_map", None)
        target_coord = ""
        if fm is not None:
            special_types = ("treasure", "landmark", "cafe", "shop", "rest", "life_merchant")
            unvisited = [c for c, r in fm.rooms.items() if r.room_type in special_types and not r.explored]
            if not unvisited:
                cur = fm.player_coords.get(run.user_id, "")
                unvisited = [c for c, r in fm.rooms.items() if r.room_type in special_types and c != cur]
            if unvisited:
                target_coord = random.choice(unvisited)
        engine.enter_next_stage(run)
        if fm is not None and target_coord:
            fm.player_coords[run.user_id] = target_coord
            room = fm.rooms.get(target_coord)
            if room:
                room.explored = True
            if target_coord not in fm.revealed_coords:
                fm.revealed_coords.append(target_coord)
            engine.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_grid_map.event.mist_ferryman.result_ferry", cost_msg=cost_msg, coord=target_coord)
        fb_gold = int(cfg.get("fallback_gold", 20))
        fb_heal = int(cfg.get("fallback_heal", 6))
        p.gold += fb_gold
        p.hp = min(p.max_hp, p.hp + fb_heal)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.mist_ferryman.result_fallback", gold=fb_gold, heal=fb_heal)


class FerryRefuseOption(EventOption, action="ferry_refuse", text=get_locale_text("i18n_grid_map.event.mist_ferryman.opt_refuse")):
    def _run_effect(self, run, engine) -> str:
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.mist_ferryman.result_refuse")


class BladesongLearnOption(EventOption, action="bladesong_learn", text=get_locale_text("i18n_grid_map.event.bladesinger_echo.opt_learn")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("bladesinger_echo", {})
        sp_cost = int(cfg.get("sp_cost", 3))
        hp_cost = int(cfg.get("hp_cost", 6))
        consume_sp(p, sp_cost, allow_overdraft=True)
        p.hp = max(EVENT_MIN_HP, p.hp - hp_cost)
        DeckService.add_card_to_deck(p, "bladesong")
        upgraded_name = ""
        upgradable = []
        for idx, raw in enumerate(p.deck):
            st = ensure_card_state(raw)
            if not st.upgraded and st.id in CARD_UPGRADE_CONFIG:
                upgradable.append((idx, st))
        if upgradable:
            idx, st = random.choice(upgradable)
            st.upgraded = True
            p.deck[idx] = st
            up_card = ALL_CARDS.get(st)
            upgraded_name = up_card.name if up_card else f"{st.id}+"
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        if upgraded_name:
            return get_locale_text("i18n_grid_map.event.bladesinger_echo.result_learn_upgraded", sp=sp_cost, hp=hp_cost, card=upgraded_name)
        return get_locale_text("i18n_grid_map.event.bladesinger_echo.result_learn", sp=sp_cost, hp=hp_cost)


class BladesongMeditateOption(EventOption, action="bladesong_meditate", text=get_locale_text("i18n_grid_map.event.bladesinger_echo.opt_meditate")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("bladesinger_echo", {})
        sp_gain = int(cfg.get("meditate_sp", 4))
        heal_gain = int(cfg.get("meditate_heal", 8))
        restore_sp(p, sp_gain)
        p.hp = min(p.max_hp, p.hp + heal_gain)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_grid_map.event.bladesinger_echo.result_meditate", sp=sp_gain, heal=heal_gain)
