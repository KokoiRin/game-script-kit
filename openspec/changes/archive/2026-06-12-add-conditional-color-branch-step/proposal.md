## Why

当前脚本已经支持固定顺序动作和 `Repeat` 控制流，但无法根据屏幕状态选择不同步骤。用户在编写游戏脚本时需要基于单点颜色判断走不同分支，同时继续保持领域模型、runner、adapter 和脚本管理的模块边界清晰。

## What Changes

- 新增平台无关的条件模型，用于表达脚本可评估的运行时判断。
- 新增单点颜色匹配条件，复用现有 `Color` 和 `PixelColorReader` 端口，不把取色能力并入 `InputDevice`。
- 新增 `If` 控制流步骤，按条件结果执行 `then_steps` 或可选 `else_steps`。
- 扩展 `ScriptRunner`，让 runner 解释 `If`，并通过注入的颜色读取端口评估颜色条件。
- 扩展 CLI adapter 组装：真实运行时注入桌面取色 adapter，dry-run 使用可预测的取色 reader，保证分支脚本可测试和可演示。
- 增加一个命名示例脚本，用现有 `star run <name> --dry-run` 路径验证条件分支行为。

## Capabilities

### New Capabilities

### Modified Capabilities
- `script-action-model`: 增加条件模型和 `If` 条件分支步骤的领域约束。
- `game-script-core`: 增加 `ScriptRunner` 对条件分支步骤的解释语义，并保持输入设备和屏幕读取端口分离。
- `script-management`: 增加条件分支脚本通过默认 catalog 和 CLI dry-run 可运行的行为。
- `screen-color-sampling`: 明确脚本运行时可以通过已有取色端口读取屏幕颜色以评估条件。

## Impact

- 受影响代码：`src/game_automation/domain/`、`src/game_automation/engine/runner.py`、`src/game_automation/engine/ports.py`、`src/game_automation/adapters/dry_run.py`、`src/game_automation/star_cli.py`、`src/game_automation/scripts_manager/`。
- 受影响测试：领域模型测试、runner 测试、CLI dry-run 测试、脚本 catalog 测试。
- 不新增第三方依赖；继续复用现有 pyautogui 桌面取色 adapter。
- 不引入外部 YAML/JSON DSL、不做区域取色、图像识别、OCR、表达式解析器或运行时变量系统。
