## ADDED Requirements

### Requirement: UI 使用探测状态填充 dry-run 状态
本地控制 UI SHALL 允许用户把最近一次界面探测返回的非 `未知` 状态填入 dry-run 模拟状态输入。最近探测状态为 `未知` 或没有探测结果时，系统 MUST 保留用户当前输入且展示清晰提示。

#### Scenario: 使用已识别状态
- **GIVEN** 界面探测最近返回当前状态 `主页`
- **WHEN** 用户点击使用探测状态按钮
- **THEN** dry-run 模拟状态输入被设置为 `主页`

#### Scenario: 没有可用探测状态
- **GIVEN** 界面探测最近状态为 `未知`
- **WHEN** 用户点击使用探测状态按钮
- **THEN** dry-run 模拟状态输入保持不变
- **AND** 页面展示没有可用探测状态的提示
