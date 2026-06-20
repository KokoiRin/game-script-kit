## Why

用户现在可以通过 `probe-state` 查看当前界面，也可以通过 `--dry-run-screen-state` 手工指定 dry-run 状态。但实际调试脚本时，更自然的路径是：先读取当前游戏界面状态，再用这个状态安全地 dry-run 脚本分支，避免真实点击桌面。

## What Changes

- 为 `star run` 增加 `--dry-run-probed-screen-state` 参数。
- 该参数要求同时使用 `--dry-run`，执行脚本前先探测一次当前界面状态。
- 探测成功后，把探测结果的 `current_state` 作为 dry-run 固定状态运行脚本。
- 保持手工 `--dry-run-screen-state`、真实运行和 UI 行为不变。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `script-management`: CLI dry-run 支持使用当前探测到的界面状态作为状态条件输入。

## Impact

- 影响 CLI `star run` 参数和 dry-run 前置流程。
- 需要补充 CLI 行为测试和错误路径测试。
- 不修改脚本 DSL、状态识别配置格式或图片匹配策略。
