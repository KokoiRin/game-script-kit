## ADDED Requirements

### Requirement: CLI dry-run 支持使用当前探测界面状态

系统 SHALL 允许用户通过 `star run <name> --dry-run --dry-run-probed-screen-state` 在运行 dry-run 前执行一轮界面状态探测，并把探测结果的 `current_state` 作为本次 dry-run 的固定界面状态。CLI MUST 复用 application 层状态探测用例，不得在入口层执行图片匹配或解释状态识别规则。

#### Scenario: dry-run 使用当前探测状态

- **WHEN** 用户运行 `star run <name> --dry-run --dry-run-probed-screen-state`
- **AND** 单次界面状态探测返回当前状态 `主页`
- **AND** 命名脚本包含 `ScreenStateIs("主页")`
- **THEN** CLI 使用 `主页` 作为本次 dry-run 状态条件输入
- **AND** dry-run 按状态命中分支输出计划操作

#### Scenario: 参数要求 dry-run 模式

- **WHEN** 用户运行 `star run <name> --dry-run-probed-screen-state` 但未提供 `--dry-run`
- **THEN** CLI 返回配置错误且不运行脚本

#### Scenario: 状态来源冲突

- **WHEN** 用户同时提供 `--dry-run-probed-screen-state` 和 `--dry-run-screen-state 主页`
- **THEN** CLI 返回配置错误且不运行脚本

#### Scenario: 探测配置错误

- **WHEN** 状态配置非法
- **AND** 用户运行 `star run <name> --dry-run --dry-run-probed-screen-state`
- **THEN** CLI 返回配置错误并把原因写入 stderr
- **AND** 不运行脚本

#### Scenario: 探测运行失败

- **WHEN** 图像定位 adapter 不可用
- **AND** 用户运行 `star run <name> --dry-run --dry-run-probed-screen-state`
- **THEN** CLI 返回运行错误并把原因写入 stderr
- **AND** 不运行脚本
