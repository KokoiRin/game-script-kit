# script-management Specification

## Purpose
定义脚本管理能力（`scripts_manager` 包），使具名脚本可被集中保存、查找和通过 `star` CLI 按名称启动。
## Requirements
### Requirement: 命名脚本可被集中管理

系统 SHALL 在 `scripts_manager.catalog` 中提供 `ScriptCatalog`，用于集中保存和通过名称查找多个具名 `Script` 定义。

#### Scenario: 列出所有脚本

- **WHEN** 调用方请求查看可用脚本
- **THEN** 系统会返回所有已注册脚本的名称

#### Scenario: 按名称读取脚本

- **WHEN** 调用方使用已存在的脚本名称读取脚本
- **THEN** 系统会返回对应的 `Script` 定义

#### Scenario: 未知脚本名称被拒绝

- **WHEN** 调用方使用不存在的脚本名称读取脚本
- **THEN** 系统会拒绝请求，并报告脚本名称不存在

#### Scenario: 重复脚本名称被拒绝

- **WHEN** 系统加载多个名称相同的脚本定义
- **THEN** 系统会拒绝脚本集合，并报告脚本名称重复

### Requirement: 脚本定义可独立编辑

系统 SHALL 将脚本定义放在 `scripts_manager` 中，与 `engine` 和 `adapters` 分离，使用户可以编辑某个脚本而不需要修改 runner 或平台 adapter。

#### Scenario: 编辑脚本动作不影响 runner

- **WHEN** 用户修改 `scripts_manager` 中某个脚本定义的动作序列
- **THEN** `ScriptRunner` 和 `InputDevice` adapter 不需要同步修改即可执行更新后的脚本

#### Scenario: 新增脚本不需要新增专用 CLI

- **WHEN** 用户新增一个脚本定义并注册到 `ScriptCatalog` 中
- **THEN** 用户可以通过 `star run <name>` 按名称启动该脚本

### Requirement: CLI 支持按名称启动脚本

系统 SHALL 提供 `star` 命令行入口，允许用户通过脚本名称选择并启动脚本。

#### Scenario: dry-run 指定脚本

- **WHEN** 用户通过 `star run <name> --dry-run` 运行脚本
- **THEN** 系统会使用 `DryRunInputDevice` 按该脚本的动作顺序即时打印计划执行的操作，而不移动真实鼠标

#### Scenario: macOS 模式指定脚本

- **WHEN** 用户通过 `star run <name>` 运行脚本（默认使用 macOS adapter）
- **THEN** 系统会加载 macOS `InputDevice` adapter 并执行该脚本

#### Scenario: CLI 报告未知脚本

- **WHEN** 用户通过 `star run <name>` 指定不存在的脚本名称
- **THEN** 系统会返回非零退出码，并提示该脚本不存在

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
