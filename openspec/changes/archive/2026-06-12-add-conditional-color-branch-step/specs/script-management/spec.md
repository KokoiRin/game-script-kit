## ADDED Requirements

### Requirement: CLI dry-run 支持条件分支脚本
系统 SHALL 允许用户通过 `star run <name> --dry-run` 验证包含颜色条件分支的脚本。dry-run 模式 MUST 使用可预测的颜色读取实现，而不读取真实屏幕。

#### Scenario: dry-run 使用默认固定颜色
- **WHEN** 用户通过 `star run <name> --dry-run` 运行条件分支脚本且未指定 dry-run 颜色
- **THEN** 系统会使用默认固定颜色评估颜色条件，并打印对应分支的计划操作

#### Scenario: dry-run 使用用户指定颜色
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-color #RRGGBB` 运行条件分支脚本
- **THEN** 系统会使用用户指定颜色评估颜色条件，并打印对应分支的计划操作

#### Scenario: 默认 catalog 包含条件分支示例脚本
- **WHEN** 用户列出默认脚本
- **THEN** 结果中包含一个可用于验证颜色条件分支的示例脚本

### Requirement: CLI 真实运行注入颜色读取 adapter
系统 SHALL 在真实运行包含颜色条件分支的脚本时注入桌面取色 adapter，使 runner 可以通过 `PixelColorReader` 端口评估颜色条件。

#### Scenario: macOS 模式运行条件分支脚本
- **WHEN** 用户通过 `star run <name>` 运行条件分支脚本
- **THEN** 系统会同时加载输入设备 adapter 和颜色读取 adapter，并把它们注入 ScriptRunner

#### Scenario: 颜色读取 adapter setup 失败被报告
- **WHEN** 真实运行时颜色读取 adapter 因依赖、权限或运行环境不可用而初始化失败
- **THEN** CLI 会返回非零退出码，并向用户报告脚本运行 setup 失败
