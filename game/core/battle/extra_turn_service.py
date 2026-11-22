import random
from typing import Optional

from ...data.battle.extra_turn_config import ARHAT_MAX_PLAYS
from ...models.state import CardState, GameRun, PlayerState, ensure_card_state
from ..text.events import LocaleText, TextDocument, locale_text

QUEUE_KEY = "extra_turn_queue"
ACTIVE_KEY = "active_extra_turn"
LEGACY_KEY = "extra_turns_left"
LEGACY_UPGRADED_KEY = "time_stop_upgraded"

MODE_TIME_STOP = "time_stop"
MODE_ARHAT = "arhat"
MODE_EXTRA = "extra"


def _make_spec(mode: str, break_on_damage: bool = False, pause_debuffs: bool = False, source: str = "") -> dict:
    return {
        "mode": str(mode),
        "break_on_damage": bool(break_on_damage),
        "pause_debuffs": bool(pause_debuffs),
        "source": str(source or ""),
    }


def _owner(run: GameRun) -> str:
    uid = str(run.user_id or "")
    if uid and uid in run.players:
        return uid
    humans = run.human_uids()
    if humans:
        return str(humans[0])
    return uid


def _queue(run: GameRun) -> dict:
    queue = run.node_data.get(QUEUE_KEY)
    if not isinstance(queue, dict):
        queue = {}
        run.node_data[QUEUE_KEY] = queue
    return queue


def _normalize(run: GameRun) -> None:
    queue = _queue(run)
    for uid in list(queue.keys()):
        specs = queue.get(uid)
        if not isinstance(specs, list):
            queue.pop(uid, None)
            continue
        cleaned = [dict(spec) for spec in specs if isinstance(spec, dict) and str(spec.get("mode") or "")]
        if cleaned:
            queue[uid] = cleaned
        else:
            queue.pop(uid, None)
    active = run.node_data.get(ACTIVE_KEY)
    if isinstance(active, dict) and str(active.get("uid") or "") and str(active.get("mode") or ""):
        run.node_data[ACTIVE_KEY] = {str(active["uid"]): dict(active)}
    elif isinstance(active, dict):
        cleaned_active = {
            str(uid): dict(spec)
            for uid, spec in active.items()
            if isinstance(spec, dict) and str(spec.get("mode") or "")
        }
        if cleaned_active:
            run.node_data[ACTIVE_KEY] = cleaned_active
        else:
            run.node_data.pop(ACTIVE_KEY, None)
    legacy = int(run.node_data.get(LEGACY_KEY) or 0)
    if legacy <= 0:
        return
    uid = _owner(run)
    if not uid:
        return
    spec = _make_spec(
        MODE_TIME_STOP,
        break_on_damage=True,
        pause_debuffs=bool(run.node_data.get(LEGACY_UPGRADED_KEY)),
        source="legacy",
    )
    queue.setdefault(uid, []).extend(dict(spec) for _ in range(legacy))
    run.node_data.pop(LEGACY_KEY, None)
    run.node_data.pop(LEGACY_UPGRADED_KEY, None)


def grant_extra_turn(
    run: GameRun,
    uid: str,
    mode: str,
    count: int = 1,
    *,
    break_on_damage: bool = False,
    pause_debuffs: bool = False,
    source: str = "",
) -> None:
    """为指定玩家登记一次额外回合，声明伤害中断与负面状态暂停语义。"""
    _normalize(run)
    owner = str(uid or _owner(run))
    total = max(0, int(count or 0))
    if not owner or total <= 0:
        return
    spec = _make_spec(mode, break_on_damage=break_on_damage, pause_debuffs=pause_debuffs, source=source)
    _queue(run).setdefault(owner, []).extend(dict(spec) for _ in range(total))


def _active_map(run: GameRun) -> dict:
    active = run.node_data.get(ACTIVE_KEY)
    if not isinstance(active, dict):
        active = {}
        run.node_data[ACTIVE_KEY] = active
    return active


