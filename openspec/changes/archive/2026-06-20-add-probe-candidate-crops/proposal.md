## Why

探测诊断截图可以看到候选最佳匹配框，但用户仍需要在整张大截图里放大查看框内内容。为了更快判断素材和区域是否正确，需要把每个候选的 `best_rect` 单独裁剪成小图，直接看到 Star 认为“最像”的画面片段。

## What Changes

- 新增 application 用例：执行一轮界面状态探测并导出每个候选 `best_rect` 的裁剪图。
- 新增 CLI 子命令 `star capture-probe-crops`。
- 输出裁剪图到 `.star/debug/screenshots/probe-crops/`。

## Capabilities

### New Capabilities

- 用户可以导出状态探测候选最佳匹配位置的裁剪图，用于校准素材和区域。

### Modified Capabilities

- `screen-state-probe`: 增加候选最佳匹配位置裁剪导出能力。

## Impact

- 影响 application 层、本地 CLI 和测试。
- 不改变图片匹配阈值、状态选择规则、脚本条件语义、UI 行为或 `assets/screen-states.json` 格式。
