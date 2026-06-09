## Why

坐标记录工具现在只能记录鼠标屏幕坐标；编写游戏脚本时，用户还需要知道该点当前颜色，才能后续手工设计颜色判断或状态识别逻辑。

先把“单点取色”接入现有坐标记录工具，可以在不改变脚本执行语义、不引入分支控制流的前提下，验证取色端口和平台 adapter 的边界是否合理。

## What Changes

- 新增平台无关的 RGB 颜色值对象，用于表达单个屏幕点的颜色。
- 新增平台无关的单点颜色读取端口，使业务逻辑通过 port 读取颜色，而不是直接依赖 `pyautogui`。
- 新增桌面/pyautogui 单点取色 adapter，用于读取指定屏幕坐标的颜色。
- 扩展 `CoordinateRecorder`：
  - 定时打印当前鼠标坐标时，同时打印当前点颜色。
  - 用户按 `1` 记录时，同时记录该坐标和该点颜色。
  - 结束后打印记录列表时，同时打印每条记录的坐标和颜色。
- 保持坐标记录工具作为独立入口 `star recorder`，不新增脚本动作、不改变 `ScriptRunner`、不实现脚本分支。
- 不包含 breaking changes；现有脚本运行行为保持不变。

## Capabilities

### New Capabilities
- `screen-color-sampling`: 定义平台无关的单点 RGB 颜色模型和颜色读取端口，以及平台 adapter 通过端口读取指定屏幕坐标颜色的行为。

### Modified Capabilities
- `coordinate-recorder-tool`: 坐标记录工具在实时显示、按键记录和结束汇总时，同时包含当前点的颜色信息，并继续通过端口接入平台相关实现。

## Impact

- Affected code:
  - `src/game_automation/domain/`：新增颜色值对象并导出。
  - `src/game_automation/engine/ports.py`：新增单点颜色读取端口。
  - `src/game_automation/adapters/desktop/`：新增 pyautogui 单点取色 adapter，并在桌面 adapter 包中导出。
  - `src/game_automation/tools/coordinate_recorder.py`：记录和输出从 `Point` 扩展为包含 `Point` + `Color` 的记录。
  - `src/game_automation/star_cli.py`：组装坐标读取、按键读取和颜色读取 adapter 后启动 recorder。
  - `tests/`：新增颜色模型、颜色 adapter、坐标记录器颜色输出测试。
  - `README.md`：更新坐标记录工具说明。
- Dependencies:
  - 继续复用现有 `pyautogui` 依赖；不新增第三方依赖。
- Systems:
  - macOS/桌面环境可能需要屏幕录制或自动化权限才能截图取色；错误需要清晰报告 setup 问题。