def active_spec(run: GameRun, uid: str = "") -> Optional[dict]:
    """返回当前激活的额外回合规格，未指定玩家时取首个活跃项。"""
    _normalize(run)
    active = run.node_data.get(ACTIVE_KEY)
    if not isinstance(active, dict):
        return None
    if not uid:
        return next((dict(spec) for spec in active.values() if isinstance(spec, dict)), None)
    spec = active.get(str(uid))
    return dict(spec) if isinstance(spec, dict) else None


def is_arhat_active(run: GameRun, uid: str = "") -> bool:
    """判断当前激活的额外回合是否为阿罗汉自动战斗模式。"""
    active = active_spec(run, uid)
    return bool(active and str(active.get("mode") or "") == MODE_ARHAT)


def should_pause_debuffs(run: GameRun, uid: str = "") -> bool:
    """判断当前额外回合是否暂停负面状态计时。"""
    active = active_spec(run, uid)
    return bool(active and active.get("pause_debuffs"))


def should_break_on_damage(run: GameRun, uid: str = "") -> bool:
    """判断当前额外回合是否在造成伤害后提前结束。"""
    active = active_spec(run, uid)
    return bool(active and active.get("break_on_damage"))


def clear_active(run: GameRun, uid: str = "") -> bool:
    """清除活跃额外回合；指定玩家为空时清空全部。"""
    _normalize(run)
    active = run.node_data.get(ACTIVE_KEY)
    if not isinstance(active, dict):
        return False
    if uid:
        if str(uid) not in active:
            return False
        active.pop(str(uid), None)
    else:
        active.clear()
    if not active:
        run.node_data.pop(ACTIVE_KEY, None)
    return True


def _banner(spec: dict, remaining: int) -> LocaleText:
    mode = str(spec.get("mode") or "")
    if mode == MODE_TIME_STOP:
        return locale_text("i18n_battle_core.time_stop_extra_turn", params={"count": remaining})
    if mode == MODE_ARHAT:
        return locale_text("i18n_cards_ninja.arhat_takeover")
    return locale_text("i18n_battle_core.extra_turn_start", params={"count": remaining})


def _party_target(run: GameRun, uid: str, target_type: str) -> Optional[str]:
    from .party_battle import party_slots, party_target_ref
    slots = party_slots(run, alive_only=True)
    if target_type in ("ally", "any_other"):
        slots = [item for item in slots if item[1] != uid]
    if not slots:
        return None
    return party_target_ref(run, random.choice(slots)[1])


def _random_target(run: GameRun, uid: str, card) -> Optional[str]:
    from .selection.target_rules import is_coop_ally_card
    base_id = str(getattr(card, "id", ""))
    target_type = str(getattr(card, "target_type", "enemy") or "enemy")
    if is_coop_ally_card(card):
        return _party_target(run, uid, "ally_or_self")
    if target_type in ("none", "self", "all_enemies", "random_enemy"):
        return None
    if target_type in ("ally", "ally_or_self", "any_other"):
        return _party_target(run, uid, target_type)
    alive = [index + 1 for index, enemy in enumerate(run.enemies) if enemy.hp > 0]
    if not alive:
        return None
    return f"e{random.choice(alive)}"


def _needs_target(card) -> bool:
    from .selection.target_rules import is_coop_ally_card
    base_id = str(getattr(card, "id", ""))
    target_type = str(getattr(card, "target_type", "enemy") or "enemy")
    if is_coop_ally_card(card):
        return True
    return target_type not in ("none", "self", "all_enemies", "random_enemy")


def _playable_candidates(engine, run: GameRun, uid: str, player: PlayerState, blocked: set[int]) -> list[tuple[int, Optional[str], CardState]]:
    from ...entities import ALL_CARDS
    from .card_cost import resolve_card_effective_cost_a
    candidates: list[tuple[int, Optional[str], CardState]] = []
    for index, raw_state in enumerate(player.hand, 1):
        if id(raw_state) in blocked:
            continue
        state = ensure_card_state(raw_state)
        card = ALL_CARDS.get(state)
        if card is None:
            continue
        if getattr(card, "unplayable", False) or getattr(card, "type", "") == "curse":
            continue
        if getattr(card, "arhat_forbidden", False):
            continue
        if card.get_selection_spec(run, engine) is not None:
            continue
        if getattr(card, "type", "") in ("minion", "amulet") and engine._get_free_grid(player) is None:
            continue
        cost_a = resolve_card_effective_cost_a(card, state, player)
        cost_ba = int(getattr(card, "cost_ba", 0) or 0)
        req_a = player.actions if cost_a == -1 else cost_a
        req_ba = player.bonus_actions if cost_ba == -1 else cost_ba
        if player.actions < req_a or player.bonus_actions < req_ba:
            continue
        if int(getattr(card, "self_hp_cost", 0) or 0) >= player.hp:
            continue
        target = _random_target(run, uid, card)
        if _needs_target(card) and target is None:
            continue
        if card.can_play_error(run, target, engine):
            continue
        candidates.append((index, target, state))
    return candidates


