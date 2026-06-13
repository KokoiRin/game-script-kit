## Why

当前脚本可以用 `If(ColorIs(...))` 根据屏幕颜色分支，但无法表达“等待某个颜色出现再继续”。游戏脚本里常见的加载、按钮亮起、状态刷新都需要这种带超时的等待能力。

## What Changes

- 新增 `WaitUntil(condition, timeout_seconds, interval_seconds)` 控制流步骤。
- `WaitUntil` 复用现有 `Condition` 和 `condition_evaluator`，第一版主要服务 `ColorIs`。
- `ScriptRunner` 解释 `WaitUntil` 时反复评估条件；条件满足则继续后续步骤，超时则抛出清晰 `TimeoutError`。
- 等待间隔通过现有 `InputDevice.wait()` 执行，不新增平台 adapter 方法。
- `script_requirements` 递归识别 `WaitUntil` 里的颜色条件，CLI 继续只根据端口需求组装 reader。
- 新增 `wait-until-color-demo` 命名脚本和 README 端到端 dry-run 验证命令。

## Capabilities

### New Capabilities

### Modified Capabilities
- `script-action-model`: 增加 `WaitUntil` 控制流步骤的领域约束。
- `game-script-core`: 增加 runner 对 `WaitUntil` 的解释语义、轮询、超时和嵌套控制流行为。
- `script-management`: 增加可通过默认 catalog 和 CLI dry-run 验证的 `WaitUntil` 示例脚本。

## Impact

- 受影响代码：`src/game_automation/domain/actions.py`、`src/game_automation/domain/__init__.py`、`src/game_automation/engine/runner.py`、`src/game_automation/engine/script_requirements.py`、`src/game_automation/scripts_manager/`、`README.md`。
- 受影响测试：领域模型、runner、脚本需求分析、CLI transcript、脚本 catalog。
- 不新增第三方依赖；不修改 `InputDevice`、`PixelColorReader`、macOS adapter 或桌面取色 adapter 接口。
- 不引入组合条件、表达式语言、真实时间源抽象、无限等待、`break/continue` 或运行时变量。
