## Why

`ScriptRunner` 已经支持通过 `ScreenStateReader` 评估 `ScreenStateIs`，UI 运行脚本时也会注入状态 reader。但 CLI 的本地桌面运行路径没有注入该 reader，导致 `star run <name>` 真实运行含界面状态条件的脚本时无法参考当前识别状态。

## What Changes

- 修复本地桌面 CLI 脚本运行装配，真实运行时为状态条件脚本注入 `ScreenStateReader`。
- 复用现有本地控制 application 的状态探测 reader，避免 CLI 入口直接执行图片匹配。
- 保持 dry-run 的 `--dry-run-screen-state` 行为不变。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `script-management`: `star run` 真实运行状态条件脚本时必须装配界面状态读取能力。

## Impact

- 影响本地桌面 composition 的真实运行依赖注入。
- 需要补充 composition 层行为测试。
- 不修改脚本 DSL、状态识别配置格式或 UI 行为。
