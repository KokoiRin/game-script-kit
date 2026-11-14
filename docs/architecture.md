# Star 架构约束

修改源码、port contract 或模块职责前阅读本文件，并先通过 [CONTEXT](../CONTEXT.md) 确认当前目标。
本文件规定稳定边界；当前能力、已知限制和待决问题见 [项目现状](current-state.md)。
设计理由按需查阅 [ADR 索引](adr/README.md)，运行方法见 [README](../README.md)。

## 职责与依赖

Star 使用 ports-and-adapters，把脚本规则与桌面设备、权限和入口隔开。
这让同一条规则能通过 fake 验证，并允许通过更换 adapter 接入其他平台；理由见 [ADR 0002](adr/0002-ports-and-adapters.md)。

```text
入口 → 应用用例 → 执行与规则 → 领域模型
           ↓           ↓
      应用层 ports   执行层 ports ← 平台 adapters
           ↑                         ↑
           └────── 平台装配负责注入 ───┘
```

上图区分调用与装配：平台装配可以依赖全部待连接部件，核心依赖自身声明的 port。
入口可以持有已装配的用例对象；每个请求无须重新经过装配函数。

| 角色 | 负责的判断 | 当前位置 |
| --- | --- | --- |
| 领域模型 | 任务声明、窗口、资源和值对象的不变量 | [domain](../src/game_automation/portable/domain/) |
| 执行与规则 | 运行上下文直接执行动作、观察、取消与期限 | [engine](../src/game_automation/portable/engine/) |
| 应用用例 | 编排一次用户意图、准备依赖、组织会话与运行结果 | [application](../src/game_automation/portable/application/) |
| Adapter | 将 port 请求落到设备、图像库和平台能力 | [platform](../src/game_automation/platform/)、[dry-run](../src/game_automation/portable/adapters/dry_run.py) |
| 装配 | 选择平台实现，向用例注入 factory | [composition.py](../src/game_automation/platform/local_desktop/composition.py) |
| 原生界面 | SwiftUI 展示与 AppKit 画布、窗口和进程生命周期 | [StarDesktop](../native/StarDesktop/) |
| 入口 | 解析 CLI/本地管道请求，调用用例，转换展示格式 | [entrypoints](../src/game_automation/platform/local_desktop/entrypoints/) |
| 素材准备用例 | 冻结帧、取点换算、裁图边界与保存编排，独立于脚本执行 | [preparation](../src/game_automation/portable/preparation/) |

依赖方向比目录名称更重要：领域对象不访问设备；执行层不创建真实 adapter；平台细节留在 adapter。
具体任务的点位、模板和步骤由脚本表达；任务编写取舍见 [ADR 0001](adr/0001-agent-authored-tasks.md)。

## 当前主链路与装配

CLI 单脚本链路：

```text
cli → 项目 catalog / 共享资源 → run_script_on_local_desktop
    → run_script → Python run(ctx) → TaskContext → 运行 ports
```

原生桌面链路：

```text
SwiftUI/AppKit 壳 → 受管理的 Python 子进程 / desktop_backend
  → LocalControlApplication → 后台运行会话 → run_script
    → Python run(ctx) → TaskContext → 运行 ports
```

[run_script](../src/game_automation/portable/application/script_run.py) 按脚本需求创建运行依赖，并在真实执行前准备目标应用与窗口。
[run_script_plan](../src/game_automation/portable/application/run_plan.py) 编排已有脚本及停止策略，单份脚本仍交给注入的运行函数。
[ProjectScreenStateReader](../src/game_automation/portable/application/screen_state_reader.py) 直接连接配置与识图 port；状态读取不反向装配控制台。
新增执行入口复用这些用例；保持运行控制台聚焦运行与停止的理由见 [ADR 0004](adr/0004-small-console.md)，独立素材准备壳见 [ADR 0007](adr/0007-preparation-and-execution.md)。

素材准备链路：

```text
原生准备页 → desktop_backend → PreparationService → 准备 ports ← 平台 adapter
```

准备 UI 拥有选择和框选交互；通用准备服务拥有冻结帧身份、坐标转换与校验。
准备服务不导入 runner、运行控制应用或脚本目录；执行器不读取准备 UI 的状态。
原生壳组合两个用例，不能通过共享可变界面状态驱动规则。生命周期和进程边界见 [ADR 0008](adr/0008-native-macos-desktop.md)：原生层负责监督进程，Python 会话负责取消和等待实际执行线程，双方各自回收所拥有的资源。

