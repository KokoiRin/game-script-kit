## Why

状态驱动脚本可以通过 `ScreenStateIs` 控制行为，但 UI 当前只展示步骤树和依赖，用户需要自己从缩进文本里读出“哪个状态会触发什么动作”。状态决策摘要能让用户更快判断脚本是否按预期响应当前界面状态。

## What Changes

- 脚本详情增加结构化 `state_decisions` 字段。
- 每个状态决策摘要包含状态名、命中时执行的步骤摘要、未命中时执行的步骤摘要。
- 本地 UI 在脚本详情中单独展示状态决策。
- 不改变脚本执行、条件评估或依赖检查语义。

## Capabilities

### New Capabilities

### Modified Capabilities
- `local-control-ui`: 脚本详情需要展示状态驱动决策摘要，帮助用户理解状态条件脚本。

## Impact

- 影响脚本详情 presenter、HTTP payload 和前端详情渲染。
- 增加 application/HTTP/UI 静态行为测试。
- 不新增外部依赖，不改变 engine 行为。
