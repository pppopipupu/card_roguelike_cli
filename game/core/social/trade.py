import re
from typing import Optional

from ...data.progression.trade_config import (
    TRADE_KIND_RELIC,
    TRADE_MAX_ENTRIES_PER_SIDE,
    TRADE_MAX_OUTGOING,
    TRADE_SWAP_WORDS,
)
from ..text.events import LocaleText
from ..text.pipeline import render_text_node
from .player_inspect import PlayerInspectService
from .trade_items import (
    Pair,
    Spot,
    build_plan,
    entry_name,
    resolve_entry,
    split_specs,
)
from .trade_render import (
    assets_node,
    entries_text,
    join,
    list_node,
    popup_node,
    t as _t,
)


class TradeService:
    def __init__(self, save_manager, world_social):
        self.save_manager = save_manager
        self.world_social = world_social

    def _spot(self, uid: str) -> Spot:
        stats = self.save_manager.load_stats(uid)
        run = self.save_manager.load_save(uid)
        if run is not None:
            if run.node_type == "battle":
                return Spot("battle", run=run, stats=stats)
            if getattr(run, "coop_id", "") and uid in getattr(run, "players", {}):
                return Spot("coop", run=run, stats=stats)
            return Spot("solo", run=run, stats=stats)
        return Spot("town", stats=stats)

    def _pair(self, uid: str, target_uid: str) -> tuple[Optional[Pair], Optional[LocaleText]]:
        actor = self._spot(uid)
        if actor.kind == "battle":
            return None, _t("i18n_trade.err_battle")
        target = self._spot(target_uid)
        if target.kind == "battle":
            return None, _t("i18n_trade.err_target_battle")
        if actor.kind == "coop" and target.kind == "coop":
            assert actor.run is not None
            assert target.run is not None
            if actor.run.coop_id != target.run.coop_id:
                return None, _t("i18n_trade.err_not_same_party")
            run = actor.run
            if uid not in run.players or target_uid not in run.players:
                return None, _t("i18n_trade.err_not_same_party")
            if getattr(run.players[uid], "is_mercenary", False) or getattr(run.players[target_uid], "is_mercenary", False):
                return None, _t("i18n_trade.err_not_same_party")
            return Pair(self.save_manager, "coop", run=run), None
        if actor.kind == "town" and target.kind == "town":
            assert actor.stats is not None
            assert target.stats is not None
            return Pair(
                self.save_manager,
                "town",
                stats={uid: actor.stats, target_uid: target.stats},
            ), None
        return None, _t("i18n_trade.err_not_same_party")

    def _same_place(self, uid: str, target_uid: str) -> bool:
        actor_loc = self.world_social.presence.resolve_location(uid)
        target_loc = self.world_social.presence.resolve_location(target_uid)
        return actor_loc is not None and actor_loc == target_loc

    def _player_name(self, uid: str) -> str:
        stats = self.save_manager.load_stats(uid)
        return getattr(stats, "player_name", "") or uid

    def _split_target(self, uid: str, text: str):
        location = self.world_social.presence.resolve_location(uid)
        if location is None:
            return None, "", _t("i18n_trade.err_no_world")
        target, rest = self.world_social.resolve_target(location[0], location[1], text, exclude_uid=uid)
        if target is None:
            return None, "", _t("i18n_trade.err_target_not_here", query=text.split()[0] if text.strip() else "")
        return target, rest.strip(), None

    def _error(self, error: tuple) -> LocaleText:
        key, params = error
        return _t(key, **params)

    def _outgoing_limit_reached(self, uid: str, target_uid: str) -> bool:
        outgoing = [
            offer
            for offer in self.save_manager.trades.outgoing(uid)
            if str(offer.get("to_uid", "")) != str(target_uid)
        ]
        return len(outgoing) >= TRADE_MAX_OUTGOING

    def _create_offer(self, uid: str, target: dict, give: list, want: list, mode: str):
        target_uid = str(target.get("user_id", ""))
        target_name = str(target.get("name") or self._player_name(target_uid))
        if self._outgoing_limit_reached(uid, target_uid):
            return False, _t("i18n_trade.err_too_many_offers", max=TRADE_MAX_OUTGOING)
        location = self.world_social.presence.resolve_location(uid)
        world, coord = location if location is not None else ("", "")
        self.save_manager.trades.remove_pair(uid, target_uid)
        self.save_manager.trades.create({
            "from_uid": uid,
            "from_name": self._player_name(uid),
            "to_uid": target_uid,
            "to_name": target_name,
            "mode": mode,
            "give": give,
            "want": want,
            "world": world,
            "coord": coord,
        })
        if want:
            return True, _t(
                "i18n_trade.offer_created",
                name=target_name,
                give=entries_text(give),
                want=entries_text(want),
            )
        return True, _t("i18n_trade.gift_created", name=target_name, items=entries_text(give))

    def _push(self, uid: str, node: LocaleText, command: str, player_name: str) -> None:
        self.world_social.push_log(
            uid,
            render_text_node(node),
            command=command,
            player_name=player_name,
        )

    def _notify_offer(self, uid: str, target_uid: str, give: list, want: list) -> None:
        from_name = self._player_name(uid)
        if want:
            node = _t(
                "i18n_trade.notify_offer",
                name=from_name,
                give=entries_text(give),
                want=entries_text(want),
            )
        else:
            node = _t("i18n_trade.notify_gift", name=from_name, items=entries_text(give))
        self._push(target_uid, node, "trade_offer", from_name)

    def _reject_duplicate_relics(self, entries: list) -> Optional[LocaleText]:
        seen = set()
        for entry in entries:
            if entry.get("kind") != TRADE_KIND_RELIC:
                continue
            relic_id = str(entry.get("relic_id", ""))
            if relic_id in seen:
                return _t("i18n_trade.err_duplicate_entry", name=entry_name(entry))
            seen.add(relic_id)
        return None

    def create_gift(self, uid: str, text: str):
        target, spec_text, error = self._split_target(uid, text)
        if error is not None:
            return error
        assert target is not None
        if not spec_text:
            return _t("i18n_trade.err_need_spec")
        specs = split_specs(spec_text)
        if len(specs) > TRADE_MAX_ENTRIES_PER_SIDE:
            return _t("i18n_trade.err_too_many", max=TRADE_MAX_ENTRIES_PER_SIDE)
        target_uid = str(target.get("user_id", ""))
        if target_uid == uid:
            return _t("i18n_trade.err_self")
        if not self._same_place(uid, target_uid):
            return _t("i18n_trade.err_target_not_here", query=target.get("name", ""))
        pair, error = self._pair(uid, target_uid)
        if error is not None:
            return error
        assert pair is not None
        give = []
        for spec in specs:
            entry, entry_error = resolve_entry(pair, uid, spec, self._player_name(uid), True)
            if entry_error is not None:
                return self._error(entry_error)
            assert entry is not None
            give.append(entry)
        duplicate = self._reject_duplicate_relics(give)
        if duplicate is not None:
            return duplicate
        _plan, plan_error = build_plan(pair, uid, target_uid, give, [], self._player_name)
        if plan_error is not None:
            return self._error(plan_error)
        created, result = self._create_offer(uid, target, give, [], "gift")
        if created:
            self._notify_offer(uid, target_uid, give, [])
        return result

    def create_exchange(self, uid: str, text: str):
        target, rest, error = self._split_target(uid, text)
        if error is not None:
            return error
        assert target is not None
        marker = "|".join(re.escape(word) for word in sorted(TRADE_SWAP_WORDS, key=len, reverse=True))
        match = re.search(rf"\s+(?:{marker})\s+", rest, flags=re.IGNORECASE)
        if match is None:
            return _t("i18n_trade.err_need_want")
        give_text = rest[:match.start()].strip()
        want_text = rest[match.end():].strip()
        if not give_text or not want_text:
            return _t("i18n_trade.err_need_want")
        give_specs = split_specs(give_text)
        want_specs = split_specs(want_text)
        if len(give_specs) > TRADE_MAX_ENTRIES_PER_SIDE or len(want_specs) > TRADE_MAX_ENTRIES_PER_SIDE:
            return _t("i18n_trade.err_too_many", max=TRADE_MAX_ENTRIES_PER_SIDE)
        target_uid = str(target.get("user_id", ""))
        if target_uid == uid:
            return _t("i18n_trade.err_self")
        if not self._same_place(uid, target_uid):
            return _t("i18n_trade.err_target_not_here", query=target.get("name", ""))
        pair, error = self._pair(uid, target_uid)
        if error is not None:
            return error
        assert pair is not None
        target_name = str(target.get("name") or self._player_name(target_uid))
        give = []
        for spec in give_specs:
            entry, entry_error = resolve_entry(pair, uid, spec, self._player_name(uid), True)
            if entry_error is not None:
                return self._error(entry_error)
            assert entry is not None
            give.append(entry)
        want = []
        for spec in want_specs:
            entry, entry_error = resolve_entry(pair, target_uid, spec, target_name, False)
            if entry_error is not None:
                return self._error(entry_error)
            assert entry is not None
            want.append(entry)
        for entries in (give, want):
            duplicate = self._reject_duplicate_relics(entries)
            if duplicate is not None:
                return duplicate
        _plan, plan_error = build_plan(pair, uid, target_uid, give, want, self._player_name)
        if plan_error is not None:
            return self._error(plan_error)
        created, result = self._create_offer(uid, target, give, want, "trade")
        if created:
            self._notify_offer(uid, target_uid, give, want)
        return result

    def _pick_offer(self, offers: list, query: str) -> Optional[dict]:
        text = str(query or "").strip()
        if not text:
            return offers[0] if offers else None
        for offer in offers:
            offer_id = str(offer.get("id", ""))
            if text == offer_id or (len(text) >= 6 and offer_id.endswith(text)):
                return offer
        lowered = text.lower()
        for offer in offers:
            if str(offer.get("from_name", "")).lower() == lowered:
                return offer
        for offer in offers:
            if lowered in str(offer.get("from_name", "")).lower():
                return offer
        return None

    def _pop_stale(self, offer: dict, actor_uid: str, reason: LocaleText) -> None:
        self.save_manager.trades.pop(str(offer.get("id", "")))
        from_uid = str(offer.get("from_uid", ""))
        actor_name = self._player_name(actor_uid)
        self._push(
            from_uid,
            _t("i18n_trade.invalid_notify", name=actor_name, reason=reason),
            "trade_invalid",
            actor_name,
        )

    def _apply_plan(self, pair: Pair, plan: dict, actor_uid: str) -> None:
        for uid, chunk in plan["work"].items():
            pair.set_deck(uid, chunk["deck"])
            pair.set_bag(uid, chunk["bag"])
        for uid, relic_ids in plan["removed_relics"].items():
            for relic_id in relic_ids:
                pair.remove_relic(uid, relic_id)
        for uid, entries in plan["added_relics"].items():
            for relic_id, counter in entries:
                pair.add_relic(uid, relic_id, counter)
        pair.save(actor_uid)

    def accept(self, uid: str, query: str = ""):
        offers = self.save_manager.trades.incoming(uid)
        offer = self._pick_offer(offers, query)
        if offer is None:
            return _t("i18n_trade.err_offer_not_found")
        from_uid = str(offer.get("from_uid", ""))
        from_name = str(offer.get("from_name") or self._player_name(from_uid))
        pair, error = self._pair(uid, from_uid)
        if error is not None:
            return error
        assert pair is not None
        if not self._same_place(uid, from_uid):
            self._pop_stale(offer, uid, _t("i18n_trade.err_not_same_place"))
            return _t("i18n_trade.err_not_same_place")
        give = list(offer.get("give") or [])
        want = list(offer.get("want") or [])
        plan, plan_error = build_plan(pair, from_uid, uid, give, want, self._player_name)
        if plan_error is not None:
            rendered = self._error(plan_error)
            self._pop_stale(offer, uid, rendered)
            return rendered
        assert plan is not None
        self._apply_plan(pair, plan, uid)
        self.save_manager.trades.pop(str(offer.get("id", "")))
        actor_name = self._player_name(uid)
        if want:
            self._push(
                from_uid,
                _t(
                    "i18n_trade.accepted_notify",
                    name=actor_name,
                    gain=entries_text(give),
                    give=entries_text(want),
                ),
                "trade_accept",
                actor_name,
            )
            return _t(
                "i18n_trade.accepted",
                gain=entries_text(want),
                give=entries_text(give),
            )
        self._push(
            from_uid,
            _t(
                "i18n_trade.accepted_notify_gift",
                name=actor_name,
                give=entries_text(give),
            ),
            "trade_accept",
            actor_name,
        )
        return _t("i18n_trade.accepted_gift", name=from_name, gain=entries_text(give))

    def decline(self, uid: str, query: str = ""):
        offers = self.save_manager.trades.incoming(uid)
        offer = self._pick_offer(offers, query)
        if offer is None:
            return _t("i18n_trade.err_offer_not_found")
        self.save_manager.trades.pop(str(offer.get("id", "")))
        from_uid = str(offer.get("from_uid", ""))
        from_name = str(offer.get("from_name") or self._player_name(from_uid))
        actor_name = self._player_name(uid)
        self._push(
            from_uid,
            _t("i18n_trade.declined_notify", name=actor_name),
            "trade_decline",
            actor_name,
        )
        return _t("i18n_trade.declined_self", name=from_name)

    def cancel(self, uid: str, query: str = ""):
        outgoing = self.save_manager.trades.outgoing(uid)
        text = str(query or "").strip()
        if text:
            lowered = text.lower()
            outgoing = [
                offer
                for offer in outgoing
                if str(offer.get("id", "")) == text
                or str(offer.get("to_name", "")).lower() == lowered
                or lowered in str(offer.get("to_name", "")).lower()
            ]
        if not outgoing:
            return _t("i18n_trade.err_cancel_none")
        actor_name = self._player_name(uid)
        parts = []
        for offer in outgoing:
            self.save_manager.trades.pop(str(offer.get("id", "")))
            to_uid = str(offer.get("to_uid", ""))
            to_name = str(offer.get("to_name") or self._player_name(to_uid))
            self._push(
                to_uid,
                _t("i18n_trade.cancelled_notify", name=actor_name),
                "trade_cancel",
                actor_name,
            )
            parts.append(_t("i18n_trade.cancelled", name=to_name))
        return join(parts) if len(parts) > 1 else parts[0]

    def render_assets(self, uid: str, target_uid: str):
        target_name = self._player_name(target_uid)
        pair, error = self._pair(uid, target_uid)
        if error is not None:
            return error
        assert pair is not None
        return assets_node(pair, uid, target_uid, target_name)

    def render_pending_popup(self, uid: str):
        offers = self.save_manager.trades.incoming(uid)
        if not offers:
            return None
        return popup_node(offers[0], len(offers) - 1)

    def respond_popup_input(self, uid: str, parts: list, state: str = ""):
        if len(parts) != 1:
            return None
        if not self.save_manager.trades.incoming(uid):
            return None
        stats = self.save_manager.load_stats(uid)
        if self.world_social.has_dialog(uid, stats) or stats.town_flags.get("current_dialog"):
            return None
        run = self.save_manager.load_save(uid)
        if run is not None and (run.node_type == "battle" or run.node_data.get("state_stack")):
            return None
        token = str(parts[0]).strip().lower()
        if token in ("接受", "同意", "accept", "yes", "y"):
            return self.accept(uid)
        if token in ("拒绝", "不接受", "decline", "reject", "no", "n"):
            return self.decline(uid)
        if token in ("1", "2"):
            if state not in ("menu", "town", "grid_map"):
                return None
            return self.accept(uid) if token == "1" else self.decline(uid)
        return None

    def render_list(self, uid: str):
        incoming = self.save_manager.trades.incoming(uid)
        outgoing = self.save_manager.trades.outgoing(uid)
        if not incoming and not outgoing:
            return _t("i18n_trade.list_empty")
        return list_node(incoming, outgoing)

    def usage(self) -> LocaleText:
        return _t("i18n_trade.usage")

    def handle(self, uid: str, parts: list):
        args = list(parts[1:])
        if not args:
            return self.usage()
        head = str(args[0]).strip().lower()
        rest = " ".join(args[1:]).strip()
        if head in ("列表", "list", "ls", "状态", "status"):
            return self.render_list(uid)
        if head in ("接受", "同意", "accept"):
            return self.accept(uid, rest)
        if head in ("拒绝", "decline", "reject", "refuse"):
            return self.decline(uid, rest)
        if head in ("取消", "cancel"):
            return self.cancel(uid, rest)
        if head in ("帮助", "help", "用法", "?"):
            return self.usage()
        if head in ("给", "给予", "赠送", "gift", "give"):
            return self.create_gift(uid, rest)
        if head in ("交换", "换", "offer", "swap", "trade"):
            return self.create_exchange(uid, rest)
        if head in ("view", "inspect", "查看", "看"):
            return self.render_view(uid, rest)
        return self.render_assets_for_query(uid, " ".join(args).strip())

    def render_assets_for_query(self, uid: str, query: str):
        target, _rest, error = self._split_target(uid, query)
        if error is not None:
            return error
        assert target is not None
        target_uid = str(target.get("user_id", ""))
        if target_uid == uid:
            return _t("i18n_trade.err_self")
        return self.render_assets(uid, target_uid)

    def render_view(self, uid: str, text: str):
        inspect = PlayerInspectService(self.save_manager, self.world_social)
        chunks = str(text or "").split()
        part = ""
        if chunks:
            resolved = inspect.view_part(chunks[-1])
            if resolved:
                part = resolved
                chunks = chunks[:-1]
        if not chunks:
            return _t("i18n_trade.view_usage")
        target, _rest, error = self._split_target(uid, " ".join(chunks).strip())
        if error is not None:
            return error
        assert target is not None
        target_uid = str(target.get("user_id", ""))
        if target_uid == uid:
            return _t("i18n_trade.err_self")
        return inspect.inventory_node(target_uid, part)
