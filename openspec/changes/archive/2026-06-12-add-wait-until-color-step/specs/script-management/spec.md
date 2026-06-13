## ADDED Requirements

### Requirement: CLI dry-run 支持条件等待示例脚本
系统 SHALL 提供一个默认注册的条件等待示例脚本，使用户可以通过 `star run <name> --dry-run` 验证 `WaitUntil(ColorIs(...))` 的成功和超时路径。

#### Scenario: 默认 catalog 包含条件等待示例脚本
- **WHEN** 用户列出默认脚本
- **THEN** 结果中包含一个可用于验证条件等待的示例脚本

#### Scenario: dry-run 验证条件等待成功路径
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-color #RRGGBB` 提供满足条件的固定颜色
- **THEN** 系统会立即通过条件等待，并打印后续计划操作

#### Scenario: dry-run 验证条件等待超时路径
- **WHEN** 用户通过 `star run <name> --dry-run` 使用不满足条件的默认固定颜色
- **THEN** 系统会按等待间隔打印计划等待操作，并以非零退出码报告条件等待超时
