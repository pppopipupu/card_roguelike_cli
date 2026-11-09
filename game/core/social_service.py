import random
import string
from datetime import datetime

from ..models.state import UserStats


class SocialService:
    def __init__(self, save_manager, engine=None):
        self.save_manager = save_manager
        self.engine = engine

    def _now(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    def _stats(self, uid):
        return self.save_manager.load_stats(uid)

    def _profile(self, uid):
        stats = self._stats(uid)
        return {
            "user_id": uid,
            "name": getattr(stats, "player_name", "玩家"),
            "im_account": getattr(stats, "im_account", ""),
            "selected_class": getattr(stats, "selected_class", "法师"),
            "selected_subclass": getattr(stats, "selected_subclass", ""),
        }

    def _class_text(self, stats):
        base = getattr(stats, "selected_class", "法师")
        sub = getattr(stats, "selected_subclass", "")
        return f"{base}·{sub}" if sub else base

    def _profile_class_text(self, profile):
        base = profile.get("selected_class", "法师")
        sub = profile.get("selected_subclass", "")
        return f"{base}·{sub}" if sub else base

    def _all_profiles(self):
        profiles = self.save_manager.list_player_profiles()
        return sorted(profiles, key=lambda item: item.get("name", ""))

    def _find_profile(self, query):
        text = str(query or "").strip()
        if not text:
            return None
        profiles = self._all_profiles()
        for profile in profiles:
            if profile.get("user_id") == text:
                return profile
        for profile in profiles:
            if profile.get("im_account") and profile.get("im_account") == text:
                return profile
        for profile in profiles:
            if profile.get("name") == text:
                return profile
        lowered = text.lower()
        for profile in profiles:
            haystack = f"{profile.get('name', '')} {profile.get('user_id', '')} {profile.get('im_account', '')}".lower()
            if lowered in haystack:
                return profile
        return None

    def _online_text(self, uid):
        stats = self._stats(uid)
        if getattr(stats, "active_coop_id", ""):
            return "联机牌局中"
        if self.save_manager.has_personal_save(uid):
            return "单人牌局中"
        if getattr(stats, "in_town", False):
            return "主城中"
        return "空闲"

    def friend_id(self, uid):
        stats = self._stats(uid)
        account = getattr(stats, "im_account", "")
        account_text = f"，绑定账号 {account}" if account else "，尚未绑定通讯账号"
        return f"🪪 你的玩家 ID：{uid}\n昵称：{getattr(stats, 'player_name', '玩家')}{account_text}"

    def friend_name(self, uid, name):
        text = str(name or "").strip()
        if not text:
            return "❌ 请提供新的昵称，例如：friend name 冒险者小明"
        if len(text) > 16:
            return "❌ 昵称最多 16 个字符。"
        if any(ch in "\n\r\t" for ch in text):
            return "❌ 昵称不能包含换行或制表符。"
        stats = self._stats(uid)
        stats.player_name = text
        self.save_manager.save_stats(uid, stats)
        return f"✅ 昵称已修改为【{text}】。"

    def friend_bind(self, uid, account):
        text = str(account or "").strip()
        if not text:
            return "❌ 请提供要绑定的通讯账号，例如：friend bind QQ123456"
        if len(text) > 40:
            return "❌ 通讯账号最多 40 个字符。"
        for profile in self._all_profiles():
            if profile.get("user_id") == uid:
                continue
            if profile.get("im_account") == text:
                return "❌ 该通讯账号已被其他玩家绑定。"
        stats = self._stats(uid)
        stats.im_account = text
        self.save_manager.save_stats(uid, stats)
        return f"✅ 已绑定通讯账号【{text}】，好友现在可以通过它搜索到你。"

    def friend_search(self, uid, keyword):
        text = str(keyword or "").strip()
        if not text:
            return "❌ 请提供搜索关键词，例如：friend search 小明"
        lowered = text.lower()
        matches = []
        for profile in self._all_profiles():
            if profile.get("user_id") == uid:
                continue
            haystack = f"{profile.get('name', '')} {profile.get('user_id', '')} {profile.get('im_account', '')}".lower()
            if lowered in haystack:
                matches.append(profile)
        if not matches:
            return f"🔍 没有找到与【{text}】匹配的玩家。"
        lines = [f"🔍 找到 {len(matches)} 名玩家："]
        for profile in matches[:10]:
            class_text = self._profile_class_text(profile)
            account = f" | 账号 {profile.get('im_account')}" if profile.get("im_account") else ""
            lines.append(f"【{profile.get('name')}】{class_text}{account}")
            lines.append(f"  ID：{profile.get('user_id')}")
        lines.append("💡 发送好友申请：friend add <玩家ID或昵称>")
        return "\n".join(lines)

    def friend_add(self, uid, query):
        target = self._find_profile(query)
        if not target:
            return f"❌ 没有找到玩家【{query}】。可先用 friend search <关键词> 搜索。"
        target_uid = target.get("user_id")
        if target_uid == uid:
            return "❌ 不能添加自己为好友。"
        my_stats = self._stats(uid)
        target_stats = self._stats(target_uid)
        if target_uid in my_stats.friends:
            return f"✅ 【{target.get('name')}】已经是你的好友。"
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
            return f"✅ 你们此前已互相申请，现已成为好友：{target.get('name')}。"
        if target_uid not in my_stats.friend_requests_out:
            my_stats.friend_requests_out.append(target_uid)
        incoming = [
            item for item in target_stats.friend_requests_in
            if str(item.get("uid") if isinstance(item, dict) else item) == uid
        ]
        if not incoming:
            target_stats.friend_requests_in.append({
                "uid": uid,
                "name": getattr(my_stats, "player_name", "玩家"),
                "time": self._now(),
            })
        self.save_manager.save_stats(uid, my_stats)
        self.save_manager.save_stats(target_uid, target_stats)
        return f"📨 已向【{target.get('name')}】发送好友申请，等待对方 accept。"

    def friend_accept(self, uid, query):
        target = self._find_profile(query)
        if not target:
            return f"❌ 没有找到玩家【{query}】。"
        target_uid = target.get("user_id")
        my_stats = self._stats(uid)
        incoming = []
        for item in my_stats.friend_requests_in:
            item_uid = item.get("uid") if isinstance(item, dict) else str(item)
            if item_uid == target_uid:
                incoming.append(item)
        if not incoming:
            return f"❌ 【{target.get('name')}】没有向你发送好友申请。"
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
        return f"✅ 已接受【{target.get('name')}】的好友申请，现在你们是好友。"

    def friend_reject(self, uid, query):
        target = self._find_profile(query)
        if not target:
            return f"❌ 没有找到玩家【{query}】。"
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
            return f"❌ 【{target.get('name')}】没有向你发送好友申请。"
        return f"✅ 已拒绝【{target.get('name')}】的好友申请。"

    def friend_remove(self, uid, query):
        target = self._find_profile(query)
        if not target:
            return f"❌ 没有找到玩家【{query}】。"
        target_uid = target.get("user_id")
        my_stats = self._stats(uid)
        if target_uid not in my_stats.friends:
            return f"❌ 【{target.get('name')}】不在你的好友列表中。"
        my_stats.friends = [item for item in my_stats.friends if item != target_uid]
        target_stats = self._stats(target_uid)
        target_stats.friends = [item for item in target_stats.friends if item != uid]
        self.save_manager.save_stats(uid, my_stats)
        self.save_manager.save_stats(target_uid, target_stats)
        lobby = self._lobby_of(uid)
        if lobby and target_uid in lobby.get("invited", []):
            lobby["invited"] = [item for item in lobby["invited"] if item != target_uid]
            self.save_manager.save_lobby(lobby)
        return f"✅ 已从好友列表中移除【{target.get('name')}】。"

    def friend_list(self, uid):
        stats = self._stats(uid)
        if not stats.friends:
            return "👥 你的好友列表为空。使用 friend search 查找玩家，再用 friend add 发送申请。"
        lines = [f"👥 好友列表（{len(stats.friends)} 人）："]
        for index, friend_uid in enumerate(stats.friends, 1):
            profile = self._profile(friend_uid)
            lines.append(f" {index}. 【{profile['name']}】{self._class_text(self._stats(friend_uid))} | {self._online_text(friend_uid)}")
            lines.append(f"    ID：{friend_uid}")
        lines.append("💡 组队邀请：friend invite <好友昵称或ID>")
        return "\n".join(lines)

    def friend_requests(self, uid):
        stats = self._stats(uid)
        lines = ["📬 好友申请："]
        if stats.friend_requests_in:
            lines.append("收到：")
            for index, item in enumerate(stats.friend_requests_in, 1):
                item_uid = item.get("uid") if isinstance(item, dict) else str(item)
                profile = self._profile(item_uid)
                lines.append(f" [{index}] 【{profile['name']}】ID：{item_uid}")
            lines.append("接受：friend accept <昵称或ID>；拒绝：friend reject <昵称或ID>")
        else:
            lines.append("收到：无")
        if stats.friend_requests_out:
            lines.append("已发送：")
            for item in stats.friend_requests_out:
                profile = self._profile(item)
                lines.append(f" - 【{profile['name']}】ID：{item}（等待对方处理）")
        else:
            lines.append("已发送：无")
        return "\n".join(lines)

    def _lobby_of(self, uid):
        stats = self._stats(uid)
        lobby_id = getattr(stats, "active_lobby_id", "")
        if not lobby_id:
            return None
        lobby = self.save_manager.get_lobby(lobby_id)
        if not lobby:
            stats.active_lobby_id = ""
            self.save_manager.save_stats(uid, stats)
            return None
        return lobby

    def _lobby_status(self, lobby):
        members = lobby.get("members", [])
        ready = lobby.get("ready", {})
        leader_id = lobby.get("leader_id", "")
        lines = [f"🏠 队伍 {lobby.get('lobby_id')}（队长：{self._profile(leader_id)['name']}）"]
        for member_uid in members:
            profile = self._profile(member_uid)
            marker = "（队长）" if member_uid == leader_id else ""
            ready_text = "✅ 已准备" if ready.get(member_uid) else "⬜ 未准备"
            lines.append(f" - {profile['name']}{marker} | {self._class_text(self._stats(member_uid))} | {ready_text}")
        invited = lobby.get("invited", [])
        if invited:
            names = "、".join(self._profile(member_uid)["name"] for member_uid in invited)
            lines.append(f"📨 待接受邀请：{names}")
        lines.append(f"👥 人数：{len(members)}/4")
        return "\n".join(lines)

    def team_create(self, uid):
        stats = self._stats(uid)
        lobby = self._lobby_of(uid)
        if lobby:
            return f"❌ 你已在队伍 {lobby.get('lobby_id')} 中。\n{self._lobby_status(lobby)}"
        if getattr(stats, "active_coop_id", ""):
            return "❌ 你正在进行联机牌局，无法创建队伍。"
        if self.save_manager.has_personal_save(uid):
            return "❌ 你有一局单人冒险尚未结束。请先输入 放弃 结束单人存档，再创建队伍。"
        lobby_id = self._new_lobby_id()
        lobby = {
            "lobby_id": lobby_id,
            "leader_id": uid,
            "members": [uid],
            "invited": [],
            "ready": {uid: True},
            "created_at": self._now(),
        }
        self.save_manager.save_lobby(lobby)
        stats.active_lobby_id = lobby_id
        self.save_manager.save_stats(uid, stats)
        return f"🏠 已创建队伍 {lobby_id}。\n{self._lobby_status(lobby)}\n邀请好友：friend invite <好友昵称或ID>"

    def _new_lobby_id(self):
        while True:
            lobby_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not self.save_manager.get_lobby(lobby_id):
                return lobby_id

    def team_invite(self, uid, query):
        lobby = self._lobby_of(uid)
        if not lobby:
            return "❌ 你还没有队伍。先输入 team create 创建队伍。"
        if lobby.get("leader_id") != uid:
            return "❌ 只有队长可以邀请好友加入队伍。"
        if getattr(self._stats(uid), "active_coop_id", ""):
            return "❌ 联机牌局进行中，无法继续邀请队员。"
        target = self._find_profile(query)
        if not target:
            return f"❌ 没有找到玩家【{query}】。"
        target_uid = target.get("user_id")
        if target_uid == uid:
            return "❌ 不能邀请自己。"
        leader_stats = self._stats(uid)
        if target_uid not in leader_stats.friends:
            return f"❌ 【{target.get('name')}】还不是你的好友。先发送 friend add。"
        if target_uid in lobby.get("members", []):
            return f"✅ 【{target.get('name')}】已经在队伍中。"
        if target_uid in lobby.get("invited", []):
            return f"📨 已经邀请过【{target.get('name')}】，等待对方 team join 接受。"
        if len(lobby.get("members", [])) + len(lobby.get("invited", [])) >= 4:
            return "❌ 队伍最多 4 人，邀请名额已满。"
        target_stats = self._stats(target_uid)
        if getattr(target_stats, "active_coop_id", ""):
            return f"❌ 【{target.get('name')}】正在联机牌局中，无法接受邀请。"
        lobby.setdefault("invited", []).append(target_uid)
        self.save_manager.save_lobby(lobby)
        return (
            f"📨 已邀请【{target.get('name')}】加入队伍 {lobby.get('lobby_id')}。\n"
            f"对方可输入 team join {lobby.get('lobby_id')} 接受邀请。"
        )

    def team_invites(self, uid):
        lobbies = self.save_manager.load_lobbies()
        lines = []
        for lobby in lobbies.values():
            if uid in lobby.get("invited", []):
                leader = self._profile(lobby.get("leader_id", ""))
                lines.append(
                    f"🏠 队伍 {lobby.get('lobby_id')}（队长：{leader['name']}，"
                    f"人数 {len(lobby.get('members', []))}/4）"
                )
        if not lines:
            return "📭 当前没有收到组队邀请。"
        return "📬 收到的组队邀请：\n" + "\n".join(lines) + "\n💡 输入 team join <队伍编号> 接受邀请。"

    def team_join(self, uid, lobby_id):
        if not lobby_id:
            lobbies = [
                lobby for lobby in self.save_manager.load_lobbies().values()
                if uid in lobby.get("invited", [])
            ]
            if len(lobbies) == 1:
                lobby_id = lobbies[0].get("lobby_id")
            else:
                return "❌ 请提供队伍编号，例如：team join A1B2C3。可输入 team invites 查看邀请。"
        lobby = self.save_manager.get_lobby(str(lobby_id).upper())
        if not lobby:
            return f"❌ 队伍【{lobby_id}】不存在。"
        if uid not in lobby.get("invited", []):
            return "❌ 你没有收到该队伍的邀请。"
        if uid in lobby.get("members", []):
            return "✅ 你已经在队伍中。"
        stats = self._stats(uid)
        if getattr(stats, "active_coop_id", ""):
            return "❌ 你正在进行联机牌局，无法加入队伍。"
        current_lobby = self._lobby_of(uid)
        if current_lobby and current_lobby.get("lobby_id") != lobby.get("lobby_id"):
            return f"❌ 你已在队伍 {current_lobby.get('lobby_id')} 中，请先 team leave。"
        if self.save_manager.has_personal_save(uid):
            return "❌ 你有一局单人冒险尚未结束。请先输入 放弃 结束单人存档，再接受邀请。"
        if len(lobby.get("members", [])) >= 4:
            return "❌ 该队伍人数已满。"
        lobby.setdefault("members", []).append(uid)
        lobby.setdefault("ready", {})[uid] = False
        lobby["invited"] = [item for item in lobby.get("invited", []) if item != uid]
        self.save_manager.save_lobby(lobby)
        stats.active_lobby_id = lobby.get("lobby_id")
        self.save_manager.save_stats(uid, stats)
        return f"✅ 已加入队伍 {lobby.get('lobby_id')}。\n{self._lobby_status(lobby)}\n准备就绪：team ready"

    def team_leave(self, uid):
        lobby = self._lobby_of(uid)
        if not lobby:
            return "❌ 你当前不在任何队伍中。"
        lobby_id = lobby.get("lobby_id")
        stats = self._stats(uid)
        if uid in lobby.get("members", []) and getattr(stats, "active_coop_id", ""):
            return "❌ 联机牌局进行中，无法离开队伍。"
        if uid not in lobby.get("members", []):
            lobby["invited"] = [item for item in lobby.get("invited", []) if item != uid]
            self.save_manager.save_lobby(lobby)
            stats = self._stats(uid)
            stats.active_lobby_id = ""
            self.save_manager.save_stats(uid, stats)
            return "✅ 已取消该队伍的邀请。"
        members = [item for item in lobby.get("members", []) if item != uid]
        lobby["ready"] = {key: value for key, value in lobby.get("ready", {}).items() if key != uid}
        stats = self._stats(uid)
        stats.active_lobby_id = ""
        self.save_manager.save_stats(uid, stats)
        if not members:
            self.save_manager.delete_lobby(lobby_id)
            return f"✅ 你已离开队伍 {lobby_id}，队伍已解散。"
        lobby["members"] = members
        if lobby.get("leader_id") == uid:
            lobby["leader_id"] = members[0]
            lobby.setdefault("ready", {})[members[0]] = True
        self.save_manager.save_lobby(lobby)
        return f"✅ 你已离开队伍 {lobby_id}。\n{self._lobby_status(lobby)}"

    def team_disband(self, uid):
        lobby = self._lobby_of(uid)
        if not lobby:
            return "❌ 你当前不在任何队伍中。"
        if lobby.get("leader_id") != uid:
            return "❌ 只有队长可以解散队伍。"
        if any(getattr(self._stats(member_uid), "active_coop_id", "") for member_uid in lobby.get("members", [])):
            return "❌ 联机牌局进行中，无法解散队伍。"
        for member_uid in lobby.get("members", []) + lobby.get("invited", []):
            stats = self._stats(member_uid)
            if getattr(stats, "active_lobby_id", "") == lobby.get("lobby_id"):
                stats.active_lobby_id = ""
                self.save_manager.save_stats(member_uid, stats)
        self.save_manager.delete_lobby(lobby.get("lobby_id"))
        return f"✅ 队伍 {lobby.get('lobby_id')} 已解散。"

    def team_kick(self, uid, query):
        lobby = self._lobby_of(uid)
        if not lobby:
            return "❌ 你当前不在任何队伍中。"
        if lobby.get("leader_id") != uid:
            return "❌ 只有队长可以移出队员。"
        target = self._find_profile(query)
        if not target:
            return f"❌ 没有找到玩家【{query}】。"
        target_uid = target.get("user_id")
        if target_uid == uid:
            return "❌ 不能移出自己。"
        if getattr(self._stats(target_uid), "active_coop_id", ""):
            return f"❌ 【{target.get('name')}】正在联机牌局中，无法移出队伍。"
        removed = False
        if target_uid in lobby.get("members", []):
            lobby["members"] = [item for item in lobby["members"] if item != target_uid]
            lobby.get("ready", {}).pop(target_uid, None)
            removed = True
        if target_uid in lobby.get("invited", []):
            lobby["invited"] = [item for item in lobby["invited"] if item != target_uid]
            removed = True
        if not removed:
            return f"❌ 【{target.get('name')}】不在你的队伍中。"
        target_stats = self._stats(target_uid)
        if getattr(target_stats, "active_lobby_id", "") == lobby.get("lobby_id"):
            target_stats.active_lobby_id = ""
            self.save_manager.save_stats(target_uid, target_stats)
        self.save_manager.save_lobby(lobby)
        return f"✅ 已将【{target.get('name')}】移出队伍。\n{self._lobby_status(lobby)}"

    def team_ready(self, uid, ready=True):
        lobby = self._lobby_of(uid)
        if not lobby:
            return "❌ 你当前不在任何队伍中。"
        if uid not in lobby.get("members", []):
            return "❌ 你不在该队伍中。"
        lobby.setdefault("ready", {})[uid] = bool(ready)
        self.save_manager.save_lobby(lobby)
        if ready:
            return f"✅ 你已准备就绪。\n{self._lobby_status(lobby)}\n队长可输入 team start 开启联机牌局。"
        return f"⬜ 你已取消准备。\n{self._lobby_status(lobby)}"

    def team_status(self, uid):
        lobby = self._lobby_of(uid)
        if lobby:
            return self._lobby_status(lobby)
        stats = self._stats(uid)
        return self.team_invites(uid) if not getattr(stats, "active_coop_id", "") else "❌ 你正在联机牌局中。"

    def team_start(self, uid):
        lobby = self._lobby_of(uid)
        if not lobby:
            return "❌ 你当前不在任何队伍中。"
        if lobby.get("leader_id") != uid:
            return "❌ 只有队长可以开启联机牌局。"
        members = list(lobby.get("members", []))
        if len(members) < 2:
            return "❌ 联机牌局至少需要 2 名玩家。邀请好友后再开始。"
        if len(members) > 4:
            return "❌ 联机牌局最多 4 名玩家。"
        ready = lobby.get("ready", {})
        not_ready = [self._profile(member_uid)["name"] for member_uid in members if not ready.get(member_uid)]
        if uid in not_ready:
            not_ready.remove(uid)
        if not_ready:
            return f"❌ 以下队员尚未准备：{'、'.join(not_ready)}。"
        stale = []
        for member_uid in members:
            stats = self._stats(member_uid)
            if getattr(stats, "active_lobby_id", "") != lobby.get("lobby_id"):
                stale.append(self._profile(member_uid)["name"])
                continue
            if getattr(stats, "active_coop_id", ""):
                return f"❌ 【{self._profile(member_uid)['name']}】正在联机牌局中。"
            if self.save_manager.has_personal_save(member_uid):
                return f"❌ 【{self._profile(member_uid)['name']}】还有单人冒险存档。请其先输入 放弃 结束单人存档。"
        if stale:
            return f"❌ 以下队员已离开队伍：{'、'.join(stale)}。"
        if not self.engine:
            return "❌ 联机引擎未初始化。"
        from .coop_engine import CoopEngine
        coop = CoopEngine(self.save_manager, self.engine)
        run = coop.start_coop(self.engine, members, uid)
        self.save_manager.delete_lobby(lobby.get("lobby_id"))
        notice = (
            f"🎉 队伍 {lobby.get('lobby_id')} 已开启联机牌局！\n"
            f"队伍成员：{'、'.join(self._profile(member_uid)['name'] for member_uid in members)}\n"
            "所有队员输入任意冒险指令即可载入共享地图。"
        )
        return notice, run
