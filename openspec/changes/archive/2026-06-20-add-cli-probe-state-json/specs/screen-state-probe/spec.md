## ADDED Requirements

### Requirement: CLI 单次界面状态探测支持 JSON 输出

系统 SHALL 支持用户通过 `star probe-state --json` 获取机器可读的一轮界面状态探测结果。JSON 输出 MUST 复用 application 层状态探测结果，不得在 CLI 入口层执行图片匹配或解释状态识别规则。

#### Scenario: 输出机器可读探测结果

- **WHEN** 用户运行 `star probe-state --json`
- **THEN** CLI 执行一轮状态探测
- **AND** stdout 输出 JSON object
- **AND** JSON 包含 `current_state`、`known`、`elapsed_ms` 和 `candidates`
- **AND** 每个候选包含 `name`、`search_name`、`status`、`elapsed_ms` 和 `confidence`

#### Scenario: JSON 输出保留最低置信度参数

- **WHEN** 用户运行 `star probe-state --json --min-confidence 0.75`
- **THEN** CLI 使用 `0.75` 作为本次状态探测最低置信度
- **AND** stdout 输出 JSON object

#### Scenario: JSON 候选状态使用稳定枚举

- **WHEN** 候选命中、未命中或被跳过
- **AND** 用户运行 `star probe-state --json`
- **THEN** 对应候选的 `status` 分别为 `matched`、`missed` 或 `skipped`

#### Scenario: JSON 模式下配置错误仍写入 stderr

- **WHEN** 状态配置非法
- **AND** 用户运行 `star probe-state --json`
- **THEN** CLI 返回配置错误并把原因写入 stderr
- **AND** stdout 不输出 JSON
