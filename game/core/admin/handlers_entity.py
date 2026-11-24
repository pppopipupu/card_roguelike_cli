from typing import Any

from ...cards import ALL_CARDS, resolve_card_id
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.entities.gem_data import GEM_CONFIG
from ...data.entities.relic_data import RELIC_CONFIG
from ...data.text.locale_data import get_locale_text
from ...models.state import BuffState, CardState
from ...renderer import GameRenderer
from ..inventory.bag_service import get_item_display_name
from ..inventory.enchantment_service import get_enchantment_name
from ..inventory.relic_service import grant_relic, revoke_relic, set_relic_counter
from ..world.persistent_buffs import (
    add_persistent_buff,
    remove_persistent_buff,
    set_persistent_buff,
    sync_persistent_buffs_to_battle,
)
from .registry import AdminCommandHandler, AdminContext, register_admin_command
from .resolvers import (
    parse_bool,
    resolve_battle_entities,
    resolve_buff,
    resolve_enchantment,
    resolve_gem,
    resolve_item,
    resolve_relic,
    resolve_target_user,
)

PLAYER_INT_ATTR_MAP = {
    "hp": "hp",
    "max_hp": "max_hp",
    "maxhp": "max_hp",
    "shield": "shield",
    "block": "shield",
    "gold": "gold",
    "sp": "sp",
    "max_sp": "max_sp",
    "maxsp": "max_sp",
    "actions": "actions",
    "a": "actions",
    "bonus_actions": "bonus_actions",
    "ba": "bonus_actions",
    "lex": "lex_kela",
    "lex_kela": "lex_kela",
    "stage": "stage",
    "exhaustion": "exhaustion",
    "bag_max_weight": "bag_max_weight",
    "weight": "bag_max_weight",
}

PLAYER_STR_ATTR_MAP = {
    "class": "selected_class",
    "selected_class": "selected_class",
    "subclass": "subclass",
    "name": "name",
}

PLAYER_BOOL_ATTR_MAP = {
    "downed": "downed",
}

STATS_INT_ATTR_MAP = {
    "gp": "gp",
    "total_damage": "total_damage",
    "total_kills": "total_kills",
    "total_stages": "total_stages",
    "town_health_bonus": "town_health_bonus",
    "yog_kill": "yog_sothoth_kill_count",
    "yog_sothoth_kill_count": "yog_sothoth_kill_count",
    "yog_challenge": "yog_sothoth_challenge_count",
    "yog_sothoth_challenge_count": "yog_sothoth_challenge_count",
    "open_world_hp": "open_world_hp",
    "open_world_max_hp": "open_world_max_hp",
    "open_world_sp": "open_world_sp",
    "open_world_gold": "open_world_gold",
}

STATS_BOOL_ATTR_MAP = {
    "tutorial_done": "tutorial_done",
    "in_town": "in_town",
    "rogue_mode": "rogue_mode",
    "pvp_enabled": "pvp_enabled",
    "killed_icerainboww": "killed_icerainboww",
    "unlocked_gatekey": "unlocked_gatekey",
    "achievement_all_view": "achievement_all_view",
}

STATS_STR_ATTR_MAP = {
    "town_pos": "town_pos",
    "daily_blessing": "daily_blessing",
    "stats_class": "selected_class",
    "stats_subclass": "selected_subclass",
}

CLASS_ALIASES = {
    "mage": "法师",
    "wizard": "法师",
    "法师": "法师",
    "warrior": "战士",
    "战士": "战士",
    "ninja": "蕾忍",
    "lex": "蕾忍",
    "蕾忍": "蕾忍",
    "忍者": "蕾忍",
}

PILE_MAP = {
    "deck": "deck",
    "hand": "hand",
    "draw": "draw_pile",
    "draw_pile": "draw_pile",
    "discard": "discard_pile",
    "discard_pile": "discard_pile",
    "exhaust": "exhaust_pile",
    "exhaust_pile": "exhaust_pile",
}


