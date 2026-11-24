from ...data.entities.mercenary_data import MERCENARY_CONFIG
from ...data.entities.minions.minion_data import MINION_CONFIG
from ...data.text.locale_data import get_locale_text
from ...entities import get_enemy_template
from ...models.events import BattleStartEvent, EnemyRollIntentEvent, TurnStartEvent
from ...models.state import EnemyState, GameRun, MinionState
from ...renderer import GameRenderer
from ..battle.party_battle import assign_enemy_targets
from ..party.mercenary import (
    build_mercenary_player,
    is_mercenary,
    summon_evil_twin_mercenary,
)
from ..party.session import SessionContextScoper
from .registry import AdminCommandHandler, AdminContext, register_admin_command
from .resolvers import (
    enemy_default_stats,
    resolve_battle_entities,
    resolve_enemy,
    resolve_mercenary,
    resolve_minion,
)


def _init_single_enemy(battle_engine, run: GameRun, enemy: EnemyState) -> None:
    template = get_enemy_template(enemy.name)
    if hasattr(template, "on_battle_start") and not getattr(enemy, "_battle_init_done", False):
        enemy._battle_init_done = True
        template.on_battle_start(run, enemy, battle_engine)
    roll_evt = EnemyRollIntentEvent(run, enemy)
    battle_engine.event_bus.dispatch(roll_evt)
    if roll_evt.cancelled:
        enemy.intents = []
    else:
        enemy.intents = template.roll_intents(run, battle_engine, enemy)
    battle_engine.enemy_controller.sync_enemy_intents(enemy)


def _start_custom_battle(battle_engine, run: GameRun, enemies: list[EnemyState]) -> None:
    battle_engine.current_run = run
    caller = run.user_id
    fm = getattr(run, "floor_map", None)
    if fm is not None:
        coord = fm.player_coords.get(caller, "")
        SessionContextScoper.create_session(
            run,
            coord=coord,
            node_type="battle",
            participants=[caller],
            node_data={"turn_count": 1, "difficulty": "normal", "admin_spawned": True},
            enemies=list(enemies),
        )
    else:
        run.node_type = "battle"
        run.node_data = {"turn_count": 1, "difficulty": "normal", "admin_spawned": True}
        run.enemies = list(enemies)
    viewer = run.player
    turn_ready = {}
    for uid in run.party_order:
        pl = run.players.get(uid)
        if pl is None:
            continue
        run.player = pl
        run.user_id = uid
        battle_engine._init_player_battle(run, pl, "normal")
        turn_ready[uid] = pl.downed or getattr(pl, "is_mercenary", False)
    run.node_data["turn_ready"] = turn_ready
    run.player = viewer
    run.user_id = caller
    for uid in run.party_order:
        pl = run.players.get(uid)
        if pl is None or pl.downed or pl.hp <= 0:
            continue
        run.player = pl
        run.user_id = uid
        battle_engine.event_bus.dispatch(BattleStartEvent(run))
    for uid in run.party_order:
        pl = run.players.get(uid)
        if pl is None or pl.downed or pl.hp <= 0:
            continue
        run.player = pl
        run.user_id = uid
        battle_engine.event_bus.dispatch(TurnStartEvent(run, is_player=True))
    run.player = viewer
    run.user_id = caller
    battle_engine._roll_enemy_intent(run)
    assign_enemy_targets(run, battle_engine)


