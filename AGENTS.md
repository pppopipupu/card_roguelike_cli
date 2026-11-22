# 核心仓库开发规范

## 1. 基础约束

- 在用户没有明确要求的情况下，禁止在 Python 源码、测试脚本中编写新注释或新 docstring；JSON 配置中严禁任何注释。核心公共接口、事件模型、实体钩子基类与通用组件上已维护的多行文档注释（`"""`）必须随接口变更同步保持准确，禁止随意删除。
- 本项目统一使用 Python 3.15：`py`、`.venv`、`pyproject.toml` 与 Pyright 的 `pythonVersion` 均以 3.15 为准，源码采用 3.15 兼容语法，不保留 3.12 兼容写法。
- AstrBot 客户端插件使用 Python 3.12，以兼容 AstrBot 运行时；除该插件外不得为 3.12 降级本仓库语法或依赖。
- 所有文本文件读写必须显式指定 UTF-8。
- 第一开发语言为中文；中文文案必须语法纯正，禁止中英混杂介词。
- 伤害类型文案规范：物理伤害是挥砍、穿刺、钝击的总称，魔法伤害是各类法术元素伤害的总称，不存在单一的“物理伤害”或“魔法伤害”类型；严禁在卡牌、技能、遗物或敌人描述中使用“造成 xx 物理伤害”或“造成 xx 魔法伤害”的措辞，必须写明具体伤害类型（如挥砍伤害、穿刺伤害、钝击伤害、火焰伤害、寒冷伤害、闪电伤害、雷鸣伤害、力场伤害、黯蚀伤害、光耀伤害、心灵伤害、毒素伤害、酸液伤害、真实伤害）；“物理伤害”与“魔法伤害”仅可用于类别加成/减免/易伤等修饰措辞（如“物理伤害增加 50%”“魔法伤害增加 100%”）。
- 临时分析脚本只能放在 `scratch/`（已被 gitignore，不提交）或会话脑区，禁止留在 `game/`、`server/` 等工作区目录。
- 除用户明确要求，禁止执行任何 git 命令。
- 除用户明确要求外，禁止修改 README.md。
- Windows 下统一使用 `py` 启动脚本，禁止使用 `python`；测试前设置 `PYTHONPATH="."` 与 `PYTHONIOENCODING="utf-8"`。

## 2. 架构与扩展

