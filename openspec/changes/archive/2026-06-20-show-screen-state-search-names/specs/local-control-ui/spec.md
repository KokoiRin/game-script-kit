## ADDED Requirements

### Requirement: UI 展示界面候选搜索项名称
本地控制 UI SHALL 在最近界面候选结果中展示配置搜索项名称。HTTP 状态查询 payload MUST 为每个候选结果包含 `search_name` 字段；当该字段存在时，页面 MUST 同时展示状态名和搜索项名。

#### Scenario: HTTP 候选结果包含搜索项名称
- **WHEN** 页面轮询 `/api/screen-state-probe` 且最近候选来自搜索项 `离开按钮`
- **THEN** HTTP 响应候选结果包含 `search_name` 为 `离开按钮`

#### Scenario: 页面展示状态和搜索项
- **WHEN** 最近候选结果的状态名为 `战斗失败`，搜索项名称为 `离开按钮`
- **THEN** 页面展示 `战斗失败 / 离开按钮`

#### Scenario: 无搜索项名称时只展示状态名
- **WHEN** 最近候选结果没有搜索项名称
- **THEN** 页面只展示状态名