## 只读窗口观察

原生观察页通过后台协议调用独立的观察会话。会话持有采样生命周期与有效性，平台 probe 负责一帧窗口捕获及批量识别，原生壳显示快照并监督后台退出。准备帧与持续观察图像分别拥有，不互相替换。

状态快照是观察结果。脚本现有状态 reader 仍按自己的运行契约读取画面，不消费 UI 缓存。连续观察、素材坐标和停止边界见 [ADR 0009](adr/0009-live-window-observation.md)。

## Port 归属与副作用

Port 的接口由消费它的核心职责决定，adapter 负责实现；新增接缝先确定调用方需要知道什么。
[engine ports](../src/game_automation/portable/engine/ports.py) 声明执行所需的输入、取色、识图、状态、日志和取消能力。
[application ports](../src/game_automation/portable/application/ports.py) 声明运行前激活应用、选择窗口等环境能力。
[准备 ports](../src/game_automation/portable/preparation/ports.py) 声明素材采集所需的窗口、截图、裁图和存储能力。准备与执行可共享公共几何及 [截图坐标转换](../src/game_automation/platform/desktop/adapters/screen_capture.py)，不互相装配。
现有坐标记录工具也从 engine ports 使用指针和按键 reader；工具读取按键与模拟键盘输出各有职责。

- `InputDevice` 负责原子输入；组合键的按下、释放和失败清理由 adapter 一次完成。
- `TaskContext` 直接拥有目标解析、原子动作调用、轮询、期限、取消检查与事件。
- 识图 adapter 隐藏截图、物理像素换算、模板读取和底层库错误。
- 装配以 factory 延迟创建真实能力；普通查询和 dry-run 保持其声明的无桌面副作用边界。

端口变化同时核对调用方、真实 adapter、dry-run 和 fake 的行为契约。
仅为透传而增加一层接口前，先判断它是否收拢了调用顺序、错误结果或稳定规则。

## 运行状态与取消的所有权

[FunctionTask](../src/game_automation/portable/domain/task.py) 保存元信息和主文件源码快照；运行结果和会话状态存放在它之外。
[LocalControlApplication](../src/game_automation/portable/application/local_control.py) 拥有当前后台会话、线程安全日志和取消标记。
入口请求停止时设置标记，执行器通过 `CancellationToken` 在执行边界读取；adapter 不决定脚本的循环策略。
取消的检查时机和响应限制属于当前行为，详见 [项目现状](current-state.md)，不把“立即停止”作为未验证的保证。

任务函数使用 Python 的循环和异常传播组织退出。检查点在上下文调用和等待轮询中读取退出条件，用户取消拥有独立的终止信号。
期限作用域与操作使用独立身份。核心维护作用域的进入、到期与退出，局部恢复通过 `scope_id` 识别自己拥有的期限。任务恢复逻辑中的普通异常捕获继续让终止取消传播。
[状态 reader](../src/game_automation/portable/application/screen_state_reader.py) 每次读取最新配置与画面，返回本轮状态；运行条件不依赖 UI 中缓存的显示结果。
日志与步骤事件描述已发生的执行，展示层消费这些记录；它们不作为驱动脚本的第二套状态机。
局部恢复、重试和子任务的讨论不改变现有契约；是否实现及具体语义以当前决策和代码为准。

## Python 任务与资源

[任务发现](../src/game_automation/portable/application/task_discovery.py) 统一文件枚举、读取、编码和逐文件错误隔离。[函数任务解析](../src/game_automation/portable/application/function_task_loader.py) 通过 AST 读取 `TASK` 字面量与同步 `run(ctx)` 入口，生成 `FunctionTask`。查询阶段只解析元信息，应用用例在运行时执行源码快照并管理 tracing 和平台资源。

[TaskContext](../src/game_automation/portable/engine/task_context.py) 直接绑定窗口、命名资源和已打开能力，拥有动作、观察、期限与取消。任务目录中的 Python 代码通过线程局部 tracing 检查用户取消，平台输入与清理沿用平台约定。整体职责见 [ADR 0014](adr/0014-core-first-execution.md)。

Python 是唯一任务格式。任务自身使用函数、分支、循环和异常处理。[ADR 0015](adr/0015-python-only-tasks.md) 记录旧 JSON 步骤格式与步骤树解释器的退役。状态和素材配置继续使用 JSON，各自由所属配置模块读取。

