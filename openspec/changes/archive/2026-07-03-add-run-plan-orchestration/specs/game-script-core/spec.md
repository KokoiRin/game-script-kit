## MODIFIED Requirements

### Requirement: ScriptRunner 执行条件等待步骤

引擎层 `ScriptRunner` SHALL 在条件等待未满足时正常停止本轮脚本，并返回调用方可观察的 `stopped_unmet_condition` 结束原因。正常停止 MUST 保持成功退出码，不得误报完整执行。

#### Scenario: 条件等待未满足
- **WHEN** `WaitUntil` 在超时时间内始终不满足
- **THEN** runner 不执行后续步骤
- **AND** runner 返回 `stopped_unmet_condition` 结束原因

### Requirement: ScriptRunner 执行图片目标点击

引擎层 `ScriptRunner` SHALL 在图片目标未找到时正常停止本轮脚本，并返回调用方可观察的 `stopped_unmet_condition` 结束原因。

#### Scenario: 图片目标未找到
- **WHEN** `ScreenImageLocator` 没有找到图片目标
- **THEN** runner 不执行点击和后续步骤
- **AND** runner 返回 `stopped_unmet_condition` 结束原因