- 数据驱动：卡牌、随从、敌人、护符、遗物、Buff、事件、文本与数值全部放入 `game/data/` 的独立配置；执行类不得硬编码文案或奖励数值。
- 本地化：所有玩家可见文本（提示、日志、错误、选项、投影消息）最终必须通过 `get_locale_text` 与 `game/data/locale/zh_cn/` 中的本地化键名读取；执行类禁止硬编码展示文案。新代码按“文本管线”规则延迟烘焙，禁止在底层逻辑中提前调用 `get_locale_text`。
- 文本管线：新编写的代码一律采用事件流架构。底层逻辑禁止拼接展示字符串或调用 `get_locale_text`，必须返回 `msgspec.Struct` 事件流（`LocaleText` 携带本地化键名与参数）；由 `game/core/text/pipeline.py` 按 `game/data/text_layout_data.py` 的配置聚合，统一在上层渲染边界完成本地化与拼接。`RenderedText` 仅允许包装其他渲染器已产出的最终 UI 片段；存量代码按改动范围逐步迁移。
- 数值：所有玩法数值（伤害、生命、护盾、金币、概率、层数、数量、价格、倍率等）必须放入 `game/data/` 配置并具名引用；执行类禁止硬编码玩法数值。
- 开闭原则：新增卡牌、遗物、Buff、事件或敌人机制时，不修改核心战斗引擎；通过订阅 `event_bus` 的原子事件实现。Boss 濒死、死亡拦截、形态转换由具体敌人模板订阅事件并取消结算。
- 结算全面钩子化：所有卡牌、Buff、遗物、随从、护符、宝石与附魔的战斗结算必须注册为标准事件与实体钩子（`EventBus`、`BuffImpl`、`Card`、`RelicImpl`、`MinionTemplate`、`EnemyTemplate` 及对应 `TriggerHandler`）；严禁向 `card_player_turn.py`、`card_player.py`、`party_battle.py`、`combat_resolver.py`、`enemy_controller.py` 等核心战斗类添加具体实体 ID 的硬编码判断逻辑，需要新时机时必须先在 `game/models/events.py` 定义标准 `GameEvent` 子类并经由 `event_bus` 派发。
- 事件模型：`game/models/events.py` 中的所有战斗事件必须继承 `GameEvent`（`msgspec.Struct`，基类字段 `cancelled`、`engine` 为 keyword-only）；禁止使用 `@dataclass` 定义事件，禁止给事件实例动态追加未声明字段。新增事件只声明业务字段，并保持既有位置参数顺序。
- 额外回合：统一通过 `game/core/battle/extra_turn_service.py` 的 `grant_extra_turn` 与 `end_and_begin` 管理，除该服务的旧存档迁移逻辑外，禁止直接读写 `extra_turns_left`、`time_stop_upgraded` 或自行维护额外回合计数。额外回合按玩家排队，结束回合时必须先进入自己的额外回合；单机、协作与 PVP 都只在最后一个额外回合结束后才认定回合结束。时间停止等“造成伤害提前结束”“暂停负面状态”的行为通过额外回合条目的 `break_on_damage` 与 `pause_debuffs` 声明。
- 统一选择器与通用选择组件：所有战斗内的目标选择、抉择（多选一）、发掘（从牌堆或卡池选卡）、强制弃牌与多步交互必须复用 `game/core/battle/selection/` 中的通用声明式组件（如 `choose_one_spec`、`discover_from_pile_spec`、`discover_from_pool_spec`、`discard_hand_spec`、`target_step`、`SelectionResult` 与 `TargetRule`），通过 `Card.get_selection_spec` / `execute_with_selections` / `execute_post_selections` 接入统一 `interaction_session` 协议；严禁在卡牌、Buff、遗物或 CLI 路由中直接向 `state_stack` 追加自定义选择类型或手写 `pending_*` 状态流转。
- 注册：卡牌、遗物、Buff、命令与事件分支使用装饰器或 `__init_subclass__` 自动注册；禁止硬编码注册字典和大型 if-else。
- 命令模式：具体动作与命令拆为独立 Handler，由路由表分发。新增命令必须同时提供英文变体、至少一个快捷别名，并同步更新状态白名单与 allowed_states。
- 指令优先级：所有玩家可见的指令提示、用法、帮助条目与错误文案必须优先展示英文简写指令（如 `trade`、`touch`），中文指令仅作为辅助别名随后展示；新增指令必须同时提供英文变体与中文别名，英文别名注册在别名列表首位。
- 更新日志：玩家通过 `changelog` 指令查看近期更改，内容取自仓库根目录 `CHANGELOG.md`；每个面向玩家的改动必须同步记入该文件，输出前经 `strip_markdown` 转为纯文本，避免向玩家展示 Markdown 标记。
- 拆分：一个文件只承担一个职责；非二进制文件超过 1000 行必须物理拆分。核心引擎只做 Facade，具体逻辑委派给子组件。
- 上帝类红线：非二进制文件超过 500 行应考虑重构，超过 1000 行必须立即重构；无论用户是否要求，均须执行。
- 复用：通用判断、数值缩放、排版与流程使用基类模板方法或共享工具函数，禁止复制粘贴相似逻辑。
- 卡牌预览：`game/renderer/card_preview.py` 是卡牌介绍的渲染边界，负责 `{base_dmg}` 等占位符替换、动态伤害数值与条件文案括号。宝石、附魔等持久修改必须在生成卡牌对象时直接写入基础数值与介绍中的数字；力量、虚弱、重度虚弱等战斗内条件修饰才在预览时通过 `game/entities/cards/base.py` 的 `annotate_number_modifier` 以“原值（当前值）”追加，且仅在数值实际变化时显示。禁止在预览层或执行类中手写数字括号或复制该格式化逻辑。
- 文本管线：底层逻辑返回 `msgspec.Struct` 事件，经 `game/core/text/pipeline.py` 按 `game/data/text_layout_data.py` 聚合后，在渲染边界加载本地化键名。
- 状态：实体状态使用 `models/state.py` 中的 Dataclass，持久化统一走 `models/manager.py` 的 SaveManager。卡牌堆中的卡牌必须是 `CardState`，禁止使用裸字符串。新代码禁止 `from_cid`；禁止修改卡牌 id 或追加后缀，升级、宝石、重放等状态只改属性。重放、易碎等修饰不得写入卡牌名称，只追加到描述末尾。
- 序列化：JSON 读写与 HTTP 响应统一走 `game/json_codec.py` 与 `server/responses.py`（orjson），禁止直接 `import json`。
- 大数统计：`total_damage` 等无界累计值在存档 JSON 中保存为字符串，展示时超过 12 位使用科学记数法。
- 事件循环：服务端在 Linux 与 macOS 使用 uvloop，Windows 回退 asyncio；业务代码禁止自行创建事件循环或替换运行中的循环。
- 后端：只暴露 `POST /api/v1/action` 与 `/healthz`；单进程、单 worker、每用户串行锁、原子写存档。JWT 通过 Supabase JWKS 校验；禁止使用 Supabase service_role；密钥只从环境变量读取。
- 输出：游戏交互文本除非用户明确要求的场合否则禁止Markdown、LaTeX 和解释性括号；除查询模式可附英文 ID 外，禁止裸露未翻译的实体 ID。玩家昵称只在需要的界面通过显式变量格式化，禁止全局替换“玩家”。

