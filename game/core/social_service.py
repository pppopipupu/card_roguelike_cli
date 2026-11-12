from datetime import datetime

from ..data.account_config import RENAME_COST_GP
from ..data.checkin_data import (
    DEFAULT_CLASS_NAME,
    DEFAULT_PLAYER_NAME,
    FRIEND_SEARCH_LIMIT,
    IM_ACCOUNT_MAX_LENGTH,
    PLAYER_NAME_MAX_LENGTH,
)
from ..data.locale_data import get_locale_text
from .player_names import PlayerNameError, parse_player_name, unique_handle
from .social_team import SocialTeamMixin


class SocialService(SocialTeamMixin):
    def __init__(self, save_manager, engine=None):
        self.save_manager = save_manager
        self.engine = engine

    def _now(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    def _stats(self, uid):
        return self.save_manager.load_stats(uid)

    def _profile(self, uid):
        stats = self._stats(uid)
        handle = getattr(stats, "player_handle", "") or getattr(
            stats, "player_name", DEFAULT_PLAYER_NAME
        )
        return {
            "user_id": uid,
            "player_id": handle,
            "name": getattr(stats, "player_name", DEFAULT_PLAYER_NAME),
            "im_account": getattr(stats, "im_account", ""),
            "selected_class": getattr(stats, "selected_class", DEFAULT_CLASS_NAME),
            "selected_subclass": getattr(stats, "selected_subclass", ""),
        }

    def _class_text(self, stats):
        base = getattr(stats, "selected_class", DEFAULT_CLASS_NAME)
        sub = getattr(stats, "selected_subclass", "")
        separator = get_locale_text("i18n_social.common.class_separator")
        return f"{base}{separator}{sub}" if sub else base

    def _profile_class_text(self, profile):
        base = profile.get("selected_class", DEFAULT_CLASS_NAME)
        sub = profile.get("selected_subclass", "")
        separator = get_locale_text("i18n_social.common.class_separator")
        return f"{base}{separator}{sub}" if sub else base

    def _all_profiles(self):
        profiles = sorted(
            self.save_manager.list_player_profiles(),
            key=lambda item: (item.get("mtime", 0), item.get("user_id", "")),
        )
        taken = set()
        for profile in profiles:
            base = profile.get("player_handle") or profile.get("name") or DEFAULT_PLAYER_NAME
            handle = unique_handle(str(base), taken)
            taken.add(handle)
            profile["player_id"] = handle
        return sorted(profiles, key=lambda item: item.get("name", ""))

    def _find_profile(self, query):
        text = str(query or "").strip()
        if not text:
            return None
        profiles = self._all_profiles()
        for profile in profiles:
            if profile.get("player_id") == text:
                return profile
        for profile in profiles:
            if profile.get("im_account") and profile.get("im_account") == text:
                return profile
        for profile in profiles:
            if profile.get("name") == text:
                return profile
        lowered = text.lower()
        for profile in profiles:
            haystack = f"{profile.get('name', '')} {profile.get('player_id', '')} {profile.get('im_account', '')}".lower()
            if lowered in haystack:
                return profile
        return None

    def _online_text(self, uid):
        stats = self._stats(uid)
        if getattr(stats, "active_coop_id", ""):
            return get_locale_text("i18n_social.online.coop")
        if self.save_manager.has_personal_save(uid):
            return get_locale_text("i18n_social.online.solo")
        if getattr(stats, "in_town", False):
            return get_locale_text("i18n_social.online.town")
        return get_locale_text("i18n_social.online.idle")

    def friend_id(self, uid):
        stats = self._stats(uid)
        profile = self._profile(uid)
        account = getattr(stats, "im_account", "")
        account_text = (
            get_locale_text("i18n_social.friend_id.account_bound", account=account)
            if account
            else get_locale_text("i18n_social.friend_id.no_account")
        )
        return get_locale_text(
            "i18n_social.friend_id.text",
            player_id=profile["player_id"],
            name=getattr(stats, "player_name", DEFAULT_PLAYER_NAME),
            account_text=account_text,
        )

    def friend_name(self, uid, name):
        try:
            base = parse_player_name(name)
        except PlayerNameError as exc:
            if exc.reason == "empty":
                return get_locale_text(
                    "i18n_social.friend_name.need_arg", cost=RENAME_COST_GP
                )
            if exc.reason == "too_long":
                return get_locale_text(
                    "i18n_social.friend_name.too_long", limit=PLAYER_NAME_MAX_LENGTH
                )
            return get_locale_text("i18n_social.friend_name.invalid_char")
        stats = self._stats(uid)
        if base == (stats.player_handle or stats.player_name):
            return get_locale_text("i18n_social.friend_name.same", name=base)
        if stats.gp < RENAME_COST_GP:
            return get_locale_text(
                "i18n_social.friend_name.insufficient_gp",
                cost=RENAME_COST_GP,
                gp=stats.gp,
            )
        taken = {
            profile["player_id"]
            for profile in self._all_profiles()
            if profile.get("user_id") != uid
        }
        if base in taken:
            return get_locale_text("i18n_social.friend_name.taken", name=base)
        handle = base
        stats.gp -= RENAME_COST_GP
        stats.player_name = handle
        stats.player_handle = handle
        stats.name_customized = True
        self.save_manager.save_stats(uid, stats)
        run = self.save_manager.load_save(uid)
        if run is not None and run.player is not None:
            run.player.name = handle
            if uid in getattr(run, "players", {}):
                run.players[uid].name = handle
            self.save_manager.save_save(uid, run)
        return get_locale_text(
            "i18n_social.friend_name.success",
            name=handle,
            cost=RENAME_COST_GP,
            gp=stats.gp,
        )

    def friend_bind(self, uid, account):
        text = str(account or "").strip()
        if not text:
            return get_locale_text("i18n_social.friend_bind.need_arg")
        if len(text) > IM_ACCOUNT_MAX_LENGTH:
            return get_locale_text("i18n_social.friend_bind.too_long", limit=IM_ACCOUNT_MAX_LENGTH)
        for profile in self._all_profiles():
            if profile.get("user_id") == uid:
                continue
            if profile.get("im_account") == text:
                return get_locale_text("i18n_social.friend_bind.already_bound")
        stats = self._stats(uid)
        stats.im_account = text
        self.save_manager.save_stats(uid, stats)
        return get_locale_text("i18n_social.friend_bind.success", account=text)

    def friend_search(self, uid, keyword):
        text = str(keyword or "").strip()
        if not text:
            return get_locale_text("i18n_social.friend_search.need_arg")
        lowered = text.lower()
        matches = []
        for profile in self._all_profiles():
            if profile.get("user_id") == uid:
                continue
            haystack = f"{profile.get('name', '')} {profile.get('player_id', '')} {profile.get('im_account', '')}".lower()
            if lowered in haystack:
                matches.append(profile)
        if not matches:
            return get_locale_text("i18n_social.friend_search.no_match", keyword=text)
        lines = [get_locale_text("i18n_social.friend_search.header", count=len(matches))]
        for profile in matches[:FRIEND_SEARCH_LIMIT]:
            class_text = self._profile_class_text(profile)
            account = (
                get_locale_text("i18n_social.friend_search.account_suffix", account=profile.get("im_account"))
                if profile.get("im_account")
                else ""
            )
            lines.append(
                get_locale_text(
                    "i18n_social.friend_search.entry",
                    name=profile.get("name"),
                    class_text=class_text,
                    account=account,
                )
            )
            lines.append(get_locale_text("i18n_social.friend_search.id_line", player_id=profile.get("player_id")))
        lines.append(get_locale_text("i18n_social.friend_search.hint"))
        return "\n".join(lines)

    def friend_add(self, uid, query):
        target = self._find_profile(query)
        if not target:
            return get_locale_text("i18n_social.friend_add.not_found", query=query)
        target_uid = target.get("user_id")
        if target_uid == uid:
            return get_locale_text("i18n_social.friend_add.self")
        my_stats = self._stats(uid)
        target_stats = self._stats(target_uid)
        if target_uid in my_stats.friends:
            return get_locale_text("i18n_social.friend_add.already_friend", name=target.get("name"))
        if uid in target_stats.friend_requests_out and target_uid not in my_stats.friends:
            my_stats.friends.append(target_uid)
            target_stats.friends.append(uid)
            target_stats.friend_requests_out = [item for item in target_stats.friend_requests_out if item != uid]
            my_stats.friend_requests_in = [
                item for item in my_stats.friend_requests_in
                if str(item.get("uid") if isinstance(item, dict) else item) != target_uid
            ]
            my_stats.friend_requests_out = [item for item in my_stats.friend_requests_out if item != target_uid]
            self.save_manager.save_stats(uid, my_stats)
            self.save_manager.save_stats(target_uid, target_stats)
            return get_locale_text("i18n_social.friend_add.mutual", name=target.get("name"))
        if target_uid not in my_stats.friend_requests_out:
            my_stats.friend_requests_out.append(target_uid)
        incoming = [
            item for item in target_stats.friend_requests_in
            if str(item.get("uid") if isinstance(item, dict) else item) == uid
        ]
        if not incoming:
            target_stats.friend_requests_in.append({
                "uid": uid,
                "name": getattr(my_stats, "player_name", DEFAULT_PLAYER_NAME),
                "time": self._now(),
            })
        self.save_manager.save_stats(uid, my_stats)
        self.save_manager.save_stats(target_uid, target_stats)
        return get_locale_text("i18n_social.friend_add.sent", name=target.get("name"))

    def friend_accept(self, uid, query):
        target = self._find_profile(query)
        if not target:
            return get_locale_text("i18n_social.common.player_not_found", query=query)
        target_uid = target.get("user_id")
        my_stats = self._stats(uid)
        incoming = []
        for item in my_stats.friend_requests_in:
            item_uid = item.get("uid") if isinstance(item, dict) else str(item)
            if item_uid == target_uid:
                incoming.append(item)
        if not incoming:
            return get_locale_text("i18n_social.common.no_request", name=target.get("name"))
        target_stats = self._stats(target_uid)
        if target_uid not in my_stats.friends:
            my_stats.friends.append(target_uid)
        if uid not in target_stats.friends:
            target_stats.friends.append(uid)
        my_stats.friend_requests_in = [
            item for item in my_stats.friend_requests_in
            if str(item.get("uid") if isinstance(item, dict) else item) != target_uid
        ]
        target_stats.friend_requests_out = [item for item in target_stats.friend_requests_out if item != uid]
        self.save_manager.save_stats(uid, my_stats)
        self.save_manager.save_stats(target_uid, target_stats)
        return get_locale_text("i18n_social.friend_accept.success", name=target.get("name"))

    def friend_reject(self, uid, query):
        target = self._find_profile(query)
        if not target:
            return get_locale_text("i18n_social.common.player_not_found", query=query)
        target_uid = target.get("user_id")
        my_stats = self._stats(uid)
        before = len(my_stats.friend_requests_in)
        my_stats.friend_requests_in = [
            item for item in my_stats.friend_requests_in
            if str(item.get("uid") if isinstance(item, dict) else item) != target_uid
        ]
        target_stats = self._stats(target_uid)
        target_stats.friend_requests_out = [item for item in target_stats.friend_requests_out if item != uid]
        self.save_manager.save_stats(uid, my_stats)
        self.save_manager.save_stats(target_uid, target_stats)
        if len(my_stats.friend_requests_in) == before:
            return get_locale_text("i18n_social.common.no_request", name=target.get("name"))
        return get_locale_text("i18n_social.friend_reject.success", name=target.get("name"))

    def friend_remove(self, uid, query):
        target = self._find_profile(query)
        if not target:
            return get_locale_text("i18n_social.common.player_not_found", query=query)
        target_uid = target.get("user_id")
        my_stats = self._stats(uid)
        if target_uid not in my_stats.friends:
            return get_locale_text("i18n_social.friend_remove.not_friend", name=target.get("name"))
        my_stats.friends = [item for item in my_stats.friends if item != target_uid]
        target_stats = self._stats(target_uid)
        target_stats.friends = [item for item in target_stats.friends if item != uid]
        self.save_manager.save_stats(uid, my_stats)
        self.save_manager.save_stats(target_uid, target_stats)
        lobby = self._lobby_of(uid)
        if lobby and target_uid in lobby.get("invited", []):
            lobby["invited"] = [item for item in lobby["invited"] if item != target_uid]
            self.save_manager.save_lobby(lobby)
        return get_locale_text("i18n_social.friend_remove.success", name=target.get("name"))

    def friend_list(self, uid):
        stats = self._stats(uid)
        if not stats.friends:
            return get_locale_text("i18n_social.friend_list.empty")
        lines = [get_locale_text("i18n_social.friend_list.header", count=len(stats.friends))]
        for index, friend_uid in enumerate(stats.friends, 1):
            profile = self._profile(friend_uid)
            lines.append(
                get_locale_text(
                    "i18n_social.friend_list.entry",
                    index=index,
                    name=profile["name"],
                    class_text=self._class_text(self._stats(friend_uid)),
                    online=self._online_text(friend_uid),
                )
            )
            lines.append(get_locale_text("i18n_social.friend_list.id_line", player_id=profile["player_id"]))
        lines.append(get_locale_text("i18n_social.friend_list.hint"))
        return "\n".join(lines)

    def friend_requests(self, uid):
        stats = self._stats(uid)
        lines = [get_locale_text("i18n_social.friend_requests.header")]
        if stats.friend_requests_in:
            lines.append(get_locale_text("i18n_social.friend_requests.received"))
            for index, item in enumerate(stats.friend_requests_in, 1):
                item_uid = item.get("uid") if isinstance(item, dict) else str(item)
                profile = self._profile(item_uid)
                lines.append(
                    get_locale_text(
                        "i18n_social.friend_requests.incoming_entry",
                        index=index,
                        name=profile["name"],
                        player_id=profile["player_id"],
                    )
                )
            lines.append(get_locale_text("i18n_social.friend_requests.actions"))
        else:
            lines.append(get_locale_text("i18n_social.friend_requests.received_none"))
        if stats.friend_requests_out:
            lines.append(get_locale_text("i18n_social.friend_requests.sent"))
            for item in stats.friend_requests_out:
                profile = self._profile(item)
                lines.append(
                    get_locale_text(
                        "i18n_social.friend_requests.outgoing_entry",
                        name=profile["name"],
                        player_id=profile["player_id"],
                    )
                )
        else:
            lines.append(get_locale_text("i18n_social.friend_requests.sent_none"))
        return "\n".join(lines)
