# game-script-kit

一个用于练习跨平台游戏脚本架构的 Python 项目。

目标是把游戏脚本的核心业务逻辑和平台相关输入设备实现分开：脚本只描述要执行的动作，adapter 负责把动作落到 macOS、Windows、模拟器或其他平台。

## 当前能力

- 使用 `Script` 表达一组按顺序执行的动作。
- 支持第一版动作模型：`Click`、`Drag`、`Wait`。
- 脚本绑定单个窗口，脚本内点击和拖拽都在该窗口坐标系内执行。
- 支持两类窗口：
  - `ScreenWindow`：点坐标直接视为屏幕坐标。
  - `AreaWindow(Rect(...))`：点坐标按区域左上角偏移解析为屏幕坐标。
- 通过 `InputDevice` 端口隔离平台输入实现。
- 提供 macOS `pyautogui` adapter 和 dry-run demo。

## 代码结构

```text
src/game_automation/
├── core/
│   ├── actions.py        # Click / Drag / Wait
│   ├── geometry.py       # Point / Rect
│   ├── windows.py        # ScreenWindow / AreaWindow
│   ├── script.py         # Script
│   ├── runner.py         # ScriptRunner
│   └── ports.py          # InputDevice
├── adapters/
│   └── macos.py          # macOS pyautogui adapter
└── cli.py                # demo CLI
```

OpenSpec 规格和已归档变更放在 `openspec/`。

## 安装

项目当前要求 Python 3.14。

```bash
cd /path/to/game-script-kit
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## 运行 dry-run

dry-run 只打印脚本动作，不会移动真实鼠标。

```bash
.venv/bin/python -m game_automation.cli --dry-run
```

示例输出：

```text
RecordedOperation(name='click', target=Point(x=300, y=300), start=None, end=None, duration_seconds=None)
RecordedOperation(name='drag_to', target=None, start=Point(x=300, y=300), end=Point(x=460, y=360), duration_seconds=0.4)
```

## 运行 macOS demo

macOS demo 会真的移动和点击鼠标。

```bash
.venv/bin/python -m game_automation.cli --macos
```

运行前确认：

- 已安装依赖。
- 终端或 Python 运行时已在 macOS 系统设置中获得“辅助功能”权限。
- demo 坐标适合当前屏幕，避免点到危险位置。

## 使用核心模型

```python
from game_automation.core import (
    AreaWindow,
    Click,
    Drag,
    Point,
    Rect,
    Script,
    ScriptRunner,
    Wait,
)

script = Script(
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