FORCE_END_REQUEST_KEY = "force_end_request"


def request_force_end(run: GameRun, player: PlayerState, source: str) -> None:
    """登记一次强制结束回合请求，统一旧版三个 node_data 键。"""
    uid = run.uid_for(player) or run.user_id
    run.node_data[FORCE_END_REQUEST_KEY] = {"uid": uid, "source": source}


def consume_force_end_request(run: GameRun, player: PlayerState) -> bool:
    """消费当前玩家的强制结束回合请求；其他玩家的请求保留。"""
    request = run.node_data.get(FORCE_END_REQUEST_KEY)
    if not isinstance(request, dict):
        return False
    uid = run.uid_for(player) or run.user_id
    if request.get("uid") != uid:
        return False
    run.node_data.pop(FORCE_END_REQUEST_KEY, None)
    return True


def _run_arhat_turn(engine, run: GameRun, uid: str, player: PlayerState) -> TextDocument:
    from ...entities import ALL_CARDS
    events: TextDocument = []
    blocked: set[int] = set()
    played = 0
    while played < ARHAT_MAX_PLAYS:
        if player.hp <= 0 or player.downed or engine.is_battle_won(run):
            break
        if consume_force_end_request(run, player):
            break
        candidates = _playable_candidates(engine, run, uid, player, blocked)
        if not candidates:
            events.append(locale_text("i18n_cards_ninja.arhat_no_action"))
            break
        index, target, state = random.choice(candidates)
        card = ALL_CARDS.get(state)
        result = engine.card_player.play_card(run, index, target)
        played += 1
        if not result or result.startswith("❌") or result.startswith("[FAIL]"):
            blocked.add(id(state))
            continue
        events.append(locale_text(
            "i18n_cards_ninja.arhat_play_card",
            params={"card": card.name if card is not None else state.id, "result": result},
        ))
    return events


def begin_pending(engine, run: GameRun, uid: str) -> tuple[TextDocument, bool]:
    """启动排队中的额外回合，返回文本事件流与是否仍需等待后续回合。"""
    from ..party.coordinator import restore_player, swap_player
    _normalize(run)
    owner = str(uid or _owner(run))
    player = run.players.get(owner)
    events: TextDocument = []
    while True:
        if player is None or player.hp <= 0 or player.downed or engine.is_battle_won(run):
            return events, False
        specs = _queue(run).get(owner)
        if not isinstance(specs, list) or not specs:
            return events, False
        spec = dict(specs.pop(0))
        spec["uid"] = owner
        if not specs:
            _queue(run).pop(owner, None)
        _active_map(run)[owner] = spec
        events.append(_banner(spec, len(specs)))
        previous, previous_user = swap_player(run, player)
        try:
            events.extend(engine.card_player._begin_player_phase_events(run, player, advance_global=False))
            if str(spec.get("mode") or "") == MODE_ARHAT:
                events.extend(_run_arhat_turn(engine, run, owner, player))
                events.extend(engine.card_player._end_player_phase_events(run, player))
        finally:
            restore_player(run, previous, previous_user)
        if player.hp <= 0 or player.downed or engine.is_battle_won(run):
            clear_active(run, owner)
            return events, False
        if str(spec.get("mode") or "") != MODE_ARHAT:
            return events, True
        clear_active(run, owner)


def end_and_begin(engine, run: GameRun, uid: str) -> tuple[TextDocument, bool]:
    """结束当前额外回合并立即启动下一个排队项。"""
    clear_active(run, uid)
    return begin_pending(engine, run, uid)
