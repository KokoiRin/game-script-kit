## ADDED Requirements

### Requirement: UI 展示选中脚本详情
本地控制 UI SHALL 在用户选择脚本时展示该脚本的可读详情。详情 MUST 包含脚本名称、步骤摘要和依赖摘要。HTTP adapter MUST 只委托 application 层生成详情，不得在入口层解释脚本模型。

#### Scenario: 展示状态驱动脚本详情
- **WHEN** 用户在本地 UI 选择包含 `ScreenStateIs("主页")` 的脚本
- **THEN** 页面展示该脚本名称
- **AND** 页面展示包含 `ScreenStateIs("主页")` 的步骤摘要
- **AND** 页面展示该脚本依赖界面状态 `主页`

#### Scenario: 未知脚本详情请求
- **WHEN** UI 请求不存在的脚本详情
- **THEN** 系统返回非零退出码和清晰错误消息
