## ADDED Requirements

### Requirement: 默认脚本包含界面状态等待示例

系统 SHALL 在默认脚本 catalog 中提供 `wait-until-screen-state-demo`，用于展示脚本如何等待当前界面状态达到指定值后继续执行。该脚本 MUST 使用 `WaitUntil(ScreenStateIs("主页"))` 表达等待语义，并在等待成功后执行后续示例动作。

#### Scenario: 默认 catalog 列出状态等待示例

- **WHEN** 用户运行 `star list`
- **THEN** 输出包含 `wait-until-screen-state-demo`

#### Scenario: 详情展示状态等待步骤

- **WHEN** 用户运行 `star details wait-until-screen-state-demo`
- **THEN** 输出包含 `WaitUntil ScreenStateIs("主页")`
- **AND** 输出包含状态依赖检查结果

#### Scenario: dry-run 状态等待成功

- **WHEN** 用户运行 `star run wait-until-screen-state-demo --dry-run --dry-run-screen-state 主页`
- **THEN** dry-run 使用 `主页` 作为当前界面状态
- **AND** 脚本继续执行等待后的示例动作
