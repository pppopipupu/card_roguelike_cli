# 魔法肉鸽卡牌游戏核心

基于 DND 5.5E 背景的文字回合制肉鸽卡牌游戏。本仓库是无头游戏核心、单接口后端和本地控制台入口;AstrBot 插件与网页前端在独立仓库中运行。

## 当前状态

- 核心与联机测试:132 项通过。
- 后端测试:26 项通过。
- 网页端默认使用游客登录，输入昵称即可游玩；即时通讯端新用户发送 `start` 以游客身份开始，或发送 `start <网页绑定码>` 关联已有网页账号。
- 游客账号以 UUID 作为鉴权文件，可在其他设备恢复；绑定 GitHub 后成为正式账号并奖励 1000 GP。公开玩家 ID 使用可读昵称，新账号重名时自动追加 `#2`、`#3` 后缀，改名重名会被拒绝。
- `rename` / `改名` / `昵称` 修改玩家名，消耗 1000 GP。
- 联机日志按玩家隔离;队友投影按操作逐条返回,私聊与网页默认开启,群聊禁用。
- `logs` 查看个人战斗与行动日志,`logc` 查看队伍日志,默认 20 条、最多 50 条;命令队列最多 50 条指令。
- `help` 按分类列出全部指令,`help <指令|别名>` 查看单条指令的用法、别名、可用场景与示例。
- 输入 `changelog` 或 `cl` 查看近期更改,内容取自仓库根目录 `CHANGELOG.md`;网页终端的 `fastfetch` 与 `neofetch` 属于终端模拟彩蛋指令。
- `potion list` 查看药水槽与效果,`potion drink`、`potion throw`、`potion drop` 分别饮用、投掷与丢弃药水;投掷省略目标时默认投向第一个敌人。
- 联机地图与事件采用同一套队伍决策:队长选择直接生效,半数及以上存活队员选择同一分支或选项时生效;事件为全队共享一个,效果作用于所有队员,触发战斗时全队一并进入。
- 战斗日志只输出本次指令新产生的事件;联机【我方战场】按队员分段展示全队随从与护符;单回合 Buff、每回合出牌计数与流血层数按玩家各自结算。
- 架构重构已完成战斗、联机、路由、渲染、本地化与数值配置化;`game/` 与 `server/` 全部 Python 文件不超过 650 行。

## 目录

| 路径 | 说明 |
| :--- | :--- |
| `game/` | 游戏核心：卡牌、战斗、地图、探索、主城、咖啡馆、渲染与存档 |
| `server/` | FastAPI 单接口后端：`POST /api/v1/action` |
| `server/shell/` | 终端：文件系统、历史与补全提示 |
| `play_rogue.py` | 本地控制台入口，免前缀游玩 |
| `game/test/core/` | 核心与联机回归测试：游戏逻辑与主要交互 |
| `game/test/server/` | 后端账号、认证与接口回归测试 |
| `game/test/check_refactor_gates.py` | 重构门禁扫描 |
| `scratch/` | 临时脚本目录，已被 gitignore，不提交 |
| `deploy/` | systemd、Cloudflare Tunnel 与环境变量模板 |

## 本地游玩

```bash
py play_rogue.py
```

输入 `exit` 或 `quit` 退出。控制台模式默认使用 `data/` 下的存档。

## 核心测试

```bash
PYTHONPATH="." PYTHONIOENCODING="utf-8" py -m unittest discover -s game/test/core -t . -p "test_*.py"
```

## 后端

安装依赖：

```bash
uv venv .venv --python 3.15
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
```

启动：

```bash
PYTHONPATH="." .venv/Scripts/python.exe -m uvicorn server.app:create_app --factory --host 127.0.0.1 --port 8787 --workers 1
```

后端必须单进程。游戏核心包含进程级状态，多 worker 会破坏每用户串行与存档一致性。

### 环境变量

