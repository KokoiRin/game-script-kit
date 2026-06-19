## ADDED Requirements

### Requirement: ScriptRunner 支持取消运行
引擎层 `ScriptRunner` SHALL 支持可选取消检查；当取消信号被置位时，runner MUST 停止执行后续脚本步骤并报告脚本运行已取消。取消机制 MUST 通过可注入端口表达，不得依赖 UI、HTTP 或平台 adapter。

#### Scenario: 重复步骤中取消
- **WHEN** ScriptRunner 执行 `Repeat` 时取消信号变为已取消
- **THEN** runner 停止后续轮次和步骤，并报告运行已取消

#### Scenario: 等待前后检查取消
- **WHEN** ScriptRunner 执行等待步骤前或等待返回后发现取消信号
- **THEN** runner 停止后续脚本步骤，并报告运行已取消

#### Scenario: 未注入取消检查时行为不变
- **WHEN** ScriptRunner 未注入取消检查
- **THEN** runner 按现有语义完整执行脚本
