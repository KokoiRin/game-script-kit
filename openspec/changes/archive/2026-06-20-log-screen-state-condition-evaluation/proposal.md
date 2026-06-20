## Why

状态驱动脚本已经可以根据 `ScreenStateIs` 分支执行，但运行日志只间接体现分支结果。用户调试脚本时需要直接看到“期望状态、实际状态、是否命中”，否则很难判断是状态识别问题、脚本条件写错，还是分支逻辑问题。

## What Changes

- `ScreenStateIs` 条件评估时输出结构化运行日志。
- 日志包含期望状态、实际状态、最低置信度和匹配结果。
- 不改变状态读取、条件真假、分支执行和等待语义。

## Capabilities

### New Capabilities

### Modified Capabilities
- `game-script-core`: 界面状态条件评估需要产生可观察日志，帮助用户调试状态驱动脚本。

## Impact

- 影响 `condition_evaluator` 的日志输出。
- 补充 condition evaluator 和 script run 行为测试。
- 不新增依赖，不改变 adapter 或 UI 结构。
