## ADDED Requirements

### Requirement: 本地 UI 提供屏幕识别环境诊断入口

本地控制 UI SHALL 提供屏幕识别环境诊断入口，用于从浏览器触发一次截图诊断和单轮界面状态探测。HTTP adapter MUST 委托 application 层组合用例，UI MUST 展示退出码、stdout、stderr 和诊断截图。

#### Scenario: 页面提供环境诊断按钮
- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示屏幕识别环境诊断按钮
- **AND** 前端脚本会向 `/api/diagnose-screen` 发起请求

#### Scenario: HTTP 触发环境诊断
- **WHEN** UI 向 `/api/diagnose-screen` 提交最低置信度
- **THEN** HTTP adapter 调用 application 层屏幕诊断用例
- **AND** payload 包含退出码、stdout、stderr、截图路径和截图预览 URL

#### Scenario: 非法最低置信度
- **WHEN** UI 向 `/api/diagnose-screen` 提交非数字最低置信度
- **THEN** HTTP adapter 不调用 application 层屏幕诊断用例
- **AND** payload 返回配置错误和清晰错误原因
