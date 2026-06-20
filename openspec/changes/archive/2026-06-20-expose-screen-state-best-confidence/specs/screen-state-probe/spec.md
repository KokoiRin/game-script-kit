## ADDED Requirements

### Requirement: 界面状态候选暴露最佳匹配置信度

系统 SHALL 在界面状态探测候选结果中暴露每个已执行候选的最佳匹配置信度。候选未达到最低阈值时，系统 MUST 仍保留底层图像匹配得到的最佳分数；候选被跳过或无法执行匹配时，最佳置信度 MAY 为 `null`。状态选择规则 MUST 继续只根据是否达到最低阈值判断命中。

#### Scenario: 未命中候选保留最佳置信度

- **WHEN** 候选图片匹配得到最佳分数 `0.62`
- **AND** 该候选最低阈值为 `0.8`
- **THEN** 候选结果未命中
- **AND** 候选结果的 `best_confidence` 为 `0.62`

#### Scenario: CLI JSON 输出最佳置信度

- **WHEN** 用户运行 `star probe-state --json`
- **THEN** 每个候选 JSON object 包含 `best_confidence`
- **AND** 未命中候选的 `confidence` 仍为 `null`

#### Scenario: CLI 文本输出最佳置信度

- **WHEN** 用户运行 `star probe-state`
- **THEN** 每个候选文本行包含最佳置信度
