## Why

脚本已经可以使用 `ScreenStateIs(...)` 根据当前界面状态做分支，但本地 UI 运行脚本时无法指定 dry-run 的当前状态。用户在 UI 中调试状态驱动脚本时，只能切回 CLI 使用 `--dry-run-screen-state`，反馈链路不够顺手。

## What Changes

- 本地 UI 的脚本运行工具栏新增“模拟状态”输入。
- UI 启动脚本时把该值作为 dry-run 当前状态传给 application 层。
- 后台脚本运行和同步脚本运行都使用该参数构造 dry-run 状态 reader。
- 默认值保持 `未知`，不影响不使用状态条件的脚本。

## Capabilities

### New Capabilities

### Modified Capabilities
- `local-control-ui`: UI 运行命名脚本时支持指定 dry-run 当前界面状态。

## Impact

- 影响本地控制 UI 静态页面、前端请求 payload、HTTP adapter 和 application 层脚本运行用例。
- 不改变 `ScreenStateIs` DSL、engine port 或真实状态探测语义。
- 不新增运行时依赖。
