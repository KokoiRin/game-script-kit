## Context

当前项目已经有 `Point` 领域模型和 port-and-adapter 结构，但用户在编写脚本前还需要一个简单方式采集真实屏幕坐标。这个能力更像开发辅助工具，而不是脚本执行核心能力，因此应复用现有架构思想，但和现有 `Script`、`ScriptRunner`、demo 流程分离。

第一版工具只做最小交互：实时读取鼠标当前位置，每 1 秒打印一次；以更短间隔检查按键；按 `1` 时立即重新读取并记录当前坐标；按 `Q` 或 `q` 时立即结束；结束后打印记录的所有坐标。

## Goals / Non-Goals

**Goals:**

- 提供一个单独坐标记录工具入口。
- 每 1 秒打印当前鼠标坐标。
- 以较短间隔检查按键状态，默认按键检测间隔为 50ms。
- 按 `1` 时立即重新读取当前坐标并记录，记录值使用现有 `Point` 模型表达。
- 按 `Q` 或 `q` 时立即结束，并在结束后打印所有记录坐标。
- 工具实现与现有脚本 runner、demo CLI 和输入设备 adapter 流程分离。
- 定义坐标读取和按键状态读取 port，由平台 adapter 实现真实读取逻辑。
- 将坐标读取、按键监听、时间等待和输出做成可注入依赖，便于测试。

**Non-Goals:**

- 不生成脚本文件或自动插入 `Click` / `Drag` 动作。
- 不做窗口坐标转换；第一版记录屏幕绝对坐标。
- 不支持复杂快捷键、鼠标点击记录、录制拖拽轨迹或 GUI。
- 不新增 `GetCoordinate` / `RecordCoordinate` 脚本 action。
- 不改变 `Script`、`ScriptRunner`、`InputDevice` 或 macOS adapter 的行为。

## Decisions

### 实现落点

实现时按下面的文件和职责拆分：

```text
src/game_automation/
├── core/
│   └── ports.py
├── tools/
│   ├── __init__.py
│   └── coordinate_recorder.py
├── adapters/
│   └── desktop/
│       ├── pointer_position.py
│       └── terminal_keyboard.py
└── coordinate_recorder_cli.py
```

`core/ports.py` 放跨平台读取端口：

- `PointerPositionReader`：定义 `current_position() -> Point`
- `KeyStateReader`：定义 `is_pressed(key: str) -> bool`

`tools/coordinate_recorder.py` 放工具应用服务：

- `CoordinateRecorder`：实现循环、打印、记录、退出和最终汇总
- `RecordedCoordinateSession` 或简单 `list[Point]`：保存本次记录结果

`adapters/desktop/pointer_position.py` 放桌面通用鼠标坐标读取：

- `PyAutoGuiPointerPositionReader.current_position()` 调用 `pyautogui.position()` 并转换为 `Point`

`adapters/desktop/terminal_keyboard.py` 放终端按键状态读取：

- `TerminalKeyStateReader.is_pressed(key)` 从当前交互终端读取按键事件
- 终端不可交互或运行环境不支持时，包装成清晰的 setup 错误

`coordinate_recorder_cli.py` 只负责组装真实 adapter、启动 `CoordinateRecorder`，并在退出时恢复终端输入模式，不放循环业务逻辑。

理由：这个拆法让工具核心可以用 fake reader 测试，也让真实平台读取能力保持在 adapter 层。CLI 只负责组装，避免把交互循环写成不可测脚本。

### 独立 tools 模块和单独 CLI 入口

新增工具模块，例如 `game_automation.tools.coordinate_recorder`，并提供单独命令入口，例如 `game-coordinate-recorder`。现有 `game_automation.cli` demo 不承载这个交互工具。

理由：坐标采集是脚本编写辅助能力，不是脚本执行流程的一部分。单独入口可以避免 demo CLI 越来越杂，也能让后续工具继续独立扩展。

备选方案：把坐标记录作为 `game_automation.cli` 的一个参数。这个方案实现较快，但会把 demo 和开发辅助工具混在一起，边界不清。

### 复用 Point，但不新增脚本 Action

工具读取和记录的坐标使用 `Point` 表达，但不会创建 `Script` 或 `Action`。第一版不新增 `GetCoordinate`、`RecordCoordinate` 或类似脚本动作。

理由：现有 `Action` 表达脚本对游戏执行的动作，例如点击、拖拽和等待；获取坐标是开发工具从外部环境读取状态，不是脚本对游戏执行的动作。把它建成脚本 action 会混淆“执行动作”和“采集辅助信息”。

备选方案：新增 `GetCoordinate` action 并由 adapter 执行。这个方案看似统一，但会让 `ScriptRunner` 开始处理返回值和交互式记录状态，破坏当前脚本“一次性按顺序执行动作”的简单模型。后续如果脚本需要读取屏幕状态，应单独设计 observation/query 能力，而不是把开发工具动作塞进第一版 action 集合。

### 使用坐标读取 port 和平台 adapter

在 `core/ports.py` 新增一个坐标读取端口，例如 `PointerPositionReader.current_position() -> Point`。坐标记录工具依赖该端口获取当前鼠标屏幕坐标；真实平台实现放在 adapter 层，例如 macOS/桌面实现通过 `pyautogui.position()` 转为 `Point`。

