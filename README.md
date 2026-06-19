# game-script-kit

一个用于练习跨平台游戏脚本架构的 Python 项目。

目标是把游戏脚本的核心业务逻辑和平台相关输入设备实现分开：脚本只描述要执行的步骤，adapter 负责把原子动作步骤落到 macOS、Windows、模拟器或其他平台。

## 当前能力

- 使用带名称的 `Script` 表达一组按顺序执行的步骤。
- 支持原子动作步骤：`Click`、`Drag`、`Wait`。
- 支持固定次数重复步骤：`Repeat(times, steps)`。
- 支持颜色条件分支：`If(ColorIs(...), then_steps, else_steps)`。
- 支持颜色条件等待：`WaitUntil(ColorIs(...), timeout_seconds, interval_seconds)`。
- 支持图片存在条件等待：`WaitUntil(ImageExists(...), timeout_seconds, interval_seconds)`。
- 脚本绑定单个窗口，脚本内点击和拖拽都在该窗口坐标系内执行。
- 支持两类窗口：
  - `ScreenWindow`：点坐标直接视为屏幕坐标。
  - `AreaWindow(Rect(...))`：点坐标按区域左上角偏移解析为屏幕坐标。
- 通过 `InputDevice` 端口隔离平台输入实现。
- 通过 `ScreenImageLocator` 端口隔离屏幕图像匹配实现。
- 提供 macOS `pyautogui` adapter 和 dry-run demo。
- 提供独立坐标记录工具，用于采集屏幕绝对坐标。
- 提供命名脚本管理入口，可列出脚本并通过脚本名称启动。
- 提供本地控制 UI，可在浏览器窗口中选择脚本、运行 dry-run 和触发固定测试任务。

## 代码结构

```text
src/game_automation/
├── portable/             # 跨平台可复用核心
│   ├── domain/           # 纯领域数据模型：Click / Wait / If / WaitUntil / ColorIs / ImageMatch
│   ├── engine/           # 脚本执行引擎和运行能力 ports
│   ├── scripts_manager/  # 脚本定义与注册管理
│   ├── application/      # 用例编排：脚本运行、本地 UI 控制
│   ├── adapters/         # 不绑定具体平台的 adapter，例如 dry-run
│   └── tools/            # 可复用工具核心，例如坐标记录循环
├── platform/             # 平台相关实现，迁移平台时优先替换这里
│   ├── desktop/          # 桌面通用 adapter：取色、鼠标位置、终端按键
│   ├── macos/            # macOS 专用输入 adapter
│   └── local_desktop/    # 本机 CLI/UI 入口和 adapter composition
└── __init__.py           # 顶层包元信息
```

迁移到新平台时，优先保留 `portable/`，替换或重接 `platform/`。旧的 `game_automation.domain`、`game_automation.engine`、`game_automation.adapters` 等导入路径已经移除，新代码统一使用 `game_automation.portable.*` 或 `game_automation.platform.*`。

OpenSpec 规格和已归档变更放在 `openspec/`。

## 安装

项目当前要求 Python 3.14。

```bash
cd /path/to/game-script-kit
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## 列出和运行命名脚本

推荐使用 `star` 统一管理脚本。脚本定义放在 `src/game_automation/portable/scripts_manager/`，默认注册表在 `src/game_automation/portable/scripts_manager/catalog.py`。

列出当前可用脚本：

```bash
.venv/bin/star list
```

按名称 dry-run，先检查顺序：

```bash
.venv/bin/star run demo --dry-run
.venv/bin/star run recorded-clicks --dry-run
```

确认无误后直接运行。`run` 默认使用 macOS adapter，所以不需要输入 `--macos`：

```bash
.venv/bin/star run recorded-clicks
```

运行前确认：

- 已安装依赖。
- 终端或 Python 运行时已在 macOS 系统设置中获得“辅助功能”权限。
- 脚本坐标适合当前屏幕，避免点到危险位置。

## 本地控制 UI

启动本地 UI，默认打开浏览器窗口：

```bash
.venv/bin/star ui
```

测试或手动指定地址时，可以只启动服务不自动打开窗口：

```bash
.venv/bin/star ui --host 127.0.0.1 --port 8765 --no-open
```

打开 `http://127.0.0.1:8765/` 后，可以选择脚本、勾选或取消“模拟运行”、输入模拟颜色并查看输出。“运行测试”按钮只运行项目内置的固定测试任务，不接受任意 shell 命令。