def _attach_mercenary(run: GameRun, owner_uid: str, merc_id: str, battle_engine) -> tuple[str, int, str]:
    if merc_id == "evil_twin" and run.node_type == "battle":
        merc_uid, slot, merc = summon_evil_twin_mercenary(battle_engine, run, owner_uid)
        return merc_uid, slot, merc.name
    merc_uid = f"merc:{merc_id}:{owner_uid}"
    suffix = 1
    while merc_uid in run.players:
        suffix += 1
        merc_uid = f"merc:{merc_id}:{owner_uid}:{suffix}"
    merc = build_mercenary_player(merc_id, owner_uid)
    owner = run.players.get(owner_uid) or run.player
    merc.stage = owner.stage
    run.players[merc_uid] = merc
    run.party_order.append(merc_uid)
    full_order = getattr(run, "_full_party_order", None)
    if isinstance(full_order, list) and merc_uid not in full_order:
        full_order.append(merc_uid)
    fm = getattr(run, "floor_map", None)
    if fm is not None and isinstance(getattr(fm, "player_session_map", None), dict):
        sid = fm.player_session_map.get(owner_uid)
        if sid and sid in fm.active_sessions:
            fm.player_session_map[merc_uid] = sid
            sess = fm.active_sessions[sid]
            if merc_uid not in sess.participants:
                sess.participants.append(merc_uid)
            if merc_uid not in sess.roster:
                sess.roster.append(merc_uid)
    slot = run.party_order.index(merc_uid) + 1
    if run.node_type == "battle":
        battle_engine.join_battle(run, merc_uid)
    return merc_uid, slot, merc.name


def _dismiss_mercenary(run: GameRun, query: str) -> list[str]:
    removed: list[str] = []
    target_mid = resolve_mercenary(query) if query.lower() != "all" else None
    for uid in list(run.party_order):
        pl = run.players.get(uid)
        if not is_mercenary(pl):
            continue
        if query.lower() != "all":
            if pl.mercenary_id != target_mid and pl.name.lower() != query.lower() and uid != query:
                continue
        removed.append(pl.name)
        run.party_order = [u for u in run.party_order if u != uid]
        full_order = getattr(run, "_full_party_order", None)
        if isinstance(full_order, list) and uid in full_order:
            setattr(run, "_full_party_order", [u for u in full_order if u != uid])
        fm = getattr(run, "floor_map", None)
        if fm is not None:
            fm.player_session_map.pop(uid, None)
            for sess in fm.active_sessions.values():
                if uid in sess.participants:
                    sess.participants.remove(uid)
                if uid in sess.roster:
                    sess.roster.remove(uid)
        run.players.pop(uid, None)
        turn_ready = run.node_data.get("turn_ready")
        if isinstance(turn_ready, dict):
            turn_ready.pop(uid, None)
    return removed


