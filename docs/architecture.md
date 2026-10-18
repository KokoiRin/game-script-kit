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
| 领域模型 | 步骤、条件、窗口、资源和值对象的不变量 | [domain](../src/game_automation/portable/domain/) |
| 执行与规则 | 解释步骤树、评估条件、解析目标并调用 ports | [engine](../src/game_automation/portable/engine/) |
| 应用用例 | 编排一次用户意图、准备依赖、组织会话与运行结果 | [application](../src/game_automation/portable/application/) |
| Adapter | 将 port 请求落到设备、图像库和平台能力 | [platform](../src/game_automation/platform/)、[dry-run](../src/game_automation/portable/adapters/dry_run.py) |
| 装配 | 选择平台实现，向用例注入 factory | [composition.py](../src/game_automation/platform/local_desktop/composition.py) |
| 入口 | 解析 CLI/HTTP 输入，调用用例，转换展示格式 | [entrypoints](../src/game_automation/platform/local_desktop/entrypoints/) |

依赖方向比目录名称更重要：领域对象不访问设备；执行层不创建真实 adapter；平台细节留在 adapter。
具体任务的点位、模板和步骤由脚本表达；任务编写取舍见 [ADR 0001](adr/0001-agent-authored-tasks.md)。

## 当前主链路与装配

CLI 单脚本链路：

```text
cli → 项目 catalog / 共享资源 → run_script_on_local_desktop
    → run_script → ScriptRunner → 已注入的输入、识图与状态 ports
```

控制台链路：

```text
local_ui → 已装配的 LocalControlApplication → 后台运行会话
         → run_script → ScriptRunner → 相同的运行 ports
```

[run_script](../src/game_automation/portable/application/script_run.py) 按脚本需求创建运行依赖，并在真实执行前准备目标应用与窗口。
[run_script_plan](../src/game_automation/portable/application/run_plan.py) 编排已有脚本及停止策略，单份脚本仍交给注入的运行函数。
[ProjectScreenStateReader](../src/game_automation/portable/application/screen_state_reader.py) 直接连接配置与识图 port；状态读取不反向装配控制台。
新增入口复用这些用例；保持控制台聚焦运行与停止的理由见 [ADR 0004](adr/0004-small-console.md)。

## Port 归属与副作用

Port 的接口由消费它的核心职责决定，adapter 负责实现；新增接缝先确定调用方需要知道什么。
[engine ports](../src/game_automation/portable/engine/ports.py) 声明执行所需的输入、取色、识图、状态、日志和取消能力。
[application ports](../src/game_automation/portable/application/ports.py) 声明运行前激活应用、选择窗口等环境能力。
现有坐标记录工具也从 engine ports 使用指针和按键 reader；工具读取按键与模拟键盘输出各有职责。

- `InputDevice` 负责原子输入；组合键的按下、释放和失败清理由 adapter 一次完成。
- `ScriptRunner` 负责动作顺序、条件与循环作用域；不持有平台按键状态。
- 识图 adapter 隐藏截图、物理像素换算、模板读取和底层库错误。
- 装配以 factory 延迟创建真实能力；普通查询和 dry-run 保持其声明的无桌面副作用边界。

端口变化同时核对调用方、真实 adapter、dry-run 和 fake 的行为契约。
仅为透传而增加一层接口前，先判断它是否收拢了调用顺序、错误结果或稳定规则。

## 运行状态与取消的所有权

[Script](../src/game_automation/portable/domain/script.py) 保存不可变的执行输入；运行结果和会话状态存放在它之外。
[LocalControlApplication](../src/game_automation/portable/application/local_control.py) 拥有当前后台会话、线程安全日志和取消标记。
入口请求停止时设置标记，执行器通过 `CancellationToken` 在执行边界读取；adapter 不决定脚本的循环策略。
取消的检查时机和响应限制属于当前行为，详见 [项目现状](current-state.md)，不把“立即停止”作为未验证的保证。

