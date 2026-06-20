## Why

真实 `star probe-state` 当前可能只输出 `当前状态：未知`，但用户需要知道这是素材没命中，还是截图权限/桌面会话导致画面不可用。截图诊断命令已经能提示疑似全黑截图，单次状态探测也应暴露类似的诊断线索，减少排查成本。

## What Changes

- 状态探测结果新增用户可见的诊断提示列表。
- 当一轮探测没有识别出状态，且已执行候选的最佳置信度全部为 `0` 时，结果提示用户检查屏幕录制权限、前台窗口或桌面会话。
- `star probe-state` 文本输出和 JSON 输出展示该提示。
- 本地 UI 的后台状态探测 payload 和页面展示该提示。
- 不改变图片匹配算法、状态选择规则或截图诊断命令。

## Capabilities

### New Capabilities

### Modified Capabilities

- `screen-state-probe`: 状态探测结果、CLI 输出和 UI 状态接口增加诊断提示。

## Impact

- 影响界面状态探测领域结果、CLI `probe-state` presenter、本地 UI 状态 payload 和前端展示。
- 需要补充领域结果、CLI 文本/JSON、UI HTTP payload 和静态页面测试。