def _apply_int_change(current: int, raw: str, mode: str) -> int:
    text = raw.strip()
    if mode == "add":
        return current + int(text)
    if text.startswith("+") or text.startswith("-"):
        if mode == "auto":
            return current + int(text)
    return int(text)


def _set_entity_buff(entity: Any, bid: str, name: str, desc: str, stacks: int, stacks2: int | None = None) -> None:
    allow_neg = bool(BUFF_CONFIG.get(bid, {}).get("allow_negative", False))
    existing = next((b for b in entity.buffs if b.id == bid), None)
    if stacks == 0 or (stacks < 0 and not allow_neg):
        if existing is not None:
            entity.buffs.remove(existing)
        return
    if existing is not None:
        existing.stacks = stacks
        if stacks2 is not None:
            existing.stacks2 = stacks2
        return
    entity.buffs.append(BuffState(id=bid, name=name, stacks=stacks, stacks2=stacks2, desc=desc))


@register_admin_command(
    aliases=("buff", "bf", "状态"),
    category="entity",
    help_key="i18n_admin.help_cmd_buff",
    detail_key="i18n_admin.detail_buff",
)
class BuffAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = list(ctx.args)
        if not args:
            return get_locale_text("i18n_admin.detail_buff")

        persistent = False
        cleaned: list[str] = []
        for tok in args:
            if tok.lower() in ("-p", "--persistent", "persistent"):
                persistent = True
            else:
                cleaned.append(tok)
        args = cleaned
        if not args:
            return get_locale_text("i18n_admin.detail_buff")

        sub = args[0].lower()
        if sub in ("list", "ls", "查看"):
            target_tok = args[1] if len(args) >= 2 else "p0"
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                entities = resolve_battle_entities(run, target_tok)
                if not entities:
                    return get_locale_text("i18n_admin.err_target_not_found", target=target_tok)
                lines = []
                for label, ent in entities:
                    items = [f"{b.name}({b.id}):{b.stacks}" for b in getattr(ent, "buffs", [])]
                    p_items = [f"{b.name}({b.id}):{b.stacks}" for b in getattr(ent, "persistent_buffs", [])]
                    lines.append(
                        get_locale_text(
                            "i18n_admin.buff_list_row",
                            target=label,
                            buffs=", ".join(items) if items else "-",
                            persistent=", ".join(p_items) if p_items else "-",
                        )
                    )
                return "\n".join(lines)

        if sub in ("clear", "清空"):
            target_tok = args[1] if len(args) >= 2 else "p0"
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                entities = resolve_battle_entities(run, target_tok)
                if not entities:
                    return get_locale_text("i18n_admin.err_target_not_found", target=target_tok)
                labels = []
                for label, ent in entities:
                    if persistent and hasattr(ent, "persistent_buffs"):
                        ent.persistent_buffs.clear()
                    else:
                        ent.buffs.clear()
                    labels.append(label)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                return get_locale_text("i18n_admin.buff_cleared", targets=", ".join(labels))

        if sub in ("del", "remove", "rm", "移除"):
            if len(args) < 2:
                return get_locale_text("i18n_admin.detail_buff")
            resolved = resolve_buff(args[1])
            bid = resolved[0] if resolved else args[1]
            bname = resolved[1] if resolved else args[1]
            target_tok = args[2] if len(args) >= 3 else "p0"
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                entities = resolve_battle_entities(run, target_tok)
                if not entities:
                    return get_locale_text("i18n_admin.err_target_not_found", target=target_tok)
                labels = []
                for label, ent in entities:
                    if persistent and hasattr(ent, "persistent_buffs"):
                        remove_persistent_buff(ent, bid)
                    ent.buffs = [b for b in ent.buffs if b.id != bid]
                    labels.append(label)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                return get_locale_text(
                    "i18n_admin.buff_removed",
                    buff=bname,
                    bid=bid,
                    targets=", ".join(labels),
                )

        if sub in ("add", "set"):
            action = sub
            rest = args[1:]
        else:
            action = "add"
            rest = args

        if not rest:
            return get_locale_text("i18n_admin.detail_buff")

        buff_query = rest[0]
        resolved = resolve_buff(buff_query)
        if not resolved:
            return get_locale_text("i18n_admin.err_buff_not_found", buff=buff_query)
        bid, bname, bdesc = resolved

        stacks = 1
        target_tok = "p0"
        stacks2: int | None = None
        if len(rest) >= 2:
            try:
                stacks = int(rest[1])
            except ValueError:
                return get_locale_text("i18n_admin.err_int_required", value=rest[1])
        if len(rest) >= 3:
            target_tok = rest[2]
        if len(rest) >= 4:
            try:
                stacks2 = int(rest[3])
            except ValueError:
                return get_locale_text("i18n_admin.err_int_required", value=rest[3])

        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            entities = resolve_battle_entities(run, target_tok)
            if not entities:
                return get_locale_text("i18n_admin.err_target_not_found", target=target_tok)
            labels = []
            for label, ent in entities:
                if persistent and hasattr(ent, "persistent_buffs"):
                    if action == "set":
                        set_persistent_buff(ent, bid, stacks, name=bname, desc=bdesc)
                    else:
                        add_persistent_buff(ent, bid, stacks, name=bname, desc=bdesc)
                    if run.node_type == "battle":
                        sync_persistent_buffs_to_battle(ent)
                elif action == "set":
                    _set_entity_buff(ent, bid, bname, bdesc, stacks, stacks2)
                else:
                    ctx.engine.battle_engine.combat_resolver.add_buff_to(
                        ent, bid, bname, bdesc, count=stacks, count2=stacks2, run=run
                    )
                labels.append(label)
            ctx.save_manager.save_save(ctx.target_user_id, run)
            key = "i18n_admin.buff_set_ok" if action == "set" else "i18n_admin.buff_added_ok"
            msg = get_locale_text(key, buff=bname, bid=bid, stacks=stacks, targets=", ".join(labels))
            return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))


