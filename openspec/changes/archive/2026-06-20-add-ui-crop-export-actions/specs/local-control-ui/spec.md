## ADDED Requirements

### Requirement: UI 触发状态裁剪导出

本地控制 UI SHALL 提供状态区域裁剪和探测候选裁剪导出入口。HTTP adapter MUST 只把请求委托给 application 层裁剪导出用例，并把 application 返回的退出码、stdout 和 stderr 展示给用户。

#### Scenario: 页面展示裁剪导出入口

- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示区域裁剪导出按钮
- **AND** 页面展示探测候选裁剪导出按钮

#### Scenario: 导出状态区域裁剪

- **WHEN** 用户点击区域裁剪导出按钮
- **THEN** UI 调用区域裁剪导出接口
- **AND** HTTP adapter 调用 application 层区域裁剪导出用例
- **AND** UI 展示 application 返回的输出和错误信息

#### Scenario: 导出探测候选裁剪

- **WHEN** 用户点击探测候选裁剪导出按钮
- **THEN** UI 调用探测候选裁剪导出接口
- **AND** HTTP adapter 把当前最低置信度传给 application 层候选裁剪导出用例
- **AND** UI 展示 application 返回的输出和错误信息
