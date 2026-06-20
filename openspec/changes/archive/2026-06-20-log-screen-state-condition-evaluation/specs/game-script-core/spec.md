## ADDED Requirements

### Requirement: ScriptRunner 记录界面状态条件评估日志
引擎层 SHALL 在评估 `ScreenStateIs` 条件时通过已注入的运行日志端口记录评估摘要。日志 MUST 包含期望状态、实际状态、最低置信度和条件是否匹配。未注入日志端口时，系统 MUST 保持现有条件评估行为且不报错。

#### Scenario: 状态条件命中时记录日志
- **WHEN** ScriptRunner 评估 `ScreenStateIs("主页")`
- **AND** `ScreenStateReader` 返回当前状态 `主页`
- **THEN** 运行日志包含期望状态 `主页`、实际状态 `主页` 和匹配结果 `True`

#### Scenario: 状态条件未命中时记录日志
- **WHEN** ScriptRunner 评估 `ScreenStateIs("主页")`
- **AND** `ScreenStateReader` 返回当前状态 `人物`
- **THEN** 运行日志包含期望状态 `主页`、实际状态 `人物` 和匹配结果 `False`

#### Scenario: 没有日志端口时保持静默
- **WHEN** 条件评估调用未注入运行日志端口
- **THEN** `ScreenStateIs` 条件继续按当前状态返回布尔结果
