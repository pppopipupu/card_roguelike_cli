# 核心仓库开发规范

## 1. 基础约束

- Python 源码、测试脚本与 JSON 配置中禁止任何注释和 docstring。
- 所有文本文件读写必须显式指定 UTF-8。
- 第一开发语言为中文；中文文案必须语法纯正，禁止中英混杂介词。
- 临时分析脚本只能放在会话脑区 scratch，禁止留在项目工作区。
- 除用户明确要求，禁止执行任何 git 命令。
- Windows 下统一使用 `py` 启动脚本，禁止使用 `python`；测试前设置 `PYTHONPATH="."` 与 `PYTHONIOENCODING="utf-8"`。

## 2. 架构与扩展

- 数据驱动：卡牌、随从、敌人、护符、遗物、Buff、事件、文本与数值全部放入 `game/data/` 的独立配置；执行类不得硬编码文案或奖励数值。
- 本地化：所有玩家可见文本（提示、日志、错误、选项、投影消息）必须通过 `get_locale_text` 与 `game/data/locale/zh_cn/` 中的本地化键名读取；执行类禁止硬编码展示文案。
- 数值：所有玩法数值（伤害、生命、护盾、金币、概率、层数、数量、价格、倍率等）必须放入 `game/data/` 配置并具名引用；执行类禁止硬编码玩法数值。
- 开闭原则：新增卡牌、遗物、Buff、事件或敌人机制时，不修改核心战斗引擎；通过订阅 `event_bus` 的原子事件实现。Boss 濒死、死亡拦截、形态转换由具体敌人模板订阅事件并取消结算。
- 注册：卡牌、遗物、Buff、命令与事件分支使用装饰器或 `__init_subclass__` 自动注册；禁止硬编码注册字典和大型 if-else。
- 命令模式：具体动作与命令拆为独立 Handler，由路由表分发。新增命令必须同时提供英文变体、至少一个快捷别名，并同步更新状态白名单与 allowed_states。
- 拆分：一个文件只承担一个职责；非二进制文件超过 1000 行必须物理拆分。核心引擎只做 Facade，具体逻辑委派给子组件。
- 上帝类红线：非二进制文件超过 500 行应考虑重构，超过 1000 行必须立即重构；无论用户是否要求，均须执行。
- 复用：通用判断、数值缩放、排版与流程使用基类模板方法或共享工具函数，禁止复制粘贴相似逻辑。
- 状态：实体状态使用 `models/state.py` 中的 Dataclass，持久化统一走 `models/manager.py` 的 SaveManager。卡牌堆中的卡牌必须是 `CardState`，禁止使用裸字符串。新代码禁止 `from_cid`；禁止修改卡牌 id 或追加后缀，升级、宝石、重放等状态只改属性。重放、易碎等修饰不得写入卡牌名称，只追加到描述末尾。
- 后端：只暴露 `POST /api/v1/action` 与 `/healthz`；单进程、单 worker、每用户串行锁、原子写存档。JWT 通过 Supabase JWKS 校验；禁止使用 Supabase service_role；密钥只从环境变量读取。
- 输出：机器人可见文本禁止 Markdown、LaTeX 和解释性括号；除查询模式可附英文 ID 外，禁止裸露未翻译的实体 ID。玩家昵称只在需要的界面通过显式变量格式化，禁止全局替换“玩家”。

## 3. 测试

- 测试代码同样禁止注释与 docstring。
- 核心测试通过 `run_command(plugin, "command")` 模拟真实输入，禁止直接调用 `cli_router.handle_command`；后端测试通过 FastAPI TestClient 调用 `POST /api/v1/action`。
- 禁止直接改写关卡节点、怪物血量或动作点、Buff、卡牌堆等内存状态。关卡切换与战斗结算必须由真实命令触发；高血量目标使用测试训练假人。
- 允许的 Mock 仅限：存档 IO 桩、随机数确定化、事件监听计数桩。禁止用 Mock 替代关卡流转、战斗结算和卡牌堆演进。
- 纯静态数值调整无需运行仿真与流程测试。
- 本地入口：`py scratch/test_flow.py`；后端测试：`PYTHONPATH="." .venv/Scripts/python.exe -m unittest discover -s scratch/server_tests -p "test_*.py" -v`；后端启动必须单 worker。
