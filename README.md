# game-script-kit

一个用于练习跨平台游戏脚本架构的 Python 项目。

目标是把游戏脚本的核心业务逻辑和平台相关输入设备实现分开：脚本只描述要执行的动作，adapter 负责把动作落到 macOS、Windows、模拟器或其他平台。

## 当前能力

- 使用带名称的 `Script` 表达一组按顺序执行的动作。
- 支持第一版动作模型：`Click`、`Drag`、`Wait`。
- 脚本绑定单个窗口，脚本内点击和拖拽都在该窗口坐标系内执行。
- 支持两类窗口：
  - `ScreenWindow`：点坐标直接视为屏幕坐标。
  - `AreaWindow(Rect(...))`：点坐标按区域左上角偏移解析为屏幕坐标。
- 通过 `InputDevice` 端口隔离平台输入实现。
- 提供 macOS `pyautogui` adapter 和 dry-run demo。
- 提供独立坐标记录工具，用于采集屏幕绝对坐标。
- 提供命名脚本管理入口，可列出脚本并通过脚本名称启动。

## 代码结构

```text
src/game_automation/
├── domain/              # 纯领域数据模型
│   ├── actions.py       # Click / Drag / Wait
│   ├── geometry.py      # Point / Rect
│   ├── windows.py       # ScreenWindow / AreaWindow
│   └── script.py        # Script
├── engine/               # 脚本执行引擎
│   ├── ports.py          # InputDevice / PointerPositionReader / KeyStateReader
│   └── runner.py         # ScriptRunner
├── scripts_manager/      # 脚本定义与注册管理
│   ├── demo.py
│   ├── recorded_clicks.py
│   └── catalog.py        # ScriptCatalog + DEFAULT_SCRIPT_CATALOG
├── adapters/             # 平台适配与模拟设备（实现 engine.ports）
│   ├── desktop/
│   │   ├── pointer_position.py
│   │   └── terminal_keyboard.py
│   ├── macos/
│   │   └── pointer_device.py
│   └── dry_run.py        # DryRunInputDevice / RecordedOperation
├── tools/
│   └── coordinate_recorder.py # 坐标记录工具核心循环
├── script_cli.py         # 按名称列出和运行脚本
└── coordinate_recorder_cli.py # 坐标记录工具 CLI
```

OpenSpec 规格和已归档变更放在 `openspec/`。

## 安装

项目当前要求 Python 3.14。

```bash
cd /path/to/game-script-kit
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## 列出和运行命名脚本

推荐使用 `game-scripts` 统一管理脚本。脚本定义放在 `src/game_automation/scripts_manager/`，默认注册表在 `src/game_automation/scripts_manager/catalog.py`。

列出当前可用脚本：

```bash
.venv/bin/game-scripts list
```

按名称 dry-run，先检查顺序：

```bash
.venv/bin/game-scripts run demo --dry-run
.venv/bin/game-scripts run recorded-clicks --dry-run
```

确认无误后直接运行。`run` 默认使用 macOS adapter，所以不需要输入 `--macos`：

```bash
.venv/bin/game-scripts run recorded-clicks
```

运行前确认：

- 已安装依赖。
- 终端或 Python 运行时已在 macOS 系统设置中获得“辅助功能”权限。
- 脚本坐标适合当前屏幕，避免点到危险位置。

## 新增或编辑脚本

第一版脚本定义使用 Python 文件，方便直接复用 `Click`、`Drag`、`Wait`、`ScreenWindow` 和 `AreaWindow`。

新增脚本的最小流程：

1. 在 `src/game_automation/scripts_manager/<script_name>.py` 新增一个 `Script(name="<script-name>", ...)`。
2. 在 `src/game_automation/scripts_manager/catalog.py` 把它加入 `DEFAULT_SCRIPT_CATALOG`。
3. 运行 `.venv/bin/game-scripts list` 确认脚本名称可见。
4. 运行 `.venv/bin/game-scripts run <script-name> --dry-run` 检查动作顺序。

编辑已有脚本时，直接修改 `src/game_automation/scripts_manager/` 下对应文件里的动作序列，不需要修改 runner 或平台 adapter。

## 运行 demo dry-run

通过统一入口 dry-run 检查 demo 脚本动作：

```bash
.venv/bin/game-scripts run demo --dry-run
```

## 记录鼠标坐标

坐标记录工具是独立工具，不走 `ScriptRunner`，也不会创建脚本动作。它记录的是屏幕绝对坐标。

```bash
.venv/bin/game-coordinate-recorder
```

交互方式：

- 每 1 秒打印一次当前鼠标坐标。
- 每 50ms 检查一次按键状态。
- 按 `1` 时立即重新读取当前鼠标坐标并记录。
- 按 `Q` 或 `q` 结束。
- 结束后打印本次记录的所有坐标。

运行前确认：

- 已安装依赖。
- 终端窗口保持焦点；默认按键 adapter 从当前终端读取 `1` 和 `Q/q`，不使用全局键盘监听。
- 终端或 Python 运行时可能仍需要系统允许读取鼠标位置。
- `1` 和 `Q/q` 需要正常按下，极短瞬时敲击可能被 50ms 轮询错过。

## 运行已记录点击脚本

这个脚本会按顺序执行：等待 3 秒，点击 `(242, 92)`，等待 3 秒，点击 `(736, 323)`，等待 10 秒，点击 `(741, 400)` 后结束。

```bash
.venv/bin/game-scripts run recorded-clicks --dry-run
.venv/bin/game-scripts run recorded-clicks
```

## 使用核心模型

```python
from game_automation.domain import (
    AreaWindow,
    Click,
    Drag,
    Point,
    Rect,
    Script,
    Wait,
)
from game_automation.engine.runner import ScriptRunner

script = Script(
    name="sample-clicks",
    window=AreaWindow(Rect(left=100, top=200, width=800, height=600)),
    actions=(
        Click(Point(10, 20)),
        Drag(Point(30, 40), Point(50, 60), duration_seconds=0.4),
        Wait(0.2),
    ),
)

ScriptRunner(device).run(script)
```

坐标解析规则：

- `ScreenWindow.resolve(Point(x, y)) -> Point(x, y)`
- `AreaWindow(Rect(left, top, width, height)).resolve(Point(x, y)) -> Point(left + x, top + y)`
- 第一版不做边界夹取。

## 测试

```bash
.venv/bin/python -m pytest
```

## 项目状态

这是一个早期实验项目，当前重点是领域模型和 port-and-adapter 边界。循环、条件判断、图像识别、OCR、脚本文件格式、多窗口编排和自动窗口查找都还没有实现。
