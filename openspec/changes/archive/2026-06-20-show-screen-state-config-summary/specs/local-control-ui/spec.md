## ADDED Requirements

### Requirement: UI 展示界面状态配置摘要
本地控制 UI SHALL 在界面探测 tab 展示当前界面状态配置摘要。HTTP adapter MUST 提供配置摘要接口，并只委托 application 层生成摘要。页面 MUST 展示状态名、搜索项、图片路径、区域信息和最低置信度；没有配置或配置非法时 MUST 展示清晰提示。

#### Scenario: 页面加载状态配置摘要
- **WHEN** 用户打开本地 UI 页面且状态配置有效
- **THEN** 页面通过 HTTP 接口获取并展示状态配置摘要

#### Scenario: 没有状态配置
- **WHEN** 用户打开本地 UI 页面但没有 `assets/screen-states.json`
- **THEN** 页面展示未配置状态识别
- **AND** 页面仍允许用户启动界面探测

#### Scenario: 状态配置非法
- **WHEN** 状态配置摘要接口返回非零退出码
- **THEN** 页面展示配置错误消息
- **AND** 页面不尝试在前端解析配置文件
