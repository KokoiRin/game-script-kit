## Why

当 `probe-state` 返回 `未知` 时，用户需要快速确认两件事：当前截图是否拿到了正确游戏画面，以及 `assets/screen-states.json` 中的识别区域是否覆盖到素材所在位置。现在这些诊断能力只在 UI 中有入口，命令行调试和 harness 调用不够直接。

## What Changes

- 新增 `star capture-screen` 子命令，保存一张当前屏幕截图。
- 新增 `star capture-region-diagnostics` 子命令，保存一张带状态识别区域框的诊断截图。
- 两个命令复用 application 层已有截图诊断能力。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `screen-state-probe`: CLI 提供状态识别截图与区域诊断入口。

## Impact

- 影响 CLI 参数和输出。
- 需要补充 CLI 行为测试。
- 不修改状态识别规则、图片匹配策略、配置格式或 UI 行为。