UI 也提供图片点击路径：把 `.png`、`.jpg`、`.jpeg` 或 `.webp` 模板图片放到项目根目录 `assets/` 下，点击“刷新图片”，选择目标图片和最低置信度后点击“查找并点击图片”。模拟运行会把所选图片视为已找到并打印计划点击；真实运行会使用 OpenCV 在当前屏幕中查找该图片并点击匹配区域中心点。

端到端 smoke 方法：

```bash
.venv/bin/star ui --host 127.0.0.1 --port 8765 --no-open
curl http://127.0.0.1:8765/api/scripts
curl -X POST http://127.0.0.1:8765/api/run-script \
  -H 'Content-Type: application/json' \
  -d '{"name":"conditional-color-demo","dry_run":true,"dry_run_color":"#102030"}'
curl http://127.0.0.1:8765/api/image-assets
curl -X POST http://127.0.0.1:8765/api/click-image \
  -H 'Content-Type: application/json' \
  -d '{"asset":"start.png","dry_run":true,"min_confidence":0.8}'
```

自动化测试：

```bash
.venv/bin/python -m pytest tests/test_local_control.py tests/test_local_control_ui.py tests/test_script_cli.py
```

## 新增或编辑脚本

第一版脚本定义使用 Python 文件，方便直接复用 `Click`、`Drag`、`Wait`、`ScreenWindow` 和 `AreaWindow`。

新增脚本的最小流程：

1. 在 `src/game_automation/portable/scripts_manager/<script_name>.py` 新增一个 `Script(name="<script-name>", ...)`。
2. 在 `src/game_automation/portable/scripts_manager/catalog.py` 把它加入 `DEFAULT_SCRIPT_CATALOG`。
3. 运行 `.venv/bin/star list` 确认脚本名称可见。
4. 运行 `.venv/bin/star run <script-name> --dry-run` 检查步骤执行顺序。

编辑已有脚本时，直接修改 `src/game_automation/portable/scripts_manager/` 下对应文件里的步骤序列，不需要修改 runner 或平台 adapter。

## 运行 demo dry-run

通过统一入口 dry-run 检查 demo 脚本步骤：

```bash
.venv/bin/star run demo --dry-run
```

## 验证颜色条件分支和条件等待

`conditional-color-demo` 使用 `If(ColorIs(...))`。默认 dry-run 颜色为 `#000000`，会走 else 分支；指定匹配颜色 `#102030` 会走 then 分支：

```bash
.venv/bin/star run conditional-color-demo --dry-run
.venv/bin/star run conditional-color-demo --dry-run --dry-run-color '#102030'
```

`wait-until-color-demo` 使用 `WaitUntil(ColorIs(...), timeout_seconds=1, interval_seconds=0.5)`。指定匹配颜色会立即通过并点击；默认颜色不匹配，会打印两次等待并以非零退出码报告超时：

```bash
.venv/bin/star run wait-until-color-demo --dry-run --dry-run-color '#102030'
.venv/bin/star run wait-until-color-demo --dry-run
```

## 图片存在条件、图片目标点击和屏幕图像匹配

当前已经提供平台无关的屏幕图像匹配 seam，并接入 `ImageExists(...)` 条件和 `Click(ImageTarget(...))` 图片目标点击。第一版能力包括：

- `ImageTemplate(path)` 表达待查找模板图片。
- `ImageMatch(rect, confidence)` 表达匹配区域、中心点和置信度。
- `ImageExists(template, region=None, min_confidence=1.0)` 表达图片存在条件。
- `ImageTarget(template, region=None, min_confidence=1.0, offset=Point(0, 0))` 表达按图片匹配中心点点击的目标。
- `ScreenImageLocator.locate(template, region=None, min_confidence=1.0)` 在当前屏幕或指定区域内查找模板。
- `PyAutoGuiScreenImageLocator` 是本地桌面 adapter，延迟加载 `pyautogui`、OpenCV 和 numpy，并隐藏截图、模板读取和平台依赖错误；在 Retina 屏幕上会把截图物理像素坐标转换成鼠标可点击坐标。
- `DryRunScreenImageLocator` 可在测试或 dry-run 路径中返回预设匹配结果。

`wait-until-image-demo` 使用 `WaitUntil(ImageExists(ImageTemplate("assets/start.png")), timeout_seconds=1, interval_seconds=0.5)`。默认 dry-run 不配置图片，条件会超时；指定匹配模板路径会立即通过并点击：

```bash
.venv/bin/star run wait-until-image-demo --dry-run
.venv/bin/star run wait-until-image-demo --dry-run --dry-run-image assets/start.png
```

