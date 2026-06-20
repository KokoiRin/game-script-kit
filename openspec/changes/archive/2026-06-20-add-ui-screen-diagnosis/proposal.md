## Why

`star diagnose-screen` 已经能把截图健康和单轮状态探测合成一次诊断，但用户主要在本地 UI 中调试脚本和观察状态。若诊断只能在 CLI 中运行，UI 中遇到“识别不到图片”时仍需要切回终端，反馈链路不够顺手。

## What Changes

- 在本地 UI 增加屏幕识别环境诊断按钮。
- 新增 `/api/diagnose-screen` HTTP endpoint，委托 application 层 `diagnose_screen_setup()`。
- UI 点击诊断按钮时传递当前界面探测最低置信度，并展示 stdout、stderr、退出码和诊断截图。
- 不修改状态探测语义、截图实现、图片匹配算法或脚本 DSL。

## Capabilities

### New Capabilities

### Modified Capabilities
- `local-control-ui`: 增加本地 UI 屏幕识别环境诊断入口。

## Impact

- 影响本地 UI HTTP adapter、静态 HTML/JS/CSS 和 UI endpoint 测试。
- 复用已有 application 层 `diagnose_screen_setup()`，不新增平台依赖。
- 影响 `local-control-ui` OpenSpec 规格。
