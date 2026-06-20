## MODIFIED Requirements

### Requirement: UI 生成状态区域诊断截图

本地控制 UI SHALL 提供状态区域诊断入口，根据当前屏幕截图和 `assets/screen-states.json` 中的命名区域生成带区域框的诊断图片。HTTP adapter MUST 只把请求委托给 application 层，UI MUST 展示退出码、输出信息和诊断图片。application 层 MAY 通过专用屏幕诊断 use case 承载内部编排，但 MUST 保持 HTTP endpoint 和前端 payload 语义稳定。

#### Scenario: 页面展示区域诊断入口

- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示用于生成状态区域诊断截图的按钮

#### Scenario: 生成并展示区域诊断截图

- **WHEN** 用户点击区域诊断按钮且 `assets/screen-states.json` 包含命名区域
- **THEN** 系统保存一张带区域框和区域名称的诊断图片
- **AND** UI 在诊断预览区域展示该图片

#### Scenario: 缺少状态区域配置

- **WHEN** 用户点击区域诊断按钮但状态配置不存在、非法或没有命名区域
- **THEN** 系统返回非零退出码和清晰错误消息
- **AND** 系统不启动界面状态探测循环