@register_admin_command(
    aliases=("stat", "attr", "prop", "属性"),
    category="entity",
    help_key="i18n_admin.help_cmd_stat",
    detail_key="i18n_admin.detail_stat",
)
class StatAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args or args[0].lower() in ("list", "ls", "show", "查看"):
            async with ctx.lock():
                stats = ctx.save_manager.load_stats(ctx.target_user_id)
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if run:
                    p = run.player
                    return get_locale_text(
                        "i18n_admin.stat_snapshot_run",
                        uid=ctx.target_user_id,
                        name=p.name,
                        cls=p.selected_class,
                        sub=p.subclass or "-",
                        hp=p.hp,
                        max_hp=p.max_hp,
                        shield=p.shield,
                        gold=p.gold,
                        sp=p.sp,
                        max_sp=p.max_sp,
                        a=p.actions,
                        ba=p.bonus_actions,
                        lex=p.lex_kela,
                        stage=p.stage,
                        exhaustion=p.exhaustion,
                        gp=stats.gp,
                        node=run.node_type,
                    )
                return get_locale_text(
                    "i18n_admin.stat_snapshot_stats",
                    uid=ctx.target_user_id,
                    name=stats.player_name,
                    cls=stats.selected_class,
                    sub=stats.selected_subclass or "-",
                    gp=stats.gp,
                    damage=stats.total_damage,
                    kills=stats.total_kills,
                    stages=stats.total_stages,
                    tutorial=stats.tutorial_done,
                    in_town=stats.in_town,
                )

        if args[0].lower() in ("set", "add", "get") and len(args) >= 2:
            mode = args[0].lower()
            field_tok = args[1].lower()
            val_tok = args[2] if len(args) >= 3 else ""
        else:
            mode = "auto"
            field_tok = args[0].lower()
            val_tok = args[1] if len(args) >= 2 else ""

        if mode == "get" or not val_tok:
            async with ctx.lock():
                stats = ctx.save_manager.load_stats(ctx.target_user_id)
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if field_tok in PLAYER_INT_ATTR_MAP or field_tok in PLAYER_STR_ATTR_MAP or field_tok in PLAYER_BOOL_ATTR_MAP:
                    if not run:
                        return get_locale_text("i18n_cli_core.err_admin_no_save")
                    attr = (
                        PLAYER_INT_ATTR_MAP.get(field_tok)
                        or PLAYER_STR_ATTR_MAP.get(field_tok)
                        or PLAYER_BOOL_ATTR_MAP.get(field_tok)
                    )
                    return get_locale_text("i18n_admin.stat_get_ok", field=attr, value=getattr(run.player, str(attr)))
                attr = (
                    STATS_INT_ATTR_MAP.get(field_tok)
                    or STATS_BOOL_ATTR_MAP.get(field_tok)
                    or STATS_STR_ATTR_MAP.get(field_tok)
                )
                if attr:
                    return get_locale_text("i18n_admin.stat_get_ok", field=attr, value=getattr(stats, attr))
                return get_locale_text("i18n_admin.err_stat_unknown", field=field_tok)

        async with ctx.lock():
            if field_tok in PLAYER_INT_ATTR_MAP or field_tok in PLAYER_STR_ATTR_MAP or field_tok in PLAYER_BOOL_ATTR_MAP:
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                p = run.player
                if field_tok in PLAYER_INT_ATTR_MAP:
                    attr = PLAYER_INT_ATTR_MAP[field_tok]
                    old_val = int(getattr(p, attr, 0) or 0)
                    try:
                        new_val = _apply_int_change(old_val, val_tok, mode)
                    except ValueError:
                        return get_locale_text("i18n_admin.err_int_required", value=val_tok)
                    if attr in ("max_hp", "max_sp", "bag_max_weight"):
                        new_val = max(1, new_val)
                    elif attr in ("hp", "shield", "gold", "sp", "actions", "bonus_actions", "lex_kela", "exhaustion"):
                        new_val = max(0, new_val)
                    setattr(p, attr, new_val)
                    if attr == "hp" and p.hp > p.max_hp:
                        p.max_hp = p.hp
                    elif attr == "max_hp" and p.hp > p.max_hp:
                        p.hp = p.max_hp
                    elif attr == "sp" and p.sp > p.max_sp:
                        p.max_sp = p.sp
                    elif attr == "max_sp" and p.sp > p.max_sp:
                        p.sp = p.max_sp
                    ctx.save_manager.save_save(ctx.target_user_id, run)
                    msg = get_locale_text("i18n_admin.stat_updated", field=attr, old=old_val, new=getattr(p, attr))
                    return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))

                if field_tok in PLAYER_BOOL_ATTR_MAP:
                    attr = PLAYER_BOOL_ATTR_MAP[field_tok]
                    parsed = parse_bool(val_tok)
                    if parsed is None:
                        return get_locale_text("i18n_admin.err_bool_required", value=val_tok)
                    old_val = bool(getattr(p, attr))
                    setattr(p, attr, parsed)
                    ctx.save_manager.save_save(ctx.target_user_id, run)
                    msg = get_locale_text("i18n_admin.stat_updated", field=attr, old=old_val, new=parsed)
                    return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))

                attr = PLAYER_STR_ATTR_MAP[field_tok]
                old_val = getattr(p, attr)
                new_str = CLASS_ALIASES.get(val_tok.lower(), val_tok) if attr == "selected_class" else val_tok
                if new_str.lower() in ("none", "clear", "null"):
                    new_str = ""
                setattr(p, attr, new_str)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                msg = get_locale_text("i18n_admin.stat_updated", field=attr, old=old_val, new=new_str)
                return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))

            stats = ctx.save_manager.load_stats(ctx.target_user_id)
            if field_tok in STATS_INT_ATTR_MAP:
                attr = STATS_INT_ATTR_MAP[field_tok]
                old_val = int(getattr(stats, attr, 0) or 0)
                try:
                    new_val = _apply_int_change(old_val, val_tok, mode)
                except ValueError:
                    return get_locale_text("i18n_admin.err_int_required", value=val_tok)
                setattr(stats, attr, new_val)
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
                return get_locale_text("i18n_admin.stat_updated", field=attr, old=old_val, new=new_val)

            if field_tok in STATS_BOOL_ATTR_MAP:
                attr = STATS_BOOL_ATTR_MAP[field_tok]
                parsed = parse_bool(val_tok)
                if parsed is None:
                    return get_locale_text("i18n_admin.err_bool_required", value=val_tok)
                old_val = bool(getattr(stats, attr))
                setattr(stats, attr, parsed)
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
                return get_locale_text("i18n_admin.stat_updated", field=attr, old=old_val, new=parsed)

            if field_tok in STATS_STR_ATTR_MAP:
                attr = STATS_STR_ATTR_MAP[field_tok]
                old_val = getattr(stats, attr)
                new_str = CLASS_ALIASES.get(val_tok.lower(), val_tok) if attr == "selected_class" else val_tok
                if new_str.lower() in ("none", "clear", "null"):
                    new_str = ""
                setattr(stats, attr, new_str)
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
                return get_locale_text("i18n_admin.stat_updated", field=attr, old=old_val, new=new_str)

            return get_locale_text("i18n_admin.err_stat_unknown", field=field_tok)