| 变量 | 说明 |
| :--- | :--- |
| `ROGUE_DATA_DIR` | 存档与 SQLite 根目录，默认 `data/server` |
| `ROGUE_DB_PATH` | 账号数据库，默认 `<ROGUE_DATA_DIR>/accounts.sqlite3` |
| `ROGUE_PLAYER_DIR` | 每玩家 JSON 存档目录，默认 `<ROGUE_DATA_DIR>/players` |
| `ROGUE_IM_TOKEN` | 即时通讯令牌 |
| `ROGUE_ORIGIN_KEY` | Worker 来源校验头，可留空关闭 |
| `SUPABASE_URL` | Supabase 项目地址 |
| `SUPABASE_JWKS_URL` | Supabase JWKS 地址 |
| `SUPABASE_JWT_ISSUER` | JWT issuer |
| `SUPABASE_JWT_AUD` | JWT audience，默认 `authenticated` |
| `SUPABASE_JWT_SECRET` | 可选，仅用于 HS256 兼容 |
| `ROGUE_ALLOWED_ORIGINS` | CORS 白名单，逗号分隔 |
| `ROGUE_IM_PREFIXES` | 即时通讯指令前缀，逗号分隔 |

### 管理员授权

管理员身份由账号数据库 `players.is_admin` 字段决定，默认 `0`；`rogueadmin`、`admin` 与 `admin accounts` 仅对该字段为 `1` 的用户开放。线上目前只授权了 `pppopipupu` 的主账号：

```bash
py -m server.adminctl set <用户ID> on
py -m server.adminctl list
```

`set` 按 `id`、`im_user_id`、`web_user_id` 或可读 `handle` 精确定位用户；用户需先登录一次生成记录，具体用户 ID 可由 `adminctl list` 查看。也可直接执行 `UPDATE players SET is_admin = 1 WHERE id = '<用户ID>';`。设为 `off` 可收回权限。Linux 部署时把上述命令中的 `py` 换成虚拟环境中的 `python`。

### 接口

```http
POST /api/v1/action
Content-Type: application/json

{
  "command": "p 1 e1",
  "channel": "web",
  "name": "可选显示名",
  "force": false,
  "prefixes": [".rogue"],
  "group": false,
  "is_group": false,
  "group_id": "",
  "message_type": "",
  "projection_poll": false
}
```

认证：

| 来源 | 请求头 |
| :--- | :--- |
| 网页 GitHub | `Authorization: Bearer <Supabase access token>` |
| 网页游客 | `X-Rogue-Guest-Id: <UUID>` |
| 网页游客首次建号 | `X-Rogue-Guest-Id: <UUID>` + `X-Rogue-Guest-Create: 1` |
| 即时通讯 | `X-Rogue-IM-Token: <token>` + `X-Rogue-IM-User: <平台用户 ID>` |
| 管理命令 | 无独立令牌，按用户数据的 `is_admin` 字段鉴权 |

游客 UUID 是账号鉴权文件，不能公开。网页同时携带 GitHub 令牌与游客 UUID 时，后端会把该游客账号绑定到 GitHub 身份并发放一次 1000 GP 奖励。

响应：

```json
{
  "ok": true,
  "handled": true,
  "text": "渲染文本",
  "state": { "v": 1, "screen": "battle" },
  "projections": [
    {
      "player": "队友",
      "command": "使用 火球术",
      "result": "造成 12 点伤害。",
      "text": "📡 队友投影\n[队友] 使用 火球术\n造成 12 点伤害。"
    }
  ],
  "account": {
    "id": "小明",
    "handle": "小明",
    "uuid": "0f8fad5b-d9cb-469f-a165-70867728950e",
    "display_name": "小明",
    "linked": false,
    "is_guest": true,
    "is_formal": false,
    "bind_reward_claimed": false
  },
  "shell": {
    "user": "tester",
    "host": "rogue-core",
    "cwd": "~",
    "branch": "master",
    "status": 0
  },
  "clear": false
}
```

`state` 只对网页通道返回。`handled=false` 表示即时通讯消息不是游戏指令,前端不应回复。`shell` 是终端提示符状态,`clear=true` 表示前端应清空屏幕。

联机牌局中 `projections` 按队友的每次操作返回一条投影，包含指令与结果；队伍中默认开启，可用 `projection 开启|关闭|状态` 切换。即时通讯群聊(`group`、`is_group`、`group_id` 或群聊 `message_type`)禁用该命令且不返回投影。网页空闲时使用同一接口发送 `projection_poll=true` 拉取新投影，拉取后队列清空。`account.id` 与 `account.handle` 是可读玩家 ID，用于好友、组队与展示；`account.uuid` 是当前账号的鉴权文件，只返回给账号本人，请勿公开。

### 终端命令