循环中断属于该层 `Repeat` 的执行作用域，嵌套层按作用域传播；它与整脚本取消分别处理。
[状态 reader](../src/game_automation/portable/application/screen_state_reader.py) 每次读取最新配置与画面，返回本轮状态；运行条件不依赖 UI 中缓存的显示结果。
日志与步骤事件描述已发生的执行，展示层消费这些记录；它们不作为驱动脚本的第二套状态机。
局部恢复、重试和子任务的讨论不改变现有契约；是否实现及具体语义以当前决策和代码为准。

## JSON、领域对象与资源

[JSON loader](../src/game_automation/portable/application/config_script_loader.py) 将文件结构转换为标准 `Script`、步骤和资源对象。
它负责字段解析、文件格式错误和资源路径解析；领域类型负责可复用的不变量，执行器负责步骤语义。
CLI 和 HTTP 入口不自行解释 JSON 步骤，也不为某个游戏增加 runner 分支。

[项目 catalog](../src/game_automation/portable/application/project_scripts.py) 合并命名脚本、隔离坏文件并报告错误，注册过程不执行步骤。
[共享资源合并](../src/game_automation/portable/application/script_resources.py) 保留脚本局部资源的同名覆盖权，避免入口重复实现资源优先级。
JSON 只是现有脚本入口之一；领域能力是否已开放到 JSON，须核对 loader 与 [项目现状](current-state.md)。
新增文件语法优先映射已有领域对象；确有新执行含义时，先明确公开行为，再修改对应规则和入口。

## 窗口与坐标边界

[Window](../src/game_automation/portable/domain/windows.py) 负责点位和搜索区域的坐标解析；真实窗口发现与激活由 application port 和平台 adapter 完成。
运行前选窗得到的范围用于本次脚本副本，不修改 catalog 中的脚本定义。
脚本点位、图片匹配结果、显示像素和实际输入坐标要在对应边界转换，调用方应明确自己使用的坐标系。
窗口移动、状态识别区域及入口能力差异的当前限制记录在 [项目现状](current-state.md)；它们不是需要永久保留的架构规则。

## 结果与验证边界

执行层报告是否按所选分支与循环规则正常结束及停止原因，应用层将运行结果映射为入口可用的结果。
判断完成同时看 `finish_reason` 和退出码；正常停止可能返回 `0`，动作已发送也不等于业务目标已经达成。
结果对象与验证证据的取舍见 [ADR 0003](adr/0003-results-and-verification.md)。

[视觉靶场](../src/star_visual_lab/) 是独立目标应用；Star 通过像素和输入操作它，验收程序再读取真值 API。
核心规则用 fake 验证，入口验证用户可见映射，真实桌面按需 smoke；证据不能由自己的成功日志替代。
重点边界可从 [runner](../tests/test_runner.py)、[运行用例](../tests/test_script_run.py)、[控制台用例](../tests/test_local_control.py) 和 [装配](../tests/test_local_desktop_composition.py) 测试进入。

## 常见需求落点与重审信号

| 需求 | 优先落点 | 需要重审的越界做法 |
| --- | --- | --- |
| 某任务增加点击、等待或模板 | 脚本与 assets，复用现有步骤 | 在 runner 中判断游戏或任务名称 |
| 确认新增通用动作或控制语义 | 领域类型、执行规则；按需补 loader 与 adapter | 在 CLI/JS 中拼出另一套执行器 |
| 增加平台输入或窗口能力 | 对应 adapter 与 composition；必要时调整消费方 port | 让 portable 层导入平台库或系统命令 |
| 增加入口或调整展示 | 入口映射及已有 application 用例 | 用页面显示状态替代执行时读取 |
| 调整运行结果或停止策略 | 负责该层编排的 runner / application | 从退出码 `0` 推断业务完成 |

规则重复、修改一个行为需同步多个入口、或测试被迫读取内部细节时，先重新确认职责归属。
局部重构应收拢本轮触达的复杂度；接口只少一层转发时，检查能否直接使用已有能力。
跨模块的重要取舍写入 [ADR](adr/README.md)，现状和限制更新到 current-state；文档分工见 [ADR 0005](adr/0005-repository-documentation.md)。