目标和资源声明在 [task_metadata](../src/game_automation/portable/application/task_metadata.py) 解析，领域类型负责可复用的不变量。CLI 和管道协议调用同一任务用例，具体游戏流程保存在工作区任务文件。

[项目 catalog](../src/game_automation/portable/application/project_scripts.py) 从所选数据根加载命名任务、隔离坏文件并报告错误，加载过程只读取声明。[共享资源合并](../src/game_automation/portable/application/script_resources.py) 保留任务局部资源的同名覆盖权。

[任务分析](../src/game_automation/portable/domain/task_analysis.py) 从 `requires` 和局部资源声明产生依赖与能力事实。详情、资源校验、共享资源需求和端口装配消费相同事实。任务作者负责声明动态代码使用的共享资源与能力。

### 框架与任务工作区

主仓保存框架、通用示例与开发验收工具；业务脚本、素材、状态配置和任务记录保存在仓库外的任务工作区，取舍见 [ADR 0006](adr/0006-local-task-workspaces.md)。
全局 `--workspace PATH` 将 CLI 和控制台绑定到同一个数据根；脚本发现、详情依赖、共享资源和状态 reader 使用该根，不由各入口自行猜测目录。
显式工作区只加载其中的 Python 任务；无参数时加载主仓 `scripts/` 的通用示例。
一个后台进程始终绑定一个根。原生壳切换工作区时先关闭旧后台，再创建新会话；不能在运行中切换或把旧帧带入新工作区。
任务工作区不是 Git 分支，新增任务不改变框架分层，也不需要建立游戏专用分支。

## 窗口与坐标边界

[Window](../src/game_automation/portable/domain/windows.py) 负责点位和搜索区域的坐标解析；真实窗口发现与激活由 application port 和平台 adapter 完成。
运行前选窗得到的范围用于本次脚本副本，不修改 catalog 中的脚本定义。
脚本点位、图片匹配结果、显示像素和实际输入坐标要在对应边界转换，调用方应明确自己使用的坐标系。
窗口移动、状态识别区域及入口能力差异的当前限制记录在 [项目现状](current-state.md)；它们不是需要永久保留的架构规则。

准备会话按帧 ID 绑定 PNG、实际像素尺寸、窗口逻辑范围与采集时间。UI 的显示坐标先转图像像素，再由准备服务转窗口相对或屏幕坐标；裁图只读取指定帧的内容。准备选窗不会修改运行目标，准备截图不充当运行状态缓存。

## 结果与验证边界

执行层报告任务函数的结束情况，应用层将运行结果映射为入口可用的结果。
判断完成同时看 `finish_reason` 和退出码；正常停止可能返回 `0`，动作已发送也不等于业务目标已经达成。
结果对象与验证证据的取舍见 [ADR 0003](adr/0003-results-and-verification.md)。

[视觉靶场](../src/star_visual_lab/) 是独立目标应用；Star 通过像素和输入操作它，验收程序再读取真值 API。
核心规则用 fake 验证，入口验证用户可见映射，真实桌面按需 smoke；证据不能由自己的成功日志替代。
重点边界可从 [执行核心](../tests/test_execution_core.py)、[运行用例](../tests/test_script_run.py)、[控制台用例](../tests/test_local_control.py) 和 [装配](../tests/test_local_desktop_composition.py) 测试进入。

## 常见需求落点与重审信号

| 需求 | 优先落点 | 需要重审的越界做法 |
| --- | --- | --- |
| 某任务增加点击、等待或模板 | 外部工作区的脚本与 assets，复用上下文动作 | 在主仓保存玩法记录或在 runner 中判断游戏名称 |
| 确认新增通用动作或控制语义 | 执行核心与作者接口，按需补声明解析与 adapter | 在 CLI/JS 中拼出另一套执行器 |
| 增加平台输入或窗口能力 | 对应 adapter 与 composition；必要时调整消费方 port | 让 portable 层导入平台库或系统命令 |
| 增加入口或调整展示 | 入口映射及已有 application 用例 | 用页面显示状态替代执行时读取 |
| 调整运行结果或停止策略 | 负责该层编排的执行核心或 application | 从退出码 `0` 推断业务完成 |

规则重复、修改一个行为需同步多个入口、或测试被迫读取内部细节时，先重新确认职责归属。
局部重构应收拢本轮触达的复杂度；接口只少一层转发时，检查能否直接使用已有能力。
跨模块的重要取舍写入 [ADR](adr/README.md)，现状和限制更新到 current-state；文档分工见 [ADR 0005](adr/0005-repository-documentation.md)。