`click-image-demo` 使用 `Click(ImageTarget(ImageTemplate("assets/start.png")))`。默认 dry-run 不配置图片，会报告目标未找到；指定匹配模板路径会点击匹配区域中心点：

```bash
.venv/bin/star run click-image-demo --dry-run
.venv/bin/star run click-image-demo --dry-run --dry-run-image assets/start.png
```

示例：

```python
from game_automation.portable.domain import ImageExists, ImageTarget, ImageTemplate, Point, Rect

condition = ImageExists(
    ImageTemplate("assets/start-button.png"),
    region=Rect(left=0, top=0, width=800, height=600),
    min_confidence=1.0,
)

target = ImageTarget(
    ImageTemplate("assets/start-button.png"),
    region=Rect(left=0, top=0, width=800, height=600),
    min_confidence=1.0,
    offset=Point(0, 8),
)
```

macOS 真实运行前确认：

- 终端或 Python 运行时已获得“屏幕录制”权限。
- 真实点击还需要终端或 Python 运行时已获得“辅助功能”权限。
- 模板图片路径存在且适合当前缩放、主题和分辨率。
- 尽量提供 `region` 缩小搜索范围，避免全屏模板匹配过慢。
- `min_confidence < 1.0` 走 OpenCV 置信度匹配；项目运行依赖已声明 `opencv-python-headless`。

注意：当前只支持把首个匹配区域中心点解析为点击坐标；拖拽图片目标、多匹配选择、截图录制和脚本文件格式仍未接入。

## 记录鼠标坐标和颜色

坐标记录工具是独立工具，不走 `ScriptRunner`，也不会创建脚本步骤。它读取的是屏幕绝对坐标，以及该坐标点当前的 RGB 颜色。

```bash
.venv/bin/star recorder
```

交互方式：

- 每 1 秒打印一次当前鼠标坐标和该点颜色。
- 每 50ms 检查一次按键状态。
- 按 `1` 时立即重新读取当前鼠标坐标和该点颜色并记录。
- 按 `Q` 或 `q` 结束。
- 结束后打印本次记录的所有坐标和对应颜色。

输出示例：

```text
current: Point(x=242, y=92) #78828C
recorded: Point(x=242, y=92) #78828C
recorded points:
1. Point(x=242, y=92) #78828C
```

运行前确认：

- 已安装依赖。
- 终端窗口保持焦点；默认按键 adapter 从当前终端读取 `1` 和 `Q/q`，不使用全局键盘监听。
- 终端或 Python 运行时可能仍需要系统允许读取鼠标位置。
- macOS 可能需要给终端或 Python 运行时授予“屏幕录制”权限，否则截图取色会失败。
- `1` 和 `Q/q` 需要正常按下，极短瞬时敲击可能被 50ms 轮询错过。

## 运行已记录点击脚本

这个脚本会按顺序执行：等待 3 秒，点击 `(242, 92)`，等待 3 秒，点击 `(736, 323)`，等待 10 秒，点击 `(741, 400)` 后结束。

```bash
.venv/bin/star run recorded-clicks --dry-run
.venv/bin/star run recorded-clicks
```

## 使用核心模型

```python
from game_automation.portable.domain import (
    AreaWindow,
    Click,
    Color,
    ColorIs,
    Drag,
    If,
    Point,
    Rect,
    Repeat,
    Script,
    Wait,
    WaitUntil,
)
from game_automation.portable.engine.runner import ScriptRunner

script = Script(
    name="sample-clicks",
    window=AreaWindow(Rect(left=100, top=200, width=800, height=600)),
    steps=(
        Click(Point(10, 20)),
        Repeat(
            times=3,
            steps=(
                Drag(Point(30, 40), Point(50, 60), duration_seconds=0.4),
                Wait(0.2),
            ),
        ),
        WaitUntil(
            condition=ColorIs(Point(60, 70), Color.from_hex("#102030")),
            timeout_seconds=5,
            interval_seconds=0.5,
        ),
        If(
            condition=ColorIs(Point(60, 70), Color.from_hex("#102030")),
            then_steps=(Click(Point(100, 120)),),
            else_steps=(Wait(0.2),),
        ),
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
.venv/bin/python -m pytest --cov=game_automation --cov-report=term-missing
```

## 项目状态

这是一个早期实验项目，当前重点是领域模型和 port-and-adapter 边界。屏幕图像匹配端口、脚本级图片存在条件和按图片定位点击已经建立；OCR、脚本文件格式、多窗口编排和自动窗口查找都还没有实现。
