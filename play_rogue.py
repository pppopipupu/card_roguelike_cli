import os
import sys
import io
import asyncio

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from game.core.api.headless_server import HeadlessGameServer
from game.renderer import GameRenderer

async def main():
    server = HeadlessGameServer(None)
    print("================━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━====================")
    print("  ✨ 欢迎来到魔法肉鸽卡牌游戏控制台版！")
    print("  💬 本控制台版不需要前缀即可游玩，比如输入：开启 / 使用 1 / 结束")
    print("  🚪 输入 exit 退出控制台")
    print("================━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━====================")
    
    run = server.save_manager.load_save("console_player")
    if run:
        print(GameRenderer.render_game(run))
    else:
        print(GameRenderer.render_menu())
        
    while True:
        try:
            line = input("RogueConsole> ").strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit"):
                break
            if not line.startswith(".") and not line.startswith("/"):
                line = ".rogue " + line
            
            res = await server.handle_rogue_message(
                user_id="console_player",
                sender_name="玩家",
                message=line,
                shortcut_prefix=[".rogue"],
                enable_shortcut=True
            )
            if res:
                print(res)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
