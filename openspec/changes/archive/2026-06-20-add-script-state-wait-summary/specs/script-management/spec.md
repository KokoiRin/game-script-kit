## ADDED Requirements

### Requirement: 脚本详情展示状态等待摘要

系统 SHALL 在脚本详情中展示 `WaitUntil(ScreenStateIs(...))` 的状态等待摘要，使用户可以区分“脚本根据状态分支”和“脚本等待某个状态后继续”。该摘要 MUST 由 application 层脚本详情能力生成，CLI 和 UI 入口不得自行解析脚本步骤文本。

#### Scenario: CLI 展示状态等待

- **WHEN** 用户运行 `star details wait-until-screen-state-demo`
- **THEN** CLI 输出包含“状态等待”分组
- **AND** 输出包含 `等待状态: 主页`

#### Scenario: UI 详情接口返回状态等待

- **WHEN** UI 通过 `/api/script-details` 请求包含 `WaitUntil(ScreenStateIs("主页"))` 的脚本详情
- **THEN** JSON payload 包含 `state_waits` 字段
- **AND** `state_waits` 包含 `主页`

#### Scenario: UI 使用当前探测状态预览等待满足情况

- **WHEN** UI 已获得当前探测状态 `主页`
- **AND** 当前脚本详情包含状态等待 `主页`
- **THEN** 脚本详情展示该状态等待当前已满足
