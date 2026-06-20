## MODIFIED Requirements

### Requirement: ScreenStateIs 条件通过 ScreenStateReader 端口评估
引擎层 `ScriptRunner` SHALL 支持通过 `ScreenStateReader` 端口评估 `ScreenStateIs` 条件。runner MUST 保持平台无关，不得直接读取状态配置文件、启动 UI 或创建桌面图像匹配 adapter。外层 application MAY 提供带缓存策略的 `ScreenStateReader` 实现。

#### Scenario: 状态相等时条件成立
- **GIVEN** ScreenStateReader 返回当前状态 `主页`
- **AND** ScriptRunner 评估 `ScreenStateIs("主页")`
- **THEN** 条件结果为 true

#### Scenario: 状态不等时条件不成立
- **GIVEN** ScreenStateReader 返回当前状态 `装备`
- **AND** ScriptRunner 评估 `ScreenStateIs("主页")`
- **THEN** 条件结果为 false

#### Scenario: 条件最低置信度传递给 reader
- **WHEN** ScriptRunner 评估带最低置信度的 `ScreenStateIs`
- **THEN** runner 通过 ScreenStateReader 端口传递该最低置信度

#### Scenario: 缺少状态 reader 时失败
- **WHEN** ScriptRunner 需要评估 `ScreenStateIs` 但没有 ScreenStateReader
- **THEN** runner 返回清晰运行错误
