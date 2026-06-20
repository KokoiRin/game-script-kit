## Context

本地 UI 已有独立的截屏诊断、区域诊断、探测诊断和候选裁剪按钮，也已有固定高度日志区和截图预览。`LocalControlApplication.diagnose_screen_setup()` 已经在 application 层组合截图诊断与单轮状态探测，适合作为 UI 的屏幕识别环境诊断后端。

本变更只把该用例暴露给 UI，不在浏览器端解释状态探测规则，也不在 HTTP adapter 中执行截图或图片匹配。

## Goals / Non-Goals

**Goals:**

- UI 中提供一个按钮，运行屏幕识别环境诊断。
- HTTP adapter 新增 `/api/diagnose-screen`，解析最低置信度并委托 application 层。
- 诊断结果复用已有结果日志和截图预览展示方式。

**Non-Goals:**

- 不新增后台循环诊断。
- 不修改 `probe-state`、`capture-screen` 或 `diagnose-screen` CLI 行为。
- 不自动修复 macOS 权限或前台窗口问题。
- 不重新设计 UI 布局。

## Decisions

1. **复用现有截图预览状态。**
   - 理由：`diagnose_screen_setup()` 返回普通截图路径，HTTP adapter 可以像 `/api/capture-screen` 一样更新 `latest_screenshot_path` 和 `screenshot_url`，浏览器无需新增图片通道。
   - 备选：新增独立诊断截图 URL。当前诊断截图就是普通截图，独立通道会增加状态管理复杂度。

2. **复用 `screen-state-confidence` 输入。**
   - 理由：环境诊断中的状态探测和现有界面探测使用同一最低置信度概念，用户不需要维护两套参数。
   - 备选：新增一个诊断专用置信度输入。当前没有独立调参需求，会增加界面负担。

3. **HTTP adapter 只做参数校验和 payload 转换。**
   - 理由：符合项目入口层保持薄的约束；诊断组合语义已经在 application 层。

## Risks / Trade-offs

- [Risk] UI 按钮增多后工具栏更拥挤。→ Mitigation：把诊断按钮放在已有截图诊断工具组内，复用现有按钮样式和日志区。
- [Risk] 用户可能混淆“探测诊断截图”和“屏幕识别环境诊断”。→ Mitigation：按钮文案使用“环境诊断”，输出仍显示保存截图和状态探测摘要。
