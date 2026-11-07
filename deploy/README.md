# 部署模板

以下文件是模板，不包含任何真实密钥。

| 文件 | 用途 |
| :--- | :--- |
| `rogue.service` | systemd 单元，单进程 uvicorn |
| `cloudflared.yml` | Cloudflare Tunnel 入口，只暴露 `origin-rogue.114514256.xyz` |
| `env.example` | 后端环境变量模板 |

## VPS 目录约定

```text
/opt/rogue/
├── card_roguelike_cli/     # 本仓库
├── venv/                   # uv 创建的虚拟环境
├── data/                   # 存档与 accounts.sqlite3
└── rogue.env               # 从 env.example 复制并填入真实值
```

## 启动

```bash
cd /opt/rogue/card_roguelike_cli
/opt/rogue/venv/bin/uvicorn server.app:create_app --factory --host 127.0.0.1 --port 8787 --workers 1
```

只允许单 worker。游戏核心存在进程级状态，多 worker 会导致存档串档。
