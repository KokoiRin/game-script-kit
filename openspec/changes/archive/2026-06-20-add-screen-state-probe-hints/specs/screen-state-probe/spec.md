## ADDED Requirements

### Requirement: 界面状态探测暴露诊断提示

系统 SHALL 在一轮界面状态探测结果中提供用户可见的诊断提示列表。当探测结果为未知、至少执行过一个候选、所有已执行候选都提供最佳置信度且最大最佳置信度为 `0` 时，系统 MUST 提示用户可能需要检查屏幕录制权限、前台窗口或桌面会话。CLI 和 UI MUST 复用该结构化提示，不得在入口层重复解释候选匹配规则。

#### Scenario: 未知状态且最佳置信度全为零

- **WHEN** 一轮状态探测没有候选命中
- **AND** 所有已执行候选的 `best_confidence` 都为 `0`
- **THEN** 探测结果的诊断提示包含检查屏幕录制权限、前台窗口或桌面会话的提示

#### Scenario: 普通未命中不提示权限问题

- **WHEN** 一轮状态探测没有候选命中
- **AND** 至少一个已执行候选的 `best_confidence` 大于 `0`
- **THEN** 探测结果不生成疑似截图不可用提示

#### Scenario: CLI 文本输出诊断提示

- **WHEN** 用户运行 `star probe-state`
- **AND** 探测结果包含诊断提示
- **THEN** CLI 输出“提示”分组
- **AND** 输出每条诊断提示

#### Scenario: CLI JSON 输出诊断提示

- **WHEN** 用户运行 `star probe-state --json`
- **AND** 探测结果包含诊断提示
- **THEN** JSON object 包含 `hints` 数组
- **AND** `hints` 包含诊断提示

#### Scenario: UI 状态接口返回诊断提示

- **WHEN** 页面轮询 `/api/screen-state-probe`
- **AND** 最近一轮探测结果包含诊断提示
- **THEN** HTTP payload 包含 `hints` 字段
- **AND** 页面展示诊断提示
