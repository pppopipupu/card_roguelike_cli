import os
import sys
import io
import asyncio
import random


if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from game.core.headless_server import HeadlessGameServer


async def run_command(plugin: HeadlessGameServer, cmd_str: str) -> str:
    result = await plugin.handle_rogue_message(
        user_id="test_user",
        sender_name="测试玩家",
        message=cmd_str,
        shortcut_prefix=[".rogue"],
        enable_shortcut=True,
        force_execute=True,
    )
    return result or ""


async def test_auto():
    plugin = HeadlessGameServer()
    save_manager = plugin.save_manager
    save_manager.delete_save("test_user")

    res = await run_command(plugin, ".rogue 开启")
    if "进行中的游戏" in res:
        res = await run_command(plugin, ".rogue 开启 确认")
    print(res)

    res = await run_command(plugin, ".rogue 选择 1")
    print(res)

    actions_pool = [
        ".rogue 使用 1",
        ".rogue 使用 2",
        ".rogue 使用 3",
        ".rogue 使用 [1, 2]",
        ".rogue 使用 1 e0",
        ".rogue 使用 1 e1",
        ".rogue 使用 2 p0",
        ".rogue 随从 1 攻击 0",
        ".rogue 随从 1 攻击 1",
        ".rogue 随从 1 技能 1",
        ".rogue 随从 1 技能 2",
        ".rogue 随从 1 技能 2",
        ".rogue 随从 1 技能 2 e0",
        ".rogue 选择 1",
        ".rogue 选择 2",
        ".rogue 选择 3",
        ".rogue 特殊 1",
        ".rogue 特殊 1 e0",
        ".rogue 结束",
        ".rogue 状态",
        ".rogue 牌组",
        ".rogue 队列 [使用 1, 随从 1 技能 2]",
        ".rogue 队列 [使用 1, 队列 [随从 1 攻击 0, 结束]]",
        ".rogue q [使用 1, 结束]",
        ".rogue queue [使用 2, 结束]",
        ".rogue 折叠",
        ".rogue 队列 [使用 1, 折叠, 结束]",
    ]

    for step in range(1, 151):
        cmd = random.choice(actions_pool)
        try:
            res = await run_command(plugin, cmd)
            print(f"Step {step}: {cmd}")
            print(res)
            print("=" * 50)
            if (
                "冒险结束" in res
                or "击败" in res
                or "通关成功" in res
                or "当前进度已清空" in res
            ):
                await run_command(plugin, ".rogue 开启确认")
                await run_command(plugin, ".rogue 开启")
        except Exception as ex:
            print(f"Exception at step {step} on command {cmd}: {ex}")
            raise ex
    print("Auto simulation finished successfully.")


async def test_interactive():
    plugin = HeadlessGameServer()
    print(
        "Interactive Test Console. Input commands like '.rogue 开启' or '.rogue 使用 1'. Input 'exit' to quit."
    )
    while True:
        try:
            line = input("> ").strip()
            if not line or line.lower() == "exit":
                break
            res = await run_command(plugin, line)
            print(res)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    if "--auto" in sys.argv:
        asyncio.run(test_auto())
    else:
        asyncio.run(test_interactive())