@register_admin_command(
    aliases=("heal", "full", "回满"),
    category="entity",
    help_key="i18n_admin.help_cmd_heal",
    detail_key="i18n_admin.detail_heal",
)
class HealAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            for pl in run.players.values():
                pl.hp = pl.max_hp
                pl.sp = pl.max_sp
                pl.downed = False
                pl.exhaustion = 0
            ctx.save_manager.save_save(ctx.target_user_id, run)
            msg = get_locale_text("i18n_admin.heal_ok", hp=run.player.hp, max_hp=run.player.max_hp, sp=run.player.sp)
            return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))


@register_admin_command(
    aliases=("add_card", "card", "ac", "卡牌"),
    category="entity",
    help_key="i18n_admin.help_cmd_card",
    detail_key="i18n_admin.detail_card",
)
class CardAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args:
            return get_locale_text("i18n_cli_core.err_admin_add_card_usage")

        sub = args[0].lower()
        if sub in ("del", "remove", "rm", "移除"):
            return await self._remove_card(ctx, args[1:])
        if sub in ("clear", "清空"):
            return await self._clear_pile(ctx, args[1:])
        if sub in ("upgrade", "up", "升级"):
            return await self._upgrade_card(ctx, args[1:])
        if sub in ("gem", "宝石"):
            return await self._add_gem(ctx, args[1:])
        if sub in ("enchant", "enc", "附魔"):
            return await self._add_enchant(ctx, args[1:])

        rest = args[1:] if sub == "add" else args
        if not rest:
            return get_locale_text("i18n_cli_core.err_admin_add_card_usage")

        target_uid = ctx.target_user_id
        card_input = rest[0]
        count = 1
        pile_key = ""

        if sub != "add" and len(rest) == 2 and not rest[1].isdigit() and rest[1].lower() not in PILE_MAP:
            resolved_first = resolve_card_id(rest[0])
            if resolved_first:
                target_uid = resolve_target_user(ctx.save_manager, rest[1]) or rest[1]
            else:
                resolved_second = resolve_card_id(rest[1])
                if resolved_second:
                    card_input = rest[1]
                    target_uid = resolve_target_user(ctx.save_manager, rest[0]) or rest[0]
        else:
            for extra in rest[1:]:
                low = extra.lower()
                if low in PILE_MAP:
                    pile_key = PILE_MAP[low]
                elif extra.isdigit():
                    count = max(1, min(50, int(extra)))

        upgraded = card_input.endswith("+")
        card_id = resolve_card_id(card_input)
        if not card_id:
            return get_locale_text("i18n_cli_core.err_admin_card_not_found", card_input=card_input)

        async with ctx.lock(target_uid):
            run = ctx.save_manager.load_save(target_uid)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            card_obj = ALL_CARDS.get(card_id)
            card_name = card_obj.name if card_obj else card_id
            if upgraded:
                card_name += "+"

            in_battle = run.node_type == "battle"
            for _ in range(count):
                card_state = CardState(id=card_id, upgraded=upgraded)
                if pile_key:
                    getattr(run.player, pile_key).append(card_state)
                else:
                    run.player.deck.append(card_state)
                    if in_battle:
                        run.player.hand.append(card_state)

            ctx.save_manager.save_save(target_uid, run)
            if pile_key or count > 1:
                msg = get_locale_text(
                    "i18n_admin.card_added_ext",
                    card_name=card_name,
                    count=count,
                    pile=pile_key or ("deck+hand" if in_battle else "deck"),
                    target_user_id=target_uid,
                )
            elif in_battle:
                msg = get_locale_text(
                    "i18n_cli_core.admin_card_added_battle",
                    card_name=card_name,
                    target_user_id=target_uid,
                )
            else:
                msg = get_locale_text(
                    "i18n_cli_core.admin_card_added",
                    card_name=card_name,
                    target_user_id=target_uid,
                )
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )

    async def _remove_card(self, ctx: AdminContext, args: list[str]) -> str:
        if not args:
            return get_locale_text("i18n_admin.detail_card")
        target_tok = args[0]
        pile_name = PILE_MAP.get(args[1].lower(), "deck") if len(args) >= 2 else "deck"
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            pile = getattr(run.player, pile_name)
            removed = None
            if target_tok.isdigit():
                idx = int(target_tok) - 1
                if 0 <= idx < len(pile):
                    removed = pile.pop(idx)
            else:
                cid = resolve_card_id(target_tok)
                for idx, cs in enumerate(pile):
                    if cs.id == cid or cs.id == target_tok:
                        removed = pile.pop(idx)
                        break
            if removed is None:
                return get_locale_text("i18n_cli_core.err_admin_card_not_found", card_input=target_tok)
            ctx.save_manager.save_save(ctx.target_user_id, run)
            card_obj = ALL_CARDS.get(removed.id)
            cname = (card_obj.name if card_obj else removed.id) + ("+" if removed.upgraded else "")
            return get_locale_text("i18n_admin.card_removed", card_name=cname, pile=pile_name)

    async def _clear_pile(self, ctx: AdminContext, args: list[str]) -> str:
        if not args or args[0].lower() not in PILE_MAP:
            return get_locale_text("i18n_admin.detail_card")
        pile_name = PILE_MAP[args[0].lower()]
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            pile = getattr(run.player, pile_name)
            count = len(pile)
            pile.clear()
            ctx.save_manager.save_save(ctx.target_user_id, run)
            return get_locale_text("i18n_admin.card_pile_cleared", pile=pile_name, count=count)

    async def _upgrade_card(self, ctx: AdminContext, args: list[str]) -> str:
        if not args:
            return get_locale_text("i18n_admin.detail_card")
        target_tok = args[0]
        pile_name = PILE_MAP.get(args[1].lower(), "deck") if len(args) >= 2 else "deck"
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            pile = getattr(run.player, pile_name)
            upgraded_count = 0
            if target_tok.lower() == "all":
                for cs in pile:
                    if not cs.upgraded:
                        cs.upgraded = True
                        upgraded_count += 1
            elif target_tok.isdigit():
                idx = int(target_tok) - 1
                if 0 <= idx < len(pile):
                    pile[idx].upgraded = True
                    upgraded_count = 1
            else:
                cid = resolve_card_id(target_tok)
                for cs in pile:
                    if cs.id == cid and not cs.upgraded:
                        cs.upgraded = True
                        upgraded_count = 1
                        break
            if upgraded_count == 0:
                return get_locale_text("i18n_cli_core.err_admin_card_not_found", card_input=target_tok)
            ctx.save_manager.save_save(ctx.target_user_id, run)
            return get_locale_text("i18n_admin.card_upgraded", count=upgraded_count, pile=pile_name)

    async def _add_gem(self, ctx: AdminContext, args: list[str]) -> str:
        if len(args) < 2:
            return get_locale_text("i18n_admin.detail_card")
        if not args[0].isdigit():
            return get_locale_text("i18n_admin.err_int_required", value=args[0])
        idx = int(args[0]) - 1
        gid = resolve_gem(args[1])
        if not gid:
            return get_locale_text("i18n_admin.err_gem_not_found", gem=args[1])
        pile_name = PILE_MAP.get(args[2].lower(), "deck") if len(args) >= 3 else "deck"
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            pile = getattr(run.player, pile_name)
            if not (0 <= idx < len(pile)):
                return get_locale_text("i18n_admin.err_index_out_of_range", index=args[0])
            pile[idx].gems.append(gid)
            ctx.save_manager.save_save(ctx.target_user_id, run)
            gname = GEM_CONFIG[gid]["name"]
            return get_locale_text("i18n_admin.card_gem_added", index=idx + 1, gem=gname, pile=pile_name)

    async def _add_enchant(self, ctx: AdminContext, args: list[str]) -> str:
        if len(args) < 2:
            return get_locale_text("i18n_admin.detail_card")
        if not args[0].isdigit():
            return get_locale_text("i18n_admin.err_int_required", value=args[0])
        idx = int(args[0]) - 1
        eid = resolve_enchantment(args[1])
        if not eid:
            return get_locale_text("i18n_admin.err_enchant_not_found", enchant=args[1])
        pile_name = PILE_MAP.get(args[2].lower(), "deck") if len(args) >= 3 else "deck"
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            pile = getattr(run.player, pile_name)
            if not (0 <= idx < len(pile)):
                return get_locale_text("i18n_admin.err_index_out_of_range", index=args[0])
            pile[idx].enchantments.append(eid)
            ctx.save_manager.save_save(ctx.target_user_id, run)
            return get_locale_text("i18n_admin.card_enchant_added", index=idx + 1, enchant=get_enchantment_name(eid), pile=pile_name)


