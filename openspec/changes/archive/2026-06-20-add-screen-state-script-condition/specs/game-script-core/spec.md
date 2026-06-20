## ADDED Requirements

### Requirement: ScriptRunner 评估界面状态条件
引擎层 `ScriptRunner` SHALL 支持通过 `ScreenStateReader` 端口评估 `ScreenStateIs` 条件。runner MUST 保持平台无关，不得直接读取状态配置文件、启动 UI 或创建桌面图像匹配 adapter。

#### Scenario: 界面状态条件为真
- **WHEN** `ScreenStateReader` 返回当前状态 `主页`
- **AND** ScriptRunner 评估 `ScreenStateIs("主页")`
- **THEN** 条件评估结果为真

#### Scenario: 界面状态条件为假
- **WHEN** `ScreenStateReader` 返回当前状态 `人物`
- **AND** ScriptRunner 评估 `ScreenStateIs("主页")`
- **THEN** 条件评估结果为假

#### Scenario: 界面状态条件传递最低置信度
- **WHEN** ScriptRunner 评估带最低置信度的 `ScreenStateIs`
- **THEN** 条件评估模块会把该最低置信度传给 `ScreenStateReader`

#### Scenario: 缺少界面状态读取端口时报错
- **WHEN** ScriptRunner 执行包含界面状态条件的脚本但未注入界面状态读取端口
- **THEN** 它会拒绝执行该条件并报告界面状态读取端口缺失

#### Scenario: 条件分支使用界面状态条件
- **WHEN** ScriptRunner 执行界面状态条件结果为真的 `If`
- **THEN** 它会按现有条件分支语义执行 `then_steps`

#### Scenario: 条件等待使用界面状态条件
- **WHEN** ScriptRunner 执行界面状态条件初始为假但在超时前变为真的 `WaitUntil`
- **THEN** 它会按现有条件等待语义轮询并在条件满足后继续执行后续步骤