终端命令与游戏指令共用同一输入框；命中终端命令时优先执行，其余输入交给游戏。终端命令在主菜单和战斗中都可用。

| 类别 | 示例 |
| :--- | :--- |
| 文件 | `ls`、`ls -la`、`cd dungeon`、`pwd`、`cat README.md` |
| 写入 | `echo 文本 > note.txt`、`echo 追加 >> note.txt`、`touch note.txt`、`rm note.txt` |
| 查询 | `uname -a`、`whoami`、`date`、`df -h`、`free -h`、`ps aux`、`top` |
| 检索 | `grep card README.md`、`find . -name "*.md"`、`head`、`tail`、`wc`、`tree` |
| 彩蛋 | `neofetch`、`git status`、`systemctl status rogue-core`、`journalctl -u rogue-core` |
| 帮助 | `help system`、`man ls`、`history`、`clear` |

`help` 默认显示分类指令一览,`help <指令|别名>` 显示单条指令详解；`help system` 显示终端命令帮助。网页端肉鸽模式固定开启，`mode` 指令已移除；即时通讯端使用 `mode` 切换免前缀模式。

账号命令也走同一接口：

| 命令 | 说明 |
| :--- | :--- |
| `我的ID` / `uuid` / `myid` | 私聊返回当前玩家的可读 ID、账号 UUID 与绑定状态 |
| `secrets` / `迁移码` | 私聊返回账号 UUID 并提醒该 UUID 是鉴权文件 |
| `绑定码` / `bindcode` | 网页端生成一次性网页绑定码，供即时通讯端 `start <绑定码>` 使用 |
| `rename` / `改名` / `昵称` | 修改玩家名并消耗 1000 GP，重名会被拒绝且不扣 GP |
| `friend name` | 同上，保留为好友子命令形式 |
| `admin accounts` | 导出 UUID / 可读 ID / IM / Web 映射，仅管理员用户可用 |
| `leaderboard` | 查看 GP 排行榜前 20，显示可读玩家 ID、GP 与当前层数 |
| `leaderboard online` | 查看最近 5 分钟在线玩家 |
| `签到` / `checkin` | 每日 UTC+0 签到，领取下一局祝福并给集换卡盖章 |
| `friend` / `好友` | 好友列表、搜索、申请、接受、删除与组队邀请 |
| `team` / `队伍` | 创建 2~4 人队伍、邀请、准备并开启联机合作牌局 |

即时通讯端新用户必须发送 `start` 以游客身份开始，或发送 `start <网页绑定码>` 关联已有网页账号；其他指令在未建号前只返回帮助与绑定提示。

## 尸体与冤魂

玩家在某一层被击败后，会在该层留下全局唯一的尸体节点，并记录阵亡者昵称、死因、金币与死亡时的卡组。其他玩家在同层地图选择尸体节点后会进入冤魂战：

- 冤魂使用阵亡者死亡时的卡组，每回合随机打出一张牌。
- 击败冤魂后，搜刮者获得阵亡者本局结算 GP 的 30%~50%，并可从死者卡组中 6 选 2，每次都可以跳过。
- 强化、宝石等卡牌状态会保留。
- 尸体只会被首个击败冤魂的玩家搜刮；搜刮完成后该层尸体节点对所有玩家消失。
- 搜刮者被冤魂击败时按正常死亡处理，原尸体保留，同时搜刮者自己也会留下新尸体。
- 尸体节点是可选临时节点；完成搜刮后回到当前层地图，不会推进到下一层。

## 测试

回归测试长期保留在 `game/test/`，只覆盖核心游戏逻辑与主要交互；临时脚本放在 `scratch/`，该目录已被 gitignore，不进入版本库。

```bash
PYTHONPATH="." PYTHONIOENCODING="utf-8" py -m unittest discover -s game/test/core -t . -p "test_*.py"
PYTHONPATH="." PYTHONIOENCODING="utf-8" .venv/Scripts/python.exe -m unittest discover -s game/test/server -t . -p "test_*.py" -v
```

## 相关仓库

| 仓库 | 说明 |
| :--- | :--- |
| `pppopipupu/card_roguelike_cli` | 本仓库，无头核心与后端 |
| `pppopipupu/astrbot_plugin_text_roguelike` | AstrBot 薄客户端插件 |
| `pppopipupu/rogue_frontend` | Solid + WebGL 网页前端与 Cloudflare Worker |