@register_admin_command(
    aliases=("relic", "rl", "遗物"),
    category="entity",
    help_key="i18n_admin.help_cmd_relic",
    detail_key="i18n_admin.detail_relic",
)
class RelicAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args or args[0].lower() in ("list", "ls", "查看"):
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                items = [
                    f"{RELIC_CONFIG.get(rid, {}).get('name', rid)}({rid})"
                    for rid in run.player.relics
                ]
                return get_locale_text("i18n_admin.relic_list", items=", ".join(items) if items else "-")

        sub = args[0].lower()
        if sub in ("clear", "清空"):
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                run.player.relics.clear()
                run.player.relic_counters.clear()
                ctx.save_manager.save_save(ctx.target_user_id, run)
                return get_locale_text("i18n_admin.relic_cleared")

        if sub in ("counter", "cnt", "计数"):
            if len(args) < 3:
                return get_locale_text("i18n_admin.detail_relic")
            rid = resolve_relic(args[1])
            if not rid:
                return get_locale_text("i18n_admin.err_relic_not_found", relic=args[1])
            try:
                val = int(args[2])
            except ValueError:
                return get_locale_text("i18n_admin.err_int_required", value=args[2])
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                set_relic_counter(run.player, rid, val)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                rname = RELIC_CONFIG[rid]["name"]
                return get_locale_text("i18n_admin.relic_counter_set", relic=rname, rid=rid, value=val)

        if sub in ("del", "remove", "rm", "移除"):
            if len(args) < 2:
                return get_locale_text("i18n_admin.detail_relic")
            rid = resolve_relic(args[1]) or args[1]
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                if not revoke_relic(run.player, rid):
                    return get_locale_text("i18n_admin.err_relic_not_owned", relic=args[1])
                ctx.save_manager.save_save(ctx.target_user_id, run)
                rname = RELIC_CONFIG.get(rid, {}).get("name", rid)
                return get_locale_text("i18n_admin.relic_removed", relic=rname, rid=rid)

        query = args[1] if sub == "add" and len(args) >= 2 else args[0]
        rid = resolve_relic(query)
        if not rid:
            return get_locale_text("i18n_admin.err_relic_not_found", relic=query)
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            grant_relic(run.player, rid)
            ctx.save_manager.save_save(ctx.target_user_id, run)
            rname = RELIC_CONFIG[rid]["name"]
            return get_locale_text("i18n_admin.relic_added", relic=rname, rid=rid)


