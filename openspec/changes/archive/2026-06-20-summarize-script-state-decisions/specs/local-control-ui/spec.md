## ADDED Requirements

### Requirement: UI 展示脚本状态决策摘要
本地控制 UI SHALL 在脚本详情中展示状态驱动决策摘要。脚本详情 HTTP payload MUST 包含结构化字段 `state_decisions`；每个决策 MUST 包含状态名、状态命中时执行的步骤摘要，以及状态未命中时执行的步骤摘要。该摘要 MUST 由 application 层生成，HTTP adapter 和前端不得直接解释脚本步骤模型。

#### Scenario: 展示状态分支决策
- **WHEN** 用户选择包含 `If(ScreenStateIs("主页"))` 的脚本
- **THEN** 脚本详情 payload 包含状态决策 `主页`
- **AND** 页面展示状态为 `主页` 时执行的步骤摘要

#### Scenario: 展示状态未命中分支
- **WHEN** 状态分支包含 else 步骤
- **THEN** 状态决策摘要包含状态未命中时执行的步骤摘要

#### Scenario: 没有状态决策
- **WHEN** 用户选择不包含 `If(ScreenStateIs(...))` 的脚本
- **THEN** 页面展示没有状态决策
