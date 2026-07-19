## ADDED Requirements

### Requirement: CLI 支持一轮任务编排

系统 SHALL 提供 `star run-plan <script>...` 命令，用于在一次操作中按用户给定顺序运行多个已有命名脚本。Run Plan MUST 复用命名脚本 catalog、共享脚本资源、dry-run adapter、真实运行 adapter 和单脚本运行结果映射；CLI MUST NOT 解释脚本步骤语义。

#### Scenario: dry-run 顺序执行多个脚本
- **WHEN** 用户运行 `star run-plan first second --dry-run`
- **AND** `first` 和 `second` 都是可用命名脚本
- **THEN** 系统按顺序 dry-run 两个脚本
- **AND** 输出包含两个脚本的运行摘要
- **AND** 命令返回成功退出码

#### Scenario: 默认遇到失败后停止
- **WHEN** 用户运行 `star run-plan first second --dry-run`
- **AND** `first` 返回非零退出码
- **THEN** 系统不运行 `second`
- **AND** 输出包含 `first` 的失败摘要
- **AND** 命令返回 `first` 的退出码

#### Scenario: 默认遇到未满足条件后停止
- **WHEN** 用户运行 `star run-plan first second --dry-run`
- **AND** `first` 以退出码 0 和 `stopped_unmet_condition` 正常停止
- **THEN** 系统不运行 `second`
- **AND** 整轮摘要使用 `stopped_unmet_condition`，不得显示为 `completed`
- **AND** 命令保持成功退出码

#### Scenario: 继续收集失败后的结果
- **WHEN** 用户运行 `star run-plan first second --dry-run --continue-on-error`
- **AND** `first` 返回非零退出码
- **THEN** 系统继续运行 `second`
- **AND** 输出包含两个脚本的运行摘要
- **AND** 命令返回第一个失败脚本的退出码

#### Scenario: 自动使用每个脚本的图片依赖
- **WHEN** 用户运行 `star run-plan first second --dry-run --dry-run-script-images`
- **AND** 两个脚本分别声明图片依赖
- **THEN** 系统为每个脚本使用该脚本自己的图片依赖执行 dry-run

#### Scenario: 未知脚本阻止计划执行
- **WHEN** 用户运行 `star run-plan missing second --dry-run`
- **AND** `missing` 不是可用脚本
- **THEN** 系统返回非零退出码并提示未知脚本
- **AND** 不运行后续脚本
