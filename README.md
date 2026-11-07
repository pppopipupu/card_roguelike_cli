# 魔法肉鸽卡牌游戏核心

基于 DND 5.5E 背景的文字回合制肉鸽卡牌游戏。本仓库是无头游戏核心、单接口后端和本地控制台入口；AstrBot 插件与网页前端在独立仓库中运行。

## 目录

| 路径 | 说明 |
| :--- | :--- |
| `game/` | 游戏核心：卡牌、战斗、地图、探索、主城、咖啡馆、渲染与存档 |
| `server/` | FastAPI 单接口后端：`POST /api/v1/action` |
| `play_rogue.py` | 本地控制台入口，免前缀游玩 |
| `scratch/rogue_tests/` | 核心单元与集成测试 |
| `scratch/server_tests/` | 后端账号、认证与接口测试 |
| `deploy/` | systemd、Cloudflare Tunnel 与环境变量模板 |

## 本地游玩

```bash
py play_rogue.py
```

输入 `exit` 或 `quit` 退出。控制台模式默认使用 `data/` 下的存档。

## 核心测试

```bash
PYTHONPATH="." PYTHONIOENCODING="utf-8" py scratch/test_flow.py
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
| `ROGUE_ADMIN_TOKEN` | 管理员令牌 |
| `ROGUE_ORIGIN_KEY` | Worker 来源校验头，可留空关闭 |
| `SUPABASE_URL` | Supabase 项目地址 |
| `SUPABASE_JWKS_URL` | Supabase JWKS 地址 |
| `SUPABASE_JWT_ISSUER` | JWT issuer |
| `SUPABASE_JWT_AUD` | JWT audience，默认 `authenticated` |
| `SUPABASE_JWT_SECRET` | 可选，仅用于 HS256 兼容 |
| `ROGUE_ALLOWED_ORIGINS` | CORS 白名单，逗号分隔 |
| `ROGUE_IM_PREFIXES` | 即时通讯指令前缀，逗号分隔 |

### 接口

```http
POST /api/v1/action
Content-Type: application/json

{
  "command": "p 1 e1",
  "channel": "web",
  "name": "可选显示名",
  "force": false,
  "prefixes": [".rogue"]
}
```

认证：

| 来源 | 请求头 |
| :--- | :--- |
| 网页 | `Authorization: Bearer <Supabase access token>` |
| 即时通讯 | `X-Rogue-IM-Token: <token>` + `X-Rogue-IM-User: <平台用户 ID>` |
| 管理命令 | 额外 `X-Rogue-Admin-Token: <token>` |

响应：

```json
{
  "ok": true,
  "handled": true,
  "text": "渲染文本",
  "state": { "v": 1, "screen": "battle" },
  "account": { "uuid": "...", "linked": false }
}
```

`state` 只对网页通道返回。`handled=false` 表示即时通讯消息不是游戏指令，前端不应回复。

账号命令也走同一接口：

| 命令 | 说明 |
| :--- | :--- |
| `我的ID` / `uuid` | 返回当前账号 UUID |
| `secrets` / `迁移码` | 即时通讯端私聊获取迁移码 UUID |
| `绑定 <uuid>` | 网页账号关联即时通讯进度 |
| `绑定 <uuid> force` | 放弃当前网页独立进度后关联 |
| `admin accounts` | 导出 UUID / IM / Web 映射，需要管理员令牌 |

## 测试

```bash
PYTHONPATH="." PYTHONIOENCODING="utf-8" .venv/Scripts/python.exe -m unittest discover -s scratch/server_tests -p "test_*.py" -v
```

## 相关仓库

| 仓库 | 说明 |
| :--- | :--- |
| `pppopipupu/card_roguelike_cli` | 本仓库，无头核心与后端 |
| `pppopipupu/astrbot_plugin_text_roguelike` | AstrBot 薄客户端插件 |
| `pppopipupu/rogue_frontend` | Solid + WebGL 网页前端与 Cloudflare Worker |