@register_admin_command(
    aliases=("item", "bag", "potion", "物品", "药水"),
    category="entity",
    help_key="i18n_admin.help_cmd_item",
    detail_key="i18n_admin.detail_item",
)
class ItemAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args or args[0].lower() in ("list", "ls", "查看"):
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                bag_names = [f"{get_item_display_name(it)}({it})" for it in run.player.bag_items]
                quest_names = list(run.player.quest_relics)
                return get_locale_text(
                    "i18n_admin.item_list",
                    bag=", ".join(bag_names) if bag_names else "-",
                    quest=", ".join(quest_names) if quest_names else "-",
                )

        sub = args[0].lower()
        if sub in ("clear", "清空"):
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                run.player.bag_items.clear()
                ctx.save_manager.save_save(ctx.target_user_id, run)
                return get_locale_text("i18n_admin.item_cleared")

        if sub in ("del", "remove", "rm", "移除"):
            if len(args) < 2:
                return get_locale_text("i18n_admin.detail_item")
            resolved = resolve_item(args[1])
            item_id = resolved[0] if resolved else args[1]
            kind = resolved[2] if resolved else "bag"
            async with ctx.lock():
                run = ctx.save_manager.load_save(ctx.target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                target_list = run.player.quest_relics if kind == "quest_relic" else run.player.bag_items
                if item_id not in target_list:
                    return get_locale_text("i18n_admin.err_item_not_owned", item=args[1])
                target_list.remove(item_id)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                name = resolved[1] if resolved else item_id
                return get_locale_text("i18n_admin.item_removed", item=name, item_id=item_id)

        rest = args[1:] if sub == "add" else args
        if not rest:
            return get_locale_text("i18n_admin.detail_item")
        resolved = resolve_item(rest[0])
        if not resolved:
            return get_locale_text("i18n_admin.err_item_not_found", item=rest[0])
        item_id, item_name, kind = resolved
        count = 1
        if len(rest) >= 2:
            try:
                count = max(1, min(50, int(rest[1])))
            except ValueError:
                return get_locale_text("i18n_admin.err_int_required", value=rest[1])

        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            if kind == "quest_relic":
                if item_id not in run.player.quest_relics:
                    run.player.quest_relics.append(item_id)
            else:
                for _ in range(count):
                    run.player.bag_items.append(item_id)
            ctx.save_manager.save_save(ctx.target_user_id, run)
            return get_locale_text("i18n_admin.item_added", item=item_name, item_id=item_id, count=count)
