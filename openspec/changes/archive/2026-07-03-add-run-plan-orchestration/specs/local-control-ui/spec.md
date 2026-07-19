## MODIFIED Requirements

### Requirement: UI 展示运行日志和图片匹配耗时

本地控制 UI SHALL 区分脚本完整执行和因条件未满足正常停止。等待条件超时或图片目标未找到时，运行状态 MUST 使用 `stopped_unmet_condition`，并以中文展示为正常停止而非运行失败。

#### Scenario: 展示未满足前置条件
- **WHEN** 后台脚本因为等待条件超时或图片目标未找到而正常停止
- **THEN** UI 展示 `stopped_unmet_condition` 对应的中文结束原因
- **AND** UI 不把该情况显示为运行失败