理由：这沿用已有 port-and-adapter 思路：工具核心只关心“能拿到一个 Point”，不直接依赖 `pyautogui`。平台差异和权限问题被隔离在 adapter 中。

备选方案：在工具循环中直接调用 `pyautogui.position()`。这个方案更短，但会让工具核心依赖平台库，测试也更难。

调用方向固定为：

```text
CoordinateRecorder
  -> PointerPositionReader.current_position()
  -> Point
```

工具不会反向调用 `InputDevice`，也不会通过 `ScriptRunner` 执行。

### 使用按键状态 port 和平台 adapter

在 `core/ports.py` 新增一个按键状态读取端口，例如 `KeyStateReader.is_pressed(key: str) -> bool`。坐标记录工具用它判断 `1`、`q`、`Q` 是否按下；真实实现放在 adapter 层，并包装终端不可交互或运行环境限制。

理由：键盘监听和鼠标坐标读取一样属于外部环境读取能力，应放在 adapter 后面。这样工具循环可以用 fake key reader 测试长按去重和退出逻辑。

备选方案：直接使用第三方键盘库回调。这个方案响应更快，但第一版不需要复杂事件模型，且 macOS 全局键盘监听权限和测试复杂度更高。

### 工具核心是应用服务，不是脚本 runner

新增 `CoordinateRecorder` 或类似应用服务，组合 `PointerPositionReader`、`KeyStateReader`、`Sleeper` 和输出函数。它负责循环、打印当前坐标、记录坐标和结束后汇总。应用服务应支持两个节奏参数：`display_interval_seconds=1.0` 和 `poll_interval_seconds=0.05`。

理由：这个工具虽然复用 port-and-adapter，但它不是常规脚本，不应该通过 `ScriptRunner` 执行。单独应用服务能保持职责清楚。

备选方案：复用 `ScriptRunner`。这个方案会迫使 runner 支持交互式循环、读取返回值和工具状态，和现有脚本执行模型不匹配。

核心循环可以按下面的状态执行：

```text
recorded = []
was_record_pressed = False
last_display_at = monotonic()

while True:
    now = monotonic()
    if now - last_display_at >= display_interval_seconds:
        point = pointer_reader.current_position()
        output(f"current: {point}")
        last_display_at = now

    record_pressed = key_reader.is_pressed("1")
    if record_pressed and not was_record_pressed:
        point = pointer_reader.current_position()
        recorded.append(point)
        output(f"recorded: {point}")
    was_record_pressed = record_pressed

    if key_reader.is_pressed("q") or key_reader.is_pressed("Q"):
        break

    sleeper(poll_interval_seconds)

output all recorded points
```

这里有两个关键状态：`was_record_pressed` 用于避免长按 `1` 时重复记录；`last_display_at` 用于让坐标打印保持 1 秒节奏，而不影响更高频的按键检测。

### 使用可注入运行循环依赖

核心循环依赖四类接口：坐标读取 port、按键状态 port、等待函数、输出函数。真实 CLI 使用平台 adapter 和标准输出；测试使用 fake 实现。

理由：实时键盘监听和鼠标位置读取在测试环境中不稳定，可注入依赖能让循环逻辑可测，也能避免单元测试真的读取鼠标或键盘。

备选方案：直接在循环里调用第三方库。这个方案代码短，但测试难写，也容易在无权限环境失败。

### 分离坐标打印节奏和按键检测节奏

工具使用轮询式按键检测，但将坐标打印节奏和按键检测节奏分离。坐标打印默认每 1 秒执行一次；按键检测默认每 50ms 执行一次。检测到 `1` 的按下边沿时，工具立即重新读取当前鼠标坐标并记录；检测到 `Q/q` 时，工具立即退出循环。

理由：如果每 1 秒才检查一次按键，用户按键可能被漏掉或响应迟钝。分离两个节奏后，屏幕输出仍保持简洁，按键响应会更接近实时。记录时重新读取坐标可以保证记录的是按键发生时的最新坐标，而不是上一次显示时的旧坐标。

备选方案：事件回调式键盘监听。这个方案响应更快，但实现和权限差异更复杂。

## Risks / Trade-offs

- 默认按键 adapter 读取当前终端输入，因此运行时终端需要保持焦点；这避免第一版依赖 macOS 全局键盘监听权限。
- 50ms 按键轮询仍可能错过极短按键 → 第一版接受该限制，并在 README 提示按键需正常按下而不是瞬时敲击。
- 更高频轮询会增加少量 CPU 消耗 → 默认 50ms 是响应速度和资源占用之间的折中。
- 读取屏幕绝对坐标不适合直接用于区域窗口脚本 → README 或输出说明中提示当前记录的是屏幕坐标。
- 终端按键读取仍有平台差异 → 把真实实现隔离在工具 adapter 层，核心循环用可注入接口测试。
- 把坐标读取做成脚本 action 会污染脚本模型 → 第一版只新增读取坐标 port 和工具应用服务，不修改 `Action` 集合。
