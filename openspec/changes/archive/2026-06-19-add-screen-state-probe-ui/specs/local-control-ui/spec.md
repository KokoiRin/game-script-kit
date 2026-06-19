## ADDED Requirements

### Requirement: UI 提供界面状态探测 tab
本地控制 UI SHALL 提供独立的界面状态探测 tab，让用户在不运行脚本的情况下持续观察当前界面状态。HTTP adapter MUST 只把探测启动、停止和状态查询请求委托给 application 层。

#### Scenario: 页面展示界面探测入口
- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示界面状态探测 tab、启动探测按钮、停止探测按钮和探测日志区域

#### Scenario: 启动界面状态探测
- **WHEN** 用户点击启动界面状态探测
- **THEN** UI 调用探测启动接口，并展示探测会话运行中状态

#### Scenario: 查询界面状态探测
- **WHEN** 页面轮询探测状态接口
- **THEN** UI 展示当前识别状态、最近退出码以及已收集日志

#### Scenario: 停止界面状态探测
- **WHEN** 用户点击停止界面状态探测
- **THEN** UI 调用探测停止接口，并最终展示探测会话已停止状态