## 3. 测试

- 在用户没有明确要求的情况下，测试代码同样禁止编写新注释与 docstring。
- 核心测试通过 `run_command(plugin, "command")` 模拟真实输入，禁止直接调用 `cli_router.handle_command`；后端测试通过 FastAPI TestClient 调用 `POST /api/v1/action`。
- 禁止直接改写关卡节点、怪物血量或动作点、Buff、卡牌堆等内存状态。关卡切换与战斗结算必须由真实命令触发；高血量目标使用测试训练假人。
- 允许的 Mock 仅限：存档 IO 桩、随机数确定化、事件监听计数桩。禁止用 Mock 替代关卡流转、战斗结算和卡牌堆演进。
- 严禁将任何单次验证加入 `game/test/` 回归测试集：纯静态数值调整（如降价、属性/概率/倍率/稀有度微调）、配置字典核对、帮助/总览/更新日志/查询（`query`/`i`）文案输出核对、管理调试指令及单次改动冒烟验证，一律只在 `scratch/` 运行一次性校验后立即删除，绝不允许污染回归集。
- 测试目录：`game/test/core/` 覆盖核心游戏逻辑与主要交互，`game/test/server/` 覆盖后端账号、认证与接口，`game/test/check_refactor_gates.py` 是重构门禁扫描。
- 回归测试必须具备通过真实指令流或接口流捕获回归缺陷的能力：核心回归测试必须由 `run_command(plugin, "...")`（或服务端 `POST /api/v1/action`）驱动完整多步游戏状态流转，验证跨回合、跨节点不变量及玩家可观察行为是否受损；严禁绕过真实指令流直接调用 `card.execute`、`opt.execute`、`opt._run_effect`、`event_bus.dispatch`、`router._execute_sub_action` 或断言静态配置常量/源码文本编写白盒或单点冒烟测试，不符合真实指令流抓错标准的测试必须立即清理删除。
- 核心测试：PYTHONPATH="." PYTHONIOENCODING="utf-8" py -m unittest discover -s game/test/core -t . -p "test_*.py"；后端测试：PYTHONPATH="." PYTHONIOENCODING="utf-8" .venv/Scripts/python.exe -m unittest discover -s game/test/server -t . -p "test_*.py"；后端启动必须单 worker。
- 静态检查：`.venv/Scripts/pyright.exe`，配置见 `pyproject.toml` 的 `[tool.pyright]`；新增未定义名称、未绑定变量或无法解析的导入会直接报错。
