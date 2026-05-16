# Game Automation Demo

这是一个小型游戏脚本架构 demo，用来演示如何把稳定的业务 workflow 和平台相关的设备控制分离。

## 结构

- `game_automation.core`: 平台无关的输入设备契约、数据类型、demo workflow。
- `game_automation.adapters`: 平台相关 adapter，目前包含 macOS Python 鼠标指针 adapter。
- `game_automation.cli`: demo 入口，负责选择 dry-run 或 macOS adapter。

## 运行 dry-run

```bash
python -m game_automation.cli --dry-run
```

dry-run 使用 fake 输入设备，只打印 workflow 请求的鼠标指针操作，不会移动真实鼠标。

## 运行 macOS 鼠标 demo

```bash
python -m game_automation.cli --macos
```

macOS 模式使用 `pyautogui` 模拟鼠标移动、点击和拖动。运行前需要：

- 安装 Python 3.14，并创建虚拟环境：`/opt/homebrew/bin/python3 -m venv .venv`
- 安装依赖：`.venv/bin/python -m pip install -e ".[dev]"`
- 在 macOS 系统设置中为运行 Python 的终端授予辅助功能权限。
- 确认 demo 坐标适合当前屏幕。多显示器和显示缩放可能影响坐标位置。

这个 demo 只验证框架边界，不承诺兼容具体游戏客户端。