@register_admin_command(
    aliases=("spawn", "sp", "生成"),
    category="battle",
    help_key="i18n_admin.help_cmd_spawn",
    detail_key="i18n_admin.detail_spawn",
)
class SpawnAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args:
            return get_locale_text("i18n_admin.detail_spawn")
        sub = args[0].lower()
        if sub in ("merc", "mercenary", "雇佣兵"):
            return await self._spawn_merc(ctx, args[1:])
        if sub in ("minion", "随从"):
            return await self._spawn_minion(ctx, args[1:])
        if sub in ("enemy", "mob", "monster", "怪物", "敌人"):
            return await self._spawn_enemy(ctx, args[1:])
        return await self._spawn_enemy(ctx, args)

    async def _spawn_enemy(self, ctx: AdminContext, args: list[str]) -> str:
        if not args:
            return get_locale_text("i18n_admin.detail_spawn")
        enemy_name = resolve_enemy(args[0])
        if not enemy_name:
            return get_locale_text("i18n_admin.err_enemy_not_found", enemy=args[0])
        count = 1
        custom_hp: int | None = None
        for tok in args[1:]:
            low = tok.lower()
            if low.startswith("hp="):
                try:
                    custom_hp = max(1, int(tok.split("=", 1)[1]))
                except ValueError:
                    return get_locale_text("i18n_admin.err_int_required", value=tok)
            elif tok.isdigit():
                count = max(1, min(10, int(tok)))
        base_hp, actions, bonus_actions = enemy_default_stats(enemy_name)
        hp = custom_hp if custom_hp is not None else base_hp

        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            battle_engine = ctx.engine.battle_engine
            created: list[EnemyState] = []
            for _ in range(count):
                enemy = battle_engine._build_enemy_state(enemy_name, hp, actions, bonus_actions)
                created.append(enemy)
            if run.node_type == "battle":
                for enemy in created:
                    run.enemies.append(enemy)
                    _init_single_enemy(battle_engine, run, enemy)
                assign_enemy_targets(run, battle_engine)
                msg = get_locale_text("i18n_admin.spawn_enemy_battle", enemy=enemy_name, count=count, hp=hp)
            else:
                _start_custom_battle(battle_engine, run, created)
                msg = get_locale_text("i18n_admin.spawn_enemy_started", enemy=enemy_name, count=count, hp=hp)
            ctx.save_manager.save_save(ctx.target_user_id, run)
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )

    async def _spawn_merc(self, ctx: AdminContext, args: list[str]) -> str:
        if not args or args[0].lower() in ("list", "ls", "查看"):
            items = [f"{cfg['name']}({mid})" for mid, cfg in MERCENARY_CONFIG.items()]
            return get_locale_text("i18n_admin.merc_list", items=", ".join(items))

        sub = args[0].lower()
        if sub in ("dismiss", "del", "remove", "rm", "解雇"):
            query = args[1] if len(args) >= 2 else "all"
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                removed = _dismiss_mercenary(run, query)
                if not removed:
                    return get_locale_text("i18n_admin.err_merc_not_in_party", merc=query)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                msg = get_locale_text("i18n_admin.merc_dismissed", items=", ".join(removed))
                return get_locale_text(
                    "i18n_cli_core.admin_action_result",
                    msg=msg,
                    rendered=GameRenderer.render_game(run),
                )

        if sub in ("hire", "unhire"):
            if len(args) < 2:
                return get_locale_text("i18n_admin.detail_spawn")
            mid = resolve_mercenary(args[1])
            if not mid:
                return get_locale_text("i18n_admin.err_merc_not_found", merc=args[1])
            async with ctx.lock():
                stats = ctx.save_manager.load_stats(ctx.target_user_id)
                hired = list(stats.hired_mercenaries or [])
                mname = MERCENARY_CONFIG[mid]["name"]
                if sub == "hire":
                    if mid not in hired:
                        hired.append(mid)
                    stats.hired_mercenaries = hired
                    ctx.save_manager.save_stats(ctx.target_user_id, stats)
                    return get_locale_text("i18n_admin.merc_hired", name=mname, mid=mid)
                if mid in hired:
                    hired.remove(mid)
                stats.hired_mercenaries = hired
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
                return get_locale_text("i18n_admin.merc_unhired", name=mname, mid=mid)

        mid = resolve_mercenary(args[0])
        if not mid:
            return get_locale_text("i18n_admin.err_merc_not_found", merc=args[0])
        count = 1
        if len(args) >= 2 and args[1].isdigit():
            count = max(1, min(4, int(args[1])))
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            slots = []
            mname = MERCENARY_CONFIG[mid]["name"]
            for _ in range(count):
                _, slot, mname = _attach_mercenary(run, ctx.target_user_id, mid, ctx.engine.battle_engine)
                slots.append(f"a{slot}")
            ctx.save_manager.save_save(ctx.target_user_id, run)
            msg = get_locale_text("i18n_admin.spawn_merc_ok", name=mname, mid=mid, slots=", ".join(slots))
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )

    async def _spawn_minion(self, ctx: AdminContext, args: list[str]) -> str:
        if not args:
            return get_locale_text("i18n_admin.detail_spawn")
        mid = resolve_minion(args[0])
        if not mid:
            return get_locale_text("i18n_admin.err_minion_not_found", minion=args[0])
        cfg = MINION_CONFIG[mid]
        hp = int(cfg.get("hp", 12) or 12)
        atk = int(cfg.get("atk", cfg.get("reset_atk", 4)) or 4)
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            if run.node_type != "battle":
                return get_locale_text("i18n_admin.err_not_in_battle")
            slot = args[1] if len(args) >= 2 and args[1] in ("1", "2", "3", "4", "5", "6") else None
            if slot is None:
                slot = ctx.engine.battle_engine.combat_resolver.get_free_grid(run.player)
            if slot is None:
                return get_locale_text("i18n_admin.err_no_minion_slot")
            minion = MinionState(
                id=mid,
                name=cfg.get("name", mid),
                hp=hp,
                max_hp=hp,
                atk=atk,
                actions=int(cfg.get("actions", 2) or 2),
                bonus_actions=int(cfg.get("bonus_actions", 1) or 1),
                attack_actions=int(cfg.get("attack_actions", 1) or 1),
            )
            run.player.minions[slot] = minion
            ctx.save_manager.save_save(ctx.target_user_id, run)
            msg = get_locale_text("i18n_admin.spawn_minion_ok", name=minion.name, mid=mid, slot=slot)
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )


