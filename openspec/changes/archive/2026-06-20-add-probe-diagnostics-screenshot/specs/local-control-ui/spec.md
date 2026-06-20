## ADDED Requirements

### Requirement: UI 生成界面探测诊断截图

本地控制 UI SHALL 提供探测诊断入口，用于执行一轮界面状态探测并展示带候选最佳匹配框的诊断截图。HTTP adapter MUST 只把请求委托给 application 层，UI MUST 展示退出码、输出信息和诊断图片。

#### Scenario: 页面展示探测诊断入口

- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示用于生成界面探测诊断截图的按钮

#### Scenario: 生成并展示探测诊断截图

- **WHEN** 用户点击探测诊断按钮
- **THEN** 系统执行一轮界面状态探测并保存诊断截图
- **AND** UI 在诊断预览区域展示该图片

#### Scenario: 探测诊断失败

- **WHEN** 状态探测、截图或屏幕尺寸不可用
- **THEN** 系统返回非零退出码和清晰错误消息
- **AND** UI 展示错误消息
