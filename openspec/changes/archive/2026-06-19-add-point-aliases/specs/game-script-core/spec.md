## ADDED Requirements

### Requirement: Runner 解析命名点位点击
引擎层 `ScriptRunner` SHALL 在执行点击前解析命名点位目标。解析 MUST 使用脚本携带的 portable 资源目录，不得直接依赖平台 adapter。

#### Scenario: 命名点位点击成功
- **WHEN** `Click` 目标引用命名点位 `头像`，且该名称解析为 `Point(242, 92)`
- **THEN** runner 会点击 `Point(242, 92)`

#### Scenario: 命名点位点击应用脚本窗口
- **WHEN** 脚本绑定 `AreaWindow` 且 `Click` 目标引用命名点位
- **THEN** runner 会按现有窗口规则把点位解析为屏幕坐标后再点击

#### Scenario: 未知命名点位点击失败
- **WHEN** `Click` 目标引用未注册的命名点位
- **THEN** runner 会拒绝执行该点击并报告未知点位名称