@register_admin_command(
    aliases=("battle", "bt", "战斗"),
    category="battle",
    help_key="i18n_admin.help_cmd_battle",
    detail_key="i18n_admin.detail_battle",
)
class BattleAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args:
            return get_locale_text("i18n_admin.detail_battle")
        sub = args[0].lower()

        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            if run.node_type != "battle":
                return get_locale_text("i18n_admin.err_not_in_battle")

            be = ctx.engine.battle_engine
            if sub in ("win", "胜利"):
                for e in run.enemies:
                    e.hp = 0
                    e.shield = 0
                be.card_player.handle_battle_win(run)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                msg = get_locale_text("i18n_admin.battle_won")
                return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))

            if sub in ("kill", "击杀"):
                target_tok = args[1] if len(args) >= 2 else "all_e"
                if target_tok.lower() == "all":
                    target_tok = "all_e"
                entities = resolve_battle_entities(run, target_tok)
                if not entities:
                    return get_locale_text("i18n_admin.err_target_not_found", target=target_tok)
                labels = []
                for label, ent in entities:
                    ent.hp = 0
                    ent.shield = 0
                    labels.append(label)
                if be.is_battle_won(run):
                    be.card_player.handle_battle_win(run)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                msg = get_locale_text("i18n_admin.battle_killed", targets=", ".join(labels))
                return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))

            if sub == "hp":
                if len(args) < 3:
                    return get_locale_text("i18n_admin.detail_battle")
                entities = resolve_battle_entities(run, args[1])
                if not entities:
                    return get_locale_text("i18n_admin.err_target_not_found", target=args[1])
                try:
                    hp_val = max(0, int(args[2]))
                except ValueError:
                    return get_locale_text("i18n_admin.err_int_required", value=args[2])
                labels = []
                for label, ent in entities:
                    ent.hp = hp_val
                    if hp_val > ent.max_hp:
                        ent.max_hp = hp_val
                    labels.append(label)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                msg = get_locale_text("i18n_admin.battle_hp_set", targets=", ".join(labels), hp=hp_val)
                return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))

            if sub in ("draw", "抽牌"):
                count = 1
                if len(args) >= 2:
                    try:
                        count = max(1, min(20, int(args[1])))
                    except ValueError:
                        return get_locale_text("i18n_admin.err_int_required", value=args[1])
                be._draw_cards(run.player, count, run, ignore_focus=True)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                msg = get_locale_text("i18n_admin.battle_drawn", count=count)
                return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))

            if sub in ("energy", "ap", "能量"):
                try:
                    if len(args) >= 2:
                        run.player.actions = max(0, int(args[1]))
                    if len(args) >= 3:
                        run.player.bonus_actions = max(0, int(args[2]))
                    if len(args) >= 4:
                        run.player.lex_kela = max(0, int(args[3]))
                except ValueError as exc:
                    return get_locale_text("i18n_admin.err_int_required", value=str(exc))
                ctx.save_manager.save_save(ctx.target_user_id, run)
                msg = get_locale_text(
                    "i18n_admin.battle_energy_set",
                    a=run.player.actions,
                    ba=run.player.bonus_actions,
                    lex=run.player.lex_kela,
                )
                return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))

            if sub in ("reroll", "意图"):
                be._roll_enemy_intent(run)
                assign_enemy_targets(run, be)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                msg = get_locale_text("i18n_admin.battle_rerolled")
                return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))

            return get_locale_text("i18n_admin.detail_battle")
